from copy import deepcopy
from pathlib import Path
import pytest
from symmetrylab.schemas import read_json

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def case_factory():
    def load(name="T01"):
        return deepcopy(read_json(ROOT / "benchmarks/golden" / (name + ".json")))
    return load
