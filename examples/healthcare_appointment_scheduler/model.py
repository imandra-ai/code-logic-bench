from enum import Enum
from typing import NamedTuple


class InsuranceStatus(Enum):
    """Insurance verification status for a patient."""

    VERIFIED = "verified"
    PENDING = "pending"
    DENIED = "denied"
    EXPIRED = "expired"


class Priority(Enum):
    """Appointment priority level."""

    ROUTINE = "routine"
    URGENT = "urgent"
    EMERGENCY = "emergency"


class AppointmentResult(Enum):
    """Outcome of appointment request evaluation."""

    APPROVED = "approved"
    WAITLIST = "waitlist"
    REJECTED = "rejected"


def emergency_override(priority: Priority, no_show_count: int) -> bool:
    """
    Emergency appointments can bypass certain constraints, but only if patient
    record is acceptable (no_show_count < 3).
    """
    return priority == Priority.EMERGENCY and no_show_count < 3


def insurance_acceptable(
    status: InsuranceStatus, provider_premium: bool, age: int
) -> bool:
    """
    Insurance verification depends on provider type and age.
    Different providers have different rules for "acceptable" insurance.
    """
    if status == InsuranceStatus.VERIFIED:
        return True
    elif status == InsuranceStatus.PENDING:
        # Premium providers accept pending for seniors
        return provider_premium and age >= 65
    elif status in (InsuranceStatus.EXPIRED, InsuranceStatus.DENIED):
        return False
    return False


def in_scheduling_dead_zone(time_slot: int, daily_count: int) -> bool:
    """
    Certain time slots (720-750) with high daily_count (18-20) are ambiguous.
    These represent lunch hour borderline cases where policies are unclear.
    """
    # 12:00-12:30 PM, near capacity
    return (720 <= time_slot <= 750) and (18 <= daily_count <= 20)


def calculate_approval_score(
    insurance_ok: bool,
    slot_available: bool,
    pre_auth_ok: bool,
    no_show_acceptable: bool,
    days_in_advance_ok: bool,
) -> int:
    """
    Approval requires 3 out of 5 conditions.
    Returns the count of satisfied conditions.
    """
    count = sum(
        [
            insurance_ok,
            slot_available,
            pre_auth_ok,
            no_show_acceptable,
            days_in_advance_ok,
        ]
    )
    return count


def determine_appointment_decision(
    # Patient info
    insurance_status: InsuranceStatus,
    no_show_count: int,
    patient_age: int,
    pre_auth_provided: bool,
    # Request info
    priority: Priority,
    days_in_advance: int,
    time_slot: int,
    # Doctor/system info
    daily_count: int,
    provider_premium: bool,
    slot_available: bool,
    pre_auth_required: bool,
) -> AppointmentResult:
    """
    Core appointment scheduling decision.

    Determines whether to approve, waitlist, or reject appointment requests based
    on patient insurance status, no-show history, appointment priority, and system
    constraints.

    Implements:
    - Insurance verification with provider-specific rules
    - Emergency override patterns
    - Scheduling dead zones during lunch hours
    - Quorum-based approval system requiring multiple conditions
    """
    # Check dead zone first
    in_dead_zone = in_scheduling_dead_zone(time_slot, daily_count)

    if in_dead_zone:
        # Dead zone goes to waiting list for manual review
        return AppointmentResult.WAITLIST

    # Check emergency override
    is_emergency_override = emergency_override(priority, no_show_count)

    if is_emergency_override:
        # Emergency bypasses normal checks
        return AppointmentResult.APPROVED

    # Normal approval logic with quorum pattern

    # Check individual conditions
    insurance_ok = insurance_acceptable(insurance_status, provider_premium, patient_age)

    pre_auth_ok = (not pre_auth_required) or pre_auth_provided

    no_show_ok = no_show_count <= 2

    days_ok = days_in_advance <= 90

    # Calculate approval score (quorum)
    score = calculate_approval_score(
        insurance_ok, slot_available, pre_auth_ok, no_show_ok, days_ok
    )

    # Need 3 out of 5 conditions for approval
    if score >= 3:
        return (
            AppointmentResult.APPROVED if slot_available else AppointmentResult.WAITLIST
        )
    elif score >= 2:
        # Borderline cases go to waiting list
        return AppointmentResult.WAITLIST
    else:
        return AppointmentResult.REJECTED
