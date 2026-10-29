import pytest

from x2power.methods import BiogasStream, CODProcess, DigestionProcess, ThermalProcess
from x2power.methods.generation import generate_power
from x2power.models import AuxiliaryLoads, Generator, SolidFeedstock
from x2power.scenario import run_scenario


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, True, "12"])
def test_invalid_feed_mass(bad):
    with pytest.raises(ValueError):
        SolidFeedstock(bad, 0.2, 18)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Generator(0),
        lambda: Generator(0.6, 0.5),
        lambda: Generator(0.3, rated_power_kw=-1),
        lambda: SolidFeedstock(1, 1.01, 10),
        lambda: BiogasStream(1, 0),
        lambda: DigestionProcess(1, 1.1, 0.5),
        lambda: CODProcess(-0.1, 0.3),
        lambda: AuxiliaryLoads(electric_heater_efficiency=0),
        lambda: AuxiliaryLoads(process_heat_usable_fraction=2),
        lambda: ThermalProcess("unknown", 0.5, 1),
        lambda: generate_power(1, Generator(0.3), duration_h=0),
        lambda: generate_power(1, Generator(0.3), availability=1.1),
    ],
)
def test_invalid_physical_parameters(factory):
    with pytest.raises(ValueError):
        factory()


@pytest.mark.parametrize(
    "key,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("route", "unknown"),
        ("generator", []),
        ("availability", "0.5"),
        ("typo", 1),
    ],
)
def test_scenario_schema_rejects_invalid_inputs(biogas_config, key, value):
    biogas_config[key] = value
    with pytest.raises(ValueError):
        run_scenario(biogas_config)


def test_unknown_nested_parameters_fail(biogas_config):
    biogas_config["generator"]["efficency"] = 0.5
    with pytest.raises(ValueError, match="generator"):
        run_scenario(biogas_config)


@pytest.mark.parametrize("process", [[], {"typo": 1}])
def test_unknown_biogas_process_fails(biogas_config, process):
    biogas_config["process"] = process
    with pytest.raises(ValueError):
        run_scenario(biogas_config)


def test_numeric_overflow_fails_explicitly():
    with pytest.raises(ValueError, match="finite"):
        SolidFeedstock(10**400, 0, 18)
    with pytest.raises(ValueError, match="finite"):
        generate_power(
            1, Generator(0.3), duration_h=1e308, auxiliaries=AuxiliaryLoads(fixed_power_kw=1e308)
        )
