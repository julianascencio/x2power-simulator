"""Vary wet-basis moisture at constant wet feed mass, including evaporation duty."""

from pathlib import Path

from x2power.utilities.experiments import sweep_parameter
from x2power.utilities.io import load_scenario, write_csv


def main() -> None:
    config = load_scenario(Path(__file__).parent / "scenarios/biomass_gasification.json")
    rows = sweep_parameter(config, "feedstock.moisture_fraction", [i / 10 for i in range(9)])
    write_csv(rows, "results/moisture_sweep.csv")
    for row in rows:
        print(f"moisture={row['input_value']:.0%}: net={row['net_electricity_kwh']:.2f} kWh")


if __name__ == "__main__":
    main()
