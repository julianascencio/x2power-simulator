# Scenario reference

The CLI reads one JSON object per scenario. `schema_version` must be integer `1`.
Unknown root or component keys are rejected. Numeric values must be finite numbers,
not strings or booleans. Fractions lie in `[0, 1]` unless noted otherwise.

## Common fields

| Field | Required/default | Meaning |
| --- | --- | --- |
| `schema_version` | Required: `1` | Input format version |
| `name`, `description` | Optional | Descriptive metadata |
| `route` | Required | `combustion`, `gasification`, `pyrolysis`, `digestion`, `wastewater`, `biogas` |
| `duration_h` | `1.0` | Positive interval duration |
| `availability` | `1.0` | Generator online fraction; uniformly supplied fuel cannot be rescheduled |
| `feedstock` | Required object | Route-specific feed amounts and properties |
| `process` | Required except biogas | Route-specific conversion parameters |
| `generator` | Required object | Electrical and recovered-heat conversion |
| `auxiliaries` | Empty object | Electrical loads and heat integration |

Feed amounts are **totals per interval**. For a rate of 50 kg/h over 24 h, enter
`mass_kg: 1200` and `duration_h: 24`. Increasing duration alone holds total feed
constant, reduces average feed rate and increases fixed auxiliary consumption.

## Generator and auxiliary fields

| Object/field | Default | Unit or constraint |
| --- | --- | --- |
| `generator.electrical_efficiency` | Required | Fraction greater than zero |
| `generator.heat_recovery_efficiency` | `0.0` | Fraction; electrical + heat efficiency must be ≤ 1 |
| `generator.rated_power_kw` | `null` | Gross electrical limit; `0` disables generation |
| `auxiliaries.fixed_power_kw` | `0.0` | Standing load during the whole interval, including outages |
| `auxiliaries.electricity_fraction_of_gross` | `0.0` | Fraction of gross electricity |
| `auxiliaries.process_electricity_kwh` | `0.0` | Additional interval electrical load |
| `auxiliaries.electric_heater_efficiency` | `1.0` | Fraction greater than zero; resistance-heater convention |
| `auxiliaries.process_heat_usable_fraction` | `1.0` | Fraction of recovered heat suitable for process demand |

The default heat usability of `1` assumes all recovered heat has a suitable
temperature level. Set it explicitly for each case; the thermal examples use zero
where high-temperature heat integration has not been established.

## Route-specific feedstock and process objects

### Combustion, gasification and pyrolysis

- `feedstock`: `mass_kg`, `moisture_fraction` (wet basis), `dry_lhv_mj_per_kg` (> 0).
- `process`: `fuel_energy_recovery`, `evaporation_heat_kwh_per_kg_water`,
  optional `process_heat_kwh_per_kg_dry` (default 0).
- Specify `route` at the root only. All duties are nonnegative. Recovery is a gross
  fraction before the explicitly declared process heat. See [models.md](models.md).

### Digestion

- `feedstock`: the same solid-feed fields as thermal routes.
- Required `process`: `volatile_solids_fraction_dry`, `vs_destruction_fraction`,
  `methane_yield_nm3_per_kg_vs_destroyed`.
- Optional `process`: `methane_fraction` (0.6, > 0), `capture_fraction` (0.98),
  `methane_lhv_kwh_per_nm3` (9.94, > 0), `process_heat_kwh_per_kg_wet` (0).

### Wastewater

- `feedstock`: `volume_m3`, `cod_kg_per_m3`.
- Required `process`: `cod_removal_fraction`, `methane_yield_nm3_per_kg_cod_removed`
  (maximum 0.35021875 at the specified normal state).
- Optional `process`: `methane_fraction` (0.6, > 0), `capture_fraction` (0.98),
  `methane_lhv_kwh_per_nm3` (9.94, > 0), `process_heat_kwh_per_m3` (0).

### Biogas

- Required `feedstock`: `volume_nm3`, `methane_fraction` (> 0).
- Optional `feedstock`: `methane_lhv_kwh_per_nm3` (9.94, > 0), `capture_fraction` (1).
- Optional `process`: `process_heat_kwh` (0).

All gas volumes use **dry gas at 0 °C and 101325 Pa**. For measured wet gas, use
`x2power.utilities.units.normalize_gas_volume` with absolute pressure, temperature
and water-vapour partial pressure. This assumes ideal-gas behaviour.

## Minimal complete example

```json
{
  "schema_version": 1,
  "name": "Synthetic methane generation example",
  "route": "biogas",
  "duration_h": 1,
  "feedstock": {
    "volume_nm3": 100,
    "methane_fraction": 0.6,
    "methane_lhv_kwh_per_nm3": 10
  },
  "generator": {
    "electrical_efficiency": 0.4
  }
}
```

This produces 240 kWh gross and net electricity, with no declared heat demand,
auxiliary consumption or capacity limit. These deliberately simple numbers are an
arithmetic example, not recommended equipment parameters.

## Outputs

`run` returns the route, a shared `power` ledger and route-specific `metrics`.
`gross_electricity_kwh` precedes all declared electrical deductions;
`net_electricity_kwh` deducts auxiliary and electric-heater inputs.
`net_power_kw` is the interval-average net output, not peak power.
`electric_heating_kwh` is separate from `auxiliary_electricity_kwh`.

`fuel_energy_available_kwh` describes energy entering the downstream generator
boundary after conversion/capture. `unused_fuel_energy_kwh` is not automatically
stored or flared. `balance_residual_kwh` checks this boundary only. See
[models.md](models.md) for each metric's interpretation.

The `compare` command writes a compact table with scenario, route, duration,
gross/net kWh and mean net kW. Use `run` for the complete heat and fuel ledger.
