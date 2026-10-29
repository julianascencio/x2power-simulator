"""Verify plot data, signed energy, time axes, optional imports and rendered files."""

import builtins
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from x2power.cli import main
from x2power.methods import generate_power
from x2power.models import AuxiliaryLoads, Generator, SimulationResult
from x2power.scenario import run_scenario
from x2power.utilities.plotting import (
    plot_energy_balance,
    plot_profile,
    plot_sensitivity,
    plot_uncertainty,
    save_figure,
)

ROOT = Path(__file__).parents[1]


def test_energy_waterfall_and_heat_use_different_energy_bases():
    result = SimulationResult(
        "biogas",
        generate_power(
            1000,
            Generator(0.35, 0.4),
            duration_h=2,
            process_heat_kwh=500,
            auxiliaries=AuxiliaryLoads(10, 0.05, 5, electric_heater_efficiency=0.5),
        ),
    )
    figure = plot_energy_balance(result)
    electricity, heat = figure.axes
    assert [bar.get_height() for bar in electricity.patches] == [350, -42.5, -200, 107.5]
    assert [bar.get_y() for bar in electricity.patches] == [0, 350, 307.5, 0]
    assert electricity.get_ylim()[1] > 350
    # 200 kWh electrical input delivers only 100 kWh thermal at 50% heater efficiency.
    assert [bar.get_width() for bar in heat.patches] == [400, 400, 0, 100]


def test_negative_net_remains_visible():
    result = SimulationResult(
        "biogas",
        generate_power(
            0,
            Generator(0.4),
            duration_h=2,
            auxiliaries=AuxiliaryLoads(fixed_power_kw=4),
        ),
    )
    figure = plot_energy_balance(result)
    assert figure.axes[0].patches[-1].get_height() == -8
    assert figure.axes[0].get_ylim()[0] < -8


def test_profile_preserves_unequal_interval_widths_and_energy():
    results = [
        SimulationResult(
            "biogas",
            generate_power(
                1000,
                Generator(0.4),
                duration_h=1,
                availability=0,
                auxiliaries=AuxiliaryLoads(fixed_power_kw=5),
            ),
        ),
        SimulationResult("biogas", generate_power(1000, Generator(0.4), duration_h=3)),
    ]
    figure = plot_profile(results)
    data = figure.axes[0].patches[1].get_data()
    assert list(data.edges) == [0, 1, 4]
    assert list(data.values) == pytest.approx([-5, 400 / 3])
    integrated = sum(
        value * (end - start)
        for value, start, end in zip(data.values, data.edges[:-1], data.edges[1:], strict=True)
    )
    assert integrated == pytest.approx(395)


def test_sensitivity_sorts_without_mutation_and_retains_negative_results():
    rows = [
        {"input_value": 0.8, "gross_electricity_kwh": 20, "net_electricity_kwh": -10},
        {"input_value": 0.2, "gross_electricity_kwh": 80, "net_electricity_kwh": 60},
    ]
    original = deepcopy(rows)
    figure = plot_sensitivity(rows)
    assert list(figure.axes[0].lines[0].get_xdata()) == [0.2, 0.8]
    assert list(figure.axes[0].lines[1].get_ydata()) == [60, -10]
    assert rows == original


def test_uncertainty_quantiles_and_histogram_counts():
    figure = plot_uncertainty([-10, 0, 10], bins=3)
    axis = figure.axes[0]
    assert sum(bar.get_height() for bar in axis.patches) == 3
    assert [line.get_xdata()[0] for line in axis.lines[:3]] == [-9, 0, 9]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: plot_sensitivity([]),
        lambda: plot_sensitivity([{"input_value": 1}]),
        lambda: plot_sensitivity(
            [{"input_value": 1, "gross_electricity_kwh": 1, "net_electricity_kwh": 0}] * 2
        ),
        lambda: plot_profile([]),
        lambda: plot_uncertainty([]),
        lambda: plot_uncertainty([float("nan")]),
        lambda: plot_uncertainty([1], bins=True),
        lambda: plot_uncertainty([1], bins=0),
    ],
)
def test_invalid_plot_inputs_fail(factory):
    with pytest.raises(ValueError):
        factory()


@pytest.mark.parametrize(
    "extension,signature",
    [
        ("png", b"\x89PNG"),
        ("svg", b"<?xml"),
        ("pdf", b"%PDF"),
    ],
)
def test_save_figure_writes_valid_format(tmp_path, extension, signature):
    figure = plot_uncertainty([1, 2, 3])
    path = save_figure(figure, tmp_path / f"nested/chart.{extension}")
    assert path.read_bytes().startswith(signature)
    assert path.stat().st_size > 1000
    with pytest.raises(ValueError, match="output"):
        save_figure(figure, tmp_path / "chart.html")
    with pytest.raises(ValueError, match="dpi"):
        save_figure(figure, tmp_path / "chart.png", dpi=0)


def test_missing_matplotlib_does_not_disable_simulation(monkeypatch, biogas_config, capsys):
    original_import = builtins.__import__

    def block_matplotlib(name, *args, **kwargs):
        if name.startswith("matplotlib"):
            raise ImportError("Matplotlib intentionally absent")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block_matplotlib)
    result = run_scenario(biogas_config)
    assert result.power.net_electricity_kwh > 0
    with pytest.raises(ImportError, match=r"\[plots\]"):
        plot_energy_balance(result)
    assert (
        main(["plot", str(ROOT / "use_cases/scenarios/biogas_engine.json"), "-o", "unused.png"])
        == 2
    )
    assert "requires Matplotlib" in capsys.readouterr().err


def test_cli_plot(tmp_path):
    scenario = ROOT / "use_cases/scenarios/biomass_gasification.json"
    output = tmp_path / "chart.svg"
    assert main(["plot", str(scenario), "-o", str(output)]) == 0
    assert "<svg" in output.read_text()
    assert main(["plot", str(scenario), "-o", str(tmp_path / "bad.html")]) == 2


def test_visual_example_reproduces_numerical_results(tmp_path):
    destination = tmp_path / "report"
    command = [
        sys.executable,
        str(ROOT / "use_cases/visual_report.py"),
        "--output-dir",
        str(destination),
    ]
    first = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, check=False)
    assert first.returncode == 0, first.stderr
    first_data = (destination / "results.json").read_bytes()
    result = json.loads(first_data)
    assert len(list(destination.glob("*.png"))) == 4
    assert len(list(destination.glob("*.svg"))) == 4
    assert len(list(destination.glob("*.csv"))) == 2
    assert len(result["uncertainty"]["draws"]) == 1000
    assert result["sensitivity"][-1]["net_electricity_kwh"] < 0
    assert result["profile"][2]["power"]["net_electricity_kwh"] < 0
    assert (
        result["baseline"]
        == run_scenario(result["configurations"]["biomass_gasification"]).to_dict()
    )
    second = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, check=False)
    assert second.returncode == 0, second.stderr
    assert (destination / "results.json").read_bytes() == first_data
