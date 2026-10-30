# Continuous biogas plants

Simulate mixed organic feeds, a continuously stirred tank reactor (CSTR), a gas
holder and combined heat and power (CHP). This model carries substrate and gas
inventories between intervals. It complements the independent, steady-interval
`simulate_digestion` and `simulate_profile` methods.

The three supplied configurations are **synthetic technical examples**. They
represent common agroindustrial and livestock feed combinations, not measured
plants. The implementation is a reduced-order research model; detailed biological
and equipment validation remains to be done and errors may remain.

## Run a plant

```bash
python -m pip install -e '.[plots]'
python use_cases/biogas_plant.py --plant agroindustrial_chp --days 30 --plot
python use_cases/biogas_plant.py --plant dairy_manure_chp --days 30 --plot
python use_cases/biogas_plant.py --plant swine_slurry_chp --days 30 --plot
```

Outputs under `results/biogas_plant/<plant>/` include a PNG profile, CSV intervals
and a JSON record containing the entire configuration, schedule, initial state,
final states and summary. Omit `--plot` to run without Matplotlib. There is no
random sampling. The [worked gallery example](gallery/plot_05_biogas_plant.rst)
walks through the model and compares storage against the same plant without storage.

| Configuration | Wet feed | Gross CHP rating | Equivalent digester | Gas holder |
| --- | --- | --- | --- | --- |
| `agroindustrial_chp` | 100 t/day: food residues, slurry, sludge | 1,000 kW | 3,500 m³ | 2,500 Nm³ |
| `dairy_manure_chp` | 120 t/day: dairy manure and food residues | 500 kW | 4,000 m³ | 1,500 Nm³ |
| `swine_slurry_chp` | 85 t/day: swine slurry and food residues | 250 kW | 2,500 m³ | 800 Nm³ |

All feed properties, decay rates, vessel sizes, gas-holder sizes, efficiencies and
loads in these configurations are assumptions to vary or calibrate. Nameplate
rating is a limit, not a prediction of continuous generation. Their differing
feed composition and throughput prevent a direct performance ranking.

The example uses hourly steps. A 12-hour CHP outage begins at hour 120, and all
feeds stop from hour 240 to 288. These events only occur when the requested run is
long enough. Site demand and weather inputs are synthetic constants. Digestion
continues during the outage; heat and electrical demands remain accounted for.

## Inputs and state

Use `DigesterFeedstock`, `ContinuousDigester`, `BiogasPlant` and `PlantInterval`
from `x2power.methods.biogas_plant`.

```python
from x2power.methods.biogas_plant import PlantInterval, simulate_biogas_plant
from x2power.utilities.biogas_plant import plant_from_config, summarize_plant
from x2power.utilities.io import load_scenario

config = load_scenario("use_cases/plants/agroindustrial_chp.json")
plant = plant_from_config(config)
results = simulate_biogas_plant(plant, [PlantInterval() for _ in range(24)])
print(summarize_plant(results)["net_electricity_kwh"])

# Continue with exactly the same plant definition and feedstock order.
next_day = simulate_biogas_plant(
    plant, [PlantInterval() for _ in range(24)], initial_state=results[-1].state
)
```

Plant JSON uses `model: continuous_biogas_plant` and `schema_version: 1`; it is a
separate configuration from the existing `x2power run` route scenarios. Pass it
through `plant_from_config`, or use the example runner above. Feed rates are
**kg wet/day**, unlike the interval totals accepted by the older route models.
`feed_multipliers` follows the order of `plant.feedstocks`; an empty tuple uses
all base rates. A zero multiplier stops a feed without removing its reactor inventory.

By default, substrate pools start at steady state for the first interval's feeds,
and the gas holder starts empty. Use `initial_plant_state(..., steady_state=False)`
for zero substrate inventory in an already full, warm digester. This does not
simulate microbial inoculation, startup heating or vessel filling. Initial gas
must be declared explicitly and cannot exceed holder capacity.

## Reactor equations and boundaries

For feed `i`, let wet flow be `W_i` (kg/day), density `rho_i` (kg/m³), wet-basis
solids fraction `TS_i`, volatile fraction of solids `VS_i`, biodegradable fraction
of VS `b_i` and first-order conversion rate `k_i` (1/day). Let `V` be working volume.

```{math}
Q = \sum_i W_i/\rho_i,\qquad D = Q/V,\qquad
\mathrm{HRT} = V/Q,\qquad
\mathrm{OLR} = \frac{\sum_i W_i TS_i VS_i}{V}.
```

At zero flow, HRT is undefined and reported as `None` / JSON `null`. The model
assumes constant liquid volume, equal inlet/outlet flow and perfect mixing. It
neglects gas-volume effects on liquid hydraulics. There is no solids separation,
recycle or independent solids retention time. Parallel tanks can be represented
as one equivalent mixed volume only when that approximation is justified; tanks
in series and post-digesters need separate models.

Each feed has a degradable VS pool `M_i` and an inert VS pool `I_i`, in kg:

