"""
NAAC Criterion 4: Infrastructure and Learning Resources - Pydantic Schemas

This module defines request/response schemas for Criterion 4 API endpoints.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ==================== ENUMS ====================

class InfrastructureType(str, Enum):
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


class EquipmentStatus(str, Enum):
    WORKING = "working"
    UNDER_MAINTENANCE = "under_maintenance"
    NEEDS_REPAIR = "needs_repair"
    CONDEMNED = "condemned"
    NOT_IN_USE = "not_in_use"


class LicenseType(str, Enum):
    PERPETUAL = "perpetual"
    SUBSCRIPTION = "subscription"
    ACADEMIC = "academic"
    OPEN_SOURCE = "open_source"
    TRIAL = "trial"
    FREEWARE = "freeware"


class ResourceType(str, Enum):
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


class MaintenanceType(str, Enum):
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    EMERGENCY = "emergency"
    UPGRADE = "upgrade"
    ANNUAL = "annual"


# ==================== INFRASTRUCTURE SCHEMAS ====================

class InfrastructureCreate(BaseModel):
    """Schema for creating infrastructure"""
    name: str = Field(..., min_length=1, max_length=255)
    infra_type: InfrastructureType
    description: Optional[str] = None
    location: Optional[str] = None
    room_number: Optional[str] = None
    department: Optional[str] = None
    is_shared: bool = False
    area_sqft: Optional[float] = Field(None, gt=0)
    seating_capacity: Optional[int] = Field(None, gt=0)
    establishment_date: Optional[date] = None
    has_projector: bool = False
    has_smart_board: bool = False
    has_ac: bool = False
    has_wifi: bool = False
    has_cctv: bool = False
    ict_tools: Optional[List[str]] = None


class InfrastructureUpdate(BaseModel):
    """Schema for updating infrastructure"""
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    is_shared: Optional[bool] = None
    area_sqft: Optional[float] = None
    seating_capacity: Optional[int] = None
    status: Optional[EquipmentStatus] = None
    is_active: Optional[bool] = None
    last_renovation_date: Optional[date] = None
    has_projector: Optional[bool] = None
    has_smart_board: Optional[bool] = None
    has_ac: Optional[bool] = None
    has_wifi: Optional[bool] = None
    has_cctv: Optional[bool] = None
    ict_tools: Optional[List[str]] = None


class InfrastructureResponse(BaseModel):
    """Schema for infrastructure response"""
    id: str
    name: str
    infra_type: str
    description: Optional[str]
    location: Optional[str]
    room_number: Optional[str]
    department: Optional[str]
    is_shared: bool
    area_sqft: Optional[float]
    seating_capacity: Optional[int]
    status: str
    is_active: bool
    establishment_date: Optional[date]
    last_renovation_date: Optional[date]
    has_projector: bool
    has_smart_board: bool
    has_ac: bool
    has_wifi: bool
    has_cctv: bool
    ict_tools: Optional[List[str]]
    photo_path: Optional[str]
    layout_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class InfrastructureListResponse(BaseModel):
    """Schema for paginated infrastructure list"""
    items: List[InfrastructureResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None
    by_department: Optional[Dict[str, int]] = None


# ==================== LAB EQUIPMENT SCHEMAS ====================

class LabEquipmentCreate(BaseModel):
    """Schema for creating lab equipment"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    asset_id: Optional[str] = None
    lab_id: Optional[str] = None
    department: str = Field(..., min_length=1, max_length=255)
    purchase_date: Optional[date] = None
    purchase_cost: Optional[float] = Field(None, ge=0)
    vendor_name: Optional[str] = None
    warranty_expiry: Optional[date] = None
    invoice_number: Optional[str] = None
    quantity: int = Field(default=1, ge=1)


class LabEquipmentUpdate(BaseModel):
    """Schema for updating lab equipment"""
    name: Optional[str] = None
    description: Optional[str] = None
    lab_id: Optional[str] = None
    status: Optional[EquipmentStatus] = None
    quantity: Optional[int] = None
    current_value: Optional[float] = None
    last_maintenance_date: Optional[date] = None
    next_maintenance_date: Optional[date] = None
    amc_vendor: Optional[str] = None
    amc_expiry: Optional[date] = None


