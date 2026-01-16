from dataclasses import dataclass
from enum import Enum, auto


class VitalCategory(Enum):
    """Vital sign category classification."""

    CRITICAL_LOW = auto()
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL_HIGH = auto()


class PainLevel(Enum):
    """Patient pain level classification."""

    NO_PAIN = auto()
    MILD = auto()
    MODERATE = auto()
    SEVERE = auto()
    EXCRUCIATING = auto()


class AgeCategory(Enum):
    """Patient age group classification."""

    INFANT = auto()
    CHILD = auto()
    ADULT = auto()
    ELDERLY = auto()
    VERY_ELDERLY = auto()


class ArrivalMode(Enum):
    """Patient arrival mode."""

    AMBULATORY = auto()
    WHEELCHAIR = auto()
    STRETCHER = auto()
    AMBULANCE = auto()
    HELICOPTER = auto()


class ResourceLevel(Enum):
    """Predicted resource needs."""

    NO_RESOURCES = auto()
    SINGLE_RESOURCE = auto()
    MULTIPLE_RESOURCES = auto()
    COMPLEX_RESOURCES = auto()


class ESICategory(Enum):
    """Emergency Severity Index level."""

    ESI_1 = auto()
    ESI_2 = auto()
    ESI_3 = auto()
    ESI_4 = auto()
    ESI_5 = auto()


@dataclass
class TriageDecision:
    """Triage decision output with ESI level and associated metadata."""

    esi_level: ESICategory
    immediate_intervention: bool
    high_risk_situation: bool
    resource_prediction: ResourceLevel
    upgrade_from_initial: bool


def has_critical_vital(
    bp: VitalCategory, hr: VitalCategory, resp: VitalCategory, o2: VitalCategory
) -> bool:
    """Check if any vital sign is in critical range - ESI_1 indicator."""
    critical_values = {VitalCategory.CRITICAL_LOW, VitalCategory.CRITICAL_HIGH}
    return any(vital in critical_values for vital in [bp, hr, resp, o2])


def count_abnormal_vitals(
    bp: VitalCategory, hr: VitalCategory, resp: VitalCategory, o2: VitalCategory
) -> int:
    """Count number of abnormal vital signs."""
    return sum(1 for vital in [bp, hr, resp, o2] if vital != VitalCategory.NORMAL)


def check_high_risk_quorum(
    pain: PainLevel, age: AgeCategory, arrival: ArrivalMode, abnormal_count: int
) -> bool:
    """
    Quorum-based high-risk detection: requires 2 of 4 conditions.

    Conditions:
    - Severe/excruciating pain
    - Infant or very elderly
    - Ambulance/helicopter arrival
    - 2+ abnormal vitals
    """
    c1 = pain in {PainLevel.SEVERE, PainLevel.EXCRUCIATING}
    c2 = age in {AgeCategory.INFANT, AgeCategory.VERY_ELDERLY}
    c3 = arrival in {ArrivalMode.AMBULANCE, ArrivalMode.HELICOPTER}
    c4 = abnormal_count >= 2

    count = sum([c1, c2, c3, c4])
    return count >= 2


def is_in_triage_dead_zone(
    bp: VitalCategory, hr: VitalCategory, pain: PainLevel, age: AgeCategory
) -> bool:
    """
    Dead zone: certain combinations are ambiguous.

    One borderline vital + moderate pain + non-extreme age = ambiguous.
    """
    one_borderline = (
        bp in {VitalCategory.LOW, VitalCategory.HIGH} and hr == VitalCategory.NORMAL
    ) or (bp == VitalCategory.NORMAL and hr in {VitalCategory.LOW, VitalCategory.HIGH})
    moderate_pain = pain == PainLevel.MODERATE
    non_extreme_age = age in {AgeCategory.CHILD, AgeCategory.ADULT}

    return one_borderline and moderate_pain and non_extreme_age


