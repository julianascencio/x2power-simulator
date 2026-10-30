"""Mixed-feed CSTR, gas inventory and CHP simulation; see docs/biogas_plants.md.

The first-order substrate pools are a reduced-order approximation, not ADM1.
Temperature is maintained by recovered heat and unlimited electric backup heat.
Gas dispatch uses each interval's average production; use short operating intervals.
"""

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from math import exp, expm1, fsum
from typing import Any

from x2power.methods.generation import generate_power
from x2power.models import AuxiliaryLoads, Generator, PowerResult
from x2power.utilities.validation import fraction, number


@dataclass(frozen=True)
class DigesterFeedstock:
    """Continuous wet feed; methane yield is per kg of degradable VS destroyed.

    ``total_solids_fraction`` is wet basis; ``volatile_solids_fraction_ts`` is
    relative to total solids. ``biodegradable_vs_fraction`` partitions incoming VS
    into degradable and inert pools. Rate constants apply at the declared digester
    temperature and require calibration. Gas volumes are dry at 0 C, 101325 Pa.
    """

    name: str
    wet_mass_kg_per_day: float
    total_solids_fraction: float
    volatile_solids_fraction_ts: float
    biodegradable_vs_fraction: float
    methane_yield_nm3_per_kg_vs_destroyed: float
    decay_rate_per_day: float
    density_kg_per_m3: float = 1000.0
    dry_lhv_mj_per_kg: float = 18.0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Feedstock name must be non-empty")
        for key in (
            "wet_mass_kg_per_day",
            "methane_yield_nm3_per_kg_vs_destroyed",
            "decay_rate_per_day",
        ):
            number(key, getattr(self, key))
        for key in (
            "total_solids_fraction",
            "volatile_solids_fraction_ts",
            "biodegradable_vs_fraction",
        ):
            fraction(key, getattr(self, key))
        number("density_kg_per_m3", self.density_kg_per_m3, strict=True)
        number("dry_lhv_mj_per_kg", self.dry_lhv_mj_per_kg, strict=True)

    @property
    def vs_kg_per_day(self) -> float:
        return (
            self.wet_mass_kg_per_day * self.total_solids_fraction * self.volatile_solids_fraction_ts
        )


@dataclass(frozen=True)
class ContinuousDigester:
    """One perfectly mixed working volume; no solids retention or liquid recycle.

    HRT and OLR limits only produce diagnostic flags; they are not inhibition
    kinetics or universal operating recommendations. Heat loss is UA * delta T.
    """

    working_volume_m3: float
    temperature_c: float = 37.0
    heat_loss_kw_per_k: float = 0.0
    feed_heat_capacity_kj_per_kg_k: float = 4.18
    minimum_hrt_days: float | None = None
    maximum_olr_kg_vs_m3_day: float | None = None

    def __post_init__(self) -> None:
        number("working_volume_m3", self.working_volume_m3, strict=True)
        number("temperature_c", self.temperature_c, minimum=-273.15, strict=True)
        number("heat_loss_kw_per_k", self.heat_loss_kw_per_k)
        number("feed_heat_capacity_kj_per_kg_k", self.feed_heat_capacity_kj_per_kg_k, strict=True)
        for key in ("minimum_hrt_days", "maximum_olr_kg_vs_m3_day"):
            if getattr(self, key) is not None:
                number(key, getattr(self, key), strict=True)