class LabEquipmentResponse(BaseModel):
    """Schema for lab equipment response"""
    id: str
    name: str
    description: Optional[str]
    make: Optional[str]
    model: Optional[str]
    serial_number: Optional[str]
    asset_id: Optional[str]
    lab_id: Optional[str]
    department: str
    purchase_date: Optional[date]
    purchase_cost: Optional[float]
    vendor_name: Optional[str]
    warranty_expiry: Optional[date]
    invoice_number: Optional[str]
    status: str
    quantity: int
    current_value: Optional[float]
    last_maintenance_date: Optional[date]
    next_maintenance_date: Optional[date]
    amc_vendor: Optional[str]
    amc_expiry: Optional[date]
    photo_path: Optional[str]
    invoice_path: Optional[str]
    manual_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class LabEquipmentListResponse(BaseModel):
    """Schema for paginated lab equipment list"""
    items: List[LabEquipmentResponse]
    total: int
    page: int
    page_size: int
    total_value: Optional[float] = None
    by_status: Optional[Dict[str, int]] = None


# ==================== SOFTWARE LICENSE SCHEMAS ====================

class SoftwareLicenseCreate(BaseModel):
    """Schema for creating software license"""
    software_name: str = Field(..., min_length=1, max_length=255)
    version: Optional[str] = None
    vendor: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    license_type: LicenseType
    license_key: Optional[str] = None
    license_count: int = Field(default=1, ge=1)
    department: Optional[str] = None
    is_institution_wide: bool = False
    purchase_date: Optional[date] = None
    activation_date: Optional[date] = None
    expiry_date: Optional[date] = None
    purchase_cost: Optional[float] = Field(None, ge=0)
    annual_cost: Optional[float] = Field(None, ge=0)


class SoftwareLicenseUpdate(BaseModel):
    """Schema for updating software license"""
    version: Optional[str] = None
    license_count: Optional[int] = None
    users_assigned: Optional[int] = None
    expiry_date: Optional[date] = None
    annual_cost: Optional[float] = None
    installation_count: Optional[int] = None
    labs_installed: Optional[List[str]] = None
    is_active: Optional[bool] = None


class SoftwareLicenseResponse(BaseModel):
    """Schema for software license response"""
    id: str
    software_name: str
    version: Optional[str]
    vendor: Optional[str]
    description: Optional[str]
    category: Optional[str]
    license_type: str
    license_key: Optional[str]
    license_count: int
    users_assigned: int
    department: Optional[str]
    is_institution_wide: bool
    purchase_date: Optional[date]
    activation_date: Optional[date]
    expiry_date: Optional[date]
    purchase_cost: Optional[float]
    annual_cost: Optional[float]
    installation_count: int
    labs_installed: Optional[List[str]]
    license_document_path: Optional[str]
    invoice_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class SoftwareLicenseListResponse(BaseModel):
    """Schema for paginated software license list"""
    items: List[SoftwareLicenseResponse]
    total: int
    page: int
    page_size: int
    total_cost: Optional[float] = None
    by_type: Optional[Dict[str, int]] = None


# ==================== LIBRARY RESOURCE SCHEMAS ====================

class LibraryResourceCreate(BaseModel):
    """Schema for creating library resource"""
    title: str = Field(..., min_length=1, max_length=500)
    resource_type: ResourceType
    author: Optional[str] = None
    publisher: Optional[str] = None
    edition: Optional[str] = None
    year_of_publication: Optional[int] = Field(None, ge=1900, le=2100)
    isbn: Optional[str] = None
    issn: Optional[str] = None
    accession_number: Optional[str] = None
    call_number: Optional[str] = None
    subject: Optional[str] = None
    department: Optional[str] = None
    keywords: Optional[List[str]] = None
    copies_total: int = Field(default=1, ge=1)
    location: Optional[str] = None
    pages: Optional[int] = Field(None, ge=1)
    is_digital: bool = False
    digital_url: Optional[str] = None
    database_name: Optional[str] = None
    access_type: Optional[str] = None
    purchase_cost: Optional[float] = Field(None, ge=0)
    subscription_cost: Optional[float] = Field(None, ge=0)
    subscription_period: Optional[str] = None
    acquired_date: Optional[date] = None


class LibraryResourceUpdate(BaseModel):
    """Schema for updating library resource"""
    copies_available: Optional[int] = None
    copies_total: Optional[int] = None
    location: Optional[str] = None
    is_available: Optional[bool] = None
    is_active: Optional[bool] = None
    digital_url: Optional[str] = None
    times_borrowed: Optional[int] = None
    times_accessed: Optional[int] = None


