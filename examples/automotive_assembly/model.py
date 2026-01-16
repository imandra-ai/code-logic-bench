from enum import Enum
from dataclasses import dataclass
from typing import Literal


class VehicleType(Enum):
    """Type of vehicle being processed."""

    SEDAN = "Sedan"
    SUV = "SUV"
    TRUCK = "Truck"


class StationId(Enum):
    """Assembly line station identifier."""

    BODY_WELDING = "BodyWelding"
    ENGINE_INSTALL = "EngineInstall"
    PAINT_BOOTH = "PaintBooth"
    QUALITY_CONTROL = "QualityControl"


class EquipmentStatus(Enum):
    """Status of station equipment."""

    OPERATIONAL = "Operational"
    MAINTENANCE = "Maintenance"
    FAULTY = "Faulty"


class DecisionClassification(Enum):
    """Classification of the station processing decision."""

    PROCESS_APPROVED = "ProcessApproved"
    EQUIPMENT_DOWN = "EquipmentDown"
    INSUFFICIENT_WORKERS = "InsufficientWorkers"
    EMERGENCY_STOP = "EmergencyStop"
    INVALID_CONFIG = "InvalidConfig"


@dataclass
class StationDecision:
    """Decision on whether a station can process a vehicle."""

    can_process: bool
    processing_time: int
    decision_type: DecisionClassification


def base_processing_time(station: StationId, vehicle_type: VehicleType) -> int:
    """
    Get base processing time for a station and vehicle type combination.

    Args:
        station: The assembly line station
        vehicle_type: The type of vehicle

    Returns:
        Base processing time in minutes
    """
    processing_times = {
        (StationId.BODY_WELDING, VehicleType.SEDAN): 45,
        (StationId.BODY_WELDING, VehicleType.SUV): 60,
        (StationId.BODY_WELDING, VehicleType.TRUCK): 75,
        (StationId.ENGINE_INSTALL, VehicleType.SEDAN): 30,
        (StationId.ENGINE_INSTALL, VehicleType.SUV): 40,
        (StationId.ENGINE_INSTALL, VehicleType.TRUCK): 50,
        (StationId.PAINT_BOOTH, VehicleType.SEDAN): 90,
        (StationId.PAINT_BOOTH, VehicleType.SUV): 110,
        (StationId.PAINT_BOOTH, VehicleType.TRUCK): 130,
    }

    # Quality control has fixed time regardless of vehicle type
    if station == StationId.QUALITY_CONTROL:
        return 20

    return processing_times[(station, vehicle_type)]


def check_emergency_trigger(
    equipment_status: EquipmentStatus, defect_rate: int, safety_violations: int
) -> bool:
    """
    Check if emergency stop conditions are met.

    Args:
        equipment_status: Current equipment status
        defect_rate: Defect rate percentage
        safety_violations: Number of safety violations

    Returns:
        True if emergency stop is needed
    """
    return (
        equipment_status == EquipmentStatus.FAULTY
        or defect_rate > 15
        or safety_violations > 2
    )


def is_valid_config(maintenance_due: int, worker_count: int) -> bool:
    """
    Check if station configuration is valid.

    Dead zone: maintenance_due 48-52 with worker_count 1-2 is invalid.

    Args:
        maintenance_due: Hours until maintenance is due
        worker_count: Number of workers available

    Returns:
        True if configuration is valid
    """
    # Check for dead zone: maintenance 48-52 with worker_count 1-2
    in_dead_zone = 48 <= maintenance_due <= 52 and 1 <= worker_count <= 2

    # Check for invalid data
    invalid_data = maintenance_due < 0 or worker_count < 0

    return not (in_dead_zone or invalid_data)


def determine_station_processing(
    station_id: StationId,
    vehicle_type: VehicleType,
    equipment_status: EquipmentStatus,
    maintenance_due: int,
    worker_count: int,
    defect_rate: int,
) -> StationDecision:
    """
    Determine whether a station can process vehicles based on operational factors.

    Evaluates equipment status, worker availability, capacity constraints, and
    safety conditions to make a processing decision.

    Args:
        station_id: The assembly line station
        vehicle_type: Type of vehicle to process
        equipment_status: Current equipment status
        maintenance_due: Hours until maintenance is due
        worker_count: Number of workers available
        defect_rate: Defect rate percentage

    Returns:
        StationDecision with processing capability, time, and classification
    """
    # Hardcoded for simplicity as per original model
    safety_violations = 0

    # Check validity first
    valid = is_valid_config(maintenance_due, worker_count)

    if not valid:
        return StationDecision(
            can_process=False,
            processing_time=0,
            decision_type=DecisionClassification.INVALID_CONFIG,
        )

    # Emergency overrides everything
    emergency = check_emergency_trigger(
        equipment_status, defect_rate, safety_violations
    )

    if emergency:
        return StationDecision(
            can_process=False,
            processing_time=0,
            decision_type=DecisionClassification.EMERGENCY_STOP,
        )

    # Check equipment status
    if equipment_status != EquipmentStatus.OPERATIONAL:
        return StationDecision(
            can_process=False,
            processing_time=0,
            decision_type=DecisionClassification.EQUIPMENT_DOWN,
        )

    # Check worker availability
    if worker_count == 0:
        return StationDecision(
            can_process=False,
            processing_time=0,
            decision_type=DecisionClassification.INSUFFICIENT_WORKERS,
        )

    # Can process - calculate time
    base_time = base_processing_time(station_id, vehicle_type)

    # Adjust time based on maintenance schedule
    if maintenance_due <= 10:
        adjusted_time = base_time + (base_time * 20 // 100)
    elif maintenance_due <= 30:
        adjusted_time = base_time + (base_time * 10 // 100)
    else:
        adjusted_time = base_time

    return StationDecision(
        can_process=True,
        processing_time=adjusted_time,
        decision_type=DecisionClassification.PROCESS_APPROVED,
    )
