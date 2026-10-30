# Tenerife banana pseudostems

Source-backed feasibility screening of an assumed 5,000 wet-tonne/year digestion
and electricity project. Published Tenerife production is context only; substrate
properties are a Gran Canaria laboratory proxy. No operating-plant data, contracted
feedstock or supplier quotations are claimed.

```bash
python -m pip install -e '.[plots]'
python -m analysis.tenerife_banana.run --plot
```

Run from the repository root. Omit `--plot` for the standard-library-only numeric
workflow. Optional `--inputs` and `--output-dir` arguments select a case and output
folder. Default outputs go to `results/tenerife_banana/`.

| File | Purpose |
| --- | --- |
| `inputs.json` | Pinned facts, source locators, engineering/economic assumptions and cost breakdowns |
| `case.py` | Daily simulation, energy valuation, annual cash flows and sensitivity calculations |
| `plots.py` | Shared figures for the runner and gallery |
| `run.py` | CLI and JSON/CSV/PNG/SVG export |
| `reference_results/` | Committed full-precision baseline summary, cash flows and sensitivity tables |

The baseline produces **80.89 MWh/year net**, with **EUR −2.00 million NPV** over
20 years at 8% real. This result depends on the explicit cost and performance
assumptions. Imported electricity is priced separately from deliveries. The
required EUR 40.72/t gate fee is a break-even condition, not an available contract.

See the [full method, evidence and limitations](../../docs/tenerife_banana.md),
[financial equations](../../docs/cost_benefit.md) and
[live results gallery](https://julianascencio.github.io/x2power-simulator/gallery/plot_07_tenerife_banana.html).

The JSON export records all inputs and their canonical SHA-256 fingerprint. The
reference outputs are regenerated with the same command and `--output-dir
analysis/tenerife_banana/reference_results` (omit `--plot` when refreshing the
numeric snapshot). Keep the summary, cash flows and sensitivity tables; daily
results remain a generated output to avoid storing a repeated 365-row ledger.
