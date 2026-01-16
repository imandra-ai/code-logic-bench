from enum import Enum
from typing import NamedTuple


class CustomerTier(Enum):
    """Customer tier levels."""

    BRONZE = "Bronze"
    SILVER = "Silver"
    GOLD = "Gold"
    PLATINUM = "Platinum"


class InventoryLevel(Enum):
    """Inventory availability levels."""

    OUT_OF_STOCK = "OutOfStock"
    CRITICAL_LOW = "CriticalLow"
    LOW = "Low"
    NORMAL = "Normal"
    HIGH = "High"


class DiscountLevel(Enum):
    """Discount magnitude levels."""

    NO_DISCOUNT = "NoDiscount"
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"
    VERY_LARGE = "VeryLarge"


class VIPStatus(Enum):
    """VIP status indicator."""

    NOT_VIP = "NotVIP"
    VIP = "VIP"


class PriceCategory(Enum):
    """Final price categorization."""

    ZERO_PRICE = "ZeroPrice"
    BELOW_COST = "BelowCost"
    AT_MIN_MARGIN = "AtMinMargin"
    PROFITABLE_PRICE = "ProfitablePrice"


class PricingDecision(NamedTuple):
    """Result of pricing determination."""

    final_price_category: PriceCategory
    margin_enforced: bool
    price_valid: bool


def _tier_discount(tier: CustomerTier) -> DiscountLevel:
    """Get base discount level for customer tier."""
    tier_map = {
        CustomerTier.BRONZE: DiscountLevel.NO_DISCOUNT,
        CustomerTier.SILVER: DiscountLevel.SMALL,
        CustomerTier.GOLD: DiscountLevel.MEDIUM,
        CustomerTier.PLATINUM: DiscountLevel.LARGE,
    }
    return tier_map[tier]


def _scarcity_adjustment(inventory: InventoryLevel) -> int:
    """Calculate scarcity-based price adjustment."""
    adjustments = {
        InventoryLevel.OUT_OF_STOCK: -100,  # Invalid
        InventoryLevel.CRITICAL_LOW: 15,  # Premium
        InventoryLevel.LOW: 8,
        InventoryLevel.NORMAL: 0,
        InventoryLevel.HIGH: -5,  # Clearance discount
    }
    return adjustments[inventory]


def _is_invalid_stacking(coupon_disc: DiscountLevel, flash_disc: DiscountLevel) -> bool:
    """Check if discount combination is invalid (dead zone)."""
    # Cannot stack Medium coupon with VeryLarge flash
    if coupon_disc == DiscountLevel.MEDIUM and flash_disc == DiscountLevel.VERY_LARGE:
        return True
    # Cannot stack Large coupon with Large flash
    if coupon_disc == DiscountLevel.LARGE and flash_disc == DiscountLevel.LARGE:
        return True
    return False


def _determine_vip_status(
    tier: CustomerTier, loyalty_high: bool, orders_high: bool
) -> VIPStatus:
    """Determine VIP status using quorum pattern (2 out of 3 conditions)."""
    c1 = tier == CustomerTier.PLATINUM
    c2 = loyalty_high
    c3 = orders_high

    count = sum([c1, c2, c3])
    return VIPStatus.VIP if count >= 2 else VIPStatus.NOT_VIP


