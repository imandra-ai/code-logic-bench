from enum import Enum
from dataclasses import dataclass


class SystemMode(Enum):
    """Enumeration of possible system operating modes."""

    NORMAL = "normal"
    DEBRIS_AVOIDANCE = "debris_avoidance"
    POWER_SAVE = "power_save"


class LinkStatus(Enum):
    """Enumeration of communication link statuses."""

    ACTIVE = "active"
    DEGRADED = "degraded"
    LOST = "lost"


@dataclass
class ManeuverDecision:
    """Represents the decision outcome for a satellite maneuver request."""

    approved: bool
    use_electric: bool
    use_chemical: bool
    use_rcs: bool
    requires_ground_approval: bool


def _categorize_battery(battery_pct: float) -> int:
    """
    Categorize battery level into discrete levels.

    Args:
        battery_pct: Battery percentage (0-100)

    Returns:
        Battery level: 3 (Full), 2 (Good), 1 (Low), 0 (Critical)
    """
    if battery_pct >= 75:
        return 3  # Full
    elif battery_pct >= 50:
        return 2  # Good
    elif battery_pct >= 25:
        return 1  # Low
    else:
        return 0  # Critical


def _is_emergency_maneuver(mode: SystemMode) -> bool:
    """Check if the current mode requires emergency maneuvering."""
    return mode == SystemMode.DEBRIS_AVOIDANCE


def _needs_ground_approval(link_status: LinkStatus, fuel_pct: float) -> bool:
    """
    Determine if ground approval is required based on link status and fuel.

    Args:
        link_status: Current communication link status
        fuel_pct: Remaining fuel percentage

    Returns:
        True if ground approval is needed
    """
    return (
        link_status == LinkStatus.LOST or link_status == LinkStatus.DEGRADED
    ) and fuel_pct < 20


def determine_maneuver_approval(
    mode: SystemMode,
    battery_pct: float,
    link_status: LinkStatus,
    fuel_remaining_pct: float,
) -> ManeuverDecision:
    """
    Determine whether to approve a satellite orbital maneuver and select thrusters.

    The system evaluates the current operating mode, battery level, communication
    link status, and fuel reserves to make maneuver decisions. Emergency debris
    avoidance maneuvers are always approved with RCS thrusters. Otherwise, thruster
    selection depends on battery level: electric for full battery, chemical for
    good battery, and RCS for low battery. Critical battery levels reject maneuvers.

    Args:
        mode: Current system operating mode
        battery_pct: Battery charge percentage (0-100)
        link_status: Communication link status
        fuel_remaining_pct: Remaining fuel percentage (0-100)

    Returns:
        ManeuverDecision with approval status and thruster selection
    """
    emergency = _is_emergency_maneuver(mode)

    if emergency:
        # Emergency: always use RCS
        needs_approval = _needs_ground_approval(link_status, fuel_remaining_pct)
        return ManeuverDecision(
            approved=True,
            use_electric=False,
            use_chemical=False,
            use_rcs=True,
            requires_ground_approval=needs_approval,
        )

    battery_level = _categorize_battery(battery_pct)

    if battery_level == 0:
        # Critical battery: reject
        return ManeuverDecision(
            approved=False,
            use_electric=False,
            use_chemical=False,
            use_rcs=False,
            requires_ground_approval=False,
        )
    elif battery_level >= 3:
        # Full battery: use Electric (most efficient)
        needs_approval = _needs_ground_approval(link_status, fuel_remaining_pct)
        return ManeuverDecision(
            approved=True,
            use_electric=True,
            use_chemical=False,
            use_rcs=False,
            requires_ground_approval=needs_approval,
        )
    elif battery_level >= 2:
        # Good battery: use Chemical
        needs_approval = _needs_ground_approval(link_status, fuel_remaining_pct)
        return ManeuverDecision(
            approved=True,
            use_electric=False,
            use_chemical=True,
            use_rcs=False,
            requires_ground_approval=needs_approval,
        )
    else:
        # Low battery: use RCS
        needs_approval = _needs_ground_approval(link_status, fuel_remaining_pct)
        return ManeuverDecision(
            approved=True,
            use_electric=False,
            use_chemical=False,
            use_rcs=True,
            requires_ground_approval=needs_approval,
        )
