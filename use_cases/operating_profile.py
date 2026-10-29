"""Variable flow, interval length and an outage; standing loads remain active."""

from pathlib import Path

from x2power.methods.profile import OperatingInterval, simulate_profile, summarize_profile
from x2power.utilities.io import load_scenario, write_json


def main() -> None:
    config = load_scenario(Path(__file__).parent / "scenarios/biogas_engine.json")
    intervals = [
        OperatingInterval(6, 0.6),
        OperatingInterval(8, 1.0),
        OperatingInterval(2, 1.0, 0.0),
        OperatingInterval(8, 1.2),
    ]
    results = simulate_profile(config, intervals)
    summary = summarize_profile(results)
    write_json(
        {"intervals": [r.to_dict() for r in results], "summary": summary},
        "results/operating_profile.json",
    )
    print(summary)


if __name__ == "__main__":
    main()
