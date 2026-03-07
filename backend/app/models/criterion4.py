"""
NAAC Criterion 4: Infrastructure & Learning Resources - Database Models

This module defines database models for managing NAAC Criterion 4 requirements:
- Physical Infrastructure (Classrooms, Labs, Amenities)
- IT Infrastructure (Smart Classrooms, Computing Resources)
- Library Resources (Books, E-Resources, Digital Library)
- Lab Utilization Tracking
- Asset Management
- Software Licenses
"""

from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, JSON, Boolean, Index, Float, Date
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


# ==================== ENUMS ====================

class InfrastructureType(str, enum.Enum):
    """Types of physical infrastructure"""
    CLASSROOM = "classroom"
    SMART_CLASSROOM = "smart_classroom"
    LABORATORY = "laboratory"
    COMPUTER_LAB = "computer_lab"
    WORKSHOP = "workshop"
    LIBRARY = "library"
    SEMINAR_HALL = "seminar_hall"
    AUDITORIUM = "auditorium"
    SPORTS_FACILITY = "sports_facility"
    HOSTEL = "hostel"
    CANTEEN = "canteen"
    MEDICAL_CENTER = "medical_center"
    PARKING = "parking"
    OTHER = "other"


class EquipmentStatus(str, enum.Enum):
    """Status of equipment/asset"""
    WORKING = "working"
    UNDER_MAINTENANCE = "under_maintenance"
    NEEDS_REPAIR = "needs_repair"
    CONDEMNED = "condemned"
    NOT_IN_USE = "not_in_use"


class LicenseType(str, enum.Enum):
    """Software license types"""
    PERPETUAL = "perpetual"
    SUBSCRIPTION = "subscription"
    ACADEMIC = "academic"
    OPEN_SOURCE = "open_source"
    TRIAL = "trial"
    FREEWARE = "freeware"


class ResourceType(str, enum.Enum):
    """Library resource types"""
    BOOK = "book"
    E_BOOK = "e_book"
    JOURNAL = "journal"
    E_JOURNAL = "e_journal"
    MAGAZINE = "magazine"
    NEWSPAPER = "newspaper"
    CD_DVD = "cd_dvd"
    PROJECT_REPORT = "project_report"
    THESIS = "thesis"
    QUESTION_PAPER = "question_paper"
    OTHER = "other"


class MaintenanceType(str, enum.Enum):
    """Maintenance types"""
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    EMERGENCY = "emergency"
    UPGRADE = "upgrade"
    ANNUAL = "annual"


# ==================== MODELS ====================

