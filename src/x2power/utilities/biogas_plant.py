"""Configuration, tabulation and energy totals for continuous biogas plants."""

from collections.abc import Sequence
from typing import Any

from x2power.methods.biogas_plant import (
    BiogasPlant,
    ContinuousDigester,
    DigesterFeedstock,
    PlantResult,
)
from x2power.models import Generator


def plant_from_config(config: dict[str, Any]) -> BiogasPlant:
    """Read a dedicated plant schema, separate from the existing route scenario schema.

    Accepts JSON-compatible dictionaries; unknown constructor fields are rejected.
    The optional name and assumptions fields are descriptive metadata only.
    """
    if set(config) - {"schema_version", "model", "name", "assumptions", "plant"}:
        raise ValueError("Unknown plant configuration fields")
    version = config.get("schema_version")
    if type(version) is not int or version != 1 or config.get("model") != "continuous_biogas_plant":
        raise ValueError("Expected continuous_biogas_plant schema_version 1")
    try:
        data = dict(config["plant"])
        data["feedstocks"] = tuple(DigesterFeedstock(**feed) for feed in data["feedstocks"])
        data["digester"] = ContinuousDigester(**data["digester"])
        data["generator"] = Generator(**data["generator"])
        return BiogasPlant(**data)
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Invalid plant configuration: {exc}") from exc


def plant_profile_rows(results: Sequence[PlantResult]) -> list[dict[str, Any]]:
    """Flatten interval metrics and power values with explicit elapsed timestamps."""
    rows = []
    elapsed = 0.0
    for result in results:
        row = {
            "start_h": elapsed,
            "end_h": elapsed + result.power.duration_h,
            **result.to_dict()["power"],
            **result.metrics,
            "flags": ";".join(result.flags),
        }
        rows.append(row)
        elapsed += result.power.duration_h
    return rows


def summarize_plant(results: Sequence[PlantResult]) -> dict[str, float]:
    """Sum additive flows/energies only; do not sum HRT, OLR or stored inventories."""
    if not results:
        raise ValueError("Cannot summarize an empty plant simulation")
    power_keys = (
        "duration_h",
        "gross_electricity_kwh",
        "net_electricity_kwh",
        "recovered_heat_kwh",
        "auxiliary_electricity_kwh",
        "electric_heating_kwh",
        "process_heat_demand_kwh",
        "heat_to_process_kwh",
        "generator_loss_kwh",
    )
    metric_keys = (
        "wet_feed_kg",
        "volatile_solids_fed_kg",
        "volatile_solids_destroyed_kg",
        "effluent_volatile_solids_kg",
        "methane_produced_nm3",
        "methane_not_captured_nm3",
        "biogas_captured_nm3",
        "biogas_to_chp_nm3",
        "biogas_flared_nm3",
        "grid_import_kwh",
        "grid_export_kwh",
        "site_electricity_demand_kwh",
        "site_heat_demand_kwh",
        "heat_delivered_to_site_kwh",
        "unserved_site_heat_kwh",
        "rejected_heat_kwh",
    )
    totals = {key: sum(getattr(r.power, key) for r in results) for key in power_keys}
    for key in metric_keys:
        totals[key] = sum(float(r.metrics[key] or 0) for r in results)
    totals["mean_net_power_kw"] = totals["net_electricity_kwh"] / totals["duration_h"]
    totals["initial_stored_biogas_nm3"] = float(
        results[0].metrics["initial_stored_biogas_nm3"] or 0
    )
    totals["final_stored_biogas_nm3"] = results[-1].state.stored_biogas_nm3
    for key in ("vs_balance_residual_kg", "gas_balance_residual_nm3"):
        totals["maximum_absolute_" + key] = max(abs(float(r.metrics[key] or 0)) for r in results)
    return totals
