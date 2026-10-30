"""
Plastic to electricity: pyrolysis, heat and net power
=========================================================

Follow a synthetic 2-tonne plastic-containing feed through a lumped pyrolysis
stage and a generator over 24 hours. Three figures explain the electrical and
thermal balance, fuel-recovery sensitivity, and the effect of generator capacity.
These inputs are illustrative, not measured performance or equipment guarantees.
"""

from x2power.scenario import run_scenario
from x2power.utilities.experiments import sweep_parameter
from x2power.utilities.plotting import plot_energy_balance, plot_sensitivity

# %%
# 1. Specify the feed and conversion assumptions. The 40 MJ/kg lower heating
# value is per kg of dry feed. With 2% moisture, 2000 kg wet feed contains 1960 kg
# dry material and 40 kg water. Selected pyrolysis fuel products carry 70% of the
# dry-feed chemical energy before the explicitly modelled process heat demand.
# Product gas/oil/char mass yields and fuel-engine compatibility are not predicted.
#
# The dictionary is self-contained so the downloaded Python/notebook runs without
# input files. It uses the same inputs as ``scenarios/plastic_pyrolysis.json``.
scenario = {
    "schema_version": 1,
    "duration_h": 24.0,
    "availability": 0.95,
    "description": "Synthetic illustrative parameters; not measured equipment performance.",
    "name": "plastic_pyrolysis",
    "generator": {
        "electrical_efficiency": 0.35,
        "heat_recovery_efficiency": 0.4,
        "rated_power_kw": 500.0,
    },
    "auxiliaries": {
        "fixed_power_kw": 3.0,
        "electricity_fraction_of_gross": 0.04,
        "process_electricity_kwh": 20.0,
        "electric_heater_efficiency": 0.95,
        "process_heat_usable_fraction": 0.0,
    },
    "route": "pyrolysis",
    "feedstock": {"mass_kg": 2000.0, "moisture_fraction": 0.02, "dry_lhv_mj_per_kg": 40.0},
    "process": {
        "fuel_energy_recovery": 0.7,
        "evaporation_heat_kwh_per_kg_water": 0.75,
        "process_heat_kwh_per_kg_dry": 0.6,
    },
}

# %%
# 2. Convert the selected fuel in a 500 kW gross generator, with 35% electrical
# efficiency and 95% availability. Pyrolysis and drying heat are supplied by an
# electric heater. Recovered generator heat is deliberately not credited to the
# high-temperature process: temperature suitability/integration is unverified.
# Pumps, preparation and other auxiliaries are represented by the declared loads.
result = run_scenario(scenario)
power = result.power
print(f"Dry-feed chemical energy: {result.metrics['feedstock_chemical_energy_kwh']:,.1f} kWh")
print(f"Selected fuel energy: {power.fuel_energy_available_kwh:,.1f} kWh")
print(f"Unused selected fuel: {power.unused_fuel_energy_kwh:,.1f} kWh")
print(f"Gross electricity: {power.gross_electricity_kwh:,.1f} kWh")
print(f"Process heat demand: {power.process_heat_demand_kwh:,.1f} kWh thermal")
print(f"Heater electricity: {power.electric_heating_kwh:,.1f} kWh")
print(f"Auxiliary electricity: {power.auxiliary_electricity_kwh:,.1f} kWh")
print(f"Net electricity: {power.net_electricity_kwh:,.1f} kWh over 24 h")
print(f"Average net power: {power.net_power_kw:,.1f} kW")
wet_tonnes = scenario["feedstock"]["mass_kg"] / 1000
print(f"Net per wet tonne: {power.net_electricity_kwh / wet_tonnes:,.1f} kWh/t")

# %%
# 3. Inspect the electricity waterfall and heat allocation. Heater electricity
# exceeds delivered heat because heater efficiency is 95%. Recovered heat that
# cannot serve this process is shown separately and is not counted as electricity.
# Unused fuel from unavailable/capacity-limited hours is reported without assuming
# storage, flaring or a particular product destination.
balance_figure = plot_energy_balance(
    result, title="Synthetic plastic pyrolysis: 2 tonnes over 24 hours"
)

# %%
# 4. Vary only fuel-energy recovery. These wide stress-test values are not an
# experimentally supported range. At low recovery, heating and auxiliary loads
# can exceed generation. Negative net output is retained as an electrical import
# requirement. All other inputs, including the heater load, remain fixed.
recovery = sweep_parameter(scenario, "process.fuel_energy_recovery", [i / 10 for i in range(1, 10)])
recovery_figure = plot_sensitivity(
    recovery,
    xlabel="Fraction of dry-feed LHV recovered in selected fuel products",
    title="Plastic-to-power: fuel recovery sensitivity",
)

# %%
# 5. Vary wet throughput at the same moisture and LHV. Gross generation eventually
# reaches the 500 kW rating times 24 hours times 95% availability. Heating scales
# with processed feed, so adding feed beyond generator capacity need not improve
# net electricity. Fixed loads and the 20 kWh interval process load remain fixed;
# the percentage auxiliary load follows gross generation. No reactor capacity
# constraint or automatic feed reduction is assumed.
throughput = sweep_parameter(
    scenario, "feedstock.mass_kg", [0, 500, 1000, 2000, 4000, 6000, 8000, 10000]
)
throughput_figure = plot_sensitivity(
    [{**row, "input_value": row["input_value"] / 1000} for row in throughput],
    xlabel="Wet feed (tonnes over 24 hours)",
    title="Plastic-to-power: throughput with a 500 kW generator",
)

# %%
# 6. Check the generator energy ledger. This residual does not validate upstream
# chemistry or the assumed yields. Actual plastic composition, contamination,
# preparation, product conditioning, generator compatibility and emissions need
# separate data and models. Do not interpret these assumptions as a universal
# result for mixed plastics or as a detailed reactor design.
print(f"Generator energy residual: {power.balance_residual_kwh:.3e} kWh")
maximum_gross = max(row["gross_electricity_kwh"] for row in throughput)
print(f"Maximum gross electricity in sweep: {maximum_gross:,.1f} kWh")