```{math}
\frac{dM_i}{dt} = W_i TS_i VS_i b_i - (k_i+D)M_i,\qquad
\frac{dI_i}{dt} = W_i TS_i VS_i(1-b_i)-DI_i.
```

Inputs are constant within an interval. The code integrates each linear equation
analytically, including its integrated reaction and effluent flows. Thus:

```{math}
M_{i,1}=M_{i,0}e^{-(k_i+D)\Delta t}
+\frac{W_i TS_i VS_i b_i}{k_i+D}(1-e^{-(k_i+D)\Delta t}).
```

The zero-rate limit is handled explicitly. Destroyed VS is the integral of
`k_i M_i`; methane equals destroyed VS times the declared yield. This yield is
**Nm³ CH4/kg VS destroyed**, not biogas per kg wet feed, per kg VS fed, or a batch
BMP measurement. Do not insert a BMP value without reconciling the denominator
and assumed biodegradability. A feed-level upper-potential check rejects methane
energy greater than the dry feed's declared LHV. This is a plausibility check,
not a complete reactor energy balance.

The VS ledger is initial inventory + feed = destroyed + effluent + final inventory.
Effluent VS is reported, but total digestate wet mass, nutrient content, pathogen
removal and fertilizer properties are not predicted. The first-order equations
are an explicit project approximation, **not an implementation of ADM1**. They
do not resolve pH, microbial growth, ammonia/VFA inhibition or temperature kinetics.
Configured HRT/OLR limits generate diagnostic flags without changing the rates.

## Gas, CHP, heat and electricity

All gas volumes use a dry normal reference of **0 °C and 101325 Pa**. Holder
capacity is an equivalent normal gas volume, not a geometric membrane capacity.
A constant methane fraction converts methane to biogas; capture losses are
reported separately as methane not captured. Cleaning electricity is included,
but contaminant removal and gas composition changes are not calculated.

Each interval uses its **average captured gas production** for dispatch. CHP demand
is limited by rating × setpoint fraction × availability × elapsed time. Available
fuel comprises initial stored gas and captured production. The engine uses up to
its demand; remaining gas fills the holder, and excess goes to an unlimited ideal
flare. The ledger is initial storage + captured = CHP + flare + final storage.
There are no holder flow limits, pressure dynamics, storage leaks, minimum engine
load or startup costs. Flared volume is a destination flow, not methane emitted.
Fractional availability is an equivalent derating; resolve actual outages with
separate 0/1 intervals. Check sensitivity to shorter time steps when feeds change
rapidly or the holder empties/fills. Within-interval gas fluctuations are not resolved.

The engine has constant LHV-based electrical and recovered-heat efficiencies.
Recovered heat supplies the digester first. Heating demand is:

```{math}
H_{feed}=\frac{m_{wet}c_p\max(T_d-T_{feed},0)}{3600},\qquad
H_{loss}=UA\max(T_d-T_{ambient},0)\Delta t_h.
```

`c_p` is kJ/(kg K), `UA` is kW/K and each heat term is kWh. Fixed digester temperature
is maintained by an **unlimited electric backup heater** when recovered heat is
insufficient. Its electricity is deducted from output, including during outages.
There is no thermal storage, cooling load, boiler or pasteurization step. Any
upstream sanitization demand must be modelled separately. Remaining recovered heat
can serve declared site heat demand; unmet site heat and rejected heat are explicit.

Plant net electricity deducts mixing, fixed auxiliaries, feed preparation, gas
treatment and backup heating. Site electricity demand is then subtracted to split
positive grid exports from grid imports. Export is unconstrained, without a grid
connection limit or demand tariff. Negative plant net output remains visible.
The CHP follows the declared setpoint; it is not an optimizing dispatch controller.

## Technical sources and validation

These references establish the process context and measurement definitions;
they do **not** validate the synthetic configurations or supply their numerical
parameters:

- U.S. EPA AgSTAR, *Project Development Handbook*, third edition, April 2020,
  EPA 430-B-20-001: chapters 3–5 on digestion, feedstocks and gas/CHP equipment.
  [Official publication](https://www.epa.gov/agstar/agstar-project-development-handbook).
- U.S. EPA AgSTAR, *Anaerobic Digester/Biogas System Operator Guidebook*, November
  2020, EPA 430-B-20-003: sections 3.1–3.5 on retention, loading, temperature and
  methane potential; section 7.4 on gas utilization and CHP heat recovery.
  [Official PDF](https://www.epa.gov/sites/default/files/2020-11/documents/agstar-operator-guidebook.pdf).
- Bernhard Drosg, *Process monitoring in biogas plants*, IEA Bioenergy Task 37,
  2013: biological stability and the need for plant-specific monitoring.
  [Official report page](https://task37.ieabioenergy.com/technical-reports/process-monitoring-in-biogas-plants/).

Tests compare steady-state and transient results against independent analytical
solutions and check VS, gas, electricity and heat ledgers, storage limits, outages,
state continuation, small steps and invalid inputs. Before treating results as
plant predictions, calibrate feed TS/VS, yields, rate constants, measured gas
composition, heat losses, engine curves and auxiliary loads. Validate against
independent measured intervals, including disturbances. See [validation guidance](validation.md).
