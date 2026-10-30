"""Plastic-to-electricity example with reproducible energy balances and sweeps.

Run from any working directory after installing X2Power. Add --plot to save figures.
All parameters are synthetic; the selected pyrolysis products are a lumped fuel.
"""

import argparse
from pathlib import Path

from x2power import __version__
from x2power.scenario import run_scenario
from x2power.utilities.experiments import sweep_parameter
from x2power.utilities.io import load_scenario, write_csv, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("results/plastic_to_power"))
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()
    scenario = load_scenario(Path(__file__).parent / "scenarios" / "plastic_pyrolysis.json")
    result = run_scenario(scenario)
    recovery = sweep_parameter(
        scenario, "process.fuel_energy_recovery", [i / 10 for i in range(1, 10)]
    )
    throughput = sweep_parameter(
        scenario, "feedstock.mass_kg", [0, 500, 1000, 2000, 4000, 6000, 8000, 10000]
    )
    wet_tonnes = scenario["feedstock"]["mass_kg"] / 1000
    indicators = {
        "net_electricity_kwh_per_tonne_wet_feed": result.power.net_electricity_kwh / wet_tonnes,
        "net_electricity_per_dry_feed_lhv": (
            result.power.net_electricity_kwh / result.metrics["feedstock_chemical_energy_kwh"]
        ),
    }
    write_json(
        {
            "report_schema_version": 1,
            "simulator_version": __version__,
            "note": "Synthetic inputs; uncalibrated lumped pyrolysis-to-electricity model.",
            "scenario": scenario,
            "baseline": result.to_dict(),
            "indicators": indicators,
            "sweeps": {
                "fuel_energy_recovery": {
                    "parameter": "process.fuel_energy_recovery",
                    "rows": recovery,
                },
                "throughput": {"parameter": "feedstock.mass_kg", "rows": throughput},
            },
        },
        args.output_dir / "simulation.json",
    )
    write_csv(recovery, args.output_dir / "recovery_sweep.csv")
    write_csv(throughput, args.output_dir / "throughput_sweep.csv")
    if args.plot:
        from x2power.utilities.plotting import plot_energy_balance, plot_sensitivity, save_figure

        figures = {
            "energy_balance": plot_energy_balance(
                result, title="Synthetic plastic pyrolysis: 2 tonnes over 24 hours"
            ),
            "recovery_sweep": plot_sensitivity(
                recovery,
                xlabel="Fraction of dry-feed LHV recovered in selected fuel products",
                title="Plastic-to-power: fuel recovery sensitivity",
            ),
            "throughput_sweep": plot_sensitivity(
                [{**row, "input_value": row["input_value"] / 1000} for row in throughput],
                xlabel="Wet feed (tonnes over 24 hours)",
                title="Plastic-to-power: throughput with a 500 kW generator",
            ),
        }
        for name, figure in figures.items():
            save_figure(figure, args.output_dir / f"{name}.png")
            save_figure(figure, args.output_dir / f"{name}.svg")
            figure.clear()
    print(f"Gross electricity: {result.power.gross_electricity_kwh:,.1f} kWh / 24 h")
    print(f"Process heater electricity: {result.power.electric_heating_kwh:,.1f} kWh / 24 h")
    print(f"Auxiliary electricity: {result.power.auxiliary_electricity_kwh:,.1f} kWh / 24 h")
    print(f"Net electricity: {result.power.net_electricity_kwh:,.1f} kWh / 24 h")
    print(f"Average net power: {result.power.net_power_kw:,.1f} kW")
    specific_net = indicators["net_electricity_kwh_per_tonne_wet_feed"]
    print(f"Net electricity per wet tonne: {specific_net:,.1f} kWh/t")
    print(f"Outputs: {args.output_dir}")


if __name__ == "__main__":
    main()
