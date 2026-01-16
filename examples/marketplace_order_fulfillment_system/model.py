from enum import Enum
from dataclasses import dataclass


class SellerTier(Enum):
    """Seller tier levels in the marketplace."""

    BASIC = "Basic"
    SILVER = "Silver"
    GOLD = "Gold"
    PLATINUM = "Platinum"
    ENTERPRISE = "Enterprise"


class ProductCategory(Enum):
    """Product categories with different handling requirements."""

    ELECTRONICS = "Electronics"
    APPAREL = "Apparel"
    FOOD = "Food"
    FURNITURE = "Furniture"
    BOOKS = "Books"


class FulfillmentMethod(Enum):
    """Available fulfillment methods."""

    STANDARD = "Standard"
    EXPRESS = "Express"
    SAME_DAY = "SameDay"
    PICKUP = "Pickup"
    DROP_SHIP = "DropShip"


class WarehouseZone(Enum):
    """Warehouse location zones."""

    URBAN = "Urban"
    SUBURBAN = "Suburban"
    RURAL = "Rural"
    INTERNATIONAL = "International"


class InventoryStatus(Enum):
    """Current inventory availability levels."""

    ABUNDANT = "Abundant"
    ADEQUATE = "Adequate"
    LIMITED = "Limited"
    CRITICAL = "Critical"


@dataclass
class FulfillmentDecision:
    """Result of fulfillment strategy determination."""

    method_selected: FulfillmentMethod
    can_use_air_carrier: bool
    estimated_hours: int
    forced_downgrade: bool


def seller_sla_hours(tier: SellerTier) -> int:
    """Get the base SLA hours for a seller tier."""
    sla_map = {
        SellerTier.BASIC: 72,
        SellerTier.SILVER: 48,
        SellerTier.GOLD: 24,
        SellerTier.PLATINUM: 12,
        SellerTier.ENTERPRISE: 6,
    }
    return sla_map[tier]


def category_handling_multiplier(category: ProductCategory) -> int:
    """Get the handling time multiplier for a product category."""
    multiplier_map = {
        ProductCategory.ELECTRONICS: 2,  # Careful handling
        ProductCategory.APPAREL: 1,
        ProductCategory.FOOD: 3,  # Special storage
        ProductCategory.FURNITURE: 4,  # Large items
        ProductCategory.BOOKS: 1,
    }
    return multiplier_map[category]


def zone_base_processing_hours(zone: WarehouseZone) -> int:
    """Get the base processing hours for a warehouse zone."""
    hours_map = {
        WarehouseZone.URBAN: 2,
        WarehouseZone.SUBURBAN: 4,
        WarehouseZone.RURAL: 8,
        WarehouseZone.INTERNATIONAL: 24,
    }
    return hours_map[zone]


def method_delivery_hours(fm: FulfillmentMethod) -> int:
    """Get the base delivery hours for a fulfillment method."""
    hours_map = {
        FulfillmentMethod.STANDARD: 72,
        FulfillmentMethod.EXPRESS: 24,
        FulfillmentMethod.SAME_DAY: 6,
        FulfillmentMethod.PICKUP: 2,
        FulfillmentMethod.DROP_SHIP: 96,
    }
    return hours_map[fm]


def zone_supports_method(zone: WarehouseZone, fm: FulfillmentMethod) -> bool:
    """Check if a warehouse zone supports a given fulfillment method."""
    compatibility_matrix = {
        (WarehouseZone.URBAN, FulfillmentMethod.SAME_DAY): True,
        (WarehouseZone.URBAN, FulfillmentMethod.EXPRESS): True,
        (WarehouseZone.URBAN, FulfillmentMethod.STANDARD): True,
        (WarehouseZone.URBAN, FulfillmentMethod.PICKUP): True,
        (WarehouseZone.URBAN, FulfillmentMethod.DROP_SHIP): False,
        (WarehouseZone.SUBURBAN, FulfillmentMethod.SAME_DAY): False,
        (WarehouseZone.SUBURBAN, FulfillmentMethod.EXPRESS): True,
        (WarehouseZone.SUBURBAN, FulfillmentMethod.STANDARD): True,
        (WarehouseZone.SUBURBAN, FulfillmentMethod.PICKUP): True,
        (WarehouseZone.SUBURBAN, FulfillmentMethod.DROP_SHIP): False,
        (WarehouseZone.RURAL, FulfillmentMethod.SAME_DAY): False,
        (WarehouseZone.RURAL, FulfillmentMethod.EXPRESS): False,
        (WarehouseZone.RURAL, FulfillmentMethod.STANDARD): True,
        (WarehouseZone.RURAL, FulfillmentMethod.PICKUP): False,
        (WarehouseZone.RURAL, FulfillmentMethod.DROP_SHIP): True,
        (WarehouseZone.INTERNATIONAL, FulfillmentMethod.SAME_DAY): False,
        (WarehouseZone.INTERNATIONAL, FulfillmentMethod.EXPRESS): False,
        (WarehouseZone.INTERNATIONAL, FulfillmentMethod.STANDARD): True,
        (WarehouseZone.INTERNATIONAL, FulfillmentMethod.PICKUP): False,
        (WarehouseZone.INTERNATIONAL, FulfillmentMethod.DROP_SHIP): True,
    }
    return compatibility_matrix.get((zone, fm), False)


