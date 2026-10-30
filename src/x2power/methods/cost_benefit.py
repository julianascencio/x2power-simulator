"""Annual discounted cash-flow screening in one consistent currency/price basis.

Year zero is the initial investment; subsequent flows occur at year end. This is
an unlevered, pre-tax calculation, not a tax, financing or electricity-bill model.
Use a real discount rate with constant-price inputs, or nominal rates with nominal
flows. Benefits and costs are separate nonnegative amounts, avoiding hidden credits.
"""

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from math import fsum
from typing import Any

from x2power.utilities.validation import fraction, number


@dataclass(frozen=True)
class AnnualCashFlow:
    """One year's costs, benefits and electricity delivered outside plant loads.

    All monetary amounts use the same currency. Electricity excludes plant imports
    and internal consumption. Include import purchases in costs. No cost allocation
    to heat or other co-products is implied by the electricity denominator.
    """

    year: int
    costs: float = 0.0
    benefits: float = 0.0
    delivered_electricity_kwh: float = 0.0

    def __post_init__(self) -> None:
        if isinstance(self.year, bool) or not isinstance(self.year, int) or self.year < 0:
            raise ValueError("year must be a nonnegative integer")
        for key in ("costs", "benefits", "delivered_electricity_kwh"):
            number(key, getattr(self, key))


@dataclass(frozen=True)
class CostBenefitResult:
    """Discounted metrics; undefined ratios and unreached paybacks are None.

    LCOE is gross lifecycle cost divided by discounted delivered electricity, with
    no subtraction of gate fees, grants or other benefits. BCR includes all stated
    benefits and costs; describe the project perspective before interpreting it.
    """

    net_present_value: float
    present_value_costs: float
    present_value_benefits: float
    discounted_delivered_electricity_kwh: float
    benefit_cost_ratio: float | None
    levelized_cost_per_kwh: float | None
    simple_payback_years: float | None
    discounted_payback_years: float | None
    cash_flows: tuple[dict[str, float | int], ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rate(discount_rate: float) -> None:
    # Negative discount rates are outside this screening API's scope.
    number("discount_rate", discount_rate)


def net_present_value(cash_flows: Sequence[float], discount_rate: float) -> float:
    """Discount signed, consecutive yearly net flows, starting at year zero."""
    _rate(discount_rate)
    if not cash_flows:
        raise ValueError("Supply at least one cash flow")
    for value in cash_flows:
        number("cash_flow", value, minimum=float("-inf"))
    return fsum(value * (1 / (1 + discount_rate)) ** year for year, value in enumerate(cash_flows))


def payback_period(cash_flows: Sequence[float], discount_rate: float = 0.0) -> float | None:
    """First cumulative recovery, with linear within-year interpolation.

    This interpolation is an approximation to the year-end ledger. A later cost
    can make the cumulative balance negative again; payback is not a viability test.
    Returns zero when no initial deficit exists, and None if recovery is not reached.
    """
    net_present_value(cash_flows, discount_rate)  # validate all entries and rate
    cumulative = cash_flows[0]
    if cumulative >= 0:
        return 0.0
    for year, value in enumerate(cash_flows[1:], start=1):
        discounted = value * (1 / (1 + discount_rate)) ** year
        if cumulative + discounted >= 0:
            return year - 1 + (-cumulative / discounted)
        cumulative += discounted
    return None


def break_even_unit_value(
    present_value_costs: float,
    present_value_other_benefits: float,
    discounted_quantity: float,
) -> float | None:
    """Constant unit value making NPV zero; negative values are retained.

    Quantity and other benefits must cover the same years and discount rate as
    costs. Returns None for zero quantity. This solves an arithmetic threshold,
    not evidence that a buyer or waste supplier will pay that value.
    """
    for name, value in (
        ("present_value_costs", present_value_costs),
        ("present_value_other_benefits", present_value_other_benefits),
        ("discounted_quantity", discounted_quantity),
    ):
        number(name, value)
    return (
        (present_value_costs - present_value_other_benefits) / discounted_quantity
        if discounted_quantity
        else None
    )


def value_electricity(
    delivered_kwh: float,
    imported_kwh: float,
    *,
    self_consumption_fraction: float,
    avoided_purchase_price_per_kwh: float,
    export_price_per_kwh: float,
    import_price_per_kwh: float,
) -> dict[str, float]:
    """Value separate delivered and imported energy without annual net metering.

    The self-consumption fraction applies only to delivered positive energy after
    plant loads. Establish it from coincident external demand; it is an assumption
    when no interval demand exists. Demand charges, fixed bills and taxes are absent.
    """
    for name, value in (
        ("delivered_kwh", delivered_kwh),
        ("imported_kwh", imported_kwh),
        ("avoided_purchase_price_per_kwh", avoided_purchase_price_per_kwh),
        ("export_price_per_kwh", export_price_per_kwh),
        ("import_price_per_kwh", import_price_per_kwh),
    ):
        number(name, value)
    fraction("self_consumption_fraction", self_consumption_fraction)
    consumed = delivered_kwh * self_consumption_fraction
    exported = delivered_kwh - consumed
    return {
        "self_consumed_kwh": consumed,
        "exported_kwh": exported,
        "imported_kwh": imported_kwh,
        "avoided_purchase_value": consumed * avoided_purchase_price_per_kwh,
        "export_revenue": exported * export_price_per_kwh,
        "import_cost": imported_kwh * import_price_per_kwh,
    }


def evaluate_cost_benefit(
    annual_flows: Sequence[AnnualCashFlow], discount_rate: float
) -> CostBenefitResult:
    """Calculate NPV, BCR, gross LCOE and paybacks from an explicit yearly ledger."""
    _rate(discount_rate)
    if not annual_flows or [f.year for f in annual_flows] != list(range(len(annual_flows))):
        raise ValueError("Cash flows must have consecutive years starting at zero")
    rows = []
    cumulative = discounted_cumulative = 0.0
    for flow in annual_flows:
        factor = (1 / (1 + discount_rate)) ** flow.year
        net = flow.benefits - flow.costs
        cumulative += net
        discounted_cumulative += net * factor
        rows.append(
            {
                **asdict(flow),
                "net_cash_flow": net,
                "discount_factor": factor,
                "discounted_costs": flow.costs * factor,
                "discounted_benefits": flow.benefits * factor,
                "discounted_electricity_kwh": flow.delivered_electricity_kwh * factor,
                "cumulative_cash_flow": cumulative,
                "discounted_cumulative_cash_flow": discounted_cumulative,
            }
        )
    costs = fsum(row["discounted_costs"] for row in rows)
    benefits = fsum(row["discounted_benefits"] for row in rows)
    electricity = fsum(row["discounted_electricity_kwh"] for row in rows)
    net_flows = [row["net_cash_flow"] for row in rows]
    return CostBenefitResult(
        net_present_value=benefits - costs,
        present_value_costs=costs,
        present_value_benefits=benefits,
        discounted_delivered_electricity_kwh=electricity,
        benefit_cost_ratio=benefits / costs if costs else None,
        levelized_cost_per_kwh=costs / electricity if electricity else None,
        simple_payback_years=payback_period(net_flows),
        discounted_payback_years=payback_period(net_flows, discount_rate),
        cash_flows=tuple(rows),
    )
