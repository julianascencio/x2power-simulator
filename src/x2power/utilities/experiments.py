"""One-variable sweeps and independently sampled uniform-input uncertainty experiments."""

from collections.abc import Mapping, Sequence
from copy import deepcopy
from math import floor, isfinite
from random import Random
from typing import Any

from x2power.scenario import run_scenario
from x2power.utilities.validation import number


def set_parameter(config: dict[str, Any], path: str, value: float) -> None:
    """Set an existing numeric leaf using a dotted path; never create silent typos."""
    parts = path.split(".")
    target = config
    for part in parts[:-1]:
        nested = target.get(part)
        if not isinstance(nested, dict):
            raise ValueError(f"Unknown parameter path: {path}")
        target = nested
    old = target.get(parts[-1])
    if isinstance(old, bool) or not isinstance(old, (int, float)) or path == "schema_version":
        raise ValueError(f"Parameter is not an existing numeric input: {path}")
    number(path, value, minimum=float("-inf"))
    target[parts[-1]] = value


def sweep_parameter(
    scenario: Mapping[str, Any],
    path: str,
    values: Sequence[float],
) -> list[dict[str, float]]:
    if not values:
        raise ValueError("Supply at least one sweep value")
    rows = []
    for value in values:
        config = deepcopy(dict(scenario))
        set_parameter(config, path, value)
        result = run_scenario(config)
        rows.append(
            {
                "input_value": value,
                "gross_electricity_kwh": result.power.gross_electricity_kwh,
                "net_electricity_kwh": result.power.net_electricity_kwh,
                "net_power_kw": result.power.net_power_kw,
            }
        )
    return rows


def percentile(values: Sequence[float], probability: float) -> float:
    if not values or not 0 <= probability <= 1 or not all(isfinite(v) for v in values):
        raise ValueError("Percentile needs finite values and a probability in [0, 1]")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = floor(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])


def monte_carlo(
    scenario: Mapping[str, Any],
    bounds: Mapping[str, tuple[float, float]],
    *,
    samples: int = 1000,
    seed: int = 0,
) -> dict[str, Any]:
    """Sample uniform independent bounds. Invalid physical samples fail loudly.

    Returned quantiles describe the chosen input assumptions, not calibrated confidence.
    Draws and net outputs are retained for reproducibility and inspection.
    """
    if type(samples) is not int or samples <= 0:
        raise ValueError("samples must be a positive integer")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if not bounds:
        raise ValueError("Supply at least one uncertain input")
    for path, (low, high) in bounds.items():
        number(path, low, minimum=float("-inf"))
        number(path, high, minimum=float("-inf"))
        if low > high:
            raise ValueError(f"Reversed bounds for {path}")
    rng = Random(seed)
    rows: list[dict[str, Any]] = []
    for index in range(samples):
        config = deepcopy(dict(scenario))
        draw = {key: rng.uniform(*bounds[key]) for key in sorted(bounds)}
        for path, value in draw.items():
            set_parameter(config, path, value)
        try:
            result = run_scenario(config)
        except ValueError as exc:
            raise ValueError(f"Invalid Monte Carlo sample {index}: {exc}") from exc
        rows.append({"sample": index, "inputs": draw, "net_kwh": result.power.net_electricity_kwh})
    values = [row["net_kwh"] for row in rows]
    return {
        "seed": seed,
        "samples": samples,
        "net_electricity_kwh": {
            "p05": percentile(values, 0.05),
            "p50": percentile(values, 0.5),
            "p95": percentile(values, 0.95),
            "mean": sum(values) / samples,
        },
        "draws": rows,
    }
