"""Tool registry and tool tests (spec section 20)."""
import pytest

from app.schemas.common import DataTrust
from app.tools import build_default_registry


@pytest.fixture()
def registry():
    return build_default_registry()


@pytest.mark.asyncio
async def test_geocode_known_city(registry):
    res = await registry.execute("geocode", query="Tokyo")
    assert res.ok
    assert round(res.data["lat"]) == 36
    assert res.trust is DataTrust.VERIFIED


@pytest.mark.asyncio
async def test_geocode_unknown(registry):
    res = await registry.execute("geocode", query="Atlantis")
    assert not res.ok


@pytest.mark.asyncio
async def test_currency_conversion(registry):
    res = await registry.execute("currency", amount=100, from_currency="USD", to_currency="INR")
    assert res.ok
    assert res.data["converted"] > 100  # INR weaker than USD
    assert res.trust is DataTrust.ESTIMATED


@pytest.mark.asyncio
async def test_flight_estimate_labelled_estimated(registry):
    res = await registry.execute("flight_search", origin="Delhi", destination="Tokyo", travelers=2)
    assert res.ok
    assert res.data["duration_hours"] > 0
    assert res.trust is DataTrust.ESTIMATED  # never presented as live


@pytest.mark.asyncio
async def test_unknown_tool_returns_error_not_raise(registry):
    res = await registry.execute("nope")
    assert not res.ok and res.error


@pytest.mark.asyncio
async def test_weather_is_estimated_offline(registry):
    res = await registry.execute("weather", destination="Paris", month=1)
    assert res.ok
    assert res.data["season"] == "winter"
    assert res.trust is DataTrust.ESTIMATED
