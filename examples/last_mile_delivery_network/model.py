from enum import Enum
from typing import NamedTuple


class VehicleType(Enum):
    """Types of delivery vehicles available in the network."""

    TRUCK = "Truck"
    DRONE = "Drone"
    ROBOT = "Robot"


class PackagePriority(Enum):
    """Priority levels for package delivery."""

    STANDARD = "Standard"
    URGENT = "Urgent"
    EMERGENCY = "Emergency"


class WeatherCondition(Enum):
    """Current weather conditions affecting vehicle operation."""

    CLEAR = "Clear"
    RAIN = "Rain"
    STORM = "Storm"


class AssignmentDecision(Enum):
    """Possible outcomes for vehicle assignment requests."""

    ASSIGNED = "Assigned"
    WAITLIST = "Waitlist"
    REJECTED = "Rejected"


def _emergency_override(priority: PackagePriority, battery_level: float) -> bool:
    """
    Emergency packages can be assigned despite lower battery,
    but only if battery is above critical threshold (15%).
    """
    return priority == PackagePriority.EMERGENCY and battery_level > 15


def _vehicle_weather_compatible(
    vehicle_type: VehicleType, weather: WeatherCondition
) -> bool:
    """Vehicle operability depends on type and weather."""
    if vehicle_type == VehicleType.TRUCK:
        return True  # Trucks work in all weather
    elif vehicle_type == VehicleType.DRONE:
        return weather != WeatherCondition.STORM  # Drones grounded in storm
    elif vehicle_type == VehicleType.ROBOT:
        return weather != WeatherCondition.STORM  # Robots restricted in storm
    return False


def _in_battery_dead_zone(vehicle_type: VehicleType, battery_level: float) -> bool:
    """
    Battery levels in certain ranges are ambiguous for assignment.
    Different vehicles have different "nervous" battery ranges.
    """
    if vehicle_type == VehicleType.TRUCK:
        return 20 <= battery_level <= 25
    elif vehicle_type == VehicleType.DRONE:
        return 25 <= battery_level <= 35  # Drones need more margin
    elif vehicle_type == VehicleType.ROBOT:
        return 15 <= battery_level <= 20
    return False


def _distance_suitable(vehicle_type: VehicleType, distance: float) -> bool:
    """Calculate distance category suitability for vehicle type."""
    if vehicle_type == VehicleType.TRUCK:
        return distance <= 200  # Long range
    elif vehicle_type == VehicleType.DRONE:
        return distance <= 30  # Short range
    elif vehicle_type == VehicleType.ROBOT:
        return distance <= 50  # Medium range
    return False


def _calculate_assignment_score(
    weather_ok: bool,
    battery_sufficient: bool,
    capacity_ok: bool,
    distance_ok: bool,
    priority_acceptable: bool,
    not_overloaded: bool,
) -> int:
    """Assignment requires 4 out of 6 conditions."""
    count = sum(
        [
            weather_ok,
            battery_sufficient,
            capacity_ok,
            distance_ok,
            priority_acceptable,
            not_overloaded,
        ]
    )
    return count


def determine_vehicle_assignment(
    vehicle_type: VehicleType,
    battery_level: float,
    current_load: float,
    capacity: float,
    package_weight: float,
    distance: float,
    priority: PackagePriority,
    weather: WeatherCondition,
) -> AssignmentDecision:
    """
    Core vehicle assignment decision for last-mile delivery network.

    Determines whether to assign, waitlist, or reject package assignments
    based on battery levels, capacity constraints, distance requirements,
    package priority, and weather conditions.

    Args:
        vehicle_type: Type of delivery vehicle
        battery_level: Current battery level percentage
        current_load: Current load weight on vehicle
        capacity: Maximum capacity of vehicle
        package_weight: Weight of package to assign
        distance: Delivery distance required
        priority: Priority level of package
        weather: Current weather conditions

    Returns:
        Assignment decision (Assigned, Waitlist, or Rejected)
    """
    # Check battery dead zone first
    in_dead_zone = _in_battery_dead_zone(vehicle_type, battery_level)

    if in_dead_zone:
        return (
            AssignmentDecision.WAITLIST
        )  # Dead zone → wait for recharge or alternative

    # Check emergency override
    is_emergency_override = _emergency_override(priority, battery_level)

    if is_emergency_override:
        return AssignmentDecision.ASSIGNED  # Emergency bypasses normal checks

    # Normal assignment logic with quorum

    # Check individual conditions
    weather_ok = _vehicle_weather_compatible(vehicle_type, weather)

    if vehicle_type == VehicleType.TRUCK:
        battery_ok = battery_level >= 25
    elif vehicle_type == VehicleType.DRONE:
        battery_ok = battery_level >= 35
    elif vehicle_type == VehicleType.ROBOT:
        battery_ok = battery_level >= 20
    else:
        battery_ok = False

    capacity_ok = current_load + package_weight <= capacity

    distance_ok = _distance_suitable(vehicle_type, distance)

    if priority == PackagePriority.EMERGENCY:
        priority_ok = True  # Already handled by override
    elif priority == PackagePriority.URGENT:
        priority_ok = battery_level >= 40  # Urgent needs good battery
    else:  # Standard
        priority_ok = True

    not_overloaded = current_load < (capacity * 80 // 100)  # < 80% capacity

    # Calculate assignment score (quorum)
    score = _calculate_assignment_score(
        weather_ok, battery_ok, capacity_ok, distance_ok, priority_ok, not_overloaded
    )

    # Need 4 out of 6 conditions for assignment
    if score >= 4:
        return AssignmentDecision.ASSIGNED
    elif score >= 3:
        return AssignmentDecision.WAITLIST  # Borderline cases
    else:
        return AssignmentDecision.REJECTED
