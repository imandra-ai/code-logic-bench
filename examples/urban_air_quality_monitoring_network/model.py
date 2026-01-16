from enum import Enum
from typing import NamedTuple


class PollutantType(Enum):
    """Types of air pollutants monitored by the system."""

    PM25 = "PM25"
    NO2 = "NO2"
    OZONE = "Ozone"
    CO = "CO"
    SO2 = "SO2"


class SensorStatus(Enum):
    """Status of the monitoring sensor."""

    ACTIVE = "Active"
    FAULTY = "Faulty"
    CALIBRATING = "Calibrating"


class AlertLevel(Enum):
    """Air quality alert levels based on WHO guidelines."""

    NORMAL = "Normal"
    MODERATE = "Moderate"
    UNHEALTHY = "Unhealthy"
    VERY_UNHEALTHY = "VeryUnhealthy"
    HAZARDOUS = "Hazardous"


class WeatherCondition(Enum):
    """Weather conditions affecting pollutant dispersion."""

    CLEAR = "Clear"
    CLOUDY = "Cloudy"
    RAINY = "Rainy"
    WINDY = "Windy"
    FOGGY = "Foggy"


class MonitoringResponse(NamedTuple):
    """Response from the air quality monitoring system."""

    final_alert_level: AlertLevel
    trigger_emergency: bool
    reading_valid: bool
    adjusted_reading: int


def base_threshold(pollutant: PollutantType, level: AlertLevel) -> int:
    """
    WHO Air Quality Guidelines - Base thresholds (μg/m³).

    Args:
        pollutant: Type of pollutant
        level: Alert level

    Returns:
        Threshold value in μg/m³
    """
    thresholds = {
        (PollutantType.PM25, AlertLevel.MODERATE): 15,
        (PollutantType.PM25, AlertLevel.UNHEALTHY): 35,
        (PollutantType.PM25, AlertLevel.VERY_UNHEALTHY): 75,
        (PollutantType.PM25, AlertLevel.HAZARDOUS): 150,
        (PollutantType.NO2, AlertLevel.MODERATE): 25,
        (PollutantType.NO2, AlertLevel.UNHEALTHY): 50,
        (PollutantType.NO2, AlertLevel.VERY_UNHEALTHY): 100,
        (PollutantType.NO2, AlertLevel.HAZARDOUS): 200,
        (PollutantType.OZONE, AlertLevel.MODERATE): 100,
        (PollutantType.OZONE, AlertLevel.UNHEALTHY): 160,
        (PollutantType.OZONE, AlertLevel.VERY_UNHEALTHY): 240,
        (PollutantType.OZONE, AlertLevel.HAZARDOUS): 300,
        (PollutantType.CO, AlertLevel.MODERATE): 10,
        (PollutantType.CO, AlertLevel.UNHEALTHY): 20,
        (PollutantType.CO, AlertLevel.VERY_UNHEALTHY): 40,
        (PollutantType.CO, AlertLevel.HAZARDOUS): 60,
        (PollutantType.SO2, AlertLevel.MODERATE): 20,
        (PollutantType.SO2, AlertLevel.UNHEALTHY): 50,
        (PollutantType.SO2, AlertLevel.VERY_UNHEALTHY): 100,
        (PollutantType.SO2, AlertLevel.HAZARDOUS): 200,
    }
    return thresholds.get((pollutant, level), 0)


def weather_adjusted_threshold(
    pollutant: PollutantType, level: AlertLevel, weather: WeatherCondition
) -> int:
    """
    Adjust threshold based on weather conditions affecting pollutant dispersion.

    Args:
        pollutant: Type of pollutant
        level: Alert level
        weather: Current weather condition

    Returns:
        Weather-adjusted threshold value
    """
    base = base_threshold(pollutant, level)

    if pollutant == PollutantType.PM25 and weather == WeatherCondition.FOGGY:
        return (base * 4) // 5  # 20% stricter
    elif pollutant == PollutantType.PM25 and weather == WeatherCondition.RAINY:
        return (base * 13) // 10  # 30% relaxed
    elif pollutant == PollutantType.OZONE and weather == WeatherCondition.CLEAR:
        return (base * 17) // 20  # 15% stricter
    elif pollutant == PollutantType.NO2 and weather == WeatherCondition.WINDY:
        return (base * 11) // 10  # 10% relaxed
    else:
        return base


def apply_drift(raw_reading: int, drift_factor: int) -> int:
    """Apply sensor drift adjustment to raw reading."""
    return (raw_reading * drift_factor) // 100


def classify_base_level(
    reading: int, pollutant: PollutantType, weather: WeatherCondition
) -> AlertLevel:
    """
    Classify base alert level from sensor reading.

    Args:
        reading: Adjusted sensor reading
        pollutant: Type of pollutant
        weather: Current weather condition

    Returns:
        Base alert level before fault escalation
    """
    hazardous_threshold = weather_adjusted_threshold(
        pollutant, AlertLevel.HAZARDOUS, weather
    )
    very_unhealthy_threshold = weather_adjusted_threshold(
        pollutant, AlertLevel.VERY_UNHEALTHY, weather
    )
    unhealthy_threshold = weather_adjusted_threshold(
        pollutant, AlertLevel.UNHEALTHY, weather
    )
    moderate_threshold = weather_adjusted_threshold(
        pollutant, AlertLevel.MODERATE, weather
    )

    if reading >= hazardous_threshold:
        return AlertLevel.HAZARDOUS
    elif reading >= very_unhealthy_threshold:
        return AlertLevel.VERY_UNHEALTHY
    elif reading >= unhealthy_threshold:
        return AlertLevel.UNHEALTHY
    elif reading >= moderate_threshold:
        return AlertLevel.MODERATE
    else:
        return AlertLevel.NORMAL


