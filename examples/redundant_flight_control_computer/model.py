from enum import Enum
from typing import NamedTuple


class ComputerStatus(Enum):
    """Status of a flight control computer."""

    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    FAILED = "failed"


class FlightPhase(Enum):
    """Current phase of flight."""

    TAKEOFF = "takeoff"
    CRUISE = "cruise"
    LANDING = "landing"


class SensorAgreement(Enum):
    """Level of agreement between sensors."""

    FULL_AGREEMENT = "full_agreement"
    PARTIAL_AGREEMENT = "partial_agreement"
    DISAGREEMENT = "disagreement"


class ControlDecision(NamedTuple):
    """Flight control system decision output."""

    use_computer_a: bool
    use_computer_b: bool
    use_computer_c: bool
    require_pilot_intervention: bool
    system_confidence: int  # 0-100


def _base_confidence(flight_phase: FlightPhase) -> int:
    """Calculate base confidence level for a given flight phase."""
    if flight_phase == FlightPhase.TAKEOFF:
        return 95  # Require high confidence
    elif flight_phase == FlightPhase.CRUISE:
        return 85
    elif flight_phase == FlightPhase.LANDING:
        return 98  # Require highest confidence
    return 0


def _agreement_factor(agreement: SensorAgreement) -> int:
    """Calculate confidence factor based on sensor agreement level."""
    if agreement == SensorAgreement.FULL_AGREEMENT:
        return 100  # No reduction
    elif agreement == SensorAgreement.PARTIAL_AGREEMENT:
        return 85  # 15% reduction
    elif agreement == SensorAgreement.DISAGREEMENT:
        return 60  # 40% reduction
    return 0


def _count_operational(
    comp_a: ComputerStatus, comp_b: ComputerStatus, comp_c: ComputerStatus
) -> int:
    """Count the number of operational computers."""
    count = 0
    if comp_a == ComputerStatus.OPERATIONAL:
        count += 1
    if comp_b == ComputerStatus.OPERATIONAL:
        count += 1
    if comp_c == ComputerStatus.OPERATIONAL:
        count += 1
    return count


def _has_quorum(
    comp_a: ComputerStatus, comp_b: ComputerStatus, comp_c: ComputerStatus
) -> bool:
    """Check if quorum exists (at least 2 operational computers)."""
    return _count_operational(comp_a, comp_b, comp_c) >= 2


def _requires_pilot_override(
    flight_phase: FlightPhase,
    agreement: SensorAgreement,
    comp_a: ComputerStatus,
    comp_b: ComputerStatus,
    comp_c: ComputerStatus,
) -> bool:
    """Determine if pilot override is required based on flight phase and conditions."""
    critical_phase = (
        flight_phase == FlightPhase.TAKEOFF or flight_phase == FlightPhase.LANDING
    )

    if critical_phase:
        # Critical phases need pilot...
        needs_pilot = True
        # ...EXCEPT with full agreement and quorum
        override = agreement == SensorAgreement.FULL_AGREEMENT and _has_quorum(
            comp_a, comp_b, comp_c
        )
        return not override if override else needs_pilot
    else:
        return False  # Cruise doesn't require pilot


def _is_valid_state(confidence: int, comp_degraded_count: int, altitude: int) -> bool:
    """Check if the system state is valid (not in dead zone or invalid range)."""
    # Confidence 83-87 with 1 degraded computer at altitude 9800-10200 is ambiguous
    in_dead_zone = (
        83 <= confidence <= 87
        and comp_degraded_count == 1
        and 9800 <= altitude <= 10200
    )

    invalid = confidence < 0 or confidence > 100 or altitude < 0 or altitude > 50000

    return not (in_dead_zone or invalid)


def _select_computers(
    comp_a: ComputerStatus, comp_b: ComputerStatus, comp_c: ComputerStatus
) -> tuple[bool, bool, bool]:
    """Determine which computers to use based on their status."""
    use_a = comp_a == ComputerStatus.OPERATIONAL or comp_a == ComputerStatus.DEGRADED
    use_b = comp_b == ComputerStatus.OPERATIONAL or comp_b == ComputerStatus.DEGRADED
    use_c = comp_c == ComputerStatus.OPERATIONAL or comp_c == ComputerStatus.DEGRADED

    # If quorum exists, use all operational + degraded
    # If no quorum, pilot takes over anyway
    return (use_a, use_b, use_c)


def determine_flight_control(
    comp_a: ComputerStatus,
    comp_b: ComputerStatus,
    comp_c: ComputerStatus,
    flight_phase: FlightPhase,
    agreement: SensorAgreement,
    altitude: int,
) -> ControlDecision:
    """
    Determine flight control system configuration based on computer status,
    flight phase, sensor agreement, and altitude.

    Implements triple-redundant quorum-based operation with phase-specific
    confidence requirements and override logic for critical phases.
    """
    op_count = _count_operational(comp_a, comp_b, comp_c)
    degraded_count = sum(
        [
            1 if comp_a == ComputerStatus.DEGRADED else 0,
            1 if comp_b == ComputerStatus.DEGRADED else 0,
            1 if comp_c == ComputerStatus.DEGRADED else 0,
        ]
    )

    # Calculate confidence
    base_conf = _base_confidence(flight_phase)
    agree_factor = _agreement_factor(agreement)
    confidence = (base_conf * agree_factor) // 100

    # Check validity
    valid = _is_valid_state(confidence, degraded_count, altitude)

    if not valid:
        return ControlDecision(
            use_computer_a=False,
            use_computer_b=False,
            use_computer_c=False,
            require_pilot_intervention=True,
            system_confidence=0,
        )

    # Check quorum
    quorum = _has_quorum(comp_a, comp_b, comp_c)

    # Check override requirement
    pilot_needed = _requires_pilot_override(
        flight_phase, agreement, comp_a, comp_b, comp_c
    )

    # Select computers
    use_a, use_b, use_c = _select_computers(comp_a, comp_b, comp_c)

    return ControlDecision(
        use_computer_a=use_a and quorum,
        use_computer_b=use_b and quorum,
        use_computer_c=use_c and quorum,
        require_pilot_intervention=pilot_needed or not quorum,
        system_confidence=confidence,
    )
