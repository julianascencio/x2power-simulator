"""Run generic biogas-plant scenarios with an outage and a feed interruption.

Usage: python use_cases/biogas_plant.py --plant agroindustrial_chp --days 30
Optional figures: add --plot after installing the plots extra.
"""

import argparse
from dataclasses import asdict
from pathlib import Path

from x2power.methods.biogas_plant import PlantInterval, initial_plant_state, simulate_biogas_plant
from x2power.utilities.biogas_plant import plant_from_config, plant_profile_rows, summarize_plant
from x2power.utilities.io import load_scenario, write_csv, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plant",
        choices=("agroindustrial_chp", "dairy_manure_chp", "swine_slurry_chp"),
        default="agroindustrial_chp",
    )
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output-dir", type=Path, default=Path("results/biogas_plant"))
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days must be at least 1")
    config = load_scenario(Path(__file__).parent / "plants" / f"{args.plant}.json")
    plant = plant_from_config(config)
    rating = plant.generator.rated_power_kw
    assert rating is not None
    schedule = [
        PlantInterval(
            feed_multipliers=(0.0 if 240 <= hour < 288 else 1.0,) * len(plant.feedstocks),
            generator_availability=0.0 if 120 <= hour < 132 else 1.0,
            ambient_temperature_c=10,
            feed_temperature_c=12,
            site_electricity_demand_kw=rating * 0.15,
            site_heat_demand_kw=rating * 0.3,
        )
        for hour in range(args.days * 24)
    ]
    initial = initial_plant_state(plant, interval=schedule[0])
    results = simulate_biogas_plant(plant, schedule, initial_state=initial)
    summary = summarize_plant(results)
    destination = args.output_dir / args.plant
    write_json(
        {
            "configuration": config,
            "initial_state": asdict(initial),
            "schedule": [asdict(point) for point in schedule],
            "summary": summary,
            "results": [result.to_dict() for result in results],
        },
        destination / "simulation.json",
    )
    write_csv(plant_profile_rows(results), destination / "profile.csv")
    if args.plot:
        from x2power.utilities.plant_plotting import plot_biogas_plant
        from x2power.utilities.plotting import save_figure

        figure = plot_biogas_plant(results, title=f"Synthetic {args.plant}: {args.days} days")
        save_figure(figure, destination / "profile.png")
    print(f"{args.plant}: {summary['net_electricity_kwh'] / 1000:.2f} MWh net electricity")
    print(
        f"Grid export/import: {summary['grid_export_kwh'] / 1000:.2f} / "
        f"{summary['grid_import_kwh'] / 1000:.2f} MWh"
    )
    print(f"Flared biogas: {summary['biogas_flared_nm3']:.1f} Nm3")
    print(f"Outputs: {destination}")


if __name__ == "__main__":
    main()
