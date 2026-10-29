"""Portable JSON/CSV I/O without third-party runtime dependencies."""

import csv
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def load_scenario(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Scenario JSON root must be an object")
    return data


def write_json(data: object, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(rows: Sequence[Mapping[str, Any]], path: str | Path) -> None:
    if not rows:
        raise ValueError("Cannot write an empty CSV table")
    keys = list(rows[0])
    if any(set(row) != set(keys) for row in rows):
        raise ValueError("CSV rows must have identical fields")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
