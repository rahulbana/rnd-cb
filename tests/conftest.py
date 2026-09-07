import json
from importlib import resources

import pytest


@pytest.fixture
def sample_payload():
    with resources.files("product_intel.fixtures").joinpath(
        "acousticpro_headphones.json"
    ).open("r", encoding="utf-8") as fh:
        return json.load(fh)
