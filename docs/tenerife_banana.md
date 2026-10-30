# Tenerife banana residues: electricity feasibility case

This source-backed screening evaluates **5,000 wet tonnes/year of raw banana
pseudostems** in an assumed digestion/CHP project in Tenerife. It combines published
island context with adjacent-island laboratory measurements and explicit engineering
and financial assumptions. It is **not an operating plant, a contracted feed supply,
a detailed design or a supplier quotation**.

Open the [executable results gallery](gallery/plot_07_tenerife_banana.rst) for five
figures, a downloadable Python script and a notebook. The reproducible analysis is
in [`analysis/tenerife_banana/`](https://github.com/julianascencio/x2power-simulator/tree/main/analysis/tenerife_banana).

## Evidence and assumptions

| Input | Value | Status and source |
| --- | ---: | --- |
| Tenerife banana-fruit production, 2024 | 186,771 t | Published context: CES Canarias, Table 40. Not a residue inventory. |
| Raw pseudostem total solids / wet mass | 6.2% | Laboratory measurement: Durán Hernández et al., Table 3. |
| Volatile solids / total solids | 67.8% | Same raw-pseudostem sample and table. |
| Methane potential / VS fed | 0.36329 Nm³/kg VS | Blank-corrected laboratory BMP, Table 6; 0 °C and 101.325 kPa. |
| Feed quantity | 5,000 wet t/year | Selected project scale, not a supply estimate. |
| Realized fraction of laboratory BMP | 70% | Scale-up assumption; stress-tested at 50% and 90%. |
| CHP nameplate / electrical efficiency | 50 kW / 30% | Engineering assumptions; no measured part-load curve. |
| Heat recovery / methane capture | 45% / 98% | Engineering assumptions, applied separately. |
| Digester volume / temperature | 600 m³ / 37 °C | Assumptions; HRT/OLR are diagnostics, not stability criteria. |
| CHP outages | 30 days/year | Two assumed 15-day shutdowns; digestion and plant loads continue. |
| Initial investment | EUR 650,000 | Itemized assumption, not a quote. |
| Export / import electricity value | EUR 0.07 / 0.18 per kWh | Scenario assumptions, not current tariffs or contracts. |
| Analysis period / real discount rate | 20 years / 8% | Constant 2026 EUR, unlevered and pre-tax. |

The laboratory material was collected in **Gáldar, Gran Canaria**, and tested in
Madrid. Transferring these properties to Tenerife requires local sampling. The
publication's accepted manuscript distinguishes BMP from full-scale performance.
The case uses raw pseudostem values; it applies no steam-explosion enhancement and
includes neither fruit, rachis, leaves nor a co-substrate.

The production figure is a pinned **2024** context observation, not a claim to the
latest harvest data. Fruit tonnes are never converted into available residues.
No collection fraction, residue-to-fruit ratio or island-wide generation potential
is inferred. The 5,000 t/year supply remains to be established with growers.

## Physical calculation

```text
VS_fed = wet_mass * total_solids_fraction * volatile_solids_fraction_ts
CH4_potential = VS_fed * laboratory_BMP_per_VS_fed
CH4_produced = CH4_potential * realization_fraction
CH4_captured = CH4_produced * capture_fraction
```

The dedicated `BMPProcess` keeps the **VS-fed basis** distinct from the original
`DigestionProcess`, whose yield is per VS destroyed. No VS-destruction fraction is
inferred from BMP. The potential methane energy must not exceed the configured
feedstock LHV. The assumed 15 MJ/kg dry LHV is an energy plausibility bound, not a
calorimetry measurement of these samples.

The established digester supplies methane uniformly over a representative 365-day
year. Each day uses the existing generator and auxiliary model. The daily heat
demand is feed sensible heat plus vessel loss:

```text
H_feed = wet_kg_per_day * cp_kJ_per_kg_K * max(T_digester - T_feed, 0) / 3600
H_vessel = UA_kW_per_K * max(T_digester - T_ambient, 0) * 24
```

Both feed and ambient temperature are assumed to be 20 °C; this is not a weather
replay. Recovered heat meets digester duty first, with electric backup during
outages and other deficits. Mixing, fixed plant loads and shredding persist on
outage days. Additional auxiliaries are 5% of gross generation. No heat is sold.

There is no microbial startup, inhibition, nutrient-balance, storage, seasonal
supply, reactor sizing or detailed gas-cleaning model. Unused captured fuel is
reported; the case does not assume that it is stored, flared or released. An actual
installation requires a defined gas-management system. Methane emissions, carbon
savings and lifecycle environmental impacts are not calculated.

## Baseline results

These are model outputs under the stated inputs, rounded for display. The gallery
recomputes the result from the pinned JSON; committed reference outputs retain
full precision.

| Metric | Result |
| --- | ---: |
| Methane produced | 53,449 Nm³/year |
| Gross electricity | 143.36 MWh/year |
| Plant auxiliaries | 52.32 MWh/year |
| Electric backup heating | 10.15 MWh/year |
| Positive electricity delivered/exported | 94.75 MWh/year |
| Electricity imported | 13.86 MWh/year |
| Net electricity (deliveries minus imports) | **80.89 MWh/year** |
| Net electricity per wet tonne | 16.18 kWh/t |
| Annual operating cash flow | **−EUR 134,862** |
| 20-year NPV | **−EUR 1,999,062** |
| Benefit/cost ratio | 0.032 |
| Gross LCOE per delivered kWh | EUR 2.219/kWh |
| Simple and discounted payback | Not reached within 20 years |
| Total gate fee required for zero NPV | EUR 40.72/t of incoming feed |

The baseline does not support a standalone electricity-sales project under these
assumptions. The break-even fee is an arithmetic requirement, not evidence of a
payer or a waste-management contract. A different feed mix, lower shared costs or
an electricity user can change the result and must be modeled explicitly.

## Cost boundary and sensitivity

The input file itemizes receiving/shredding, digestion/civil works, gas treatment,
CHP/heat recovery, electrical connection and engineering/contingency. Operating
costs cover labour/monitoring, maintenance, insurance/administration, collection,
transport, residue handling and imported electricity. The transport rate assumes
the empty return is included; only loaded one-way tonne-km are charged. Residue
handling is a cost per incoming tonne, not a prediction of digestate mass.

Year 10 includes EUR 40,000 replacement cost and year 20 includes EUR 30,000
closure cost. The model does not include land purchase, taxes, financing, grants,
price escalation, heat/digestate/carbon sales or an avoided-disposal credit. Land,
nutrient replacement, inoculum, permitting conditions and any omitted site costs
need local verification; their omission does not strengthen feasibility.

The [cost-benefit methods](cost_benefit.md) price exports and imports separately.
The two-dimensional sensitivity varies the value of positive electricity deliveries
(EUR 0.05–0.30/kWh) and a hypothetical gate fee (EUR 0–60/t), keeping import price
and all other inputs fixed. These are deterministic stress tests, not probability
bounds or market forecasts. A further sensitivity varies BMP realization.

## Reproduce and audit

```bash
git clone https://github.com/julianascencio/x2power-simulator.git
cd x2power-simulator
python -m pip install -e '.[plots]'
python -m analysis.tenerife_banana.run --plot
```

For numeric output only, install the package without extras and omit `--plot`.
Use `--inputs path/to/inputs.json` and `--output-dir path/to/output` for variants.
The analysis is repository code, not part of the installed core wheel: run it from
the checkout. The downloadable gallery script/notebook needs that same checkout.

Outputs include the full inputs and their SHA-256 fingerprint, annual metrics,
365 daily energy rows, 21 annual cash-flow rows, both sensitivities and five PNG/SVG
figures. No network calls, credentials or random sampling are used. Source facts
are transcribed into the input file with source IDs, locators and retrieval date;
complete third-party publications are not copied into the repository.

Before progressing: measure Tenerife feed properties and collectable quantities,
verify nutrient requirements and stable digestion, measure logistics and existing
residue use, request installed-cost quotes, and validate an offtake or coincident
self-consumption profile. Model co-digestion separately instead of attributing its
potential to banana pseudostems alone.

## References

1. **CES Canarias, Informe Anual 2024**, Table 40, printed p. 86, PDF p. 88.
   [Original report](https://www.cescanarias.es/?wpdmdl=470). The table attributes
   production figures to ASPROCAN.
2. **Durán Hernández et al. (2026)**, *Methane production from the co-digestion of
   banana crop residues and the organic fraction of municipal solid waste:
   influence of steam explosion*. [DOI: 10.1186/s13068-026-02794-y](https://doi.org/10.1186/s13068-026-02794-y).
   Accepted manuscript: §2.1 and §2.3, Table 3 (PDF p. 19) and Table 6 (PDF p. 24).
3. **NREL (2020)**, *LCOE in SAM using FCR and Single Owner Financial Models*.
   [Financial convention](https://sam.nrel.gov/images/web_page_files/sam-lcoe-fcr-vs-cash-flow.pdf),
   not a source of the example's prices, costs or discount rate.
