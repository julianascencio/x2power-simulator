"""Independent reactor solutions and plant-wide conservation/dispatch checks."""

from dataclasses import asdict, replace
from math import exp
from pathlib import Path

import pytest

from x2power import Generator
from x2power.methods.biogas_plant import (
    BiogasPlant,
    ContinuousDigester,
    DigesterFeedstock,
    PlantInterval,
    PlantState,
    initial_plant_state,
    simulate_biogas_plant,
)
from x2power.utilities.biogas_plant import plant_from_config, plant_profile_rows, summarize_plant
from x2power.utilities.io import load_scenario, write_json


@pytest.fixture
def plant():
    # Q=1 m3/day, D=.01/day; input 100 degradable + 100 inert kg VS/day.
    # At equilibrium: Mdeg=1000, Minert=10000, destroyed=90 kg VS/day.
    feed = DigesterFeedstock("test_feed", 1000, 0.2, 1, 0.5, 0.5, 0.09)
    return BiogasPlant(
        (feed,),
        ContinuousDigester(100),
        Generator(0.4, 0.4, 100),
        capture_fraction=1,
        methane_lhv_kwh_per_nm3=10,
    )


def point(hours=24, **kwargs):
    return PlantInterval(hours, feed_temperature_c=37, ambient_temperature_c=37, **kwargs)


def test_steady_state_independent_arithmetic(plant):
    state = initial_plant_state(plant)
    assert state.degradable_vs_kg == pytest.approx((1000,))
    assert state.inert_vs_kg == pytest.approx((10000,))
    result = simulate_biogas_plant(plant, [point()])[0]
    m = result.metrics
    assert m["hydraulic_retention_days"] == 100
    assert m["organic_loading_kg_vs_m3_day"] == 2
    assert m["volatile_solids_destroyed_kg"] == pytest.approx(90)
    assert m["effluent_volatile_solids_kg"] == pytest.approx(110)
    assert m["methane_produced_nm3"] == pytest.approx(45)
    assert result.power.gross_electricity_kwh == pytest.approx(180)
    assert result.power.recovered_heat_kwh == pytest.approx(180)
    assert result.state.degradable_vs_kg == pytest.approx(state.degradable_vs_kg)
    assert result.state.inert_vs_kg == pytest.approx(state.inert_vs_kg)


def test_feed_interruption_retains_methane_production(plant):
    initial = initial_plant_state(plant)
    result = simulate_biogas_plant(plant, [point(feed_multipliers=(0,))], initial_state=initial)[0]
    destroyed = 1000 * (1 - exp(-0.09))
    assert result.metrics["volatile_solids_destroyed_kg"] == pytest.approx(destroyed)
    assert result.metrics["methane_produced_nm3"] == pytest.approx(destroyed * 0.5)
    assert result.metrics["effluent_volatile_solids_kg"] == 0
    assert result.metrics["hydraulic_retention_days"] is None
    assert result.state.inert_vs_kg == initial.inert_vs_kg
    assert result.state.degradable_vs_kg[0] == pytest.approx(1000 * exp(-0.09))


def test_empty_inventory_exact_cstr_solution(plant):
    result = simulate_biogas_plant(
        plant, [point()], initial_state=initial_plant_state(plant, steady_state=False)
    )[0]
    inventory = 1000 * (1 - exp(-0.1))
    destroyed = 0.09 * (1000 - 10000 * (1 - exp(-0.1)))
    assert result.state.degradable_vs_kg[0] == pytest.approx(inventory)
    assert result.metrics["volatile_solids_destroyed_kg"] == pytest.approx(destroyed)
    assert result.metrics["vs_balance_residual_kg"] == pytest.approx(0, abs=1e-10)


def test_outage_storage_capacity_and_release(plant):
    plant = replace(plant, gas_storage_capacity_nm3=50)
    results = simulate_biogas_plant(plant, [point(generator_availability=0), point()])
    # 75 Nm3/day captured: store 50 and flare 25; following day burn 75 + 50.
    assert results[0].state.stored_biogas_nm3 == pytest.approx(50)
    assert results[0].metrics["biogas_flared_nm3"] == pytest.approx(25)
    assert results[0].power.gross_electricity_kwh == 0
    assert results[1].metrics["biogas_to_chp_nm3"] == pytest.approx(125)
    assert results[1].power.gross_electricity_kwh == pytest.approx(300)
    assert results[1].state.stored_biogas_nm3 == pytest.approx(0)


