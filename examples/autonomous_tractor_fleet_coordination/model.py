from enum import Enum
from typing import NamedTuple


class TaskType(Enum):
    """Types of agricultural tasks that can be assigned to tractors."""

    PLANTING = "planting"
    HARVESTING = "harvesting"
    SPRAYING = "spraying"
    TILLAGE = "tillage"


class Weather(Enum):
    """Weather conditions affecting task assignment."""

    SUNNY = "sunny"
    RAINY = "rainy"
    STORMY = "stormy"


class AssignmentDecision(Enum):
    """Possible assignment decisions for a tractor."""

    ASSIGN_TASK = "assign_task"
    REFUEL_FIRST = "refuel_first"
    MAINTENANCE_REQUIRED = "maintenance_required"
    ABORT_WEATHER = "abort_weather"
    ABORT_COLLISION = "abort_collision"


class TaskAssignment(NamedTuple):
    """Result of task assignment evaluation."""

    decision: AssignmentDecision
    can_proceed: bool


def _in_critical_zone(fuel_level: float, maintenance_hours: float) -> bool:
    """Check if tractor is in critical zone (fuel/maintenance ambiguity)."""
    return 18 <= fuel_level <= 22 and 195 <= maintenance_hours <= 205


def _task_weather_compatible(task_type: TaskType, weather: Weather) -> bool:
    """Check if task type is compatible with current weather conditions."""
    if task_type == TaskType.SPRAYING and weather in (Weather.RAINY, Weather.STORMY):
        return False
    if weather == Weather.STORMY:
        return False
    return True


def _check_collision_override(
    distance_to_nearest_tractor: float, collision_active: bool
) -> bool:
    """Check if collision zone overrides all other decisions."""
    return collision_active and distance_to_nearest_tractor < 50


def _readiness_quorum_met(
    fuel_level: float,
    maintenance_hours: float,
    has_equipment: bool,
    task_deadline_ok: bool,
) -> bool:
    """Check if at least 3 out of 4 readiness conditions are met."""
    c1 = fuel_level >= 30
    c2 = maintenance_hours < 180
    c3 = has_equipment
    c4 = task_deadline_ok

    count = sum([c1, c2, c3, c4])
    return count >= 3


def determine_task_assignment(
    task_type: TaskType,
    weather: Weather,
    fuel_level: float,
    maintenance_hours: float,
    has_equipment: bool,
    task_deadline_ok: bool,
    distance_to_nearest_tractor: float,
    collision_active: bool,
) -> TaskAssignment:
    """
    Determine task assignment for an autonomous tractor.

    Evaluates operational readiness, weather conditions, fuel levels, maintenance needs,
    and collision avoidance to decide if a task can be assigned. Implements a readiness
    quorum requiring 3 out of 4 conditions for task assignment.

    Args:
        task_type: Type of agricultural task to assign
        weather: Current weather conditions
        fuel_level: Current fuel level (percentage or units)
        maintenance_hours: Hours since last maintenance
        has_equipment: Whether tractor has required equipment
        task_deadline_ok: Whether task can be completed within deadline
        distance_to_nearest_tractor: Distance to nearest other tractor
        collision_active: Whether collision avoidance is active

    Returns:
        TaskAssignment with decision and whether tractor can proceed
    """
    # Dead zone check
    if _in_critical_zone(fuel_level, maintenance_hours):
        return TaskAssignment(AssignmentDecision.MAINTENANCE_REQUIRED, False)

    # Override: Collision zone check first
    if _check_collision_override(distance_to_nearest_tractor, collision_active):
        return TaskAssignment(AssignmentDecision.ABORT_COLLISION, False)

    # Weather compatibility check
    if not _task_weather_compatible(task_type, weather):
        return TaskAssignment(AssignmentDecision.ABORT_WEATHER, False)

    # Critical resource checks with precedence
    if fuel_level < 15:
        return TaskAssignment(AssignmentDecision.REFUEL_FIRST, False)

    if maintenance_hours > 200:
        return TaskAssignment(AssignmentDecision.MAINTENANCE_REQUIRED, False)

    # Readiness quorum check
    if _readiness_quorum_met(
        fuel_level, maintenance_hours, has_equipment, task_deadline_ok
    ):
        return TaskAssignment(AssignmentDecision.ASSIGN_TASK, True)

    # Decide based on what's missing
    if fuel_level < 30:
        return TaskAssignment(AssignmentDecision.REFUEL_FIRST, False)

    if maintenance_hours >= 180:
        return TaskAssignment(AssignmentDecision.MAINTENANCE_REQUIRED, False)

    return TaskAssignment(AssignmentDecision.ABORT_WEATHER, False)