@dataclass(frozen=True)
class BiogasPlant:
    """Plant parameters shared across intervals, without third-party dependencies.

    Storage capacity is dry normal biogas volume, not geometric membrane volume.
    Generator rating is mandatory and gross electrical. Fixed loads and mixing
    persist during outages. Treatment electricity applies to all captured gas.
    """

    feedstocks: tuple[DigesterFeedstock, ...]
    digester: ContinuousDigester
    generator: Generator
    gas_storage_capacity_nm3: float = 0.0
    methane_fraction: float = 0.6
    capture_fraction: float = 0.98
    methane_lhv_kwh_per_nm3: float = 9.94
    fixed_auxiliary_power_kw: float = 0.0
    mixing_power_w_per_m3: float = 0.0
    feed_preparation_kwh_per_tonne: float = 0.0
    gas_treatment_kwh_per_nm3: float = 0.0
    electric_heater_efficiency: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.feedstocks, tuple) or not self.feedstocks:
            raise ValueError("feedstocks must be a non-empty tuple")
        if len({feed.name for feed in self.feedstocks}) != len(self.feedstocks):
            raise ValueError("Feedstock names must be unique")
        if self.generator.rated_power_kw is None:
            raise ValueError("Plant generator requires rated_power_kw")
        for key in (
            "gas_storage_capacity_nm3",
            "fixed_auxiliary_power_kw",
            "mixing_power_w_per_m3",
            "feed_preparation_kwh_per_tonne",
            "gas_treatment_kwh_per_nm3",
        ):
            number(key, getattr(self, key))
        fraction("methane_fraction", self.methane_fraction, positive=True)
        fraction("capture_fraction", self.capture_fraction)
        fraction("electric_heater_efficiency", self.electric_heater_efficiency, positive=True)
        number("methane_lhv_kwh_per_nm3", self.methane_lhv_kwh_per_nm3, strict=True)
        for feed in self.feedstocks:
            potential = (
                feed.volatile_solids_fraction_ts
                * feed.biodegradable_vs_fraction
                * feed.methane_yield_nm3_per_kg_vs_destroyed
                * self.methane_lhv_kwh_per_nm3
            )
            if potential > feed.dry_lhv_mj_per_kg / 3.6 + 1e-9:
                raise ValueError(f"Methane potential exceeds dry feedstock LHV: {feed.name}")


@dataclass(frozen=True)
class PlantInterval:
    """Constant inputs over one interval; multipliers follow feedstock tuple order.

    Empty multipliers use all base rates. Availability is an equivalent capacity
    derating within the interval; resolve actual outages as separate 0/1 intervals.
    The CHP follows its setpoint, regardless of external electrical/thermal demand.
    """

    duration_h: float = 1.0
    feed_multipliers: tuple[float, ...] = ()
    generator_availability: float = 1.0
    generator_setpoint_fraction: float = 1.0
    feed_temperature_c: float = 15.0
    ambient_temperature_c: float = 15.0
    site_electricity_demand_kw: float = 0.0
    site_heat_demand_kw: float = 0.0

    def __post_init__(self) -> None:
        number("duration_h", self.duration_h, strict=True)
        if not isinstance(self.feed_multipliers, tuple):
            raise ValueError("feed_multipliers must be a tuple")
        for value in self.feed_multipliers:
            number("feed_multiplier", value)
        fraction("generator_availability", self.generator_availability)
        fraction("generator_setpoint_fraction", self.generator_setpoint_fraction)
        for key in ("feed_temperature_c", "ambient_temperature_c"):
            number(key, getattr(self, key), minimum=-273.15, strict=True)
        number("site_electricity_demand_kw", self.site_electricity_demand_kw)
        number("site_heat_demand_kw", self.site_heat_demand_kw)


@dataclass(frozen=True)
class PlantState:
    """Inventory passed between calls for the same unchanged plant configuration."""

    feedstock_names: tuple[str, ...]
    degradable_vs_kg: tuple[float, ...]
    inert_vs_kg: tuple[float, ...]
    stored_biogas_nm3: float = 0.0

    def __post_init__(self) -> None:
        for values in (self.feedstock_names, self.degradable_vs_kg, self.inert_vs_kg):
            if not isinstance(values, tuple):
                raise ValueError("State pools and names must be tuples")
        if not (len(self.feedstock_names) == len(self.degradable_vs_kg) == len(self.inert_vs_kg)):
            raise ValueError("State pool lengths must match feedstock names")
        for value in self.degradable_vs_kg + self.inert_vs_kg:
            number("VS inventory", value)
        number("stored_biogas_nm3", self.stored_biogas_nm3)


@dataclass(frozen=True)
class PlantResult:
    """One interval ledger and end state; no digestate nutrient or full mass balance."""

    power: PowerResult
    state: PlantState
    metrics: dict[str, float | None]
    flags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _flows(plant: BiogasPlant, interval: PlantInterval) -> tuple[list[float], float, float]:
    multipliers = interval.feed_multipliers or (1.0,) * len(plant.feedstocks)
    if len(multipliers) != len(plant.feedstocks):
        raise ValueError("feed_multipliers must match the plant feedstock count")
    wet = [
        feed.wet_mass_kg_per_day * scale
        for feed, scale in zip(plant.feedstocks, multipliers, strict=True)
    ]
    flow = fsum(
        mass / feed.density_kg_per_m3 for mass, feed in zip(wet, plant.feedstocks, strict=True)
    )
    return wet, flow, flow / plant.digester.working_volume_m3


