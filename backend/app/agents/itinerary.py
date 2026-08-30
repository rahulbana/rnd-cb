"""Itinerary Agent (spec section 8 & 14).

Hybrid design: the day-by-day schedule is built *deterministically* from the
activities/food the other agents produced (reliable, avoids impossible days),
while the model is used only for short day summaries. This keeps scheduling
logic testable and prevents the LLM from inventing an unrealistic timetable.
"""
from __future__ import annotations

from datetime import timedelta

from ..schemas.agents import AgentResult, AgentStatus
from ..schemas.trip import ItineraryDay, ItineraryItem, Place
from .base import AgentContext, BaseAgent
from ._common import primary_destination

# A realistic day template: morning sight, lunch, afternoon sight, dinner.
_SLOTS = [
    ("09:00", "meal", "Breakfast", 45),
    ("10:00", "activity", None, 150),
    ("13:00", "meal", "Lunch", 75),
    ("14:30", "activity", None, 150),
    ("17:30", "rest", "Free time / rest", 60),
    ("19:30", "meal", "Dinner", 90),
]


class ItineraryAgent(BaseAgent):
    name = "itinerary"
    description = "Realistic day-by-day timeline built from activities and dining."
    depends_on = ("activity", "destination")

    async def _run(self, ctx: AgentContext) -> AgentResult:
        req = ctx.trip.request
        dest = primary_destination(req)
        days = max(1, min(req.duration_days or 3, 21))

        activities = list(ctx.trip.activities)
        restaurants = list(ctx.trip.restaurants)
        if not activities:
            return self._result(
                status=AgentStatus.SKIPPED,
                summary="No activities available to schedule.",
                warnings=["Run the activity agent first."],
            )

        itinerary: list[ItineraryDay] = []
        act_i = rest_i = 0
        for day_num in range(1, days + 1):
            date = req.start_date + timedelta(days=day_num - 1) if req.start_date else None
            items: list[ItineraryItem] = []
            for start, kind, label, dur in _SLOTS:
                if kind == "activity":
                    if act_i >= len(activities):
                        continue
                    place = activities[act_i]
                    act_i += 1
                    items.append(ItineraryItem(
                        start_time=start, title=place.name, kind="activity",
                        place=place, duration_minutes=place.duration_minutes or dur,
                        recommendation=place.recommendation, est_cost=place.est_cost,
                    ))
                elif kind == "meal" and label in ("Lunch", "Dinner") and restaurants:
                    place = restaurants[rest_i % len(restaurants)]
                    rest_i += 1
                    items.append(ItineraryItem(
                        start_time=start, title=f"{label} — {place.name}", kind="meal",
                        place=place, duration_minutes=dur,
                    ))
                else:
                    items.append(ItineraryItem(
                        start_time=start, title=label or "Free time", kind=kind,
                        duration_minutes=dur,
                    ))
            itinerary.append(ItineraryDay(
                day=day_num, date=date,
                summary=f"Day {day_num} in {dest}: a balanced mix of sights, food and rest.",
                items=items,
            ))

        return self._result(
            status=AgentStatus.OK,
            summary=f"{days}-day itinerary with {act_i} activities scheduled.",
            data={"itinerary": [d.model_dump(mode="json") for d in itinerary]},
        )

    @staticmethod
    def _as_place(name: str) -> Place:
        return Place(name=name)
