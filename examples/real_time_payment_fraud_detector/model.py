from enum import Enum
from dataclasses import dataclass


class MerchantCategory(Enum):
    """Merchant category types for transaction classification."""

    GROCERY = "grocery"
    ONLINE_RETAIL = "online_retail"
    CASINO = "casino"
    CRYPTO = "crypto"


class DeviceTrust(Enum):
    """Device trust levels."""

    TRUSTED = "trusted"
    UNVERIFIED = "unverified"
    SUSPICIOUS = "suspicious"


class TransactionTime(Enum):
    """Time of day categories for transactions."""

    BUSINESS = "business"
    EVENING = "evening"
    LATE_NIGHT = "late_night"


@dataclass
class FraudDecision:
    """Decision output from fraud detection system."""

    allow_transaction: bool
    require_2fa: bool
    flag_for_review: bool
    risk_score: int  # 0-100


def base_risk_score(category: MerchantCategory, amount: float) -> int:
    """
    Calculate base risk score by merchant category (multiplexer pattern).

    Args:
        category: Merchant category
        amount: Transaction amount

    Returns:
        Base risk score
    """
    if category == MerchantCategory.GROCERY:
        return 5
    elif category == MerchantCategory.ONLINE_RETAIL:
        return 20 if amount > 500 else 10
    elif category == MerchantCategory.CASINO:
        return 40
    elif category == MerchantCategory.CRYPTO:
        return 50
    return 0


def device_risk_multiplier(device_trust: DeviceTrust) -> int:
    """
    Calculate risk multiplier based on device trust level.

    Args:
        device_trust: Device trust level

    Returns:
        Risk multiplier percentage (100 = no change)
    """
    if device_trust == DeviceTrust.TRUSTED:
        return 100  # 100% = no change
    elif device_trust == DeviceTrust.UNVERIFIED:
        return 150  # 50% increase
    elif device_trust == DeviceTrust.SUSPICIOUS:
        return 250  # 150% increase
    return 100


def time_risk_factor(
    transaction_time: TransactionTime, category: MerchantCategory
) -> int:
    """
    Calculate risk factor based on time of day and category (multiplexer).

    Args:
        transaction_time: Time of day
        category: Merchant category

    Returns:
        Risk factor percentage (100 = no change)
    """
    if transaction_time == TransactionTime.LATE_NIGHT:
        if category == MerchantCategory.CASINO:
            return 180  # 80% increase for late night casino
        elif category == MerchantCategory.CRYPTO:
            return 170  # 70% increase for late night crypto
        else:
            return 130  # 30% increase otherwise
    elif transaction_time == TransactionTime.EVENING:
        return 110  # 10% increase
    else:  # BUSINESS
        return 100  # No change


def check_amount_threshold(
    amount: float, device_trust: DeviceTrust, account_age: int
) -> bool:
    """
    Check if amount triggers review (override pattern).

    High amounts trigger review EXCEPT for trusted devices with old accounts.

    Args:
        amount: Transaction amount
        device_trust: Device trust level
        account_age: Account age in days

    Returns:
        True if transaction should be reviewed
    """
    if amount > 1000:
        # Override: large amounts need review...
        needs_review = True
        # ...EXCEPT trusted device + old account
        trusted_account = device_trust == DeviceTrust.TRUSTED and account_age > 365
        return not needs_review if trusted_account else needs_review
    return False


def check_velocity_risk(
    tx_count_24h: int,
    amount_24h: float,
    location_changes: int,
    consecutive_failures: int,
) -> bool:
    """
    Check for velocity risk using quorum pattern.

    Requires at least 2 of 4 risk factors to be present.

    Args:
        tx_count_24h: Number of transactions in last 24 hours
        amount_24h: Total amount in last 24 hours
        location_changes: Number of location changes
        consecutive_failures: Number of consecutive failed attempts

    Returns:
        True if velocity risk detected (2+ risk factors)
    """
    c1 = tx_count_24h > 10
    c2 = amount_24h > 2000
    c3 = location_changes > 3
    c4 = consecutive_failures > 2

    risk_factors = sum([c1, c2, c3, c4])

    return risk_factors >= 2


def is_valid_transaction(amount: float, risk_score: int, account_age: int) -> bool:
    """
    Check if transaction is valid (not in dead zone or out of bounds).

    Args:
        amount: Transaction amount
        risk_score: Calculated risk score
        account_age: Account age in days

    Returns:
        True if transaction is valid
    """
    # Amounts 985-1015 with risk 48-52 and account age 363-367 are ambiguous
    in_dead_zone = (
        985 <= amount <= 1015 and 48 <= risk_score <= 52 and 363 <= account_age <= 367
    )

    # Also invalid if values out of bounds
    invalid = (
        amount < 0
        or amount > 10000
        or risk_score < 0
        or risk_score > 100
        or account_age < 0
    )

    return not (in_dead_zone or invalid)


def calculate_risk_score(
    category: MerchantCategory,
    amount: float,
    device_trust: DeviceTrust,
    transaction_time: TransactionTime,
) -> int:
    """
    Calculate final risk score.

    Args:
        category: Merchant category
        amount: Transaction amount
        device_trust: Device trust level
        transaction_time: Time of day

    Returns:
        Final risk score (0-100)
    """
    base = base_risk_score(category, amount)
    device_mult = device_risk_multiplier(device_trust)
    time_mult = time_risk_factor(transaction_time, category)
    return (base * device_mult * time_mult) // 10000


def determine_fraud_decision(
    category: MerchantCategory,
    amount: float,
    device_trust: DeviceTrust,
    transaction_time: TransactionTime,
    account_age: int,
    tx_count_24h: int,
    amount_24h: float,
    location_changes: int,
    consecutive_failures: int,
) -> FraudDecision:
    """
    Core fraud detection decision function.

    Evaluates transaction risk based on multiple factors including merchant category,
    amount, device trust, time, account age, and velocity patterns. Returns decision
    on whether to allow, require 2FA, or flag for review.

    Args:
        category: Merchant category
        amount: Transaction amount
        device_trust: Device trust level
        transaction_time: Time of day
        account_age: Account age in days
        tx_count_24h: Number of transactions in last 24 hours
        amount_24h: Total amount in last 24 hours
        location_changes: Number of location changes
        consecutive_failures: Number of consecutive failed attempts

    Returns:
        FraudDecision with allow/2FA/review flags and risk score
    """
    # Calculate initial risk score
    risk = calculate_risk_score(category, amount, device_trust, transaction_time)

    # Check validity
    valid = is_valid_transaction(amount, risk, account_age)

    if not valid:
        return FraudDecision(
            allow_transaction=False,
            require_2fa=False,
            flag_for_review=False,
            risk_score=0,
        )

    # Check amount threshold (override)
    amount_review = check_amount_threshold(amount, device_trust, account_age)

    # Check velocity risk (quorum)
    velocity_risk = check_velocity_risk(
        tx_count_24h, amount_24h, location_changes, consecutive_failures
    )

    # Determine if transaction allowed
    allow = risk < 60 and not velocity_risk

    # 2FA requirement
    needs_2fa = (40 <= risk < 60) or (
        amount > 500 and device_trust != DeviceTrust.TRUSTED
    )

    # Flag for review
    flag = amount_review or velocity_risk or risk >= 70

    return FraudDecision(
        allow_transaction=allow,
        require_2fa=needs_2fa,
        flag_for_review=flag,
        risk_score=risk,
    )
