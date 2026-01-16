from enum import Enum
from dataclasses import dataclass
from typing import Literal


class SensorStatus(Enum):
    """Sensor operational status."""

    ACTIVE = "Active"
    DEGRADED = "Degraded"


class Weather(Enum):
    """Weather conditions."""

    CLEAR = "Clear"
    RAIN = "Rain"


class ControlMode(Enum):
    """Lane keeping control mode."""

    FULL_AUTONOMOUS = "FullAutonomous"
    ASSISTED_DRIVING = "AssistedDriving"
    MANUAL_OVERRIDE = "ManualOverride"


@dataclass
class LaneKeepingDecision:
    """Lane keeping control decision output."""

    control_mode: ControlMode
    allow_steering: bool
    require_driver_alert: bool
    max_steering_angle: int  # degrees
    confidence_level: int  # 0-100


def _safe_distance_factor(weather: Weather, speed: int) -> int:
    """
    Calculate safe following distance multiplier (multiplexer pattern).

    Args:
        weather: Current weather condition
        speed: Vehicle speed in km/h

    Returns:
        Distance factor multiplier
    """
    base_factor = 10 if weather == Weather.CLEAR else 15

    # Speed affects safety margin
    if speed < 40:
        return base_factor
    else:
        return (base_factor * 13) // 10  # 30% increase


def _sensor_confidence(camera_status: SensorStatus, lidar_status: SensorStatus) -> int:
    """
    Calculate overall sensor confidence based on individual sensor states.

    Args:
        camera_status: Camera sensor status
        lidar_status: Lidar sensor status

    Returns:
        Confidence level (0-100)
    """
    if camera_status == SensorStatus.ACTIVE and lidar_status == SensorStatus.ACTIVE:
        return 95
    elif camera_status == SensorStatus.ACTIVE and lidar_status == SensorStatus.DEGRADED:
        return 75
    elif camera_status == SensorStatus.DEGRADED and lidar_status == SensorStatus.ACTIVE:
        return 70
    else:  # Both degraded
        return 40


def _visibility_acceptable(
    weather: Weather, time_of_day: int, sensor_conf: int
) -> bool:
    """
    Override pattern: weather degrades visibility BUT clear night is exception.

    Args:
        weather: Current weather condition
        time_of_day: Hour of day (0-23)
        sensor_conf: Sensor confidence level

    Returns:
        Whether visibility is acceptable for autonomous operation
    """
    if weather == Weather.CLEAR:
        # Clear weather allows operation...
        # ...EXCEPT at night (6pm-6am) with degraded sensors
        night = time_of_day < 6 or time_of_day >= 18
        degraded = sensor_conf < 70
        return not (night and degraded)
    else:  # Rain
        # Rain requires good sensors
        return sensor_conf >= 75


def _check_close_obstacle(obstacle_distance: int, speed: int, weather: Weather) -> bool:
    """
    Check if there is a close obstacle requiring intervention.

    Args:
        obstacle_distance: Distance to obstacle in meters
        speed: Vehicle speed in km/h
        weather: Current weather condition

    Returns:
        Whether obstacle is dangerously close
    """
    safe_dist = _safe_distance_factor(weather, speed)
    return obstacle_distance < safe_dist and speed > 15


def _requires_manual_override(
    camera_status: SensorStatus,
    lidar_status: SensorStatus,
    driver_intervention_time: int,
) -> bool:
    """
    Check if manual override is needed (quorum-based logic).

    Args:
        camera_status: Camera sensor status
        lidar_status: Lidar sensor status
        driver_intervention_time: Seconds since last driver intervention

    Returns:
        Whether manual override is required
    """
    both_degraded = (
        camera_status == SensorStatus.DEGRADED and lidar_status == SensorStatus.DEGRADED
    )
    long_intervention = driver_intervention_time > 15
    return both_degraded or long_intervention