def can_use_air(zone: WarehouseZone, fm: FulfillmentMethod) -> bool:
    """Check if air carrier can be used for the given zone and method."""
    air_compatible = {
        (WarehouseZone.URBAN, FulfillmentMethod.EXPRESS): True,
        (WarehouseZone.URBAN, FulfillmentMethod.SAME_DAY): True,
        (WarehouseZone.SUBURBAN, FulfillmentMethod.EXPRESS): True,
        (WarehouseZone.RURAL, FulfillmentMethod.EXPRESS): True,
    }
    return air_compatible.get((zone, fm), False)


def stock_sufficient_for_method(
    inventory_status: InventoryStatus, fm: FulfillmentMethod
) -> bool:
    """Check if inventory level is sufficient for the fulfillment method."""
    if inventory_status == InventoryStatus.CRITICAL:
        return fm not in (FulfillmentMethod.SAME_DAY, FulfillmentMethod.EXPRESS)
    elif inventory_status == InventoryStatus.LIMITED:
        return fm != FulfillmentMethod.SAME_DAY
    else:  # ADEQUATE or ABUNDANT
        return True


def premium_express_override(
    tier: SellerTier,
    zone: WarehouseZone,
    category: ProductCategory,
    inventory_status: InventoryStatus,
) -> bool:
    """
    Check if premium seller can use Express from Rural zone.

    Platinum/Enterprise sellers can use Express from Rural via Air carrier,
    except for Food products (perishable risk) and Critical inventory.
    """
    is_premium = tier in (SellerTier.PLATINUM, SellerTier.ENTERPRISE)
    is_rural = zone == WarehouseZone.RURAL
    not_food = category != ProductCategory.FOOD
    stock_ok = inventory_status != InventoryStatus.CRITICAL
    return is_premium and is_rural and not_food and stock_ok


def calculate_fulfillment_time(
    tier: SellerTier,
    category: ProductCategory,
    zone: WarehouseZone,
    fm: FulfillmentMethod,
) -> int:
    """Calculate total fulfillment time including processing and delivery."""
    sla_base = seller_sla_hours(tier)
    handling_mult = category_handling_multiplier(category)
    zone_hours = zone_base_processing_hours(zone)
    delivery_hours = method_delivery_hours(fm)
    return (zone_hours * handling_mult) + delivery_hours


def meets_sla(
    tier: SellerTier,
    category: ProductCategory,
    zone: WarehouseZone,
    fm: FulfillmentMethod,
) -> bool:
    """Check if the fulfillment method meets the seller's SLA."""
    total_time = calculate_fulfillment_time(tier, category, zone, fm)
    sla = seller_sla_hours(tier)
    return total_time <= sla


def in_inventory_dead_zone(
    inventory_status: InventoryStatus, requested_method: FulfillmentMethod
) -> bool:
    """
    Check if order is in inventory dead zone.

    Limited inventory with Express/SameDay is too risky but not critical enough to block entirely.
    """
    return inventory_status == InventoryStatus.LIMITED and requested_method in (
        FulfillmentMethod.EXPRESS,
        FulfillmentMethod.SAME_DAY,
    )


def determine_fulfillment_strategy(
    seller_tier: SellerTier,
    product_category: ProductCategory,
    inventory_status: InventoryStatus,
    requested_method: FulfillmentMethod,
    warehouse_zone: WarehouseZone,
) -> FulfillmentDecision:
    """
    Determine optimal fulfillment strategy based on seller tier, product category,
    inventory levels, requested method, and warehouse zone.

    Implements premium seller overrides, zone-method compatibility checks,
    inventory dead zones, and quorum-based method selection.
    """
    # Check inventory dead zone first
    if in_inventory_dead_zone(inventory_status, requested_method):
        # Dead zone → downgrade to Standard
        std_time = calculate_fulfillment_time(
            seller_tier, product_category, warehouse_zone, FulfillmentMethod.STANDARD
        )
        return FulfillmentDecision(
            method_selected=FulfillmentMethod.STANDARD,
            can_use_air_carrier=False,
            estimated_hours=std_time,
            forced_downgrade=True,
        )

    # Check premium express override
    use_override = premium_express_override(
        seller_tier, warehouse_zone, product_category, inventory_status
    )

    if use_override and requested_method == FulfillmentMethod.EXPRESS:
        # Premium forcing Express from Rural (non-Food, non-Critical)
        expr_time = calculate_fulfillment_time(
            seller_tier, product_category, warehouse_zone, FulfillmentMethod.EXPRESS
        )
        return FulfillmentDecision(
            method_selected=FulfillmentMethod.EXPRESS,
            can_use_air_carrier=True,  # Override uses Air
            estimated_hours=expr_time,
            forced_downgrade=False,
        )

    # Normal fulfillment logic - check all criteria
    zone_ok = zone_supports_method(warehouse_zone, requested_method)
    stock_ok = stock_sufficient_for_method(inventory_status, requested_method)
    sla_ok = meets_sla(seller_tier, product_category, warehouse_zone, requested_method)

    # All three must be satisfied for requested method
    if zone_ok and stock_ok and sla_ok:
        can_air = can_use_air(warehouse_zone, requested_method)
        time = calculate_fulfillment_time(
            seller_tier, product_category, warehouse_zone, requested_method
        )
        return FulfillmentDecision(
            method_selected=requested_method,
            can_use_air_carrier=can_air,
            estimated_hours=time,
            forced_downgrade=False,
        )
    else:
        # Fallback to Standard
        std_time = calculate_fulfillment_time(
            seller_tier, product_category, warehouse_zone, FulfillmentMethod.STANDARD
        )
        return FulfillmentDecision(
            method_selected=FulfillmentMethod.STANDARD,
            can_use_air_carrier=False,
            estimated_hours=std_time,
            forced_downgrade=True,
        )
