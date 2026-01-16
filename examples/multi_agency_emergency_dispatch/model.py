from enum import Enum
from dataclasses import dataclass
from typing import NamedTuple


class IncidentCategory(Enum):
    ROUTINE_MEDICAL = "RoutineMedical"
    SERIOUS_MEDICAL = "SeriousMedical"
    CRITICAL_MEDICAL = "CriticalMedical"
    ROUTINE_FIRE = "RoutineFire"
    SERIOUS_FIRE = "SeriousFire"
    CRITICAL_FIRE = "CriticalFire"


class ResourceType(Enum):
    AMBULANCE = "Ambulance"
    FIRE_TRUCK = "FireTruck"
    POLICE_UNIT = "PoliceUnit"
    HELICOPTER = "Helicopter"
    HAZMAT_TEAM = "HazmatTeam"


class WeatherCondition(Enum):
    CLEAR = "Clear"
    RAIN = "Rain"
    SNOW = "Snow"
    STORM = "Storm"


class TrafficLevel(Enum):
    LIGHT = "Light"
    MODERATE = "Moderate"
    HEAVY = "Heavy"
    GRIDLOCK = "Gridlock"


class DispatchDecision(NamedTuple):
    dispatch_approved: bool
    response_time_minutes: int
    requires_backup: bool
    escalation_needed: bool


def _category_priority(incident_category: IncidentCategory) -> int:
    """Return base priority for an incident category."""
    priority_map = {
        IncidentCategory.ROUTINE_MEDICAL: 4,
        IncidentCategory.SERIOUS_MEDICAL: 8,
        IncidentCategory.CRITICAL_MEDICAL: 16,
        IncidentCategory.ROUTINE_FIRE: 6,
        IncidentCategory.SERIOUS_FIRE: 12,
        IncidentCategory.CRITICAL_FIRE: 24,
    }
    return priority_map[incident_category]


def _resource_compatible(
    incident_category: IncidentCategory, resource_type: ResourceType
) -> bool:
    """Check if a resource type is compatible with an incident category."""
    compatibility = {
        (IncidentCategory.ROUTINE_MEDICAL, ResourceType.AMBULANCE): True,
        (IncidentCategory.ROUTINE_MEDICAL, ResourceType.POLICE_UNIT): True,
        (IncidentCategory.ROUTINE_MEDICAL, ResourceType.HELICOPTER): True,
        (IncidentCategory.SERIOUS_MEDICAL, ResourceType.AMBULANCE): True,
        (IncidentCategory.SERIOUS_MEDICAL, ResourceType.HELICOPTER): True,
        (IncidentCategory.CRITICAL_MEDICAL, ResourceType.AMBULANCE): True,
        (IncidentCategory.CRITICAL_MEDICAL, ResourceType.HELICOPTER): True,
        (IncidentCategory.CRITICAL_MEDICAL, ResourceType.HAZMAT_TEAM): True,
        (IncidentCategory.ROUTINE_FIRE, ResourceType.FIRE_TRUCK): True,
        (IncidentCategory.ROUTINE_FIRE, ResourceType.POLICE_UNIT): True,
        (IncidentCategory.SERIOUS_FIRE, ResourceType.FIRE_TRUCK): True,
        (IncidentCategory.SERIOUS_FIRE, ResourceType.HAZMAT_TEAM): True,
        (IncidentCategory.SERIOUS_FIRE, ResourceType.HELICOPTER): True,
        (IncidentCategory.CRITICAL_FIRE, ResourceType.FIRE_TRUCK): True,
        (IncidentCategory.CRITICAL_FIRE, ResourceType.HAZMAT_TEAM): True,
        (IncidentCategory.CRITICAL_FIRE, ResourceType.HELICOPTER): True,
    }
    return compatibility.get((incident_category, resource_type), False)


