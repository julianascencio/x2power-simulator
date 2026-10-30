"""Run with: python -m analysis.tenerife_banana.run --plot"""

import argparse
import sys
from pathlib import Path

from x2power import __version__
from x2power.utilities.io import write_csv, write_json

from .case import INPUTS, load_case, sensitivities, simulate_case


def _format_metric(value: float | None, digits: int = 3) -> str:
    return "undefined" if value is None else f"{value:.{digits}f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=INPUTS)
    parser.add_argument("--output-dir", type=Path, default=Path("results/tenerife_banana"))
    parser.add_argument("--plot", action="store_true", help="Requires the plots extra")
    args = parser.parse_args()
    config = load_case(args.inputs)
    result = simulate_case(config)
    sensitivity = sensitivities(config, result)
    output = args.output_dir
    write_json(
        {
            **{k: v for k, v in result.items() if k != "daily_results"},
            "x2power_version": __version__,
            "python_version": sys.version.split()[0],
            "reproduce": "python -m analysis.tenerife_banana.run --plot",
        },
        output / "summary.json",
    )
    write_csv(result["daily_results"], output / "daily_energy.csv")
    write_csv(result["cost_benefit"]["cash_flows"], output / "cash_flows.csv")
    write_csv(sensitivity["bmp_realization"], output / "bmp_sensitivity.csv")
    write_csv(sensitivity["electricity_value_gate_fee"], output / "value_fee_sensitivity.csv")
    if args.plot:
        from x2power.utilities.plotting import save_figure

        from .plots import (
            cash_flow_figure,
            cost_figure,
            energy_figure,
            operation_figure,
            sensitivity_figure,
        )

        figures = {
            "energy_balance": energy_figure(result),
            "operating_year": operation_figure(result),
            "annual_cost_benefit": cost_figure(result),
            "cash_flow": cash_flow_figure(result),
            "sensitivity": sensitivity_figure(sensitivity),
        }
        for name, figure in figures.items():
            for suffix in ("png", "svg"):
                save_figure(figure, output / f"{name}.{suffix}")
    metrics, finance = result["metrics"], result["cost_benefit"]
    print(f"Net electricity: {metrics['annual_net_electricity_kwh'] / 1000:.2f} MWh/year")
    print(f"Deliveries: {metrics['annual_delivered_electricity_kwh'] / 1000:.2f} MWh/year")
    print(f"Imports: {metrics['annual_imported_electricity_kwh'] / 1000:.2f} MWh/year")
    print(f"NPV: EUR {finance['net_present_value']:,.0f}")
    print(f"Benefit/cost ratio: {_format_metric(finance['benefit_cost_ratio'])}")
    print(f"Gross LCOE: EUR {_format_metric(finance['levelized_cost_per_kwh'])}/kWh")
    fee = _format_metric(metrics["break_even_total_gate_fee_eur_per_tonne"], 2)
    print(f"Break-even gate fee: EUR {fee}/t")
    payback = finance["simple_payback_years"]
    print(f"Payback: {'not reached within horizon' if payback is None else payback}")
    print(f"Outputs: {output}")


if __name__ == "__main__":
    main()
