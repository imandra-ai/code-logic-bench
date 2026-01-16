from dataclasses import dataclass
from enum import Enum, auto


class TransportMode(Enum):
    """Transportation modes available for cargo routing."""

    TRUCK = auto()
    RAIL = auto()
    AIR = auto()
    SEA = auto()


class Weather(Enum):
    """Weather conditions affecting transport."""

    CLEAR = auto()
    RAIN = auto()
    SNOW = auto()
    STORM = auto()
    HURRICANE = auto()


class GeopoliticalRisk(Enum):
    """Geopolitical risk levels for route assessment."""

    STABLE = auto()
    TENSIONS = auto()
    SANCTIONS = auto()
    WAR_ZONE = auto()


class CargoType(Enum):
    """Types of cargo being transported."""

    STANDARD = auto()
    FRAGILE = auto()
    HAZARDOUS = auto()
    PERISHABLE = auto()


@dataclass
class RouteDecision:
    """Result of route decision evaluation."""

    approved: bool
    adjusted_cost: int
    adjusted_time: int
    emergency_routing: bool


def _base_cost_by_mode(mode: TransportMode) -> int:
    """Return base cost for the given transport mode."""
    return {
        TransportMode.TRUCK: 100,
        TransportMode.RAIL: 150,
        TransportMode.AIR: 500,
        TransportMode.SEA: 200,
    }[mode]


def _base_time_by_mode(mode: TransportMode) -> int:
    """Return base time in hours for the given transport mode."""
    return {
        TransportMode.TRUCK: 48,
        TransportMode.RAIL: 72,
        TransportMode.AIR: 8,
        TransportMode.SEA: 336,  # 14 days
    }[mode]


def _weather_cost_multiplier(mode: TransportMode, weather: Weather) -> int:
    """Calculate weather-related cost multiplier based on mode and conditions."""
    multipliers = {
        # Air is sensitive to storms
        (TransportMode.AIR, Weather.STORM): 3,
        (TransportMode.AIR, Weather.HURRICANE): 5,
        (TransportMode.AIR, Weather.SNOW): 2,
        (TransportMode.AIR, Weather.RAIN): 1,
        (TransportMode.AIR, Weather.CLEAR): 1,
        # Sea is sensitive to hurricanes
        (TransportMode.SEA, Weather.HURRICANE): 4,
        (TransportMode.SEA, Weather.STORM): 2,
        (TransportMode.SEA, Weather.RAIN): 1,
        (TransportMode.SEA, Weather.SNOW): 1,
        (TransportMode.SEA, Weather.CLEAR): 1,
        # Truck sensitive to snow
        (TransportMode.TRUCK, Weather.SNOW): 3,
        (TransportMode.TRUCK, Weather.STORM): 2,
        (TransportMode.TRUCK, Weather.RAIN): 1,
        (TransportMode.TRUCK, Weather.HURRICANE): 2,
        (TransportMode.TRUCK, Weather.CLEAR): 1,
        # Rail relatively stable
        (TransportMode.RAIL, Weather.HURRICANE): 2,
        (TransportMode.RAIL, Weather.STORM): 1,
        (TransportMode.RAIL, Weather.SNOW): 1,
        (TransportMode.RAIL, Weather.RAIN): 1,
        (TransportMode.RAIL, Weather.CLEAR): 1,
    }
    return multipliers[(mode, weather)]


def _geopolitical_cost_multiplier(mode: TransportMode, risk: GeopoliticalRisk) -> int:
    """Calculate geopolitical risk cost multiplier based on mode and risk level."""
    multipliers = {
        # Air can bypass many risks
        (TransportMode.AIR, GeopoliticalRisk.WAR_ZONE): 4,
        (TransportMode.AIR, GeopoliticalRisk.SANCTIONS): 2,
        (TransportMode.AIR, GeopoliticalRisk.TENSIONS): 1,
        (TransportMode.AIR, GeopoliticalRisk.STABLE): 1,
        # Sea heavily affected by tensions/war
        (TransportMode.SEA, GeopoliticalRisk.WAR_ZONE): 5,
        (TransportMode.SEA, GeopoliticalRisk.SANCTIONS): 3,
        (TransportMode.SEA, GeopoliticalRisk.TENSIONS): 2,
        (TransportMode.SEA, GeopoliticalRisk.STABLE): 1,
        # Land routes moderately affected
        (TransportMode.TRUCK, GeopoliticalRisk.WAR_ZONE): 3,
        (TransportMode.TRUCK, GeopoliticalRisk.SANCTIONS): 2,
        (TransportMode.TRUCK, GeopoliticalRisk.TENSIONS): 1,
        (TransportMode.TRUCK, GeopoliticalRisk.STABLE): 1,
        (TransportMode.RAIL, GeopoliticalRisk.WAR_ZONE): 3,
        (TransportMode.RAIL, GeopoliticalRisk.SANCTIONS): 2,
        (TransportMode.RAIL, GeopoliticalRisk.TENSIONS): 1,
        (TransportMode.RAIL, GeopoliticalRisk.STABLE): 1,
    }
    return multipliers[(mode, risk)]


