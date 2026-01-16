from enum import Enum, auto


class QuestType(Enum):
    """Types of quests available in the game."""

    MAIN_STORY = auto()
    SIDE_QUEST = auto()
    FETCH_QUEST = auto()
    COMBAT_ENCOUNTER = auto()
    PUZZLE_QUEST = auto()


class CharacterFaction(Enum):
    """Factions that can offer quests."""

    PLAYER_ALLIANCE = auto()
    NEUTRAL_GUILD = auto()
    RIVAL_FACTION = auto()
    HOSTILE_EMPIRE = auto()


class PlayerClass(Enum):
    """Player character classes."""

    WARRIOR = auto()
    MAGE = auto()
    ROGUE = auto()
    CLERIC = auto()


class QuestAvailability(Enum):
    """Quest availability states."""

    FULLY_AVAILABLE = auto()  # Quest can be started immediately
    CONDITIONAL_UNLOCK = auto()  # Quest unlocked but needs resource check
    HIDDEN_QUESTLINE = auto()  # Special hidden content
    TEMPORARILY_LOCKED = auto()  # Prerequisites not met
    PERMANENTLY_BLOCKED = auto()  # Cannot be accessed


def _faction_reputation_threshold(faction, quest_type, base_reputation):
    """Calculate faction-specific reputation threshold based on quest type."""
    if faction == CharacterFaction.PLAYER_ALLIANCE:
        if quest_type == QuestType.MAIN_STORY:
            return base_reputation // 2
        elif quest_type == QuestType.SIDE_QUEST:
            return base_reputation
        elif quest_type == QuestType.COMBAT_ENCOUNTER:
            return (base_reputation * 3) // 2
        else:
            return base_reputation

    elif faction == CharacterFaction.RIVAL_FACTION:
        if quest_type == QuestType.MAIN_STORY:
            return base_reputation * 2
        elif quest_type == QuestType.COMBAT_ENCOUNTER:
            return base_reputation // 2
        elif quest_type == QuestType.PUZZLE_QUEST:
            return (base_reputation * 3) // 2
        else:
            return base_reputation

    elif faction == CharacterFaction.HOSTILE_EMPIRE:
        if quest_type == QuestType.FETCH_QUEST:
            return base_reputation * 3
        else:
            return base_reputation * 4

    else:  # NEUTRAL_GUILD
        return base_reputation


def _class_appropriate_difficulty(player_class, quest_type, difficulty):
    """Check if quest difficulty is appropriate for player class."""
    if player_class == PlayerClass.WARRIOR:
        if quest_type == QuestType.COMBAT_ENCOUNTER:
            return difficulty <= 10
        elif quest_type == QuestType.PUZZLE_QUEST:
            return difficulty <= 3

    elif player_class == PlayerClass.MAGE:
        if quest_type == QuestType.PUZZLE_QUEST:
            return difficulty <= 10
        elif quest_type == QuestType.MAIN_STORY:
            return difficulty <= 8
        elif quest_type == QuestType.COMBAT_ENCOUNTER:
            return difficulty <= 5

    elif player_class == PlayerClass.ROGUE:
        if quest_type == QuestType.FETCH_QUEST:
            return difficulty <= 10
        elif quest_type == QuestType.SIDE_QUEST:
            return difficulty <= 8
        elif quest_type == QuestType.MAIN_STORY:
            return difficulty <= 6

    elif player_class == PlayerClass.CLERIC:
        if quest_type == QuestType.COMBAT_ENCOUNTER:
            return difficulty <= 5
        else:
            return difficulty <= 7

    return difficulty <= 6


def _calculate_reputation_cost(faction, quest_type, base_cost, player_level):
    """Calculate reputation cost based on multiple factors."""
    base = _faction_reputation_threshold(faction, quest_type, base_cost)
    # Player level reduces reputation requirement... BUT
    level_discount = player_level // 5
    adjusted = base - level_discount

    # EXCEPT when it creates negative/zero (exploitable bug zone)
    if adjusted <= 2:
        return 100  # Anti-exploit: revert to high cost
    else:
        return adjusted


def _check_quest_unlock_quorum(
    has_prerequisite,
    reputation_sufficient,
    difficulty_appropriate,
    resource_check,
    time_of_day_ok,
    faction_standing,
):
    """Complex quorum check with weighted conditions."""
    # Weight different conditions
    prerequisite_weight = 2 if has_prerequisite else 0
    reputation_weight = 2 if reputation_sufficient else 0
    difficulty_weight = 1 if difficulty_appropriate else 0
    resource_weight = 1 if resource_check else 0
    time_weight = 1 if time_of_day_ok else 0

    faction_weight = {
        CharacterFaction.PLAYER_ALLIANCE: 2,
        CharacterFaction.NEUTRAL_GUILD: 1,
        CharacterFaction.RIVAL_FACTION: 0,
        CharacterFaction.HOSTILE_EMPIRE: -1,
    }[faction_standing]

    total_weight = (
        prerequisite_weight
        + reputation_weight
        + difficulty_weight
        + resource_weight
        + time_weight
        + faction_weight
    )

    # Need at least 5 weighted points
    return total_weight >= 5