def test_heating_parasitics_grid_and_useful_heat(plant):
    plant = replace(
        plant,
        digester=replace(plant.digester, heat_loss_kw_per_k=1),
        fixed_auxiliary_power_kw=1,
        mixing_power_w_per_m3=10,
        feed_preparation_kwh_per_tonne=2,
        gas_treatment_kwh_per_nm3=0.1,
        electric_heater_efficiency=0.5,
    )
    interval = PlantInterval(
        24,
        feed_temperature_c=17,
        ambient_temperature_c=27,
        site_electricity_demand_kw=10,
        site_heat_demand_kw=5,
    )
    result = simulate_biogas_plant(plant, [interval])[0]
    heat = 1000 * 4.18 * 20 / 3600 + 10 * 24
    auxiliaries = 2 * 24 + 2 + 75 * 0.1
    heater = (heat - 180) / 0.5
    assert result.power.process_heat_demand_kwh == pytest.approx(heat)
    assert result.power.auxiliary_electricity_kwh == pytest.approx(auxiliaries)
    assert result.power.electric_heating_kwh == pytest.approx(heater)
    assert result.metrics["grid_import_kwh"] == pytest.approx(240 - 180 + auxiliaries + heater)
    assert result.metrics["grid_export_kwh"] == 0
    assert result.metrics["unserved_site_heat_kwh"] == 120
    warm = simulate_biogas_plant(plant, [point(site_heat_demand_kw=2)])[0]
    assert warm.metrics["heat_delivered_to_site_kwh"] == pytest.approx(48)
    assert warm.metrics["rejected_heat_kwh"] == pytest.approx(132)


@pytest.mark.parametrize("hours", [1e-8, 0.5, 24, 2400])
@pytest.mark.parametrize("availability", [0, 0.3, 1])
def test_all_ledgers_and_bounds(plant, hours, availability):
    plant = replace(
        plant, gas_storage_capacity_nm3=30, capture_fraction=0.9, generator=Generator(0.4, 0.4, 5)
    )
    initial = initial_plant_state(plant, stored_biogas_nm3=12)
    result = simulate_biogas_plant(
        plant,
        [point(hours, generator_availability=availability, site_electricity_demand_kw=1)],
        initial_state=initial,
    )[0]
    m, p = result.metrics, result.power
    assert m["vs_balance_residual_kg"] == pytest.approx(0, abs=1e-8)
    assert m["gas_balance_residual_nm3"] == pytest.approx(0, abs=1e-8)
    assert 0 <= result.state.stored_biogas_nm3 <= 30
    assert p.gross_electricity_kwh <= 5 * hours * availability + 1e-8
    assert p.balance_residual_kwh == pytest.approx(0, abs=1e-8)
    assert p.net_electricity_kwh + m["grid_import_kwh"] == pytest.approx(
        m["site_electricity_demand_kwh"] + m["grid_export_kwh"]
    )
    assert p.recovered_heat_kwh == pytest.approx(
        p.heat_to_process_kwh + m["heat_delivered_to_site_kwh"] + m["rejected_heat_kwh"]
    )
    assert m["methane_not_captured_nm3"] == pytest.approx(m["methane_produced_nm3"] * 0.1)


def test_restart_and_subdivision(plant):
    schedule = [point(2), point(5, feed_multipliers=(0.3,)), point(3)]
    results = simulate_biogas_plant(plant, schedule)
    restarted = simulate_biogas_plant(plant, schedule[1:], initial_state=results[0].state)
    assert restarted == results[1:]
    cold = initial_plant_state(plant, steady_state=False)
    daily = simulate_biogas_plant(plant, [point()], initial_state=cold)
    hourly = simulate_biogas_plant(plant, [point(1)] * 24, initial_state=cold)
    assert daily[0].state.degradable_vs_kg == pytest.approx(hourly[-1].state.degradable_vs_kg)
    assert summarize_plant(daily)["methane_produced_nm3"] == pytest.approx(
        summarize_plant(hourly)["methane_produced_nm3"]
    )


def test_zero_rates_and_zero_feed(plant):
    feed = replace(plant.feedstocks[0], decay_rate_per_day=0)
    plant = replace(plant, feedstocks=(feed,))
    result = simulate_biogas_plant(plant, [point()])[0]
    assert result.metrics["methane_produced_nm3"] == 0
    assert result.metrics["effluent_volatile_solids_kg"] == pytest.approx(200)
    stopped = simulate_biogas_plant(
        plant, [point(feed_multipliers=(0,))], initial_state=result.state
    )[0]
    assert stopped.state == result.state
    assert initial_plant_state(plant, interval=point(feed_multipliers=(0,))).inert_vs_kg == (0,)


