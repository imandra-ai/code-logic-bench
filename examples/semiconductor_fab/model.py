from enum import Enum
from dataclasses import dataclass


class ProcessStep(Enum):
    """Semiconductor fabrication process steps."""

    PHOTOLITHOGRAPHY = "photolithography"
    ETCHING = "etching"
    DEPOSITION = "deposition"
    ION_IMPLANT = "ion_implant"
    METROLOGY = "metrology"


class ContaminationClass(Enum):
    """Cleanroom contamination classification levels."""

    CLASS1 = 1
    CLASS10 = 10
    CLASS100 = 100
    CLASS1000 = 1000
    CONTAMINATED = 9999


class ToolStatus(Enum):
    """Status of fabrication tool."""

    AVAILABLE = "available"
    PROCESSING = "processing"
    MAINTENANCE = "maintenance"
    FAILED = "failed"


class WaferPriority(Enum):
    """Priority level of wafer processing."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class ProcessDecision:
    """Decision result for wafer processing approval."""

    approved: bool
    decontamination_required: bool
    qualification_needed: bool
    estimated_yield_loss_pct: int


def _contamination_requirement(step: ProcessStep) -> ContaminationClass:
    """Get contamination requirement for a process step."""
    requirements = {
        ProcessStep.PHOTOLITHOGRAPHY: ContaminationClass.CLASS1,  # Most sensitive
        ProcessStep.ION_IMPLANT: ContaminationClass.CLASS10,
        ProcessStep.DEPOSITION: ContaminationClass.CLASS100,
        ProcessStep.METROLOGY: ContaminationClass.CLASS100,
        ProcessStep.ETCHING: ContaminationClass.CLASS1000,  # Least sensitive
    }
    return requirements[step]


def _contamination_acceptable(
    chamber_contamination: ContaminationClass, required_class: ContaminationClass
) -> bool:
    """Check if chamber contamination level is acceptable for required class."""
    if chamber_contamination == ContaminationClass.CONTAMINATED:
        return False

    # Lower contamination class value means cleaner environment
    return chamber_contamination.value <= required_class.value


def _is_tool_qualified(tool_status: ToolStatus, maintenance_cycles: int) -> bool:
    """Determine if tool is qualified based on status and maintenance cycles."""
    if tool_status in (ToolStatus.FAILED, ToolStatus.MAINTENANCE):
        return False
    elif tool_status == ToolStatus.AVAILABLE:
        return maintenance_cycles < 100
    elif tool_status == ToolStatus.PROCESSING:
        return maintenance_cycles < 120  # Some tolerance during processing
    return False


def _temp_limit_for_step(step: ProcessStep) -> int:
    """Get temperature limit for a process step."""
    limits = {
        ProcessStep.PHOTOLITHOGRAPHY: 150,
        ProcessStep.ION_IMPLANT: 800,
        ProcessStep.DEPOSITION: 600,
        ProcessStep.METROLOGY: 100,
        ProcessStep.ETCHING: 400,
    }
    return limits[step]


def _temp_safe_for_step(temperature: int, step: ProcessStep) -> bool:
    """Check if temperature is safe for the process step."""
    return temperature <= _temp_limit_for_step(step)


def _critical_override_contamination(
    priority: WaferPriority,
    required_class: ContaminationClass,
    chamber_contamination: ContaminationClass,
) -> bool:
    """Critical wafers can process in Class10 even if Class1 required."""
    return (
        priority == WaferPriority.CRITICAL
        and required_class == ContaminationClass.CLASS1
        and chamber_contamination == ContaminationClass.CLASS10
    )


def _estimate_yield_loss(
    chamber_contamination: ContaminationClass, required_class: ContaminationClass
) -> int:
    """Estimate yield loss percentage based on contamination mismatch."""
    if chamber_contamination == required_class:
        return 0

    if chamber_contamination == ContaminationClass.CONTAMINATED:
        return 100

    # Yield loss based on contamination level mismatch
    loss_map = {
        (ContaminationClass.CLASS10, ContaminationClass.CLASS1): 5,
        (ContaminationClass.CLASS100, ContaminationClass.CLASS10): 10,
        (ContaminationClass.CLASS100, ContaminationClass.CLASS1): 15,
        (ContaminationClass.CLASS1000, ContaminationClass.CLASS100): 20,
        (ContaminationClass.CLASS1000, ContaminationClass.CLASS10): 30,
        (ContaminationClass.CLASS1000, ContaminationClass.CLASS1): 40,
    }

    return loss_map.get((chamber_contamination, required_class), 25)


def determine_process_approval(
    step: ProcessStep,
    priority: WaferPriority,
    chamber_contamination: ContaminationClass,
    tool_status: ToolStatus,
    maintenance_cycles: int,
    temperature: int,
) -> ProcessDecision:
    """
    Determine whether to approve wafer processing in semiconductor fab cleanroom.

    Evaluates tool qualification, temperature safety, and contamination levels
    to make processing approval decision with yield loss estimation.

    Args:
        step: The fabrication process step
        priority: Wafer priority level
        chamber_contamination: Current chamber contamination class
        tool_status: Current status of the tool
        maintenance_cycles: Number of maintenance cycles completed
        temperature: Current process temperature

    Returns:
        ProcessDecision with approval status and requirements
    """
    # Check tool qualification first
    qualified = _is_tool_qualified(tool_status, maintenance_cycles)

    if not qualified:
        return ProcessDecision(
            approved=False,
            decontamination_required=False,
            qualification_needed=True,
            estimated_yield_loss_pct=0,
        )

    # Check temperature safety
    temp_ok = _temp_safe_for_step(temperature, step)

    if not temp_ok:
        return ProcessDecision(
            approved=False,
            decontamination_required=False,
            qualification_needed=False,
            estimated_yield_loss_pct=0,
        )

    # Check contamination
    required_class = _contamination_requirement(step)
    contam_ok = _contamination_acceptable(chamber_contamination, required_class)

    # Critical override for contamination
    override = _critical_override_contamination(
        priority, required_class, chamber_contamination
    )

    if contam_ok or override:
        # Approve, but may need decontamination after
        needs_decontam = not contam_ok and override
        yield_loss = _estimate_yield_loss(chamber_contamination, required_class)

        return ProcessDecision(
            approved=True,
            decontamination_required=needs_decontam,
            qualification_needed=False,
            estimated_yield_loss_pct=yield_loss,
        )
    else:
        # Contamination too high, need cleaning
        return ProcessDecision(
            approved=False,
            decontamination_required=True,
            qualification_needed=False,
            estimated_yield_loss_pct=0,
        )
