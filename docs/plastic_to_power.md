# Plastic to electricity

The [worked gallery example](gallery/plot_06_plastic_to_power.rst) follows a plastic
feed through selected pyrolysis fuel products and a generator. It includes three
figures: electricity/heat accounting, fuel-recovery sensitivity and throughput at a
fixed generator rating. Download its Python script or notebook to run it separately.

The model uses **synthetic assumptions**, not measurements from a particular plant.
It accounts for energy in selected fuel products without predicting gas, oil or
char composition, product mass yields or their compatibility with an engine.

## Run and export

```bash
python -m pip install -e '.[plots]'
python use_cases/plastic_to_power.py --plot
```

The runner reads `use_cases/scenarios/plastic_pyrolysis.json` and writes to
`results/plastic_to_power/` by default. Use `--output-dir PATH` to change the
output directory. JSON contains the input scenario, full baseline result,
indicators and both sweeps. CSV tables retain the sweep parameter in its native
units: fraction for recovery, kg wet feed for throughput. PNG and SVG figures
present throughput in tonnes over 24 hours. Omit `--plot` to use only the Python
standard library.

The existing CLI can also run the baseline directly:

```bash
x2power run use_cases/scenarios/plastic_pyrolysis.json -o results/plastic.json
```

## Baseline assumptions

| Input | Synthetic value |
| --- | --- |
| Simulation duration | 24 hours |
| Wet feed / moisture | 2,000 kg / 2% wet basis |
| Dry-feed lower heating value | 40 MJ/kg dry |
| Energy recovery in selected fuel products | 70% of dry-feed LHV |
| Generator | 500 kW gross rating; 35% electrical efficiency |
| Availability | 95%, with no implicit fuel storage |
| Recovered-heat efficiency | 40%; no credit to process heating |
| Drying / dry-feed process heat | 0.75 kWh/kg water / 0.6 kWh/kg dry feed |
| Electric-heater efficiency | 95% |
| Auxiliary loads | 3 kW fixed + 4% of gross electricity + 20 kWh per interval |

The dry feed contains 21,777.8 kWh of chemical energy; 15,244.4 kWh reaches the
selected fuel stream. With the declared availability, 762.2 kWh of that fuel is
unused. The baseline predicts approximately **5,068.8 kWh gross** and
**3,504.6 kWh net electricity over 24 hours**, or **146.0 kW average net power**.
Process heating consumes 1,269.5 kWh of electricity and other auxiliaries consume
294.8 kWh. These are numerical consequences of the inputs, not validated yields.

## Interpret the sweeps

- **Fuel recovery:** vary the selected-fuel energy fraction from 0.1 to 0.9 while
  holding all other inputs fixed. This is a stress test, not a measured parameter
  range. Low recovery can make the process a net electricity consumer.
- **Throughput:** vary wet feed from 0 to 10 tonnes over the same 24 hours. Gross
  generation caps at 11,400 kWh: 500 kW × 24 h × 0.95. Feed-dependent heating keeps
  increasing, so net output can fall after the generator reaches capacity. The
  fixed 20 kWh process load is held constant; no reactor throughput limit or
  automatic feed curtailment is assumed.

Recovered generator heat is not credited to the process because suitable
heat temperature and integration have not been established. Unused recovered heat
may have other applications, but no external heat user is modelled here. Product
fuel left unused during unavailable or capacity-limited hours is reported without
assigning a storage, combustion or disposal destination.

Characterize the actual plastic mixture and moisture, then calibrate LHV, recovery,
process heat, conditioning loads and generator efficiency. This example does not
model chlorine, contaminants, gas cleaning, emissions, reaction kinetics or reactor
design. See [model equations](models.md) and [validation guidance](validation.md).
