from enum import Enum
from dataclasses import dataclass


class VehicleType(Enum):
    """Types of vehicles on the highway."""

    AUTONOMOUS = "autonomous"
    HUMAN_DRIVEN = "human_driven"
    EMERGENCY_VEHICLE = "emergency_vehicle"


class Weather(Enum):
    """Weather conditions affecting merge safety."""

    CLEAR = "clear"
    RAINY = "rainy"
    ADVERSE = "adverse"


class MergeCommand(Enum):
    """Commands for merge execution."""

    EXECUTE_MERGE = "execute_merge"
    ABORT_MERGE = "abort_merge"
    EMERGENCY_BRAKE = "emergency_brake"
    ADJUST_SPEED = "adjust_speed"


@dataclass
class MergeDecision:
    """Decision output for highway merge maneuver."""

    command: MergeCommand
    safe_to_merge: bool


def _base_gap_threshold(v_type: VehicleType) -> int:
    """Return base gap threshold in meters by vehicle type."""
    thresholds = {
        VehicleType.AUTONOMOUS: 30,
        VehicleType.HUMAN_DRIVEN: 45,
        VehicleType.EMERGENCY_VEHICLE: 25,
    }
    return thresholds[v_type]


def _weather_gap_multiplier(weather: Weather) -> int:
    """Return weather multiplier (scaled by 10 for integer arithmetic)."""
    multipliers = {
        Weather.CLEAR: 10,  # 1.0x
        Weather.RAINY: 13,  # 1.3x
        Weather.ADVERSE: 17,  # 1.7x
    }
    return multipliers[weather]


def _adjusted_gap_threshold(v_type: VehicleType, weather: Weather) -> int:
    """Calculate weather-adjusted gap threshold."""
    base = _base_gap_threshold(v_type)
    multiplier = _weather_gap_multiplier(weather)
    return (base * multiplier) // 10


def _in_dead_zone(gap_size: int, closing_rate: int) -> bool:
    """Check if gap/rate combination is in ambiguous dead zone."""
    return (48 <= gap_size <= 52) and (18 <= closing_rate <= 22)


def _safety_quorum_met(
    gap_size: int, threshold: int, closing_rate: int, speed_matched: bool
) -> bool:
    """Check if 2 out of 3 safety conditions are met."""
    c1 = gap_size >= threshold
    c2 = closing_rate < 15
    c3 = speed_matched

    count = sum([c1, c2, c3])
    return count >= 2


def determine_merge_decision(
    v_type: VehicleType,
    weather: Weather,
    gap_size: int,
    closing_rate: int,
    speed_matched: bool,
    emergency_present: bool,
) -> MergeDecision:
    """
    Determine safe merging maneuver for highway entry.

    Args:
        v_type: Type of vehicle attempting to merge
        weather: Current weather conditions
        gap_size: Size of gap in highway traffic (meters)
        closing_rate: Rate at which gap is closing (m/s)
        speed_matched: Whether vehicle speed matches highway traffic
        emergency_present: Whether emergency vehicle is present in merge zone

    Returns:
        MergeDecision with command and safety flag
    """
    # Dead zone check first
    if _in_dead_zone(gap_size, closing_rate):
        return MergeDecision(command=MergeCommand.ADJUST_SPEED, safe_to_merge=False)

    threshold = _adjusted_gap_threshold(v_type, weather)

    # Critical gap check
    critical = closing_rate > 30
    if critical:
        return MergeDecision(command=MergeCommand.EMERGENCY_BRAKE, safe_to_merge=False)

    # Check safety quorum
    quorum = _safety_quorum_met(gap_size, threshold, closing_rate, speed_matched)

    # Emergency vehicles override normal merge
    if emergency_present and v_type != VehicleType.EMERGENCY_VEHICLE:
        return MergeDecision(command=MergeCommand.ABORT_MERGE, safe_to_merge=False)

    if quorum:
        # Safe to merge
        if gap_size >= threshold + 10:
            return MergeDecision(command=MergeCommand.EXECUTE_MERGE, safe_to_merge=True)
        else:
            return MergeDecision(command=MergeCommand.ADJUST_SPEED, safe_to_merge=False)
    else:
        # Quorum not met
        return MergeDecision(command=MergeCommand.ABORT_MERGE, safe_to_merge=False)
