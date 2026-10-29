"""Repeatable uncertainty experiment; ranges are synthetic and independent."""

from pathlib import Path

from x2power.utilities.experiments import monte_carlo
from x2power.utilities.io import load_scenario, write_json


def main() -> None:
    config = load_scenario(Path(__file__).parent / "scenarios/food_waste_digestion.json")
    result = monte_carlo(
        config,
        {
            "process.vs_destruction_fraction": (0.45, 0.65),
            "process.methane_yield_nm3_per_kg_vs_destroyed": (0.4, 0.55),
            "generator.electrical_efficiency": (0.30, 0.38),
        },
        samples=1000,
        seed=42,
    )
    write_json(result, "results/uncertainty.json")
    print(result["net_electricity_kwh"])


if __name__ == "__main__":
    main()
