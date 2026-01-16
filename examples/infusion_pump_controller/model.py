from enum import Enum
from dataclasses import dataclass


class DrugClass(Enum):
    """Drug classification for infusion."""

    OPIOID = "Opioid"
    VASOPRESSOR = "Vasopressor"
    FLUID = "Fluid"


class PatientRisk(Enum):
    """Patient risk level."""

    LOW_RISK = "LowRisk"
    MEDIUM_RISK = "MediumRisk"
    HIGH_RISK = "HighRisk"


class HardwareStatus(Enum):
    """Hardware status of the infusion pump."""

    NORMAL = "Normal"
    DEGRADED = "Degraded"
    CRITICAL = "Critical"


@dataclass
class InfusionDecision:
    """Decision outcome for infusion safety check."""

    allow_infusion: bool
    require_double_check: bool
    trigger_alarm: bool
    adjusted_max_rate: int  # ml/hour
    safety_level: PatientRisk


def base_max_rate(drug: DrugClass) -> int:
    """Drug-specific base maximum rates (ml/hour)."""
    rates = {
        DrugClass.OPIOID: 20,
        DrugClass.VASOPRESSOR: 30,
        DrugClass.FLUID: 500,
    }
    return rates[drug]


def base_min_rate(drug: DrugClass) -> int:
    """Drug-specific base minimum rates (ml/hour)."""
    rates = {
        DrugClass.OPIOID: 1,
        DrugClass.VASOPRESSOR: 1,
        DrugClass.FLUID: 10,
    }
    return rates[drug]


def is_critical_drug(drug: DrugClass) -> bool:
    """Check if drug is classified as critical."""
    return drug in (DrugClass.OPIOID, DrugClass.VASOPRESSOR)


def adjust_max_rate_for_patient(
    drug: DrugClass, patient_risk: PatientRisk, patient_weight: int
) -> int:
    """
    Adjust maximum rate based on patient parameters using multiplexer pattern.

    Different drug classes have different weight-adjustment formulas.
    """
    base = base_max_rate(drug)

    # Weight adjustment multiplier based on drug class
    if drug == DrugClass.OPIOID:
        if patient_weight < 50:
            weight_factor = 60  # 60% for lightweight patients
        elif patient_weight > 90:
            weight_factor = 120  # 120% for heavy patients
        else:
            weight_factor = 100
    elif drug == DrugClass.VASOPRESSOR:
        if patient_weight < 60:
            weight_factor = 70
        elif patient_weight > 85:
            weight_factor = 110
        else:
            weight_factor = 100
    else:  # Fluid
        weight_factor = 100  # Fluid rates don't vary by weight

    # Risk adjustment
    risk_factors = {
        PatientRisk.LOW_RISK: 100,
        PatientRisk.MEDIUM_RISK: 80,
        PatientRisk.HIGH_RISK: 60,
    }
    risk_factor = risk_factors[patient_risk]

    # Compute adjusted rate
    return (base * weight_factor * risk_factor) // 10000


def evaluate_hardware_safety(
    hardware: HardwareStatus,
    requested_rate: int,
    drug: DrugClass,
    patient_risk: PatientRisk,
) -> bool:
    """
    Evaluate hardware safety with override pattern.

    Degraded hardware restricts high rates BUT critical drugs override
    this restriction for high-risk patients.
    """
    if hardware == HardwareStatus.NORMAL:
        return True

    if hardware == HardwareStatus.DEGRADED:
        # Degraded hardware restricts high rates...
        rate_ok = requested_rate <= 50
        # ...BUT critical drugs override this restriction if patient is HighRisk
        critical_override = (
            is_critical_drug(drug) and patient_risk == PatientRisk.HIGH_RISK
        )
        return True if critical_override else rate_ok

    if hardware == HardwareStatus.CRITICAL:
        # Critical hardware: only allow low rates for critical drugs
        return is_critical_drug(drug) and requested_rate <= 10

    return False


def is_valid_configuration(
    requested_rate: int, patient_weight: int, battery_level: int
) -> bool:
    """
    Check for dead zones and invalid configurations.

    Certain combinations are ambiguous and should be rejected.
    """
    # Rates in 48-52 range with weight 69-71 and battery 19-21% are ambiguous
    in_dead_zone = (
        48 <= requested_rate <= 52
        and 69 <= patient_weight <= 71
        and 19 <= battery_level <= 21
    )

    battery_too_low = battery_level < 10
    rate_invalid = requested_rate < 0 or requested_rate > 1000

    return not (in_dead_zone or battery_too_low or rate_invalid)


def check_alarm_conditions(
    drug: DrugClass,
    patient_risk: PatientRisk,
    hardware: HardwareStatus,
    requested_rate: int,
    adjusted_max: int,
) -> bool:
    """
    Quorum-based alarm triggering requiring 2-out-of-4 risk factors.
    """
    c1 = is_critical_drug(drug)
    c2 = patient_risk == PatientRisk.HIGH_RISK
    c3 = hardware == HardwareStatus.CRITICAL
    c4 = requested_rate > adjusted_max

    alarm_factors = sum([c1, c2, c3, c4])

    return alarm_factors >= 2


def determine_infusion_safety(
    drug: DrugClass,
    patient_risk: PatientRisk,
    patient_weight: int,
    hardware: HardwareStatus,
    requested_rate: int,
    battery_level: int,
) -> InfusionDecision:
    """
    Core decision function for infusion pump safety controller.

    Determines whether to allow medication infusions based on drug class,
    patient risk level, patient weight, hardware status, and requested
    infusion rate.
    """
    # Check validity first
    valid = is_valid_configuration(requested_rate, patient_weight, battery_level)

    if not valid:
        return InfusionDecision(
            allow_infusion=False,
            require_double_check=False,
            trigger_alarm=False,
            adjusted_max_rate=0,
            safety_level=PatientRisk.LOW_RISK,
        )

    # Calculate adjusted max rate (multiplexer)
    max_rate = adjust_max_rate_for_patient(drug, patient_risk, patient_weight)
    min_rate = base_min_rate(drug)

    # Check hardware safety (override)
    hardware_ok = evaluate_hardware_safety(hardware, requested_rate, drug, patient_risk)

    # Check rate bounds
    rate_in_bounds = min_rate <= requested_rate <= max_rate

    # Determine if double check needed
    needs_double_check = is_critical_drug(drug) and (
        patient_risk == PatientRisk.HIGH_RISK
        or hardware == HardwareStatus.DEGRADED
        or requested_rate > (max_rate * 80) // 100
    )

    # Check alarm conditions (quorum)
    alarm = check_alarm_conditions(
        drug, patient_risk, hardware, requested_rate, max_rate
    )

    final_allowed = hardware_ok and rate_in_bounds

    return InfusionDecision(
        allow_infusion=final_allowed,
        require_double_check=needs_double_check,
        trigger_alarm=alarm,
        adjusted_max_rate=max_rate,
        safety_level=patient_risk,
    )
