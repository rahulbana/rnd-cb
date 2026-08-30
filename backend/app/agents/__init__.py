"""Specialised travel agents and their registry."""
from __future__ import annotations

from .activity import ActivityAgent
from .base import AgentContext, BaseAgent
from .budget import BudgetAgent
from .destination import DestinationAgent
from .flight import FlightAgent
from .food import FoodAgent
from .hotel import HotelAgent
from .itinerary import ItineraryAgent
from .local_guide import LocalGuideAgent
from .packing import PackingAgent
from .safety import SafetyAgent
from .transportation import TransportationAgent
from .visa import VisaAgent
from .weather_agent import WeatherAgent

# Instantiated once; agents are stateless.
ALL_AGENTS: dict[str, BaseAgent] = {
    a.name: a
    for a in (
        DestinationAgent(),
        FlightAgent(),
        HotelAgent(),
        ActivityAgent(),
        FoodAgent(),
        WeatherAgent(),
        ItineraryAgent(),
        TransportationAgent(),
        BudgetAgent(),
        VisaAgent(),
        SafetyAgent(),
        PackingAgent(),
        LocalGuideAgent(),
    )
}


def get_agent(name: str) -> BaseAgent:
    return ALL_AGENTS[name]


__all__ = ["ALL_AGENTS", "AgentContext", "BaseAgent", "get_agent"]
