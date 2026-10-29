import json
import subprocess
import sys
from pathlib import Path

import pytest

from x2power.cli import main
from x2power.scenario import run_scenario
from x2power.utilities.io import load_scenario

ROOT = Path(__file__).parents[1]
CASES = sorted((ROOT / "use_cases/scenarios").glob("*.json"))


@pytest.mark.parametrize("path", CASES, ids=lambda p: p.stem)
def test_all_bundled_scenarios_balance(path):
    result = run_scenario(load_scenario(path))
    assert abs(result.power.balance_residual_kwh) < 1e-8
    assert result.power.net_electricity_kwh <= result.power.gross_electricity_kwh
    assert result.to_dict()["route"] == result.route


def test_cli_run_compare_and_errors(tmp_path, capsys):
    assert main(["run", str(CASES[0])]) == 0
    assert json.loads(capsys.readouterr().out)["power"]["duration_h"] == 24
    output = tmp_path / "run.json"
    assert main(["run", str(CASES[0]), "-o", str(output)]) == 0
    assert output.exists()
    assert main(["compare", str(CASES[0]), str(CASES[1])]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 2
    assert main(["compare", str(CASES[0]), "--csv", str(tmp_path / "out.csv")]) == 0
    assert main(["run", str(tmp_path / "missing.json")]) == 2
    assert "x2power:" in capsys.readouterr().err


@pytest.mark.parametrize(
    "name", ["compare_routes", "moisture_sweep", "operating_profile", "uncertainty"]
)
def test_examples_run_from_other_working_directory(tmp_path, name):
    completed = subprocess.run(
        [sys.executable, str(ROOT / f"use_cases/{name}.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert list((tmp_path / "results").iterdir())


def test_module_entrypoint():
    output = subprocess.check_output([sys.executable, "-m", "x2power", "--version"], text=True)
    assert output.strip() == "0.1.0"
