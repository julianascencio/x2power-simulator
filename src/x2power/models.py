"""Immutable inputs and interval-integrated outputs with units in field names."""

from dataclasses import asdict, dataclass, field, fields
from typing import Any

from x2power.utilities.validation import fraction, number


@dataclass(frozen=True)
class SolidFeedstock:
    """Mass over one interval. Moisture is wet-basis; LHV is per kg dry matter."""

    mass_kg: float
    moisture_fraction: float
    dry_lhv_mj_per_kg: float

    def __post_init__(self) -> None:
        number("mass_kg", self.mass_kg)
        fraction("moisture_fraction", self.moisture_fraction)
        number("dry_lhv_mj_per_kg", self.dry_lhv_mj_per_kg, strict=True)

    @property
    def dry_mass_kg(self) -> float:
        return self.mass_kg * (1 - self.moisture_fraction)

    @property
    def water_mass_kg(self) -> float:
        return self.mass_kg * self.moisture_fraction

    @property
    def chemical_energy_kwh(self) -> float:
        return self.dry_mass_kg * self.dry_lhv_mj_per_kg / 3.6


@dataclass(frozen=True)
class Generator:
    """Constant LHV-basis efficiencies; rating is gross electrical power."""

    electrical_efficiency: float
    heat_recovery_efficiency: float = 0.0
    rated_power_kw: float | None = None

    def __post_init__(self) -> None:
        fraction("electrical_efficiency", self.electrical_efficiency, positive=True)
        fraction("heat_recovery_efficiency", self.heat_recovery_efficiency)
        if self.electrical_efficiency + self.heat_recovery_efficiency > 1.0:
            raise ValueError("Electrical and recovered-heat efficiencies must sum to <= 1")
        if self.rated_power_kw is not None:
            number("rated_power_kw", self.rated_power_kw)


@dataclass(frozen=True)
class AuxiliaryLoads:
    """Standing load applies throughout the interval, including generator outages."""

    fixed_power_kw: float = 0.0
    electricity_fraction_of_gross: float = 0.0
    process_electricity_kwh: float = 0.0
    electric_heater_efficiency: float = 1.0
    process_heat_usable_fraction: float = 1.0

    def __post_init__(self) -> None:
        number("fixed_power_kw", self.fixed_power_kw)
        fraction("electricity_fraction_of_gross", self.electricity_fraction_of_gross)
        number("process_electricity_kwh", self.process_electricity_kwh)
        fraction("electric_heater_efficiency", self.electric_heater_efficiency, positive=True)
        fraction("process_heat_usable_fraction", self.process_heat_usable_fraction)


@dataclass(frozen=True)
class PowerResult:
    """Energy ledger at the generator boundary, plus explicit plant electrical loads."""

    duration_h: float
    fuel_energy_available_kwh: float
    fuel_energy_used_kwh: float
    unused_fuel_energy_kwh: float
    gross_electricity_kwh: float
    recovered_heat_kwh: float
    generator_loss_kwh: float
    process_heat_demand_kwh: float
    heat_to_process_kwh: float
    surplus_heat_kwh: float
    electric_heating_kwh: float
    auxiliary_electricity_kwh: float
    net_electricity_kwh: float
    balance_residual_kwh: float

    def __post_init__(self) -> None:
        for item in fields(self):
            number(item.name, getattr(self, item.name), minimum=float("-inf"))
        number("duration_h", self.duration_h, strict=True)
        number("net_power_kw", self.net_power_kw, minimum=float("-inf"))
        if self.net_electrical_efficiency is not None:
            number(
                "net_electrical_efficiency", self.net_electrical_efficiency, minimum=float("-inf")
            )

    @property
    def net_power_kw(self) -> float:
        return self.net_electricity_kwh / self.duration_h

    @property
    def net_electrical_efficiency(self) -> float | None:
        """Net electricity / available fuel energy; undefined for zero fuel."""
        if self.fuel_energy_available_kwh == 0:
            return None
        return self.net_electricity_kwh / self.fuel_energy_available_kwh


@dataclass(frozen=True)
class SimulationResult:
    route: str
    power: PowerResult
    metrics: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for key, value in self.metrics.items():
            number(key, value, minimum=float("-inf"))

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["power"]["net_power_kw"] = self.power.net_power_kw
        result["power"]["net_electrical_efficiency"] = self.power.net_electrical_efficiency
        return result
