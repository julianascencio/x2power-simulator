"""Offline, deterministic case: measured substrate properties plus explicit assumptions."""

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, dataclass, fields
from math import fsum
from pathlib import Path
from typing import Any

from x2power import AuxiliaryLoads, Generator, SolidFeedstock
from x2power.methods.bmp import BMPProcess, simulate_bmp_digestion
from x2power.methods.cost_benefit import (
    AnnualCashFlow,
    break_even_unit_value,
    evaluate_cost_benefit,
    value_electricity,
)
from x2power.utilities.validation import fraction, number

INPUTS = Path(__file__).with_name("inputs.json")
DAYS = 365  # a representative operating year, not a replay of the 2024 calendar


@dataclass(frozen=True)
class Assumptions:
    """Explicit engineering/economic choices; no defaults hidden outside inputs.json."""

    feed_tonnes_per_year: float
    bmp_realization_fraction: float
    dry_lhv_mj_per_kg: float
    methane_fraction: float
    methane_capture_fraction: float
    methane_lhv_kwh_per_nm3: float
    generator_rating_kw: float
    electrical_efficiency: float
    heat_recovery_efficiency: float
    digester_temperature_c: float
    feed_temperature_c: float
    ambient_temperature_c: float
    feed_heat_capacity_kj_per_kg_k: float
    digester_working_volume_m3: float
    feed_density_kg_per_m3: float
    heat_loss_kw_per_k: float
    fixed_auxiliary_power_kw: float
    mixing_power_w_per_m3: float
    feed_preparation_kwh_per_tonne: float
    electricity_fraction_of_gross: float
    electric_heater_efficiency: float
    process_heat_usable_fraction: float
    chp_outage_day_ranges: list[list[int]]
    self_consumption_fraction: float
    avoided_purchase_price_eur_per_kwh: float
    export_price_eur_per_kwh: float
    import_price_eur_per_kwh: float
    gate_fee_eur_per_tonne: float
    collection_eur_per_tonne: float
    transport_loaded_distance_km: float
    transport_eur_per_tonne_km: float
    residue_handling_eur_per_feed_tonne: float
    horizon_years: int
    real_discount_rate: float
    replacement_year: int
    replacement_cost_eur: float
    decommissioning_cost_eur: float
    salvage_value_eur: float

    def __post_init__(self) -> None:
        for item in fields(self):
            name = item.name
            if name == "chp_outage_day_ranges":
                continue
            value = getattr(self, name)
            if name.endswith("_c"):
                number(name, value, minimum=-273.15, strict=True)
            else:
                number(name, value)
            if name.endswith("_fraction") or name.endswith("_efficiency"):
                fraction(name, value)
        for name in (
            "feed_tonnes_per_year",
            "digester_working_volume_m3",
            "feed_density_kg_per_m3",
        ):
            number(name, getattr(self, name), strict=True)
        for name in ("horizon_years", "replacement_year"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.replacement_year > self.horizon_years:
            raise ValueError("replacement_year exceeds horizon_years")
        outage_days(self.chp_outage_day_ranges)


def outage_days(ranges: list[list[int]]) -> set[int]:
    """Validate inclusive, one-based day ranges without overlap."""
    days: set[int] = set()
    if not isinstance(ranges, list):
        raise ValueError("chp_outage_day_ranges must be a list")
    for bounds in ranges:
        if (
            not isinstance(bounds, list)
            or len(bounds) != 2
            or any(isinstance(v, bool) or not isinstance(v, int) for v in bounds)
            or not 1 <= bounds[0] <= bounds[1] <= DAYS
        ):
            raise ValueError("Outage bounds must be integer days in 1..365")
        interval = set(range(bounds[0], bounds[1] + 1))
        if days & interval:
            raise ValueError("Outage ranges overlap")
        days |= interval
    return days


def load_case(path: str | Path = INPUTS) -> dict[str, Any]:
    """Read the pinned inputs without a network call."""
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config, dict) or type(config.get("schema_version")) is not int:
        raise ValueError("Case requires integer schema_version")
    if config["schema_version"] != 1:
        raise ValueError("Only case schema_version 1 is supported")
    return config


def _cost_items(items: dict[str, float]) -> dict[str, float]:
    if not isinstance(items, dict) or not items:
        raise ValueError("Cost breakdown must be a non-empty object")
    for name, value in items.items():
        number(name, value)
    return dict(items)


