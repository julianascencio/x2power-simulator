"""Versioned JSON configuration adapter. Unknown keys fail rather than being ignored."""

from collections.abc import Mapping
from typing import Any, TypeVar

from x2power.methods import (
    BiogasStream,
    CODProcess,
    DigestionProcess,
    ThermalProcess,
    WastewaterStream,
    simulate_biogas,
    simulate_digestion,
    simulate_thermal,
    simulate_wastewater,
)
from x2power.models import AuxiliaryLoads, Generator, SimulationResult, SolidFeedstock

T = TypeVar("T")


def _build(cls: type[T], raw: object, label: str) -> T:
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object")
    try:
        return cls(**raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: {exc}") from exc


def run_scenario(config: Mapping[str, Any]) -> SimulationResult:
    allowed = {
        "schema_version",
        "name",
        "description",
        "route",
        "duration_h",
        "availability",
        "feedstock",
        "process",
        "generator",
        "auxiliaries",
    }
    unknown = set(config) - allowed
    if unknown:
        raise ValueError(f"Unknown scenario fields: {sorted(unknown)}")
    if type(config.get("schema_version")) is not int or config["schema_version"] != 1:
        raise ValueError("schema_version must be integer 1")
    route = config.get("route")
    if route not in (
        "combustion",
        "gasification",
        "pyrolysis",
        "digestion",
        "wastewater",
        "biogas",
    ):
        raise ValueError(f"Unsupported route: {route!r}")
    generator = _build(Generator, config.get("generator"), "generator")
    aux = _build(AuxiliaryLoads, config.get("auxiliaries", {}), "auxiliaries")
    duration = config.get("duration_h", 1.0)
    availability = config.get("availability", 1.0)
    if route in ("combustion", "gasification", "pyrolysis"):
        feed = _build(SolidFeedstock, config.get("feedstock"), "feedstock")
        parameters = config.get("process")
        if not isinstance(parameters, dict):
            raise ValueError("process must be an object")
        if "route" in parameters:
            raise ValueError("Specify route only at scenario root")
        thermal = _build(ThermalProcess, {"route": route, **parameters}, "process")
        return simulate_thermal(
            feed,
            thermal,
            generator,
            duration_h=duration,
            availability=availability,
            auxiliaries=aux,
        )
    if route == "digestion":
        feed = _build(SolidFeedstock, config.get("feedstock"), "feedstock")
        digestion = _build(DigestionProcess, config.get("process"), "process")
        return simulate_digestion(
            feed,
            digestion,
            generator,
            duration_h=duration,
            availability=availability,
            auxiliaries=aux,
        )
    if route == "wastewater":
        water = _build(WastewaterStream, config.get("feedstock"), "feedstock")
        cod = _build(CODProcess, config.get("process"), "process")
        return simulate_wastewater(
            water,
            cod,
            generator,
            duration_h=duration,
            availability=availability,
            auxiliaries=aux,
        )
    gas = _build(BiogasStream, config.get("feedstock"), "feedstock")
    parameters = config.get("process", {})
    if not isinstance(parameters, dict) or set(parameters) - {"process_heat_kwh"}:
        raise ValueError("biogas process accepts only process_heat_kwh")
    return simulate_biogas(
        gas,
        generator,
        duration_h=duration,
        availability=availability,
        process_heat_kwh=parameters.get("process_heat_kwh", 0.0),
        auxiliaries=aux,
    )
