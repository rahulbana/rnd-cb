"""Intent detection tests (spec section 9)."""
import pytest

from app.orchestration.intent import Intent, detect_intent


@pytest.mark.parametrize("text,expected", [
    ("Plan a trip to Japan for 7 days", Intent.PLAN_TRIP),
    ("make this trip cheaper", Intent.OPTIMIZE),
    ("what's the weather like in October?", Intent.WEATHER),
    ("find me a hotel near the center", Intent.HOTEL),
    ("do I need a visa?", Intent.VISA),
    ("is it safe there?", Intent.SAFETY),
    ("what should I pack?", Intent.PACKING),
    ("best vegetarian restaurants", Intent.FOOD),
    ("how do I get around?", Intent.TRANSPORT),
])
def test_intent_detection(text, expected):
    assert detect_intent(text).intent is expected


def test_unknown_is_general_low_confidence():
    r = detect_intent("hello there")
    assert r.intent is Intent.GENERAL
    assert r.confidence < 0.5
