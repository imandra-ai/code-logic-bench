from enum import Enum
from dataclasses import dataclass


class ProductType(Enum):
    STANDARD = "Standard"
    FRAGILE = "Fragile"
    HAZARDOUS = "Hazardous"
    PERISHABLE = "Perishable"
    HIGH_VALUE = "HighValue"


class TemperatureZone(Enum):
    AMBIENT = "Ambient"
    REFRIGERATED = "Refrigerated"
    FROZEN = "Frozen"


class PriorityLevel(Enum):
    NORMAL = "Normal"
    HIGH = "High"
    EMERGENCY = "Emergency"


class DockStatus(Enum):
    AVAILABLE = "Available"
    PARTIALLY_OCCUPIED = "PartiallyOccupied"
    FULLY_OCCUPIED = "FullyOccupied"
    MAINTENANCE = "Maintenance"


@dataclass
class RoutingDecision:
    """Result of a routing decision in the cross-docking system."""

    route_approved: bool
    assigned_dock_id: int
    requires_emergency_override: bool
    estimated_handling_time: int
    routing_valid: bool


def base_handling_time(product_type: ProductType) -> int:
    """Get base handling time in minutes for a product type."""
    return {
        ProductType.STANDARD: 15,
        ProductType.FRAGILE: 30,
        ProductType.HAZARDOUS: 45,
        ProductType.PERISHABLE: 20,
        ProductType.HIGH_VALUE: 25,
    }[product_type]


def temp_handling_multiplier(temp_zone: TemperatureZone) -> int:
    """Get handling time multiplier based on temperature zone."""
    return {
        TemperatureZone.AMBIENT: 1,
        TemperatureZone.REFRIGERATED: 2,
        TemperatureZone.FROZEN: 3,
    }[temp_zone]


def dock_capacity_limit(dock_status: DockStatus) -> int:
    """Get capacity limit for a dock based on its status."""
    return {
        DockStatus.AVAILABLE: 100,
        DockStatus.PARTIALLY_OCCUPIED: 60,
        DockStatus.FULLY_OCCUPIED: 0,
        DockStatus.MAINTENANCE: 0,
    }[dock_status]


def priority_capacity_adjustment(priority: PriorityLevel) -> int:
    """Get capacity adjustment based on priority level."""
    return {
        PriorityLevel.NORMAL: 0,
        PriorityLevel.HIGH: -10,  # High priority can squeeze into slightly fuller docks
        PriorityLevel.EMERGENCY: -30,  # Emergency can override more capacity
    }[priority]


def is_temp_compatible(
    dock_temp_zone: TemperatureZone, product_temp_zone: TemperatureZone
) -> bool:
    """Check if dock temperature zone is compatible with product temperature requirements."""
    if dock_temp_zone == product_temp_zone:
        # Exact match always works
        return True

    # Refrigerated docks can handle Ambient (but not ideal)
    if (
        dock_temp_zone == TemperatureZone.REFRIGERATED
        and product_temp_zone == TemperatureZone.AMBIENT
    ):
        return True

    # Frozen can handle Refrigerated and Ambient (but not ideal)
    if dock_temp_zone == TemperatureZone.FROZEN and product_temp_zone in (
        TemperatureZone.REFRIGERATED,
        TemperatureZone.AMBIENT,
    ):
        return True

    # Other combinations don't work
    return False


def calculate_handling_time(
    product_type: ProductType, temp_zone: TemperatureZone, priority: PriorityLevel
) -> int:
    """Calculate adjusted handling time based on temperature zone, product type, and priority."""
    base = base_handling_time(product_type)
    temp_mult = temp_handling_multiplier(temp_zone)
    adjusted = base * temp_mult

    # Emergency reduces handling time, EXCEPT for Hazardous
    if priority == PriorityLevel.EMERGENCY:
        if product_type == ProductType.HAZARDOUS:
            return adjusted  # Cannot rush hazardous handling
        else:
            return (adjusted * 7) // 10  # 30% faster
    elif priority == PriorityLevel.HIGH:
        return (adjusted * 9) // 10  # 10% faster
    else:
        return adjusted


def check_capacity_fit(
    product_volume: int, dock_status: DockStatus, priority: PriorityLevel
) -> bool:
    """Check if product volume fits in dock capacity with priority adjustments."""
    dock_capacity = dock_capacity_limit(dock_status)
    priority_adjustment = priority_capacity_adjustment(priority)
    effective_capacity = dock_capacity + priority_adjustment
    return product_volume <= effective_capacity


