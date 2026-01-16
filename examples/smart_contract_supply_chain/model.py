from enum import Enum
from dataclasses import dataclass


class Jurisdiction(Enum):
    """Represents the jurisdiction where the contract is executed."""

    US = "US"
    EU = "EU"
    APAC = "APAC"


class ProductCategory(Enum):
    """Represents the category of product in the supply chain."""

    ELECTRONICS = "Electronics"
    PHARMACEUTICALS = "Pharmaceuticals"
    FOOD = "Food"
    CHEMICALS = "Chemicals"


class QualityStandard(Enum):
    """Represents quality certification standards."""

    ISO9001 = "ISO9001"
    FDA = "FDA"
    CE = "CE"
    HACCP = "HACCP"


class PartyRole(Enum):
    """Represents the role of a party in the supply chain."""

    SUPPLIER = "Supplier"
    BUYER = "Buyer"
    LOGISTICS = "Logistics"


@dataclass
class ContractDecision:
    """Represents the outcome of contract validation."""

    approved: bool
    requires_audit: bool
    penalty_applies: bool


def party_certified_for_product(role: PartyRole, category: ProductCategory) -> bool:
    """Check if party is certified to handle the product category."""
    if role == PartyRole.SUPPLIER:
        return True
    elif role == PartyRole.BUYER:
        return True
    elif role == PartyRole.LOGISTICS:
        return category in (ProductCategory.FOOD, ProductCategory.ELECTRONICS)
    return False


def requires_standard(category: ProductCategory, standard: QualityStandard) -> bool:
    """Check if a product category requires a specific quality standard."""
    requirements = {
        ProductCategory.PHARMACEUTICALS: {QualityStandard.FDA, QualityStandard.ISO9001},
        ProductCategory.FOOD: {QualityStandard.HACCP, QualityStandard.ISO9001},
        ProductCategory.ELECTRONICS: {QualityStandard.CE, QualityStandard.ISO9001},
        ProductCategory.CHEMICALS: {QualityStandard.ISO9001},
    }
    return standard in requirements.get(category, set())


def jurisdiction_permits(jurisdiction: Jurisdiction, category: ProductCategory) -> bool:
    """Check if jurisdiction allows the product category."""
    if jurisdiction == Jurisdiction.US:
        return True
    elif jurisdiction == Jurisdiction.EU:
        return category != ProductCategory.CHEMICALS  # EU restricts Chemicals
    elif jurisdiction == Jurisdiction.APAC:
        return True
    return False


def needs_mandatory_audit(category: ProductCategory) -> bool:
    """Check if product category requires mandatory audit."""
    return category == ProductCategory.PHARMACEUTICALS


def determine_contract_validity(
    role: PartyRole,
    category: ProductCategory,
    jurisdiction: Jurisdiction,
    has_iso9001: bool,
    has_fda: bool,
    has_ce: bool,
    has_haccp: bool,
    reputation_score: int,
    payment_advance_pct: int,
) -> ContractDecision:
    """
    Determine contract validity based on supply chain parameters.

    Validates contracts based on jurisdiction permissions, party certifications,
    quality standards, reputation, and payment terms. Pharmaceuticals have
    mandatory audit requirements and strict FDA compliance.

    Args:
        role: Role of the party in the supply chain
        category: Product category being contracted
        jurisdiction: Legal jurisdiction of the contract
        has_iso9001: Whether party has ISO9001 certification
        has_fda: Whether party has FDA approval
        has_ce: Whether party has CE certification
        has_haccp: Whether party has HACCP certification
        reputation_score: Reputation score (0-100)
        payment_advance_pct: Payment advance percentage

    Returns:
        ContractDecision with approval status, audit requirement, and penalty flag
    """
    # Check jurisdiction permits category first
    jurisdiction_ok = jurisdiction_permits(jurisdiction, category)

    if not jurisdiction_ok:
        return ContractDecision(
            approved=False, requires_audit=False, penalty_applies=False
        )

    # Check party certification
    party_ok = party_certified_for_product(role, category)

    if not party_ok:
        return ContractDecision(
            approved=False, requires_audit=False, penalty_applies=False
        )

    # Check quality standards
    iso_ok = (
        has_iso9001 if requires_standard(category, QualityStandard.ISO9001) else True
    )
    fda_ok = has_fda if requires_standard(category, QualityStandard.FDA) else True
    ce_ok = has_ce if requires_standard(category, QualityStandard.CE) else True
    haccp_ok = has_haccp if requires_standard(category, QualityStandard.HACCP) else True

    standards_ok = iso_ok and fda_ok and ce_ok and haccp_ok

    if not standards_ok:
        return ContractDecision(
            approved=False,
            requires_audit=False,
            penalty_applies=True,  # Penalty for missing standards
        )

    # Check reputation
    reputation_ok = reputation_score >= 70

    if not reputation_ok:
        return ContractDecision(
            approved=False,
            requires_audit=True,  # Low reputation needs audit
            penalty_applies=False,
        )

    # Check payment terms
    payment_ok = payment_advance_pct >= 30

    if not payment_ok:
        return ContractDecision(
            approved=False,
            requires_audit=False,
            penalty_applies=True,  # Penalty for risky payment terms
        )

    # Mandatory audit for critical categories
    needs_audit = needs_mandatory_audit(category)

    return ContractDecision(
        approved=True, requires_audit=needs_audit, penalty_applies=False
    )
