# Equations and model boundaries

This page describes the original independent route models. For stateful substrate
pools and gas storage, see [continuous biogas plants](biogas_plants.md).

All energies below are in kWh unless stated otherwise. Feed amounts, gas volumes
and electrical loads refer to one interval of duration `t` hours. Efficiencies are
dimensionless fractions on an LHV basis. These models expose assumptions; they do
not infer equipment parameters from a feedstock name.

## Shared generation model

Let `F` be the available fuel energy, `a` the availability, `P` the optional gross
electrical power rating, `eta_e` the electrical efficiency and `eta_h` the recovered
heat efficiency. Both efficiencies are applied to the same fuel input, with
`eta_e + eta_h <= 1`.

```text
F_used = F * a                              (without a power rating)
F_used = min(F * a, P * t * a / eta_e)       (with a power rating)
E_gross = F_used * eta_e
H_recovered = F_used * eta_h
L_generator = F_used * (1 - eta_e - eta_h)
F_unused = F - F_used
```

Availability is the fraction of the interval when the generator can operate. Fuel
is supplied uniformly, so fuel arriving during unavailable hours cannot be shifted
to online hours. A profile can instead set the feed rate to zero during a complete
feed interruption. Upstream processing and standing loads otherwise remain active.

For process demand `H_demand`, recovered-heat usability fraction `u`, electric
heater efficiency `eta_heater`, fixed auxiliary power `P_aux`, gross-output load
fraction `f_aux` and interval process electricity `E_process`:

```text
H_to_process = min(H_recovered * u, H_demand)
H_surplus = H_recovered - H_to_process
E_heater = (H_demand - H_to_process) / eta_heater
E_aux = P_aux * t + f_aux * E_gross + E_process
E_net = E_gross - E_aux - E_heater
P_net_mean = E_net / t
```

`H_surplus` includes recovered heat that cannot serve the declared process duty;
it is not automatically useful export heat. Temperature levels, heat exchanger
pinches and heat losses outside the specified efficiencies are not solved.

`E_net < 0` is an external electricity requirement. Electric heating is a deliberate
boundary choice: a plant that burns a fuel fraction for process heat needs a
different allocation model. Do not treat this model as that fuel-fired configuration.

The reported generator balance residual is:

```text
F - (E_gross + H_recovered + L_generator + F_unused)
```

It should be zero within floating-point tolerance. This is a generator-boundary
identity, not validation of the upstream conversion or a full-plant heat balance.
`net_electrical_efficiency` is `E_net / F`, uses **available downstream fuel** as
its denominator, and is undefined (`null` in JSON) when `F = 0`. It is not the
overall feedstock-to-electricity efficiency. For solid-feed routes, divide net
electricity by `metrics.feedstock_chemical_energy_kwh` for that separate ratio.

## Thermal conversion

For wet mass `m`, wet-basis moisture `w`, dry-feed LHV `L` in MJ/kg, selected fuel
energy recovery `r`, water evaporation duty `q_water` in kWh/kg water and dry-feed
process duty `q_dry` in kWh/kg dry matter:

```text
m_dry = m * (1 - w)
m_water = m * w
E_feed = m_dry * L / 3.6
F = E_feed * r
H_demand = m_water * q_water + m_dry * q_dry
```

The dry LHV applies to all dry matter, including any ash already present; no
additional ash correction is made. All feed moisture is assumed to evaporate.
`q_water` must include the appropriate sensible and latent heat. `q_dry` represents
the separately specified reaction and sensible duty of the dry feed.

The meaning of `r` depends on the route:

| Route | Recovery boundary |
| --- | --- |
| Combustion | Energy transferred from the boiler to the downstream power block |
| Gasification | Chemical energy in the selected fuel gas supplied to the generator |
| Pyrolysis | Combined chemical energy in the selected fuel products supplied to the generator |

Use recovery fractions **before the explicit process-heat deductions**. A quoted
net efficiency that already deducts drying or reactor heat would count those
demands twice. The combustion model similarly assumes drying demand is specified
separately from boiler energy recovery. Pyrolysis products are aggregated; product
fractions, char yields, gas composition and engine fuel compatibility are not
predicted. One common generator efficiency is an approximation if several products
would use different conversion equipment.

