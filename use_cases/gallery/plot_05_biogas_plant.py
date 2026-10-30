"""
Continuous biogas plant: feed, storage and electricity
===========================================================

Follow a synthetic 1 MW CHP plant from three organic feedstocks to grid export.
The model carries volatile-solids and gas inventories between hourly intervals.
The inputs are illustrative, not measurements or a reconstruction of a real plant.
"""

from dataclasses import replace

from x2power import Generator
from x2power.methods.biogas_plant import (
    BiogasPlant,
    ContinuousDigester,
    DigesterFeedstock,
    PlantInterval,
    initial_plant_state,
    simulate_biogas_plant,
)
from x2power.utilities.biogas_plant import summarize_plant
from x2power.utilities.plant_plotting import plot_biogas_plant

# %%
# 1. Define a mixed feed of 100 tonnes per day. TS is per wet mass, VS is per
# TS, and methane yield is per VS destroyed. Each substrate has its own decay
# constant and degradable fraction; these require laboratory/operating calibration.
feedstocks = (
    DigesterFeedstock(
        "food_processing_residues", 45000, 0.22, 0.9, 0.85, 0.55, 0.12, dry_lhv_mj_per_kg=20
    ),
    DigesterFeedstock("livestock_slurry", 35000, 0.08, 0.8, 0.65, 0.45, 0.06, dry_lhv_mj_per_kg=20),
    DigesterFeedstock("organic_sludge", 20000, 0.06, 0.75, 0.65, 0.48, 0.08, dry_lhv_mj_per_kg=20),
)
plant = BiogasPlant(
    feedstocks,
    ContinuousDigester(
        3500, heat_loss_kw_per_k=0.55, minimum_hrt_days=15, maximum_olr_kg_vs_m3_day=5
    ),
    Generator(0.38, 0.45, rated_power_kw=1000),
    gas_storage_capacity_nm3=2500,
    fixed_auxiliary_power_kw=20,
    mixing_power_w_per_m3=3,
    feed_preparation_kwh_per_tonne=2,
    gas_treatment_kwh_per_nm3=0.02,
    electric_heater_efficiency=0.98,
)

# %%
# 2. Begin with steady-feed substrate inventories and an empty gas holder. Resolve
# a 12-hour CHP outage on day 6 explicitly, then stop feeds during days 11 and 12.
# The digesters stay warm: unmet digester heat uses an electric backup heater.
schedule = [
    PlantInterval(
        feed_multipliers=(0.0 if 240 <= hour < 288 else 1.0,) * 3,
        generator_availability=0.0 if 120 <= hour < 132 else 1.0,
        feed_temperature_c=12,
        ambient_temperature_c=10,
        site_electricity_demand_kw=150,
        site_heat_demand_kw=300,
    )
    for hour in range(30 * 24)
]
initial = initial_plant_state(plant, interval=schedule[0])
results = simulate_biogas_plant(plant, schedule, initial_state=initial)
first = results[0]
print(f"Initial HRT: {first.metrics['hydraulic_retention_days']:.1f} days")
print(f"Initial OLR: {first.metrics['organic_loading_kg_vs_m3_day']:.2f} kg VS/m³/day")

# %%
# 3. Read the four ledgers: captured gas/CHP/flare, electrical output, gas-holder
# inventory and heat. Gas keeps forming during the outage and feed interruption.
# A full holder sends excess gas to an ideal flare. During outages, plant net
# electricity is negative because auxiliary loads and backup heating continue.
figure = plot_biogas_plant(results, title="Synthetic 1 MW biogas CHP: 30-day operating profile")

# %%
# 4. Compare the same feed, initial gas and schedule without a holder. Initial VS
# inventories stay identical. Include final gas inventory in the comparison: gas
# left in the holder has not yet generated electricity.
without_storage = simulate_biogas_plant(
    replace(plant, gas_storage_capacity_nm3=0), schedule, initial_state=initial
)
for label, outcome in (("2500 Nm³ holder", results), ("No holder", without_storage)):
    summary = summarize_plant(outcome)
    print(
        f"{label}: net {summary['net_electricity_kwh'] / 1000:.2f} MWh; "
        f"export {summary['grid_export_kwh'] / 1000:.2f} MWh; "
        f"flare {summary['biogas_flared_nm3']:.0f} Nm³; "
        f"final stored {summary['final_stored_biogas_nm3']:.0f} Nm³"
    )

# %%
# 5. Check the conservation residuals, then retain independent plant observations
# for calibration/validation. Conservation alone does not establish accuracy.
summary = summarize_plant(results)
print(f"Maximum VS residual: {summary['maximum_absolute_vs_balance_residual_kg']:.3e} kg")
print(f"Maximum gas residual: {summary['maximum_absolute_gas_balance_residual_nm3']:.3e} Nm³")
