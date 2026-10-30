"""BMP-fed basis, independent heat/electricity arithmetic and physical limits."""

import pytest

from x2power import AuxiliaryLoads, Generator, SolidFeedstock
from x2power.methods.bmp import BMPProcess, simulate_bmp_digestion


def test_bmp_fed_basis_and_separate_losses():
    # 1000 wet kg -> 100 dry kg -> 80 VS kg -> 32 Nm3 potential -> 16 realized.
    result = simulate_bmp_digestion(
        SolidFeedstock(1000, 0.9, 20),
        BMPProcess(0.8, 0.4, 0.5, capture_fraction=0.9, methane_lhv_kwh_per_nm3=10),
        Generator(0.3, 0.4),
        duration_h=24,
        availability=0.5,
        process_heat_kwh=40,
        auxiliaries=AuxiliaryLoads(fixed_power_kw=1, electric_heater_efficiency=0.8),
    )
    assert result.metrics["laboratory_methane_potential_nm3"] == pytest.approx(32)
    assert result.metrics["methane_produced_nm3"] == pytest.approx(16)
    assert result.metrics["methane_captured_nm3"] == pytest.approx(14.4)
    assert result.power.gross_electricity_kwh == pytest.approx(21.6)
    assert result.power.electric_heating_kwh == pytest.approx((40 - 28.8) / 0.8)
    assert result.power.net_electricity_kwh == pytest.approx(21.6 - 24 - 14)
    assert result.power.unused_fuel_energy_kwh == pytest.approx(72)
    assert result.power.balance_residual_kwh == pytest.approx(0)
    assert "volatile_solids_destroyed_kg" not in result.metrics


def test_bmp_zero_feed_outage_and_capacity():
    process = BMPProcess(0.8, 0.4, 0.7)
    zero = simulate_bmp_digestion(SolidFeedstock(0, 0.9, 20), process, Generator(0.3))
    assert zero.power.net_electricity_kwh == 0
    out = simulate_bmp_digestion(
        SolidFeedstock(1000, 0.9, 20),
        process,
        Generator(0.3, rated_power_kw=1),
        duration_h=1,
        process_heat_kwh=5,
        availability=0,
    )
    assert out.power.gross_electricity_kwh == 0
    assert out.power.net_electricity_kwh == -5
    cap = simulate_bmp_digestion(
        SolidFeedstock(1000, 0.9, 20), process, Generator(0.3, rated_power_kw=1), duration_h=1
    )
    assert cap.power.gross_electricity_kwh == 1
    assert cap.power.unused_fuel_energy_kwh > 0


def test_impossible_potential_rejected_even_with_low_realization():
    with pytest.raises(ValueError, match="exceeds"):
        simulate_bmp_digestion(SolidFeedstock(1000, 0.5, 1), BMPProcess(1, 1, 0.01), Generator(0.3))
    with pytest.raises(ValueError):
        BMPProcess(0.8, 0.4, 1.1)
