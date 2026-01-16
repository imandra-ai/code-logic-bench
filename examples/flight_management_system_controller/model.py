from enum import Enum, auto
from dataclasses import dataclass


class FlightPhase(Enum):
    GROUND = auto()
    TAKEOFF = auto()
    CLIMB = auto()
    CRUISE = auto()
    DESCENT = auto()
    APPROACH = auto()
    LANDING = auto()


class SystemHealth(Enum):
    NORMAL = auto()
    DEGRADED = auto()
    FAILED = auto()


class AltitudeState(Enum):
    GROUND = auto()
    VERY_LOW = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    VERY_HIGH = auto()


class WeatherCondition(Enum):
    CLEAR = auto()
    LIGHT_TURBULENCE = auto()
    MODERATE_TURBULENCE = auto()
    SEVERE = auto()
    ICING = auto()


class AutopilotCapability(Enum):
    FULL_CAPABILITY = auto()
    LIMITED_CAPABILITY = auto()
    MINIMAL_CAPABILITY = auto()


@dataclass
class ApModeDecision:
    mode_allowed: bool
    capability_level: AutopilotCapability
    requires_copilot_monitor: bool
    emergency_disconnect: bool
    mode_downgraded: bool


def _phase_allows_ap(phase: FlightPhase) -> bool:
    """Check if flight phase allows autopilot engagement."""
    return phase not in (FlightPhase.GROUND, FlightPhase.LANDING)


def _altitude_phase_compatible(phase: FlightPhase, alt_state: AltitudeState) -> bool:
    """Check if altitude state is compatible with flight phase."""
    if phase == FlightPhase.APPROACH and alt_state in (
        AltitudeState.VERY_HIGH,
        AltitudeState.HIGH,
    ):
        return False
    if phase == FlightPhase.TAKEOFF and alt_state in (
        AltitudeState.MEDIUM,
        AltitudeState.HIGH,
        AltitudeState.VERY_HIGH,
    ):
        return False
    if phase == FlightPhase.CRUISE and alt_state in (
        AltitudeState.GROUND,
        AltitudeState.VERY_LOW,
        AltitudeState.LOW,
    ):
        return False
    if alt_state == AltitudeState.GROUND:
        return False
    return True


def _determine_capability(
    health: SystemHealth, weather: WeatherCondition
) -> AutopilotCapability:
    """Determine autopilot capability level based on system health and weather."""
    if health == SystemHealth.FAILED:
        return AutopilotCapability.MINIMAL_CAPABILITY

    if health == SystemHealth.NORMAL:
        if weather in (WeatherCondition.CLEAR, WeatherCondition.LIGHT_TURBULENCE):
            return AutopilotCapability.FULL_CAPABILITY
        elif weather == WeatherCondition.MODERATE_TURBULENCE:
            return AutopilotCapability.LIMITED_CAPABILITY
        else:  # SEVERE or ICING
            return AutopilotCapability.MINIMAL_CAPABILITY

    # health == SystemHealth.DEGRADED
    if weather == WeatherCondition.CLEAR:
        return AutopilotCapability.LIMITED_CAPABILITY
    else:
        return AutopilotCapability.MINIMAL_CAPABILITY


def _requires_monitoring(
    phase: FlightPhase, weather: WeatherCondition, health: SystemHealth
) -> bool:
    """Check if copilot monitoring is required."""
    if phase == FlightPhase.APPROACH:
        # Requires monitoring UNLESS weather is clear AND health is normal
        return not (weather == WeatherCondition.CLEAR and health == SystemHealth.NORMAL)
    elif phase == FlightPhase.DESCENT:
        return weather in (WeatherCondition.SEVERE, WeatherCondition.ICING)
    return False


def _is_in_dead_zone(
    alt_state: AltitudeState, phase: FlightPhase, weather: WeatherCondition
) -> bool:
    """Check if current state is in an ambiguous dead zone."""
    # VeryLow altitude during Descent with ModerateTurbulence
    if (
        alt_state == AltitudeState.VERY_LOW
        and phase == FlightPhase.DESCENT
        and weather == WeatherCondition.MODERATE_TURBULENCE
    ):
        return True
    # Low altitude during Climb with Icing
    if (
        alt_state == AltitudeState.LOW
        and phase == FlightPhase.CLIMB
        and weather == WeatherCondition.ICING
    ):
        return True
    return False


def _check_emergency_disconnect(
    health: SystemHealth,
    phase: FlightPhase,
    alt_state: AltitudeState,
    weather: WeatherCondition,
) -> bool:
    """Check emergency disconnect using quorum (2 of 4 conditions)."""
    c1 = health == SystemHealth.FAILED
    c2 = phase == FlightPhase.APPROACH and alt_state == AltitudeState.VERY_LOW
    c3 = weather in (WeatherCondition.SEVERE, WeatherCondition.ICING)
    c4 = alt_state == AltitudeState.VERY_LOW and health == SystemHealth.DEGRADED

    count = sum([c1, c2, c3, c4])
    return count >= 2


def _is_downgraded(capability: AutopilotCapability, health: SystemHealth) -> bool:
    """Check if capability has been downgraded from expected level."""
    if health == SystemHealth.NORMAL and capability in (
        AutopilotCapability.LIMITED_CAPABILITY,
        AutopilotCapability.MINIMAL_CAPABILITY,
    ):
        return True
    if (
        health == SystemHealth.DEGRADED
        and capability == AutopilotCapability.MINIMAL_CAPABILITY
    ):
        return True
    return False


def determine_ap_mode(
    phase: FlightPhase,
    health: SystemHealth,
    alt_state: AltitudeState,
    weather: WeatherCondition,
) -> ApModeDecision:
    """
    Determine autopilot mode decision based on flight conditions.

    Args:
        phase: Current flight phase
        health: System health status
        alt_state: Current altitude state
        weather: Current weather conditions

    Returns:
        ApModeDecision containing mode allowance, capability level, monitoring requirements,
        emergency disconnect status, and downgrade indication
    """
    # Check dead zone first
    if _is_in_dead_zone(alt_state, phase, weather):
        return ApModeDecision(
            mode_allowed=False,
            capability_level=AutopilotCapability.MINIMAL_CAPABILITY,
            requires_copilot_monitor=False,
            emergency_disconnect=False,
            mode_downgraded=False,
        )

    # Check phase compatibility
    if not _phase_allows_ap(phase):
        return ApModeDecision(
            mode_allowed=False,
            capability_level=AutopilotCapability.MINIMAL_CAPABILITY,
            requires_copilot_monitor=False,
            emergency_disconnect=False,
            mode_downgraded=False,
        )

    # Check altitude-phase compatibility
    alt_ok = _altitude_phase_compatible(phase, alt_state)

    # Determine capability level
    capability = _determine_capability(health, weather)

    # Check copilot monitoring requirement
    needs_monitor = _requires_monitoring(phase, weather, health)

    # Check emergency disconnect (quorum)
    emergency = _check_emergency_disconnect(health, phase, alt_state, weather)

    # Emergency disconnects AP regardless
    if emergency:
        mode_allowed = False
    else:
        mode_allowed = alt_ok and health != SystemHealth.FAILED

    downgraded = _is_downgraded(capability, health)

    return ApModeDecision(
        mode_allowed=mode_allowed,
        capability_level=capability,
        requires_copilot_monitor=needs_monitor,
        emergency_disconnect=emergency,
        mode_downgraded=downgraded,
    )