class LibraryResourceResponse(BaseModel):
    """Schema for library resource response"""
    id: str
    title: str
    resource_type: str
    author: Optional[str]
    publisher: Optional[str]
    edition: Optional[str]
    year_of_publication: Optional[int]
    isbn: Optional[str]
    issn: Optional[str]
    accession_number: Optional[str]
    call_number: Optional[str]
    subject: Optional[str]
    department: Optional[str]
    keywords: Optional[List[str]]
    copies_available: int
    copies_total: int
    location: Optional[str]
    pages: Optional[int]
    is_digital: bool
    digital_url: Optional[str]
    database_name: Optional[str]
    access_type: Optional[str]
    purchase_cost: Optional[float]
    subscription_cost: Optional[float]
    subscription_period: Optional[str]
    times_borrowed: int
    times_accessed: int
    is_available: bool
    is_active: bool
    acquired_date: Optional[date]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class LibraryResourceListResponse(BaseModel):
    """Schema for paginated library resource list"""
    items: List[LibraryResourceResponse]
    total: int
    page: int
    page_size: int
    by_type: Optional[Dict[str, int]] = None
    total_books: Optional[int] = None
    total_ebooks: Optional[int] = None
    total_journals: Optional[int] = None


# ==================== LAB UTILIZATION SCHEMAS ====================

class LabUtilizationCreate(BaseModel):
    """Schema for creating lab utilization record"""
    lab_id: str
    lab_name: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=255)
    date: date
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    duration_hours: Optional[float] = Field(None, gt=0)
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    semester: Optional[int] = Field(None, ge=1, le=8)
    batch: Optional[str] = None
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    faculty_name: Optional[str] = None
    faculty_email: Optional[str] = None
    students_count: int = Field(default=0, ge=0)
    student_list: Optional[List[Dict[str, str]]] = None
    purpose: Optional[str] = None
    topics_covered: Optional[List[str]] = None
    experiments_conducted: Optional[List[str]] = None
    equipment_used: Optional[List[str]] = None
    software_used: Optional[List[str]] = None
    remarks: Optional[str] = None


class LabUtilizationUpdate(BaseModel):
    """Schema for updating lab utilization record"""
    students_count: Optional[int] = None
    student_list: Optional[List[Dict[str, str]]] = None
    topics_covered: Optional[List[str]] = None
    experiments_conducted: Optional[List[str]] = None
    equipment_used: Optional[List[str]] = None
    software_used: Optional[List[str]] = None
    remarks: Optional[str] = None


class LabUtilizationResponse(BaseModel):
    """Schema for lab utilization response"""
    id: str
    lab_id: str
    lab_name: str
    department: str
    date: date
    start_time: str
    end_time: str
    duration_hours: Optional[float]
    course_code: Optional[str]
    course_name: Optional[str]
    semester: Optional[int]
    batch: Optional[str]
    academic_year: str
    faculty_name: Optional[str]
    faculty_email: Optional[str]
    students_count: int
    student_list: Optional[List[Dict[str, str]]]
    purpose: Optional[str]
    topics_covered: Optional[List[str]]
    experiments_conducted: Optional[List[str]]
    equipment_used: Optional[List[str]]
    software_used: Optional[List[str]]
    remarks: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class LabUtilizationListResponse(BaseModel):
    """Schema for paginated lab utilization list"""
    items: List[LabUtilizationResponse]
    total: int
    page: int
    page_size: int
    total_hours: Optional[float] = None
    by_lab: Optional[Dict[str, float]] = None
    by_department: Optional[Dict[str, float]] = None


# ==================== MAINTENANCE RECORD SCHEMAS ====================

class MaintenanceRecordCreate(BaseModel):
    """Schema for creating maintenance record"""
    asset_type: str = Field(..., pattern=r"^(infrastructure|equipment|software)$")
    asset_id: str
    asset_name: str = Field(..., min_length=1, max_length=255)
    department: Optional[str] = None
    maintenance_type: MaintenanceType
    description: Optional[str] = None
    issue_reported: Optional[str] = None
    request_date: Optional[date] = None
    maintenance_date: date
    technician_name: Optional[str] = None
    vendor_name: Optional[str] = None
    cost: Optional[float] = Field(None, ge=0)
    parts_replaced: Optional[List[Dict[str, Any]]] = None


class MaintenanceRecordUpdate(BaseModel):
    """Schema for updating maintenance record"""
    action_taken: Optional[str] = None
    completion_date: Optional[date] = None
    is_completed: Optional[bool] = None
    next_maintenance_due: Optional[date] = None
    cost: Optional[float] = None
    parts_replaced: Optional[List[Dict[str, Any]]] = None


