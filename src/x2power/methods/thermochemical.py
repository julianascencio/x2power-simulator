"""Lumped conversion models; no reaction equilibrium or product-composition prediction."""

from dataclasses import dataclass
from typing import Literal

from x2power.methods.generation import generate_power
from x2power.models import AuxiliaryLoads, Generator, SimulationResult, SolidFeedstock
from x2power.utilities.validation import fraction, number


@dataclass(frozen=True)
class ThermalProcess:
    """Recovery is fraction of dry LHV reaching the downstream power block.

    Combustion: boiler-to-power-block energy fraction. Gasification: selected fuel-gas
    energy fraction. Pyrolysis: combined energy of selected fuel products. Fractions
    are gross before explicitly declared process heat and must not already include it.
    All feed moisture is evaporated. Drying duty must include sensible and latent heat.
    """

    route: Literal["combustion", "gasification", "pyrolysis"]
    fuel_energy_recovery: float
    evaporation_heat_kwh_per_kg_water: float
    process_heat_kwh_per_kg_dry: float = 0.0

    def __post_init__(self) -> None:
        if self.route not in {"combustion", "gasification", "pyrolysis"}:
            raise ValueError("Unsupported thermal route")
        fraction("fuel_energy_recovery", self.fuel_energy_recovery)
        number("evaporation_heat_kwh_per_kg_water", self.evaporation_heat_kwh_per_kg_water)
        number("process_heat_kwh_per_kg_dry", self.process_heat_kwh_per_kg_dry)


def simulate_thermal(
    feedstock: SolidFeedstock,
    process: ThermalProcess,
    generator: Generator,
    *,
    duration_h: float = 1.0,
    availability: float = 1.0,
    auxiliaries: AuxiliaryLoads | None = None,
) -> SimulationResult:
    source = feedstock.chemical_energy_kwh
    fuel = source * process.fuel_energy_recovery
    evaporation = feedstock.water_mass_kg * process.evaporation_heat_kwh_per_kg_water
    process_heat = feedstock.dry_mass_kg * process.process_heat_kwh_per_kg_dry
    power = generate_power(
        fuel,
        generator,
        duration_h=duration_h,
        availability=availability,
        process_heat_kwh=evaporation + process_heat,
        auxiliaries=auxiliaries,
    )
    return SimulationResult(
        process.route,
        power,
        {
            "wet_feed_kg": feedstock.mass_kg,
            "dry_feed_kg": feedstock.dry_mass_kg,
            "evaporated_water_kg": feedstock.water_mass_kg,
            "feedstock_chemical_energy_kwh": source,
            "unrecovered_feedstock_energy_kwh": source - fuel,
            "evaporation_heat_kwh": evaporation,
            "reaction_and_sensible_heat_kwh": process_heat,
        },
    )