def is_in_dead_zone(product_volume: int, dock_status: DockStatus) -> bool:
    """Check if product volume is in an ambiguous dead zone for the dock status."""
    if dock_status == DockStatus.PARTIALLY_OCCUPIED:
        return 58 <= product_volume <= 62
    return False


def check_emergency_override_needed(
    priority: PriorityLevel,
    time_to_deadline: int,
    product_value: int,
    dock_distance: int,
) -> bool:
    """Check if emergency override is needed based on a quorum of factors (3 out of 4)."""
    c1 = priority == PriorityLevel.EMERGENCY
    c2 = time_to_deadline < 30  # Less than 30 minutes
    c3 = product_value > 10000
    c4 = dock_distance > 100  # Long distance needs override

    count = sum([c1, c2, c3, c4])
    return count >= 3


def assign_dock_by_temp_and_status(
    dock_temp_zone: TemperatureZone, dock_status: DockStatus
) -> int:
    """Assign dock ID based on temperature zone and status."""
    dock_map = {
        (TemperatureZone.AMBIENT, DockStatus.AVAILABLE): 1,
        (TemperatureZone.AMBIENT, DockStatus.PARTIALLY_OCCUPIED): 2,
        (TemperatureZone.REFRIGERATED, DockStatus.AVAILABLE): 3,
        (TemperatureZone.REFRIGERATED, DockStatus.PARTIALLY_OCCUPIED): 4,
        (TemperatureZone.FROZEN, DockStatus.AVAILABLE): 5,
        (TemperatureZone.FROZEN, DockStatus.PARTIALLY_OCCUPIED): 6,
    }
    return dock_map.get((dock_temp_zone, dock_status), 0)  # 0 for invalid


def determine_routing_decision(
    product_type: ProductType,
    product_temp_zone: TemperatureZone,
    product_volume: int,
    priority: PriorityLevel,
    dock_temp_zone: TemperatureZone,
    dock_status: DockStatus,
    time_to_deadline: int,
    product_value: int,
    dock_distance: int,
) -> RoutingDecision:
    """
    Determine routing decision for a product in the cross-docking system.

    Routes products from inbound to outbound docks based on product characteristics,
    dock availability and capacity, and priority levels. Handles temperature zone
    compatibility, capacity constraints, and emergency routing scenarios.
    """
    # Check validity conditions first
    in_dead_zone = is_in_dead_zone(product_volume, dock_status)

    if in_dead_zone:
        return RoutingDecision(
            route_approved=False,
            assigned_dock_id=0,
            requires_emergency_override=False,
            estimated_handling_time=0,
            routing_valid=False,
        )

    # Check temperature compatibility
    temp_compatible = is_temp_compatible(dock_temp_zone, product_temp_zone)

    if not temp_compatible:
        return RoutingDecision(
            route_approved=False,
            assigned_dock_id=0,
            requires_emergency_override=False,
            estimated_handling_time=0,
            routing_valid=True,
        )

    # Check capacity fit
    capacity_ok = check_capacity_fit(product_volume, dock_status, priority)

    # Maintenance dock blocks all routing EXCEPT Emergency with override
    blocked_by_maintenance = dock_status == DockStatus.MAINTENANCE

    # Calculate handling time
    handling_time = calculate_handling_time(product_type, product_temp_zone, priority)

    # Check if emergency override is needed
    needs_override = check_emergency_override_needed(
        priority, time_to_deadline, product_value, dock_distance
    )

    # Override logic - Emergency can bypass capacity and maintenance
    emergency_bypass = priority == PriorityLevel.EMERGENCY and needs_override

    # Final routing decision
    if blocked_by_maintenance:
        # Only emergency with override can use maintenance docks
        can_route = emergency_bypass
    else:
        # Normal routing requires capacity
        can_route = capacity_ok or emergency_bypass

    if can_route:
        dock_id = assign_dock_by_temp_and_status(dock_temp_zone, dock_status)
        return RoutingDecision(
            route_approved=True,
            assigned_dock_id=dock_id,
            requires_emergency_override=needs_override,
            estimated_handling_time=handling_time,
            routing_valid=True,
        )
    else:
        return RoutingDecision(
            route_approved=False,
            assigned_dock_id=0,
            requires_emergency_override=False,
            estimated_handling_time=0,
            routing_valid=True,
        )
