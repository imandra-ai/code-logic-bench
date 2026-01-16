from enum import Enum
from dataclasses import dataclass


class DifficultyLevel(Enum):
    """Represents the difficulty level of quiz questions."""

    EASY = 1
    MEDIUM = 2
    HARD = 3
    EXPERT = 4


class AnswerResult(Enum):
    """Represents the outcome of a student's answer."""

    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


@dataclass
class ProgressionDecision:
    """Decision output from the adaptive quiz engine."""

    new_difficulty: DifficultyLevel
    intervention_needed: bool
    confidence_change: int
    valid_progression: bool
    emergency_reset: bool


def _base_confidence_change(result: AnswerResult, confidence_level: int) -> int:
    """Calculate base confidence change from answer result."""
    if result == AnswerResult.CORRECT:
        return 5 if confidence_level >= 8 else 3
    elif result == AnswerResult.PARTIAL:
        return 1
    elif result == AnswerResult.INCORRECT:
        return -2 if confidence_level <= 3 else -4
    else:  # TIMEOUT
        return -6


def _apply_confidence_change(current_confidence: int, change: int) -> int:
    """Apply confidence change and clamp to valid range [0, 100]."""
    return max(0, min(100, current_confidence + change))


def _should_increase_difficulty(
    current_streak: int,
    response_time: int,
    avg_time: int,
    confidence_level: int,
    result: AnswerResult,
) -> bool:
    """Determine if difficulty should increase based on performance."""
    if result == AnswerResult.CORRECT:
        return (
            current_streak >= 3
            and response_time < (avg_time * 80 // 100)
            and confidence_level >= 7
        )
    return False


def _should_decrease_difficulty(
    current_streak: int, response_time: int, avg_time: int, result: AnswerResult
) -> bool:
    """Determine if difficulty should decrease based on performance."""
    if result == AnswerResult.INCORRECT:
        return current_streak == 0 and response_time > (avg_time * 150 // 100)
    elif result == AnswerResult.TIMEOUT:
        return True
    return False


def _needs_emergency_reset(
    current_confidence: int, total_answered: int, correct_answered: int
) -> bool:
    """Check if student needs emergency reset due to severe struggle."""
    return total_answered >= 10 and (
        correct_answered * 100 // total_answered < 20 or current_confidence < 15
    )


def _check_intervention_conditions(
    total_answered: int,
    correct_answered: int,
    current_streak: int,
    current_confidence: int,
) -> bool:
    """Check if intervention is needed using quorum voting on conditions."""
    c1 = total_answered >= 5 and correct_answered * 100 // total_answered < 40
    c2 = current_streak == 0 and total_answered >= 5
    c3 = current_confidence < 30
    c4 = total_answered >= 8 and correct_answered * 100 // total_answered < 25

    count = sum([c1, c2, c3, c4])
    return count >= 2


def _is_valid_progression(
    total_answered: int, correct_answered: int, current_streak: int
) -> bool:
    """Check if progression state is valid and not in ambiguous 'dead zone'."""
    # Dead zone: 5-7 questions with exactly 2-3 correct and streak 0 creates ambiguous state
    in_dead_zone = (
        5 <= total_answered <= 7 and 2 <= correct_answered <= 3 and current_streak == 0
    )

    # Invalid if numbers don't make sense
    invalid_data = correct_answered > total_answered or current_streak < 0

    return not (in_dead_zone or invalid_data)


def determine_student_progression(
    current_difficulty: DifficultyLevel,
    current_streak: int,
    total_answered: int,
    correct_answered: int,
    current_confidence: int,
    response_time: int,
    avg_response_time: int,
    result: AnswerResult,
    confidence_level: int,
) -> ProgressionDecision:
    """
    Determine student progression and difficulty adjustment in adaptive quiz.

    Analyzes student performance across multiple dimensions (streaks, confidence,
    response time) to make progression decisions. Handles edge cases including
    ambiguous states and emergency resets for severely struggling students.

    Args:
        current_difficulty: Current difficulty level
        current_streak: Current streak of correct answers
        total_answered: Total questions answered so far
        correct_answered: Total correct answers so far
        current_confidence: Current confidence score (0-100)
        response_time: Time taken for current answer
        avg_response_time: Average response time
        result: Result of current answer
        confidence_level: Student's self-reported confidence level

    Returns:
        ProgressionDecision with new difficulty, intervention status, and metadata
    """
    # Check validity first
    valid = _is_valid_progression(total_answered, correct_answered, current_streak)

    if not valid:
        return ProgressionDecision(
            new_difficulty=DifficultyLevel.EASY,
            intervention_needed=True,
            confidence_change=0,
            valid_progression=False,
            emergency_reset=False,
        )

    # Check for emergency reset
    emergency = _needs_emergency_reset(
        current_confidence, total_answered, correct_answered
    )

    if emergency:
        return ProgressionDecision(
            new_difficulty=DifficultyLevel.EASY,
            intervention_needed=True,
            confidence_change=20,  # Boost to encourage
            valid_progression=True,
            emergency_reset=True,
        )

    # Normal progression logic
    base_change = _base_confidence_change(result, confidence_level)
    new_confidence = _apply_confidence_change(current_confidence, base_change)

    # Determine difficulty adjustment
    current_diff_value = current_difficulty.value
    should_increase = _should_increase_difficulty(
        current_streak, response_time, avg_response_time, confidence_level, result
    )
    should_decrease = _should_decrease_difficulty(
        current_streak, response_time, avg_response_time, result
    )

    if should_increase:
        new_diff_value = min(4, current_diff_value + 1)
    elif should_decrease:
        new_diff_value = max(1, current_diff_value - 1)
    else:
        new_diff_value = current_diff_value

    new_difficulty = DifficultyLevel(new_diff_value)

    # Update correct count for intervention check
    new_correct = (
        correct_answered + 1
        if result in (AnswerResult.CORRECT, AnswerResult.PARTIAL)
        else correct_answered
    )
    new_total = total_answered + 1

    # Check if intervention needed (quorum)
    intervention = _check_intervention_conditions(
        new_total, new_correct, 0, new_confidence
    )

    return ProgressionDecision(
        new_difficulty=new_difficulty,
        intervention_needed=intervention,
        confidence_change=base_change,
        valid_progression=True,
        emergency_reset=False,
    )
