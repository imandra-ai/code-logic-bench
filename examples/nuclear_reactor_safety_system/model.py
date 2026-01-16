from enum import Enum
from dataclasses import dataclass


class ReactorState(Enum):
    """Reactor operational states."""

    SHUTDOWN = "Shutdown"
    HOT_STANDBY = "HotStandby"
    POWER_OPERATION = "PowerOperation"
    EMERGENCY_SHUTDOWN = "EmergencyShutdown"


class SafetySystemStatus(Enum):
    """Safety system health status."""

    OPERATIONAL = "Operational"
    DEGRADED = "Degraded"
    FAILED = "Failed"


class OperatorOverrideType(Enum):
    """Types of operator override actions."""

    NO_OVERRIDE = "NoOverride"
    SUPPRESS_ALARM = "SuppressAlarm"
    DELAY_SCRAM = "DelayScram"
    BYPASS_INTERLOCK = "BypassInterlock"
    MAINTENANCE_MODE = "MaintenanceMode"


@dataclass
class SafetyResponse:
    """Safety system response with recommended actions."""

    recommended_state: ReactorState
    initiate_scram: bool
    activate_eccs: bool  # Emergency Core Cooling System
    isolate_containment: bool
    response_valid: bool


# Safety thresholds based on reactor physics
TEMP_THRESHOLD_MODERATE = 550  # Celsius
TEMP_THRESHOLD_HIGH = 620
TEMP_THRESHOLD_CRITICAL = 650

PRESSURE_THRESHOLD_MODERATE = 2200  # PSI
PRESSURE_THRESHOLD_HIGH = 2400
PRESSURE_THRESHOLD_CRITICAL = 2500

FLUX_THRESHOLD_HIGH = 103  # % of nominal
FLUX_THRESHOLD_CRITICAL = 105

RADIATION_THRESHOLD_HIGH = 80  # mR/hr
RADIATION_THRESHOLD_CRITICAL = 100

XENON_THRESHOLD_HIGH = 25  # Xenon poisoning threshold


def is_in_measurement_dead_zone(
    temperature: float, pressure: float, xenon_level: float
) -> bool:
    """
    Check if readings are in measurement dead zone.

    Dead zone: readings near threshold boundaries with conflicting signals.
    """
    temp_ambiguous = temperature >= (TEMP_THRESHOLD_HIGH - 2) and temperature <= (
        TEMP_THRESHOLD_HIGH + 2
    )
    pressure_ambiguous = pressure >= (PRESSURE_THRESHOLD_HIGH - 10) and pressure <= (
        PRESSURE_THRESHOLD_HIGH + 10
    )

    # This looks like it adds xenon condition, but it's actually unreachable because
    # if xenon>30 and temp/pressure are in ranges, the first two conditions already cover it
    xenon_extreme = xenon_level > 30

    return (temp_ambiguous and pressure_ambiguous) or (
        xenon_extreme and temp_ambiguous and pressure >= PRESSURE_THRESHOLD_HIGH
    )


def classify_severity(
    temperature: float,
    pressure: float,
    neutron_flux: float,
    radiation_level: float,
    xenon_level: float,
    time_since_last_scram: float,
) -> ReactorState:
    """Classify severity based on parameter combinations with complex quorum logic."""
    # Check for critical conditions
    temp_critical = temperature >= TEMP_THRESHOLD_CRITICAL
    pressure_critical = pressure >= PRESSURE_THRESHOLD_CRITICAL
    flux_critical = neutron_flux >= FLUX_THRESHOLD_CRITICAL
    radiation_critical = radiation_level >= RADIATION_THRESHOLD_CRITICAL
    xenon_high = xenon_level >= XENON_THRESHOLD_HIGH

    temp_high = temperature >= TEMP_THRESHOLD_HIGH
    pressure_high = pressure >= PRESSURE_THRESHOLD_HIGH
    flux_high = neutron_flux >= FLUX_THRESHOLD_HIGH
    radiation_high = radiation_level >= RADIATION_THRESHOLD_HIGH

    # Recent SCRAM changes thresholds
    recent_scram = time_since_last_scram < 12

    # Count critical conditions
    critical_count = sum(
        [temp_critical, pressure_critical, flux_critical, radiation_critical]
    )

    high_count = sum([temp_high, pressure_high, flux_high, radiation_high])

    # Complex quorum logic with interactions
    if critical_count >= 2:
        return ReactorState.EMERGENCY_SHUTDOWN
    # If recent SCRAM, lower threshold to 1 critical condition IF xenon is also high
    elif recent_scram and critical_count >= 1 and xenon_high:
        return ReactorState.EMERGENCY_SHUTDOWN
    # Temperature + Pressure combination is special: even at "high" (not critical),
    # both together trigger EmergencyShutdown
    elif temp_high and pressure_high and temperature >= 640 and pressure >= 2450:
        return ReactorState.EMERGENCY_SHUTDOWN
    # This looks important but is unreachable because if critical_count >= 1 and
    # high_count >= 4, we already hit critical_count >= 2
    elif critical_count >= 1 and high_count >= 4:
        return ReactorState.EMERGENCY_SHUTDOWN
    elif critical_count >= 1 or high_count >= 3:
        return ReactorState.HOT_STANDBY
    elif high_count >= 1:
        return ReactorState.POWER_OPERATION
    else:
        return ReactorState.SHUTDOWN