def simulate_case(config: dict[str, Any]) -> dict[str, Any]:
    """Run daily heat/electricity balances and a repeating annual cash-flow model.

    Feed and methane supply are constant; explicit CHP outage days do not stop
    digestion, heating or fixed loads. No storage, microbial dynamics or seasonal
    production is inferred. Positive deliveries and imports are summed separately.
    """
    a = Assumptions(**config["assumptions"])
    m = config["feedstock_measurements"]
    fraction("total_solids_fraction_wet", m["total_solids_fraction_wet"])
    feed = SolidFeedstock(
        a.feed_tonnes_per_year * 1000 / DAYS,
        1 - m["total_solids_fraction_wet"],
        a.dry_lhv_mj_per_kg,
    )
    process = BMPProcess(
        m["volatile_solids_fraction_ts"],
        m["methane_potential_nm3_per_kg_vs_fed"],
        a.bmp_realization_fraction,
        a.methane_fraction,
        a.methane_capture_fraction,
        a.methane_lhv_kwh_per_nm3,
    )
    generator = Generator(
        a.electrical_efficiency, a.heat_recovery_efficiency, a.generator_rating_kw
    )
    heat = (
        feed.mass_kg
        * a.feed_heat_capacity_kj_per_kg_k
        * max(0.0, a.digester_temperature_c - a.feed_temperature_c)
        / 3600
        + a.heat_loss_kw_per_k * max(0.0, a.digester_temperature_c - a.ambient_temperature_c) * 24
    )
    auxiliaries = AuxiliaryLoads(
        fixed_power_kw=(
            a.fixed_auxiliary_power_kw
            + a.mixing_power_w_per_m3 * a.digester_working_volume_m3 / 1000
        ),
        electricity_fraction_of_gross=a.electricity_fraction_of_gross,
        process_electricity_kwh=feed.mass_kg / 1000 * a.feed_preparation_kwh_per_tonne,
        electric_heater_efficiency=a.electric_heater_efficiency,
        process_heat_usable_fraction=a.process_heat_usable_fraction,
    )
    offline = outage_days(a.chp_outage_day_ranges)
    # There are only two distinct operating conditions. Calculate each once.
    conditions = {
        available: simulate_bmp_digestion(
            feed,
            process,
            generator,
            duration_h=24,
            availability=float(available),
            process_heat_kwh=heat,
            auxiliaries=auxiliaries,
        )
        for available in (False, True)
    }
    results = [conditions[day not in offline] for day in range(1, DAYS + 1)]
    powers = [asdict(result.power) for result in results]
    totals = {key: fsum(power[key] for power in powers) for key in powers[0]}
    delivered = fsum(max(0, result.power.net_electricity_kwh) for result in results)
    imported = fsum(max(0, -result.power.net_electricity_kwh) for result in results)
    electricity = value_electricity(
        delivered,
        imported,
        self_consumption_fraction=a.self_consumption_fraction,
        avoided_purchase_price_per_kwh=a.avoided_purchase_price_eur_per_kwh,
        export_price_per_kwh=a.export_price_eur_per_kwh,
        import_price_per_kwh=a.import_price_eur_per_kwh,
    )
    capital = _cost_items(config["capital_costs_eur"])
    costs = _cost_items(config["annual_fixed_costs_eur"])
    variable = {
        "collection": a.feed_tonnes_per_year * a.collection_eur_per_tonne,
        "transport": a.feed_tonnes_per_year
        * a.transport_loaded_distance_km
        * a.transport_eur_per_tonne_km,
        "residue_handling": a.feed_tonnes_per_year * a.residue_handling_eur_per_feed_tonne,
        "import_electricity": electricity["import_cost"],
    }
    if costs.keys() & variable.keys():
        raise ValueError("Fixed cost names collide with calculated variable costs")
    costs.update(variable)
    benefits = {
        "export_electricity": electricity["export_revenue"],
        "avoided_electricity_purchase": electricity["avoided_purchase_value"],
        "gate_fees": a.feed_tonnes_per_year * a.gate_fee_eur_per_tonne,
    }
    flows = [AnnualCashFlow(0, costs=fsum(capital.values()))]
    for year in range(1, a.horizon_years + 1):
        replacement = a.replacement_cost_eur if year == a.replacement_year else 0
        last = year == a.horizon_years
        flows.append(
            AnnualCashFlow(
                year,
                costs=fsum(costs.values())
                + replacement
                + (a.decommissioning_cost_eur if last else 0),
                benefits=fsum(benefits.values()) + (a.salvage_value_eur if last else 0),
                delivered_electricity_kwh=delivered,
            )
        )
    financial = evaluate_cost_benefit(flows, a.real_discount_rate).to_dict()
    annuity = fsum((1 / (1 + a.real_discount_rate)) ** y for y in range(1, a.horizon_years + 1))
    salvage_pv = a.salvage_value_eur * (1 / (1 + a.real_discount_rate)) ** a.horizon_years
    other_pv = benefits["gate_fees"] * annuity + salvage_pv
    electricity_pv = (
        benefits["export_electricity"] + benefits["avoided_electricity_purchase"]
    ) * annuity
    metrics = {
        "annual_delivered_electricity_kwh": delivered,
        "annual_imported_electricity_kwh": imported,
        "annual_net_electricity_kwh": totals["net_electricity_kwh"],
        "annual_methane_produced_nm3": fsum(r.metrics["methane_produced_nm3"] for r in results),
        "annual_methane_not_captured_nm3": fsum(
            r.metrics["methane_not_captured_nm3"] for r in results
        ),
        "annual_unused_methane_equivalent_nm3": totals["unused_fuel_energy_kwh"]
        / a.methane_lhv_kwh_per_nm3,
        "annual_operating_cash_flow_eur": fsum(benefits.values()) - fsum(costs.values()),
        "net_kwh_per_wet_tonne": totals["net_electricity_kwh"] / a.feed_tonnes_per_year,
        "hydraulic_retention_days": a.digester_working_volume_m3
        / (feed.mass_kg / a.feed_density_kg_per_m3),
        "organic_loading_kg_vs_m3_day": feed.dry_mass_kg
        * m["volatile_solids_fraction_ts"]
        / a.digester_working_volume_m3,
        "outage_days": len(offline),
        "maximum_absolute_generator_balance_residual_kwh": max(
            abs(r.power.balance_residual_kwh) for r in results
        ),
        "break_even_delivered_electricity_eur_per_kwh": break_even_unit_value(
            financial["present_value_costs"], other_pv, delivered * annuity
        ),
        "break_even_total_gate_fee_eur_per_tonne": break_even_unit_value(
            financial["present_value_costs"],
            electricity_pv + salvage_pv,
            a.feed_tonnes_per_year * annuity,
        ),
    }
    daily = [
        {
            "day": day,
            "chp_available": day not in offline,
            **power,
            "delivered_electricity_kwh": max(0, power["net_electricity_kwh"]),
            "imported_electricity_kwh": max(0, -power["net_electricity_kwh"]),
        }
        for day, power in enumerate(powers, start=1)
    ]
    return {
        "case_name": config["case_name"],
        "inputs_sha256": hashlib.sha256(
            json.dumps(config, sort_keys=True, allow_nan=False).encode()
        ).hexdigest(),
        "model": (
            "Steady BMP screening with 365 daily CHP/heat balances; "
            "no biological stability prediction"
        ),
        "price_basis": config["financial_basis"],
        "inputs": deepcopy(config),
        "annual_power_totals": totals,
        "electricity_valuation": electricity,
        "capital_costs_eur": capital,
        "annual_costs_eur": costs,
        "annual_benefits_eur": benefits,
        "metrics": metrics,
        "cost_benefit": financial,
        "daily_results": daily,
    }