class Infrastructure(Base):
    """
    Physical Infrastructure Records.
    Key Indicator 4.1: Physical Facilities
    """
    __tablename__ = "infrastructure"

    __table_args__ = (
        Index('ix_infrastructure_type', 'infra_type'),
        Index('ix_infrastructure_department', 'department'),
        Index('ix_infrastructure_status', 'status'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Basic details
    name = Column(String(255), nullable=False)
    infra_type = Column(SQLEnum(InfrastructureType), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)  # Building, Floor, Room No
    room_number = Column(String(50), nullable=True)

    # Department
    department = Column(String(255), nullable=True)  # Null for common facilities
    is_shared = Column(Boolean, default=False)

    # Capacity
    area_sqft = Column(Float, nullable=True)
    seating_capacity = Column(Integer, nullable=True)

    # Status
    status = Column(SQLEnum(EquipmentStatus), default=EquipmentStatus.WORKING)
    is_active = Column(Boolean, default=True)
    establishment_date = Column(Date, nullable=True)
    last_renovation_date = Column(Date, nullable=True)

    # Smart classroom features
    has_projector = Column(Boolean, default=False)
    has_smart_board = Column(Boolean, default=False)
    has_ac = Column(Boolean, default=False)
    has_wifi = Column(Boolean, default=False)
    has_cctv = Column(Boolean, default=False)
    ict_tools = Column(JSON, nullable=True)  # ["projector", "smart_board", ...]

    # Documents
    photo_path = Column(String(500), nullable=True)
    layout_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Infrastructure {self.name}>"


class LabEquipment(Base):
    """
    Laboratory Equipment and Assets.
    Key Indicator 4.1: Physical Facilities
    """
    __tablename__ = "lab_equipment"

    __table_args__ = (
        Index('ix_lab_equipment_lab_id', 'lab_id'),
        Index('ix_lab_equipment_status', 'status'),
        Index('ix_lab_equipment_department', 'department'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Equipment details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    make = Column(String(255), nullable=True)  # Manufacturer
    model = Column(String(255), nullable=True)
    serial_number = Column(String(100), nullable=True)
    asset_id = Column(String(100), nullable=True)  # Internal asset ID

    # Location
    lab_id = Column(GUID, ForeignKey("infrastructure.id", ondelete="SET NULL"), nullable=True)
    department = Column(String(255), nullable=False)

    # Purchase details
    purchase_date = Column(Date, nullable=True)
    purchase_cost = Column(Float, nullable=True)
    vendor_name = Column(String(255), nullable=True)
    warranty_expiry = Column(Date, nullable=True)
    invoice_number = Column(String(100), nullable=True)

    # Status
    status = Column(SQLEnum(EquipmentStatus), default=EquipmentStatus.WORKING)
    quantity = Column(Integer, default=1)
    current_value = Column(Float, nullable=True)  # Depreciated value

    # Maintenance
    last_maintenance_date = Column(Date, nullable=True)
    next_maintenance_date = Column(Date, nullable=True)
    amc_vendor = Column(String(255), nullable=True)
    amc_expiry = Column(Date, nullable=True)

    # Documents
    photo_path = Column(String(500), nullable=True)
    invoice_path = Column(String(500), nullable=True)
    manual_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<LabEquipment {self.name}>"


class SoftwareLicense(Base):
    """
    Software Licenses Management.
    Key Indicator 4.2: IT Infrastructure
    """
    __tablename__ = "software_licenses"

    __table_args__ = (
        Index('ix_software_licenses_type', 'license_type'),
        Index('ix_software_licenses_department', 'department'),
        Index('ix_software_licenses_expiry', 'expiry_date'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Software details
    software_name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=True)
    vendor = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # IDE, CAD, Simulation, etc.

    # License details
    license_type = Column(SQLEnum(LicenseType), nullable=False)
    license_key = Column(String(500), nullable=True)
    license_count = Column(Integer, default=1)  # Number of licenses
    users_assigned = Column(Integer, default=0)

    # Department
    department = Column(String(255), nullable=True)  # Null for institution-wide
    is_institution_wide = Column(Boolean, default=False)

    # Dates
    purchase_date = Column(Date, nullable=True)
    activation_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)

    # Cost
    purchase_cost = Column(Float, nullable=True)
    annual_cost = Column(Float, nullable=True)

    # Usage
    installation_count = Column(Integer, default=0)
    labs_installed = Column(JSON, nullable=True)  # List of lab IDs

    # Documents
    license_document_path = Column(String(500), nullable=True)
    invoice_path = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SoftwareLicense {self.software_name}>"


class LibraryResource(Base):
    """
    Library Resources (Books, E-Resources).
    Key Indicator 4.2: Library as a Learning Resource
    """
    __tablename__ = "library_resources"

    __table_args__ = (
        Index('ix_library_resources_type', 'resource_type'),
        Index('ix_library_resources_department', 'department'),
        Index('ix_library_resources_accession', 'accession_number'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Resource details
    title = Column(String(500), nullable=False)
    resource_type = Column(SQLEnum(ResourceType), nullable=False)
    author = Column(String(500), nullable=True)
    publisher = Column(String(255), nullable=True)
    edition = Column(String(50), nullable=True)
    year_of_publication = Column(Integer, nullable=True)
    isbn = Column(String(50), nullable=True)
    issn = Column(String(50), nullable=True)

    # Library cataloging
    accession_number = Column(String(100), nullable=True, unique=True)
    call_number = Column(String(100), nullable=True)
    subject = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    keywords = Column(JSON, nullable=True)

    # Physical details
    copies_available = Column(Integer, default=1)
    copies_total = Column(Integer, default=1)
    location = Column(String(100), nullable=True)  # Shelf number
    pages = Column(Integer, nullable=True)

    # E-Resource details
    is_digital = Column(Boolean, default=False)
    digital_url = Column(String(500), nullable=True)
    database_name = Column(String(255), nullable=True)  # For e-journals
    access_type = Column(String(50), nullable=True)  # IP-based, Login, Open

    # Cost
    purchase_cost = Column(Float, nullable=True)
    subscription_cost = Column(Float, nullable=True)  # For journals
    subscription_period = Column(String(50), nullable=True)

    # Usage stats
    times_borrowed = Column(Integer, default=0)
    times_accessed = Column(Integer, default=0)  # For e-resources

    # Status
    is_available = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    # Timestamps
    acquired_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<LibraryResource {self.title[:50]}>"


class LabUtilization(Base):
    """
    Lab Utilization Logs.
    Key Indicator 4.1: Physical Facilities Utilization
    """
    __tablename__ = "lab_utilization"

    __table_args__ = (
        Index('ix_lab_utilization_lab_id', 'lab_id'),
        Index('ix_lab_utilization_date', 'date'),
        Index('ix_lab_utilization_department', 'department'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Lab reference
    lab_id = Column(GUID, ForeignKey("infrastructure.id", ondelete="CASCADE"), nullable=False)
    lab_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)

    # Session details
    date = Column(Date, nullable=False)
    start_time = Column(String(10), nullable=False)  # HH:MM format
    end_time = Column(String(10), nullable=False)
    duration_hours = Column(Float, nullable=True)

    # Academic details
    course_code = Column(String(50), nullable=True)
    course_name = Column(String(255), nullable=True)
    semester = Column(Integer, nullable=True)
    batch = Column(String(50), nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Faculty and students
    faculty_name = Column(String(255), nullable=True)
    faculty_email = Column(String(255), nullable=True)
    students_count = Column(Integer, default=0)
    student_list = Column(JSON, nullable=True)

    # Purpose
    purpose = Column(String(255), nullable=True)  # Regular class, Extra lab, Project work
    topics_covered = Column(JSON, nullable=True)
    experiments_conducted = Column(JSON, nullable=True)

    # Equipment used
    equipment_used = Column(JSON, nullable=True)  # List of equipment IDs
    software_used = Column(JSON, nullable=True)  # List of software names

    # Remarks
    remarks = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<LabUtilization {self.lab_name} - {self.date}>"


class MaintenanceRecord(Base):
    """
    Maintenance Records for Infrastructure and Equipment.
    Key Indicator 4.4: Maintenance of Infrastructure
    """
    __tablename__ = "maintenance_records"

    __table_args__ = (
        Index('ix_maintenance_records_type', 'maintenance_type'),
        Index('ix_maintenance_records_date', 'maintenance_date'),
        Index('ix_maintenance_records_asset_type', 'asset_type'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Asset reference
    asset_type = Column(String(50), nullable=False)  # infrastructure, equipment, software
    asset_id = Column(GUID, nullable=False)
    asset_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=True)

    # Maintenance details
    maintenance_type = Column(SQLEnum(MaintenanceType), nullable=False)
    description = Column(Text, nullable=True)
    issue_reported = Column(Text, nullable=True)
    action_taken = Column(Text, nullable=True)

    # Dates
    request_date = Column(Date, nullable=True)
    maintenance_date = Column(Date, nullable=False)
    completion_date = Column(Date, nullable=True)

    # Personnel
    reported_by = Column(String(255), nullable=True)
    technician_name = Column(String(255), nullable=True)
    vendor_name = Column(String(255), nullable=True)

    # Cost
    cost = Column(Float, nullable=True)
    parts_replaced = Column(JSON, nullable=True)

    # Status
    is_completed = Column(Boolean, default=False)
    next_maintenance_due = Column(Date, nullable=True)

    # Documents
    work_order_path = Column(String(500), nullable=True)
    invoice_path = Column(String(500), nullable=True)
    photo_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MaintenanceRecord {self.asset_name} - {self.maintenance_date}>"


class EResourceAccess(Base):
    """
    E-Resource Access Logs.
    Key Indicator 4.2: Library as a Learning Resource
    """
    __tablename__ = "e_resource_access"

    __table_args__ = (
        Index('ix_e_resource_access_resource_id', 'resource_id'),
        Index('ix_e_resource_access_date', 'access_date'),
        Index('ix_e_resource_access_department', 'department'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Resource reference
    resource_id = Column(GUID, ForeignKey("library_resources.id", ondelete="CASCADE"), nullable=True)
    resource_name = Column(String(500), nullable=False)
    resource_type = Column(String(50), nullable=True)
    database_name = Column(String(255), nullable=True)

    # Access details
    access_date = Column(Date, nullable=False)
    access_time = Column(String(10), nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    # User details
    user_type = Column(String(50), nullable=True)  # student, faculty, staff
    user_id = Column(String(50), nullable=True)
    user_name = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)

    # Session details
    ip_address = Column(String(50), nullable=True)
    access_mode = Column(String(50), nullable=True)  # on-campus, remote
    pages_viewed = Column(Integer, nullable=True)
    downloaded = Column(Boolean, default=False)

    # Academic year
    academic_year = Column(String(20), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<EResourceAccess {self.resource_name} - {self.access_date}>"
