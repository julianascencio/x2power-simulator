# Installation and quick start

## Install from the repository

X2Power requires Python 3.11 or newer. Install the source checkout:

```bash
git clone https://github.com/julianascencio/x2power-simulator.git
cd x2power-simulator
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

On Windows, activate with `.venv\Scripts\Activate.ps1` in PowerShell. Install
`python -m pip install -e '.[plots]'` to enable plotting. The simulation core has no
runtime dependencies.

## First Python simulation

This deliberately simple example converts 100 Nm³ of biogas with 60% methane,
using an illustrative methane LHV of 10 kWh/Nm³ and 40% electrical efficiency.

```python
from x2power import Generator
from x2power.methods import BiogasStream, simulate_biogas

result = simulate_biogas(
    BiogasStream(volume_nm3=100, methane_fraction=0.6, methane_lhv_kwh_per_nm3=10),
    Generator(electrical_efficiency=0.4),
    duration_h=1,
)

print(result.power.gross_electricity_kwh)  # 240.0
print(result.power.net_electricity_kwh)  # 240.0
print(result.power.net_power_kw)  # 240.0
```

No auxiliary loads, heat demand or power limit are declared, so gross and net
electricity are equal. Feed volumes are totals over the interval. Gas volumes use
dry gas at 0 °C and 101325 Pa.

## Run a JSON scenario

From the repository root:

```bash
x2power run use_cases/scenarios/biogas_engine.json
x2power run use_cases/scenarios/organic_wastewater.json -o results/wastewater.json
x2power compare use_cases/scenarios/biomass_gasification.json use_cases/scenarios/biomass_combustion.json --csv results/comparison.csv
```

`python -m x2power` is equivalent to the `x2power` command. Consult the
[scenario reference](../scenarios.md) for field names, units and defaults.

## Plot and export

```bash
python -m pip install -e '.[plots]'
x2power plot use_cases/scenarios/biomass_gasification.json -o results/energy_balance.png
python use_cases/visual_report.py
```

The visual example produces four figures, CSV tables and a JSON record of inputs
and results. The [example gallery](../gallery/index.rst) provides self-contained
Python scripts and downloadable notebooks for individual calculations.

## Choosing a model

Use measured biogas input when gas properties are available. Use the digestion
model for a volatile-solids yield basis, or the wastewater model for a removed-COD
basis. Thermal routes require dry-feed LHV, selected fuel-energy recovery and an
explicit process-heat duty. Route labels do not determine these parameters for you.

Read the [equations and boundaries](../models.md) before transferring parameters
from equipment literature, especially LHV/HHV efficiencies and yield denominators.
