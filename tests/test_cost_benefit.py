"""Independent arithmetic, time conventions, undefined metrics and imports."""

import pytest

from x2power.methods.cost_benefit import (
    AnnualCashFlow,
    break_even_unit_value,
    evaluate_cost_benefit,
    net_present_value,
    payback_period,
    value_electricity,
)


def test_discounted_ledger_independent_arithmetic():
    flows = [
        AnnualCashFlow(0, costs=100),
        AnnualCashFlow(1, 10, 70, 100),
        AnnualCashFlow(2, 20, 90, 80),
    ]
    result = evaluate_cost_benefit(flows, 0.1)
    costs = 100 + 10 / 1.1 + 20 / 1.21
    benefits = 70 / 1.1 + 90 / 1.21
    energy = 100 / 1.1 + 80 / 1.21
    assert result.net_present_value == pytest.approx(benefits - costs)
    assert result.present_value_costs == pytest.approx(costs)
    assert result.present_value_benefits == pytest.approx(benefits)
    assert result.levelized_cost_per_kwh == pytest.approx(costs / energy)
    assert result.benefit_cost_ratio == pytest.approx(benefits / costs)
    assert result.simple_payback_years == pytest.approx(1 + 40 / 70)
    assert result.discounted_payback_years == pytest.approx(1 + (100 - 60 / 1.1) / (70 / 1.21))
    assert result.cash_flows[-1]["discounted_cumulative_cash_flow"] == pytest.approx(
        result.net_present_value
    )
    assert result.to_dict()["net_present_value"] == result.net_present_value
    assert net_present_value([-100, 60, 70], 0.1) == pytest.approx(result.net_present_value)


def test_undefined_metrics_and_no_investment():
    result = evaluate_cost_benefit([AnnualCashFlow(0), AnnualCashFlow(1)], 0)
    assert result.levelized_cost_per_kwh is None
    assert result.benefit_cost_ratio is None
    assert result.simple_payback_years == 0
    assert payback_period([-100, 0, 20]) is None
    assert payback_period([-100, 50, 50]) == 2
    assert break_even_unit_value(100, 20, 0) is None
    assert break_even_unit_value(100, 120, 10) == -2
    assert net_present_value([-100, 50, 50], 0) == 0


def test_replacement_costs_and_first_crossing_are_explicit():
    flows = [AnnualCashFlow(0, 100), AnnualCashFlow(1, benefits=110), AnnualCashFlow(2, costs=200)]
    result = evaluate_cost_benefit(flows, 0)
    assert result.simple_payback_years == pytest.approx(100 / 110)
    assert result.net_present_value == -190
    assert result.cash_flows[-1]["cumulative_cash_flow"] == -190


def test_imports_never_net_against_export_revenue():
    values = value_electricity(
        1000,
        200,
        self_consumption_fraction=0.25,
        avoided_purchase_price_per_kwh=0.2,
        export_price_per_kwh=0.07,
        import_price_per_kwh=0.3,
    )
    assert values == {
        "self_consumed_kwh": 250,
        "exported_kwh": 750,
        "imported_kwh": 200,
        "avoided_purchase_value": 50,
        "export_revenue": pytest.approx(52.5),
        "import_cost": 60,
    }
    assert break_even_unit_value(1000, 200, 400) == 2


@pytest.mark.parametrize("value", [True, -1, float("nan"), float("inf"), "10"])
def test_reject_invalid_money_and_rates(value):
    with pytest.raises(ValueError):
        AnnualCashFlow(1, costs=value)
    with pytest.raises(ValueError):
        evaluate_cost_benefit([AnnualCashFlow(0)], value)
    with pytest.raises(ValueError):
        break_even_unit_value(value, 0, 1)


@pytest.mark.parametrize("year", [True, -1, 1.5, "1"])
def test_invalid_year(year):
    with pytest.raises(ValueError):
        AnnualCashFlow(year)


@pytest.mark.parametrize("flows", [[], [AnnualCashFlow(1)], [AnnualCashFlow(0), AnnualCashFlow(2)]])
def test_missing_or_nonconsecutive_years(flows):
    with pytest.raises(ValueError):
        evaluate_cost_benefit(flows, 0.08)


def test_invalid_net_flows_and_valuation():
    with pytest.raises(ValueError):
        net_present_value([], 0)
    with pytest.raises(ValueError):
        net_present_value([1, float("nan")], 0)
    with pytest.raises(ValueError):
        value_electricity(
            100,
            0,
            self_consumption_fraction=1.1,
            avoided_purchase_price_per_kwh=0,
            export_price_per_kwh=0,
            import_price_per_kwh=0,
        )
