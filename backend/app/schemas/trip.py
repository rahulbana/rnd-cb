"""Trip domain schemas.

``TripState`` (section 10) is the single structured object every agent reads
from and writes into. It is deliberately explicit rather than an unstructured
conversation blob.
"""
from __future__ import annotations

from datetime import date as _date, datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from .common import (
    DataPoint,
    GeoPoint,
    Money,
    Recommendation,
    TravelStyle,
    TravelerType,
)


class UserPreferences(BaseModel):
    """Section 11 — personalisation inputs."""

    travel_style: TravelStyle = TravelStyle.COMFORT
    interests: list[str] = Field(default_factory=list)
    dietary: list[str] = Field(default_factory=list)  # vegetarian, vegan, halal...
    preferred_airlines: list[str] = Field(default_factory=list)
    walking_tolerance: str = "moderate"  # low | moderate | high
    adventure_level: str = "moderate"
    accessibility_needs: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class TripRequest(BaseModel):
    """Structured requirements extracted from a natural-language request."""

    origin: str | None = None
    destinations: list[str] = Field(default_factory=list)
    start_date: _date | None = None
    end_date: _date | None = None
    duration_days: int | None = Field(default=None, ge=1, le=90)
    travelers: int = Field(1, ge=1, le=30)
    traveler_type: TravelerType = TravelerType.SOLO
    budget: Money | None = None
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    notes: str | None = None

    @model_validator(mode="after")
    def _derive_duration(self) -> "TripRequest":
        if self.duration_days is None and self.start_date and self.end_date:
            delta = (self.end_date - self.start_date).days
            if delta > 0:
                object.__setattr__(self, "duration_days", delta)
        return self


class Place(BaseModel):
    name: str
    category: str = "attraction"  # attraction | restaurant | hotel | station | airport
    location: GeoPoint | None = None
    address: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    price_level: int | None = Field(default=None, ge=1, le=4)  # $ .. $$$$
    recommendation: Recommendation | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    est_cost: Money | None = None
    tags: list[str] = Field(default_factory=list)
    note: str | None = None


class ItineraryItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    start_time: str  # "HH:MM"
    title: str
    kind: str = "activity"  # activity | meal | transport | rest | checkin
    place: Place | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    est_cost: Money | None = None
    recommendation: Recommendation | None = None
    notes: str | None = None


class ItineraryDay(BaseModel):
    day: int = Field(..., ge=1)
    date: _date | None = None
    summary: str | None = None
    items: list[ItineraryItem] = Field(default_factory=list)


class BudgetLine(BaseModel):
    category: str
    minimum: Money
    comfort: Money
    premium: Money
    note: str | None = None


class BudgetBreakdown(BaseModel):
    currency: str = "USD"
    lines: list[BudgetLine] = Field(default_factory=list)
    total_minimum: Money | None = None
    total_comfort: Money | None = None
    total_premium: Money | None = None
    within_budget: bool | None = None
    advice: list[str] = Field(default_factory=list)


class TripStatus(str, Enum):
    DRAFT = "draft"
    PLANNING = "planning"
    PLANNED = "planned"
    FAILED = "failed"


class TripState(BaseModel):
    """The complete, structured state of a trip (spec section 10)."""

    trip_id: UUID = Field(default_factory=uuid4)
    user_id: UUID | None = None
    title: str = "Untitled trip"
    status: TripStatus = TripStatus.DRAFT
    request: TripRequest = Field(default_factory=TripRequest)

    # Agent-produced sections. Each is optional until its agent runs.
    destination_overview: dict[str, Any] | None = None
    flights: dict[str, Any] | None = None
    accommodation: dict[str, Any] | None = None
    itinerary: list[ItineraryDay] = Field(default_factory=list)
    transportation: dict[str, Any] | None = None
    restaurants: list[Place] = Field(default_factory=list)
    activities: list[Place] = Field(default_factory=list)
    weather: dict[str, Any] | None = None
    budget: BudgetBreakdown | None = None
    visa: dict[str, Any] | None = None
    safety: dict[str, Any] | None = None
    packing: list[str] = Field(default_factory=list)
    local_tips: dict[str, Any] | None = None

    # Provenance-tagged highlights surfaced to the UI.
    highlights: list[DataPoint[str]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)


class TripCreate(BaseModel):
    title: str | None = None
    request: TripRequest = Field(default_factory=TripRequest)


class TripSummary(BaseModel):
    trip_id: UUID
    title: str
    status: TripStatus
    destinations: list[str]
    start_date: _date | None
    duration_days: int | None
    travelers: int
    updated_at: datetime
