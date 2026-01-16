from enum import Enum
from dataclasses import dataclass


class ResourceType(Enum):
    """Types of energy resources in the virtual power plant."""

    SOLAR = "solar"
    BATTERY = "battery"
    EV_CHARGER = "ev_charger"
    LOAD = "load"


class GridCondition(Enum):
    """Grid operational states."""

    NORMAL = "normal"
    CONGESTION = "congestion"
    EMERGENCY = "emergency"


class DispatchCommand(Enum):
    """Commands for resource control."""

    CHARGE = "charge"
    DISCHARGE = "discharge"
    CURTAIL = "curtail"
    MAINTAIN = "maintain"


@dataclass
class ControlDecision:
    """Decision output for a resource."""

    command: DispatchCommand
    power_level: int
    participate: bool


def _in_price_dead_zone(battery_soc: int, electricity_price: int) -> bool:
    """Check if battery SOC and price are in the dead zone where no action is taken."""
    return (48 <= battery_soc <= 52) and (18 <= electricity_price <= 22)


def _price_threshold_adjusted(grid_condition: GridCondition, base_price: int) -> int:
    """Adjust price threshold based on grid condition (higher thresholds during stress)."""
    if grid_condition == GridCondition.NORMAL:
        return base_price
    elif grid_condition == GridCondition.CONGESTION:
        return (base_price * 13) // 10  # 30% premium
    else:  # EMERGENCY
        return base_price * 2  # 100% premium


def _dispatch_quorum_met(
    price_favorable: bool, soc_adequate: bool, grid_needs_support: bool
) -> bool:
    """Check if at least 2 out of 3 dispatch conditions are met."""
    count = sum([price_favorable, soc_adequate, grid_needs_support])
    return count >= 2


def determine_dispatch(
    resource_type: ResourceType,
    grid_condition: GridCondition,
    battery_soc: int,
    electricity_price: int,
    solar_generation: int,
    grid_frequency: float,
) -> ControlDecision:
    """
    Determine dispatch command for a resource based on grid conditions and resource state.

    Args:
        resource_type: Type of energy resource
        grid_condition: Current grid operational state
        battery_soc: Battery state of charge (0-100%)
        electricity_price: Current electricity price
        solar_generation: Solar generation level
        grid_frequency: Grid frequency in Hz

    Returns:
        ControlDecision with command, power level, and participation flag
    """
    # Dead zone check - no action in neutral SOC/price range
    if _in_price_dead_zone(battery_soc, electricity_price):
        return ControlDecision(
            command=DispatchCommand.MAINTAIN, power_level=0, participate=False
        )

    # Emergency override - prioritize grid stability
    if grid_condition == GridCondition.EMERGENCY:
        if resource_type == ResourceType.BATTERY:
            return ControlDecision(
                command=DispatchCommand.DISCHARGE, power_level=50, participate=True
            )
        elif resource_type == ResourceType.LOAD:
            return ControlDecision(
                command=DispatchCommand.CURTAIL, power_level=30, participate=True
            )
        else:
            return ControlDecision(
                command=DispatchCommand.MAINTAIN, power_level=0, participate=True
            )

    # Normal dispatch logic with adjusted thresholds
    base_price_threshold = 25
    adjusted_threshold = _price_threshold_adjusted(grid_condition, base_price_threshold)
    high_price = electricity_price >= adjusted_threshold
    low_price = electricity_price < 15

    # Resource-specific dispatch logic
    if resource_type == ResourceType.SOLAR:
        # Solar generates whenever available
        if solar_generation > 0:
            return ControlDecision(
                command=DispatchCommand.DISCHARGE,
                power_level=solar_generation,
                participate=True,
            )
        else:
            return ControlDecision(
                command=DispatchCommand.MAINTAIN, power_level=0, participate=False
            )

    elif resource_type == ResourceType.BATTERY:
        # Require quorum of conditions for battery participation
        price_favorable = high_price and battery_soc > 20
        soc_adequate = 30 <= battery_soc <= 90
        grid_needs = grid_frequency < 59 or grid_frequency > 61
        quorum = _dispatch_quorum_met(price_favorable, soc_adequate, grid_needs)

        if quorum:
            if high_price and battery_soc > 40:
                return ControlDecision(
                    command=DispatchCommand.DISCHARGE, power_level=40, participate=True
                )
            elif low_price and battery_soc < 80:
                return ControlDecision(
                    command=DispatchCommand.CHARGE, power_level=30, participate=True
                )
            else:
                return ControlDecision(
                    command=DispatchCommand.MAINTAIN, power_level=0, participate=True
                )
        else:
            return ControlDecision(
                command=DispatchCommand.MAINTAIN, power_level=0, participate=False
            )

    elif resource_type == ResourceType.EV_CHARGER:
        # Charge EVs during low price periods
        if low_price:
            return ControlDecision(
                command=DispatchCommand.CHARGE, power_level=20, participate=True
            )
        else:
            return ControlDecision(
                command=DispatchCommand.CURTAIL, power_level=0, participate=False
            )

    else:  # LOAD
        # Curtail loads during high price and congestion
        if high_price and grid_condition == GridCondition.CONGESTION:
            return ControlDecision(
                command=DispatchCommand.CURTAIL, power_level=15, participate=True
            )
        else:
            return ControlDecision(
                command=DispatchCommand.MAINTAIN, power_level=0, participate=False
            )
