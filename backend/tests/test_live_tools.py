"""Live-API integration logic, verified with mocked HTTP responses.

These tests prove each tool parses real API payloads and labels them LIVE,
without making any network call.
"""
import pytest

from app.config.settings import Settings
from app.schemas.common import DataTrust
from app.tools import currency, flights, geocode, places, search, weather


def _live_settings(**overrides) -> Settings:
    base = dict(enable_live_data=True)
    base.update(overrides)
    return Settings(**base)


@pytest.mark.asyncio
async def test_geocode_live_parses_open_meteo(monkeypatch):
    async def fake_get_json(url, **kw):
        return {"results": [{"latitude": 35.0116, "longitude": 135.7681,
                             "name": "Kyoto", "country": "Japan", "timezone": "Asia/Tokyo"}]}
    monkeypatch.setattr(geocode, "get_settings", _live_settings)
    monkeypatch.setattr(geocode, "get_json", fake_get_json)

    res = await geocode.GeocodeTool().run(query="Kyoto")
    assert res.ok and res.trust is DataTrust.LIVE and res.source == "open-meteo"
    assert round(res.data["lat"], 2) == 35.01
    assert res.data["country"] == "Japan"


@pytest.mark.asyncio
async def test_currency_live_parses_frankfurter(monkeypatch):
    async def fake_get_json(url, **kw):
        return {"amount": 1.0, "base": "USD", "rates": {"INR": 83.42}}
    monkeypatch.setattr(currency, "get_settings", _live_settings)
    monkeypatch.setattr(currency, "get_json", fake_get_json)

    res = await currency.CurrencyTool().run(amount=100, from_currency="USD", to_currency="INR")
    assert res.ok and res.trust is DataTrust.LIVE and res.source == "frankfurter/ecb"
    assert res.data["converted"] == 8342.0


@pytest.mark.asyncio
async def test_weather_live_archive(monkeypatch):
    async def fake_resolve(q):
        return {"lat": 48.85, "lng": 2.35, "timezone": "Europe/Paris", "source": "open-meteo"}
    async def fake_get_json(url, **kw):
        return {"daily": {"temperature_2m_max": [12, 14, 16],
                          "temperature_2m_min": [5, 6, 7],
                          "precipitation_probability_max": [40, 50, 60]}}
    monkeypatch.setattr(weather, "get_settings", _live_settings)
    monkeypatch.setattr(weather, "resolve_coords", fake_resolve)
    monkeypatch.setattr(weather, "get_json", fake_get_json)

    # A far-future month -> archive path -> trust RECENT.
    res = await weather.WeatherTool().run(destination="Paris", month=1)
    assert res.ok and res.trust in (DataTrust.LIVE, DataTrust.RECENT)
    assert res.data["typical_high_c"] == 14.0 and res.data["typical_low_c"] == 6.0
    assert res.data["rain_probability"] == "moderate"


@pytest.mark.asyncio
async def test_flights_live_amadeus(monkeypatch):
    settings = _live_settings(amadeus_client_id="id", amadeus_client_secret="sec")
    monkeypatch.setattr(flights, "get_settings", lambda: settings)

    async def fake_post_json(url, **kw):
        return {"access_token": "tok", "expires_in": 1799}
    async def fake_get_json(url, **kw):
        if "reference-data/locations" in url:
            kw_params = kw.get("params", {})
            code = "DEL" if kw_params.get("keyword") == "Delhi" else "NRT"
            return {"data": [{"iataCode": code}]}
        if "flight-offers" in url:
            return {"data": [{
                "price": {"total": "540.00", "currency": "USD"},
                "itineraries": [{"duration": "PT7H35M",
                                 "segments": [{"carrierCode": "AI"}]}],
            }]}
        return None
    monkeypatch.setattr(flights, "post_json", fake_post_json)
    monkeypatch.setattr(flights, "get_json", fake_get_json)
    flights._token.update({"value": None, "expires_at": 0.0})

    res = await flights.FlightSearchTool().run(
        origin="Delhi", destination="Tokyo", travelers=2,
        departure_date="2026-10-05", currency="USD")
    assert res.ok and res.trust is DataTrust.LIVE and res.source == "amadeus"
    assert res.data["mode"] == "live"
    assert res.data["cheapest_price"]["amount"] == 540.0


@pytest.mark.asyncio
async def test_flights_estimate_uses_real_geocoding(monkeypatch):
    # No amadeus creds -> estimate path, but coordinates come from (mocked) geocoding.
    monkeypatch.setattr(flights, "get_settings", _live_settings)

    async def fake_resolve(q):
        return {"Delhi": {"lat": 28.61, "lng": 77.20},
                "Tokyo": {"lat": 35.67, "lng": 139.65}}[q]
    monkeypatch.setattr(flights, "resolve_coords", fake_resolve)

    res = await flights.FlightSearchTool().run(origin="Delhi", destination="Tokyo", travelers=1)
    assert res.ok and res.data["mode"] == "estimate"
    assert res.trust is DataTrust.ESTIMATED
    assert 5000 < res.data["distance_km"] < 7000  # real Delhi-Tokyo ~5850 km


@pytest.mark.asyncio
async def test_search_live_tavily(monkeypatch):
    monkeypatch.setattr(search, "get_settings", lambda: _live_settings(tavily_api_key="t"))

    async def fake_post_json(url, **kw):
        return {"results": [{"title": "Kyoto guide", "url": "https://x", "content": "..."}],
                "answer": "Kyoto is great."}
    monkeypatch.setattr(search, "post_json", fake_post_json)

    res = await search.WebSearchTool().run(query="things to do in Kyoto")
    assert res.ok and res.trust is DataTrust.LIVE and res.source == "tavily"
    assert res.data["results"][0]["title"] == "Kyoto guide"


@pytest.mark.asyncio
async def test_places_live_opentripmap(monkeypatch):
    monkeypatch.setattr(places, "get_settings", lambda: _live_settings(opentripmap_api_key="k"))

    async def fake_resolve(q):
        return {"lat": 35.01, "lng": 135.76, "timezone": "Asia/Tokyo"}
    async def fake_get_json(url, **kw):
        return [{"name": "Kinkaku-ji", "kinds": "cultural,historic",
                 "point": {"lat": 35.03, "lon": 135.72}, "xid": "X1"},
                {"name": "", "point": {"lat": 0, "lon": 0}}]  # blank name filtered out
    monkeypatch.setattr(places, "resolve_coords", fake_resolve)
    monkeypatch.setattr(places, "get_json", fake_get_json)

    res = await places.PlacesTool().run(destination="Kyoto", kind="attractions")
    assert res.ok and res.trust is DataTrust.LIVE
    assert len(res.data["places"]) == 1
    assert res.data["places"][0]["name"] == "Kinkaku-ji"
