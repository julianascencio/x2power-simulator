"""Independent hand calculations, conservation identities and limiting behaviour."""

from dataclasses import replace

import pytest

from x2power.methods import (
    BiogasStream,
    CODProcess,
    DigestionProcess,
    ThermalProcess,
    WastewaterStream,
    generate_power,
    simulate_biogas,
    simulate_digestion,
    simulate_thermal,
    simulate_wastewater,
)
from x2power.models import AuxiliaryLoads, Generator, SolidFeedstock


def test_hand_calculated_chp_heat_deficit():
    result = generate_power(
        1000,
        Generator(0.35, 0.4),
        duration_h=2,
        process_heat_kwh=500,
        auxiliaries=AuxiliaryLoads(10, 0.05, 5),
    )
    assert result.gross_electricity_kwh == pytest.approx(350)
    assert result.generator_loss_kwh == pytest.approx(250)
    assert result.auxiliary_electricity_kwh == pytest.approx(42.5)
    assert result.electric_heating_kwh == pytest.approx(100)
    assert result.net_electricity_kwh == pytest.approx(207.5)
    assert result.net_power_kw == pytest.approx(103.75)
    assert result.net_electrical_efficiency == pytest.approx(0.2075)


def test_heat_grade_and_heater_efficiency():
    result = generate_power(
        1000,
        Generator(0.3, 0.5),
        process_heat_kwh=400,
        auxiliaries=AuxiliaryLoads(
            electric_heater_efficiency=0.8, process_heat_usable_fraction=0.4
        ),
    )
    assert result.heat_to_process_kwh == 200
    assert result.surplus_heat_kwh == 300
    assert result.electric_heating_kwh == 250
    assert result.net_electricity_kwh == 50


@pytest.mark.parametrize("availability", [0, 0.25, 1])
@pytest.mark.parametrize("rating", [0, 50, 10000, None])
def test_generator_energy_conservation_and_capacity(availability, rating):
    result = generate_power(
        1234, Generator(0.4, 0.3, rating), duration_h=3, availability=availability
    )
    ledger = (
        result.gross_electricity_kwh
        + result.recovered_heat_kwh
        + result.generator_loss_kwh
        + result.unused_fuel_energy_kwh
    )
    assert ledger == pytest.approx(1234)
    assert abs(result.balance_residual_kwh) < 1e-9
    assert result.gross_electricity_kwh <= 1234 * 0.4 * availability + 1e-9
    if rating is not None:
        assert result.gross_electricity_kwh <= rating * 3 * availability + 1e-9


def test_capacity_and_outage_do_not_reschedule_fuel():
    result = generate_power(1000, Generator(0.4, 0.4, 100), duration_h=2, availability=0.5)
    assert result.gross_electricity_kwh == 100
    assert result.fuel_energy_used_kwh == 250
    assert result.unused_fuel_energy_kwh == 750


def test_zero_fuel_and_standing_load_allow_negative_net():
    result = generate_power(
        0, Generator(0.3), duration_h=2, auxiliaries=AuxiliaryLoads(fixed_power_kw=4)
    )
    assert result.net_electricity_kwh == -8
    assert result.net_electrical_efficiency is None


def test_thermal_hand_calculation_and_feed_mass_partition():
    feed = SolidFeedstock(100, 0.2, 18)
    result = simulate_thermal(
        feed, ThermalProcess("gasification", 0.7, 0.7, 0.2), Generator(0.3, 0.4)
    )
    assert feed.dry_mass_kg + feed.water_mass_kg == feed.mass_kg
    assert result.metrics["feedstock_chemical_energy_kwh"] == pytest.approx(400)
    assert result.metrics["unrecovered_feedstock_energy_kwh"] == pytest.approx(120)
    assert result.power.process_heat_demand_kwh == pytest.approx(30)
    assert result.power.gross_electricity_kwh == pytest.approx(84)
    assert result.power.surplus_heat_kwh == pytest.approx(82)


def test_digestion_vs_destroyed_basis_and_capture():
    result = simulate_digestion(
        SolidFeedstock(1000, 0.8, 18),
        DigestionProcess(0.8, 0.5, 0.5, capture_fraction=0.9, methane_lhv_kwh_per_nm3=10),
        Generator(0.35),
    )
    assert result.metrics["volatile_solids_fed_kg"] == pytest.approx(160)
    assert result.metrics["volatile_solids_destroyed_kg"] == pytest.approx(80)
    assert result.metrics["methane_produced_nm3"] == pytest.approx(40)
    assert result.metrics["methane_not_captured_nm3"] == pytest.approx(4)
    assert result.power.gross_electricity_kwh == pytest.approx(126)


def test_cod_stoichiometric_bound_and_hand_calculation():
    result = simulate_wastewater(
        WastewaterStream(100, 2),
        CODProcess(0.8, 0.3, capture_fraction=1, methane_lhv_kwh_per_nm3=10),
        Generator(0.4),
    )
    assert result.metrics["cod_remaining_kg"] == 40
    assert result.metrics["methane_produced_nm3"] == 48
    assert result.power.gross_electricity_kwh == pytest.approx(192)
    with pytest.raises(ValueError, match="stoichiometric"):
        CODProcess(1, 0.36)


def test_digestion_rejects_energy_creation():
    with pytest.raises(ValueError, match="exceeds feedstock"):
        simulate_digestion(SolidFeedstock(100, 0, 1), DigestionProcess(1, 1, 1), Generator(0.4))


def test_biogas_volume_basis():
    result = simulate_biogas(BiogasStream(100, 0.6, 10, 0.9), Generator(0.4))
    assert result.power.gross_electricity_kwh == 216
    assert result.metrics["methane_captured_nm3"] == 54


def test_drying_can_make_wet_thermal_conversion_net_consumer():
    process = ThermalProcess("combustion", 0.8, 0.75)
    dry = simulate_thermal(SolidFeedstock(100, 0.1, 18), process, Generator(0.3))
    wet = simulate_thermal(SolidFeedstock(100, 0.95, 18), process, Generator(0.3))
    assert dry.power.net_electricity_kwh > 0 > wet.power.net_electricity_kwh


def test_linear_feed_scaling_without_capacity_or_standing_load():
    feed = SolidFeedstock(100, 0.2, 18)
    process = ThermalProcess("pyrolysis", 0.6, 0.75, 0.2)
    first = simulate_thermal(feed, process, Generator(0.3))
    second = simulate_thermal(replace(feed, mass_kg=200), process, Generator(0.3))
    assert second.power.net_electricity_kwh == pytest.approx(2 * first.power.net_electricity_kwh)
