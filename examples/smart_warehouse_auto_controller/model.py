from enum import Enum
from dataclasses import dataclass


class RobotType(Enum):
    """Types of warehouse robots."""

    PICKING_ROBOT = "PickingRobot"
    TRANSPORT_ROBOT = "TransportRobot"
    SORTING_ROBOT = "SortingRobot"
    INSPECTION_ROBOT = "InspectionRobot"


class ItemType(Enum):
    """Types of items in the warehouse."""

    FRAGILE = "Fragile"
    HEAVY = "Heavy"
    STANDARD = "Standard"
    HAZARDOUS = "Hazardous"
    FROZEN = "Frozen"
    PERISHABLE = "Perishable"


class TaskPriority(Enum):
    """Priority levels for tasks."""

    CRITICAL = "Critical"
    HIGH = "High"
    NORMAL = "Normal"
    LOW = "Low"


class ZoneSafety(Enum):
    """Safety status of warehouse zones."""

    SAFE = "Safe"
    CAUTION = "Caution"
    HAZARD = "Hazard"
    EMERGENCY = "Emergency"


@dataclass
class AssignmentDecision:
    """Result of task assignment decision."""

    approved: bool
    estimated_duration: int  # minutes
    requires_supervision: bool
    priority_boost: int


def robot_handles_item(robot_type: RobotType, item_type: ItemType) -> bool:
    """Check if robot type can handle item type."""
    compatibility = {
        RobotType.PICKING_ROBOT: {ItemType.STANDARD, ItemType.FRAGILE},
        RobotType.TRANSPORT_ROBOT: {
            ItemType.STANDARD,
            ItemType.HEAVY,
            ItemType.HAZARDOUS,
        },
        RobotType.SORTING_ROBOT: {ItemType.STANDARD, ItemType.FRAGILE, ItemType.HEAVY},
        RobotType.INSPECTION_ROBOT: set(ItemType),  # Handles all types
    }
    return item_type in compatibility.get(robot_type, set())


def base_duration(item_type: ItemType) -> int:
    """Get base task duration by item type in minutes."""
    durations = {
        ItemType.FRAGILE: 30,
        ItemType.HEAVY: 50,
        ItemType.HAZARDOUS: 40,
        ItemType.FROZEN: 20,
        ItemType.PERISHABLE: 20,
        ItemType.STANDARD: 10,
    }
    return durations[item_type]


def priority_value(priority: TaskPriority) -> int:
    """Get numeric priority score by priority level."""
    values = {
        TaskPriority.CRITICAL: 100,
        TaskPriority.HIGH: 75,
        TaskPriority.NORMAL: 50,
        TaskPriority.LOW: 25,
    }
    return values[priority]


def zone_allows_task(zone_safety: ZoneSafety, item_type: ItemType) -> bool:
    """Check if zone safety status allows task execution."""
    if zone_safety == ZoneSafety.EMERGENCY:
        return False
    if zone_safety == ZoneSafety.HAZARD:
        return False
    return True


def has_sufficient_battery(battery_level: int, item_type: ItemType) -> bool:
    """Check if robot has adequate battery for item type."""
    min_battery = {
        ItemType.HEAVY: 40,
        ItemType.HAZARDOUS: 50,  # Safety margin
    }
    required = min_battery.get(item_type, 20)
    return battery_level >= required


def apply_efficiency_factor(duration: int, efficiency: int) -> int:
    """Adjust duration based on robot efficiency (0-100)."""
    factor = (100 - efficiency) // 10
    return duration + (duration * factor // 10)


def is_critical_override(
    priority: TaskPriority,
    robot_type: RobotType,
    item_type: ItemType,
    battery_level: int,
) -> bool:
    """Check if critical priority override applies."""
    return (
        priority == TaskPriority.CRITICAL
        and robot_handles_item(robot_type, item_type)
        and battery_level >= 15  # Emergency minimum
    )


def determine_task_assignment(
    robot_type: RobotType,
    item_type: ItemType,
    priority: TaskPriority,
    battery_level: int,
    efficiency: int,
    zone_safety: ZoneSafety,
    humans_in_zone: int,
) -> AssignmentDecision:
    """
    Determine whether to assign a task to a warehouse robot.

    Evaluates robot capability, item type, battery level, efficiency,
    zone safety, and task priority to make assignment decision.
    Handles critical priority overrides and supervision requirements.
    """
    # Check critical override first
    critical = is_critical_override(priority, robot_type, item_type, battery_level)

    if critical:
        # Critical override: approve immediately
        base_dur = base_duration(item_type)
        adj_dur = apply_efficiency_factor(base_dur, efficiency)
        return AssignmentDecision(
            approved=True,
            estimated_duration=adj_dur,
            requires_supervision=(item_type in {ItemType.HAZARDOUS, ItemType.HEAVY}),
            priority_boost=100,
        )

    # Normal flow: check all constraints
    capable = robot_handles_item(robot_type, item_type)

    if not capable:
        return AssignmentDecision(
            approved=False,
            estimated_duration=0,
            requires_supervision=False,
            priority_boost=0,
        )

    zone_ok = zone_allows_task(zone_safety, item_type)

    if not zone_ok:
        return AssignmentDecision(
            approved=False,
            estimated_duration=0,
            requires_supervision=False,
            priority_boost=0,
        )

    battery_ok = has_sufficient_battery(battery_level, item_type)

    if not battery_ok:
        return AssignmentDecision(
            approved=False,
            estimated_duration=0,
            requires_supervision=False,
            priority_boost=0,
        )

    # All checks passed, approve
    base_dur = base_duration(item_type)
    adj_dur = apply_efficiency_factor(base_dur, efficiency)

    # Hazardous/Heavy items need supervision if no humans present
    needs_super = (
        item_type in {ItemType.HAZARDOUS, ItemType.HEAVY}
    ) and humans_in_zone == 0

    # Calculate priority boost
    prio_val = priority_value(priority)

    return AssignmentDecision(
        approved=True,
        estimated_duration=adj_dur,
        requires_supervision=needs_super,
        priority_boost=prio_val,
    )
