# Cost-benefit methods

`x2power.methods.cost_benefit` evaluates explicit annual cash flows. All amounts
must share one currency and price basis. Use a real discount rate with constant
prices, or a nominal rate with nominal flows. The model is unlevered and pre-tax;
it does not calculate debt service, depreciation, tax, tariff schedules or grants.
Include any separately modeled costs and benefits in the supplied ledger.

For year `t`, costs `C_t`, benefits `B_t`, delivered electricity `E_t` and a
nonnegative discount rate `r`, the implementation calculates:

```text
PV_costs    = sum(C_t / (1 + r)**t)
PV_benefits = sum(B_t / (1 + r)**t)
NPV         = PV_benefits - PV_costs
BCR         = PV_benefits / PV_costs
gross_LCOE  = PV_costs / sum(E_t / (1 + r)**t)
break_even_unit_value = (PV_costs - PV_other_benefits) / PV_quantity
```

Year zero is immediate; later amounts occur at year end. Payback reports the first
cumulative crossing using linear interpolation within that year. Later costs may
reverse it, so examine the full cash flow and NPV. Undefined ratios and unreached
paybacks return `None`; they serialize as JSON `null`. Negative break-even values
are retained when other benefits already exceed costs. An IRR is not calculated.

LCOE includes **all stated costs**, including imported plant electricity, and
uses positive electricity delivered after internal plant loads. It subtracts no
heat revenue, gate fees or grants. It is a gross project cost intensity, not an
allocated co-product cost or necessarily an export tariff requirement. Use the
break-even function with explicitly separated other benefits for the latter.

## Example

```python
from x2power.methods import AnnualCashFlow, evaluate_cost_benefit

flows = [
    AnnualCashFlow(0, costs=100_000),
    AnnualCashFlow(1, costs=10_000, benefits=25_000, delivered_electricity_kwh=80_000),
    AnnualCashFlow(2, costs=10_000, benefits=25_000, delivered_electricity_kwh=80_000),
]
result = evaluate_cost_benefit(flows, discount_rate=0.08)
print(result.net_present_value)
```

`value_electricity()` separates positive deliveries into self-consumption and
exports and values imports independently. This avoids subtracting imported kWh
from exports before pricing them at different rates. A self-consumption fraction
needs evidence of coincident demand; a fraction applied to annual deliveries is
only an approximation. Do not also value that same electricity as export sales.

Use one project perspective consistently: a waste-treatment fee received by a
plant and the payer's avoided disposal charge must not both be claimed for the
same transfer. No environmental externality is monetized by default. A positive
BCR in this financial ledger is not a complete societal cost-benefit assessment.

The discounted cost/energy convention follows the approach explained in
[NREL's *LCOE in SAM using FCR and Single Owner Financial Models* (2020)](https://sam.nrel.gov/images/web_page_files/sam-lcoe-fcr-vs-cash-flow.pdf).
This simpler implementation does not reproduce SAM's financing or tax model.
See the [Tenerife banana analysis](tenerife_banana.md) for a fully itemized case.
