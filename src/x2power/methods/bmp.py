"""Screen laboratory biochemical methane potential on a VS-fed basis.

Unlike DigestionProcess, this interface does not require or infer VS destruction.
The realization fraction is an explicit scale-up assumption, not a kinetic model.
"""

from dataclasses import dataclass

from x2power.methods.biogas import BiogasStream, simulate_biogas
from x2power.models import AuxiliaryLoads, Generator, SimulationResult, SolidFeedstock
from x2power.utilities.validation import fraction, number


@dataclass(frozen=True)
class BMPProcess:
    """Dry normal methane potential per kg VS FED, before collection losses.

    Potential is a laboratory value at 0 C and 101325 Pa. Realization scales the
    potential before methane capture and CHP availability are applied separately.
    No transient digestion, nutrient adequacy or mono-digestion stability is solved.
    """

    volatile_solids_fraction_dry: float
    methane_potential_nm3_per_kg_vs_fed: float
    realization_fraction: float
    methane_fraction: float = 0.6
    capture_fraction: float = 0.98
    methane_lhv_kwh_per_nm3: float = 9.94

    def __post_init__(self) -> None:
        fraction("volatile_solids_fraction_dry", self.volatile_solids_fraction_dry)
        number("methane_potential", self.methane_potential_nm3_per_kg_vs_fed)
        fraction("realization_fraction", self.realization_fraction)
        fraction("methane_fraction", self.methane_fraction, positive=True)
        fraction("capture_fraction", self.capture_fraction)
        number("methane_lhv", self.methane_lhv_kwh_per_nm3, strict=True)


def simulate_bmp_digestion(
    feedstock: SolidFeedstock,
    process: BMPProcess,
    generator: Generator,
    *,
    duration_h: float = 1.0,
    availability: float = 1.0,
    process_heat_kwh: float = 0.0,
    auxiliaries: AuxiliaryLoads | None = None,
) -> SimulationResult:
    """Map feed and realized BMP to electricity; feed is an interval total.

    Digestion is represented as an established steady process without inventories.
    The upstream methane supply is uniform even during a CHP outage. Unused fuel
    is reported, with no implicit storage, flaring or emissions treatment.
    """
    vs = feedstock.dry_mass_kg * process.volatile_solids_fraction_dry
    potential = vs * process.methane_potential_nm3_per_kg_vs_fed
    if potential * process.methane_lhv_kwh_per_nm3 > feedstock.chemical_energy_kwh + 1e-9:
        raise ValueError("Laboratory methane potential exceeds dry feedstock LHV")
    methane = potential * process.realization_fraction
    result = simulate_biogas(
        BiogasStream(
            methane / process.methane_fraction,
            process.methane_fraction,
            process.methane_lhv_kwh_per_nm3,
            process.capture_fraction,
        ),
        generator,
        duration_h=duration_h,
        availability=availability,
        process_heat_kwh=process_heat_kwh,
        auxiliaries=auxiliaries,
    )
    return SimulationResult(
        "bmp_digestion",
        result.power,
        {
            **result.metrics,
            "wet_feed_kg": feedstock.mass_kg,
            "dry_feed_kg": feedstock.dry_mass_kg,
            "volatile_solids_fed_kg": vs,
            "laboratory_methane_potential_nm3": potential,
            "feedstock_chemical_energy_kwh": feedstock.chemical_energy_kwh,
        },
    )
