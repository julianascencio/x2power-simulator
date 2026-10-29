"""
Moisture at constant wet feed mass
==================================

More moisture reduces dry-feed chemical energy and increases evaporation demand.
The model retains negative net output when electrical loads exceed generation.
Recovery and conversion efficiencies remain fixed across this synthetic sweep.
"""

from x2power.utilities.experiments import sweep_parameter
from x2power.utilities.plotting import plot_sensitivity

# %%
# Feed mass is a total over the 24-hour interval, not a mass-flow rate.
# High-temperature process heat is supplied electrically in this example.
scenario = {
    "schema_version": 1,
    "route": "gasification",
    "duration_h": 24,
    "availability": 0.95,
    "feedstock": {"mass_kg": 4000, "moisture_fraction": 0.2, "dry_lhv_mj_per_kg": 18},
    "process": {
        "fuel_energy_recovery": 0.65,
        "evaporation_heat_kwh_per_kg_water": 0.75,
        "process_heat_kwh_per_kg_dry": 0.15,
    },
    "generator": {"electrical_efficiency": 0.35, "heat_recovery_efficiency": 0.4},
    "auxiliaries": {
        "fixed_power_kw": 3,
        "electricity_fraction_of_gross": 0.04,
        "process_electricity_kwh": 20,
        "electric_heater_efficiency": 0.95,
        "process_heat_usable_fraction": 0,
    },
}
rows = sweep_parameter(scenario, "feedstock.moisture_fraction", [i / 20 for i in range(19)])

# %%
# The zero crossing follows the assumed yields and heat duties; it does not
# establish the operating limits or stability of a real reactor.
figure = plot_sensitivity(
    rows,
    xlabel="Wet-basis moisture fraction",
    title="Synthetic gasification: fixed wet feed mass",
)
