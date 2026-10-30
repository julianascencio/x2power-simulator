"""Optional Matplotlib figures for continuous biogas-plant ledgers."""

from collections.abc import Sequence

from x2power.methods.biogas_plant import PlantResult


def plot_biogas_plant(results: Sequence[PlantResult], *, title: str = "Biogas plant"):
    """Plot interval-average flows/powers and gas inventory at interval boundaries.

    Storage is an inventory; the other panels show rates, not interval totals.
    Import is positive in the electrical panel and reported separately from net power.
    """
    from matplotlib.figure import Figure

    if not results:
        raise ValueError("Cannot plot an empty plant simulation")
    edges = [0.0]
    for result in results:
        edges.append(edges[-1] + result.power.duration_h)
    figure = Figure(figsize=(11, 10), layout="constrained")
    axes = figure.subplots(4, 1, sharex=True)
    series = (
        ("biogas_captured_nm3", "Captured", "#2f6fdb"),
        ("biogas_to_chp_nm3", "CHP", "#008577"),
        ("biogas_flared_nm3", "Flare", "#d97706"),
    )
    for key, label, color in series:
        values = [float(r.metrics[key] or 0) / r.power.duration_h for r in results]
        axes[0].stairs(values, edges, label=label, color=color)
    axes[0].set_ylabel("Biogas (Nm³/h)")
    axes[1].stairs([r.power.net_power_kw for r in results], edges, label="Plant net electricity")
    for key, label in (("grid_export_kwh", "Grid export"), ("grid_import_kwh", "Grid import")):
        axes[1].stairs(
            [float(r.metrics[key] or 0) / r.power.duration_h for r in results], edges, label=label
        )
    axes[1].set_ylabel("Electricity (kW)")
    inventory = [float(results[0].metrics["initial_stored_biogas_nm3"] or 0)]
    inventory.extend(r.state.stored_biogas_nm3 for r in results)
    axes[2].plot(edges, inventory, label="Gas holder", color="#008577")
    axes[2].set_ylabel("Stored biogas (Nm³)")
    for key, label in (
        ("recovered_heat_kwh", "CHP recovered heat"),
        ("process_heat_demand_kwh", "Digester heat demand"),
        ("electric_heating_kwh", "Backup heater electricity"),
    ):
        axes[3].stairs(
            [getattr(r.power, key) / r.power.duration_h for r in results], edges, label=label
        )
    axes[3].set_ylabel("Heat / input power (kW)")
    axes[3].set_xlabel("Elapsed time (h)")
    for axis in axes:
        axis.legend(loc="upper left", ncol=3, fontsize=8)
        axis.grid(alpha=0.2)
    figure.suptitle(title)
    return figure
