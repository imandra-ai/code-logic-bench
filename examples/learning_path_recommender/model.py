from enum import Enum


class DifficultyLevel(Enum):
    """Educational module difficulty levels."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class GoalPriority(Enum):
    """Priority levels for learning goals."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LearningStyle(Enum):
    """Learning style preferences."""

    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"


class RecommendationResult(Enum):
    """Module recommendation outcomes."""

    RECOMMENDED = "recommended"
    DEFERRED = "deferred"
    EXCLUDED = "excluded"


def _high_priority_override(
    goal_priority: GoalPriority, competency_level: int, style_match: bool
) -> bool:
    """
    High priority goals can override style mismatch if student has minimum competency (30%).

    Args:
        goal_priority: Priority level of the learning goal
        competency_level: Student's competency level (0-100)
        style_match: Whether learning styles match

    Returns:
        True if high priority override conditions are met
    """
    return (
        goal_priority == GoalPriority.HIGH
        and competency_level >= 30
        and not style_match
    )


def _prerequisite_threshold(difficulty: DifficultyLevel) -> int:
    """
    Get prerequisite competency threshold based on module difficulty.

    Args:
        difficulty: Module difficulty level

    Returns:
        Required competency level threshold
    """
    thresholds = {
        DifficultyLevel.BEGINNER: 40,
        DifficultyLevel.INTERMEDIATE: 60,
        DifficultyLevel.ADVANCED: 70,
        DifficultyLevel.EXPERT: 80,
    }
    return thresholds[difficulty]


def _in_competency_dead_zone(
    competency_level: int, difficulty: DifficultyLevel
) -> bool:
    """
    Check if competency level is in ambiguous zone near threshold (±5%).

    Competency levels near thresholds are uncertain. For example, with Intermediate
    (60% threshold), 55-65% is considered a dead zone.

    Args:
        competency_level: Student's competency level (0-100)
        difficulty: Module difficulty level

    Returns:
        True if competency is in the dead zone
    """
    threshold = _prerequisite_threshold(difficulty)
    return (threshold - 5) <= competency_level <= (threshold + 5)


def _goal_relevance_score(goal_priority: GoalPriority) -> int:
    """
    Calculate numerical score for goal priority.

    Args:
        goal_priority: Priority level of the learning goal

    Returns:
        Numerical relevance score (1-3)
    """
    scores = {GoalPriority.HIGH: 3, GoalPriority.MEDIUM: 2, GoalPriority.LOW: 1}
    return scores[goal_priority]


def determine_module_recommendation(
    module_difficulty: DifficultyLevel,
    style_matches: bool,
    competency_level: int,
    engagement_good: bool,
    goal_priority: GoalPriority,
    goal_aligned: bool,
) -> RecommendationResult:
    """
    Determine whether to recommend, defer, or exclude an educational module.

    Uses quorum-based scoring with multiple factors: competency levels, learning style
    preferences, goal alignment, and engagement. Implements high-priority goal override,
    difficulty-dependent prerequisite thresholds, and competency dead zones.

    Args:
        module_difficulty: Difficulty level of the module
        style_matches: Whether module style matches student's learning style
        competency_level: Student's competency level (0-100)
        engagement_good: Whether student has good engagement scores
        goal_priority: Priority level of the learning goal
        goal_aligned: Whether module aligns with student's goals

    Returns:
        Recommendation result (RECOMMENDED, DEFERRED, or EXCLUDED)
    """
    # Check competency dead zone first - defer for assessment
    if _in_competency_dead_zone(competency_level, module_difficulty):
        return RecommendationResult.DEFERRED

    # Check if prerequisites are met
    threshold = _prerequisite_threshold(module_difficulty)
    prereq_met = competency_level >= threshold

    # If prerequisites not met, exclude immediately
    if not prereq_met:
        return RecommendationResult.EXCLUDED

    # Check high priority override - can bypass style mismatch
    if _high_priority_override(goal_priority, competency_level, style_matches):
        return RecommendationResult.RECOMMENDED

    # Normal recommendation logic with quorum scoring

    # Check if goal is relevant (aligned and priority >= Medium)
    goal_relevant = goal_aligned and _goal_relevance_score(goal_priority) >= 2

    # Calculate recommendation score (need 3 out of 4 factors)
    score = sum([prereq_met, style_matches, goal_relevant, engagement_good])

    # Apply quorum-based decision
    if score >= 3:
        return RecommendationResult.RECOMMENDED
    elif score >= 2:
        return RecommendationResult.DEFERRED  # Borderline cases
    else:
        return RecommendationResult.EXCLUDED
