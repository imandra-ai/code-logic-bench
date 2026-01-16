from enum import Enum
from dataclasses import dataclass


class OptionType(Enum):
    """Option type: Call or Put"""

    CALL = "Call"
    PUT = "Put"


class Moneyness(Enum):
    """Moneyness classification of an option"""

    DEEP_ITM = "DeepITM"
    ITM = "ITM"
    ATM = "ATM"
    OTM = "OTM"
    DEEP_OTM = "DeepOTM"


class VolatilityRegime(Enum):
    """Market volatility regime classification"""

    LOW = "Low"
    NORMAL = "Normal"
    HIGH = "High"
    EXTREME = "Extreme"


@dataclass
class QuoteDecision:
    """Decision output for market maker quoting behavior"""

    provide_quote: bool
    widen_spread: bool
    reduce_size: bool
    halt_quoting: bool


def classify_moneyness(
    underlying_price: int, strike: int, option_type: OptionType
) -> Moneyness:
    """
    Classify the moneyness of an option based on underlying price, strike, and option type.

    Args:
        underlying_price: Current price of the underlying asset
        strike: Strike price of the option
        option_type: Type of option (Call or Put)

    Returns:
        Moneyness classification
    """
    ratio = (underlying_price * 100) // strike  # Percent of strike

    if option_type == OptionType.CALL:
        if ratio >= 120:
            return Moneyness.DEEP_ITM
        elif ratio >= 105:
            return Moneyness.ITM
        elif ratio >= 95:
            return Moneyness.ATM
        elif ratio >= 80:
            return Moneyness.OTM
        else:
            return Moneyness.DEEP_OTM
    else:  # Put
        if ratio <= 80:
            return Moneyness.DEEP_ITM
        elif ratio <= 95:
            return Moneyness.ITM
        elif ratio <= 105:
            return Moneyness.ATM
        elif ratio <= 120:
            return Moneyness.OTM
        else:
            return Moneyness.DEEP_OTM


def classify_volatility(vol_bps: int) -> VolatilityRegime:
    """
    Classify volatility regime based on volatility in basis points.

    Args:
        vol_bps: Volatility in basis points (1 bp = 0.01%)

    Returns:
        VolatilityRegime classification
    """
    if vol_bps < 1500:  # < 15%
        return VolatilityRegime.LOW
    elif vol_bps < 3000:  # 15-30%
        return VolatilityRegime.NORMAL
    elif vol_bps < 5000:  # 30-50%
        return VolatilityRegime.HIGH
    else:  # > 50%
        return VolatilityRegime.EXTREME


def delta_within_limits(delta_pct: int, max_delta_pct: int) -> bool:
    """
    Check if delta exposure is within acceptable limits.

    Args:
        delta_pct: Current delta exposure as percentage
        max_delta_pct: Maximum allowed delta exposure

    Returns:
        True if delta is within limits
    """
    return delta_pct <= max_delta_pct and delta_pct >= -max_delta_pct


def expiry_risk_high(days_to_expiry: int) -> bool:
    """
    Determine if expiry risk is high (option expires soon).

    Args:
        days_to_expiry: Number of days until option expiration

    Returns:
        True if expiry is within high-risk threshold (<= 7 days)
    """
    return days_to_expiry <= 7


def inventory_at_limit(position_count: int, max_position: int) -> bool:
    """
    Check if inventory position has reached the limit.

    Args:
        position_count: Current number of positions
        max_position: Maximum allowed positions

    Returns:
        True if at or over position limit
    """
    return position_count >= max_position


def determine_quote_decision(
    option_type: OptionType,
    underlying_price: int,
    strike: int,
    vol_bps: int,
    days_to_expiry: int,
    delta_pct: int,
    max_delta_pct: int,
    position_count: int,
    max_position: int,
) -> QuoteDecision:
    """
    Determine quoting decision for options market maker based on market conditions and risk limits.

    This function evaluates option characteristics, market volatility, risk exposures, and inventory
    to decide whether to provide quotes and how to adjust spread and size.

    Args:
        option_type: Type of option (Call or Put)
        underlying_price: Current price of underlying asset
        strike: Strike price of the option
        vol_bps: Implied volatility in basis points
        days_to_expiry: Days until option expiration
        delta_pct: Current delta exposure as percentage
        max_delta_pct: Maximum allowed delta exposure
        position_count: Current number of positions held
        max_position: Maximum allowed positions

    Returns:
        QuoteDecision with quoting behavior parameters
    """
    # Classify market conditions
    moneyness = classify_moneyness(underlying_price, strike, option_type)
    vol_regime = classify_volatility(vol_bps)

    # Check inventory limits first
    at_limit = inventory_at_limit(position_count, max_position)

    if at_limit:
        return QuoteDecision(
            provide_quote=False,
            widen_spread=False,
            reduce_size=False,
            halt_quoting=True,
        )

    # Check delta risk
    delta_ok = delta_within_limits(delta_pct, max_delta_pct)

    if not delta_ok:
        return QuoteDecision(
            provide_quote=False,
            widen_spread=False,
            reduce_size=False,
            halt_quoting=True,
        )

    # Check volatility and expiry
    high_vol = vol_regime == VolatilityRegime.EXTREME
    expiry_soon = expiry_risk_high(days_to_expiry)

    if high_vol and expiry_soon:
        # Too risky: halt
        return QuoteDecision(
            provide_quote=False,
            widen_spread=False,
            reduce_size=False,
            halt_quoting=True,
        )
    elif high_vol or expiry_soon:
        # Risky: quote but widen spread
        return QuoteDecision(
            provide_quote=True, widen_spread=True, reduce_size=True, halt_quoting=False
        )
    else:
        # Normal quoting
        wide_spread = moneyness == Moneyness.DEEP_ITM or moneyness == Moneyness.DEEP_OTM
        return QuoteDecision(
            provide_quote=True,
            widen_spread=wide_spread,
            reduce_size=False,
            halt_quoting=False,
        )
