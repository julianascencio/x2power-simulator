import json
from copy import deepcopy

import pytest

from x2power.methods.profile import OperatingInterval, simulate_profile, summarize_profile
from x2power.scenario import run_scenario
from x2power.utilities.experiments import monte_carlo, percentile, set_parameter, sweep_parameter
from x2power.utilities.io import load_scenario, write_csv, write_json
from x2power.utilities.units import mj_to_kwh, normalize_gas_volume


def test_normalized_gas_volume_ideal_gas_and_water_correction():
    assert normalize_gas_volume(10, 0, 101325) == 10
    assert normalize_gas_volume(10, 273.15, 202650) == 10
    assert normalize_gas_volume(10, 0, 101325, water_vapour_pressure_pa=10132.5) == 9
    assert mj_to_kwh(3.6) == 1
    with pytest.raises(ValueError):
        normalize_gas_volume(1, -273.15, 101325)
    with pytest.raises(ValueError):
        normalize_gas_volume(1, 0, 101325, water_vapour_pressure_pa=101325)


def test_profile_interval_partition_invariance(biogas_config):
    whole = run_scenario(biogas_config)
    profile = simulate_profile(
        biogas_config,
        [OperatingInterval(7, availability=0.95), OperatingInterval(17, availability=0.95)],
    )
    total = summarize_profile(profile)
    assert total["net_electricity_kwh"] == pytest.approx(whole.power.net_electricity_kwh)
    assert total["mean_net_power_kw"] == pytest.approx(whole.power.net_power_kw)


def test_outage_preserves_auxiliary_and_heat_demands(biogas_config):
    result = simulate_profile(biogas_config, [OperatingInterval(2, availability=0)])[0]
    assert result.power.gross_electricity_kwh == 0
    assert result.power.net_electricity_kwh < 0
    assert result.power.unused_fuel_energy_kwh > 0


def test_sweep_does_not_modify_input(biogas_config):
    original = deepcopy(biogas_config)
    rows = sweep_parameter(biogas_config, "generator.electrical_efficiency", [0.2, 0.3, 0.4])
    assert rows[0]["net_electricity_kwh"] < rows[2]["net_electricity_kwh"]
    assert biogas_config == original


def test_monte_carlo_reproducible_and_quantiles(biogas_config):
    bounds = {"generator.electrical_efficiency": (0.25, 0.4)}
    first = monte_carlo(biogas_config, bounds, samples=30, seed=42)
    assert first == monte_carlo(biogas_config, bounds, samples=30, seed=42)
    assert first != monte_carlo(biogas_config, bounds, samples=30, seed=43)
    summary = first["net_electricity_kwh"]
    assert summary["p05"] <= summary["p50"] <= summary["p95"]
    assert percentile([0, 10], 0.25) == 2.5


@pytest.mark.parametrize("path", ["unknown.x", "name", "schema_version"])
def test_invalid_parameter_paths(biogas_config, path):
    with pytest.raises(ValueError):
        set_parameter(biogas_config, path, 0.5)


def test_experiment_errors(biogas_config):
    for bounds, samples in [({}, 1), ({"availability": (1, 0)}, 1), ({"availability": (0, 1)}, 0)]:
        with pytest.raises(ValueError):
            monte_carlo(biogas_config, bounds, samples=samples)
    with pytest.raises(ValueError, match="sample 0"):
        monte_carlo(biogas_config, {"availability": (2, 2)}, samples=1)
    with pytest.raises(ValueError):
        monte_carlo(biogas_config, {"availability": (0, 1)}, seed=True)
    with pytest.raises(ValueError):
        sweep_parameter(biogas_config, "availability", [])
    with pytest.raises(ValueError):
        percentile([], 0.5)
    with pytest.raises(ValueError):
        simulate_profile(biogas_config, [])
    with pytest.raises(ValueError):
        summarize_profile([])


def test_json_csv_roundtrips_and_rejections(tmp_path, biogas_config):
    path = tmp_path / "nested/case.json"
    write_json(biogas_config, path)
    assert load_scenario(path) == biogas_config
    write_csv([{"x": 1, "y": 2}], tmp_path / "rows.csv")
    assert (tmp_path / "rows.csv").read_text().splitlines() == ["x,y", "1,2"]
    path.write_text(json.dumps([1, 2]))
    with pytest.raises(ValueError):
        load_scenario(path)
    with pytest.raises(ValueError):
        write_csv([], tmp_path / "empty.csv")
    with pytest.raises(ValueError):
        write_csv([{"x": 1}, {"y": 2}], tmp_path / "bad.csv")
