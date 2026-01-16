from enum import Enum
from dataclasses import dataclass


class LoadPriority(Enum):
    """Load priority levels in the microgrid system."""

    CRITICAL = "Critical"
    ESSENTIAL = "Essential"
    NON_ESSENTIAL = "NonEssential"
    DEFERRABLE = "Deferrable"


class SystemMode(Enum):
    """Operating modes of the microgrid system."""

    GRID_TIED = "GridTied"
    ISLANDED = "Islanded"
    EMERGENCY = "Emergency"


class EnergySourceStatus(Enum):
    """Status of energy availability."""

    ABUNDANT = "Abundant"
    ADEQUATE = "Adequate"
    LIMITED = "Limited"
    DEPLETED = "Depleted"


@dataclass
class LoadShedDecision:
    """Decision result for load shedding operations."""

    shed_deferrable: bool
    shed_non_essential: bool
    shed_essential: bool
    shed_critical: bool
    total_shed_kw: int


def load_power(priority: LoadPriority) -> int:
    """Return power level in kW for given load priority."""
    power_map = {
        LoadPriority.CRITICAL: 20,
        LoadPriority.ESSENTIAL: 40,
        LoadPriority.NON_ESSENTIAL: 30,
        LoadPriority.DEFERRABLE: 10,
    }
    return power_map[priority]


def is_sufficient(available_kw: int, load_kw: int) -> bool:
    """Check if available power is sufficient for load."""
    return available_kw >= load_kw


def calculate_deficit(available_kw: int, total_load_kw: int) -> int:
    """Calculate energy deficit between available and required power."""
    if available_kw >= total_load_kw:
        return 0
    return total_load_kw - available_kw


def classify_energy_status(
    battery_soc: int, renewable_kw: int, grid_connected: bool
) -> EnergySourceStatus:
    """Determine energy availability status from battery SOC and renewable generation."""
    if renewable_kw >= 80:
        return EnergySourceStatus.ABUNDANT
    elif renewable_kw >= 50:
        return EnergySourceStatus.ADEQUATE
    elif battery_soc >= 30 or grid_connected:
        return EnergySourceStatus.LIMITED
    else:
        return EnergySourceStatus.DEPLETED


def critical_protected(mode: SystemMode) -> bool:
    """Check if critical loads are protected in current mode."""
    return mode == SystemMode.GRID_TIED


def emergency_allows_essential_shed(mode: SystemMode) -> bool:
    """Check if emergency mode allows shedding essential loads."""
    return mode == SystemMode.EMERGENCY


def determine_load_shedding(
    mode: SystemMode,
    battery_soc: int,
    renewable_kw: int,
    total_load_kw: int,
    grid_connected: bool,
) -> LoadShedDecision:
    """
    Determine which loads to shed during energy shortages.

    Prioritizes loads (Critical > Essential > NonEssential > Deferrable) and
    enforces mode-specific protection rules (GridTied protects Critical,
    Emergency allows Essential shedding).

    Args:
        mode: Current operating mode of the microgrid
        battery_soc: Battery state of charge percentage
        renewable_kw: Available renewable energy in kW
        total_load_kw: Total load demand in kW
        grid_connected: Whether connected to main grid

    Returns:
        LoadShedDecision indicating which loads to disconnect and total power shed
    """
    deficit = calculate_deficit(renewable_kw, total_load_kw)

    if deficit == 0:
        # No deficit, no shedding needed
        return LoadShedDecision(
            shed_deferrable=False,
            shed_non_essential=False,
            shed_essential=False,
            shed_critical=False,
            total_shed_kw=0,
        )

    # Energy shortage - determine what to shed
    energy_status = classify_energy_status(battery_soc, renewable_kw, grid_connected)

    # Shed Deferrable first (always shed if deficit exists)
    deferrable_kw = load_power(LoadPriority.DEFERRABLE)
    after_deferrable = deficit - deferrable_kw

    if after_deferrable <= 0:
        return LoadShedDecision(
            shed_deferrable=True,
            shed_non_essential=False,
            shed_essential=False,
            shed_critical=False,
            total_shed_kw=deferrable_kw,
        )

    # Shed NonEssential next
    non_essential_kw = load_power(LoadPriority.NON_ESSENTIAL)
    after_non_essential = after_deferrable - non_essential_kw

    if after_non_essential <= 0:
        return LoadShedDecision(
            shed_deferrable=True,
            shed_non_essential=True,
            shed_essential=False,
            shed_critical=False,
            total_shed_kw=deferrable_kw + non_essential_kw,
        )

    # Need to shed Essential - only in Emergency mode
    can_shed_essential = emergency_allows_essential_shed(mode)

    if can_shed_essential:
        essential_kw = load_power(LoadPriority.ESSENTIAL)
        after_essential = after_non_essential - essential_kw

        if after_essential <= 0:
            return LoadShedDecision(
                shed_deferrable=True,
                shed_non_essential=True,
                shed_essential=True,
                shed_critical=False,
                total_shed_kw=deferrable_kw + non_essential_kw + essential_kw,
            )

        # Complete blackout - shed everything including Critical
        critical_kw = load_power(LoadPriority.CRITICAL)
        return LoadShedDecision(
            shed_deferrable=True,
            shed_non_essential=True,
            shed_essential=True,
            shed_critical=True,
            total_shed_kw=deferrable_kw + non_essential_kw + essential_kw + critical_kw,
        )

    # Cannot shed Essential in non-Emergency modes
    return LoadShedDecision(
        shed_deferrable=True,
        shed_non_essential=True,
        shed_essential=False,
        shed_critical=False,
        total_shed_kw=deferrable_kw + non_essential_kw,
    )
