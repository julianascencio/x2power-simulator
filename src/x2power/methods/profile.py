"""Quasi-steady interval profiles. No reactor kinetics, inventory or startup state."""

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any

from x2power.models import SimulationResult
from x2power.scenario import run_scenario
from x2power.utilities.validation import fraction, number


@dataclass(frozen=True)
class OperatingInterval:
    duration_h: float
    feed_rate_multiplier: float = 1.0
    availability: float = 1.0

    def __post_init__(self) -> None:
        number("duration_h", self.duration_h, strict=True)
        number("feed_rate_multiplier", self.feed_rate_multiplier)
        fraction("availability", self.availability)


def simulate_profile(
    base_scenario: Mapping[str, Any],
    intervals: Sequence[OperatingInterval],
) -> list[SimulationResult]:
    """Scale interval feed amounts from base scenario's flow (amount / duration).

    Fixed process electricity and biogas process heat scale with elapsed time;
    feed-dependent heat is recomputed by each route. A point's availability replaces
    the base scenario's availability. Every point is independent.
    """
    run_scenario(base_scenario)
    if not intervals:
        raise ValueError("Supply at least one interval")
    base_duration = base_scenario.get("duration_h", 1.0)
    route = base_scenario["route"]
    amount_key = {"biogas": "volume_nm3", "wastewater": "volume_m3"}.get(route, "mass_kg")
    results = []
    for point in intervals:
        config = deepcopy(dict(base_scenario))
        ratio = point.duration_h / base_duration
        config["feedstock"][amount_key] *= ratio * point.feed_rate_multiplier
        config["duration_h"] = point.duration_h
        config["availability"] = point.availability
        if "process_electricity_kwh" in config.get("auxiliaries", {}):
            config["auxiliaries"]["process_electricity_kwh"] *= ratio
        if route == "biogas" and "process_heat_kwh" in config.get("process", {}):
            config["process"]["process_heat_kwh"] *= ratio
        results.append(run_scenario(config))
    return results


def summarize_profile(results: Sequence[SimulationResult]) -> dict[str, float]:
    if not results:
        raise ValueError("Cannot summarize an empty profile")
    fields = asdict(results[0].power)
    totals = {key: sum(getattr(r.power, key) for r in results) for key in fields}
    totals["mean_net_power_kw"] = totals["net_electricity_kwh"] / totals["duration_h"]
    totals["peak_net_power_kw"] = max(r.power.net_power_kw for r in results)
    return totals