def _is_valid_state(obstacle_distance: int, speed: int, lane_offset: int) -> bool:
    """
    Check if state is valid (not in dead zone or out of bounds).

    Args:
        obstacle_distance: Distance to obstacle in meters
        speed: Vehicle speed in km/h
        lane_offset: Lane offset in cm

    Returns:
        Whether the state is valid
    """
    # Dead zone: certain combinations are ambiguous
    in_dead_zone = (
        48 <= obstacle_distance <= 52 and 38 <= speed <= 42 and 28 <= lane_offset <= 32
    )

    # Invalid if values are out of reasonable bounds
    invalid_values = (
        obstacle_distance < 5
        or obstacle_distance > 100
        or speed < 10
        or speed > 80
        or lane_offset < 10
        or lane_offset > 60
    )

    return not (in_dead_zone or invalid_values)


def _calculate_max_steering(sensor_conf: int, speed: int) -> int:
    """
    Calculate maximum allowed steering angle.

    Args:
        sensor_conf: Sensor confidence level
        speed: Vehicle speed in km/h

    Returns:
        Maximum steering angle in degrees
    """
    base_angle = 45

    # Higher speed reduces max steering
    if speed < 30:
        speed_factor = 100
    elif speed < 60:
        speed_factor = 80
    else:
        speed_factor = 60

    # Lower confidence reduces max steering
    if sensor_conf >= 90:
        conf_factor = 100
    elif sensor_conf >= 70:
        conf_factor = 80
    else:
        conf_factor = 60

    return (base_angle * speed_factor * conf_factor) // 10000


def determine_lane_keeping_control(
    camera_status: SensorStatus,
    lidar_status: SensorStatus,
    weather: Weather,
    time_of_day: int,
    obstacle_distance: int,
    speed: int,
    lane_offset: int,
    driver_intervention_time: int,
) -> LaneKeepingDecision:
    """
    Determine appropriate lane keeping control mode based on system state.

    This controller determines the appropriate control mode (FullAutonomous,
    AssistedDriving, ManualOverride) based on sensor status, weather conditions,
    obstacle distance, vehicle speed, and driver intervention time.

    Args:
        camera_status: Camera sensor operational status
        lidar_status: Lidar sensor operational status
        weather: Current weather conditions
        time_of_day: Hour of day (0-23)
        obstacle_distance: Distance to nearest obstacle in meters
        speed: Vehicle speed in km/h
        lane_offset: Offset from lane center in cm
        driver_intervention_time: Seconds since last driver intervention

    Returns:
        Lane keeping decision with control mode and parameters
    """
    # Check validity first
    valid = _is_valid_state(obstacle_distance, speed, lane_offset)

    if not valid:
        return LaneKeepingDecision(
            control_mode=ControlMode.MANUAL_OVERRIDE,
            allow_steering=False,
            require_driver_alert=False,
            max_steering_angle=0,
            confidence_level=0,
        )

    # Calculate sensor confidence
    sensor_conf = _sensor_confidence(camera_status, lidar_status)

    # Check visibility
    visibility_ok = _visibility_acceptable(weather, time_of_day, sensor_conf)

    # Check close obstacle
    close_obstacle = _check_close_obstacle(obstacle_distance, speed, weather)

    # Check manual override requirements
    needs_manual = _requires_manual_override(
        camera_status, lidar_status, driver_intervention_time
    )

    # Determine control mode
    if close_obstacle or needs_manual or not visibility_ok:
        mode = ControlMode.MANUAL_OVERRIDE
    elif sensor_conf >= 90 and lane_offset < 25:
        mode = ControlMode.FULL_AUTONOMOUS
    else:
        mode = ControlMode.ASSISTED_DRIVING

    # Determine steering allowance
    steering_allowed = mode in (
        ControlMode.FULL_AUTONOMOUS,
        ControlMode.ASSISTED_DRIVING,
    )

    # Driver alert requirements
    alert_needed = (
        sensor_conf < 75
        or (mode == ControlMode.ASSISTED_DRIVING and lane_offset > 35)
        or close_obstacle
    )

    # Calculate max steering
    max_angle = _calculate_max_steering(sensor_conf, speed)

    return LaneKeepingDecision(
        control_mode=mode,
        allow_steering=steering_allowed,
        require_driver_alert=alert_needed,
        max_steering_angle=max_angle,
        confidence_level=sensor_conf,
    )
