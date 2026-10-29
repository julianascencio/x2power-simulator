from pathlib import Path

import pytest

from x2power.utilities.io import load_scenario

SCENARIOS = Path(__file__).parents[1] / "use_cases/scenarios"


@pytest.fixture
def biogas_config():
    return load_scenario(SCENARIOS / "biogas_engine.json")