def apply_fault_escalation(
    base_level: AlertLevel,
    drift_factor: int,
    weather: WeatherCondition,
    pollutant: PollutantType,
    status: SensorStatus,
) -> AlertLevel:
    """
    Apply fault escalation logic with weather and drift overrides.

    Args:
        base_level: Base alert level
        drift_factor: Sensor drift factor
        weather: Current weather condition
        pollutant: Type of pollutant
        status: Sensor status

    Returns:
        Final alert level after fault escalation
    """
    if status == SensorStatus.ACTIVE:
        return base_level
    elif status == SensorStatus.CALIBRATING:
        # Override: Calibrating sensors always report Normal
        return AlertLevel.NORMAL
    elif status == SensorStatus.FAULTY:
        # Faulty sensors escalate severity
        escalation_map = {
            AlertLevel.NORMAL: AlertLevel.MODERATE,
            AlertLevel.MODERATE: AlertLevel.UNHEALTHY,
            AlertLevel.UNHEALTHY: AlertLevel.VERY_UNHEALTHY,
            AlertLevel.VERY_UNHEALTHY: AlertLevel.HAZARDOUS,
            AlertLevel.HAZARDOUS: AlertLevel.HAZARDOUS,
        }
        escalated = escalation_map[base_level]

        # BUT if drift is acceptable AND weather is favorable, override the escalation
        drift_acceptable = 90 <= drift_factor <= 110
        weather_favorable = (
            pollutant == PollutantType.PM25 and weather == WeatherCondition.RAINY
        ) or (pollutant == PollutantType.NO2 and weather == WeatherCondition.WINDY)

        # EXCEPT if already at Hazardous, always escalate
        if base_level == AlertLevel.HAZARDOUS:
            return escalated
        elif drift_acceptable and weather_favorable:
            return base_level
        else:
            return escalated

    return base_level


def check_emergency_conditions(
    alert_level: AlertLevel,
    weather: WeatherCondition,
    drift_factor: int,
    time_since_last_alert: int,
) -> bool:
    """
    Check if emergency response should be triggered (requires 2+ conditions).

    Args:
        alert_level: Current alert level
        weather: Current weather condition
        drift_factor: Sensor drift factor
        time_since_last_alert: Hours since last alert

    Returns:
        True if emergency should be triggered
    """
    condition1 = alert_level in (AlertLevel.HAZARDOUS, AlertLevel.VERY_UNHEALTHY)
    condition2 = weather == WeatherCondition.FOGGY
    condition3 = drift_factor < 90 or drift_factor > 110
    condition4 = time_since_last_alert < 24

    count = sum([condition1, condition2, condition3, condition4])
    return count >= 2


def is_reading_valid(raw_reading: int, drift_factor: int) -> bool:
    """
    Check if sensor reading is valid.

    Args:
        raw_reading: Raw sensor reading
        drift_factor: Sensor drift factor

    Returns:
        True if reading is valid
    """
    # Dead zone: readings in 148-152 range with drift 98-102 are ambiguous
    in_dead_zone = (148 <= raw_reading <= 152) and (98 <= drift_factor <= 102)

    # Also invalid if drift is extreme
    extreme_drift = drift_factor < 80 or drift_factor > 120

    return not (in_dead_zone or extreme_drift)


def determine_monitoring_response(
    raw_reading: int,
    pollutant: PollutantType,
    sensor_status: SensorStatus,
    drift_factor: int,
    weather: WeatherCondition,
    time_since_last_alert: int,
) -> MonitoringResponse:
    """
    Core decision function for urban air quality monitoring system.

    Processes sensor readings with drift calibration, weather-adjusted thresholds,
    fault escalation logic, and emergency trigger conditions.

    Args:
        raw_reading: Raw sensor reading (μg/m³)
        pollutant: Type of pollutant being measured
        sensor_status: Current status of the sensor
        drift_factor: Calibration drift factor (percentage)
        weather: Current weather condition
        time_since_last_alert: Hours since last alert

    Returns:
        MonitoringResponse with alert level, emergency trigger, validity, and adjusted reading
    """
    # Check validity first
    valid = is_reading_valid(raw_reading, drift_factor)

    if not valid:
        return MonitoringResponse(
            final_alert_level=AlertLevel.NORMAL,
            trigger_emergency=False,
            reading_valid=False,
            adjusted_reading=0,
        )

    # Apply drift adjustment
    adjusted = apply_drift(raw_reading, drift_factor)

    # Classify base level with weather adjustment
    base_level = classify_base_level(adjusted, pollutant, weather)

    # Apply fault escalation with override logic
    final_level = apply_fault_escalation(
        base_level, drift_factor, weather, pollutant, sensor_status
    )

    # Check emergency quorum
    emergency = check_emergency_conditions(
        final_level, weather, drift_factor, time_since_last_alert
    )

    return MonitoringResponse(
        final_alert_level=final_level,
        trigger_emergency=emergency,
        reading_valid=True,
        adjusted_reading=adjusted,
    )
