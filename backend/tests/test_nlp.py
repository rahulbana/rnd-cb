"""Unit tests for natural-language trip parsing (spec section 16)."""
from app.services.nlp import parse_trip_request


def test_parses_duration_travelers_budget_and_origin():
    req = parse_trip_request(
        "Plan an 8 day trip to Tokyo from Delhi in October with my wife, "
        "budget 2.5 lakh, we love food culture and photography"
    )
    assert req.duration_days == 8
    assert req.origin == "Delhi"
    assert "Tokyo" in req.destinations
    assert "Delhi" not in req.destinations  # origin excluded
    assert req.travelers == 2
    assert req.budget and req.budget.currency == "INR"
    assert req.budget.amount == 250000
    assert set(req.preferences.interests) >= {"food", "culture", "photography"}


def test_weekend_is_not_a_week():
    req = parse_trip_request("Weekend trip to Paris, love art and food")
    assert req.duration_days == 3
    assert "Paris" in req.destinations


def test_family_and_usd_budget():
    req = parse_trip_request("5-day family trip to New York, budget $4000")
    assert req.traveler_type.value == "family"
    assert req.travelers >= 3
    assert req.budget.currency == "USD" and req.budget.amount == 4000
    assert "New York" in req.destinations


def test_lakh_and_no_destination():
    req = parse_trip_request("I have 1.5 lakh and 8 days, where should I go?")
    assert req.budget.amount == 150000
    assert req.duration_days == 8
    assert req.destinations == []
