from enum import Enum
from dataclasses import dataclass
from typing import NamedTuple


class CropType(Enum):
    """Types of crops supported by the irrigation system."""

    WHEAT = "wheat"
    CORN = "corn"
    TOMATOES = "tomatoes"


class CropStage(Enum):
    """Growth stages of crops."""

    SEEDLING = "seedling"
    FLOWERING = "flowering"
    MATURE = "mature"


class Weather(Enum):
    """Weather conditions."""

    SUNNY = "sunny"
    RAINY = "rainy"


class SensorStatus(Enum):
    """Status of irrigation sensors."""

    WORKING = "working"
    FAULTY = "faulty"


class IrrigationDecision(NamedTuple):
    """Decision output from the irrigation control system."""

    approved: bool
    emergency_priority: bool


def is_critical_stage(crop: CropType, stage: CropStage) -> bool:
    """
    Determine if the crop is at a critical growth stage.

    Critical stages need guaranteed irrigation:
    - Flowering stage for all crops
    - Mature stage for Tomatoes
    """
    return stage == CropStage.FLOWERING or (
        crop == CropType.TOMATOES and stage == CropStage.MATURE
    )


def determine_irrigation_decision(
    crop: CropType,
    stage: CropStage,
    moisture_pct: float,
    target_min: float,
    sensor_status: SensorStatus,
    water_available: float,
) -> IrrigationDecision:
    """
    Determine whether to irrigate based on crop conditions and resource availability.

    The system prioritizes critical growth stages (Flowering for all crops,
    Mature for Tomatoes) and will approve emergency irrigation if moisture is
    critically low (20% below target minimum).

    Args:
        crop: Type of crop being monitored
        stage: Current growth stage of the crop
        moisture_pct: Current soil moisture percentage
        target_min: Minimum target moisture percentage
        sensor_status: Status of the moisture sensor
        water_available: Amount of water available for irrigation

    Returns:
        IrrigationDecision indicating approval status and emergency priority
    """
    # Critical stage override
    is_critical = is_critical_stage(crop, stage)
    critically_dry = moisture_pct < (target_min - 20)

    if is_critical and critically_dry:
        return IrrigationDecision(approved=True, emergency_priority=True)

    # Check if irrigation is needed
    needs_water = moisture_pct < target_min
    if not needs_water:
        return IrrigationDecision(approved=False, emergency_priority=False)

    # Verify sensor is working
    sensor_ok = sensor_status == SensorStatus.WORKING
    if not sensor_ok:
        return IrrigationDecision(approved=False, emergency_priority=False)

    # Check water availability
    sufficient_water = water_available >= 100
    return IrrigationDecision(approved=sufficient_water, emergency_priority=False)
