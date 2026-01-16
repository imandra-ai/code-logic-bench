from enum import Enum
from typing import NamedTuple


class ManeuverType(Enum):
    """Type of spacecraft maneuver."""

    BURN = "Burn"
    COAST = "Coast"
    AEROBRAKE = "Aerobrake"


class PropulsionMode(Enum):
    """Propulsion system mode."""

    CHEMICAL = "Chemical"
    ION = "Ion"
    RCS = "RCS"
    OFF = "Off"


class NavState(Enum):
    """Navigation state of the spacecraft."""

    CRUISE = "Cruise"
    APPROACH = "Approach"
    EMERGENCY = "Emergency"


class FuelLevel(Enum):
    """Current fuel level status."""

    ABUNDANT = "Abundant"
    MODERATE = "Moderate"
    LOW = "Low"
    CRITICAL = "Critical"


class TrajectoryDecision(NamedTuple):
    """Decision output for trajectory planning."""

    maneuver: ManeuverType
    propulsion: PropulsionMode
    safe: bool


def _in_orbital_dead_zone(distance_to_target: float, velocity: float) -> bool:
    """Check if spacecraft is in orbital dead zone (distance/velocity combination)."""
    return 9800 <= distance_to_target <= 10200 and 48 <= velocity <= 52


def _fuel_level_to_propulsion(fuel_level: FuelLevel) -> PropulsionMode:
    """Map fuel level to appropriate propulsion mode."""
    mapping = {
        FuelLevel.ABUNDANT: PropulsionMode.CHEMICAL,
        FuelLevel.MODERATE: PropulsionMode.ION,
        FuelLevel.LOW: PropulsionMode.RCS,
        FuelLevel.CRITICAL: PropulsionMode.OFF,
    }
    return mapping[fuel_level]


def _safety_quorum_met(
    distance_safe: bool,
    velocity_safe: bool,
    fuel_adequate: bool,
    trajectory_clear: bool,
) -> bool:
    """Check if safety quorum is met (3 out of 4 conditions)."""
    count = sum([distance_safe, velocity_safe, fuel_adequate, trajectory_clear])
    return count >= 3


def determine_trajectory(
    nav_state: NavState,
    distance_to_target: float,
    velocity: float,
    fuel_level: FuelLevel,
    trajectory_clear: bool,
) -> TrajectoryDecision:
    """
    Determine spacecraft trajectory maneuvers based on navigation parameters.

    Handles emergency modes, orbital insertion challenges, fuel-dependent propulsion
    selection, and safety quorum checks requiring 3 out of 4 safety conditions.

    Args:
        nav_state: Current navigation state
        distance_to_target: Distance to target in units
        velocity: Current velocity
        fuel_level: Current fuel level status
        trajectory_clear: Whether trajectory is clear of obstacles

    Returns:
        TrajectoryDecision with maneuver type, propulsion mode, and safety status
    """
    # Dead zone check
    if _in_orbital_dead_zone(distance_to_target, velocity):
        return TrajectoryDecision(
            maneuver=ManeuverType.COAST, propulsion=PropulsionMode.OFF, safe=False
        )

    # Emergency state forces safe mode
    if nav_state == NavState.EMERGENCY:
        return TrajectoryDecision(
            maneuver=ManeuverType.COAST, propulsion=PropulsionMode.OFF, safe=False
        )

    # Distance-based decisions
    close = distance_to_target < 5000
    very_close = distance_to_target < 1000
    fast = velocity > 50

    if very_close and fast:
        return TrajectoryDecision(
            maneuver=ManeuverType.AEROBRAKE, propulsion=PropulsionMode.RCS, safe=False
        )

    # Check safety quorum
    distance_safe = distance_to_target > 500
    velocity_safe = velocity < 100
    fuel_adequate = fuel_level != FuelLevel.CRITICAL
    quorum = _safety_quorum_met(
        distance_safe, velocity_safe, fuel_adequate, trajectory_clear
    )

    if quorum:
        prop = _fuel_level_to_propulsion(fuel_level)
        if close:
            return TrajectoryDecision(
                maneuver=ManeuverType.BURN, propulsion=prop, safe=True
            )
        else:
            return TrajectoryDecision(
                maneuver=ManeuverType.COAST, propulsion=PropulsionMode.ION, safe=True
            )
    else:
        return TrajectoryDecision(
            maneuver=ManeuverType.COAST, propulsion=PropulsionMode.OFF, safe=False
        )
