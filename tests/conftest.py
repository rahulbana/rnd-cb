import json
from importlib import resources

import pytest


@pytest.fixture
def sample_payload():
    resource = (
        resources.files("product_intel")
        .joinpath("fixtures")
        .joinpath("acousticpro_headphones.json")
    )
    with resource.open("r", encoding="utf-8") as fh:
        return json.load(fh)
