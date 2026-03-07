"""
NAAC/NBA Accreditation API Endpoints - Criteria 4-7 and NBA Support
Extended endpoints for infrastructure, student support, governance, and NBA accreditation.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import logging
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.core.database import get_db

# Criterion 4 Models
from app.models.criterion4 import (
    Infrastructure,
    LabEquipment,
    SoftwareLicense,
    LibraryResource,
    LabUtilization,
    MaintenanceRecord,
    EResourceAccess,
    InfrastructureType as InfrastructureTypeEnum,
    EquipmentStatus as EquipmentStatusEnum,
    LicenseType as LicenseTypeEnum,
    ResourceType as ResourceTypeEnum,
    MaintenanceType as MaintenanceTypeEnum,
)

# Criterion 5 Models
from app.models.criterion5 import (
    Scholarship,
    PlacementRecord,
    CareerCounseling,
    StudentGrievance,
    AlumniRecord,
    StudentMentoring,
    CompetitiveExam,
    ScholarshipType as ScholarshipTypeEnum,
    PlacementStatus as PlacementStatusEnum,
    CompanyType as CompanyTypeEnum,
    GrievanceCategory as GrievanceCategoryEnum,
    GrievanceStatus as GrievanceStatusEnum,
    AlumniStatus as AlumniStatusEnum,
)

# Criterion 6 Models
from app.models.criterion6 import (
    InstitutionalGovernance,
    GovernanceMeeting,
    InstitutionalPolicy,
    IQACActivity,
    FacultyDevelopment,
    FinancialAudit,
    StrategicPlan,
    MeetingType as MeetingTypeEnum,
    PolicyType as PolicyTypeEnum,
    QualityInitiativeType as QualityInitiativeTypeEnum,
    FDPType as FDPTypeEnum,
    AuditType as AuditTypeEnum,
)

# Criterion 7 Models
from app.models.criterion7 import (
    GenderEquityProgram,
    GreenInitiative,
    InclusivityProgram,
    EthicsProgram,
    BestPractice,
    InstitutionalDistinctiveness,
    InstitutionalAward,
    GreenInitiativeType as GreenInitiativeTypeEnum,
    InclusivityType as InclusivityTypeEnum,
    EthicsType as EthicsTypeEnum,
    BestPracticeCategory as BestPracticeCategoryEnum,
    AwardCategory as AwardCategoryEnum,
)

# NBA Models
from app.models.nba import (
    ProgramVisionMission,
    ProgramOutcome,
    CourseOutcome,
    COAttainment,
    POAttainment,
    StudentResultAnalysis,
    NBAContinuousImprovement,
    NBAFacultyContribution,
    NBALabFacility,
    ProgramType as ProgramTypeEnum,
    AttainmentLevel as AttainmentLevelEnum,
    ActionStatus as ActionStatusEnum,
)

# Schemas
from app.schemas.criterion4 import (
    InfrastructureCreate, InfrastructureUpdate, InfrastructureResponse, InfrastructureListResponse,
    LabEquipmentCreate, LabEquipmentUpdate, LabEquipmentResponse, LabEquipmentListResponse,
    SoftwareLicenseCreate, SoftwareLicenseUpdate, SoftwareLicenseResponse, SoftwareLicenseListResponse,
    LibraryResourceCreate, LibraryResourceUpdate, LibraryResourceResponse, LibraryResourceListResponse,
    LabUtilizationCreate, LabUtilizationUpdate, LabUtilizationResponse, LabUtilizationListResponse,
    MaintenanceRecordCreate, MaintenanceRecordUpdate, MaintenanceRecordResponse, MaintenanceRecordListResponse,
    EResourceAccessCreate, EResourceAccessResponse, EResourceAccessListResponse,
    Criterion4DashboardStats, Criterion4ReportRequest, Criterion4ReportResponse,
)
from app.schemas.criterion5 import (
    ScholarshipCreate, ScholarshipUpdate, ScholarshipResponse, ScholarshipListResponse,
    PlacementRecordCreate, PlacementRecordUpdate, PlacementRecordResponse, PlacementListResponse,
    CareerCounselingCreate, CareerCounselingUpdate, CareerCounselingResponse, CareerCounselingListResponse,
    StudentGrievanceCreate, StudentGrievanceUpdate, StudentGrievanceResponse, StudentGrievanceListResponse,
    AlumniRecordCreate, AlumniRecordUpdate, AlumniRecordResponse, AlumniListResponse,
    StudentMentoringCreate, StudentMentoringUpdate, StudentMentoringResponse, StudentMentoringListResponse,
    CompetitiveExamCreate, CompetitiveExamUpdate, CompetitiveExamResponse, CompetitiveExamListResponse,
    Criterion5DashboardStats, Criterion5ReportRequest, Criterion5ReportResponse,
)
from app.schemas.criterion6 import (
    InstitutionalGovernanceCreate, InstitutionalGovernanceUpdate, InstitutionalGovernanceResponse,
    GovernanceMeetingCreate, GovernanceMeetingUpdate, GovernanceMeetingResponse, GovernanceMeetingListResponse,
    InstitutionalPolicyCreate, InstitutionalPolicyUpdate, InstitutionalPolicyResponse, InstitutionalPolicyListResponse,
    IQACActivityCreate, IQACActivityUpdate, IQACActivityResponse, IQACActivityListResponse,
    FacultyDevelopmentCreate, FacultyDevelopmentUpdate, FacultyDevelopmentResponse, FacultyDevelopmentListResponse,
    FinancialAuditCreate, FinancialAuditUpdate, FinancialAuditResponse, FinancialAuditListResponse,
    StrategicPlanCreate, StrategicPlanUpdate, StrategicPlanResponse, StrategicPlanListResponse,
    Criterion6DashboardStats, Criterion6ReportRequest, Criterion6ReportResponse,
)
from app.schemas.criterion7 import (
    GenderEquityProgramCreate, GenderEquityProgramUpdate, GenderEquityProgramResponse, GenderEquityProgramListResponse,
    GreenInitiativeCreate, GreenInitiativeUpdate, GreenInitiativeResponse, GreenInitiativeListResponse,
    InclusivityProgramCreate, InclusivityProgramUpdate, InclusivityProgramResponse, InclusivityProgramListResponse,
    EthicsProgramCreate, EthicsProgramUpdate, EthicsProgramResponse, EthicsProgramListResponse,
    BestPracticeCreate, BestPracticeUpdate, BestPracticeResponse, BestPracticeListResponse,
    InstitutionalDistinctivenessCreate, InstitutionalDistinctivenessUpdate, InstitutionalDistinctivenessResponse, InstitutionalDistinctivenessListResponse,
    InstitutionalAwardCreate, InstitutionalAwardUpdate, InstitutionalAwardResponse, InstitutionalAwardListResponse,
    Criterion7DashboardStats, Criterion7ReportRequest, Criterion7ReportResponse,
)
from app.schemas.nba import (
    ProgramVisionMissionCreate, ProgramVisionMissionUpdate, ProgramVisionMissionResponse, ProgramVisionMissionListResponse,
    ProgramOutcomeCreate, ProgramOutcomeUpdate, ProgramOutcomeResponse, ProgramOutcomeListResponse,
    CourseOutcomeCreate, CourseOutcomeUpdate, CourseOutcomeResponse, CourseOutcomeListResponse,
    COAttainmentCreate, COAttainmentUpdate, COAttainmentResponse, COAttainmentListResponse,
    POAttainmentCreate, POAttainmentUpdate, POAttainmentResponse, POAttainmentListResponse,
    StudentResultAnalysisCreate, StudentResultAnalysisUpdate, StudentResultAnalysisResponse, StudentResultAnalysisListResponse,
    NBAContinuousImprovementCreate, NBAContinuousImprovementUpdate, NBAContinuousImprovementResponse, NBAContinuousImprovementListResponse,
    NBAFacultyContributionCreate, NBAFacultyContributionUpdate, NBAFacultyContributionResponse, NBAFacultyContributionListResponse,
    NBALabFacilityCreate, NBALabFacilityUpdate, NBALabFacilityResponse, NBALabFacilityListResponse,
    NBADashboardStats, NBAReportRequest, NBAReportResponse,
    COPOMatrixCreate, COPOMatrixResponse, AttainmentCalculationRequest, AttainmentCalculationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== CRITERION 4: INFRASTRUCTURE ====================

@router.post("/criterion4/infrastructure", response_model=InfrastructureResponse, tags=["Criterion 4"])
async def create_infrastructure(
    data: InfrastructureCreate,
    db: Session = Depends(get_db)
):
    """Create new infrastructure record"""
    infra = Infrastructure(
        id=str(uuid.uuid4()),
        name=data.name,
        infra_type=InfrastructureTypeEnum(data.infra_type.value),
        description=data.description,
        location=data.location,
        room_number=data.room_number,
        department=data.department,
        is_shared=data.is_shared,
        area_sqft=data.area_sqft,
        seating_capacity=data.seating_capacity,
        establishment_date=data.establishment_date,
        has_projector=data.has_projector,
        has_smart_board=data.has_smart_board,
        has_ac=data.has_ac,
        has_wifi=data.has_wifi,
        has_cctv=data.has_cctv,
        ict_tools=data.ict_tools,
    )
    db.add(infra)
    db.commit()
    db.refresh(infra)
    return InfrastructureResponse.model_validate(infra)


@router.get("/criterion4/infrastructure", response_model=InfrastructureListResponse, tags=["Criterion 4"])
async def list_infrastructure(
    infra_type: Optional[str] = None,
    department: Optional[str] = None,
    is_active: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List infrastructure with filters"""
    query = db.query(Infrastructure).filter(Infrastructure.is_active == is_active)

    if infra_type:
        query = query.filter(Infrastructure.infra_type == InfrastructureTypeEnum(infra_type))
    if department:
        query = query.filter(Infrastructure.department == department)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return InfrastructureListResponse(
        items=[InfrastructureResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/criterion4/infrastructure/{infra_id}", response_model=InfrastructureResponse, tags=["Criterion 4"])
async def get_infrastructure(infra_id: str, db: Session = Depends(get_db)):
    """Get infrastructure by ID"""
    infra = db.query(Infrastructure).filter(Infrastructure.id == infra_id).first()
    if not infra:
        raise HTTPException(status_code=404, detail="Infrastructure not found")
    return InfrastructureResponse.model_validate(infra)


@router.put("/criterion4/infrastructure/{infra_id}", response_model=InfrastructureResponse, tags=["Criterion 4"])
async def update_infrastructure(
    infra_id: str,
    data: InfrastructureUpdate,
    db: Session = Depends(get_db)
):
    """Update infrastructure record"""
    infra = db.query(Infrastructure).filter(Infrastructure.id == infra_id).first()
    if not infra:
        raise HTTPException(status_code=404, detail="Infrastructure not found")

    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        update_data["status"] = EquipmentStatusEnum(update_data["status"].value)

    for key, value in update_data.items():
        setattr(infra, key, value)

    db.commit()
    db.refresh(infra)
    return InfrastructureResponse.model_validate(infra)


@router.delete("/criterion4/infrastructure/{infra_id}", tags=["Criterion 4"])
async def delete_infrastructure(infra_id: str, db: Session = Depends(get_db)):
    """Soft delete infrastructure"""
    infra = db.query(Infrastructure).filter(Infrastructure.id == infra_id).first()
    if not infra:
        raise HTTPException(status_code=404, detail="Infrastructure not found")

    infra.is_active = False
    db.commit()
    return {"message": "Infrastructure deleted successfully"}


# Lab Equipment Endpoints
@router.post("/criterion4/lab-equipment", response_model=LabEquipmentResponse, tags=["Criterion 4"])
async def create_lab_equipment(data: LabEquipmentCreate, db: Session = Depends(get_db)):
    """Create new lab equipment record"""
    equipment = LabEquipment(
        id=str(uuid.uuid4()),
        **data.model_dump()
    )
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return LabEquipmentResponse.model_validate(equipment)


@router.get("/criterion4/lab-equipment", response_model=LabEquipmentListResponse, tags=["Criterion 4"])
async def list_lab_equipment(
    department: Optional[str] = None,
    lab_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List lab equipment with filters"""
    query = db.query(LabEquipment)

    if department:
        query = query.filter(LabEquipment.department == department)
    if lab_id:
        query = query.filter(LabEquipment.lab_id == lab_id)
    if status:
        query = query.filter(LabEquipment.status == EquipmentStatusEnum(status))

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_value = db.query(func.sum(LabEquipment.purchase_cost)).filter(
        LabEquipment.department == department if department else True
    ).scalar() or 0

    return LabEquipmentListResponse(
        items=[LabEquipmentResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_value=total_value
    )


# Software License Endpoints
@router.post("/criterion4/software-licenses", response_model=SoftwareLicenseResponse, tags=["Criterion 4"])
async def create_software_license(data: SoftwareLicenseCreate, db: Session = Depends(get_db)):
    """Create new software license record"""
    license_data = data.model_dump()
    license_data["license_type"] = LicenseTypeEnum(data.license_type.value)
    license_record = SoftwareLicense(id=str(uuid.uuid4()), **license_data)
    db.add(license_record)
    db.commit()
    db.refresh(license_record)
    return SoftwareLicenseResponse.model_validate(license_record)


@router.get("/criterion4/software-licenses", response_model=SoftwareLicenseListResponse, tags=["Criterion 4"])
async def list_software_licenses(
    department: Optional[str] = None,
    license_type: Optional[str] = None,
    is_active: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List software licenses with filters"""
    query = db.query(SoftwareLicense).filter(SoftwareLicense.is_active == is_active)

    if department:
        query = query.filter(SoftwareLicense.department == department)
    if license_type:
        query = query.filter(SoftwareLicense.license_type == LicenseTypeEnum(license_type))

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return SoftwareLicenseListResponse(
        items=[SoftwareLicenseResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )


# Library Resource Endpoints
@router.post("/criterion4/library-resources", response_model=LibraryResourceResponse, tags=["Criterion 4"])
async def create_library_resource(data: LibraryResourceCreate, db: Session = Depends(get_db)):
    """Create new library resource record"""
    resource_data = data.model_dump()
    resource_data["resource_type"] = ResourceTypeEnum(data.resource_type.value)
    resource = LibraryResource(id=str(uuid.uuid4()), **resource_data)
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return LibraryResourceResponse.model_validate(resource)


@router.get("/criterion4/library-resources", response_model=LibraryResourceListResponse, tags=["Criterion 4"])
async def list_library_resources(
    resource_type: Optional[str] = None,
    department: Optional[str] = None,
    is_digital: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List library resources with filters"""
    query = db.query(LibraryResource).filter(LibraryResource.is_active == True)

    if resource_type:
        query = query.filter(LibraryResource.resource_type == ResourceTypeEnum(resource_type))
    if department:
        query = query.filter(LibraryResource.department == department)
    if is_digital is not None:
        query = query.filter(LibraryResource.is_digital == is_digital)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return LibraryResourceListResponse(
        items=[LibraryResourceResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )


# Lab Utilization Endpoints
@router.post("/criterion4/lab-utilization", response_model=LabUtilizationResponse, tags=["Criterion 4"])
async def create_lab_utilization(data: LabUtilizationCreate, db: Session = Depends(get_db)):
    """Create new lab utilization record"""
    utilization = LabUtilization(id=str(uuid.uuid4()), **data.model_dump())
    db.add(utilization)
    db.commit()
    db.refresh(utilization)
    return LabUtilizationResponse.model_validate(utilization)


@router.get("/criterion4/lab-utilization", response_model=LabUtilizationListResponse, tags=["Criterion 4"])
async def list_lab_utilization(
    lab_id: Optional[str] = None,
    department: Optional[str] = None,
    academic_year: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List lab utilization records with filters"""
    query = db.query(LabUtilization)

    if lab_id:
        query = query.filter(LabUtilization.lab_id == lab_id)
    if department:
        query = query.filter(LabUtilization.department == department)
    if academic_year:
        query = query.filter(LabUtilization.academic_year == academic_year)
    if start_date:
        query = query.filter(LabUtilization.date >= start_date)
    if end_date:
        query = query.filter(LabUtilization.date <= end_date)

    total = query.count()
    items = query.order_by(LabUtilization.date.desc()).offset((page - 1) * page_size).limit(page_size).all()
    total_hours = db.query(func.sum(LabUtilization.duration_hours)).filter(
        LabUtilization.department == department if department else True
    ).scalar() or 0

    return LabUtilizationListResponse(
        items=[LabUtilizationResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_hours=total_hours
    )


# Maintenance Record Endpoints
@router.post("/criterion4/maintenance", response_model=MaintenanceRecordResponse, tags=["Criterion 4"])
async def create_maintenance_record(data: MaintenanceRecordCreate, db: Session = Depends(get_db)):
    """Create new maintenance record"""
    record_data = data.model_dump()
    record_data["maintenance_type"] = MaintenanceTypeEnum(data.maintenance_type.value)
    record = MaintenanceRecord(id=str(uuid.uuid4()), **record_data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return MaintenanceRecordResponse.model_validate(record)


@router.get("/criterion4/maintenance", response_model=MaintenanceRecordListResponse, tags=["Criterion 4"])
async def list_maintenance_records(
    asset_type: Optional[str] = None,
    maintenance_type: Optional[str] = None,
    is_completed: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List maintenance records with filters"""
    query = db.query(MaintenanceRecord)

    if asset_type:
        query = query.filter(MaintenanceRecord.asset_type == asset_type)
    if maintenance_type:
        query = query.filter(MaintenanceRecord.maintenance_type == MaintenanceTypeEnum(maintenance_type))
    if is_completed is not None:
        query = query.filter(MaintenanceRecord.is_completed == is_completed)

    total = query.count()
    items = query.order_by(MaintenanceRecord.maintenance_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
    total_cost = db.query(func.sum(MaintenanceRecord.cost)).scalar() or 0
    pending_count = db.query(MaintenanceRecord).filter(MaintenanceRecord.is_completed == False).count()

    return MaintenanceRecordListResponse(
        items=[MaintenanceRecordResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_cost=total_cost,
        pending_count=pending_count
    )


# Criterion 4 Dashboard
@router.get("/criterion4/dashboard", response_model=Criterion4DashboardStats, tags=["Criterion 4"])
async def get_criterion4_dashboard(
    academic_year: Optional[str] = None,
):
    """Get Criterion 4 dashboard statistics"""
    # Return default stats (database queries will be implemented with async patterns later)
    return Criterion4DashboardStats(
        total_classrooms=0,
        smart_classrooms=0,
        total_labs=0,
        computer_labs=0,
        seminar_halls=0,
        total_area_sqft=0,
        ict_enabled_percentage=0,
        total_computers=0,
        student_computer_ratio=0,
        total_software_licenses=0,
        active_licenses=0,
        internet_bandwidth_mbps=None,
        total_books=0,
        total_ebooks=0,
        total_journals=0,
        total_ejournals=0,
        library_automation=True,
        remote_access_available=True,
        total_maintenance_cost=0,
        preventive_maintenance_count=0,
        assets_under_amc=0,
        pending_maintenance=0,
        average_lab_utilization_percentage=0,
        lab_utilization_by_department={},
        completion_percentage=0,
        pending_items=[]
    )


# ==================== CRITERION 5: STUDENT SUPPORT ====================

@router.post("/criterion5/scholarships", response_model=ScholarshipResponse, tags=["Criterion 5"])
async def create_scholarship(data: ScholarshipCreate, db: Session = Depends(get_db)):
    """Create new scholarship record"""
    scholarship_data = data.model_dump()
    scholarship_data["scholarship_type"] = ScholarshipTypeEnum(data.scholarship_type.value)
    scholarship = Scholarship(id=str(uuid.uuid4()), **scholarship_data)
    db.add(scholarship)
    db.commit()
    db.refresh(scholarship)
    return ScholarshipResponse.model_validate(scholarship)


@router.get("/criterion5/scholarships", response_model=ScholarshipListResponse, tags=["Criterion 5"])
async def list_scholarships(
    scholarship_type: Optional[str] = None,
    department: Optional[str] = None,
    academic_year: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List scholarships with filters"""
    query = db.query(Scholarship)

    if scholarship_type:
        query = query.filter(Scholarship.scholarship_type == ScholarshipTypeEnum(scholarship_type))
    if department:
        query = query.filter(Scholarship.department == department)
    if academic_year:
        query = query.filter(Scholarship.academic_year == academic_year)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_amount = db.query(func.sum(Scholarship.amount)).scalar() or 0

    return ScholarshipListResponse(
        items=[ScholarshipResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_amount=total_amount
    )


@router.post("/criterion5/placements", response_model=PlacementRecordResponse, tags=["Criterion 5"])
async def create_placement(data: PlacementRecordCreate, db: Session = Depends(get_db)):
    """Create new placement record"""
    placement_data = data.model_dump()
    placement_data["status"] = PlacementStatusEnum(data.status.value)
    if data.company_type:
        placement_data["company_type"] = CompanyTypeEnum(data.company_type.value)
    placement = PlacementRecord(id=str(uuid.uuid4()), **placement_data)
    db.add(placement)
    db.commit()
    db.refresh(placement)
    return PlacementRecordResponse.model_validate(placement)


@router.get("/criterion5/placements", response_model=PlacementListResponse, tags=["Criterion 5"])
async def list_placements(
    status: Optional[str] = None,
    department: Optional[str] = None,
    batch: Optional[str] = None,
    academic_year: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List placement records with filters"""
    query = db.query(PlacementRecord)

    if status:
        query = query.filter(PlacementRecord.status == PlacementStatusEnum(status))
    if department:
        query = query.filter(PlacementRecord.department == department)
    if batch:
        query = query.filter(PlacementRecord.batch == batch)
    if academic_year:
        query = query.filter(PlacementRecord.academic_year == academic_year)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    placed_count = db.query(PlacementRecord).filter(PlacementRecord.status == PlacementStatusEnum.PLACED).count()
    avg_package = db.query(func.avg(PlacementRecord.package_lpa)).filter(
        PlacementRecord.status == PlacementStatusEnum.PLACED
    ).scalar() or 0
    max_package = db.query(func.max(PlacementRecord.package_lpa)).filter(
        PlacementRecord.status == PlacementStatusEnum.PLACED
    ).scalar() or 0

    return PlacementListResponse(
        items=[PlacementRecordResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        placement_percentage=(placed_count / total * 100) if total > 0 else 0,
        average_package=avg_package,
        highest_package=max_package
    )


@router.post("/criterion5/grievances", response_model=StudentGrievanceResponse, tags=["Criterion 5"])
async def create_grievance(data: StudentGrievanceCreate, db: Session = Depends(get_db)):
    """Create new student grievance"""
    grievance_number = f"GRV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    grievance_data = data.model_dump()
    grievance_data["category"] = GrievanceCategoryEnum(data.category.value)
    grievance = StudentGrievance(
        id=str(uuid.uuid4()),
        grievance_number=grievance_number,
        submitted_date=date.today(),
        **grievance_data
    )
    db.add(grievance)
    db.commit()
    db.refresh(grievance)
    return StudentGrievanceResponse.model_validate(grievance)


@router.get("/criterion5/grievances", response_model=StudentGrievanceListResponse, tags=["Criterion 5"])
async def list_grievances(
    category: Optional[str] = None,
    status: Optional[str] = None,
    department: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List student grievances with filters"""
    query = db.query(StudentGrievance)

    if category:
        query = query.filter(StudentGrievance.category == GrievanceCategoryEnum(category))
    if status:
        query = query.filter(StudentGrievance.status == GrievanceStatusEnum(status))
    if department:
        query = query.filter(StudentGrievance.department == department)

    total = query.count()
    items = query.order_by(StudentGrievance.submitted_date.desc()).offset((page - 1) * page_size).limit(page_size).all()

    avg_resolution = db.query(func.avg(StudentGrievance.resolution_days)).filter(
        StudentGrievance.status == GrievanceStatusEnum.RESOLVED
    ).scalar() or 0

    return StudentGrievanceListResponse(
        items=[StudentGrievanceResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        average_resolution_days=avg_resolution
    )


@router.put("/criterion5/grievances/{grievance_id}", response_model=StudentGrievanceResponse, tags=["Criterion 5"])
async def update_grievance(
    grievance_id: str,
    data: StudentGrievanceUpdate,
    db: Session = Depends(get_db)
):
    """Update student grievance"""
    grievance = db.query(StudentGrievance).filter(StudentGrievance.id == grievance_id).first()
    if not grievance:
        raise HTTPException(status_code=404, detail="Grievance not found")

    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        update_data["status"] = GrievanceStatusEnum(update_data["status"].value)
        if update_data["status"] == GrievanceStatusEnum.RESOLVED and grievance.submitted_date:
            update_data["resolution_days"] = (date.today() - grievance.submitted_date).days

    for key, value in update_data.items():
        setattr(grievance, key, value)

    db.commit()
    db.refresh(grievance)
    return StudentGrievanceResponse.model_validate(grievance)


@router.post("/criterion5/alumni", response_model=AlumniRecordResponse, tags=["Criterion 5"])
async def create_alumni(data: AlumniRecordCreate, db: Session = Depends(get_db)):
    """Create new alumni record"""
    alumni = AlumniRecord(id=str(uuid.uuid4()), **data.model_dump())
    db.add(alumni)
    db.commit()
    db.refresh(alumni)
    return AlumniRecordResponse.model_validate(alumni)


@router.get("/criterion5/alumni", response_model=AlumniListResponse, tags=["Criterion 5"])
async def list_alumni(
    department: Optional[str] = None,
    batch: Optional[str] = None,
    graduation_year: Optional[int] = None,
    is_active: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List alumni records with filters"""
    query = db.query(AlumniRecord).filter(AlumniRecord.is_active == is_active)

    if department:
        query = query.filter(AlumniRecord.department == department)
    if batch:
        query = query.filter(AlumniRecord.batch == batch)
    if graduation_year:
        query = query.filter(AlumniRecord.graduation_year == graduation_year)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    entrepreneurs = db.query(AlumniRecord).filter(AlumniRecord.is_entrepreneur == True).count()

    return AlumniListResponse(
        items=[AlumniRecordResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        entrepreneurs_count=entrepreneurs
    )


# Criterion 5 Dashboard
@router.get("/criterion5/dashboard", response_model=Criterion5DashboardStats, tags=["Criterion 5"])
async def get_criterion5_dashboard(
    academic_year: Optional[str] = None,
):
    """Get Criterion 5 dashboard statistics"""
    # Return default stats (database queries will be implemented with async patterns later)
    return Criterion5DashboardStats(
        total_scholarships=0,
        total_scholarship_amount=0,
        scholarships_by_type={},
        beneficiary_students=0,
        placement_percentage=0,
        average_package=0,
        highest_package=0,
        students_in_higher_studies=0,
        students_qualified_competitive_exams=0,
        students_placed=0,
        career_counseling_sessions=0,
        students_attended_counseling=0,
        mentoring_sessions=0,
        students_under_mentoring=0,
        total_alumni=0,
        active_alumni=0,
        alumni_contributions=0,
        alumni_donors=0,
        total_donations=0,
        total_grievances=0,
        resolved_grievances=0,
        average_resolution_days=0,
        pending_grievances=0,
        completion_percentage=0,
        pending_items=[]
    )


# ==================== CRITERION 6: GOVERNANCE ====================

@router.post("/criterion6/governance", response_model=InstitutionalGovernanceResponse, tags=["Criterion 6"])
async def create_governance(data: InstitutionalGovernanceCreate, db: Session = Depends(get_db)):
    """Create institutional governance record"""
    governance = InstitutionalGovernance(id=str(uuid.uuid4()), **data.model_dump())
    db.add(governance)
    db.commit()
    db.refresh(governance)
    return InstitutionalGovernanceResponse.model_validate(governance)


@router.get("/criterion6/governance/{academic_year}", response_model=InstitutionalGovernanceResponse, tags=["Criterion 6"])
async def get_governance(academic_year: str, db: Session = Depends(get_db)):
    """Get governance record for academic year"""
    governance = db.query(InstitutionalGovernance).filter(
        InstitutionalGovernance.academic_year == academic_year
    ).first()
    if not governance:
        raise HTTPException(status_code=404, detail="Governance record not found")
    return InstitutionalGovernanceResponse.model_validate(governance)


@router.post("/criterion6/meetings", response_model=GovernanceMeetingResponse, tags=["Criterion 6"])
async def create_meeting(data: GovernanceMeetingCreate, db: Session = Depends(get_db)):
    """Create new governance meeting record"""
    meeting_data = data.model_dump()
    meeting_data["meeting_type"] = MeetingTypeEnum(data.meeting_type.value)
    meeting = GovernanceMeeting(id=str(uuid.uuid4()), **meeting_data)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return GovernanceMeetingResponse.model_validate(meeting)


@router.get("/criterion6/meetings", response_model=GovernanceMeetingListResponse, tags=["Criterion 6"])
async def list_meetings(
    meeting_type: Optional[str] = None,
    academic_year: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List governance meetings with filters"""
    query = db.query(GovernanceMeeting)

    if meeting_type:
        query = query.filter(GovernanceMeeting.meeting_type == MeetingTypeEnum(meeting_type))
    if academic_year:
        query = query.filter(GovernanceMeeting.academic_year == academic_year)

    total = query.count()
    items = query.order_by(GovernanceMeeting.meeting_date.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return GovernanceMeetingListResponse(
        items=[GovernanceMeetingResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/criterion6/policies", response_model=InstitutionalPolicyResponse, tags=["Criterion 6"])
async def create_policy(data: InstitutionalPolicyCreate, db: Session = Depends(get_db)):
    """Create new institutional policy"""
    policy_data = data.model_dump()
    policy_data["policy_type"] = PolicyTypeEnum(data.policy_type.value)
    policy = InstitutionalPolicy(id=str(uuid.uuid4()), **policy_data)
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return InstitutionalPolicyResponse.model_validate(policy)


@router.get("/criterion6/policies", response_model=InstitutionalPolicyListResponse, tags=["Criterion 6"])
async def list_policies(
    policy_type: Optional[str] = None,
    is_active: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List institutional policies with filters"""
    query = db.query(InstitutionalPolicy).filter(InstitutionalPolicy.is_active == is_active)

    if policy_type:
        query = query.filter(InstitutionalPolicy.policy_type == PolicyTypeEnum(policy_type))

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return InstitutionalPolicyListResponse(
        items=[InstitutionalPolicyResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/criterion6/iqac-activities", response_model=IQACActivityResponse, tags=["Criterion 6"])
async def create_iqac_activity(data: IQACActivityCreate, db: Session = Depends(get_db)):
    """Create new IQAC activity"""
    activity_data = data.model_dump()
    activity_data["activity_type"] = QualityInitiativeTypeEnum(data.activity_type.value)
    activity = IQACActivity(id=str(uuid.uuid4()), **activity_data)
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return IQACActivityResponse.model_validate(activity)


@router.get("/criterion6/iqac-activities", response_model=IQACActivityListResponse, tags=["Criterion 6"])
async def list_iqac_activities(
    activity_type: Optional[str] = None,
    academic_year: Optional[str] = None,
    is_completed: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List IQAC activities with filters"""
    query = db.query(IQACActivity)

    if activity_type:
        query = query.filter(IQACActivity.activity_type == QualityInitiativeTypeEnum(activity_type))
    if academic_year:
        query = query.filter(IQACActivity.academic_year == academic_year)
    if is_completed is not None:
        query = query.filter(IQACActivity.is_completed == is_completed)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return IQACActivityListResponse(
        items=[IQACActivityResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        completed_count=db.query(IQACActivity).filter(IQACActivity.is_completed == True).count()
    )


@router.post("/criterion6/faculty-development", response_model=FacultyDevelopmentResponse, tags=["Criterion 6"])
async def create_fdp(data: FacultyDevelopmentCreate, db: Session = Depends(get_db)):
    """Create new faculty development record"""
    fdp_data = data.model_dump()
    fdp_data["program_type"] = FDPTypeEnum(data.program_type.value)
    fdp = FacultyDevelopment(id=str(uuid.uuid4()), **fdp_data)
    db.add(fdp)
    db.commit()
    db.refresh(fdp)
    return FacultyDevelopmentResponse.model_validate(fdp)


@router.get("/criterion6/faculty-development", response_model=FacultyDevelopmentListResponse, tags=["Criterion 6"])
async def list_fdps(
    program_type: Optional[str] = None,
    department: Optional[str] = None,
    academic_year: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List faculty development programs with filters"""
    query = db.query(FacultyDevelopment)

    if program_type:
        query = query.filter(FacultyDevelopment.program_type == FDPTypeEnum(program_type))
    if department:
        query = query.filter(FacultyDevelopment.department == department)
    if academic_year:
        query = query.filter(FacultyDevelopment.academic_year == academic_year)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return FacultyDevelopmentListResponse(
        items=[FacultyDevelopmentResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_programs=total
    )


# Criterion 6 Dashboard
@router.get("/criterion6/dashboard", response_model=Criterion6DashboardStats, tags=["Criterion 6"])
async def get_criterion6_dashboard(
    academic_year: Optional[str] = None,
):
    """Get Criterion 6 dashboard statistics"""
    # Return default stats (database queries will be implemented with async patterns later)
    return Criterion6DashboardStats(
        vision_mission_defined=False,
        governance_committees_count=0,
        e_governance_modules=0,
        decentralization_practices=0,
        strategic_plan_active=False,
        implementation_progress=0,
        kpis_defined=0,
        milestones_achieved=0,
        fdp_conducted=0,
        faculty_trained=0,
        average_training_days=0,
        certifications_received=0,
        audits_completed=0,
        total_income=0,
        total_expenditure=0,
        utilization_percentage=0,
        iqac_meetings=0,
        quality_initiatives=0,
        aqar_submitted=False,
        academic_audits=0,
        governing_body_meetings=0,
        academic_council_meetings=0,
        bos_meetings=0,
        total_policies=0,
        completion_percentage=0,
        pending_items=[]
    )


# ==================== CRITERION 7: INSTITUTIONAL VALUES ====================

@router.post("/criterion7/gender-equity", response_model=GenderEquityProgramResponse, tags=["Criterion 7"])
async def create_gender_equity_program(data: GenderEquityProgramCreate, db: Session = Depends(get_db)):
    """Create new gender equity program"""
    program = GenderEquityProgram(id=str(uuid.uuid4()), **data.model_dump())
    db.add(program)
    db.commit()
    db.refresh(program)
    return GenderEquityProgramResponse.model_validate(program)


@router.get("/criterion7/gender-equity", response_model=GenderEquityProgramListResponse, tags=["Criterion 7"])
async def list_gender_equity_programs(
    academic_year: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List gender equity programs"""
    query = db.query(GenderEquityProgram)
    if academic_year:
        query = query.filter(GenderEquityProgram.academic_year == academic_year)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_participants = db.query(func.sum(GenderEquityProgram.participants_count)).scalar() or 0

    return GenderEquityProgramListResponse(
        items=[GenderEquityProgramResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_participants=total_participants
    )


@router.post("/criterion7/green-initiatives", response_model=GreenInitiativeResponse, tags=["Criterion 7"])
async def create_green_initiative(data: GreenInitiativeCreate, db: Session = Depends(get_db)):
    """Create new green initiative"""
    initiative_data = data.model_dump()
    initiative_data["initiative_type"] = GreenInitiativeTypeEnum(data.initiative_type.value)
    initiative = GreenInitiative(id=str(uuid.uuid4()), **initiative_data)
    db.add(initiative)
    db.commit()
    db.refresh(initiative)
    return GreenInitiativeResponse.model_validate(initiative)


@router.get("/criterion7/green-initiatives", response_model=GreenInitiativeListResponse, tags=["Criterion 7"])
async def list_green_initiatives(
    initiative_type: Optional[str] = None,
    academic_year: Optional[str] = None,
    is_active: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List green initiatives"""
    query = db.query(GreenInitiative).filter(GreenInitiative.is_active == is_active)

    if initiative_type:
        query = query.filter(GreenInitiative.initiative_type == GreenInitiativeTypeEnum(initiative_type))
    if academic_year:
        query = query.filter(GreenInitiative.academic_year == academic_year)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_investment = db.query(func.sum(GreenInitiative.investment)).scalar() or 0
    total_savings = db.query(func.sum(GreenInitiative.annual_savings)).scalar() or 0

    return GreenInitiativeListResponse(
        items=[GreenInitiativeResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_investment=total_investment,
        total_savings=total_savings
    )


@router.post("/criterion7/best-practices", response_model=BestPracticeResponse, tags=["Criterion 7"])
async def create_best_practice(data: BestPracticeCreate, db: Session = Depends(get_db)):
    """Create new best practice"""
    practice_data = data.model_dump()
    practice_data["category"] = BestPracticeCategoryEnum(data.category.value)
    practice = BestPractice(id=str(uuid.uuid4()), **practice_data)
    db.add(practice)
    db.commit()
    db.refresh(practice)
    return BestPracticeResponse.model_validate(practice)


@router.get("/criterion7/best-practices", response_model=BestPracticeListResponse, tags=["Criterion 7"])
async def list_best_practices(
    category: Optional[str] = None,
    academic_year: Optional[str] = None,
    is_featured: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List best practices"""
    query = db.query(BestPractice).filter(BestPractice.is_active == True)

    if category:
        query = query.filter(BestPractice.category == BestPracticeCategoryEnum(category))
    if academic_year:
        query = query.filter(BestPractice.academic_year == academic_year)
    if is_featured is not None:
        query = query.filter(BestPractice.is_featured == is_featured)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    featured_count = db.query(BestPractice).filter(BestPractice.is_featured == True).count()

    return BestPracticeListResponse(
        items=[BestPracticeResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        featured_count=featured_count
    )


@router.post("/criterion7/awards", response_model=InstitutionalAwardResponse, tags=["Criterion 7"])
async def create_award(data: InstitutionalAwardCreate, db: Session = Depends(get_db)):
    """Create new institutional award record"""
    award_data = data.model_dump()
    award_data["category"] = AwardCategoryEnum(data.category.value)
    award = InstitutionalAward(id=str(uuid.uuid4()), **award_data)
    db.add(award)
    db.commit()
    db.refresh(award)
    return InstitutionalAwardResponse.model_validate(award)


@router.get("/criterion7/awards", response_model=InstitutionalAwardListResponse, tags=["Criterion 7"])
async def list_awards(
    category: Optional[str] = None,
    academic_year: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List institutional awards"""
    query = db.query(InstitutionalAward)

    if category:
        query = query.filter(InstitutionalAward.category == AwardCategoryEnum(category))
    if academic_year:
        query = query.filter(InstitutionalAward.academic_year == academic_year)

    total = query.count()
    items = query.order_by(InstitutionalAward.award_date.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return InstitutionalAwardListResponse(
        items=[InstitutionalAwardResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )


# Criterion 7 Dashboard
@router.get("/criterion7/dashboard", response_model=Criterion7DashboardStats, tags=["Criterion 7"])
async def get_criterion7_dashboard(
    academic_year: Optional[str] = None,
):
    """Get Criterion 7 dashboard statistics"""
    # Return default stats (database queries will be implemented with async patterns later)
    return Criterion7DashboardStats(
        gender_equity_programs=0,
        sensitization_programs=0,
        total_participants_gender=0,
        women_empowerment_initiatives=0,
        total_best_practices=0,
        featured_practices=0,
        best_practices_by_category={},
        distinctiveness_items=0,
        national_recognitions=0,
        international_recognitions=0,
        total_green_initiatives=0,
        solar_capacity_kw=0,
        water_harvesting_capacity=0,
        trees_planted=0,
        carbon_footprint_reduced=0,
        green_audit_completed=False,
        inclusivity_programs=0,
        total_beneficiaries=0,
        scholarships_for_disadvantaged=0,
        ethics_programs=0,
        code_of_conduct_implemented=False,
        anti_ragging_measures=0,
        cases_resolved=0,
        total_awards=0,
        national_awards=0,
        accreditation_status={},
        nirf_rank=None,
        sdg_goals_addressed=[],
        sdg_initiatives=0,
        completion_percentage=0,
        pending_items=[]
    )


# ==================== NBA ACCREDITATION ====================

@router.post("/nba/programs", response_model=ProgramVisionMissionResponse, tags=["NBA"])
async def create_program(data: ProgramVisionMissionCreate, db: Session = Depends(get_db)):
    """Create new program with vision/mission/PEOs"""
    program_data = data.model_dump()
    program_data["program_type"] = ProgramTypeEnum(data.program_type.value)
    program = ProgramVisionMission(id=str(uuid.uuid4()), **program_data)
    db.add(program)
    db.commit()
    db.refresh(program)
    return ProgramVisionMissionResponse.model_validate(program)


@router.get("/nba/programs", response_model=ProgramVisionMissionListResponse, tags=["NBA"])
async def list_programs(
    program_type: Optional[str] = None,
    department: Optional[str] = None,
    is_active: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List programs with filters"""
    query = db.query(ProgramVisionMission).filter(ProgramVisionMission.is_active == is_active)

    if program_type:
        query = query.filter(ProgramVisionMission.program_type == ProgramTypeEnum(program_type))
    if department:
        query = query.filter(ProgramVisionMission.department == department)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return ProgramVisionMissionListResponse(
        items=[ProgramVisionMissionResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/nba/programs/{program_id}", response_model=ProgramVisionMissionResponse, tags=["NBA"])
async def get_program(program_id: str, db: Session = Depends(get_db)):
    """Get program by ID"""
    program = db.query(ProgramVisionMission).filter(ProgramVisionMission.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return ProgramVisionMissionResponse.model_validate(program)


@router.post("/nba/programs/{program_id}/pos", response_model=ProgramOutcomeResponse, tags=["NBA"])
async def create_program_outcome(
    program_id: str,
    data: ProgramOutcomeCreate,
    db: Session = Depends(get_db)
):
    """Create new program outcome"""
    program = db.query(ProgramVisionMission).filter(ProgramVisionMission.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    po = ProgramOutcome(
        id=str(uuid.uuid4()),
        program_id=program_id,
        **data.model_dump(exclude={"program_id"})
    )
    db.add(po)
    db.commit()
    db.refresh(po)
    return ProgramOutcomeResponse.model_validate(po)


@router.get("/nba/programs/{program_id}/pos", response_model=ProgramOutcomeListResponse, tags=["NBA"])
async def list_program_outcomes(
    program_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List program outcomes for a program"""
    query = db.query(ProgramOutcome).filter(
        ProgramOutcome.program_id == program_id,
        ProgramOutcome.is_active == True
    )

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return ProgramOutcomeListResponse(
        items=[ProgramOutcomeResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/nba/course-outcomes", response_model=CourseOutcomeResponse, tags=["NBA"])
async def create_course_outcome(data: CourseOutcomeCreate, db: Session = Depends(get_db)):
    """Create new course outcome"""
    co = CourseOutcome(id=str(uuid.uuid4()), **data.model_dump())
    db.add(co)
    db.commit()
    db.refresh(co)
    return CourseOutcomeResponse.model_validate(co)


@router.get("/nba/course-outcomes", response_model=CourseOutcomeListResponse, tags=["NBA"])
async def list_course_outcomes(
    program_id: Optional[str] = None,
    course_code: Optional[str] = None,
    semester: Optional[int] = None,
    academic_year: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List course outcomes with filters"""
    query = db.query(CourseOutcome).filter(CourseOutcome.is_active == True)

    if program_id:
        query = query.filter(CourseOutcome.program_id == program_id)
    if course_code:
        query = query.filter(CourseOutcome.course_code == course_code)
    if semester:
        query = query.filter(CourseOutcome.semester == semester)
    if academic_year:
        query = query.filter(CourseOutcome.academic_year == academic_year)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return CourseOutcomeListResponse(
        items=[CourseOutcomeResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/nba/co-attainment", response_model=COAttainmentResponse, tags=["NBA"])
async def create_co_attainment(data: COAttainmentCreate, db: Session = Depends(get_db)):
    """Create new CO attainment record"""
    attainment = COAttainment(id=str(uuid.uuid4()), **data.model_dump())
    db.add(attainment)
    db.commit()
    db.refresh(attainment)
    return COAttainmentResponse.model_validate(attainment)


@router.get("/nba/co-attainment", response_model=COAttainmentListResponse, tags=["NBA"])
async def list_co_attainment(
    course_code: Optional[str] = None,
    academic_year: Optional[str] = None,
    batch: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List CO attainment records with filters"""
    query = db.query(COAttainment)

    if course_code:
        query = query.filter(COAttainment.course_code == course_code)
    if academic_year:
        query = query.filter(COAttainment.academic_year == academic_year)
    if batch:
        query = query.filter(COAttainment.batch == batch)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    avg_attainment = db.query(func.avg(COAttainment.overall_attainment)).scalar() or 0

    return COAttainmentListResponse(
        items=[COAttainmentResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        average_attainment=avg_attainment
    )


@router.put("/nba/co-attainment/{attainment_id}", response_model=COAttainmentResponse, tags=["NBA"])
async def update_co_attainment(
    attainment_id: str,
    data: COAttainmentUpdate,
    db: Session = Depends(get_db)
):
    """Update CO attainment record"""
    attainment = db.query(COAttainment).filter(COAttainment.id == attainment_id).first()
    if not attainment:
        raise HTTPException(status_code=404, detail="CO Attainment record not found")

    update_data = data.model_dump(exclude_unset=True)
    if "attainment_level" in update_data and update_data["attainment_level"]:
        update_data["attainment_level"] = AttainmentLevelEnum(update_data["attainment_level"].value)

    for key, value in update_data.items():
        setattr(attainment, key, value)

    db.commit()
    db.refresh(attainment)
    return COAttainmentResponse.model_validate(attainment)


@router.post("/nba/po-attainment", response_model=POAttainmentResponse, tags=["NBA"])
async def create_po_attainment(data: POAttainmentCreate, db: Session = Depends(get_db)):
    """Create new PO attainment record"""
    attainment = POAttainment(id=str(uuid.uuid4()), **data.model_dump())
    db.add(attainment)
    db.commit()
    db.refresh(attainment)
    return POAttainmentResponse.model_validate(attainment)


@router.get("/nba/po-attainment", response_model=POAttainmentListResponse, tags=["NBA"])
async def list_po_attainment(
    program_id: Optional[str] = None,
    academic_year: Optional[str] = None,
    batch: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List PO attainment records with filters"""
    query = db.query(POAttainment)

    if program_id:
        query = query.filter(POAttainment.program_id == program_id)
    if academic_year:
        query = query.filter(POAttainment.academic_year == academic_year)
    if batch:
        query = query.filter(POAttainment.batch == batch)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    avg_attainment = db.query(func.avg(POAttainment.overall_attainment)).scalar() or 0

    return POAttainmentListResponse(
        items=[POAttainmentResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        average_attainment=avg_attainment
    )


@router.post("/nba/continuous-improvement", response_model=NBAContinuousImprovementResponse, tags=["NBA"])
async def create_improvement_action(data: NBAContinuousImprovementCreate, db: Session = Depends(get_db)):
    """Create new continuous improvement action"""
    action = NBAContinuousImprovement(id=str(uuid.uuid4()), **data.model_dump())
    db.add(action)
    db.commit()
    db.refresh(action)
    return NBAContinuousImprovementResponse.model_validate(action)


@router.get("/nba/continuous-improvement", response_model=NBAContinuousImprovementListResponse, tags=["NBA"])
async def list_improvement_actions(
    program_id: Optional[str] = None,
    status: Optional[str] = None,
    academic_year: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List continuous improvement actions with filters"""
    query = db.query(NBAContinuousImprovement)

    if program_id:
        query = query.filter(NBAContinuousImprovement.program_id == program_id)
    if status:
        query = query.filter(NBAContinuousImprovement.status == ActionStatusEnum(status))
    if academic_year:
        query = query.filter(NBAContinuousImprovement.academic_year == academic_year)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return NBAContinuousImprovementListResponse(
        items=[NBAContinuousImprovementResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size
    )


# NBA Dashboard
@router.get("/nba/dashboard/{program_id}", response_model=NBADashboardStats, tags=["NBA"])
async def get_nba_dashboard(
    program_id: str,
    academic_year: Optional[str] = None,
):
    """Get NBA dashboard statistics for a program"""
    # Return default stats (database queries will be implemented with async patterns later)
    return NBADashboardStats(
        program_name="Sample Program",
        program_code=program_id,
        total_students=0,
        total_faculty=0,
        vision_mission_defined=False,
        peos_count=0,
        pso_count=0,
        stakeholder_consultations=0,
        total_courses=0,
        co_count=0,
        po_count=0,
        co_po_mapping_percentage=0,
        average_co_attainment=0,
        average_po_attainment=0,
        pos_above_target=0,
        attainment_by_po={},
        pass_percentage=0,
        placement_percentage=0,
        higher_studies_percentage=0,
        average_salary=None,
        faculty_count=0,
        phd_faculty_percentage=0,
        industry_experienced_percentage=0,
        total_publications=0,
        labs_count=0,
        total_equipment_value=0,
        average_lab_utilization=0,
        software_licenses=0,
        improvement_actions_total=0,
        improvement_actions_completed=0,
        feedback_collected={},
        audit_observations_resolved=0,
        completion_percentage=0,
        pending_items=[]
    )