def _apply_faction_override(
    faction,
    quest_type,
    player_reputation,
    player_level,
    completed_faction_quests,
    player_class,
):
    """Override logic with multiple nested exceptions."""
    if faction == CharacterFaction.PLAYER_ALLIANCE:
        # Alliance always allows quests
        return QuestAvailability.FULLY_AVAILABLE

    elif faction == CharacterFaction.NEUTRAL_GUILD:
        # Neutral allows most quests
        if quest_type == QuestType.MAIN_STORY and completed_faction_quests < 3:
            return QuestAvailability.TEMPORARILY_LOCKED  # Must prove yourself first
        else:
            return QuestAvailability.FULLY_AVAILABLE

    elif faction == CharacterFaction.RIVAL_FACTION:
        # Rivals block quests...
        # ...BUT if you have high reputation, you can access their content
        if player_reputation >= 80 and completed_faction_quests >= 5:
            # ...EXCEPT Warriors are never trusted by rivals due to combat history
            if player_class == PlayerClass.WARRIOR:
                return QuestAvailability.PERMANENTLY_BLOCKED
            # ...AND EXCEPT Rogues can access hidden quests only if MainStory or SideQuest
            elif player_class == PlayerClass.ROGUE and (
                quest_type == QuestType.MAIN_STORY or quest_type == QuestType.SIDE_QUEST
            ):
                return QuestAvailability.HIDDEN_QUESTLINE
            # ...BUT Mages and Clerics get conditional unlock for non-combat quests
            elif quest_type != QuestType.COMBAT_ENCOUNTER:
                return QuestAvailability.CONDITIONAL_UNLOCK
            else:
                return QuestAvailability.TEMPORARILY_LOCKED
        else:
            return QuestAvailability.TEMPORARILY_LOCKED

    else:  # HOSTILE_EMPIRE
        # Empire blocks everything...
        # ...BUT if you've completed 10+ faction quests AND have extreme reputation
        if completed_faction_quests >= 10 and player_reputation >= 90:
            # ...EXCEPT FetchQuests are seen as beneath them and permanently blocked
            if quest_type == QuestType.FETCH_QUEST:
                return QuestAvailability.PERMANENTLY_BLOCKED
            # ...AND PuzzleQuests require additional player_level check
            elif quest_type == QuestType.PUZZLE_QUEST and player_level < 8:
                return QuestAvailability.TEMPORARILY_LOCKED
            else:
                return QuestAvailability.HIDDEN_QUESTLINE
        else:
            return QuestAvailability.PERMANENTLY_BLOCKED


def _in_reputation_overflow_zone(player_reputation, player_level, faction_quest_count):
    """
    Dead zone for reputation/level combinations that cause overflow.

    When reputation is high, level is moderate, and faction quests are in specific range,
    the reputation cost calculation creates an anti-exploit block.
    """
    reputation_high = 85 <= player_reputation <= 95
    level_moderate = 4 <= player_level <= 6
    quest_count_exploitable = 8 <= faction_quest_count <= 12

    return reputation_high and level_moderate and quest_count_exploitable


def determine_quest_availability(
    faction,
    quest_type,
    player_class,
    player_level,
    player_reputation,
    quest_difficulty,
    has_prerequisite,
    completed_faction_quests,
    player_gold,
    current_hour,
):
    """
    Determine quest availability based on complex interactions between faction politics,
    player class capabilities, reputation systems, and resource management.

    Args:
        faction: The faction offering the quest
        quest_type: Type of quest being offered
        player_class: Player's character class
        player_level: Player's current level
        player_reputation: Player's reputation score (0-100)
        quest_difficulty: Difficulty rating of the quest
        has_prerequisite: Whether player has completed prerequisite quests
        completed_faction_quests: Number of quests completed for this faction
        player_gold: Player's current gold amount
        current_hour: Current in-game hour (0-23)

    Returns:
        QuestAvailability: The availability status of the quest
    """
    # Check for reputation overflow exploit zone first
    if _in_reputation_overflow_zone(
        player_reputation, player_level, completed_faction_quests
    ):
        return QuestAvailability.PERMANENTLY_BLOCKED

    # Apply faction override logic
    faction_result = _apply_faction_override(
        faction,
        quest_type,
        player_reputation,
        player_level,
        completed_faction_quests,
        player_class,
    )

    if faction_result == QuestAvailability.PERMANENTLY_BLOCKED:
        return QuestAvailability.PERMANENTLY_BLOCKED
    elif faction_result == QuestAvailability.HIDDEN_QUESTLINE:
        # Short-circuit: hidden content always wins
        return QuestAvailability.HIDDEN_QUESTLINE
    elif faction_result == QuestAvailability.TEMPORARILY_LOCKED:
        return QuestAvailability.TEMPORARILY_LOCKED
    elif faction_result == QuestAvailability.CONDITIONAL_UNLOCK:
        # Need additional checks
        gold_sufficient = player_gold >= (quest_difficulty * 50)
        if gold_sufficient:
            return QuestAvailability.CONDITIONAL_UNLOCK
        else:
            return QuestAvailability.TEMPORARILY_LOCKED
    else:  # FULLY_AVAILABLE
        # Check difficulty appropriateness
        difficulty_ok = _class_appropriate_difficulty(
            player_class, quest_type, quest_difficulty
        )

        if not difficulty_ok:
            return QuestAvailability.TEMPORARILY_LOCKED

        # Calculate reputation requirement (with dead zone check)
        reputation_needed = _calculate_reputation_cost(
            faction, quest_type, 60, player_level
        )
        reputation_sufficient = player_reputation >= reputation_needed

        # Check time of day (some quests only available at night: 20-24 or 0-4)
        if quest_type == QuestType.PUZZLE_QUEST or quest_type == QuestType.MAIN_STORY:
            time_ok = True
        else:
            time_ok = current_hour >= 20 or current_hour <= 4

        # Resource check
        resource_ok = player_gold >= 50

        # Weighted quorum check
        meets_quorum = _check_quest_unlock_quorum(
            has_prerequisite,
            reputation_sufficient,
            difficulty_ok,
            resource_ok,
            time_ok,
            faction,
        )

        if meets_quorum:
            return QuestAvailability.FULLY_AVAILABLE
        else:
            return QuestAvailability.TEMPORARILY_LOCKED