def predict_resources(
    esi_level: ESICategory, pain: PainLevel, arrival: ArrivalMode
) -> ResourceLevel:
    """Predict resource needs based on ESI level and presentation."""
    if esi_level == ESICategory.ESI_1:
        return ResourceLevel.COMPLEX_RESOURCES
    elif esi_level == ESICategory.ESI_2:
        if arrival in {ArrivalMode.AMBULANCE, ArrivalMode.HELICOPTER}:
            return ResourceLevel.MULTIPLE_RESOURCES
        elif pain == PainLevel.SEVERE:
            return ResourceLevel.MULTIPLE_RESOURCES
        else:
            return ResourceLevel.SINGLE_RESOURCE
    elif esi_level == ESICategory.ESI_3:
        return ResourceLevel.MULTIPLE_RESOURCES
    elif esi_level == ESICategory.ESI_4:
        return ResourceLevel.SINGLE_RESOURCE
    else:  # ESI_5
        return ResourceLevel.NO_RESOURCES


def apply_arrival_upgrade(
    base_esi: ESICategory, arrival: ArrivalMode, abnormal_count: int
) -> ESICategory:
    """
    Helicopter arrival upgrades ESI level EXCEPT when vitals are stable.
    """
    stable_vitals = abnormal_count == 0

    if arrival == ArrivalMode.HELICOPTER and not stable_vitals:
        upgrade_map = {
            ESICategory.ESI_5: ESICategory.ESI_4,
            ESICategory.ESI_4: ESICategory.ESI_3,
            ESICategory.ESI_3: ESICategory.ESI_2,
        }
        return upgrade_map.get(base_esi, base_esi)

    return base_esi


def determine_esi(
    bp: VitalCategory,
    hr: VitalCategory,
    resp: VitalCategory,
    o2: VitalCategory,
    pain: PainLevel,
    age: AgeCategory,
    arrival: ArrivalMode,
) -> TriageDecision:
    """
    Core ESI determination with upgrade tracking.

    Emergency triage system using ESI (Emergency Severity Index) to classify
    patients based on vital signs, pain level, age, and arrival mode.
    """
    # Check dead zone first
    in_dead_zone = is_in_triage_dead_zone(bp, hr, pain, age)

    if in_dead_zone:
        return TriageDecision(
            esi_level=ESICategory.ESI_3,
            immediate_intervention=False,
            high_risk_situation=False,
            resource_prediction=ResourceLevel.MULTIPLE_RESOURCES,
            upgrade_from_initial=False,
        )

    # Check critical vitals - ESI_1
    has_critical = has_critical_vital(bp, hr, resp, o2)

    if has_critical:
        return TriageDecision(
            esi_level=ESICategory.ESI_1,
            immediate_intervention=True,
            high_risk_situation=True,
            resource_prediction=ResourceLevel.COMPLEX_RESOURCES,
            upgrade_from_initial=False,
        )

    # Count abnormal vitals
    abnormal_count = count_abnormal_vitals(bp, hr, resp, o2)

    # Check high-risk quorum
    high_risk = check_high_risk_quorum(pain, age, arrival, abnormal_count)

    # Initial ESI based on abnormal count
    if abnormal_count >= 3:
        initial_esi = ESICategory.ESI_2
    elif abnormal_count == 2:
        initial_esi = ESICategory.ESI_3
    elif abnormal_count == 1:
        initial_esi = ESICategory.ESI_4
    else:
        initial_esi = ESICategory.ESI_5

    # Upgrade to ESI_2 if high-risk quorum met
    if high_risk and initial_esi != ESICategory.ESI_2:
        esi_after_risk = ESICategory.ESI_2
    else:
        esi_after_risk = initial_esi

    # Apply arrival mode upgrade
    final_esi = apply_arrival_upgrade(esi_after_risk, arrival, abnormal_count)

    upgraded = final_esi != initial_esi
    resources = predict_resources(final_esi, pain, arrival)

    return TriageDecision(
        esi_level=final_esi,
        immediate_intervention=False,
        high_risk_situation=final_esi in {ESICategory.ESI_2, ESICategory.ESI_3},
        resource_prediction=resources,
        upgrade_from_initial=upgraded,
    )
