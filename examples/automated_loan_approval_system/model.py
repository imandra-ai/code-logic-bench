from enum import Enum
from typing import NamedTuple


class LoanType(Enum):
    """Type of loan being applied for."""

    PERSONAL = "personal"
    AUTO = "auto"
    MORTGAGE = "mortgage"
    BUSINESS = "business"


class EmploymentStatus(Enum):
    """Employment status of the applicant."""

    EMPLOYED = "employed"
    SELF_EMPLOYED = "self_employed"
    UNEMPLOYED = "unemployed"


class DecisionClassification(Enum):
    """Classification of the loan decision."""

    AUTO_APPROVED = "auto_approved"
    CONDITIONAL_APPROVAL = "conditional_approval"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    AUTO_REJECTED = "auto_rejected"
    INVALID_APPLICATION = "invalid_application"


class ApprovalDecision(NamedTuple):
    """Result of the loan approval decision."""

    approved: bool
    decision_type: DecisionClassification
    interest_rate: int


def _calculate_risk_score(
    credit_score: int, debt_to_income: int, employment_status: EmploymentStatus
) -> int:
    """Calculate risk score based on credit, DTI, and employment."""
    credit_component = max(0, 800 - credit_score) // 10
    dti_component = max(0, debt_to_income - 30) // 2

    employment_component = {
        EmploymentStatus.UNEMPLOYED: 50,
        EmploymentStatus.SELF_EMPLOYED: 20,
        EmploymentStatus.EMPLOYED: 0,
    }[employment_status]

    return credit_component + dti_component + employment_component


def _classify_risk_level(risk_score: int) -> int:
    """Classify risk score into levels: 0=Low, 1=Medium, 2=High, 3=Extreme."""
    if risk_score <= 20:
        return 0  # Low
    elif risk_score <= 40:
        return 1  # Medium
    elif risk_score <= 70:
        return 2  # High
    else:
        return 3  # Extreme


def _requires_manual_review(
    risk_level: int, loan_amount: int, has_bankruptcy: bool, debt_to_income: int
) -> bool:
    """Check if application requires manual review."""
    return (
        risk_level >= 3 or loan_amount > 500000 or has_bankruptcy or debt_to_income > 45
    )


def _is_valid_application(credit_score: int, debt_to_income: int, age: int) -> bool:
    """Validate application data and check for dead zones."""
    # Dead zone: credit 580-620 with DTI 43-47 and age 72-74
    in_dead_zone = (
        580 <= credit_score <= 620 and 43 <= debt_to_income <= 47 and 72 <= age <= 74
    )

    invalid_data = (
        credit_score < 300
        or credit_score > 850
        or debt_to_income < 0
        or debt_to_income > 100
        or age < 18
        or age > 120
    )

    return not (in_dead_zone or invalid_data)


def _calculate_interest_rate(
    credit_score: int, loan_type: LoanType, risk_level: int
) -> int:
    """Calculate interest rate based on credit, loan type, and risk."""
    # Grade premium based on credit score
    if credit_score >= 750:
        grade_premium = 0
    elif credit_score >= 700:
        grade_premium = 100
    elif credit_score >= 650:
        grade_premium = 250
    else:
        grade_premium = 500

    # Type premium based on loan type
    type_premium = {
        LoanType.MORTGAGE: 0,
        LoanType.AUTO: 50,
        LoanType.PERSONAL: 300,
        LoanType.BUSINESS: 200,
    }[loan_type]

    risk_adjustment = risk_level * 50
    rate = 300 + grade_premium + type_premium + risk_adjustment

    return min(3600, max(300, rate))


def determine_loan_approval(
    loan_type: LoanType,
    loan_amount: int,
    credit_score: int,
    debt_to_income: int,
    age: int,
    employment_status: EmploymentStatus,
) -> ApprovalDecision:
    """
    Determine loan approval based on applicant's financial profile.

    Evaluates loan applications using credit score, debt-to-income ratio,
    employment status, and other factors. Returns a decision with approval
    status, classification, and interest rate.

    Args:
        loan_type: Type of loan being applied for
        loan_amount: Amount of loan requested
        credit_score: Applicant's credit score (300-850)
        debt_to_income: Debt-to-income ratio percentage (0-100)
        age: Applicant's age
        employment_status: Current employment status

    Returns:
        ApprovalDecision with approval status, decision type, and interest rate
    """
    # Hardcoded values for simplicity
    has_bankruptcy = False
    monthly_income = 5000

    # Check validity first
    if not _is_valid_application(credit_score, debt_to_income, age):
        return ApprovalDecision(
            approved=False,
            decision_type=DecisionClassification.INVALID_APPLICATION,
            interest_rate=0,
        )

    # Calculate risk
    risk_score = _calculate_risk_score(credit_score, debt_to_income, employment_status)
    risk_level = _classify_risk_level(risk_score)

    # Check if manual review required
    if _requires_manual_review(risk_level, loan_amount, has_bankruptcy, debt_to_income):
        return ApprovalDecision(
            approved=False,
            decision_type=DecisionClassification.MANUAL_REVIEW_REQUIRED,
            interest_rate=0,
        )

    # Check basic requirements
    loan_type_limits = {
        LoanType.PERSONAL: 100000,
        LoanType.AUTO: 150000,
        LoanType.MORTGAGE: 2000000,
        LoanType.BUSINESS: 1000000,
    }

    meets_requirements = (
        18 <= age <= 75
        and credit_score >= 500
        and monthly_income >= 2000
        and debt_to_income <= 50
        and loan_amount > 0
        and loan_amount <= loan_type_limits[loan_type]
    )

    if not meets_requirements:
        return ApprovalDecision(
            approved=False,
            decision_type=DecisionClassification.AUTO_REJECTED,
            interest_rate=0,
        )

    # Calculate interest rate
    interest_rate = _calculate_interest_rate(credit_score, loan_type, risk_level)

    # Check if conditional approval needed
    needs_conditions = (
        debt_to_income > 40 or employment_status == EmploymentStatus.SELF_EMPLOYED
    )

    if needs_conditions:
        return ApprovalDecision(
            approved=True,
            decision_type=DecisionClassification.CONDITIONAL_APPROVAL,
            interest_rate=interest_rate,
        )
    else:
        return ApprovalDecision(
            approved=True,
            decision_type=DecisionClassification.AUTO_APPROVED,
            interest_rate=interest_rate,
        )
