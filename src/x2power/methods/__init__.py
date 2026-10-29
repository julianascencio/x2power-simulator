"""Explicit physical methods for conversion pathways and electricity generation."""

from .biogas import BiogasStream, simulate_biogas
from .digestion import (
    CODProcess,
    DigestionProcess,
    WastewaterStream,
    simulate_digestion,
    simulate_wastewater,
)
from .generation import generate_power
from .thermochemical import ThermalProcess, simulate_thermal

__all__ = [
    "BiogasStream",
    "CODProcess",
    "DigestionProcess",
    "ThermalProcess",
    "WastewaterStream",
    "generate_power",
    "simulate_biogas",
    "simulate_digestion",
    "simulate_thermal",
    "simulate_wastewater",
]
