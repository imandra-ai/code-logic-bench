from enum import Enum
from typing import NamedTuple


class FlightMode(Enum):
    """Available flight modes for the quadcopter."""

    MANUAL = "manual"
    STABILIZE = "stabilize"
    ALT_HOLD = "alt_hold"
    HOVER = "hover"
    RETURN_HOME = "return_home"
    EMERGENCY = "emergency"


class SensorHealth(Enum):
    """Health status of sensors."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class ControlDecision(NamedTuple):
    """Control decision output with safety constraints."""

    approved: bool
    force_emergency_landing: bool
    limit_max_tilt: bool
    reduce_responsiveness: bool


def is_autonomous_mode(mode: FlightMode) -> bool:
    """Check if mode allows autonomous flight."""
    return mode in (FlightMode.ALT_HOLD, FlightMode.HOVER, FlightMode.RETURN_HOME)


def battery_critical(battery_pct: float) -> bool:
    """Check if battery is at critical level."""
    return battery_pct < 15


def battery_low(battery_pct: float) -> bool:
    """Check if battery is at low level."""
    return battery_pct < 30


def tilt_dangerous(tilt_deg: float) -> bool:
    """Check if tilt angle is dangerous."""
    return tilt_deg > 45


def altitude_critical(altitude_m: float) -> bool:
    """Check if altitude is critically low (ground proximity)."""
    return altitude_m < 3  # Below 3m is ground proximity


def sensor_degradation_severe(
    imu_health: SensorHealth, gps_health: SensorHealth
) -> bool:
    """Check if sensor degradation affects control severely."""
    return imu_health == SensorHealth.FAILED or (
        imu_health == SensorHealth.DEGRADED and gps_health == SensorHealth.DEGRADED
    )


def requires_emergency_landing(
    battery_pct: float, tilt_deg: float, altitude_m: float, imu_health: SensorHealth
) -> bool:
    """Determine if emergency landing is required."""
    critical_battery = battery_critical(battery_pct)
    dangerous_tilt = tilt_dangerous(tilt_deg)
    near_ground = altitude_critical(altitude_m)
    sensor_failed = imu_health == SensorHealth.FAILED

    # Emergency if: critical battery OR (dangerous tilt AND near ground) OR sensor failed
    return critical_battery or (dangerous_tilt and near_ground) or sensor_failed


def determine_control_mode(
    mode: FlightMode,
    battery_pct: float,
    tilt_deg: float,
    altitude_m: float,
    imu_health: SensorHealth,
    gps_health: SensorHealth,
) -> ControlDecision:
    """
    Determine control mode approval based on flight conditions.

    Args:
        mode: Current flight mode
        battery_pct: Battery percentage (0-100)
        tilt_deg: Tilt angle in degrees
        altitude_m: Altitude in meters
        imu_health: IMU sensor health status
        gps_health: GPS sensor health status

    Returns:
        ControlDecision with approval status and safety constraints
    """
    # Check emergency landing conditions first
    emergency_needed = requires_emergency_landing(
        battery_pct, tilt_deg, altitude_m, imu_health
    )

    if emergency_needed:
        return ControlDecision(
            approved=False,
            force_emergency_landing=True,
            limit_max_tilt=True,
            reduce_responsiveness=True,
        )

    # Check if autonomous mode is safe
    autonomous = is_autonomous_mode(mode)

    if autonomous:
        # Autonomous needs good sensors
        sensors_ok = not sensor_degradation_severe(imu_health, gps_health)

        if not sensors_ok:
            # Degrade to manual control
            return ControlDecision(
                approved=False,
                force_emergency_landing=False,
                limit_max_tilt=True,
                reduce_responsiveness=True,
            )

        # Check battery for autonomous
        battery_ok = not battery_low(battery_pct)

        if not battery_ok:
            # Low battery: limit autonomous capabilities
            return ControlDecision(
                approved=False,
                force_emergency_landing=False,
                limit_max_tilt=True,
                reduce_responsiveness=False,
            )

        # Autonomous approved
        return ControlDecision(
            approved=True,
            force_emergency_landing=False,
            limit_max_tilt=False,
            reduce_responsiveness=False,
        )
    else:
        # Manual/Stabilize modes: always approved unless emergency
        limit_tilt = battery_low(battery_pct) or imu_health == SensorHealth.DEGRADED
        reduce_resp = gps_health == SensorHealth.DEGRADED

        return ControlDecision(
            approved=True,
            force_emergency_landing=False,
            limit_max_tilt=limit_tilt,
            reduce_responsiveness=reduce_resp,
        )
