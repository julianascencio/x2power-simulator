"""Explicit physical methods for conversion pathways and electricity generation."""

from .biogas import BiogasStream, simulate_biogas
from .bmp import BMPProcess, simulate_bmp_digestion
from .cost_benefit import (
    AnnualCashFlow,
    CostBenefitResult,
    break_even_unit_value,
    evaluate_cost_benefit,
    net_present_value,
    payback_period,
    value_electricity,
)
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
    "AnnualCashFlow",
    "BMPProcess",
    "BiogasStream",
    "CODProcess",
    "CostBenefitResult",
    "DigestionProcess",
    "ThermalProcess",
    "WastewaterStream",
    "break_even_unit_value",
    "evaluate_cost_benefit",
    "generate_power",
    "net_present_value",
    "payback_period",
    "simulate_biogas",
    "simulate_bmp_digestion",
    "simulate_digestion",
    "simulate_thermal",
    "simulate_wastewater",
    "value_electricity",
]
