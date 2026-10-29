"""Constant-efficiency conversion, capacity limitation and heat/electricity accounting."""

from x2power.models import AuxiliaryLoads, Generator, PowerResult
from x2power.utilities.validation import fraction, number


def generate_power(
    fuel_energy_kwh: float,
    generator: Generator,
    *,
    duration_h: float = 1.0,
    availability: float = 1.0,
    process_heat_kwh: float = 0.0,
    auxiliaries: AuxiliaryLoads | None = None,
) -> PowerResult:
    """Convert uniformly supplied fuel; do not shift fuel between online/offline hours.

    Available recovered heat serves process demand first. The remaining heat demand
    uses an electric resistance heater; its input is deducted from net electricity.
    Negative net output means required external electrical supply. Unused fuel is
    reported explicitly; no fuel store or flaring destination is assumed.
    """
    number("fuel_energy_kwh", fuel_energy_kwh)
    number("duration_h", duration_h, strict=True)
    fraction("availability", availability)
    number("process_heat_kwh", process_heat_kwh)
    aux = auxiliaries or AuxiliaryLoads()
    used = fuel_energy_kwh * availability
    if generator.rated_power_kw is not None:
        capacity_fuel = (
            generator.rated_power_kw * duration_h * availability / generator.electrical_efficiency
        )
        used = min(used, capacity_fuel)
    gross = used * generator.electrical_efficiency
    recovered = used * generator.heat_recovery_efficiency
    loss = used * max(0.0, 1 - generator.electrical_efficiency - generator.heat_recovery_efficiency)
    heat_to_process = min(recovered * aux.process_heat_usable_fraction, process_heat_kwh)
    heater = (process_heat_kwh - heat_to_process) / aux.electric_heater_efficiency
    electrical_aux = (
        aux.fixed_power_kw * duration_h
        + aux.electricity_fraction_of_gross * gross
        + aux.process_electricity_kwh
    )
    unused = fuel_energy_kwh - used
    return PowerResult(
        duration_h=duration_h,
        fuel_energy_available_kwh=fuel_energy_kwh,
        fuel_energy_used_kwh=used,
        unused_fuel_energy_kwh=unused,
        gross_electricity_kwh=gross,
        recovered_heat_kwh=recovered,
        generator_loss_kwh=loss,
        process_heat_demand_kwh=process_heat_kwh,
        heat_to_process_kwh=heat_to_process,
        surplus_heat_kwh=recovered - heat_to_process,
        electric_heating_kwh=heater,
        auxiliary_electricity_kwh=electrical_aux,
        net_electricity_kwh=gross - electrical_aux - heater,
        balance_residual_kwh=fuel_energy_kwh - (gross + recovered + loss + unused),
    )