def sensitivities(config: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    """Deterministic stress tests, not probabilistic confidence intervals."""
    yield_rows = []
    for realization in (0.5, 0.7, 0.9):
        changed = deepcopy(config)
        changed["assumptions"]["bmp_realization_fraction"] = realization
        result = simulate_case(changed)
        yield_rows.append(
            {
                "bmp_realization_fraction": realization,
                "net_electricity_kwh": result["metrics"]["annual_net_electricity_kwh"],
                "imported_electricity_kwh": result["metrics"]["annual_imported_electricity_kwh"],
                "net_present_value_eur": result["cost_benefit"]["net_present_value"],
            }
        )
    a = Assumptions(**config["assumptions"])
    factors = fsum((1 / (1 + a.real_discount_rate)) ** y for y in range(1, a.horizon_years + 1))
    present_energy = baseline["cost_benefit"]["discounted_delivered_electricity_kwh"]
    base_value = (
        a.self_consumption_fraction * a.avoided_purchase_price_eur_per_kwh
        + (1 - a.self_consumption_fraction) * a.export_price_eur_per_kwh
    )
    prices = [0.05 + i * 0.025 for i in range(11)]
    fees = [float(i * 5) for i in range(13)]
    grid = [
        {
            "delivered_electricity_value_eur_per_kwh": price,
            "gate_fee_eur_per_tonne": fee,
            "net_present_value_eur": baseline["cost_benefit"]["net_present_value"]
            + (price - base_value) * present_energy
            + (fee - a.gate_fee_eur_per_tonne) * a.feed_tonnes_per_year * factors,
        }
        for fee in fees
        for price in prices
    ]
    return {
        "horizon_years": a.horizon_years,
        "bmp_realization": yield_rows,
        "electricity_value_gate_fee": grid,
    }