def _weather_time_multiplier(
    resource_type: ResourceType, weather: WeatherCondition
) -> int:
    """Return weather-based time multiplier for a resource type."""
    multipliers = {
        (ResourceType.AMBULANCE, WeatherCondition.CLEAR): 10,
        (ResourceType.AMBULANCE, WeatherCondition.RAIN): 13,
        (ResourceType.AMBULANCE, WeatherCondition.SNOW): 18,
        (ResourceType.AMBULANCE, WeatherCondition.STORM): 25,
        (ResourceType.FIRE_TRUCK, WeatherCondition.CLEAR): 10,
        (ResourceType.FIRE_TRUCK, WeatherCondition.RAIN): 14,
        (ResourceType.FIRE_TRUCK, WeatherCondition.SNOW): 20,
        (ResourceType.FIRE_TRUCK, WeatherCondition.STORM): 28,
        (ResourceType.POLICE_UNIT, WeatherCondition.CLEAR): 10,
        (ResourceType.POLICE_UNIT, WeatherCondition.RAIN): 12,
        (ResourceType.POLICE_UNIT, WeatherCondition.SNOW): 16,
        (ResourceType.POLICE_UNIT, WeatherCondition.STORM): 22,
        (ResourceType.HELICOPTER, WeatherCondition.CLEAR): 10,
        (ResourceType.HELICOPTER, WeatherCondition.RAIN): 18,
        (ResourceType.HELICOPTER, WeatherCondition.SNOW): 40,
        (ResourceType.HELICOPTER, WeatherCondition.STORM): 100,
        (ResourceType.HAZMAT_TEAM, WeatherCondition.CLEAR): 15,
        (ResourceType.HAZMAT_TEAM, WeatherCondition.RAIN): 20,
        (ResourceType.HAZMAT_TEAM, WeatherCondition.SNOW): 30,
        (ResourceType.HAZMAT_TEAM, WeatherCondition.STORM): 45,
    }
    return multipliers[(resource_type, weather)]


def _traffic_time_multiplier(resource_type: ResourceType, traffic: TrafficLevel) -> int:
    """Return traffic-based time multiplier for a resource type."""
    # Air units bypass traffic
    if resource_type == ResourceType.HELICOPTER:
        return 10

    multipliers = {
        (ResourceType.AMBULANCE, TrafficLevel.LIGHT): 10,
        (ResourceType.AMBULANCE, TrafficLevel.MODERATE): 15,
        (ResourceType.AMBULANCE, TrafficLevel.HEAVY): 25,
        (ResourceType.AMBULANCE, TrafficLevel.GRIDLOCK): 50,
        (ResourceType.FIRE_TRUCK, TrafficLevel.LIGHT): 10,
        (ResourceType.FIRE_TRUCK, TrafficLevel.MODERATE): 14,
        (ResourceType.FIRE_TRUCK, TrafficLevel.HEAVY): 22,
        (ResourceType.FIRE_TRUCK, TrafficLevel.GRIDLOCK): 45,
        (ResourceType.POLICE_UNIT, TrafficLevel.LIGHT): 10,
        (ResourceType.POLICE_UNIT, TrafficLevel.MODERATE): 12,
        (ResourceType.POLICE_UNIT, TrafficLevel.HEAVY): 18,
        (ResourceType.POLICE_UNIT, TrafficLevel.GRIDLOCK): 35,
        (ResourceType.HAZMAT_TEAM, TrafficLevel.LIGHT): 10,
        (ResourceType.HAZMAT_TEAM, TrafficLevel.MODERATE): 18,
        (ResourceType.HAZMAT_TEAM, TrafficLevel.HEAVY): 30,
        (ResourceType.HAZMAT_TEAM, TrafficLevel.GRIDLOCK): 60,
    }
    return multipliers[(resource_type, traffic)]


def _calculate_response_time(
    distance: int,
    resource_type: ResourceType,
    weather: WeatherCondition,
    traffic: TrafficLevel,
) -> int:
    """Calculate response time based on distance and conditions."""
    weather_mult = _weather_time_multiplier(resource_type, weather)
    traffic_mult = _traffic_time_multiplier(resource_type, traffic)
    return (distance * weather_mult * traffic_mult) // 100


def _critical_override(
    incident_category: IncidentCategory,
    fuel_level: int,
    distance: int,
    weather: WeatherCondition,
) -> bool:
    """Check if critical override applies (bypass fuel constraints)."""
    is_critical = incident_category in (
        IncidentCategory.CRITICAL_MEDICAL,
        IncidentCategory.CRITICAL_FIRE,
    )
    distance_ok = distance < 20
    weather_ok = weather != WeatherCondition.STORM
    fuel_marginal = fuel_level >= 15
    return is_critical and distance_ok and weather_ok and fuel_marginal


