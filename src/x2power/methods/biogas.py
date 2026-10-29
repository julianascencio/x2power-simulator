"""Methane-fraction model for an already available, dry biogas stream."""

from dataclasses import dataclass

from x2power.methods.generation import generate_power
from x2power.models import AuxiliaryLoads, Generator, SimulationResult
from x2power.utilities.validation import fraction, number


@dataclass(frozen=True)
class BiogasStream:
    """Nm³ means dry gas at 0 °C and 101325 Pa; all volumes must share this basis."""

    volume_nm3: float
    methane_fraction: float
    methane_lhv_kwh_per_nm3: float = 9.94
    capture_fraction: float = 1.0

    def __post_init__(self) -> None:
        number("volume_nm3", self.volume_nm3)
        fraction("methane_fraction", self.methane_fraction, positive=True)
        number("methane_lhv_kwh_per_nm3", self.methane_lhv_kwh_per_nm3, strict=True)
        fraction("capture_fraction", self.capture_fraction)


def simulate_biogas(
    stream: BiogasStream,
    generator: Generator,
    *,
    duration_h: float = 1.0,
    availability: float = 1.0,
    process_heat_kwh: float = 0.0,
    auxiliaries: AuxiliaryLoads | None = None,
) -> SimulationResult:
    methane = stream.volume_nm3 * stream.methane_fraction
    captured = methane * stream.capture_fraction
    power = generate_power(
        captured * stream.methane_lhv_kwh_per_nm3,
        generator,
        duration_h=duration_h,
        availability=availability,
        process_heat_kwh=process_heat_kwh,
        auxiliaries=auxiliaries,
    )
    return SimulationResult(
        "biogas",
        power,
        {
            "raw_biogas_nm3": stream.volume_nm3,
            "methane_produced_nm3": methane,
            "methane_captured_nm3": captured,
            "methane_not_captured_nm3": methane - captured,
        },
    )
