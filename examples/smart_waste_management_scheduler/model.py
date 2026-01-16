from enum import Enum
from typing import NamedTuple


class WasteType(Enum):
    """Types of waste that can be collected."""

    RECYCLABLE = "recyclable"
    ORGANIC = "organic"
    GENERAL = "general"
    HAZARDOUS = "hazardous"


class Weather(Enum):
    """Weather conditions affecting collection."""

    SUNNY = "sunny"
    RAINY = "rainy"
    SNOWY = "snowy"
    EXTREME = "extreme"


class TruckCapability(Enum):
    """Truck types and their collection capabilities."""

    STANDARD = "standard"
    ORGANIC_ONLY = "organic_only"
    HAZARDOUS_ONLY = "hazardous_only"
    MULTI_TYPE = "multi_type"


class CollectionDecision(NamedTuple):
    """Decision output for waste collection."""

    approved: bool
    priority_score: int
    requires_special_handling: bool
    estimated_time: int


def fill_threshold_by_waste(waste: WasteType) -> int:
    """Return the fill percentage threshold for each waste type."""
    thresholds = {
        WasteType.HAZARDOUS: 75,  # 75% - must empty sooner for safety
        WasteType.ORGANIC: 80,  # 80% - decomposition concerns
        WasteType.RECYCLABLE: 85,  # 85% - less urgent
        WasteType.GENERAL: 90,  # 90% - most tolerant
    }
    return thresholds[waste]


def weather_time_multiplier(weather: Weather) -> int:
    """Return time multiplier based on weather conditions."""
    multipliers = {
        Weather.SUNNY: 1,
        Weather.RAINY: 2,
        Weather.SNOWY: 3,
        Weather.EXTREME: 5,
    }
    return multipliers[weather]


def truck_can_collect(truck_cap: TruckCapability, waste: WasteType) -> bool:
    """Check if truck is compatible with waste type."""
    if truck_cap == TruckCapability.HAZARDOUS_ONLY:
        return waste == WasteType.HAZARDOUS
    elif truck_cap == TruckCapability.ORGANIC_ONLY:
        return waste == WasteType.ORGANIC
    elif truck_cap == TruckCapability.MULTI_TYPE:
        return True
    elif truck_cap == TruckCapability.STANDARD:
        return waste not in (WasteType.HAZARDOUS, WasteType.ORGANIC)
    return False


def is_overfilled(fill_pct: int, waste: WasteType) -> bool:
    """Check if bin is overfilled based on waste-specific threshold."""
    threshold = fill_threshold_by_waste(waste)
    return fill_pct >= threshold


def calculate_base_priority(
    fill_pct: int, waste: WasteType, days_since_empty: int
) -> int:
    """Calculate base priority score."""
    fill_component = fill_pct
    time_component = days_since_empty * 5

    waste_urgency = {
        WasteType.HAZARDOUS: 50,
        WasteType.ORGANIC: 30,
        WasteType.RECYCLABLE: 10,
        WasteType.GENERAL: 20,
    }

    return fill_component + time_component + waste_urgency[waste]


def apply_threshold_escalation(base_score: int, fill_pct: int, waste: WasteType) -> int:
    """Escalate priority if over threshold."""
    if is_overfilled(fill_pct, waste):
        return base_score * 2  # Double priority when over threshold
    return base_score


def apply_weather_penalty(score: int, weather: Weather) -> int:
    """Apply weather penalty for extreme conditions."""
    if weather == Weather.EXTREME:
        return score // 2  # Halve priority in extreme weather
    return score


def check_emergency_override(fill_pct: int, waste: WasteType) -> bool:
    """Check for emergency override: Hazardous waste at 90%+ is always priority."""
    return waste == WasteType.HAZARDOUS and fill_pct >= 90


def determine_collection_decision(
    fill_pct: int,
    waste: WasteType,
    days_since_empty: int,
    truck_cap: TruckCapability,
    weather: Weather,
    fuel_level: int,
) -> CollectionDecision:
    """
    Determine whether to collect from a bin based on multiple factors.

    Args:
        fill_pct: Current fill percentage of the bin
        waste: Type of waste in the bin
        days_since_empty: Days since the bin was last emptied
        truck_cap: Capability of the available truck
        weather: Current weather conditions
        fuel_level: Current fuel level percentage

    Returns:
        CollectionDecision with approval status, priority score,
        special handling flag, and estimated collection time
    """
    # Check truck compatibility first
    can_collect = truck_can_collect(truck_cap, waste)

    if not can_collect:
        return CollectionDecision(
            approved=False,
            priority_score=0,
            requires_special_handling=False,
            estimated_time=0,
        )

    # Check emergency override
    is_emergency = check_emergency_override(fill_pct, waste)

    if is_emergency:
        # Emergency: immediate collection
        time = 30 * weather_time_multiplier(weather)
        return CollectionDecision(
            approved=True,
            priority_score=1000,  # Maximum priority
            requires_special_handling=True,
            estimated_time=time,
        )

    # Check fuel adequacy (need at least 20% for safety margin)
    sufficient_fuel = fuel_level >= 20

    if not sufficient_fuel:
        return CollectionDecision(
            approved=False,
            priority_score=0,
            requires_special_handling=False,
            estimated_time=0,
        )

    # Normal priority calculation
    base = calculate_base_priority(fill_pct, waste, days_since_empty)
    with_threshold = apply_threshold_escalation(base, fill_pct, waste)
    final_priority = apply_weather_penalty(with_threshold, weather)

    # Approve if priority meets minimum threshold
    min_threshold = 50
    approved = final_priority >= min_threshold

    time = (45 if approved else 0) * weather_time_multiplier(weather)

    return CollectionDecision(
        approved=approved,
        priority_score=final_priority,
        requires_special_handling=(waste == WasteType.HAZARDOUS),
        estimated_time=time,
    )
