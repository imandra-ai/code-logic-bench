from enum import Enum
from typing import NamedTuple


class AlertLevel(Enum):
    """Alert levels for coastal erosion monitoring."""

    NORMAL = "Normal"
    ADVISORY = "Advisory"
    WARNING = "Warning"
    CRITICAL = "Critical"
    EMERGENCY = "Emergency"


class CoastalType(Enum):
    """Types of coastal geography."""

    SANDY = "Sandy"
    ROCKY = "Rocky"
    ESTUARY = "Estuary"


class SensorStatus(Enum):
    """Status of erosion monitoring sensors."""

    ACTIVE = "Active"
    DEGRADED = "Degraded"
    FAILED = "Failed"


class AlertDecision(NamedTuple):
    """Alert decision containing level and evacuation recommendation."""

    level: AlertLevel
    evacuate: bool


def _in_measurement_dead_zone(erosion_rate: float, wave_height: float) -> bool:
    """Check if measurements fall within ambiguous dead zone."""
    return 48 <= erosion_rate <= 52 and 28 <= wave_height <= 32


def _base_erosion_threshold(coastal_type: CoastalType, level: AlertLevel) -> float:
    """Get erosion threshold for given coastal type and alert level."""
    thresholds = {
        (CoastalType.SANDY, AlertLevel.ADVISORY): 30,
        (CoastalType.SANDY, AlertLevel.WARNING): 50,
        (CoastalType.SANDY, AlertLevel.CRITICAL): 80,
        (CoastalType.ROCKY, AlertLevel.ADVISORY): 50,
        (CoastalType.ROCKY, AlertLevel.WARNING): 80,
        (CoastalType.ROCKY, AlertLevel.CRITICAL): 120,
        (CoastalType.ESTUARY, AlertLevel.ADVISORY): 25,
        (CoastalType.ESTUARY, AlertLevel.WARNING): 40,
        (CoastalType.ESTUARY, AlertLevel.CRITICAL): 65,
    }

    # Default thresholds for Normal and Emergency
    if level == AlertLevel.NORMAL:
        return 0
    if level == AlertLevel.EMERGENCY:
        return 150

    return thresholds.get((coastal_type, level), 0)


def _danger_quorum_met(
    erosion_rate: float,
    threshold: float,
    wave_height: float,
    infrastructure_critical: bool,
) -> bool:
    """Check if at least 2 out of 3 danger indicators are present."""
    c1 = erosion_rate >= threshold
    c2 = wave_height > 25
    c3 = infrastructure_critical

    count = sum([c1, c2, c3])
    return count >= 2


def determine_alert(
    coastal_type: CoastalType,
    erosion_rate: float,
    wave_height: float,
    sensor_status: SensorStatus,
    infrastructure_critical: bool,
) -> AlertDecision:
    """
    Determine alert level and evacuation decision for coastal erosion monitoring.

    Args:
        coastal_type: Type of coastal geography (Sandy, Rocky, or Estuary)
        erosion_rate: Current erosion rate measurement
        wave_height: Current wave height measurement
        sensor_status: Status of monitoring sensors
        infrastructure_critical: Whether critical infrastructure is present

    Returns:
        AlertDecision containing the alert level and evacuation recommendation
    """
    # Dead zone check
    if _in_measurement_dead_zone(erosion_rate, wave_height):
        return AlertDecision(level=AlertLevel.ADVISORY, evacuate=False)

    # Failed sensor forces advisory
    if sensor_status == SensorStatus.FAILED:
        return AlertDecision(level=AlertLevel.ADVISORY, evacuate=False)

    # Classify base level
    threshold_emergency = _base_erosion_threshold(coastal_type, AlertLevel.EMERGENCY)
    threshold_critical = _base_erosion_threshold(coastal_type, AlertLevel.CRITICAL)
    threshold_warning = _base_erosion_threshold(coastal_type, AlertLevel.WARNING)
    threshold_advisory = _base_erosion_threshold(coastal_type, AlertLevel.ADVISORY)

    if erosion_rate >= threshold_emergency:
        return AlertDecision(level=AlertLevel.EMERGENCY, evacuate=True)
    elif erosion_rate >= threshold_critical:
        # Check quorum for critical
        quorum = _danger_quorum_met(
            erosion_rate, threshold_critical, wave_height, infrastructure_critical
        )
        if quorum:
            return AlertDecision(
                level=AlertLevel.CRITICAL, evacuate=infrastructure_critical
            )
        else:
            return AlertDecision(level=AlertLevel.WARNING, evacuate=False)
    elif erosion_rate >= threshold_warning:
        return AlertDecision(level=AlertLevel.WARNING, evacuate=False)
    elif erosion_rate >= threshold_advisory:
        return AlertDecision(level=AlertLevel.ADVISORY, evacuate=False)
    else:
        return AlertDecision(level=AlertLevel.NORMAL, evacuate=False)
