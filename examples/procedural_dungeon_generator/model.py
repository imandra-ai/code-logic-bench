from enum import Enum, auto


class RoomType(Enum):
    """Types of rooms in the dungeon."""

    ENTRANCE = auto()
    COMBAT = auto()
    TREASURE = auto()
    BOSS = auto()
    PUZZLE = auto()
    SECRET = auto()


class DifficultyTier(Enum):
    """Difficulty tiers for dungeon generation."""

    EASY = auto()
    MEDIUM = auto()
    HARD = auto()
    EXTREME = auto()


class PlacementResult(Enum):
    """Results of room placement validation."""

    APPROVED = auto()
    TOO_CLOSE = auto()
    TOO_FAR = auto()
    INVALID_SEQUENCE = auto()
    REJECTED = auto()


def _min_distance_from_entrance(room_type: RoomType) -> int:
    """Return the minimum distance from entrance for a given room type."""
    distance_map = {
        RoomType.ENTRANCE: 0,
        RoomType.COMBAT: 2,
        RoomType.TREASURE: 3,
        RoomType.PUZZLE: 4,
        RoomType.BOSS: 8,
        RoomType.SECRET: 5,
    }
    return distance_map[room_type]


def _max_count_for_type(room_type: RoomType, difficulty: DifficultyTier) -> int:
    """Return the maximum count allowed for a room type at a given difficulty."""
    count_map = {
        (RoomType.COMBAT, DifficultyTier.EASY): 3,
        (RoomType.COMBAT, DifficultyTier.MEDIUM): 5,
        (RoomType.COMBAT, DifficultyTier.HARD): 7,
        (RoomType.COMBAT, DifficultyTier.EXTREME): 10,
        (RoomType.TREASURE, DifficultyTier.EASY): 2,
        (RoomType.TREASURE, DifficultyTier.MEDIUM): 3,
        (RoomType.TREASURE, DifficultyTier.HARD): 4,
        (RoomType.TREASURE, DifficultyTier.EXTREME): 5,
        (RoomType.PUZZLE, DifficultyTier.EASY): 1,
        (RoomType.PUZZLE, DifficultyTier.MEDIUM): 2,
        (RoomType.PUZZLE, DifficultyTier.HARD): 3,
        (RoomType.PUZZLE, DifficultyTier.EXTREME): 4,
    }

    # Boss, Secret, and Entrance have fixed limits regardless of difficulty
    if room_type == RoomType.BOSS:
        return 1
    elif room_type == RoomType.SECRET:
        return 2
    elif room_type == RoomType.ENTRANCE:
        return 1

    return count_map[(room_type, difficulty)]


def _is_too_close(distance: int, room_type: RoomType) -> bool:
    """Check if a room placement is too close to the entrance."""
    min_dist = _min_distance_from_entrance(room_type)
    return distance < min_dist


def _is_too_far_for_boss(distance: int) -> bool:
    """Check if Boss room placement is too far from entrance."""
    return distance > 15


def _sequence_valid(room_type: RoomType, combat_count: int) -> bool:
    """Validate room placement sequence (Boss requires Combat rooms before it)."""
    if room_type == RoomType.BOSS:
        return combat_count >= 3
    return True


def determine_room_placement(
    room_type: RoomType,
    difficulty: DifficultyTier,
    distance_from_entrance: int,
    existing_room_count: int,
    existing_combat_count: int,
) -> PlacementResult:
    """
    Determine if a room placement is valid in the procedural dungeon.

    Validates room placements based on room type, difficulty tier, distance from
    entrance, existing room counts, and combat room prerequisites. Enforces distance
    constraints, sequence requirements, and room count limits.

    Args:
        room_type: The type of room to place
        difficulty: The difficulty tier of the dungeon
        distance_from_entrance: Distance of the room from dungeon entrance
        existing_room_count: Number of rooms of this type already placed
        existing_combat_count: Number of combat rooms already placed

    Returns:
        PlacementResult indicating whether the placement is approved or the reason
        for rejection
    """
    # Check sequence validity
    if not _sequence_valid(room_type, existing_combat_count):
        return PlacementResult.INVALID_SEQUENCE

    # Check distance constraints
    if _is_too_close(distance_from_entrance, room_type):
        return PlacementResult.TOO_CLOSE

    # Check if Boss is reachable
    if room_type == RoomType.BOSS and _is_too_far_for_boss(distance_from_entrance):
        return PlacementResult.TOO_FAR

    # Check room count limits
    max_allowed = _max_count_for_type(room_type, difficulty)
    if existing_room_count >= max_allowed:
        return PlacementResult.REJECTED

    return PlacementResult.APPROVED
