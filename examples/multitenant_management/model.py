from enum import Enum, auto


class SubscriptionTier(Enum):
    """Subscription tier levels for tenants."""

    BASIC = auto()
    PROFESSIONAL = auto()
    ENTERPRISE = auto()


class BillingStatus(Enum):
    """Billing status of a tenant."""

    CURRENT = auto()
    GRACE_PERIOD = auto()
    OVERDUE = auto()
    SUSPENDED = auto()


class TenantStatus(Enum):
    """Operational status of a tenant."""

    ACTIVE = auto()
    SUSPENDED = auto()
    QUOTA_EXCEEDED = auto()


class AllocationDecision(Enum):
    """Decision outcome for resource allocation requests."""

    FULLY_APPROVED = auto()
    PARTIALLY_APPROVED = auto()
    DENIED = auto()
    REQUIRES_REVIEW = auto()


def in_throttle_zone(usage_pct: int) -> bool:
    """
    Check if usage percentage falls in the throttle dead zone (75-85%).

    This zone triggers denial to prevent oscillation.
    """
    return 75 <= usage_pct <= 85


def tier_approval_threshold(tier: SubscriptionTier) -> int:
    """
    Get the approval threshold percentage for a given subscription tier.

    Returns:
        - Basic: 60% (strict)
        - Professional: 75%
        - Enterprise: 90% (lenient)
    """
    thresholds = {
        SubscriptionTier.BASIC: 60,
        SubscriptionTier.PROFESSIONAL: 75,
        SubscriptionTier.ENTERPRISE: 90,
    }
    return thresholds[tier]


def apply_billing_override(
    billing_status: BillingStatus, tier: SubscriptionTier, usage_pct: int
) -> AllocationDecision:
    """
    Apply billing status override rules to determine allocation decision.

    Rules:
    - Current: Always fully approved
    - GracePeriod: Allows allocation BUT denies if usage≥70%,
      EXCEPT Enterprise gets full approval
    - Overdue: Normally denies, BUT Enterprise gets review if usage<50%
    - Suspended: Always denied
    """
    if billing_status == BillingStatus.CURRENT:
        return AllocationDecision.FULLY_APPROVED

    elif billing_status == BillingStatus.GRACE_PERIOD:
        if usage_pct >= 70:
            return AllocationDecision.DENIED
        elif tier == SubscriptionTier.ENTERPRISE:
            return AllocationDecision.FULLY_APPROVED
        else:
            return AllocationDecision.PARTIALLY_APPROVED

    elif billing_status == BillingStatus.OVERDUE:
        if tier == SubscriptionTier.ENTERPRISE and usage_pct < 50:
            return AllocationDecision.REQUIRES_REVIEW
        else:
            return AllocationDecision.DENIED

    else:  # BillingStatus.SUSPENDED
        return AllocationDecision.DENIED


def calculate_usage_percentage(current_usage: int, quota_limit: int) -> int:
    """
    Calculate usage as a percentage of quota limit.

    Returns 100 if quota_limit is 0 to prevent division by zero.
    """
    if quota_limit == 0:
        return 100
    return (current_usage * 100) // quota_limit


def determine_allocation_decision(
    tier: SubscriptionTier,
    billing_status: BillingStatus,
    tenant_status: TenantStatus,
    current_usage: int,
    quota_limit: int,
    requested_amount: int,
) -> AllocationDecision:
    """
    Determine whether a resource allocation request should be approved.

    Decision logic:
    1. Deny if in throttle zone (75-85% usage) to prevent oscillation
    2. Deny if tenant is not active
    3. Apply billing status overrides
    4. Check tier-dependent approval thresholds

    Args:
        tier: Subscription tier of the tenant
        billing_status: Current billing status
        tenant_status: Operational status of the tenant
        current_usage: Current resource usage
        quota_limit: Maximum allowed quota
        requested_amount: Amount of resources requested

    Returns:
        AllocationDecision indicating approval status
    """
    usage_pct = calculate_usage_percentage(current_usage, quota_limit)
    new_usage = current_usage + requested_amount
    new_usage_pct = calculate_usage_percentage(new_usage, quota_limit)

    # Check throttle zone first
    if in_throttle_zone(usage_pct):
        return AllocationDecision.DENIED

    # Check tenant status
    if tenant_status != TenantStatus.ACTIVE:
        return AllocationDecision.DENIED

    # Get tier-specific threshold
    threshold = tier_approval_threshold(tier)

    # Apply billing override
    billing_result = apply_billing_override(billing_status, tier, usage_pct)

    if billing_result == AllocationDecision.DENIED:
        return AllocationDecision.DENIED

    elif billing_result == AllocationDecision.REQUIRES_REVIEW:
        return AllocationDecision.REQUIRES_REVIEW

    elif billing_result == AllocationDecision.FULLY_APPROVED:
        # Even with billing approved, check if new usage exceeds threshold
        if new_usage_pct > threshold:
            return AllocationDecision.PARTIALLY_APPROVED
        else:
            return AllocationDecision.FULLY_APPROVED

    else:  # AllocationDecision.PARTIALLY_APPROVED
        # Check if can at least partially approve
        if new_usage_pct > threshold:
            return AllocationDecision.DENIED
        else:
            return AllocationDecision.PARTIALLY_APPROVED
