"""Reproduce technical figures and their numerical inputs with synthetic scenarios."""

import argparse
from dataclasses import asdict
from pathlib import Path

from x2power import __version__
from x2power.methods.profile import OperatingInterval, simulate_profile, summarize_profile
from x2power.scenario import run_scenario
from x2power.utilities.experiments import monte_carlo, sweep_parameter
from x2power.utilities.io import load_scenario, write_csv, write_json
from x2power.utilities.plotting import (
    plot_energy_balance,
    plot_profile,
    plot_sensitivity,
    plot_uncertainty,
    save_figure,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("results/visual_report"))
    args = parser.parse_args()
    destination = args.output_dir
    scenarios = Path(__file__).parent / "scenarios"
    configurations = {
        name: load_scenario(scenarios / f"{name}.json")
        for name in ("biomass_gasification", "biogas_engine", "food_waste_digestion")
    }
    baseline = run_scenario(configurations["biomass_gasification"])
    moisture = [i / 20 for i in range(19)]
    sensitivity = sweep_parameter(
        configurations["biomass_gasification"], "feedstock.moisture_fraction", moisture
    )
    intervals = [
        OperatingInterval(6, 0.6),
        OperatingInterval(8, 1.0),
        OperatingInterval(2, 1.0, 0.0),
        OperatingInterval(8, 1.2),
    ]
    profile = simulate_profile(configurations["biogas_engine"], intervals)
    bounds = {
        "process.vs_destruction_fraction": (0.45, 0.65),
        "process.methane_yield_nm3_per_kg_vs_destroyed": (0.4, 0.55),
        "generator.electrical_efficiency": (0.30, 0.38),
    }
    uncertainty = monte_carlo(configurations["food_waste_digestion"], bounds, samples=1000, seed=42)
    figures = {
        "energy_balance": plot_energy_balance(
            baseline, title="Synthetic gasification: electricity and process heat"
        ),
        "moisture_sensitivity": plot_sensitivity(
            sensitivity,
            xlabel="Wet-basis moisture fraction",
            title="Synthetic gasification: moisture at constant wet feed mass",
        ),
        "operating_profile": plot_profile(
            profile, title="Synthetic biogas profile: outage from hour 14 to 16"
        ),
        "uncertainty": plot_uncertainty(
            [draw["net_kwh"] for draw in uncertainty["draws"]],
            title="Synthetic digestion: independent uniform input sampling",
        ),
    }
    for name, figure in figures.items():
        for extension in ("png", "svg"):
            save_figure(figure, destination / f"{name}.{extension}")
        figure.clear()
    write_csv(sensitivity, destination / "moisture_sensitivity.csv")
    profile_rows = []
    start = 0.0
    for result in profile:
        end = start + result.power.duration_h
        profile_rows.append(
            {
                "start_h": start,
                "end_h": end,
                "gross_power_kw": result.power.gross_electricity_kwh / result.power.duration_h,
                "net_power_kw": result.power.net_power_kw,
                "process_heat_kw": result.power.process_heat_demand_kwh / result.power.duration_h,
            }
        )
        start = end
    write_csv(profile_rows, destination / "operating_profile.csv")
    write_json(
        {
            "report_schema_version": 1,
            "simulator_version": __version__,
            "note": "Synthetic inputs; uncalibrated reduced-order simulation.",
            "configurations": configurations,
            "experiments": {
                "moisture_values": moisture,
                "intervals": [asdict(interval) for interval in intervals],
                "uniform_bounds": bounds,
                "samples": 1000,
                "seed": 42,
            },
            "baseline": baseline.to_dict(),
            "sensitivity": sensitivity,
            "profile": [result.to_dict() for result in profile],
            "profile_summary": summarize_profile(profile),
            "uncertainty": uncertainty,
        },
        destination / "results.json",
    )
    print(f"Saved four figures (PNG + SVG), two CSV tables and results.json to {destination}")


if __name__ == "__main__":
    main()
