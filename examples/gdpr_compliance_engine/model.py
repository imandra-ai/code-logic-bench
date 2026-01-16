from enum import Enum
from dataclasses import dataclass
from typing import NamedTuple


class DataCategory(Enum):
    """Categories of personal data under GDPR."""

    PERSONAL = "Personal"
    SENSITIVE = "Sensitive"
    HEALTH = "Health"


class LawfulBasis(Enum):
    """Legal basis for data processing under GDPR."""

    CONSENT = "Consent"
    LEGAL_OBLIGATION = "LegalObligation"
    LEGITIMATE_INTERESTS = "LegitimateInterests"


class ConsentQuality(Enum):
    """Quality level of consent obtained."""

    EXPLICIT = "Explicit"
    IMPLICIT = "Implicit"
    WITHDRAWN = "Withdrawn"


class TransferDestination(Enum):
    """Destination for cross-border data transfers."""

    EU_COUNTRY = "EUCountry"
    THIRD_COUNTRY = "ThirdCountry"


class RiskLevel(Enum):
    """Risk level assessment for data processing."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class ComplianceDecision(NamedTuple):
    """GDPR compliance decision output."""

    processing_allowed: bool
    requires_pia: bool
    requires_dpo_review: bool
    consent_sufficient: bool
    transfer_allowed: bool
    risk_assessment: RiskLevel


def _requires_explicit_consent(data_cat: DataCategory) -> bool:
    """Check if data category requires explicit consent."""
    return data_cat in (DataCategory.SENSITIVE, DataCategory.HEALTH)


def _consent_meets_requirements(
    data_cat: DataCategory, consent_quality: ConsentQuality, consent_age: int
) -> bool:
    """Validate consent quality and age against data category requirements."""
    explicit_needed = _requires_explicit_consent(data_cat)
    age_valid = consent_age <= 24  # months

    if consent_quality == ConsentQuality.WITHDRAWN:
        return False
    elif consent_quality == ConsentQuality.IMPLICIT:
        return not explicit_needed and age_valid
    else:  # EXPLICIT
        return age_valid


def _evaluate_lawful_basis(
    basis: LawfulBasis,
    data_cat: DataCategory,
    consent_quality: ConsentQuality,
    consent_age: int,
    automated_decision: bool,
) -> bool:
    """
    Evaluate if lawful basis is sufficient for processing.

    Implements override pattern: LegalObligation generally allows processing
    except for sensitive data with automated decision-making.
    """
    if basis == LawfulBasis.LEGAL_OBLIGATION:
        # Override: Legal obligation allows processing...
        base_allowed = True
        # ...EXCEPT when sensitive data + automated decision making
        sensitive_automated = (
            _requires_explicit_consent(data_cat) and automated_decision
        )
        return not sensitive_automated and base_allowed

    elif basis == LawfulBasis.CONSENT:
        return _consent_meets_requirements(data_cat, consent_quality, consent_age)

    else:  # LEGITIMATE_INTERESTS
        # Legitimate interests doesn't work for sensitive data
        return not _requires_explicit_consent(data_cat)


def _check_transfer_compliance(
    destination: TransferDestination,
    data_cat: DataCategory,
    transfer_safeguard_score: int,
) -> bool:
    """
    Validate cross-border transfer compliance.

    Implements multiplexer pattern: threshold varies by data category.
    """
    if destination == TransferDestination.EU_COUNTRY:
        return True

    # ThirdCountry - threshold varies by data category
    required_score = {
        DataCategory.PERSONAL: 60,
        DataCategory.SENSITIVE: 80,
        DataCategory.HEALTH: 90,
    }[data_cat]

    return transfer_safeguard_score >= required_score


def _assess_risk(
    data_cat: DataCategory,
    automated_decision: bool,
    profiling: bool,
    cross_border: bool,
) -> RiskLevel:
    """
    Assess risk level based on multiple factors.

    Implements quorum pattern: counts risk factors to determine level.
    """
    risk_factors = sum(
        [
            _requires_explicit_consent(data_cat),
            automated_decision,
            profiling,
            cross_border,
        ]
    )

    if risk_factors >= 4:
        return RiskLevel.CRITICAL
    elif risk_factors >= 3:
        return RiskLevel.HIGH
    elif risk_factors >= 2:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW


def _is_valid_safeguard_score(score: int, consent_age: int) -> bool:
    """
    Validate safeguard score and consent age combination.

    Rejects dead zone: scores 58-62 with consent age 23-25 months are ambiguous.
    """
    # Scores in 58-62 range with consent age 23-25 months are ambiguous
    in_dead_zone = 58 <= score <= 62 and 23 <= consent_age <= 25

    # Also invalid if score is extreme
    extreme_score = score < 0 or score > 100

    return not (in_dead_zone or extreme_score)


def determine_gdpr_compliance(
    data_cat: DataCategory,
    lawful_basis: LawfulBasis,
    consent_quality: ConsentQuality,
    consent_age: int,
    automated_decision: bool,
    profiling: bool,
    destination: TransferDestination,
    transfer_safeguard_score: int,
) -> ComplianceDecision:
    """
    Determine GDPR compliance for data processing activities.

    Evaluates lawful basis sufficiency, consent validity with time decay,
    cross-border transfer requirements, and risk assessment to produce
    a comprehensive compliance decision.

    Args:
        data_cat: Category of personal data being processed
        lawful_basis: Legal basis claimed for processing
        consent_quality: Quality level of consent obtained
        consent_age: Age of consent in months
        automated_decision: Whether automated decision-making is involved
        profiling: Whether profiling is performed
        destination: Destination for data transfer
        transfer_safeguard_score: Score representing transfer safeguards (0-100)

    Returns:
        ComplianceDecision with processing allowance and requirements
    """
    # Check validity first
    valid = _is_valid_safeguard_score(transfer_safeguard_score, consent_age)

    if not valid:
        return ComplianceDecision(
            processing_allowed=False,
            requires_pia=False,
            requires_dpo_review=False,
            consent_sufficient=False,
            transfer_allowed=False,
            risk_assessment=RiskLevel.LOW,
        )

    # Evaluate lawful basis with override logic
    basis_ok = _evaluate_lawful_basis(
        lawful_basis, data_cat, consent_quality, consent_age, automated_decision
    )

    # Check transfer compliance (multiplexer)
    transfer_ok = _check_transfer_compliance(
        destination, data_cat, transfer_safeguard_score
    )

    # Assess risk (quorum)
    risk = _assess_risk(
        data_cat,
        automated_decision,
        profiling,
        destination == TransferDestination.THIRD_COUNTRY,
    )

    # Determine requirements
    needs_pia = risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    needs_dpo = risk == RiskLevel.CRITICAL

    final_allowed = basis_ok and transfer_ok

    return ComplianceDecision(
        processing_allowed=final_allowed,
        requires_pia=needs_pia,
        requires_dpo_review=needs_dpo,
        consent_sufficient=_consent_meets_requirements(
            data_cat, consent_quality, consent_age
        ),
        transfer_allowed=transfer_ok,
        risk_assessment=risk,
    )