def initial_plant_state(
    plant: BiogasPlant,
    *,
    interval: PlantInterval | None = None,
    steady_state: bool = True,
    stored_biogas_nm3: float = 0.0,
) -> PlantState:
    """Initialize pools at constant-feed equilibrium or at zero VS inventory.

    Zero VS means an already full, warm liquid volume with no substrate inventory,
    not a prediction of microbial startup or digester filling. Gas defaults to zero.
    """
    number("stored_biogas_nm3", stored_biogas_nm3)
    if stored_biogas_nm3 > plant.gas_storage_capacity_nm3:
        raise ValueError("Initial biogas exceeds storage capacity")
    wet, _, dilution = _flows(plant, interval or PlantInterval())
    degradable, inert = [], []
    for feed, mass in zip(plant.feedstocks, wet, strict=True):
        vs = mass * feed.total_solids_fraction * feed.volatile_solids_fraction_ts
        rate = feed.decay_rate_per_day + dilution
        degradable.append(
            vs * feed.biodegradable_vs_fraction / rate if steady_state and rate > 0 else 0.0
        )
        inert.append(
            vs * (1 - feed.biodegradable_vs_fraction) / dilution
            if steady_state and dilution > 0
            else 0.0
        )
    return PlantState(
        tuple(f.name for f in plant.feedstocks), tuple(degradable), tuple(inert), stored_biogas_nm3
    )


def _pool(initial: float, inflow: float, rate: float, days: float) -> tuple[float, float]:
    """Exact nonnegative solution and integrated removal for dM/dt = inflow-rate*M."""
    if rate == 0:
        return initial + inflow * days, 0.0
    x = rate * days
    removed_fraction = -expm1(-x)
    # Stable integral of newly arriving substrate when x approaches zero.
    q = (
        x * (0.5 + x * (-1 / 6 + x * (1 / 24 - x / 120)))
        if x < 1e-4
        else (1 - removed_fraction / x)
    )
    remaining = initial * exp(-x) + inflow * days * (removed_fraction / x)
    removed = initial * removed_fraction + inflow * days * q
    return remaining, removed


def simulate_biogas_plant(
    plant: BiogasPlant,
    intervals: Sequence[PlantInterval],
    *,
    initial_state: PlantState | None = None,
) -> list[PlantResult]:
    """Integrate feed pools, dispatch captured gas and close electrical/heat ledgers.

    Without an explicit state, start at equilibrium for the first interval's feed
    rates with an empty gas holder. No automatic inhibition or temperature correction
    is applied to decay rates. Gas exceeding holder capacity is sent to an unlimited
    ideal flare. Flared gas volume is not an estimate of methane emitted to air.
    """
    if not intervals:
        raise ValueError("Supply at least one plant interval")
    state = initial_state or initial_plant_state(plant, interval=intervals[0])
    if state.feedstock_names != tuple(f.name for f in plant.feedstocks):
        raise ValueError("State feedstock names/order must match the plant")
    if state.stored_biogas_nm3 > plant.gas_storage_capacity_nm3:
        raise ValueError("Initial biogas exceeds storage capacity")
    results = []
    for interval in intervals:
        result = _step(plant, interval, state)
        results.append(result)
        state = result.state
    return results


