# Verification and calibration

## What the automated tests establish

- Agreement with independent arithmetic examples for generation, usable heat,
  fuel capture, thermal conversion, VS destruction and COD conversion.
- Generator-boundary conservation across capacity limits and availability values.
- Correct limiting behaviour for zero fuel, zero capacity, complete outages and
  net-negative operation.
- Rejection of invalid units-as-strings, non-finite numbers, impossible fractions,
  incompatible energy yields and unknown input fields.
- Consistent interval aggregation, deterministic seeded sampling and immutable
  source scenarios during experiments.
- Executable example scripts, CLI JSON/CSV output and package entry points.

These are software verification checks. They do not establish empirical accuracy.
All seven included scenarios use synthetic parameters and must be calibrated before
their outputs can be interpreted as a prediction of specific equipment.

## Calibrating a scenario

1. Define the interval, feedstock sampling method and measurement conditions.
2. Establish wet mass, moisture basis, dry-feed LHV, ash basis, VS/COD or dry normal
   gas properties, as appropriate to the route.
3. Obtain conversion yields with their exact denominator and standard conditions.
   Convert VS-fed yields to VS-destroyed yields when required.
4. Reconcile gross and net efficiencies, LHV versus HHV, power rating and operating
   availability with the generator boundary used here.
5. Account explicitly for pumps, preparation, gas cleaning, compression and other
   electrical consumers. Set heat demand and temperature-compatible heat recovery.
6. Compare measured fuel, gross electricity, recovered heat, auxiliary use and net
   electricity separately. Matching only net electricity can hide compensating errors.
7. Use independent observations for validation. Record parameter sources and their
   uncertainty; examine sensitivity and correlated inputs before interpreting
   Monte Carlo quantiles.

## Extension boundaries

Detailed reactor kinetics, chemical equilibrium, tar/contaminant handling,
part-load efficiency curves, storage dispatch, transient startup, product mass
balances and emissions require additional models. Add each as an explicit module
with its own boundary and reference cases rather than embedding undocumented
corrections in the existing recovery factors.
