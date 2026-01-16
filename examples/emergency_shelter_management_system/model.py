from dataclasses import dataclass
from enum import Enum


class PriorityLevel(Enum):
    """Priority levels for evacuees."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class MedicalCondition(Enum):
    """Medical condition categories."""

    NO_MEDICAL = "NoMedical"
    MINOR = "Minor"
    CHRONIC = "Chronic"
    ACUTE = "Acute"
    DISABLED = "Disabled"


class WeatherCondition(Enum):
    """Weather severity levels."""

    CLEAR = "Clear"
    RAIN = "Rain"
    STORM = "Storm"
    EXTREME = "Extreme"


class CapacityStatus(Enum):
    """Shelter capacity status."""

    FULL = "Full"
    NEAR_FULL = "NearFull"
    AVAILABLE = "Available"
    AMPLE = "Ample"


class ShelterType(Enum):
    """Types of shelters available."""

    STANDARD = "Standard"
    MEDICAL = "Medical"
    WEATHER_PROTECTED = "WeatherProtected"


@dataclass
class AssignmentDecision:
    """Result of shelter assignment decision."""

    assignment_approved: bool
    assigned_shelter_type: ShelterType
    requires_emergency_override: bool
    priority_escalated: bool
    decision_valid: bool


def has_capacity(capacity_status: CapacityStatus) -> bool:
    """Check if shelter has capacity (conservative approach)."""
    return capacity_status in (CapacityStatus.AVAILABLE, CapacityStatus.AMPLE)


def requires_medical_shelter(medical_cond: MedicalCondition) -> bool:
    """Determine if medical condition requires medical shelter."""
    return medical_cond in (
        MedicalCondition.CHRONIC,
        MedicalCondition.ACUTE,
        MedicalCondition.DISABLED,
    )


def requires_weather_protection(
    weather: WeatherCondition, medical_cond: MedicalCondition
) -> bool:
    """Determine if weather protection is required."""
    if weather == WeatherCondition.EXTREME:
        return True
    if weather == WeatherCondition.STORM and medical_cond in (
        MedicalCondition.ACUTE,
        MedicalCondition.DISABLED,
    ):
        return True
    return False


def is_in_dead_zone(
    capacity: CapacityStatus, priority: PriorityLevel, medical_cond: MedicalCondition
) -> bool:
    """Check for ambiguous dead zone: NearFull + High priority + Minor medical."""
    return (
        capacity == CapacityStatus.NEAR_FULL
        and priority == PriorityLevel.HIGH
        and medical_cond == MedicalCondition.MINOR
    )


def check_emergency_override(
    priority: PriorityLevel, weather_severe: bool, special_req: bool
) -> bool:
    """Quorum for emergency override (2 out of 3 conditions)."""
    c1 = priority == PriorityLevel.CRITICAL
    c2 = weather_severe
    c3 = special_req

    count = sum([c1, c2, c3])
    return count >= 2


def escalate_priority(
    base_priority: PriorityLevel, capacity: CapacityStatus
) -> PriorityLevel:
    """Escalate priority when capacity is near full."""
    if capacity == CapacityStatus.NEAR_FULL:
        if base_priority == PriorityLevel.MEDIUM:
            return PriorityLevel.HIGH
        elif base_priority == PriorityLevel.LOW:
            return PriorityLevel.MEDIUM
    return base_priority


def determine_shelter_type(
    medical_cond: MedicalCondition, weather: WeatherCondition
) -> ShelterType:
    """Determine required shelter type based on medical needs and weather."""
    if requires_medical_shelter(medical_cond):
        return ShelterType.MEDICAL
    elif requires_weather_protection(weather, medical_cond):
        return ShelterType.WEATHER_PROTECTED
    else:
        return ShelterType.STANDARD


def determine_assignment(
    priority: PriorityLevel,
    medical_cond: MedicalCondition,
    weather: WeatherCondition,
    capacity: CapacityStatus,
    special_req: bool,
) -> AssignmentDecision:
    """
    Core decision function for emergency shelter assignment.

    Determines evacuee placement based on priority, medical needs, weather conditions,
    and shelter capacity. Uses quorum pattern for emergency overrides and priority
    escalation when capacity is constrained.

    Args:
        priority: Evacuee priority level
        medical_cond: Medical condition category
        weather: Current weather conditions
        capacity: Current shelter capacity status
        special_req: Special requirements flag

    Returns:
        AssignmentDecision with approval status, shelter type, and decision metadata
    """
    # Check dead zone first
    if is_in_dead_zone(capacity, priority, medical_cond):
        return AssignmentDecision(
            assignment_approved=False,
            assigned_shelter_type=ShelterType.STANDARD,
            requires_emergency_override=False,
            priority_escalated=False,
            decision_valid=False,
        )

    # Escalate priority if needed
    escalated_priority = escalate_priority(priority, capacity)
    was_escalated = escalated_priority != priority

    # Check basic capacity
    has_cap = has_capacity(capacity)

    # Determine required shelter type
    shelter_type = determine_shelter_type(medical_cond, weather)

    # Check if emergency override applies (quorum)
    weather_severe = weather in (WeatherCondition.EXTREME, WeatherCondition.STORM)
    emergency_override = check_emergency_override(
        escalated_priority, weather_severe, special_req
    )

    # Emergency can bypass capacity
    can_assign = emergency_override or has_cap

    # Full shelters block ALL except Critical with override, EXCEPT Extreme weather always allows
    is_blocked = (
        capacity == CapacityStatus.FULL
        and not emergency_override
        and weather != WeatherCondition.EXTREME
    )

    final_approval = can_assign and not is_blocked

    return AssignmentDecision(
        assignment_approved=final_approval,
        assigned_shelter_type=shelter_type,
        requires_emergency_override=emergency_override,
        priority_escalated=was_escalated,
        decision_valid=True,
    )