class MaintenanceRecordResponse(BaseModel):
    """Schema for maintenance record response"""
    id: str
    asset_type: str
    asset_id: str
    asset_name: str
    department: Optional[str]
    maintenance_type: str
    description: Optional[str]
    issue_reported: Optional[str]
    action_taken: Optional[str]
    request_date: Optional[date]
    maintenance_date: date
    completion_date: Optional[date]
    reported_by: Optional[str]
    technician_name: Optional[str]
    vendor_name: Optional[str]
    cost: Optional[float]
    parts_replaced: Optional[List[Dict[str, Any]]]
    is_completed: bool
    next_maintenance_due: Optional[date]
    work_order_path: Optional[str]
    invoice_path: Optional[str]
    photo_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class MaintenanceRecordListResponse(BaseModel):
    """Schema for paginated maintenance record list"""
    items: List[MaintenanceRecordResponse]
    total: int
    page: int
    page_size: int
    total_cost: Optional[float] = None
    by_type: Optional[Dict[str, int]] = None
    pending_count: Optional[int] = None


# ==================== E-RESOURCE ACCESS SCHEMAS ====================

class EResourceAccessCreate(BaseModel):
    """Schema for creating e-resource access record"""
    resource_id: Optional[str] = None
    resource_name: str = Field(..., min_length=1, max_length=500)
    resource_type: Optional[str] = None
    database_name: Optional[str] = None
    access_date: date
    access_time: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1)
    user_type: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    department: Optional[str] = None
    ip_address: Optional[str] = None
    access_mode: Optional[str] = None
    pages_viewed: Optional[int] = Field(None, ge=0)
    downloaded: bool = False
    academic_year: Optional[str] = None


class EResourceAccessResponse(BaseModel):
    """Schema for e-resource access response"""
    id: str
    resource_id: Optional[str]
    resource_name: str
    resource_type: Optional[str]
    database_name: Optional[str]
    access_date: date
    access_time: Optional[str]
    duration_minutes: Optional[int]
    user_type: Optional[str]
    user_id: Optional[str]
    user_name: Optional[str]
    department: Optional[str]
    ip_address: Optional[str]
    access_mode: Optional[str]
    pages_viewed: Optional[int]
    downloaded: bool
    academic_year: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EResourceAccessListResponse(BaseModel):
    """Schema for paginated e-resource access list"""
    items: List[EResourceAccessResponse]
    total: int
    page: int
    page_size: int
    by_resource: Optional[Dict[str, int]] = None
    by_department: Optional[Dict[str, int]] = None


# ==================== DASHBOARD & REPORT SCHEMAS ====================

class Criterion4DashboardStats(BaseModel):
    """Dashboard statistics for Criterion 4"""
    # Key Indicator 4.1: Physical Infrastructure
    total_classrooms: int
    smart_classrooms: int
    total_labs: int
    computer_labs: int
    seminar_halls: int
    total_area_sqft: float
    ict_enabled_percentage: float

    # Key Indicator 4.2: IT Infrastructure
    total_computers: int
    student_computer_ratio: float
    total_software_licenses: int
    active_licenses: int
    internet_bandwidth_mbps: Optional[float]

    # Key Indicator 4.3: Library Resources
    total_books: int
    total_ebooks: int
    total_journals: int
    total_ejournals: int
    library_automation: bool
    remote_access_available: bool

    # Key Indicator 4.4: Maintenance
    total_maintenance_cost: float
    preventive_maintenance_count: int
    assets_under_amc: int
    pending_maintenance: int

    # Lab Utilization
    average_lab_utilization_percentage: float
    lab_utilization_by_department: Dict[str, float]

    # Overall readiness
    completion_percentage: float
    pending_items: List[Dict[str, Any]]


class Criterion4ReportRequest(BaseModel):
    """Request schema for generating Criterion 4 report"""
    institution_name: str = Field(..., min_length=1)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    department: Optional[str] = None
    include_sections: Optional[List[str]] = None
    format: str = Field(default="docx", pattern=r"^(docx|pdf)$")
    include_analytics: bool = True


class Criterion4ReportResponse(BaseModel):
    """Response schema for generated report"""
    success: bool
    report_path: Optional[str] = None
    report_url: Optional[str] = None
    sections_included: List[str]
    generated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
