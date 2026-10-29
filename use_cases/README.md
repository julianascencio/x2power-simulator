# Runnable use cases

Install the package from the repository root with `python -m pip install -e .`.
Scripts locate their input files relative to their own location and write outputs
to `results/` under the current working directory.

| Command | Demonstration | Output |
| --- | --- | --- |
| `python use_cases/compare_routes.py` | Run seven distinct synthetic scenarios | `route_comparison.csv` |
| `python use_cases/moisture_sweep.py` | Vary gasification feed moisture at constant wet mass | `moisture_sweep.csv` |
| `python use_cases/operating_profile.py` | Vary biogas flow and include a generator outage | `operating_profile.json` |
| `python use_cases/uncertainty.py` | Seeded independent uniform sampling of digestion parameters | `uncertainty.json` |
| `python use_cases/visual_report.py` | Four technical figures with all inputs and numerical outputs retained | `visual_report/` |

The visual example requires `python -m pip install -e '.[plots]'`. It saves PNG and
SVG figures, two CSV tables and a JSON record of inputs, settings and results.
Change its destination with `--output-dir PATH`. See [the plotting guide](../docs/plotting.md).

The comparison demonstrates the shared output interface. The feeds and scales differ,
so its rows do not constitute a ranking of conversion technologies.

The moisture sweep holds wet mass fixed: increasing moisture both reduces dry-feed
chemical energy and increases evaporation duty. Negative net electricity is valid.

The operating profile reports separate intervals, energy totals and mean power. Standing
loads and feed processing continue during the generator outage; unused gas is
reported without a storage or disposal assumption.

The uncertainty case preserves 1000 draws with seed 42. Its p05/p50/p95 values
describe the specified input distributions. They do not quantify empirical accuracy.

## Scenario files

- `plastic_pyrolysis.json`: selected fuel-product energy recovery and electric process heat.
- `biomass_gasification.json`: fuel-gas energy recovery, moisture and electric process heat.
- `biomass_combustion.json`: boiler-to-power-block recovery and heat integration.
- `food_waste_digestion.json`: volatile-solids destruction and methane capture.
- `sludge_digestion.json`: dilute solids and wet-feed heating demand.
- `organic_wastewater.json`: removed COD converted to methane.
- `biogas_engine.json`: measured-volume-style biogas input with a declared heat load.

Every value is illustrative. The thermal examples set heat usability explicitly;
do not transfer the assumptions to equipment without checking temperature levels.
See [the scenario reference](../docs/scenarios.md) for units and parameter meanings.
