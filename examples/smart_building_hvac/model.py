from enum import Enum
from typing import NamedTuple


class HVACMode(Enum):
    """HVAC operating modes"""

    OFF = "Off"
    VENTILATION = "Ventilation"
    HEATING = "Heating"
    COOLING = "Cooling"
    EMERGENCY = "Emergency"


class OccupancyLevel(Enum):
    """Building occupancy status"""

    EMPTY = "Empty"
    OCCUPIED = "Occupied"


class Season(Enum):
    """Current season"""

    SUMMER = "Summer"
    WINTER = "Winter"


class EmergencyState(Enum):
    """Emergency system states"""

    NO_EMERGENCY = "NoEmergency"
    FIRE_ALARM = "FireAlarm"
    MAINTENANCE_MODE = "MaintenanceMode"


class TempNeed(Enum):
    """Temperature comfort classification"""

    NO_HEATING = "NoHeating"
    COMFORTABLE = "Comfortable"
    MILD_HEATING = "MildHeating"
    NEED_HEATING = "NeedHeating"
    MILD_COOLING = "MildCooling"
    NEED_COOLING = "NeedCooling"


class HVACControlDecision(NamedTuple):
    """HVAC control decision output"""

    selected_mode: HVACMode
    fan_speed: int
    requires_override: bool


def classify_temp_need(
    temp_diff: float, season: Season, occupancy: OccupancyLevel
) -> TempNeed:
    """
    Classify temperature needs based on temperature differential, season, and occupancy.

    Args:
        temp_diff: Temperature differential value
        season: Current season (Summer/Winter)
        occupancy: Current occupancy level

    Returns:
        Temperature need classification
    """
    if occupancy == OccupancyLevel.EMPTY:
        return TempNeed.NO_HEATING

    if season == Season.SUMMER and occupancy == OccupancyLevel.OCCUPIED:
        if temp_diff >= 4:
            return TempNeed.NEED_COOLING
        elif temp_diff >= 2:
            return TempNeed.MILD_COOLING
        else:
            return TempNeed.COMFORTABLE

    if season == Season.WINTER and occupancy == OccupancyLevel.OCCUPIED:
        if temp_diff >= 4:
            return TempNeed.NEED_HEATING
        elif temp_diff >= 2:
            return TempNeed.MILD_HEATING
        else:
            return TempNeed.COMFORTABLE

    return TempNeed.COMFORTABLE


def in_dead_zone(temp_diff: float) -> bool:
    """Check if temperature differential is in the dead zone (temp_diff = 3)"""
    return temp_diff == 3


def apply_emergency_mode(
    base_mode: HVACMode,
    emergency_state: EmergencyState,
    battery_level: float,
    maintenance_hours: float,
) -> HVACMode:
    """
    Apply emergency overrides with sub-exceptions.

    Args:
        base_mode: Base HVAC mode before emergency considerations
        emergency_state: Current emergency state
        battery_level: Battery level percentage
        maintenance_hours: Hours since last maintenance

    Returns:
        Mode after applying emergency logic
    """
    if emergency_state == EmergencyState.FIRE_ALARM:
        # Fire forces Emergency...
        # ...EXCEPT if battery critical AND maintenance overdue, must go Off
        if battery_level < 10 and maintenance_hours > 10000:
            return HVACMode.OFF
        else:
            return HVACMode.EMERGENCY

    elif emergency_state == EmergencyState.MAINTENANCE_MODE:
        # Maintenance forces Off...
        # ...EXCEPT if battery OK and maintenance not too overdue, allow Ventilation
        if battery_level >= 50 and maintenance_hours < 9000:
            return HVACMode.VENTILATION
        else:
            return HVACMode.OFF

    else:  # NoEmergency
        return base_mode


