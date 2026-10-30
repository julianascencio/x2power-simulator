# X2Power

```{raw} html
<div class="asva-branding">
  <a href="https://asvaconsulting.com">
    <img
      src="https://asvaconsulting.com/wp-content/uploads/2022/05/ASVA-1-1-scaled.jpg"
      alt="ASVA Consulting"
      width="280"
    >
  </a>
  <p>
    <strong>Created by ASVA Consulting</strong><br>
    <a href="https://asvaconsulting.com">asvaconsulting.com</a><br>
    <a href="mailto:contacto@asvaconsulting.com">contacto@asvaconsulting.com</a>
  </p>
</div>
```

**Feedstock-to-electricity simulation in Python.**

Owned, created and maintained by **ASVA Consulting**, X2Power models combustion,
gasification, pyrolysis, anaerobic digestion, organic
wastewater and biogas generation. It exposes the assumptions behind gross and net
electricity, process heat, auxiliary loads, generator capacity and availability.

## AI-assisted development and literature basis

Most of the code, documentation, examples, tests and repository scaffolding are
**AI-generated under developer direction**, based on real, specifically identified
scientific and technical literature selected by the repository developers.

Developers choose the references used to define physical assumptions, methods and
parameter conventions. AI assists with implementation, documentation, testing and
iteration around that evidence base. Developers and contributors remain responsible
for source selection, review, testing and scientific validation.

AI-generated code and explanations may contain errors or imperfect interpretations
of the selected sources. Automated tests establish numerical consistency; they do
not establish empirical accuracy. Validation is still developing. The original
route scenarios and continuous-plant presets are synthetic illustrative inputs.
Source-backed analyses separately identify published measurements, assumptions
and simulated results; cited laboratory data do not validate plant performance.

Trace assumptions through the [model references](models.md),
[biogas plant references](biogas_plants.md) and
[plastic example boundaries](plastic_to_power.md). See
[verification and calibration](validation.md) for the evidence available and the
checks needed before interpreting results as equipment predictions.

## Start here

- **[User guide](user_guide/index.md):** install the package and run a first simulation.
- **[Example gallery](gallery/index.rst):** execute worked examples and inspect their figures.
- **[API reference](reference/index.rst):** explore inputs, methods and utilities generated from Python code.
- **[Model equations](models.md):** understand energy boundaries, units and physical limitations.

**[Continuous biogas plants](biogas_plants.md):** mixed feeds, substrate inventories,
gas storage, CHP outages, process heat and grid imports/exports.

**[Plastic to electricity](plastic_to_power.md):** a worked pyrolysis example with
process heating, auxiliary consumption and generator-capacity sensitivity.

**[Tenerife banana residues](tenerife_banana.md):** source-backed electricity
screening with separate grid imports/exports, cost-benefit methods and reproducible
financial sensitivities.

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
Example assumptions require calibration. Negative net electricity is
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
