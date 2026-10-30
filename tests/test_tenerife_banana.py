"""Independent case arithmetic, sensitivity closure and offline reproducibility."""

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from analysis.tenerife_banana.case import load_case, outage_days, sensitivities, simulate_case

ROOT = Path(__file__).resolve().parents[1]


def test_committed_reference_results_match_fresh_run():
    reference = json.loads(
        (ROOT / "analysis/tenerife_banana/reference_results/summary.json").read_text()
    )
    current = simulate_case(load_case())
    assert reference["inputs_sha256"] == current["inputs_sha256"]
    assert reference["inputs"] == current["inputs"]
    assert reference["metrics"] == pytest.approx(current["metrics"])
    assert reference["annual_power_totals"] == pytest.approx(current["annual_power_totals"])
    for old, new in zip(
        reference["cost_benefit"]["cash_flows"],
        current["cost_benefit"]["cash_flows"],
        strict=True,
    ):
        assert old == pytest.approx(new)


def test_case_independent_energy_and_discounted_arithmetic():
    config = load_case()
    original = deepcopy(config)
    result = simulate_case(config)
    methane = 5_000_000 * 0.062 * 0.678 * 0.36329 * 0.7
    gross = methane * 0.98 * 9.94 * 0.3 * 335 / 365
    heat = 5_000_000 * 4.18 * 17 / 3600 + 0.15 * 17 * 8760
    heater = heat * 30 / 365 / 0.98
    standing = (0.5 + 3 * 600 / 1000) * 8760 + 5 * 5000
    auxiliary = standing + 0.05 * gross
    imports = standing * 30 / 365 + heater
    delivered = gross - standing * 335 / 365 - 0.05 * gross
    net = gross - auxiliary - heater
    metrics = result["metrics"]
    assert metrics["annual_methane_produced_nm3"] == pytest.approx(methane)
    assert metrics["annual_net_electricity_kwh"] == pytest.approx(net)
    assert metrics["annual_imported_electricity_kwh"] == pytest.approx(imports)
    assert metrics["annual_delivered_electricity_kwh"] == pytest.approx(delivered)
    assert delivered - imports == pytest.approx(net)
    assert metrics["hydraulic_retention_days"] == pytest.approx(43.8)
    assert metrics["maximum_absolute_generator_balance_residual_kwh"] < 1e-8
    annual_cost = 25000 + 19500 + 6500 + 40000 + 18000 + 30000 + imports * 0.18
    annual_benefit = delivered * 0.07
    annuity = (1 - 1.08**-20) / 0.08
    expected_npv = (
        -650000 + (annual_benefit - annual_cost) * annuity - 40000 / 1.08**10 - 30000 / 1.08**20
    )
    assert result["cost_benefit"]["net_present_value"] == pytest.approx(expected_npv)
    assert result["cost_benefit"]["simple_payback_years"] is None
    assert result["cost_benefit"]["cash_flows"][10]["costs"] == pytest.approx(annual_cost + 40000)
    assert result["cost_benefit"]["cash_flows"][20]["costs"] == pytest.approx(annual_cost + 30000)
    assert config == original
    assert result == simulate_case(config)


def test_break_even_prices_close_npv_and_sensitivity_matches_rerun():
    config = load_case()
    result = simulate_case(config)
    for field, metric in [
        ("export_price_eur_per_kwh", "break_even_delivered_electricity_eur_per_kwh"),
        ("gate_fee_eur_per_tonne", "break_even_total_gate_fee_eur_per_tonne"),
    ]:
        changed = deepcopy(config)
        changed["assumptions"][field] = result["metrics"][metric]
        assert simulate_case(changed)["cost_benefit"]["net_present_value"] == pytest.approx(
            0, abs=1e-8
        )
    table = sensitivities(config, result)
    for row in (table["electricity_value_gate_fee"][0], table["electricity_value_gate_fee"][-1]):
        changed = deepcopy(config)
        changed["assumptions"]["export_price_eur_per_kwh"] = row[
            "delivered_electricity_value_eur_per_kwh"
        ]
        changed["assumptions"]["gate_fee_eur_per_tonne"] = row["gate_fee_eur_per_tonne"]
        actual = simulate_case(changed)["cost_benefit"]["net_present_value"]
        assert row["net_present_value_eur"] == pytest.approx(actual)
    assert (
        table["bmp_realization"][0]["net_electricity_kwh"]
        < table["bmp_realization"][-1]["net_electricity_kwh"]
    )


def test_full_outage_has_no_electricity_sales_or_lcoe():
    config = load_case()
    config["assumptions"]["chp_outage_day_ranges"] = [[1, 365]]
    result = simulate_case(config)
    assert result["metrics"]["annual_delivered_electricity_kwh"] == 0
    assert result["metrics"]["annual_imported_electricity_kwh"] > 0
    assert result["cost_benefit"]["levelized_cost_per_kwh"] is None
    assert result["metrics"]["break_even_delivered_electricity_eur_per_kwh"] is None


@pytest.mark.parametrize(
    "ranges", [None, [[0, 1]], [[1, 366]], [[2, 1]], [[1, True]], [[1]], [[1, 2], [2, 3]]]
)
def test_invalid_outage_ranges(ranges):
    with pytest.raises(ValueError):
        outage_days(ranges)


@pytest.mark.parametrize(
    "key,value",
    [
        ("horizon_years", 1.5),
        ("replacement_year", 30),
        ("feed_tonnes_per_year", 0),
        ("feed_temperature_c", -274),
        ("bmp_realization_fraction", 1.1),
        ("gate_fee_eur_per_tonne", -1),
    ],
)
def test_invalid_assumptions(key, value):
    config = load_case()
    config["assumptions"][key] = value
    with pytest.raises(ValueError):
        simulate_case(config)


def test_invalid_costs_and_schema(tmp_path):
    config = load_case()
    config["annual_fixed_costs_eur"]["transport"] = 1
    with pytest.raises(ValueError, match="collide"):
        simulate_case(config)
    config["annual_fixed_costs_eur"] = {}
    with pytest.raises(ValueError):
        simulate_case(config)
    for value in [True, 2, None]:
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"schema_version": value}))
        with pytest.raises(ValueError):
            load_case(path)


def test_runner_exports_offline_from_arbitrary_directory(tmp_path):
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT), str(ROOT / "src")])}
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "analysis.tenerife_banana.run",
            "--output-dir",
            str(tmp_path / "output"),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "NPV: EUR" in completed.stdout
    summary = json.loads((tmp_path / "output/summary.json").read_text())
    assert summary["inputs_sha256"] == simulate_case(load_case())["inputs_sha256"]
    assert len((tmp_path / "output/daily_energy.csv").read_text().splitlines()) == 366
    assert len((tmp_path / "output/cash_flows.csv").read_text().splitlines()) == 22
    assert len((tmp_path / "output/value_fee_sensitivity.csv").read_text().splitlines()) == 144
