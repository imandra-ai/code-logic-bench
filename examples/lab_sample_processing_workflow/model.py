from enum import Enum


class SampleType(Enum):
    """Types of laboratory samples."""

    BIOLOGICAL = "biological"
    CHEMICAL = "chemical"
    ENVIRONMENTAL = "environmental"
    UNKNOWN = "unknown"


class ContaminationLevel(Enum):
    """Levels of contamination."""

    CLEAN = "clean"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProcessingDecision(Enum):
    """Sample processing decisions."""

    APPROVED = "approved"
    QUARANTINE = "quarantine"
    REJECTED = "rejected"


def _priority_override(high_priority: bool, user_clearance: int) -> bool:
    """
    Check if priority override applies.

    High priority bypasses contamination checks only if user clearance is sufficient (≥4).
    """
    return high_priority and user_clearance >= 4


def _required_clearance(sample_type: SampleType) -> int:
    """Determine required clearance level based on sample type."""
    clearance_map = {
        SampleType.BIOLOGICAL: 3,
        SampleType.CHEMICAL: 4,
        SampleType.ENVIRONMENTAL: 2,
        SampleType.UNKNOWN: 5,
    }
    return clearance_map[sample_type]


def _in_temperature_dead_zone(temp: float, refrigerated_sample: bool) -> bool:
    """
    Check if temperature is in ambiguous dead zone.

    Refrigerated should be 2-8°C, but 0-2°C and 8-10°C are "dead zones".
    """
    return refrigerated_sample and ((0 <= temp < 2) or (8 < temp <= 10))


def _calculate_contamination(
    sample_type: SampleType,
    location_contam: ContaminationLevel,
    equipment_contam: ContaminationLevel,
) -> ContaminationLevel:
    """
    Calculate combined contamination risk.

    Highest level wins among sample base, location, and equipment contamination.
    """
    sample_base_map = {
        SampleType.BIOLOGICAL: ContaminationLevel.MEDIUM,
        SampleType.CHEMICAL: ContaminationLevel.HIGH,
        SampleType.ENVIRONMENTAL: ContaminationLevel.LOW,
        SampleType.UNKNOWN: ContaminationLevel.HIGH,
    }
    sample_base = sample_base_map[sample_type]

    # Highest level wins
    if (
        sample_base == ContaminationLevel.HIGH
        or location_contam == ContaminationLevel.HIGH
        or equipment_contam == ContaminationLevel.HIGH
    ):
        return ContaminationLevel.HIGH
    elif (
        sample_base == ContaminationLevel.MEDIUM
        or location_contam == ContaminationLevel.MEDIUM
        or equipment_contam == ContaminationLevel.MEDIUM
    ):
        return ContaminationLevel.MEDIUM
    elif (
        sample_base == ContaminationLevel.LOW
        or location_contam == ContaminationLevel.LOW
        or equipment_contam == ContaminationLevel.LOW
    ):
        return ContaminationLevel.LOW
    else:
        return ContaminationLevel.CLEAN


def _calculate_approval_score(
    user_authorized: bool,
    equipment_available: bool,
    temp_compliant: bool,
    not_expired: bool,
    low_contamination: bool,
) -> int:
    """
    Calculate approval score based on safety conditions.

    Approval needs 3 out of 5 conditions to be met.
    """
    count = sum(
        [
            user_authorized,
            equipment_available,
            temp_compliant,
            not_expired,
            low_contamination,
        ]
    )
    return count


def determine_processing_decision(
    sample_type: SampleType,
    time_since_received: int,
    refrigerated_sample: bool,
    current_temp: float,
    location_contamination: ContaminationLevel,
    equipment_contamination: ContaminationLevel,
    user_clearance: int,
    equipment_available: bool,
    high_priority: bool,
) -> ProcessingDecision:
    """
    Determine whether to approve, quarantine, or reject sample processing request.

    Args:
        sample_type: Type of sample (biological, chemical, environmental, unknown)
        time_since_received: Time since sample received in hours
        refrigerated_sample: Whether sample requires refrigeration
        current_temp: Current storage temperature in Celsius
        location_contamination: Contamination level of location
        equipment_contamination: Contamination level of equipment
        user_clearance: User's clearance level (0-5)
        equipment_available: Whether required equipment is available
        high_priority: Whether sample is high priority

    Returns:
        Processing decision (approved, quarantine, or rejected)
    """
    # Check temperature dead zone first
    in_dead_zone = _in_temperature_dead_zone(current_temp, refrigerated_sample)

    if in_dead_zone:
        # Dead zone → quarantine for review
        return ProcessingDecision.QUARANTINE

    # Check priority override
    is_priority_override = _priority_override(high_priority, user_clearance)

    if is_priority_override:
        # High priority with clearance bypasses normal checks
        return ProcessingDecision.APPROVED

    # Normal approval logic with quorum

    # Check individual conditions
    required_clear = _required_clearance(sample_type)
    user_authorized = user_clearance >= required_clear

    if refrigerated_sample:
        temp_ok = 2 <= current_temp <= 8
    else:
        # Room temperature
        temp_ok = 18 <= current_temp <= 25

    # 30 days in hours
    not_expired = time_since_received <= 720

    combined_contamination = _calculate_contamination(
        sample_type, location_contamination, equipment_contamination
    )
    contamination_ok = combined_contamination != ContaminationLevel.HIGH

    # Calculate approval score (quorum)
    score = _calculate_approval_score(
        user_authorized, equipment_available, temp_ok, not_expired, contamination_ok
    )

    # Need 3 out of 5 for approval
    if score >= 3:
        if contamination_ok:
            return ProcessingDecision.APPROVED
        else:
            # Borderline contamination
            return ProcessingDecision.QUARANTINE
    elif score >= 2:
        # Borderline cases
        return ProcessingDecision.QUARANTINE
    else:
        return ProcessingDecision.REJECTED
