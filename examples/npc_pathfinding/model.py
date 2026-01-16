from enum import Enum
from dataclasses import dataclass


class NpcType(Enum):
    """Types of NPCs with different movement capabilities."""

    CIVILIAN = "civilian"
    GUARD = "guard"
    MERCHANT = "merchant"
    WARRIOR = "warrior"
    SCOUT = "scout"


class Terrain(Enum):
    """Terrain types with varying traversal costs."""

    OPEN = "open"
    ROUGH = "rough"
    DIFFICULT = "difficult"
    WATER = "water"
    BLOCKED = "blocked"


class ObstacleType(Enum):
    """Types of obstacles that may block paths."""

    STATIC = "static"
    DYNAMIC = "dynamic"
    TEMPORARY = "temporary"


@dataclass
class PathDecision:
    """Result of path validation check."""

    path_valid: bool
    requires_replanning: bool
    avoidance_needed: bool
    estimated_cost: int


def terrain_cost(terrain: Terrain) -> int:
    """Calculate the base cost of traversing a terrain type."""
    costs = {
        Terrain.OPEN: 1,
        Terrain.ROUGH: 2,
        Terrain.DIFFICULT: 4,
        Terrain.WATER: 8,
        Terrain.BLOCKED: 100,
    }
    return costs[terrain]


def npc_speed(npc_type: NpcType) -> int:
    """Get the speed modifier for an NPC type."""
    speeds = {
        NpcType.CIVILIAN: 1,
        NpcType.GUARD: 2,
        NpcType.MERCHANT: 1,
        NpcType.WARRIOR: 3,
        NpcType.SCOUT: 4,
    }
    return speeds[npc_type]


def can_traverse(npc_type: NpcType, terrain: Terrain) -> bool:
    """Check if an NPC can traverse a specific terrain type."""
    if terrain == Terrain.BLOCKED:
        return False
    if terrain == Terrain.WATER and npc_type in (NpcType.CIVILIAN, NpcType.MERCHANT):
        return False
    if terrain == Terrain.DIFFICULT and npc_type == NpcType.MERCHANT:
        return False
    return True


def obstacle_blocks(obstacle_type: ObstacleType, distance: int) -> bool:
    """Determine if an obstacle blocks the path based on distance."""
    if obstacle_type == ObstacleType.STATIC:
        return distance <= 1
    elif obstacle_type == ObstacleType.DYNAMIC:
        return distance <= 2
    elif obstacle_type == ObstacleType.TEMPORARY:
        return distance <= 1
    return False


def needs_replan(stuck_count: int, last_replan_time: int, current_time: int) -> bool:
    """Check if the path needs replanning based on stuck state and time."""
    return stuck_count >= 3 or (current_time - last_replan_time) >= 10


def determine_path_validity(
    npc_type: NpcType,
    terrain: Terrain,
    obstacle_type: ObstacleType,
    obstacle_distance: int,
    stuck_count: int,
    last_replan_time: int,
    current_time: int,
    path_length: int,
) -> PathDecision:
    """
    Determine if a path is valid for an NPC.

    Validates path based on NPC type, terrain, obstacles, and stuck state.
    Returns a PathDecision indicating validity, replanning needs, and estimated cost.
    """
    # Check if NPC can traverse this terrain
    can_go = can_traverse(npc_type, terrain)

    if not can_go:
        return PathDecision(
            path_valid=False,
            requires_replanning=True,
            avoidance_needed=False,
            estimated_cost=0,
        )

    # Check obstacle
    blocked = obstacle_blocks(obstacle_type, obstacle_distance)

    if blocked:
        return PathDecision(
            path_valid=False,
            requires_replanning=False,
            avoidance_needed=True,
            estimated_cost=0,
        )

    # Check if stuck/need replan
    replan = needs_replan(stuck_count, last_replan_time, current_time)

    if replan:
        return PathDecision(
            path_valid=False,
            requires_replanning=True,
            avoidance_needed=False,
            estimated_cost=0,
        )

    # Path valid - calculate cost
    base_cost = terrain_cost(terrain)
    speed = npc_speed(npc_type)
    total_cost = (base_cost * path_length) // speed

    return PathDecision(
        path_valid=True,
        requires_replanning=False,
        avoidance_needed=False,
        estimated_cost=total_cost,
    )