def test_diagnostics_and_summary(plant):
    plant = replace(
        plant, digester=replace(plant.digester, minimum_hrt_days=101, maximum_olr_kg_vs_m3_day=1)
    )
    results = simulate_biogas_plant(plant, [point(2), point(3)])
    assert results[0].flags == ("hrt_below_configured_minimum", "olr_above_configured_maximum")
    rows = plant_profile_rows(results)
    assert [r["end_h"] for r in rows] == [2, 5]
    summary = summarize_plant(results)
    assert summary["mean_net_power_kw"] == pytest.approx(7.5)
    assert "hydraulic_retention_days" not in summary
    with pytest.raises(ValueError):
        summarize_plant([])


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), -1, "10"])
def test_invalid_numeric_inputs(plant, bad):
    with pytest.raises(ValueError):
        replace(plant.feedstocks[0], wet_mass_kg_per_day=bad)
    with pytest.raises(ValueError):
        replace(plant, gas_storage_capacity_nm3=bad)
    with pytest.raises(ValueError):
        PlantInterval(duration_h=bad)


def test_invalid_configuration_and_states(plant):
    invalid_plants = [
        dict(feedstocks=()),
        dict(feedstocks=plant.feedstocks * 2),
        dict(generator=Generator(0.4)),
        dict(methane_fraction=0),
        dict(feedstocks=(replace(plant.feedstocks[0], dry_lhv_mj_per_kg=1),)),
    ]
    for changes in invalid_plants:
        with pytest.raises(ValueError):
            replace(plant, **changes)
    for action in (
        lambda: replace(plant.feedstocks[0], name=""),
        lambda: ContinuousDigester(0),
        lambda: PlantInterval(feed_multipliers=[]),
        lambda: PlantState(("a",), (), ()),
        lambda: PlantState(("a",), [-1], (0,)),
        lambda: initial_plant_state(plant, stored_biogas_nm3=1),
        lambda: simulate_biogas_plant(plant, []),
        lambda: simulate_biogas_plant(plant, [point(feed_multipliers=(1, 2))]),
        lambda: simulate_biogas_plant(
            plant, [point()], initial_state=PlantState(("b",), (0,), (0,))
        ),
        lambda: simulate_biogas_plant(
            plant, [point()], initial_state=replace(initial_plant_state(plant), stored_biogas_nm3=1)
        ),
    ):
        with pytest.raises(ValueError):
            action()


def test_configs_and_json_export(tmp_path, plant):
    paths = Path(__file__).parents[1].joinpath("use_cases/plants").glob("*.json")
    for path in paths:
        config = load_scenario(path)
        configured = plant_from_config(config)
        result = simulate_biogas_plant(configured, [point()])[0]
        assert result.power.gross_electricity_kwh > 0
        write_json(result.to_dict(), tmp_path / path.name)
    config = dict(schema_version=1, model="continuous_biogas_plant", plant=asdict(plant))
    assert plant_from_config(config) == plant
    for bad in (
        {**config, "schema_version": True},
        {**config, "extra": 1},
        {**config, "plant": {}},
        {**config, "plant": {"feedstocks": [{}]}},
    ):
        with pytest.raises(ValueError):
            plant_from_config(bad)


def test_plot_uses_powers_and_boundary_inventories(plant, tmp_path):
    from x2power.utilities.plant_plotting import plot_biogas_plant
    from x2power.utilities.plotting import save_figure

    plant = replace(plant, gas_storage_capacity_nm3=50)
    results = simulate_biogas_plant(plant, [point(2, generator_availability=0), point(3)])
    figure = plot_biogas_plant(results)
    assert list(figure.axes[2].lines[0].get_xdata()) == [0, 2, 5]
    assert list(figure.axes[2].lines[0].get_ydata()) == pytest.approx([0, 6.25, 0])
    assert list(figure.axes[0].patches[0].get_data().values) == pytest.approx([3.125, 3.125])
    save_figure(figure, tmp_path / "plant.png")
    assert (tmp_path / "plant.png").stat().st_size > 1000
    with pytest.raises(ValueError):
        plot_biogas_plant([])