def _combine_discounts(
    tier_disc: DiscountLevel,
    coupon_disc: DiscountLevel,
    flash_disc: DiscountLevel,
    vip_status: VIPStatus,
    flash_disc_level: DiscountLevel,
) -> DiscountLevel:
    """Combine all discount sources into total discount level."""
    # VIP gets extra discount EXCEPT when flash is VeryLarge
    vip_applies = (
        vip_status == VIPStatus.VIP and flash_disc_level != DiscountLevel.VERY_LARGE
    )

    # Combine discount levels - simplified logic
    if (
        tier_disc == DiscountLevel.NO_DISCOUNT
        and coupon_disc == DiscountLevel.NO_DISCOUNT
        and flash_disc == DiscountLevel.NO_DISCOUNT
    ):
        base_total = DiscountLevel.NO_DISCOUNT
    elif (
        tier_disc == DiscountLevel.SMALL
        and coupon_disc == DiscountLevel.NO_DISCOUNT
        and flash_disc == DiscountLevel.NO_DISCOUNT
    ):
        base_total = DiscountLevel.SMALL
    elif (
        tier_disc == DiscountLevel.MEDIUM
        and coupon_disc == DiscountLevel.SMALL
        and flash_disc == DiscountLevel.NO_DISCOUNT
    ):
        base_total = DiscountLevel.MEDIUM
    elif (
        tier_disc == DiscountLevel.LARGE
        and coupon_disc == DiscountLevel.MEDIUM
        and flash_disc == DiscountLevel.SMALL
    ):
        base_total = DiscountLevel.VERY_LARGE
    elif flash_disc == DiscountLevel.VERY_LARGE:
        base_total = DiscountLevel.VERY_LARGE
    elif coupon_disc == DiscountLevel.LARGE:
        base_total = DiscountLevel.VERY_LARGE
    elif coupon_disc == DiscountLevel.MEDIUM and flash_disc == DiscountLevel.MEDIUM:
        base_total = DiscountLevel.LARGE
    else:
        base_total = DiscountLevel.MEDIUM  # Default aggregation

    # Apply VIP boost
    if vip_applies:
        vip_boost = {
            DiscountLevel.NO_DISCOUNT: DiscountLevel.SMALL,
            DiscountLevel.SMALL: DiscountLevel.MEDIUM,
            DiscountLevel.MEDIUM: DiscountLevel.LARGE,
            DiscountLevel.LARGE: DiscountLevel.VERY_LARGE,
            DiscountLevel.VERY_LARGE: DiscountLevel.VERY_LARGE,
        }
        return vip_boost[base_total]

    return base_total


def _check_margin_enforcement(cost_high: bool, total_discount: DiscountLevel) -> bool:
    """Determine if minimum margin enforcement is needed."""
    # High cost + high discount = margin enforcement needed
    if total_discount == DiscountLevel.VERY_LARGE:
        return cost_high  # Always enforce if cost is high
    elif total_discount == DiscountLevel.LARGE:
        return cost_high
    else:
        return False


def _categorize_price(
    margin_enforced: bool, cost_high: bool, inventory: InventoryLevel
) -> PriceCategory:
    """Categorize the final price based on constraints."""
    if inventory == InventoryLevel.OUT_OF_STOCK:
        return PriceCategory.ZERO_PRICE
    elif margin_enforced and cost_high:
        return PriceCategory.AT_MIN_MARGIN
    elif margin_enforced:
        return PriceCategory.BELOW_COST
    else:
        return PriceCategory.PROFITABLE_PRICE


def determine_price(
    inventory: InventoryLevel,
    tier: CustomerTier,
    coupon_disc: DiscountLevel,
    flash_disc: DiscountLevel,
    loyalty_high: bool,
    orders_high: bool,
    cost_high: bool,
) -> PricingDecision:
    """
    Core pricing decision function.

    Determines final price category based on customer tier, discounts,
    inventory levels, and VIP status (quorum pattern). Handles discount
    stacking rules and minimum margin enforcement.
    """
    # Check stacking validity
    invalid_stack = _is_invalid_stacking(coupon_disc, flash_disc)

    if invalid_stack:
        return PricingDecision(
            final_price_category=PriceCategory.ZERO_PRICE,
            margin_enforced=False,
            price_valid=False,
        )

    if inventory == InventoryLevel.OUT_OF_STOCK:
        return PricingDecision(
            final_price_category=PriceCategory.ZERO_PRICE,
            margin_enforced=False,
            price_valid=False,
        )

    # Determine VIP status
    vip_status = _determine_vip_status(tier, loyalty_high, orders_high)

    # Get tier discount
    tier_disc = _tier_discount(tier)

    # Combine all discounts
    total_disc = _combine_discounts(
        tier_disc, coupon_disc, flash_disc, vip_status, flash_disc
    )

    # Check if margin enforcement needed
    margin_enforced = _check_margin_enforcement(cost_high, total_disc)

    # Categorize price
    price_cat = _categorize_price(margin_enforced, cost_high, inventory)

    return PricingDecision(
        final_price_category=price_cat,
        margin_enforced=margin_enforced,
        price_valid=True,
    )
