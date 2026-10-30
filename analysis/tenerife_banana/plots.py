"""Optional Matplotlib figures shared by the analysis runner and gallery."""

from typing import Any

from matplotlib.figure import Figure

from x2power.models import PowerResult, SimulationResult
from x2power.utilities.plotting import plot_energy_balance


def energy_figure(result: dict[str, Any]) -> Figure:
    """Annual electric and thermal ledgers, with an explicit screening title."""
    return plot_energy_balance(
        SimulationResult("bmp_digestion", PowerResult(**result["annual_power_totals"]), {}),
        title="Banana pseudostem screening: annual electricity and heat (kWh)",
    )


def operation_figure(result: dict[str, Any]) -> Figure:
    """Daily electricity flow with negative outage imports retained."""
    fig = Figure(figsize=(10, 4), layout="constrained")
    ax = fig.subplots()
    rows = result["daily_results"]
    days = [r["day"] for r in rows]
    net = [r["net_electricity_kwh"] for r in rows]
    ax.plot(
        days, [r["gross_electricity_kwh"] for r in rows], label="Gross generation", color="#2f6fdb"
    )
    ax.plot(days, net, label="Net after plant loads", color="#16866b")
    ax.fill_between(
        days, net, 0, where=[v < 0 for v in net], color="#c84b4b", alpha=0.25, label="Grid imports"
    )
    ax.axhline(0, color="0.4", linewidth=0.8)
    ax.set(
        xlabel="Day in representative 365-day year",
        ylabel="Electricity (kWh/day)",
        title="Assumed steady methane production; two 15-day CHP shutdowns",
    )
    ax.legend(loc="lower left", ncols=3, fontsize=9)
    ax.grid(alpha=0.2)
    return fig


def cost_figure(result: dict[str, Any]) -> Figure:
    """Compare annual benefits with itemized operating costs (CAPEX excluded)."""
    fig = Figure(figsize=(10, 5), layout="constrained")
    ax = fig.subplots()
    items = [(k, v, "#16866b") for k, v in result["annual_benefits_eur"].items()]
    items += [(k, -v, "#c84b4b") for k, v in result["annual_costs_eur"].items()]
    labels = [k.replace("_", " ").capitalize() for k, _, _ in items]
    ax.barh(labels, [v / 1000 for _, v, _ in items], color=[c for _, _, c in items])
    ax.axvline(0, color="0.3", linewidth=1)
    ax.invert_yaxis()
    ax.set(
        xlabel="Constant 2026 EUR thousands/year; benefits + / costs −",
        title="Assumed annual operating ledger; excludes investment and replacements",
    )
    ax.grid(axis="x", alpha=0.2)
    return fig


def cash_flow_figure(result: dict[str, Any]) -> Figure:
    """Full project cumulative balances, including replacement and closure costs."""
    fig = Figure(figsize=(9, 4), layout="constrained")
    ax = fig.subplots()
    rows = result["cost_benefit"]["cash_flows"]
    years = [r["year"] for r in rows]
    ax.plot(
        years,
        [r["cumulative_cash_flow"] / 1e6 for r in rows],
        marker="o",
        markersize=3,
        label="Undiscounted",
    )
    rate = result["inputs"]["assumptions"]["real_discount_rate"]
    ax.plot(
        years,
        [r["discounted_cumulative_cash_flow"] / 1e6 for r in rows],
        marker="o",
        markersize=3,
        label=f"Discounted at {rate:.0%} real",
    )
    ax.axhline(0, color="0.3", linewidth=1)
    ax.set(
        xlabel="Project year (0 = initial investment)",
        ylabel="Cumulative cash flow (EUR millions)",
        title="Unlevered, pre-tax screening cash flows",
    )
    ax.legend()
    ax.grid(alpha=0.2)
    return fig


def sensitivity_figure(sensitivity: dict[str, Any]) -> Figure:
    """NPV dependence on delivered-electricity value and a hypothetical gate fee."""
    rows = sensitivity["electricity_value_gate_fee"]
    prices = sorted({r["delivered_electricity_value_eur_per_kwh"] for r in rows})
    fees = sorted({r["gate_fee_eur_per_tonne"] for r in rows})
    lookup = {
        (r["gate_fee_eur_per_tonne"], r["delivered_electricity_value_eur_per_kwh"]): r[
            "net_present_value_eur"
        ]
        / 1e6
        for r in rows
    }
    z = [[lookup[(fee, price)] for price in prices] for fee in fees]
    fig = Figure(figsize=(9, 5), layout="constrained")
    ax = fig.subplots()
    extent = max(abs(value) for row in z for value in row) or 1
    mesh = ax.pcolormesh(prices, fees, z, shading="nearest", cmap="RdBu", vmin=-extent, vmax=extent)
    flat = [v for row in z for v in row]
    if min(flat) < 0 < max(flat):
        contour = ax.contour(prices, fees, z, levels=[0], colors=["black"], linewidths=1.5)
        ax.clabel(contour, fmt={0: "NPV = 0"}, inline=True)
    fig.colorbar(mesh, ax=ax, label="NPV (EUR millions)")
    ax.set(
        xlabel="Value of delivered electricity (EUR/kWh)",
        ylabel="Hypothetical gate fee (EUR/t of feed)",
        title=f"{sensitivity['horizon_years']}-year NPV sensitivity; hypothetical gate fees",
    )
    return fig