def _cargo_restrictions(mode: TransportMode, cargo: CargoType) -> bool:
    """Check if cargo type is allowed on the given transport mode."""
    # Hazardous cannot fly
    if mode == TransportMode.AIR and cargo == CargoType.HAZARDOUS:
        return False
    # Perishable cannot use slow sea routes
    if mode == TransportMode.SEA and cargo == CargoType.PERISHABLE:
        return False
    return True


def _is_route_viable(
    mode: TransportMode, weather: Weather, geopolitical: GeopoliticalRisk
) -> bool:
    """Check if route is viable under current conditions."""
    extreme_risk = (
        weather == Weather.HURRICANE and geopolitical == GeopoliticalRisk.WAR_ZONE
    )
    air_grounded = (
        mode == TransportMode.AIR
        and weather == Weather.HURRICANE
        and geopolitical == GeopoliticalRisk.SANCTIONS
    )
    return not (extreme_risk or air_grounded)


def _calculate_cost(
    mode: TransportMode, weather: Weather, geopolitical: GeopoliticalRisk
) -> int:
    """Calculate adjusted cost based on mode, weather, and geopolitical factors."""
    base = _base_cost_by_mode(mode)
    weather_mult = _weather_cost_multiplier(mode, weather)
    geo_mult = _geopolitical_cost_multiplier(mode, geopolitical)
    return base * weather_mult * geo_mult


def _calculate_time(mode: TransportMode, weather: Weather) -> int:
    """Calculate adjusted time based on mode and weather conditions."""
    base = _base_time_by_mode(mode)
    time_mult = {
        Weather.CLEAR: 1,
        Weather.RAIN: 1,
        Weather.SNOW: 2,
        Weather.STORM: 2,
        Weather.HURRICANE: 3,
    }[weather]
    return base * time_mult


def _check_emergency_conditions(
    cargo_value: int, time_critical: int, route_cost: int, route_time: int
) -> bool:
    """Check if emergency routing should be activated."""
    c1 = cargo_value > 100000
    c2 = time_critical < 24
    c3 = route_cost < 1000
    c4 = route_time < 72

    count = sum([c1, c2, c3, c4])
    return count >= 3


def determine_route_decision(
    mode: TransportMode,
    cargo: CargoType,
    weather: Weather,
    geopolitical: GeopoliticalRisk,
    cargo_value: int,
    time_critical: int,
) -> RouteDecision:
    """
    Evaluate and determine route decision based on transport parameters.

    Args:
        mode: Transportation mode to use
        cargo: Type of cargo being transported
        weather: Current weather conditions
        geopolitical: Geopolitical risk level
        cargo_value: Value of the cargo
        time_critical: Time criticality threshold in hours

    Returns:
        RouteDecision with approval status, adjusted cost/time, and emergency routing flag
    """
    cargo_approved = _cargo_restrictions(mode, cargo)

    if not cargo_approved:
        return RouteDecision(
            approved=False, adjusted_cost=0, adjusted_time=0, emergency_routing=False
        )

    viable = _is_route_viable(mode, weather, geopolitical)

    if not viable:
        return RouteDecision(
            approved=False, adjusted_cost=0, adjusted_time=0, emergency_routing=False
        )

    cost = _calculate_cost(mode, weather, geopolitical)
    time = _calculate_time(mode, weather)
    emergency = _check_emergency_conditions(cargo_value, time_critical, cost, time)

    return RouteDecision(
        approved=True,
        adjusted_cost=cost,
        adjusted_time=time,
        emergency_routing=emergency,
    )