def _step(plant: BiogasPlant, interval: PlantInterval, state: PlantState) -> PlantResult:
    wet, flow, dilution = _flows(plant, interval)
    days = interval.duration_h / 24
    vs_fed = destroyed = vs_out = methane = 0.0
    degradable, inert = [], []
    for i, (feed, mass) in enumerate(zip(plant.feedstocks, wet, strict=True)):
        vs_rate = mass * feed.total_solids_fraction * feed.volatile_solids_fraction_ts
        vs_fed += vs_rate * days
        rate = feed.decay_rate_per_day + dilution
        end, removed = _pool(
            state.degradable_vs_kg[i], vs_rate * feed.biodegradable_vs_fraction, rate, days
        )
        reacted = removed * feed.decay_rate_per_day / rate if rate else 0.0
        inert_end, inert_out = _pool(
            state.inert_vs_kg[i], vs_rate * (1 - feed.biodegradable_vs_fraction), dilution, days
        )
        degradable.append(end)
        inert.append(inert_end)
        destroyed += reacted
        vs_out += (removed * dilution / rate if rate else 0.0) + inert_out
        methane += reacted * feed.methane_yield_nm3_per_kg_vs_destroyed
    produced = methane / plant.methane_fraction
    captured = produced * plant.capture_fraction
    available = state.stored_biogas_nm3 + captured
    lhv = plant.methane_fraction * plant.methane_lhv_kwh_per_nm3
    rating = plant.generator.rated_power_kw
    assert rating is not None  # enforced by BiogasPlant
    target = (
        rating
        * interval.generator_setpoint_fraction
        * interval.generator_availability
        * interval.duration_h
        / plant.generator.electrical_efficiency
        / lhv
    )
    used = min(available, target)
    stored = min(plant.gas_storage_capacity_nm3, max(0.0, available - used))
    flared = max(0.0, available - used - stored)
    wet_mass = fsum(wet) * days
    digester = plant.digester
    feed_heat = (
        wet_mass
        * digester.feed_heat_capacity_kj_per_kg_k
        * max(0.0, digester.temperature_c - interval.feed_temperature_c)
        / 3600
    )
    vessel_heat = (
        digester.heat_loss_kw_per_k
        * max(0.0, digester.temperature_c - interval.ambient_temperature_c)
        * interval.duration_h
    )
    auxiliary = AuxiliaryLoads(
        fixed_power_kw=(
            plant.fixed_auxiliary_power_kw
            + plant.mixing_power_w_per_m3 * digester.working_volume_m3 / 1000
        ),
        process_electricity_kwh=(
            wet_mass / 1000 * plant.feed_preparation_kwh_per_tonne
            + captured * plant.gas_treatment_kwh_per_nm3
        ),
        electric_heater_efficiency=plant.electric_heater_efficiency,
    )
    power = generate_power(
        used * lhv,
        plant.generator,
        duration_h=interval.duration_h,
        process_heat_kwh=feed_heat + vessel_heat,
        auxiliaries=auxiliary,
    )
    site_demand = interval.site_electricity_demand_kw * interval.duration_h
    grid_net = power.net_electricity_kwh - site_demand
    heat_demand = interval.site_heat_demand_kw * interval.duration_h
    useful_heat = min(power.surplus_heat_kwh, heat_demand)
    hrt = 1 / dilution if dilution > 0 else None
    olr = vs_fed / days / digester.working_volume_m3
    flags = []
    if (
        hrt is not None
        and digester.minimum_hrt_days is not None
        and hrt < digester.minimum_hrt_days
    ):
        flags.append("hrt_below_configured_minimum")
    if digester.maximum_olr_kg_vs_m3_day is not None and olr > digester.maximum_olr_kg_vs_m3_day:
        flags.append("olr_above_configured_maximum")
    new_state = PlantState(state.feedstock_names, tuple(degradable), tuple(inert), stored)
    metrics = {
        "wet_feed_kg": wet_mass,
        "influent_volume_m3": flow * days,
        "hydraulic_retention_days": hrt,
        "organic_loading_kg_vs_m3_day": olr,
        "volatile_solids_fed_kg": vs_fed,
        "volatile_solids_destroyed_kg": destroyed,
        "effluent_volatile_solids_kg": vs_out,
        "vs_balance_residual_kg": (
            fsum(state.degradable_vs_kg + state.inert_vs_kg)
            + vs_fed
            - destroyed
            - vs_out
            - fsum(degradable + inert)
        ),
        "methane_produced_nm3": methane,
        "methane_not_captured_nm3": methane * (1 - plant.capture_fraction),
        "biogas_produced_nm3": produced,
        "biogas_captured_nm3": captured,
        "biogas_to_chp_nm3": used,
        "biogas_flared_nm3": flared,
        "initial_stored_biogas_nm3": state.stored_biogas_nm3,
        "stored_biogas_nm3": stored,
        "gas_balance_residual_nm3": available - used - stored - flared,
        "feed_heating_kwh": feed_heat,
        "vessel_heat_loss_kwh": vessel_heat,
        "site_electricity_demand_kwh": site_demand,
        "grid_import_kwh": max(0.0, -grid_net),
        "grid_export_kwh": max(0.0, grid_net),
        "site_heat_demand_kwh": heat_demand,
        "heat_delivered_to_site_kwh": useful_heat,
        "unserved_site_heat_kwh": heat_demand - useful_heat,
        "rejected_heat_kwh": power.surplus_heat_kwh - useful_heat,
    }
    for key, value in metrics.items():
        if value is not None:
            number(key, value, minimum=float("-inf"))
    return PlantResult(power, new_state, metrics, tuple(flags))
