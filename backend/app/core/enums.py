from enum import StrEnum


class UserRole(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    MAINTENANCE_MANAGER = "MAINTENANCE_MANAGER"
    TECHNICIAN = "TECHNICIAN"
    VIEWER = "VIEWER"


class AssetStatus(StrEnum):
    ACTIVE = "ACTIVE"
    STOPPED = "STOPPED"
    MAINTENANCE = "MAINTENANCE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class Criticality(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Priority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING = "WAITING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class WorkOrderType(StrEnum):
    CORRECTIVE = "CORRECTIVE"
    PREVENTIVE = "PREVENTIVE"
    INSPECTION = "INSPECTION"
    IMPROVEMENT = "IMPROVEMENT"


class WorkOrderStatus(StrEnum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class FrequencyType(StrEnum):
    DAYS = "DAYS"
    WEEKS = "WEEKS"
    MONTHS = "MONTHS"
    YEARS = "YEARS"


class InventoryMovementType(StrEnum):
    RECEIPT = "RECEIPT"
    CONSUMPTION = "CONSUMPTION"
    ADJUSTMENT = "ADJUSTMENT"


class DocumentType(StrEnum):
    MANUAL = "MANUAL"
    ELECTRICAL_SCHEMATIC = "ELECTRICAL_SCHEMATIC"
    PROCEDURE = "PROCEDURE"
    SAFETY = "SAFETY"
    OTHER = "OTHER"


class DocumentIndexStatus(StrEnum):
    PENDING = "PENDING"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"
    UNSUPPORTED = "UNSUPPORTED"
