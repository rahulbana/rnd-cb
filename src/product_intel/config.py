"""Tunable knowledge bases and thresholds for the pipeline.

Centralizing the topic taxonomy, defect taxonomy and scoring weights keeps the
agents generic: point the pipeline at a different product category by editing the
keyword maps here, no agent code changes required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence


# Functional dimensions reviews get clustered into (Agent 2).
# Order matters: earlier topics win ties.
TOPIC_KEYWORDS: Dict[str, Sequence[str]] = {
    "Noise Cancellation": ["anc", "noise", "cancellation", "cancelling", "quiet", "isolation", "subway", "ambient"],
    "Connectivity": ["bluetooth", "pairing", "pair", "multipoint", "connection", "connect", "disconnect", "stutter", "latency", "range"],
    "Battery Performance": ["battery", "charge", "charging", "playtime", "drain", "hours", "usb-c", "power"],
    "Ergonomics & Comfort": ["comfort", "comfortable", "fit", "cushion", "cushions", "clamp", "ear", "headband", "weight", "heat", "sweaty", "padding"],
    "Sound Quality": ["sound", "audio", "bass", "treble", "mids", "clarity", "eq", "muddy", "tinny", "soundstage"],
    "Software & App": ["app", "firmware", "update", "software", "equalizer", "bug", "crash", "settings"],
    "Build & Durability": ["build", "durable", "durability", "hinge", "creak", "flimsy", "sturdy", "material", "plastic", "broke"],
    "Call Quality": ["call", "calls", "mic", "microphone", "voice"],
}

DEFAULT_TOPIC = "General Feedback"

# Reviews about these get filtered out of product sentiment (courier / packaging).
IRRELEVANT_KEYWORDS: Sequence[str] = [
    "courier", "delivery", "shipping", "shipped", "package was", "packaging",
    "arrived damaged", "box was", "seller", "postman", "fedex", "ups ", "dhl",
    "customs", "late arrival", "transit",
]

# Maps advertised marketing feature phrases to the cluster they belong to
# (Agent 3). Keyed by lowercase substrings found in the advertised feature text.
FEATURE_TO_CLUSTER_HINTS: Dict[str, str] = {
    "noise": "Noise Cancellation",
    "anc": "Noise Cancellation",
    "bluetooth": "Connectivity",
    "multipoint": "Connectivity",
    "pairing": "Connectivity",
    "battery": "Battery Performance",
    "playtime": "Battery Performance",
    "charge": "Battery Performance",
    "comfort": "Ergonomics & Comfort",
    "cushion": "Ergonomics & Comfort",
    "ergonomic": "Ergonomics & Comfort",
    "sound": "Sound Quality",
    "audio": "Sound Quality",
    "bass": "Sound Quality",
    "hi-res": "Sound Quality",
    "app": "Software & App",
    "firmware": "Software & App",
    "eq": "Software & App",
    "call": "Call Quality",
    "mic": "Call Quality",
}


@dataclass
class DefectPattern:
    """A defect taxonomy entry (Agent 4)."""

    signature: str  # canonical short label used for dedup
    title: str
    category: str  # one of DefectCategory values
    keywords: Sequence[str]
    cluster: str


# Standardized defect taxonomy. Frequency/severity are computed from the data;
# this table only supplies detection patterns + classification.
DEFECT_PATTERNS: List[DefectPattern] = [
    DefectPattern("bt_multipoint", "Bluetooth multipoint handoff disconnects",
                  "Functional Blocker",
                  ["multipoint", "switching", "handoff", "stutter", "disconnect", "drop"],
                  "Connectivity"),
    DefectPattern("bt_pairing", "Bluetooth pairing failures",
                  "Functional Blocker",
                  ["won't pair", "can't pair", "pairing fail", "not pairing", "pairing issue"],
                  "Connectivity"),
    DefectPattern("battery_drain", "Excessive battery drain",
                  "Functional Blocker",
                  ["battery drain", "drains", "dies fast", "dead in", "poor battery", "battery life"],
                  "Battery Performance"),
    DefectPattern("app_crash", "Companion app crashes",
                  "Functional Blocker",
                  ["app crash", "app crashes", "crashing", "app freezes", "app bug"],
                  "Software & App"),
    DefectPattern("firmware_bug", "Firmware update instability",
                  "Functional Blocker",
                  ["firmware", "bricked", "after update", "update broke"],
                  "Software & App"),
    DefectPattern("ear_heat", "Ear cushions trap heat",
                  "Usability Inconvenience",
                  ["heat", "hot", "sweaty", "sweat", "warm ears"],
                  "Ergonomics & Comfort"),
    DefectPattern("clamp_force", "Excessive clamping force / discomfort",
                  "Usability Inconvenience",
                  ["clamp", "tight", "too tight", "headache", "pressure", "uncomfortable"],
                  "Ergonomics & Comfort"),
    DefectPattern("mic_quality", "Poor call microphone quality",
                  "Usability Inconvenience",
                  ["mic", "microphone", "muffled", "can't hear me", "voice quality"],
                  "Call Quality"),
    DefectPattern("build_creak", "Hinge/frame creaking",
                  "Aesthetic/Cosmetic",
                  ["creak", "creaks", "squeak", "hinge", "rattle"],
                  "Build & Durability"),
    DefectPattern("finish_scratch", "Finish scratches easily",
                  "Aesthetic/Cosmetic",
                  ["scratch", "scratches", "scuff", "fingerprints", "paint"],
                  "Build & Durability"),
]


@dataclass
class ScoringWeights:
    """Weights used by Agent 4 severity and Agent 5 RICE synthesis."""

    # severity = w_freq * frequency_ratio + w_rating * low_rating_ratio + w_cat * category_weight
    severity_freq: float = 0.4
    severity_rating: float = 0.35
    severity_category: float = 0.25
    category_weight: Dict[str, float] = field(default_factory=lambda: {
        "Functional Blocker": 1.0,
        "Usability Inconvenience": 0.6,
        "Aesthetic/Cosmetic": 0.3,
    })
    # Priority cutoffs on the RICE score. Reach here is expressed as a
    # percentage of reviewers (0-100), so RICE magnitudes are single/low-double
    # digits; these cutoffs are calibrated to that scale, not to absolute-count
    # reach. Retune if you switch reach to an absolute audience size.
    p0_cutoff: float = 10.0
    p1_cutoff: float = 5.0


DEFAULT_WEIGHTS = ScoringWeights()
