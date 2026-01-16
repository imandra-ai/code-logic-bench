from enum import Enum
from dataclasses import dataclass


class ProductType(Enum):
    """Product type classification."""

    PRODUCT_A = "ProductA"
    PRODUCT_B = "ProductB"
    PRODUCT_C = "ProductC"


class ProductionMode(Enum):
    """Production operation mode."""

    NORMAL = "Normal"
    HIGH_SPEED = "HighSpeed"
    ECO_MODE = "EcoMode"


class SafetyLevel(Enum):
    """Safety status levels."""

    SAFE = "Safe"
    WARNING = "Warning"
    CRITICAL = "Critical"
    EMERGENCY = "Emergency"


@dataclass
class QualityDecision:
    """Production quality decision result."""

    approved: bool
    requires_inspection: bool
    production_allowed: bool


def defect_threshold(product: ProductType) -> int:
    """
    Get defect threshold by product type.

    ProductA: Strict (10)
    ProductB: Moderate (20)
    ProductC: Relaxed (30)
    """
    thresholds = {
        ProductType.PRODUCT_A: 10,
        ProductType.PRODUCT_B: 20,
        ProductType.PRODUCT_C: 30,
    }
    return thresholds[product]


def temp_limit(mode: ProductionMode) -> int:
    """
    Get temperature safety limits by production mode.

    Normal: 80
    HighSpeed: 90 (higher tolerance)
    EcoMode: 70 (stricter)
    """
    limits = {
        ProductionMode.NORMAL: 80,
        ProductionMode.HIGH_SPEED: 90,
        ProductionMode.ECO_MODE: 70,
    }
    return limits[mode]


def temp_safe(temperature: int, mode: ProductionMode) -> bool:
    """Check if temperature is within safe limits for the mode."""
    return temperature <= temp_limit(mode)


def requires_emergency_stop(safety_level: SafetyLevel, temperature: int) -> bool:
    """Determine if emergency stop is required."""
    return safety_level == SafetyLevel.EMERGENCY or temperature > 100


def determine_production_decision(
    product: ProductType,
    mode: ProductionMode,
    defect_score: int,
    temperature: int,
    safety_level: SafetyLevel,
    vibration: int,
) -> QualityDecision:
    """
    Determine production decision based on quality and safety parameters.

    The system enforces:
    - Emergency stops for critical safety conditions
    - Quality thresholds based on product type
    - Mode-specific temperature limits
    - Vibration limits (stricter for HighSpeed mode)

    Returns QualityDecision with approval status, inspection requirement,
    and production permission.
    """
    # Emergency stop override: halt production immediately
    emergency = requires_emergency_stop(safety_level, temperature)

    if emergency:
        return QualityDecision(
            approved=False, requires_inspection=True, production_allowed=False
        )

    # Check defect score
    threshold = defect_threshold(product)
    quality_ok = defect_score <= threshold

    if not quality_ok:
        return QualityDecision(
            approved=False, requires_inspection=True, production_allowed=True
        )

    # Check temperature safety
    temp_ok = temp_safe(temperature, mode)

    if not temp_ok:
        return QualityDecision(
            approved=False, requires_inspection=False, production_allowed=False
        )

    # Check vibration (HighSpeed mode sensitive)
    vibration_ok = (
        vibration <= 50 if mode == ProductionMode.HIGH_SPEED else vibration <= 70
    )

    if not vibration_ok:
        return QualityDecision(
            approved=False, requires_inspection=False, production_allowed=False
        )

    return QualityDecision(
        approved=True, requires_inspection=False, production_allowed=True
    )