def count_energy_constraints(
    battery_level: float, power_consumption: float, external_power: bool
) -> int:
    """
    Count number of active energy constraints (quorum-based).

    Args:
        battery_level: Battery level percentage
        power_consumption: Current power consumption
        external_power: Whether external power is available

    Returns:
        Number of active energy constraints (0-3)
    """
    c1 = battery_level < 30
    c2 = power_consumption > 5000
    c3 = not external_power

    return sum([c1, c2, c3])


def determine_hvac_control(
    temp_diff: float,
    season: Season,
    occupancy: OccupancyLevel,
    emergency_state: EmergencyState,
    battery_level: float,
    power_consumption: float,
    external_power: bool,
    maintenance_hours: float,
) -> HVACControlDecision:
    """
    Determine HVAC control mode based on environmental conditions, occupancy, and system state.

    This function balances comfort, safety, and energy efficiency by:
    - Classifying temperature needs based on season and occupancy
    - Applying emergency overrides with sub-exceptions
    - Implementing quorum-based energy saving (2 out of 3 constraints)
    - Handling dead zone ambiguities (temp_diff = 3)

    Args:
        temp_diff: Temperature differential
        season: Current season
        occupancy: Building occupancy level
        emergency_state: Current emergency state
        battery_level: Battery level percentage
        power_consumption: Current power consumption
        external_power: Whether external power is available
        maintenance_hours: Hours since last maintenance

    Returns:
        HVACControlDecision with selected mode, fan speed, and override flag
    """
    # Step 1: Classify temperature need
    temp_need = classify_temp_need(temp_diff, season, occupancy)

    # Step 2: Determine base mode from temp need
    if occupancy == OccupancyLevel.EMPTY:
        base_mode = HVACMode.OFF
    elif temp_need in (TempNeed.NO_HEATING, TempNeed.COMFORTABLE):
        base_mode = HVACMode.VENTILATION
    elif temp_need == TempNeed.MILD_HEATING:
        base_mode = (
            HVACMode.VENTILATION if in_dead_zone(temp_diff) else HVACMode.HEATING
        )
    elif temp_need == TempNeed.NEED_HEATING:
        base_mode = HVACMode.HEATING
    elif temp_need == TempNeed.MILD_COOLING:
        base_mode = (
            HVACMode.VENTILATION if in_dead_zone(temp_diff) else HVACMode.COOLING
        )
    elif temp_need == TempNeed.NEED_COOLING:
        base_mode = HVACMode.COOLING
    else:
        base_mode = HVACMode.VENTILATION

    # Step 3: Apply emergency overrides
    mode_after_emergency = apply_emergency_mode(
        base_mode, emergency_state, battery_level, maintenance_hours
    )

    # Step 4: Check energy constraints
    energy_constraint_count = count_energy_constraints(
        battery_level, power_consumption, external_power
    )

    # If 2+ energy constraints, downgrade non-emergency modes
    if energy_constraint_count >= 2:
        if mode_after_emergency == HVACMode.EMERGENCY:
            final_mode = HVACMode.EMERGENCY  # Never downgrade emergency
        elif mode_after_emergency in (HVACMode.HEATING, HVACMode.COOLING):
            final_mode = HVACMode.VENTILATION  # Downgrade to lower power
        else:
            final_mode = mode_after_emergency
    else:
        final_mode = mode_after_emergency

    # Step 5: Calculate fan speed
    fan_speed_map = {
        HVACMode.OFF: 0,
        HVACMode.EMERGENCY: 100,
        HVACMode.VENTILATION: 40,
        HVACMode.HEATING: 70,
        HVACMode.COOLING: 80,
    }
    fan_speed = fan_speed_map[final_mode]

    # Step 6: Check if override required
    override_needed = (
        final_mode == HVACMode.OFF and emergency_state == EmergencyState.FIRE_ALARM
    ) or (maintenance_hours > 10000 and emergency_state != EmergencyState.NO_EMERGENCY)

    return HVACControlDecision(
        selected_mode=final_mode, fan_speed=fan_speed, requires_override=override_needed
    )
