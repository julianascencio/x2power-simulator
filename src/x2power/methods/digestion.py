"""Steady-state methane yields from volatile solids and removed COD."""

from dataclasses import dataclass

from x2power.methods.biogas import BiogasStream, simulate_biogas
from x2power.models import AuxiliaryLoads, Generator, SimulationResult, SolidFeedstock
from x2power.utilities.validation import fraction, number


@dataclass(frozen=True)
class DigestionProcess:
    """Methane yield is per kg VS destroyed, NOT per kg VS fed."""

    volatile_solids_fraction_dry: float
    vs_destruction_fraction: float
    methane_yield_nm3_per_kg_vs_destroyed: float
    methane_fraction: float = 0.6
    capture_fraction: float = 0.98
    methane_lhv_kwh_per_nm3: float = 9.94
    process_heat_kwh_per_kg_wet: float = 0.0

    def __post_init__(self) -> None:
        fraction("volatile_solids_fraction_dry", self.volatile_solids_fraction_dry)
        fraction("vs_destruction_fraction", self.vs_destruction_fraction)
        number("methane_yield", self.methane_yield_nm3_per_kg_vs_destroyed)
        fraction("methane_fraction", self.methane_fraction, positive=True)
        fraction("capture_fraction", self.capture_fraction)
        number("methane_lhv_kwh_per_nm3", self.methane_lhv_kwh_per_nm3, strict=True)
        number("process_heat_kwh_per_kg_wet", self.process_heat_kwh_per_kg_wet)


def simulate_digestion(
    feedstock: SolidFeedstock,
    process: DigestionProcess,
    generator: Generator,
    *,
    duration_h: float = 1.0,
    availability: float = 1.0,
    auxiliaries: AuxiliaryLoads | None = None,
) -> SimulationResult:
    vs = feedstock.dry_mass_kg * process.volatile_solids_fraction_dry
    destroyed = vs * process.vs_destruction_fraction
    methane = destroyed * process.methane_yield_nm3_per_kg_vs_destroyed
    methane_energy = methane * process.methane_lhv_kwh_per_nm3
    if methane_energy > feedstock.chemical_energy_kwh + 1e-9:
        raise ValueError("Methane energy exceeds feedstock LHV: check yield basis and dry LHV")
    stream = BiogasStream(
        methane / process.methane_fraction,
        process.methane_fraction,
        process.methane_lhv_kwh_per_nm3,
        process.capture_fraction,
    )
    result = simulate_biogas(
        stream,
        generator,
        duration_h=duration_h,
        availability=availability,
        process_heat_kwh=feedstock.mass_kg * process.process_heat_kwh_per_kg_wet,
        auxiliaries=auxiliaries,
    )
    return SimulationResult(
        "digestion",
        result.power,
        {
            **result.metrics,
            "wet_feed_kg": feedstock.mass_kg,
            "dry_feed_kg": feedstock.dry_mass_kg,
            "volatile_solids_fed_kg": vs,
            "volatile_solids_destroyed_kg": destroyed,
            "feedstock_chemical_energy_kwh": feedstock.chemical_energy_kwh,
        },
    )


@dataclass(frozen=True)
class WastewaterStream:
    volume_m3: float
    cod_kg_per_m3: float

    def __post_init__(self) -> None:
        number("volume_m3", self.volume_m3)
        number("cod_kg_per_m3", self.cod_kg_per_m3)


@dataclass(frozen=True)
class CODProcess:
    """Empirical methane yield per kg COD removed; no biological kinetics implied."""

    cod_removal_fraction: float
    methane_yield_nm3_per_kg_cod_removed: float
    methane_fraction: float = 0.6
    capture_fraction: float = 0.98
    methane_lhv_kwh_per_nm3: float = 9.94
    process_heat_kwh_per_m3: float = 0.0

    def __post_init__(self) -> None:
        fraction("cod_removal_fraction", self.cod_removal_fraction)
        number("methane_yield", self.methane_yield_nm3_per_kg_cod_removed)
        # 1 mol CH4 consumes 2 mol O2: 22.414 L / 64 g O2 at the declared normal state.
        if self.methane_yield_nm3_per_kg_cod_removed > 22.414 / 64:
            raise ValueError("Methane yield exceeds the COD stoichiometric ceiling at 0 C")
        fraction("methane_fraction", self.methane_fraction, positive=True)
        fraction("capture_fraction", self.capture_fraction)
        number("methane_lhv_kwh_per_nm3", self.methane_lhv_kwh_per_nm3, strict=True)
        number("process_heat_kwh_per_m3", self.process_heat_kwh_per_m3)


def simulate_wastewater(
    stream: WastewaterStream,
    process: CODProcess,
    generator: Generator,
    *,
    duration_h: float = 1.0,
    availability: float = 1.0,
    auxiliaries: AuxiliaryLoads | None = None,
) -> SimulationResult:
    cod = stream.volume_m3 * stream.cod_kg_per_m3
    removed = cod * process.cod_removal_fraction
    methane = removed * process.methane_yield_nm3_per_kg_cod_removed
    gas = BiogasStream(
        methane / process.methane_fraction,
        process.methane_fraction,
        process.methane_lhv_kwh_per_nm3,
        process.capture_fraction,
    )
    result = simulate_biogas(
        gas,
        generator,
        duration_h=duration_h,
        availability=availability,
        process_heat_kwh=stream.volume_m3 * process.process_heat_kwh_per_m3,
        auxiliaries=auxiliaries,
    )
    return SimulationResult(
        "wastewater",
        result.power,
        {
            **result.metrics,
            "wastewater_m3": stream.volume_m3,
            "cod_fed_kg": cod,
            "cod_removed_kg": removed,
            "cod_remaining_kg": cod - removed,
        },
    )
