from enum import Enum, auto


class OriginType(Enum):
    """BGP route origin type."""

    IGP = auto()
    EGP = auto()
    INCOMPLETE = auto()


class MedMode(Enum):
    """MED (Multi-Exit Discriminator) comparison mode."""

    ALWAYS_COMPARE = auto()
    ONLY_SAME_AS = auto()
    NEVER_COMPARE = auto()


class SelectionResult(Enum):
    """Route selection result."""

    ROUTE1 = auto()
    ROUTE2 = auto()
    TIE = auto()


def _origin_to_int(origin: OriginType) -> int:
    """Convert origin type to integer for comparison (lower is better)."""
    return {
        OriginType.IGP: 0,
        OriginType.EGP: 1,
        OriginType.INCOMPLETE: 2,
    }[origin]


def _emergency_overrides(emergency: bool, med: int) -> bool:
    """Emergency flag trumps local_pref, BUT only if MED < 100."""
    return emergency and med < 100


def _should_compare_med(mode: MedMode, same_as: bool) -> bool:
    """Whether to compare MED depends on mode and if same AS."""
    if mode == MedMode.ALWAYS_COMPARE:
        return True
    elif mode == MedMode.ONLY_SAME_AS:
        return same_as
    else:  # MedMode.NEVER_COMPARE
        return False


def _in_dead_zone(as_path: int, med: int) -> bool:
    """AS paths 250-254 with MED 95-105 are ambiguous."""
    return 250 <= as_path <= 254 and 95 <= med <= 105


def select_best_route(
    r1_local_pref: int,
    r1_as_path: int,
    r1_origin: OriginType,
    r1_med: int,
    r1_emergency: bool,
    r2_local_pref: int,
    r2_as_path: int,
    r2_origin: OriginType,
    r2_med: int,
    r2_emergency: bool,
    same_as: bool,
    med_mode: MedMode,
) -> SelectionResult:
    """
    BGP route selection logic that determines which of two routes should be preferred.

    Implements the standard BGP best path selection algorithm with:
    - Local preference (higher wins)
    - AS path length (shorter wins)
    - Origin type (IGP > EGP > Incomplete)
    - MED comparison (depends on mode)

    Incorporates:
    - Emergency override (trumps local_pref if MED < 100)
    - MED comparison mode multiplexing
    - AS path dead zones (250-254 with MED 95-105 are invalid)
    """
    # Check dead zones first - routes in dead zone are invalid
    r1_dead = _in_dead_zone(r1_as_path, r1_med)
    r2_dead = _in_dead_zone(r2_as_path, r2_med)

    # Check basic viability
    r1_valid = r1_local_pref >= 50 and r1_as_path <= 255 and not r1_dead
    r2_valid = r2_local_pref >= 50 and r2_as_path <= 255 and not r2_dead

    if not r1_valid and not r2_valid:
        return SelectionResult.TIE
    elif not r1_valid:
        return SelectionResult.ROUTE2
    elif not r2_valid:
        return SelectionResult.ROUTE1

    # Both valid - apply BGP selection algorithm

    # Emergency override checked FIRST
    r1_emerg = _emergency_overrides(r1_emergency, r1_med)
    r2_emerg = _emergency_overrides(r2_emergency, r2_med)

    if r1_emerg and not r2_emerg:
        return SelectionResult.ROUTE1
    elif r2_emerg and not r1_emerg:
        return SelectionResult.ROUTE2

    # Step 1: Local preference (higher wins)
    if r1_local_pref > r2_local_pref:
        return SelectionResult.ROUTE1
    elif r2_local_pref > r1_local_pref:
        return SelectionResult.ROUTE2

    # Step 2: AS path length (shorter wins)
    if r1_as_path < r2_as_path:
        return SelectionResult.ROUTE1
    elif r2_as_path < r1_as_path:
        return SelectionResult.ROUTE2

    # Step 3: Origin type (IGP > EGP > Incomplete)
    r1_o = _origin_to_int(r1_origin)
    r2_o = _origin_to_int(r2_origin)

    if r1_o < r2_o:
        return SelectionResult.ROUTE1
    elif r2_o < r1_o:
        return SelectionResult.ROUTE2

    # Step 4: MED (depends on mode)
    compare_med = _should_compare_med(med_mode, same_as)

    if compare_med:
        if r1_med < r2_med:
            return SelectionResult.ROUTE1
        elif r2_med < r1_med:
            return SelectionResult.ROUTE2

    return SelectionResult.TIE
