# X2Power Simulator

A Python simulator for converting solid feedstocks, biogas and organic wastewater
into electricity. It calculates gross generation, net electricity, process heat,
auxiliary consumption and capacity constraints using explicit energy balances.

The simulation core has **no runtime dependencies** and requires **Python 3.11 or newer**.
Install the optional `plots` extra for Matplotlib figures.
Models are reduced-order, interval-based calculations. All bundled scenario inputs
are synthetic examples, not measured equipment performance.

**[Documentation](https://julianascencio.github.io/x2power-simulator/)** ·
[Example gallery](https://julianascencio.github.io/x2power-simulator/gallery/index.html) ·
[API reference](https://julianascencio.github.io/x2power-simulator/reference/index.html)

## AI-generated content

Most of the code, examples and documentation in this repository are AI-generated,
based on specific, real scientific and technical literature selected by the
repository developers. The developers guide source selection, implementation,
review and validation.

## Quick start

```bash
git clone https://github.com/julianascencio/x2power-simulator.git
cd x2power-simulator
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
x2power run use_cases/scenarios/biogas_engine.json
```

On Windows, activate with `.venv\Scripts\Activate.ps1` in PowerShell.
The equivalent module command is `python -m x2power`.

Save a full result or compare scenarios:

```bash
x2power run use_cases/scenarios/organic_wastewater.json -o results/wastewater.json
x2power compare use_cases/scenarios/biomass_gasification.json use_cases/scenarios/biomass_combustion.json --csv results/comparison.csv
```

Comparisons preserve each scenario's feed amount and interval length. Normalize
these inputs before interpreting differences as conversion performance.

## Conversion methods

| Route | Calculation basis | Example |
| --- | --- | --- |
| Combustion | Dry-feed LHV, boiler energy recovery and power-block efficiency | Biomass |
| Gasification | Dry-feed LHV and selected fuel-gas energy recovery | Biomass |
| Pyrolysis | Dry-feed LHV and combined energy recovery in selected fuel products | Plastic |
| Anaerobic digestion | Volatile solids destroyed and methane yield | Food waste, sludge |
| Organic wastewater | COD removed and methane yield | Organic wastewater |
| Biogas generation | Dry normal gas volume and methane fraction | Biogas engine |

Every route uses the same generation model, with optional gross power rating,
availability, heat recovery, electric heating and auxiliary loads. Negative net
electricity is retained and indicates a need for external electrical supply.

## Python API

```python
from x2power import AuxiliaryLoads, Generator, SolidFeedstock
from x2power.methods import ThermalProcess, simulate_thermal

result = simulate_thermal(
    SolidFeedstock(mass_kg=100, moisture_fraction=0.2, dry_lhv_mj_per_kg=18),
    ThermalProcess(
        route="gasification",
        fuel_energy_recovery=0.7,
        evaporation_heat_kwh_per_kg_water=0.7,
        process_heat_kwh_per_kg_dry=0.2,
    ),
    Generator(electrical_efficiency=0.3, heat_recovery_efficiency=0.4),
    duration_h=1,
    auxiliaries=AuxiliaryLoads(process_heat_usable_fraction=0),
)

print(result.power.gross_electricity_kwh)  # 84.0
print(result.power.net_electricity_kwh)  # 54.0
```

This example supplies process heat electrically. Set the usable recovered-heat
fraction only when the available heat matches the required temperature and duty.

## Repository layout

| Folder | Purpose |
| --- | --- |
| [`src/x2power/methods/`](src/x2power/methods) | Conversion models, shared generation model and operating profiles |
| [`src/x2power/utilities/`](src/x2power/utilities) | Validation, unit conversions, JSON/CSV, sweeps and Monte Carlo experiments |
| [`use_cases/`](use_cases) | Runnable examples, seven route scenarios and three continuous plant configurations |
| [`tests/`](tests) | Hand-calculated cases, conservation checks, limiting cases and CLI integration |
| [`docs/`](docs) | Equations, configuration reference, assumptions and validation guidance |

Run the included experiments after installation:

```bash
python use_cases/compare_routes.py
python use_cases/moisture_sweep.py
python use_cases/operating_profile.py
python use_cases/uncertainty.py
```

Outputs are written to `results/` in the current working directory. See the
[use-case guide](use_cases/README.md) for what each experiment measures.

## Plot simulation results

```bash
python -m pip install -e '.[plots]'
x2power plot use_cases/scenarios/biomass_gasification.json -o results/energy_balance.png
python use_cases/visual_report.py
```

The worked example writes electricity/heat, moisture sensitivity, operating profile
and uncertainty figures as PNG and SVG. Its JSON output retains the scenario inputs,
experiment settings, seed, sample draws and numerical results. CSV tables expose
the sensitivity sweep and interval powers. See [the plotting guide](docs/plotting.md).

![Synthetic moisture sensitivity example](docs/figures/moisture_sensitivity.svg)

## Continuous biogas plants

Simulate mixed organic feeds, a continuously stirred digester, gas storage and
CHP with hourly operating schedules. Includes generic agroindustrial, dairy-manure
and swine-slurry configurations, all with synthetic inputs.

```bash
python use_cases/biogas_plant.py --plant agroindustrial_chp --days 30 --plot
```

Install the `plots` extra for figures. The example records substrate/gas inventories,
net electricity, grid imports/exports, flaring and heat demand in JSON/CSV.
See the [plant model and assumptions](docs/biogas_plants.md) and
[step-by-step gallery](https://julianascencio.github.io/x2power-simulator/gallery/plot_05_biogas_plant.html).

## Route model boundaries

- Input masses and volumes are **totals over the simulation interval**, not rates.
- Heating values and conversion efficiencies use the **lower heating value (LHV)** basis.
- Gas volumes use a dry normal state of **0 °C and 101325 Pa**.
- Fuel arrives uniformly; unavailable hours and capacity limits leave unused fuel.
  There is no implicit fuel storage or rescheduling.
- Usable recovered heat offsets process demand. Remaining demand is supplied by an
  electric resistance heater and deducted from net electricity.
- Energy closure is checked at the generator boundary. No detailed reaction,
  product-speciation, emissions, gas-cleaning or reactor-kinetics model is included.
- The original route profiles combine independent steady intervals. The continuous
  biogas plant module separately tracks substrate and gas inventories.
  Monte Carlo quantiles describe
  the chosen input distributions, not calibrated confidence intervals.

Read [equations and boundaries](docs/models.md), the
[scenario reference](docs/scenarios.md) and
[validation guidance](docs/validation.md) before adapting a scenario.

## Development

```bash
python -m pip install -e '.[dev,plots]'
ruff check .
ruff format --check .
ty check src use_cases
pytest --cov=x2power --cov-report=term-missing
python -m build
```

CI runs the tests on Python 3.11–3.14 and checks formatting, static types and package
builds. The coverage threshold is 85%, including branches. See
[CONTRIBUTING.md](CONTRIBUTING.md) for model contribution requirements.

Build the Sphinx documentation and execute the gallery locally:

```bash
python -m pip install -e '.[docs]'
sphinx-build -W --keep-going -b html docs docs/_build/html
```

GitHub Actions validates documentation on pull requests and publishes successful
builds from `main` to GitHub Pages. See [documentation development](docs/development.md).
