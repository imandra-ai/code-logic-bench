from enum import Enum, auto
from dataclasses import dataclass
from typing import Tuple


class LightState(Enum):
    """Traffic light states"""

    RED = auto()
    YELLOW = auto()
    GREEN = auto()


class VehicleType(Enum):
    """Vehicle classification types"""

    REGULAR = auto()
    EMERGENCY = auto()
    BUS = auto()


class ActionClassification(Enum):
    """Classification of traffic light actions"""

    EMERGENCY_OVERRIDE = auto()
    PHASE_TRANSITION = auto()
    PHASE_EXTENSION = auto()
    NORMAL_TIMING = auto()
    INVALID_ACTION = auto()


@dataclass
class PhaseAction:
    """Action to be taken for the current traffic light phase"""

    new_ns_light: LightState
    new_ew_light: LightState
    phase_duration: int
    action_type: ActionClassification
    override_active: bool


def _calculate_base_duration(
    queue_size: int, pedestrian_count: int, pedestrian_wait_time: int
) -> int:
    """Calculate phase duration based on conditions"""
    base = 30
    queue_factor = min(queue_size, 10)
    ped_factor = min(pedestrian_count, 5)
    wait_factor = min(pedestrian_wait_time // 10, 10)
    return base + queue_factor + ped_factor + wait_factor


def _check_extension_conditions(
    has_bus: bool,
    has_heavy_traffic: bool,
    has_many_pedestrians: bool,
    time_remaining: int,
) -> bool:
    """Check if phase extension is needed (2 out of 3 conditions)"""
    c1 = has_bus and time_remaining < 10
    c2 = has_heavy_traffic and time_remaining < 5
    c3 = has_many_pedestrians and time_remaining < 15

    count = sum([c1, c2, c3])
    return count >= 2


def _next_light_state(
    current_ns: LightState, current_ew: LightState
) -> Tuple[LightState, LightState]:
    """Determine next light state in sequence"""
    state_map = {
        (LightState.GREEN, LightState.RED): (LightState.YELLOW, LightState.RED),
        (LightState.YELLOW, LightState.RED): (LightState.RED, LightState.RED),
        (LightState.RED, LightState.RED): (LightState.RED, LightState.GREEN),
        (LightState.RED, LightState.GREEN): (LightState.RED, LightState.YELLOW),
        (LightState.RED, LightState.YELLOW): (LightState.GREEN, LightState.RED),
    }
    # Safety fallback
    return state_map.get((current_ns, current_ew), (LightState.RED, LightState.RED))


def _is_valid_state(time_remaining: int, queue_size: int, has_emergency: bool) -> bool:
    """Validity check for state"""
    # Dead zone: time_remaining 1-3 with queue_size 4-6 and no emergency creates ambiguous state
    in_dead_zone = (
        1 <= time_remaining <= 3 and 4 <= queue_size <= 6 and not has_emergency
    )

    # Also invalid if time is negative or queue size is negative
    invalid_data = time_remaining < 0 or queue_size < 0

    return not (in_dead_zone or invalid_data)


def determine_phase_action(
    current_ns_light: LightState,
    current_ew_light: LightState,
    time_remaining: int,
    queue_size: int,
    pedestrian_count: int,
    pedestrian_wait_time: int,
    has_emergency: bool,
    has_bus: bool,
    current_emergency_override: bool,
) -> PhaseAction:
    """
    Core decision function for adaptive traffic light controller.

    Manages intersection timing based on traffic conditions, emergency vehicles,
    and pedestrian needs. Coordinates emergency override logic, phase extension
    criteria, timing calculations, and handles edge cases.

    Args:
        current_ns_light: Current north-south light state
        current_ew_light: Current east-west light state
        time_remaining: Remaining time in current phase (seconds)
        queue_size: Number of vehicles in queue
        pedestrian_count: Number of waiting pedestrians
        pedestrian_wait_time: How long pedestrians have been waiting (seconds)
        has_emergency: Whether emergency vehicle is present
        has_bus: Whether bus is present
        current_emergency_override: Whether emergency override is currently active

    Returns:
        PhaseAction with new light states, duration, and action classification
    """
    # Check validity first
    valid = _is_valid_state(time_remaining, queue_size, has_emergency)

    if not valid:
        return PhaseAction(
            new_ns_light=LightState.RED,
            new_ew_light=LightState.RED,
            phase_duration=30,
            action_type=ActionClassification.INVALID_ACTION,
            override_active=False,
        )

    # Emergency vehicles override everything
    if has_emergency:
        return PhaseAction(
            new_ns_light=LightState.GREEN,
            new_ew_light=LightState.RED,
            phase_duration=15,
            action_type=ActionClassification.EMERGENCY_OVERRIDE,
            override_active=True,
        )

    # Clear emergency override if it was active but no longer needed
    if current_emergency_override:
        return PhaseAction(
            new_ns_light=current_ns_light,
            new_ew_light=current_ew_light,
            phase_duration=30,
            action_type=ActionClassification.NORMAL_TIMING,
            override_active=False,
        )

    # Normal operation: check what to do
    if time_remaining <= 0:
        # Time expired: transition to next phase
        new_ns, new_ew = _next_light_state(current_ns_light, current_ew_light)
        duration = _calculate_base_duration(
            queue_size, pedestrian_count, pedestrian_wait_time
        )
        return PhaseAction(
            new_ns_light=new_ns,
            new_ew_light=new_ew,
            phase_duration=duration,
            action_type=ActionClassification.PHASE_TRANSITION,
            override_active=False,
        )

    # Time remaining: check if extension needed
    heavy_traffic = queue_size > 5
    many_pedestrians = pedestrian_count > 2
    should_extend = _check_extension_conditions(
        has_bus, heavy_traffic, many_pedestrians, time_remaining
    )

    if should_extend:
        # Extend current phase
        return PhaseAction(
            new_ns_light=current_ns_light,
            new_ew_light=current_ew_light,
            phase_duration=time_remaining + 10,
            action_type=ActionClassification.PHASE_EXTENSION,
            override_active=False,
        )

    # Continue normal countdown
    return PhaseAction(
        new_ns_light=current_ns_light,
        new_ew_light=current_ew_light,
        phase_duration=time_remaining - 1,
        action_type=ActionClassification.NORMAL_TIMING,
        override_active=False,
    )
