from enum import Enum
from dataclasses import dataclass


class RouterState(Enum):
    """OSPF router neighbor states."""

    DOWN = "Down"
    INIT = "Init"
    TWO_WAY = "TwoWay"
    EX_START = "ExStart"
    EXCHANGE = "Exchange"
    LOADING = "Loading"
    FULL = "Full"


class LSAAgeCategory(Enum):
    """LSA age classification for freshness determination."""

    FRESH = "Fresh"
    VALID = "Valid"
    MAX_AGE = "MaxAge"


@dataclass
class NeighborDecision:
    """Decision result for OSPF neighbor management."""

    establish_adjacency: bool
    become_full: bool
    priority_higher: bool
    dead_timer_expired: bool


def categorize_lsa_age(age_seconds: int) -> LSAAgeCategory:
    """Categorize LSA age based on OSPF freshness requirements.

    Args:
        age_seconds: Age of the LSA in seconds

    Returns:
        LSA age category (Fresh < 5min, Valid < 1hr, MaxAge >= 1hr)
    """
    if age_seconds < 300:  # < 5 minutes
        return LSAAgeCategory.FRESH
    elif age_seconds < 3600:  # < 1 hour
        return LSAAgeCategory.VALID
    else:  # >= 1 hour, needs refresh
        return LSAAgeCategory.MAX_AGE


def neighbor_dead(last_hello_seconds: int, dead_interval: int) -> bool:
    """Check if neighbor is considered dead based on hello timeout.

    Args:
        last_hello_seconds: Seconds since last hello received
        dead_interval: Dead interval threshold in seconds

    Returns:
        True if neighbor is dead (timeout exceeded)
    """
    return last_hello_seconds >= dead_interval


def state_allows_full(current_state: RouterState) -> bool:
    """Check if current state allows transition to Full state.

    Args:
        current_state: Current OSPF neighbor state

    Returns:
        True if state can progress to Full
    """
    return current_state in (
        RouterState.FULL,
        RouterState.LOADING,
        RouterState.EXCHANGE,
    )


def has_higher_priority(
    my_priority: int, neighbor_priority: int, my_id: int, neighbor_id: int
) -> bool:
    """Determine if local router has higher priority for DR election.

    Args:
        my_priority: Local router priority
        neighbor_priority: Neighbor router priority
        my_id: Local router ID (tiebreaker)
        neighbor_id: Neighbor router ID (tiebreaker)

    Returns:
        True if local router wins priority comparison
    """
    if my_priority > neighbor_priority:
        return True
    elif my_priority < neighbor_priority:
        return False
    else:
        # Tiebreaker: higher ID wins
        return my_id > neighbor_id


def should_establish_adjacency(current_state: RouterState) -> bool:
    """Check if adjacency establishment should proceed.

    Args:
        current_state: Current OSPF neighbor state

    Returns:
        True if in Init or TwoWay state (adjacency formation phase)
    """
    return current_state in (RouterState.INIT, RouterState.TWO_WAY)


def determine_neighbor_status(
    current_state: RouterState,
    my_priority: int,
    neighbor_priority: int,
    my_router_id: int,
    neighbor_router_id: int,
    last_hello_seconds: int,
    dead_interval: int,
    lsa_age_seconds: int,
) -> NeighborDecision:
    """Determine OSPF neighbor adjacency status and state transitions.

    This function evaluates neighbor health, adjacency establishment,
    Full state transitions, and priority comparisons according to OSPF
    state machine rules.

    Args:
        current_state: Current OSPF neighbor state
        my_priority: Local router priority
        neighbor_priority: Neighbor router priority
        my_router_id: Local router ID
        neighbor_router_id: Neighbor router ID
        last_hello_seconds: Seconds since last hello received
        dead_interval: Dead interval threshold
        lsa_age_seconds: Age of LSA in seconds

    Returns:
        NeighborDecision with adjacency and state transition decisions
    """
    # Check dead timer first
    is_dead = neighbor_dead(last_hello_seconds, dead_interval)

    if is_dead:
        return NeighborDecision(
            establish_adjacency=False,
            become_full=False,
            priority_higher=False,
            dead_timer_expired=True,
        )

    # Check if should establish adjacency
    adjacency_ok = should_establish_adjacency(current_state)

    if adjacency_ok:
        higher_prio = has_higher_priority(
            my_priority, neighbor_priority, my_router_id, neighbor_router_id
        )
        return NeighborDecision(
            establish_adjacency=True,
            become_full=False,
            priority_higher=higher_prio,
            dead_timer_expired=False,
        )

    # Check if can reach Full state
    can_be_full = state_allows_full(current_state)

    if can_be_full:
        # Check LSA freshness
        lsa_category = categorize_lsa_age(lsa_age_seconds)
        lsa_ok = lsa_category != LSAAgeCategory.MAX_AGE

        if lsa_ok:
            higher_prio = has_higher_priority(
                my_priority, neighbor_priority, my_router_id, neighbor_router_id
            )
            return NeighborDecision(
                establish_adjacency=False,
                become_full=True,
                priority_higher=higher_prio,
                dead_timer_expired=False,
            )
        else:
            return NeighborDecision(
                establish_adjacency=False,
                become_full=False,
                priority_higher=False,
                dead_timer_expired=False,
            )
    else:
        return NeighborDecision(
            establish_adjacency=False,
            become_full=False,
            priority_higher=False,
            dead_timer_expired=False,
        )
