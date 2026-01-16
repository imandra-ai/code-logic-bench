from enum import Enum


class PositionDirection(Enum):
    """Position direction indicator."""

    LONG = "Long"
    NEUTRAL = "Neutral"
    SHORT = "Short"


class VolatilityRegime(Enum):
    """Market volatility regime classification."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class QuoteDecision(Enum):
    """Market maker quoting decision."""

    FULL_SIZE = "FullSize"
    REDUCED_SIZE = "ReducedSize"
    NO_QUOTE = "NoQuote"


def _high_volatility_override(
    volatility_regime: VolatilityRegime, position_pct: int
) -> bool:
    """
    Check if high volatility override applies.

    High volatility forces wide spreads, but only if position is not at extreme
    (abs < 80% of max).
    """
    return volatility_regime == VolatilityRegime.HIGH and position_pct < 80


def _minimum_spread(volatility_regime: VolatilityRegime) -> int:
    """
    Get minimum spread in basis points based on volatility regime.

    Returns:
        10 basis points for Low volatility
        25 basis points for Medium volatility
        50 basis points for High volatility
    """
    if volatility_regime == VolatilityRegime.LOW:
        return 10
    elif volatility_regime == VolatilityRegime.MEDIUM:
        return 25
    else:  # HIGH
        return 50


def _in_position_dead_zone(position_pct: int) -> bool:
    """
    Check if position is in the dead zone (85-95% of max).

    Position 85-95% of max is ambiguous - too risky to quote full size,
    but not extreme enough to stop entirely.
    """
    return 85 <= position_pct <= 95


def _position_percentage(position: int, max_position: int) -> int:
    """Calculate position as percentage of maximum position."""
    if max_position == 0:
        return 0
    return (abs(position) * 100) // max_position


def _adverse_selection_detected(consecutive_adverse: int) -> bool:
    """Check if adverse selection is detected (3 or more consecutive adverse events)."""
    return consecutive_adverse >= 3


def _calculate_quote_score(
    position_safe: bool,
    spread_adequate: bool,
    no_adverse: bool,
    volatility_ok: bool,
    depth_good: bool,
    momentum_favorable: bool,
) -> int:
    """
    Calculate quote score based on favorable conditions.

    Full size quoting needs 4 out of 6 conditions to be met.
    """
    return sum(
        [
            position_safe,
            spread_adequate,
            no_adverse,
            volatility_ok,
            depth_good,
            momentum_favorable,
        ]
    )


def determine_quote_decision(
    position: int,
    max_position: int,
    consecutive_adverse: int,
    volatility_regime: VolatilityRegime,
    spread_bps: int,
    market_depth: int,
    momentum: int,
) -> QuoteDecision:
    """
    Determine market maker quoting decision.

    Evaluates whether to provide liquidity at full size, reduced size, or stop
    quoting based on inventory position, volatility regime, adverse selection
    patterns, market depth, and spread adequacy.

    Args:
        position: Current inventory position
        max_position: Maximum allowed position
        consecutive_adverse: Number of consecutive adverse selection events
        volatility_regime: Current volatility regime (Low/Medium/High)
        spread_bps: Current spread in basis points
        market_depth: Current market depth
        momentum: Market momentum (-100 to 100)

    Returns:
        QuoteDecision indicating FullSize, ReducedSize, or NoQuote
    """
    # Calculate position percentage
    position_pct = _position_percentage(position, max_position)

    # Check position dead zone first
    in_dead_zone = _in_position_dead_zone(position_pct)

    if in_dead_zone:
        # Dead zone → quote with reduced size
        return QuoteDecision.REDUCED_SIZE

    # Check if position at extreme (≥ 100%)
    if position_pct >= 100:
        # Stop quoting at max position
        return QuoteDecision.NO_QUOTE

    # Check high volatility override
    is_vol_override = _high_volatility_override(volatility_regime, position_pct)

    if is_vol_override:
        # High volatility with safe position → quote aggressively
        return QuoteDecision.FULL_SIZE

    # Normal quoting logic with quorum

    # Check individual conditions
    position_safe = position_pct <= 70

    min_spread = _minimum_spread(volatility_regime)
    spread_adequate = spread_bps >= min_spread

    no_adverse = not _adverse_selection_detected(consecutive_adverse)

    volatility_ok = volatility_regime != VolatilityRegime.HIGH

    depth_good = market_depth >= 300

    momentum_ok = abs(momentum) <= 50

    # Calculate quote score (quorum)
    score = _calculate_quote_score(
        position_safe,
        spread_adequate,
        no_adverse,
        volatility_ok,
        depth_good,
        momentum_ok,
    )

    # Need 4 out of 6 for full size
    if score >= 4:
        return QuoteDecision.FULL_SIZE
    elif score >= 2:
        # Borderline conditions
        return QuoteDecision.REDUCED_SIZE
    else:
        return QuoteDecision.NO_QUOTE
