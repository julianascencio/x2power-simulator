# X2Power

**Feedstock-to-electricity simulation in Python.**

X2Power models combustion, gasification, pyrolysis, anaerobic digestion, organic
wastewater and biogas generation. It exposes the assumptions behind gross and net
electricity, process heat, auxiliary loads, generator capacity and availability.

## AI-generated content

Most of the code, examples and documentation in this repository are AI-generated,
based on specific, real scientific and technical literature selected by the
repository developers. The developers guide source selection, implementation,
review and validation.

## Start here

- **[User guide](user_guide/index.md):** install the package and run a first simulation.
- **[Example gallery](gallery/index.rst):** execute worked examples and inspect their figures.
- **[API reference](reference/index.rst):** explore inputs, methods and utilities generated from Python code.
- **[Model equations](models.md):** understand energy boundaries, units and physical limitations.

**[Continuous biogas plants](biogas_plants.md):** mixed feeds, substrate inventories,
gas storage, CHP outages, process heat and grid imports/exports.

## What can you simulate?

| Input | Method | Main outputs |
| --- | --- | --- |
| Biomass or plastic | Combustion, gasification or pyrolysis | Selected fuel energy, drying duty, electricity and heat |
| Food waste or sludge | Volatile-solids digestion | Methane production, capture and electricity |
| Organic wastewater | Removed-COD methane yield | COD removal, biogas and electricity |
| Biogas | Methane-fraction generator model | Gross/net electricity and usable heat |

The simulation core uses the Python standard library. Optional Matplotlib support
provides electricity/heat breakdowns, operating profiles, sensitivity curves and
uncertainty figures.

![Synthetic gasification moisture sensitivity](figures/moisture_sensitivity.svg)

## Explicit assumptions

These are reduced-order, interval-based models with constant efficiencies.
Bundled inputs are synthetic and require calibration. Negative net electricity is
retained: it represents an external electrical requirement. The energy residual
checks the generator boundary, not a complete upstream reactor balance.

See [validation guidance](validation.md) before interpreting numerical output as a
prediction for specific equipment.

```{toctree}
:maxdepth: 2
:hidden:

user_guide/index
gallery/index
reference/index
development
```
