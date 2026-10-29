"""Optional Matplotlib figures built from simulation outputs, with no global GUI state."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import accumulate
from pathlib import Path
from typing import TYPE_CHECKING

from x2power.models import SimulationResult
from x2power.utilities.experiments import percentile
from x2power.utilities.validation import number

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

BLUE = "#2463a6"
TEAL = "#087f73"
ORANGE = "#d07420"
RED = "#b33a3a"
GREY = "#8c98a5"
INK = "#1c3044"


def _figure(title: str, *, height: float = 6.5) -> Figure:
    try:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
    except ImportError as exc:
        raise ImportError(
            "Plotting requires Matplotlib. Install the [plots] extra with: "
            "python -m pip install -e '.[plots]' from the repository."
        ) from exc
    figure = Figure(figsize=(11, height), layout="constrained", facecolor="white")
    FigureCanvasAgg(figure)
    figure.suptitle(title, fontsize=16, color=INK)
    return figure


def _style(axis: Axes, *, ylabel: str) -> None:
    axis.set_ylabel(ylabel)
    axis.set_axisbelow(True)
    axis.grid(axis="y", color="#e2e7ec", linewidth=0.7)
    axis.spines[["top", "right"]].set_visible(False)
    axis.axhline(0, color=INK, linewidth=0.8)


def plot_energy_balance(
    result: SimulationResult, *, title: str = "Electricity and process heat"
) -> Figure:
    """Plot signed electrical deductions and thermal heat allocation over one interval.

    The heat panel reports heat delivered, not the heater's electrical input. Unused
    recovered heat includes heat unsuitable for the specified process temperature.
    """
    power = result.power
    figure = _figure(title, height=8)
    electricity = figure.add_subplot(2, 1, 1)
    heat = figure.add_subplot(2, 1, 2)
    changes = [
        power.gross_electricity_kwh,
        -power.auxiliary_electricity_kwh,
        -power.electric_heating_kwh,
        power.net_electricity_kwh,
    ]
    starts = [0.0, changes[0], changes[0] + changes[1], 0.0]
    colors = [BLUE, GREY, ORANGE, TEAL if changes[-1] >= 0 else RED]
    bars = electricity.bar(range(4), changes, bottom=starts, color=colors, width=0.62)
    electricity.bar_label(bars, labels=[f"{value:,.1f}" for value in changes], padding=5)
    electricity.set_xticks(range(4), ["Gross", "Auxiliaries", "Electric heating", "Net"])
    electricity.set_title(
        f"{result.route} | {power.duration_h:g} h | "
        f"unused fuel: {power.unused_fuel_energy_kwh:,.1f} kWh",
        fontsize=10,
        loc="left",
    )
    electricity.use_sticky_edges = False
    electricity.margins(y=0.25)
    _style(electricity, ylabel="Electrical energy (kWh)")

    used = power.heat_to_process_kwh
    deficit = power.process_heat_demand_kwh - used
    heat.barh([0, 1], [used, used], color=TEAL, label="Recovered heat used")
    heat.barh(0, power.surplus_heat_kwh, left=used, color=GREY, label="Recovered heat not used")
    heat.barh(1, deficit, left=used, color=ORANGE, label="Heat from electric heater")
    heat.set_yticks([0, 1], ["Recovered heat", "Process demand"])
    heat.invert_yaxis()
    heat.set_xlabel("Thermal energy (kWh)")
    heat.set_xlim(left=0)
    heat.spines[["top", "right"]].set_visible(False)
    heat.grid(axis="x", color="#e2e7ec", linewidth=0.7)
    heat.set_axisbelow(True)
    heat.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncols=3, fontsize=9)
    return figure


def plot_sensitivity(
    rows: Sequence[Mapping[str, float]],
    *,
    xlabel: str = "Input value",
    title: str = "Electricity sensitivity",
) -> Figure:
    """Plot a one-variable sweep, sorting numeric x values without mutating inputs."""
    if not rows:
        raise ValueError("Supply at least one sensitivity result")
    required = ("input_value", "gross_electricity_kwh", "net_electricity_kwh")
    for row in rows:
        for key in required:
            if key not in row:
                raise ValueError(f"Missing sensitivity field: {key}")
            number(key, row[key], minimum=float("-inf"))
    ordered = sorted(rows, key=lambda row: row["input_value"])
    x = [row["input_value"] for row in ordered]
    if len(set(x)) != len(x):
        raise ValueError("Sensitivity input values must be unique")
    figure = _figure(title)
    axis = figure.add_subplot()
    axis.plot(x, [r["gross_electricity_kwh"] for r in ordered], "o--", color=BLUE, label="Gross")
    axis.plot(x, [r["net_electricity_kwh"] for r in ordered], "o-", color=TEAL, label="Net")
    axis.set_xlabel(xlabel)
    _style(axis, ylabel="Interval electricity (kWh)")
    axis.legend()
    return figure


def plot_profile(
    results: Sequence[SimulationResult], *, title: str = "Operating profile"
) -> Figure:
    """Draw interval-mean power against actual elapsed hours, including negative net output."""
    if not results:
        raise ValueError("Supply at least one profile result")
    edges = list(accumulate((r.power.duration_h for r in results), initial=0.0))
    number("profile duration", edges[-1], strict=True)
    figure = _figure(title, height=8)
    electricity = figure.add_subplot(2, 1, 1)
    heat = figure.add_subplot(2, 1, 2, sharex=electricity)
    for field, label, color in (
        ("gross_electricity_kwh", "Gross", BLUE),
        ("net_electricity_kwh", "Net", TEAL),
    ):
        values = [getattr(r.power, field) / r.power.duration_h for r in results]
        electricity.stairs(values, edges, baseline=None, color=color, label=label, linewidth=2)
    for field, label, color in (
        ("process_heat_demand_kwh", "Process demand", ORANGE),
        ("heat_to_process_kwh", "Recovered heat used", TEAL),
    ):
        values = [getattr(r.power, field) / r.power.duration_h for r in results]
        heat.stairs(
            values,
            edges,
            baseline=None,
            color=color,
            label=label,
            linewidth=2,
            linestyle="--" if field == "process_heat_demand_kwh" else "-",
            zorder=3 if field == "process_heat_demand_kwh" else 2,
        )
    _style(electricity, ylabel="Mean electrical power (kW)")
    _style(heat, ylabel="Mean thermal power (kW)")
    heat.set_xlabel("Elapsed time (h)")
    heat.set_xlim(0, edges[-1])
    if len(edges) <= 10:
        heat.set_xticks(edges)
    for axis in (electricity, heat):
        axis.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=9)
    return figure


def plot_uncertainty(
    net_electricity_kwh: Sequence[float],
    *,
    bins: int = 25,
    title: str = "Net electricity under sampled assumptions",
) -> Figure:
    """Plot sample counts and empirical quantiles, without inferring confidence intervals."""
    if not net_electricity_kwh:
        raise ValueError("Supply at least one uncertainty sample")
    if type(bins) is not int or bins <= 0:
        raise ValueError("bins must be a positive integer")
    for value in net_electricity_kwh:
        number("net_electricity_kwh", value, minimum=float("-inf"))
    figure = _figure(title)
    axis = figure.add_subplot()
    axis.hist(net_electricity_kwh, bins=bins, color=BLUE, edgecolor="white", alpha=0.85)
    for probability, color in ((0.05, ORANGE), (0.5, TEAL), (0.95, RED)):
        value = percentile(net_electricity_kwh, probability)
        axis.axvline(
            value,
            color=color,
            linestyle="--",
            linewidth=1.5,
            label=f"p{round(probability * 100):02d}: {value:,.1f} kWh",
        )
    axis.set_xlabel("Net electricity per interval (kWh)")
    axis.set_title(
        f"{len(net_electricity_kwh):,} samples; quantiles reflect input assumptions",
        fontsize=10,
        loc="left",
    )
    _style(axis, ylabel="Sample count")
    axis.legend(fontsize=9)
    return figure


def save_figure(figure: Figure, path: str | Path, *, dpi: float = 150) -> Path:
    """Save PNG, SVG or PDF, creating parent folders; return the resulting path."""
    destination = Path(path)
    suffix = destination.suffix.lower()
    if suffix not in {".png", ".svg", ".pdf"}:
        raise ValueError("Figure output must use .png, .svg or .pdf")
    number("dpi", dpi, strict=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Use stable SVG element identifiers and suppress generated timestamps.
    from matplotlib import rc_context

    metadata = {"Date": None} if suffix == ".svg" else None
    if suffix == ".pdf":
        metadata = {"CreationDate": None, "ModDate": None}
    with rc_context({"svg.hashsalt": "x2power"}):
        figure.savefig(destination, dpi=dpi, metadata=metadata)
    return destination