def apply_operator_override(
    base_state: ReactorState,
    override_type: OperatorOverrideType,
    temperature: float,
    pressure: float,
    control_rod_insertion: float,
    xenon_level: float,
    time_since_last_scram: float,
) -> ReactorState:
    """Apply operator override with multiple exception levels."""
    if override_type == OperatorOverrideType.NO_OVERRIDE:
        return base_state

    elif override_type == OperatorOverrideType.SUPPRESS_ALARM:
        # Can suppress alarm unless in EmergencyShutdown
        if base_state == ReactorState.EMERGENCY_SHUTDOWN:
            return base_state
        else:
            return ReactorState.SHUTDOWN

    elif override_type == OperatorOverrideType.DELAY_SCRAM:
        # Can delay SCRAM if conditions are marginal...
        conditions_marginal = (
            temperature < TEMP_THRESHOLD_CRITICAL
            and pressure < PRESSURE_THRESHOLD_CRITICAL
        )
        # ...AND control rods are sufficiently inserted...
        rods_adequate = control_rod_insertion >= 70

        # ...BUT if already EmergencyShutdown, override is ignored...
        if base_state == ReactorState.EMERGENCY_SHUTDOWN:
            return base_state
        # ...EXCEPT if it's been less than 6 hours since last SCRAM AND xenon < 15,
        # can delay even EmergencyShutdown
        elif (
            base_state == ReactorState.EMERGENCY_SHUTDOWN
            and time_since_last_scram < 6
            and xenon_level < 15
        ):
            return ReactorState.HOT_STANDBY
        # ...BUT only if control rods are VERY adequate (≥85%) for EmergencyShutdown override
        elif (
            base_state == ReactorState.EMERGENCY_SHUTDOWN
            and time_since_last_scram < 6
            and xenon_level < 15
            and control_rod_insertion >= 85
        ):
            return ReactorState.HOT_STANDBY
        elif conditions_marginal and rods_adequate:
            return ReactorState.POWER_OPERATION
        else:
            return base_state

    elif override_type == OperatorOverrideType.BYPASS_INTERLOCK:
        # Can bypass interlock for HotStandby...
        if base_state == ReactorState.HOT_STANDBY:
            return ReactorState.POWER_OPERATION
        # ...EXCEPT if temperature is critically high...
        elif temperature >= TEMP_THRESHOLD_CRITICAL:
            return base_state
        # ...BUT if pressure is low (<2000), can bypass even with critical temp
        elif temperature >= TEMP_THRESHOLD_CRITICAL and pressure < 2000:
            return ReactorState.POWER_OPERATION
        else:
            return base_state

    elif override_type == OperatorOverrideType.MAINTENANCE_MODE:
        # Maintenance mode forces Shutdown...
        if base_state == ReactorState.EMERGENCY_SHUTDOWN:
            return base_state
        # ...EXCEPT if conditions are safe (all parameters below moderate thresholds)...
        elif (
            temperature < TEMP_THRESHOLD_MODERATE
            and pressure < PRESSURE_THRESHOLD_MODERATE
        ):
            return ReactorState.SHUTDOWN
        # ...BUT if xenon is high, stay in current state instead
        elif (
            temperature < TEMP_THRESHOLD_MODERATE
            and pressure < PRESSURE_THRESHOLD_MODERATE
            and xenon_level >= XENON_THRESHOLD_HIGH
        ):
            return base_state
        else:
            return ReactorState.SHUTDOWN

    return base_state


