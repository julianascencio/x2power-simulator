"""Unit helpers. Gas conditions are explicit rather than inferred from a unit label."""

from x2power.utilities.validation import number


def mj_to_kwh(energy_mj: float) -> float:
    number("energy_mj", energy_mj)
    return energy_mj / 3.6


def normalize_gas_volume(
    actual_m3: float,
    temperature_c: float,
    pressure_pa: float,
    *,
    water_vapour_pressure_pa: float = 0.0,
) -> float:
    """Ideal-gas conversion to dry Nm³ at 0 °C and 101325 Pa.

    Supply ABSOLUTE pressure and the actual water-vapour partial pressure for wet gas.
    Compressibility differences are not modelled.
    """
    number("actual_m3", actual_m3)
    number("temperature_c", temperature_c, minimum=-273.15, strict=True)
    number("pressure_pa", pressure_pa, strict=True)
    number("water_vapour_pressure_pa", water_vapour_pressure_pa)
    if water_vapour_pressure_pa >= pressure_pa:
        raise ValueError("Water-vapour pressure must be lower than total absolute pressure")
    return (
        actual_m3
        * (pressure_pa - water_vapour_pressure_pa)
        / 101325
        * 273.15
        / (temperature_c + 273.15)
    )
