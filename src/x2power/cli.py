"""Command-line scenario execution and comparison."""

import argparse
import json
import sys
from pathlib import Path

from x2power import __version__
from x2power.scenario import run_scenario
from x2power.utilities.io import load_scenario, write_csv, write_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Technical feedstock-to-electricity simulation")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Run one JSON scenario")
    run.add_argument("scenario", type=Path)
    run.add_argument("-o", "--output", type=Path)
    compare = commands.add_parser(
        "compare", help="Compare scenarios with declared interval lengths"
    )
    compare.add_argument("scenarios", type=Path, nargs="+")
    compare.add_argument("--csv", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            result = run_scenario(load_scenario(args.scenario)).to_dict()
            if args.output:
                write_json(result, args.output)
            else:
                print(json.dumps(result, indent=2, allow_nan=False))
        else:
            rows = []
            for path in args.scenarios:
                config = load_scenario(path)
                result = run_scenario(config)
                rows.append(
                    {
                        "scenario": config.get("name", path.stem),
                        "route": result.route,
                        "duration_h": result.power.duration_h,
                        "gross_kwh": result.power.gross_electricity_kwh,
                        "net_kwh": result.power.net_electricity_kwh,
                        "net_kw": result.power.net_power_kw,
                    }
                )
            if args.csv:
                write_csv(rows, args.csv)
            else:
                print(json.dumps(rows, indent=2, allow_nan=False))
    except (ValueError, OSError, TypeError) as exc:
        print(f"x2power: {exc}", file=sys.stderr)
        return 2
    return 0
