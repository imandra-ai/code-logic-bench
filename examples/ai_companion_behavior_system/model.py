from enum import Enum
from dataclasses import dataclass
from typing import NamedTuple


class LoyaltyLevel(Enum):
    """Companion loyalty levels from hostile to fanatical."""

    HOSTILE = 0
    DISTRUSTFUL = 1
    WARY = 2
    NEUTRAL = 3
    FRIENDLY = 4
    DEVOTED = 5
    FANATICAL = 6


class MoodState(Enum):
    """Emotional states of the companion."""

    HAPPY = "happy"
    CONTENT = "content"
    NEUTRAL = "neutral"
    ANNOYED = "annoyed"
    ANGRY = "angry"
    DEPRESSED = "depressed"


class CompanionClass(Enum):
    """Combat role classes."""

    WARRIOR = "warrior"
    MAGE = "mage"
    HEALER = "healer"


class ContextType(Enum):
    """Situational context types."""

    COMBAT = "combat"
    SOCIAL = "social"
    NO_CONTEXT = "no_context"


class CompanionAction(Enum):
    """Possible companion actions."""

    ATTACK_ENEMY = "attack_enemy"
    HEAL_PLAYER = "heal_player"
    OFFER_ADVICE = "offer_advice"
    REFUSE_ORDER = "refuse_order"
    LEAVE_PARTY = "leave_party"
    COMPLAIN = "complain"
    STAY_SILENT = "stay_silent"


class ActionDecision(NamedTuple):
    """Result of behavior determination."""

    chosen_action: CompanionAction
    will_comply: bool
    abandonment_risk_percent: int


def _loyalty_to_int(loyalty: LoyaltyLevel) -> int:
    """Convert loyalty level to numeric value."""
    return loyalty.value


def _mood_to_modifier(mood: MoodState) -> int:
    """Calculate mood impact modifier."""
    mood_modifiers = {
        MoodState.HAPPY: 15,
        MoodState.CONTENT: 5,
        MoodState.NEUTRAL: 0,
        MoodState.ANNOYED: -5,
        MoodState.ANGRY: -15,
        MoodState.DEPRESSED: -10,
    }
    return mood_modifiers[mood]


def _calculate_abandonment_risk(
    loyalty: LoyaltyLevel, mood: MoodState, trust_score: int, needs_attention: bool
) -> int:
    """Calculate abandonment risk percentage (0, 25, 50, 75, or 100)."""
    c1 = _loyalty_to_int(loyalty) <= 1
    c2 = mood in (MoodState.ANGRY, MoodState.DEPRESSED)
    c3 = trust_score <= 20
    c4 = needs_attention

    count = sum([c1, c2, c3, c4])
    return count * 25


def _check_compliance(loyalty: LoyaltyLevel, mood: MoodState, trust_score: int) -> bool:
    """Determine if companion will comply with orders."""
    base = _loyalty_to_int(loyalty) * 15
    mood_mod = _mood_to_modifier(mood)
    trust_mod = trust_score // 5
    total = base + mood_mod + trust_mod
    return total >= 50


def _is_valid_state(loyalty: LoyaltyLevel, trust_score: int) -> bool:
    """Check if companion state is valid (not in dead zone or invalid range)."""
    # Dead zone: Wary with trust 18-22 creates ambiguous state
    in_dead_zone = loyalty == LoyaltyLevel.WARY and 18 <= trust_score <= 22
    invalid_score = trust_score < 0 or trust_score > 100
    return not (in_dead_zone or invalid_score)


def determine_companion_behavior(
    companion_class: CompanionClass,
    loyalty: LoyaltyLevel,
    mood: MoodState,
    trust_score: int,
    needs_attention: bool,
    context: ContextType,
) -> ActionDecision:
    """
    Determine companion behavior based on multiple factors.

    Args:
        companion_class: The companion's combat role
        loyalty: Current loyalty level
        mood: Current mood state
        trust_score: Trust value (0-100)
        needs_attention: Whether companion needs attention
        context: Current situational context

    Returns:
        ActionDecision with chosen action, compliance status, and abandonment risk
    """
    # Check validity first
    if not _is_valid_state(loyalty, trust_score):
        return ActionDecision(
            chosen_action=CompanionAction.STAY_SILENT,
            will_comply=False,
            abandonment_risk_percent=100,
        )

    # Calculate abandonment risk (overrides everything if >= 75)
    abandonment = _calculate_abandonment_risk(
        loyalty, mood, trust_score, needs_attention
    )

    if abandonment >= 75:
        return ActionDecision(
            chosen_action=CompanionAction.LEAVE_PARTY,
            will_comply=False,
            abandonment_risk_percent=abandonment,
        )

    will_comply = _check_compliance(loyalty, mood, trust_score)

    # Determine action based on context
    if context == ContextType.COMBAT:
        if _loyalty_to_int(loyalty) >= 3 and trust_score >= 50:
            if companion_class == CompanionClass.HEALER:
                action = CompanionAction.HEAL_PLAYER
            else:
                action = CompanionAction.ATTACK_ENEMY
        elif _loyalty_to_int(loyalty) <= 2 and mood == MoodState.ANGRY:
            action = CompanionAction.REFUSE_ORDER
        else:
            action = CompanionAction.STAY_SILENT

    elif context == ContextType.SOCIAL:
        if _loyalty_to_int(loyalty) >= 4 and trust_score >= 60:
            action = CompanionAction.OFFER_ADVICE
        else:
            action = CompanionAction.STAY_SILENT

    else:  # NoContext
        if needs_attention and _loyalty_to_int(loyalty) <= 2:
            action = CompanionAction.COMPLAIN
        elif abandonment >= 50:
            action = CompanionAction.COMPLAIN
        else:
            action = CompanionAction.STAY_SILENT

    return ActionDecision(
        chosen_action=action,
        will_comply=will_comply,
        abandonment_risk_percent=abandonment,
    )