def should_initiate_scram(
    recommended_state: ReactorState,
    safety_system_status: SafetySystemStatus,
    xenon_level: float,
    time_since_last_scram: float,
) -> bool:
    """Determine if SCRAM should be initiated with complex rules."""
    if recommended_state == ReactorState.EMERGENCY_SHUTDOWN:
        if safety_system_status == SafetySystemStatus.OPERATIONAL:
            return True
        elif safety_system_status == SafetySystemStatus.DEGRADED:
            return True
        elif safety_system_status == SafetySystemStatus.FAILED:
            return False  # Cannot SCRAM if system failed
    elif recommended_state == ReactorState.HOT_STANDBY:
        if safety_system_status == SafetySystemStatus.OPERATIONAL:
            return False
        elif safety_system_status == SafetySystemStatus.DEGRADED:
            return True  # Degraded system requires SCRAM for HotStandby
    # If recent SCRAM (<6hrs) and xenon high, require SCRAM even for PowerOperation
    elif recommended_state == ReactorState.POWER_OPERATION:
        if safety_system_status == SafetySystemStatus.OPERATIONAL:
            return time_since_last_scram < 6 and xenon_level >= XENON_THRESHOLD_HIGH
        elif safety_system_status == SafetySystemStatus.DEGRADED:
            return time_since_last_scram < 12  # Degraded is more conservative

    return False


def should_activate_eccs(
    recommended_state: ReactorState, temperature: float, xenon_level: float
) -> bool:
    """Determine ECCS activation with xenon interaction."""
    if recommended_state == ReactorState.EMERGENCY_SHUTDOWN:
        return temperature >= TEMP_THRESHOLD_HIGH
    # Xenon changes ECCS threshold interpretation
    elif recommended_state == ReactorState.HOT_STANDBY:
        if xenon_level >= XENON_THRESHOLD_HIGH:
            return temperature >= (TEMP_THRESHOLD_CRITICAL - 30)
        else:
            return temperature >= TEMP_THRESHOLD_CRITICAL
    else:
        return False


def should_isolate_containment(
    recommended_state: ReactorState, radiation_level: float, pressure: float
) -> bool:
    """Determine containment isolation."""
    # Requires EmergencyShutdown AND high radiation...
    # ...BUT if pressure is very low (<1500), containment is already compromised, so don't isolate
    return (
        recommended_state == ReactorState.EMERGENCY_SHUTDOWN
        and radiation_level >= RADIATION_THRESHOLD_HIGH
        and pressure >= 1500
    )


def determine_safety_response(
    temperature: float,
    pressure: float,
    neutron_flux: float,
    radiation_level: float,
    control_rod_insertion: float,
    xenon_level: float,
    time_since_last_scram: float,
    safety_system_status: SafetySystemStatus,
    operator_override: OperatorOverrideType,
    current_state: ReactorState,
) -> SafetyResponse:
    """
    Core decision function for nuclear reactor safety system.

    Monitors critical parameters and determines appropriate safety responses,
    balancing operator control with automatic safety protocols.
    """
    # Check validity - dead zone produces invalid response
    valid = not is_in_measurement_dead_zone(temperature, pressure, xenon_level)

    if not valid:
        return SafetyResponse(
            recommended_state=current_state,
            initiate_scram=False,
            activate_eccs=False,
            isolate_containment=False,
            response_valid=False,
        )

    # Classify base severity
    base_state = classify_severity(
        temperature,
        pressure,
        neutron_flux,
        radiation_level,
        xenon_level,
        time_since_last_scram,
    )

    # Apply operator override with exception logic
    final_state = apply_operator_override(
        base_state,
        operator_override,
        temperature,
        pressure,
        control_rod_insertion,
        xenon_level,
        time_since_last_scram,
    )

    # Determine specific safety actions
    scram = should_initiate_scram(
        final_state, safety_system_status, xenon_level, time_since_last_scram
    )
    eccs = should_activate_eccs(final_state, temperature, xenon_level)
    containment = should_isolate_containment(final_state, radiation_level, pressure)

    return SafetyResponse(
        recommended_state=final_state,
        initiate_scram=scram,
        activate_eccs=eccs,
        isolate_containment=containment,
        response_valid=True,
    )
