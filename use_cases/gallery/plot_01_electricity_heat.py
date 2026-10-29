"""
Electricity and process heat
============================

An explicit heat demand can substantially reduce net electrical output.
This example separates the electric heater's input from the heat it delivers.
The numbers are synthetic and use a constant-efficiency generator.
"""

from x2power import AuxiliaryLoads, Generator, SimulationResult
from x2power.methods import generate_power
from x2power.utilities.plotting import plot_energy_balance

# %%
# Start with 1000 kWh of fuel over two hours. Electrical efficiency is 35%,
# recovered-heat efficiency is 40%, and process heat demand is 500 kWh.
# The recovered 400 kWh leaves a 100 kWh thermal deficit.
power = generate_power(
    1000,
    Generator(electrical_efficiency=0.35, heat_recovery_efficiency=0.4),
    duration_h=2,
    process_heat_kwh=500,
    auxiliaries=AuxiliaryLoads(
        fixed_power_kw=10,
        electricity_fraction_of_gross=0.05,
        process_electricity_kwh=5,
        electric_heater_efficiency=0.8,
    ),
)
print(f"Gross electricity: {power.gross_electricity_kwh:.1f} kWh")
print(f"Heater electricity: {power.electric_heating_kwh:.1f} kWh")
print(f"Net electricity: {power.net_electricity_kwh:.1f} kWh")

# %%
# The heater consumes 125 kWh to supply 100 kWh of heat. Auxiliary electricity
# is 42.5 kWh, leaving 182.5 kWh net electricity over the interval.
figure = plot_energy_balance(
    SimulationResult("biogas", power), title="Synthetic example: electricity and heat"
)