Unrecovered feedstock energy is reported as `E_feed - F` without assigning a
destination. Only the wet/dry feed mass split is calculated; this is not a full
product mass balance. Selected recovery and heat-duty parameters require
experimental or equipment-specific calibration.

## Biogas

For dry normal biogas volume `V`, methane volume fraction `x`, methane capture
fraction `c` and methane LHV `L_CH4` in kWh/Nm³:

```text
V_CH4_produced = V * x
V_CH4_captured = V_CH4_produced * c
F = V_CH4_captured * L_CH4
```

The default methane LHV, 9.94 kWh/Nm³, is an approximate configurable value for the
declared normal state. Other combustible gas species are ignored. Gas cleaning,
compression and pumps must be included in the declared auxiliary loads. Capture
describes methane reaching the generation system; exhaust methane slip is not
modelled. Uncaptured methane and unused fuel are separate outputs with no assumed
disposal destination.

## Volatile-solids digestion

For dry-feed volatile-solids fraction `v`, destruction fraction `d` and methane
yield `y_VS` in Nm³ per kg **VS destroyed**:

```text
m_VS_fed = m_dry * v
m_VS_destroyed = m_VS_fed * d
V_CH4_produced = m_VS_destroyed * y_VS
H_demand = m_wet * process_heat_kwh_per_kg_wet
```

Biogas volume is methane volume divided by the methane fraction; the biogas model
then applies capture and generation. Do not insert a yield per kg VS fed without
converting its basis. Predicted methane chemical energy may not exceed the supplied
feedstock LHV. No retention time, inhibition, microbial kinetics, mixing or
digestate-quality prediction is included.

## Organic wastewater

For wastewater volume `V_water` in m³, concentration `C_COD` in kg COD/m³, removal
fraction `d_COD` and yield `y_COD` in Nm³ per kg COD removed:

```text
m_COD_fed = V_water * C_COD
m_COD_removed = m_COD_fed * d_COD
V_CH4_produced = m_COD_removed * y_COD
H_demand = V_water * process_heat_kwh_per_m3
```

The accepted yield is capped at `22.414 / 64 = 0.35021875` Nm³/kg COD removed.
This follows from `CH4 + 2 O2 -> CO2 + 2 H2O`: one mole of methane corresponds to
64 g oxygen demand and approximately 22.414 L ideal-gas volume at 0 °C and 1 atm.
Real yields may be substantially lower. COD removal and yield must be measured or
justified for the substrate and reactor. Concentrations in mg/L must be divided
by 1000 to obtain kg/m³.

The wastewater model has no influent LHV, so it does not report overall chemical
energy closure upstream of methane. It does not model nutrient removal, effluent
compliance, dissolved methane, hydraulics or the complete treatment process.

## Profiles and uncertainty

`simulate_profile` scales interval feed amounts from the base amount divided by
base duration. Each interval supplies a new availability and feed-rate multiplier.
Fixed interval process electricity, and the biogas route's explicit process heat,
scale with elapsed time. Route-specific mass/volume heat demands scale with feed.
Intervals are independent: there is no gas storage, startup state or reactor memory.

`monte_carlo` samples independent uniform distributions with a seeded local random
generator. It retains every draw and uses linear interpolation for quantiles.
Invalid physical combinations raise an error rather than being silently discarded.
The reported percentiles describe input assumptions; they are not probability
estimates for an actual installation without calibration and uncertainty analysis.

## Technical references

These sources describe the physical routes and accounting concepts. They do not
validate the synthetic inputs shipped with this repository.

- [US DOE: Biopower—Energy for Heat and Electricity](https://www.energy.gov/cmei/fuels/biopower-energy-heat-and-electricity): route descriptions.
- [US EPA: Basic Information about Anaerobic Digestion](https://www.epa.gov/anaerobic-digestion/basic-information-about-anaerobic-digestion): feedstocks, biogas and digestion products.
- [US EPA: Methods for Calculating CHP Efficiency](https://www.epa.gov/chp/methods-calculating-chp-efficiency): electrical and useful-heat accounting.
- [US EPA: Reciprocating Internal Combustion Engines, CHP Catalog](https://www.epa.gov/sites/default/files/2015-07/documents/catalog_of_chp_technologies_section_2._technology_characterization_-_reciprocating_internal_combustion_engines.pdf): equipment characteristics; check HHV/LHV basis before using tabulated values.
