from enum import Enum
from typing import NamedTuple


class VesselType(Enum):
    """Types of vessels in the maritime traffic system."""

    CARGO = "cargo"
    PASSENGER = "passenger"
    EMERGENCY = "emergency"
    MILITARY = "military"


class WeatherCondition(Enum):
    """Weather conditions affecting vessel traffic."""

    CLEAR = "clear"
    FOG = "fog"
    STORM = "storm"


class EntryDecision(Enum):
    """Possible decisions for vessel lane entry."""

    APPROVED = "approved"
    DELAYED = "delayed"
    DENIED = "denied"


def emergency_override(vessel_type: VesselType, visibility: int) -> bool:
    """
    Emergency vessels can bypass capacity limits if visibility is above critical threshold (200m).

    Args:
        vessel_type: Type of the vessel
        visibility: Current visibility in meters

    Returns:
        True if emergency override conditions are met
    """
    return vessel_type == VesselType.EMERGENCY and visibility > 200


def weather_capacity_reduction(weather: WeatherCondition) -> int:
    """
    Calculate capacity reduction based on weather severity.

    Args:
        weather: Current weather condition

    Returns:
        Number of vessels to reduce from maximum capacity
    """
    if weather == WeatherCondition.CLEAR:
        return 0
    elif weather == WeatherCondition.FOG:
        return 1
    elif weather == WeatherCondition.STORM:
        return 2
    return 0


def weather_speed_limit(weather: WeatherCondition, base_limit: int) -> int:
    """
    Adjust speed limit based on weather conditions.

    Args:
        weather: Current weather condition
        base_limit: Base speed limit

    Returns:
        Adjusted speed limit
    """
    if weather == WeatherCondition.CLEAR:
        return base_limit
    elif weather == WeatherCondition.FOG:
        return (base_limit * 60) // 100  # 60% of base
    elif weather == WeatherCondition.STORM:
        return (base_limit * 40) // 100  # 40% of base
    return base_limit


def in_visibility_dead_zone(visibility: int, weather: WeatherCondition) -> bool:
    """
    Check if visibility is in the dead zone (450-550m during fog).

    This represents borderline fog conditions where safety is unclear.

    Args:
        visibility: Current visibility in meters
        weather: Current weather condition

    Returns:
        True if in visibility dead zone
    """
    return weather == WeatherCondition.FOG and 450 <= visibility <= 550


def vessel_priority_score(vessel_type: VesselType) -> int:
    """
    Calculate priority score by vessel type.

    Args:
        vessel_type: Type of the vessel

    Returns:
        Priority score (higher is more priority)
    """
    if vessel_type == VesselType.EMERGENCY:
        return 4
    elif vessel_type == VesselType.MILITARY:
        return 3
    elif vessel_type == VesselType.PASSENGER:
        return 2
    elif vessel_type == VesselType.CARGO:
        return 1
    return 0


def calculate_entry_score(
    capacity_ok: bool,
    speed_compliant: bool,
    priority_sufficient: bool,
    fuel_adequate: bool,
    spacing_ok: bool,
) -> int:
    """
    Calculate entry score based on 5 conditions. Entry approval needs 3 out of 5.

    Args:
        capacity_ok: Whether capacity constraint is satisfied
        speed_compliant: Whether speed is within limits
        priority_sufficient: Whether vessel priority is sufficient
        fuel_adequate: Whether fuel level is adequate
        spacing_ok: Whether spacing requirements are met

    Returns:
        Number of conditions satisfied (0-5)
    """
    count = sum(
        [capacity_ok, speed_compliant, priority_sufficient, fuel_adequate, spacing_ok]
    )
    return count


def determine_lane_entry(
    vessel_type: VesselType,
    vessel_speed: int,
    vessel_priority: int,
    fuel_level: int,
    current_vessel_count: int,
    max_capacity: int,
    speed_limit: int,
    weather: WeatherCondition,
    visibility: int,
) -> EntryDecision:
    """
    Determine whether to approve, delay, or deny vessel entry into shipping lanes.

    The decision is based on vessel characteristics, lane state, and environmental conditions.
    Implements emergency override, weather-dependent adjustments, visibility dead zones,
    and quorum-based entry approval.

    Args:
        vessel_type: Type of the vessel
        vessel_speed: Current speed of the vessel
        vessel_priority: Priority level of the vessel
        fuel_level: Current fuel level percentage
        current_vessel_count: Number of vessels currently in lane
        max_capacity: Maximum lane capacity
        speed_limit: Base speed limit for the lane
        weather: Current weather condition
        visibility: Current visibility in meters

    Returns:
        Entry decision (Approved, Delayed, or Denied)
    """
    # Check visibility dead zone first
    if in_visibility_dead_zone(visibility, weather):
        # Dead zone → delay for visibility improvement
        return EntryDecision.DELAYED

    # Check emergency override
    if emergency_override(vessel_type, visibility):
        # Emergency bypasses normal checks
        return EntryDecision.APPROVED

    # Normal entry logic with quorum

    # Check individual conditions
    weather_reduction = weather_capacity_reduction(weather)
    effective_capacity = max_capacity - weather_reduction
    capacity_ok = current_vessel_count < effective_capacity

    adjusted_limit = weather_speed_limit(weather, speed_limit)
    speed_ok = vessel_speed <= adjusted_limit

    priority_score = vessel_priority_score(vessel_type)
    priority_ok = vessel_priority >= priority_score

    fuel_ok = fuel_level >= 30

    # Spacing check - simplified as good visibility
    spacing_ok = visibility >= 500

    # Calculate entry score (quorum)
    score = calculate_entry_score(
        capacity_ok, speed_ok, priority_ok, fuel_ok, spacing_ok
    )

    # Need 3 out of 5 for approval
    if score >= 3:
        return EntryDecision.APPROVED
    elif score >= 2:
        return EntryDecision.DELAYED  # Borderline cases
    else:
        return EntryDecision.DENIED