def _minimum_fuel_requirement(incident_category: IncidentCategory) -> int:
    """Return minimum fuel requirement based on incident priority."""
    priority = _category_priority(incident_category)
    if priority >= 20:
        return 25  # Critical: 25% minimum
    elif priority >= 10:
        return 35  # Serious: 35% minimum
    else:
        return 50  # Routine: 50% minimum


def _in_fuel_dead_zone(fuel_level: int, distance: int) -> bool:
    """Check if fuel and distance fall in ambiguous dead zone."""
    return 25 <= fuel_level <= 35 and 15 <= distance <= 25


def _backup_required(incident_category: IncidentCategory) -> bool:
    """Check if backup is required for the incident category."""
    return incident_category in (
        IncidentCategory.CRITICAL_MEDICAL,
        IncidentCategory.CRITICAL_FIRE,
        IncidentCategory.SERIOUS_FIRE,
    )


def determine_dispatch_decision(
    incident_category: IncidentCategory,
    distance_to_incident: int,
    resource_type: ResourceType,
    fuel_level: int,
    resource_ready: bool,
    weather: WeatherCondition,
    traffic: TrafficLevel,
) -> DispatchDecision:
    """
    Determine whether to dispatch emergency resources to an incident.

    Implements a multi-criteria decision system with:
    - Life-threatening incident overrides that bypass fuel constraints
    - Priority-dependent minimum fuel requirements
    - Fuel-distance dead zones for marginal situations
    - Quorum-based dispatch approval requiring multiple operational criteria

    Args:
        incident_category: Type and severity of the incident
        distance_to_incident: Distance in appropriate units
        resource_type: Type of emergency resource
        fuel_level: Current fuel level percentage
        resource_ready: Whether resource is operationally ready
        weather: Current weather conditions
        traffic: Current traffic level

    Returns:
        DispatchDecision with approval status, response time, backup needs, and escalation flag
    """
    # Check fuel dead zone first
    in_dead_zone = _in_fuel_dead_zone(fuel_level, distance_to_incident)

    if in_dead_zone:
        # Dead zone → dispatch but mark escalation needed
        response_time = _calculate_response_time(
            distance_to_incident, resource_type, weather, traffic
        )
        return DispatchDecision(
            dispatch_approved=True,
            response_time_minutes=response_time,
            requires_backup=True,
            escalation_needed=True,
        )

    # Check critical override
    use_override = _critical_override(
        incident_category, fuel_level, distance_to_incident, weather
    )

    if use_override:
        # Override: dispatch despite marginal fuel
        response_time = _calculate_response_time(
            distance_to_incident, resource_type, weather, traffic
        )
        return DispatchDecision(
            dispatch_approved=True,
            response_time_minutes=response_time,
            requires_backup=True,
            escalation_needed=False,
        )

    # Normal dispatch logic
    compatible = _resource_compatible(incident_category, resource_type)

    min_fuel = _minimum_fuel_requirement(incident_category)
    fuel_ok = fuel_level >= min_fuel

    response_time = _calculate_response_time(
        distance_to_incident, resource_type, weather, traffic
    )
    time_ok = response_time <= 30

    weather_safe = not (
        (resource_type == ResourceType.HELICOPTER)
        and (weather in (WeatherCondition.STORM, WeatherCondition.SNOW))
    )

    # Calculate dispatch score (5 factors)
    score = sum([compatible, fuel_ok, time_ok, resource_ready, weather_safe])

    # Need 4 out of 5 for dispatch
    if score >= 4:
        needs_backup = _backup_required(incident_category)
        return DispatchDecision(
            dispatch_approved=True,
            response_time_minutes=response_time,
            requires_backup=needs_backup,
            escalation_needed=False,
        )
    elif score >= 3:
        # Borderline: dispatch with escalation
        return DispatchDecision(
            dispatch_approved=True,
            response_time_minutes=response_time,
            requires_backup=True,
            escalation_needed=True,
        )
    else:
        # Cannot dispatch
        return DispatchDecision(
            dispatch_approved=False,
            response_time_minutes=0,
            requires_backup=False,
            escalation_needed=True,
        )
