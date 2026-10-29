"""Run all bundled cases; outputs are technical metrics, not an equal-feed ranking."""

from pathlib import Path

from x2power.scenario import run_scenario
from x2power.utilities.io import load_scenario, write_csv


def main() -> None:
    rows = []
    for path in sorted((Path(__file__).parent / "scenarios").glob("*.json")):
        result = run_scenario(load_scenario(path))
        row = {
            "scenario": path.stem,
            "duration_h": result.power.duration_h,
            "gross_kwh": result.power.gross_electricity_kwh,
            "net_kwh": result.power.net_electricity_kwh,
            "mean_net_kw": result.power.net_power_kw,
            "electric_heating_kwh": result.power.electric_heating_kwh,
            "unused_fuel_kwh": result.power.unused_fuel_energy_kwh,
        }
        rows.append(row)
        print(f"{path.stem:24s} {result.power.net_electricity_kwh:10.2f} net kWh")
    write_csv(rows, "results/route_comparison.csv")


if __name__ == "__main__":
    main()
