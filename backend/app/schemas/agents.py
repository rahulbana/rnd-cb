"""Structured agent I/O contracts.

Agents never return free-form text into business logic (spec section 35).
Every agent returns an :class:`AgentResult` whose ``data`` conforms to a
declared Pydantic schema, validated before it enters ``TripState``.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .common import DataPoint, Money, Recommendation


class AgentStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"        # produced results but degraded (e.g. mock data)
    SKIPPED = "skipped"
    FAILED = "failed"


class AgentResult(BaseModel):
    agent: str
    status: AgentStatus = AgentStatus.OK
    summary: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    citations: list[DataPoint[str]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    latency_ms: int | None = None
    tokens: int | None = None
    cost_usd: float | None = None
    error: str | None = None


# --- Structured payloads the LLM is asked to fill --------------------------

class DestinationOverview(BaseModel):
    destination: str
    summary: str
    best_time_to_visit: str
    ideal_duration_days: int = Field(..., ge=1, le=60)
    highlights: list[str] = Field(default_factory=list)
    hidden_gems: list[str] = Field(default_factory=list)
    neighborhoods: list[str] = Field(default_factory=list)
    local_customs: list[str] = Field(default_factory=list)


class FlightOption(BaseModel):
    airline: str
    from_airport: str
    to_airport: str
    stops: int = Field(0, ge=0)
    duration_hours: float = Field(..., ge=0)
    est_price: Money
    note: str | None = None


class HotelOption(BaseModel):
    name: str
    neighborhood: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    price_per_night: Money
    good_for: list[str] = Field(default_factory=list)
    amenities: list[str] = Field(default_factory=list)


class PlaceRec(BaseModel):
    name: str
    category: str
    why: str
    recommendation: Recommendation = Recommendation.HIGHLY_RECOMMENDED
    est_cost: Money | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    neighborhood: str | None = None


class WeatherOutlook(BaseModel):
    destination: str
    season: str
    typical_high_c: float
    typical_low_c: float
    rain_probability: str
    clothing: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class VisaInfo(BaseModel):
    destination: str
    requirement: str          # e.g. "visa required", "visa on arrival", "eTA"
    passport_validity: str
    documents: list[str] = Field(default_factory=list)
    disclaimer: str = "Verify with the official embassy/consulate before travel."


class SafetyInfo(BaseModel):
    destination: str
    overall: str
    common_scams: list[str] = Field(default_factory=list)
    emergency_numbers: dict[str, str] = Field(default_factory=dict)
    health: list[str] = Field(default_factory=list)
    caution_areas: list[str] = Field(default_factory=list)


class LocalTips(BaseModel):
    destination: str
    currency: str
    tipping: str
    etiquette: list[str] = Field(default_factory=list)
    phrases: dict[str, str] = Field(default_factory=dict)
    useful_apps: list[str] = Field(default_factory=list)
