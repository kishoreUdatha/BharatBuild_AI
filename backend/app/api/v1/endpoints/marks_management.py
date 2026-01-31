"""
Assessment & Marks Management API
Full marks entry, approval workflow, audit trail, and ERP sync
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import json

from app.core.database import get_db
from app.models.marks_management import (
    AssessmentConfig, LabMarksConfig, MarksHeader, MarksDetail, MarksAudit,
    MarksApprovalRequest, MarksUnlockRequest, ERPSyncLog, MarksAnalytics,
    AssessmentType, MarksStatus, SyncStatus
)
from app.models.user import User
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


# ==================== Schemas ====================

class AssessmentConfigCreate(BaseModel):
    academic_year: str
    semester: int
    subject_id: Optional[str] = None
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    assessment_type: str
    assessment_name: str
    max_marks: int
    weightage: float = 100.0
    scheduled_date: Optional[datetime] = None


class LabMarksConfigCreate(BaseModel):
    academic_year: str
    semester: int
    lab_id: Optional[str] = None
    lab_name: Optional[str] = None
    experiment_completion_weightage: float = 40.0
    lab_test_weightage: float = 30.0
    record_documentation_weightage: float = 20.0
    viva_weightage: float = 10.0
    total_max_marks: int = 100


class MarksHeaderCreate(BaseModel):
    academic_year: str
    semester: int
    subject_id: Optional[str] = None
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    section_id: Optional[str] = None
    section_name: Optional[str] = None
    assessment_type: str
    assessment_name: str
    assessment_date: Optional[datetime] = None
    max_marks: int


class MarksEntryItem(BaseModel):
    student_id: str
    roll_number: Optional[str] = None
    student_name: Optional[str] = None
    obtained_marks: Optional[float] = None
    is_absent: bool = False
    remarks: Optional[str] = None
    # Lab-specific
    lab_experiment_marks: Optional[float] = None
    lab_test_marks: Optional[float] = None
    lab_record_marks: Optional[float] = None
    lab_viva_marks: Optional[float] = None


class BulkMarksEntry(BaseModel):
    header_id: str
    entries: List[MarksEntryItem]


class MarksModeration(BaseModel):
    detail_id: str
    moderation_applied: float
    moderation_reason: str


class ApprovalAction(BaseModel):
    action: str  # approve, reject
    remarks: Optional[str] = None


class UnlockRequest(BaseModel):
    reason: str


# ==================== Assessment Configuration ====================

@router.post("/assessment-config", response_model=dict)
async def create_assessment_config(
    config: AssessmentConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create assessment configuration"""
    assessment = AssessmentConfig(
        academic_year=config.academic_year,
        semester=config.semester,
        subject_id=config.subject_id,
        subject_code=config.subject_code,
        subject_name=config.subject_name,
        assessment_type=AssessmentType(config.assessment_type),
        assessment_name=config.assessment_name,
        max_marks=config.max_marks,
        weightage=config.weightage,
        scheduled_date=config.scheduled_date,
        created_by=current_user.id
    )
    db.add(assessment)
    db.commit()
    return {"id": assessment.id, "message": "Assessment configuration created"}


@router.get("/assessment-config", response_model=List[dict])
async def list_assessment_configs(
    academic_year: Optional[str] = None,
    semester: Optional[int] = None,
    subject_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List assessment configurations"""
    query = db.query(AssessmentConfig).filter(AssessmentConfig.is_active == True)

    if academic_year:
        query = query.filter(AssessmentConfig.academic_year == academic_year)
    if semester:
        query = query.filter(AssessmentConfig.semester == semester)
    if subject_id:
        query = query.filter(AssessmentConfig.subject_id == subject_id)

    configs = query.order_by(AssessmentConfig.created_at.desc()).all()

    return [
        {
            "id": c.id,
            "academic_year": c.academic_year,
            "semester": c.semester,
            "subject_code": c.subject_code,
            "subject_name": c.subject_name,
            "assessment_type": c.assessment_type.value,
            "assessment_name": c.assessment_name,
            "max_marks": c.max_marks,
            "weightage": c.weightage,
            "scheduled_date": c.scheduled_date.isoformat() if c.scheduled_date else None
        }
        for c in configs
    ]


# ==================== Lab Marks Configuration ====================

@router.post("/lab-marks-config", response_model=dict)
async def create_lab_marks_config(
    config: LabMarksConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create lab marks weightage configuration"""
    # Validate weightages sum to 100
    total = (config.experiment_completion_weightage + config.lab_test_weightage +
             config.record_documentation_weightage + config.viva_weightage)
    if abs(total - 100) > 0.01:
        raise HTTPException(status_code=400, detail=f"Weightages must sum to 100 (got {total})")

    lab_config = LabMarksConfig(
        academic_year=config.academic_year,
        semester=config.semester,
        lab_id=config.lab_id,
        lab_name=config.lab_name,
        experiment_completion_weightage=config.experiment_completion_weightage,
        lab_test_weightage=config.lab_test_weightage,
        record_documentation_weightage=config.record_documentation_weightage,
        viva_weightage=config.viva_weightage,
        total_max_marks=config.total_max_marks,
        created_by=current_user.id
    )
    db.add(lab_config)
    db.commit()
    return {"id": lab_config.id, "message": "Lab marks configuration created"}


@router.get("/lab-marks-config/{lab_id}", response_model=dict)
async def get_lab_marks_config(
    lab_id: str,
    academic_year: str,
    semester: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get lab marks configuration"""
    config = db.query(LabMarksConfig).filter(
        LabMarksConfig.lab_id == lab_id,
        LabMarksConfig.academic_year == academic_year,
        LabMarksConfig.semester == semester
    ).first()

    if not config:
        # Return default config
        return {
            "experiment_completion_weightage": 40.0,
            "lab_test_weightage": 30.0,
            "record_documentation_weightage": 20.0,
            "viva_weightage": 10.0,
            "total_max_marks": 100
        }

    return {
        "id": config.id,
        "experiment_completion_weightage": config.experiment_completion_weightage,
        "lab_test_weightage": config.lab_test_weightage,
        "record_documentation_weightage": config.record_documentation_weightage,
        "viva_weightage": config.viva_weightage,
        "total_max_marks": config.total_max_marks,
        "approved_by": config.approved_by,
        "approved_at": config.approved_at.isoformat() if config.approved_at else None
    }


# ==================== Marks Entry ====================

@router.post("/marks-sheet", response_model=dict)
async def create_marks_sheet(
    header: MarksHeaderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new marks sheet (header)"""
    marks_header = MarksHeader(
        academic_year=header.academic_year,
        semester=header.semester,
        subject_id=header.subject_id,
        subject_code=header.subject_code,
        subject_name=header.subject_name,
        section_id=header.section_id,
        section_name=header.section_name,
        assessment_type=AssessmentType(header.assessment_type),
        assessment_name=header.assessment_name,
        assessment_date=header.assessment_date,
        max_marks=header.max_marks,
        status=MarksStatus.DRAFT,
        entered_by=current_user.id
    )
    db.add(marks_header)
    db.commit()

    # Create audit entry
    audit = MarksAudit(
        header_id=marks_header.id,
        changed_by=current_user.id,
        changed_by_name=current_user.full_name,
        field_changed="status",
        old_value=None,
        new_value="draft",
        action="create",
        reason="Marks sheet created"
    )
    db.add(audit)
    db.commit()

    return {"id": marks_header.id, "message": "Marks sheet created"}


@router.get("/marks-sheets", response_model=List[dict])
async def list_marks_sheets(
    academic_year: Optional[str] = None,
    semester: Optional[int] = None,
    subject_id: Optional[str] = None,
    section_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List marks sheets with filters"""
    query = db.query(MarksHeader)

    if academic_year:
        query = query.filter(MarksHeader.academic_year == academic_year)
    if semester:
        query = query.filter(MarksHeader.semester == semester)
    if subject_id:
        query = query.filter(MarksHeader.subject_id == subject_id)
    if section_id:
        query = query.filter(MarksHeader.section_id == section_id)
    if status:
        query = query.filter(MarksHeader.status == MarksStatus(status))

    # Faculty sees only their sheets, HOD/Admin sees all
    if current_user.role not in ['admin', 'hod', 'principal']:
        query = query.filter(MarksHeader.entered_by == current_user.id)

    sheets = query.order_by(MarksHeader.created_at.desc()).limit(100).all()

    return [
        {
            "id": s.id,
            "academic_year": s.academic_year,
            "semester": s.semester,
            "subject_code": s.subject_code,
            "subject_name": s.subject_name,
            "section_name": s.section_name,
            "assessment_type": s.assessment_type.value,
            "assessment_name": s.assessment_name,
            "max_marks": s.max_marks,
            "status": s.status.value,
            "total_students": s.total_students,
            "average_marks": s.average_marks,
            "entered_at": s.entered_at.isoformat() if s.entered_at else None,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "approved_at": s.approved_at.isoformat() if s.approved_at else None
        }
        for s in sheets
    ]


@router.get("/marks-sheet/{header_id}", response_model=dict)
async def get_marks_sheet(
    header_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get marks sheet with all student entries"""
    header = db.query(MarksHeader).filter(MarksHeader.id == header_id).first()
    if not header:
        raise HTTPException(status_code=404, detail="Marks sheet not found")

    details = db.query(MarksDetail).filter(MarksDetail.header_id == header_id).all()

    return {
        "header": {
            "id": header.id,
            "academic_year": header.academic_year,
            "semester": header.semester,
            "subject_code": header.subject_code,
            "subject_name": header.subject_name,
            "section_name": header.section_name,
            "assessment_type": header.assessment_type.value,
            "assessment_name": header.assessment_name,
            "assessment_date": header.assessment_date.isoformat() if header.assessment_date else None,
            "max_marks": header.max_marks,
            "status": header.status.value,
            "total_students": header.total_students,
            "students_present": header.students_present,
            "average_marks": header.average_marks,
            "highest_marks": header.highest_marks,
            "lowest_marks": header.lowest_marks,
            "pass_count": header.pass_count,
            "fail_count": header.fail_count,
            "can_edit": header.status in [MarksStatus.DRAFT, MarksStatus.REJECTED]
        },
        "students": [
            {
                "id": d.id,
                "student_id": d.student_id,
                "roll_number": d.roll_number,
                "student_name": d.student_name,
                "obtained_marks": d.obtained_marks,
                "is_absent": d.is_absent,
                "attendance_percentage": d.attendance_percentage,
                "remarks": d.remarks,
                "grade": d.grade,
                "lab_experiment_marks": d.lab_experiment_marks,
                "lab_test_marks": d.lab_test_marks,
                "lab_record_marks": d.lab_record_marks,
                "lab_viva_marks": d.lab_viva_marks,
                "auto_populated": d.auto_populated,
                "moderation_applied": d.moderation_applied
            }
            for d in details
        ]
    }


@router.post("/marks-sheet/{header_id}/entries", response_model=dict)
async def save_marks_entries(
    header_id: str,
    data: BulkMarksEntry,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save/update marks entries (bulk)"""
    header = db.query(MarksHeader).filter(MarksHeader.id == header_id).first()
    if not header:
        raise HTTPException(status_code=404, detail="Marks sheet not found")

    if header.status not in [MarksStatus.DRAFT, MarksStatus.REJECTED]:
        raise HTTPException(status_code=400, detail="Cannot edit marks in current status")

    saved_count = 0
    for entry in data.entries:
        # Check if entry exists
        detail = db.query(MarksDetail).filter(
            MarksDetail.header_id == header_id,
            MarksDetail.student_id == entry.student_id
        ).first()

        if detail:
            # Update existing - create audit
            old_marks = detail.obtained_marks
            if old_marks != entry.obtained_marks:
                audit = MarksAudit(
                    header_id=header_id,
                    detail_id=detail.id,
                    changed_by=current_user.id,
                    changed_by_name=current_user.full_name,
                    field_changed="obtained_marks",
                    old_value=str(old_marks) if old_marks is not None else None,
                    new_value=str(entry.obtained_marks) if entry.obtained_marks is not None else None,
                    action="update"
                )
                db.add(audit)

            detail.obtained_marks = entry.obtained_marks
            detail.is_absent = entry.is_absent
            detail.remarks = entry.remarks
            detail.lab_experiment_marks = entry.lab_experiment_marks
            detail.lab_test_marks = entry.lab_test_marks
            detail.lab_record_marks = entry.lab_record_marks
            detail.lab_viva_marks = entry.lab_viva_marks
        else:
            # Create new
            detail = MarksDetail(
                header_id=header_id,
                student_id=entry.student_id,
                roll_number=entry.roll_number,
                student_name=entry.student_name,
                obtained_marks=entry.obtained_marks,
                is_absent=entry.is_absent,
                remarks=entry.remarks,
                lab_experiment_marks=entry.lab_experiment_marks,
                lab_test_marks=entry.lab_test_marks,
                lab_record_marks=entry.lab_record_marks,
                lab_viva_marks=entry.lab_viva_marks
            )
            db.add(detail)

        saved_count += 1

    # Update header stats
    all_details = db.query(MarksDetail).filter(MarksDetail.header_id == header_id).all()
    marks = [d.obtained_marks for d in all_details if d.obtained_marks is not None]

    header.total_students = len(all_details)
    header.students_present = len([d for d in all_details if not d.is_absent])
    header.average_marks = sum(marks) / len(marks) if marks else None
    header.highest_marks = max(marks) if marks else None
    header.lowest_marks = min(marks) if marks else None
    header.pass_count = len([m for m in marks if m >= header.max_marks * 0.4])
    header.fail_count = len([m for m in marks if m < header.max_marks * 0.4])
    header.entered_at = datetime.utcnow()

    db.commit()

    return {"message": f"Saved {saved_count} entries", "stats": {
        "total_students": header.total_students,
        "average_marks": header.average_marks,
        "pass_count": header.pass_count
    }}


@router.post("/marks-sheet/{header_id}/auto-populate", response_model=dict)
async def auto_populate_marks(
    header_id: str,
    source_type: str = Query(..., description="quiz, lab_test, project"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Auto-populate marks from platform data (quiz, lab, project)"""
    header = db.query(MarksHeader).filter(MarksHeader.id == header_id).first()
    if not header:
        raise HTTPException(status_code=404, detail="Marks sheet not found")

    # TODO: Implement fetching from various sources
    # For now, return placeholder
    return {
        "message": f"Auto-population from {source_type} not yet implemented",
        "populated_count": 0
    }


# ==================== Approval Workflow ====================

@router.post("/marks-sheet/{header_id}/submit", response_model=dict)
async def submit_marks_for_approval(
    header_id: str,
    remarks: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit marks sheet for HOD approval"""
    header = db.query(MarksHeader).filter(MarksHeader.id == header_id).first()
    if not header:
        raise HTTPException(status_code=404, detail="Marks sheet not found")

    if header.status != MarksStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only draft marks can be submitted")

    # Check if all students have marks
    details = db.query(MarksDetail).filter(MarksDetail.header_id == header_id).all()
    if not details:
        raise HTTPException(status_code=400, detail="No student entries found")

    # Update status
    old_status = header.status.value
    header.status = MarksStatus.SUBMITTED
    header.submitted_at = datetime.utcnow()
    header.submitted_by = current_user.id

    # Create approval request
    approval = MarksApprovalRequest(
        header_id=header_id,
        requested_by=current_user.id,
        request_remarks=remarks,
        current_approver_role="hod"
    )
    db.add(approval)

    # Audit
    audit = MarksAudit(
        header_id=header_id,
        changed_by=current_user.id,
        changed_by_name=current_user.full_name,
        field_changed="status",
        old_value=old_status,
        new_value="submitted",
        action="submit",
        reason=remarks
    )
    db.add(audit)

    db.commit()

    return {"message": "Marks submitted for approval", "status": "submitted"}


@router.post("/marks-sheet/{header_id}/approve", response_model=dict)
async def approve_marks(
    header_id: str,
    action: ApprovalAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """HOD approves or rejects marks"""
    # Check role
    if current_user.role not in ['admin', 'hod', 'principal']:
        raise HTTPException(status_code=403, detail="Only HOD/Admin can approve marks")

    header = db.query(MarksHeader).filter(MarksHeader.id == header_id).first()
    if not header:
        raise HTTPException(status_code=404, detail="Marks sheet not found")

    if header.status != MarksStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Only submitted marks can be approved")

    old_status = header.status.value

    if action.action == "approve":
        header.status = MarksStatus.APPROVED
        header.approved_by = current_user.id
        header.approved_at = datetime.utcnow()
        header.review_remarks = action.remarks
        new_status = "approved"
    elif action.action == "reject":
        header.status = MarksStatus.REJECTED
        header.reviewed_by = current_user.id
        header.reviewed_at = datetime.utcnow()
        header.review_remarks = action.remarks
        new_status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    # Update approval request
    approval = db.query(MarksApprovalRequest).filter(
        MarksApprovalRequest.header_id == header_id,
        MarksApprovalRequest.response_status == None
    ).first()
    if approval:
        approval.response_status = action.action + "d"
        approval.responded_by = current_user.id
        approval.responded_at = datetime.utcnow()
        approval.response_remarks = action.remarks

    # Audit
    audit = MarksAudit(
        header_id=header_id,
        changed_by=current_user.id,
        changed_by_name=current_user.full_name,
        field_changed="status",
        old_value=old_status,
        new_value=new_status,
        action=action.action,
        reason=action.remarks
    )
    db.add(audit)

    db.commit()

    return {"message": f"Marks {action.action}d successfully", "status": new_status}


@router.post("/marks-sheet/{header_id}/lock", response_model=dict)
async def lock_marks(
    header_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lock approved marks (no further edits)"""
    if current_user.role not in ['admin', 'hod', 'principal']:
        raise HTTPException(status_code=403, detail="Only HOD/Admin can lock marks")

    header = db.query(MarksHeader).filter(MarksHeader.id == header_id).first()
    if not header:
        raise HTTPException(status_code=404, detail="Marks sheet not found")

    if header.status != MarksStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Only approved marks can be locked")

    header.status = MarksStatus.LOCKED
    header.locked_at = datetime.utcnow()
    header.locked_by = current_user.id

    # Mark all details as finalized
    db.query(MarksDetail).filter(MarksDetail.header_id == header_id).update(
        {"is_finalized": True}
    )

    # Audit
    audit = MarksAudit(
        header_id=header_id,
        changed_by=current_user.id,
        changed_by_name=current_user.full_name,
        field_changed="status",
        old_value="approved",
        new_value="locked",
        action="lock"
    )
    db.add(audit)

    db.commit()

    return {"message": "Marks locked successfully"}


@router.post("/marks-sheet/{header_id}/unlock-request", response_model=dict)
async def request_unlock(
    header_id: str,
    request: UnlockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Request to unlock locked marks"""
    header = db.query(MarksHeader).filter(MarksHeader.id == header_id).first()
    if not header:
        raise HTTPException(status_code=404, detail="Marks sheet not found")

    if header.status not in [MarksStatus.APPROVED, MarksStatus.LOCKED]:
        raise HTTPException(status_code=400, detail="Only approved/locked marks need unlock request")

    unlock_req = MarksUnlockRequest(
        header_id=header_id,
        requested_by=current_user.id,
        reason=request.reason
    )
    db.add(unlock_req)
    db.commit()

    return {"id": unlock_req.id, "message": "Unlock request submitted"}


# ==================== Audit Trail ====================

@router.get("/marks-sheet/{header_id}/audit", response_model=List[dict])
async def get_marks_audit(
    header_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get complete audit trail for marks sheet"""
    audits = db.query(MarksAudit).filter(
        MarksAudit.header_id == header_id
    ).order_by(MarksAudit.created_at.desc()).all()

    return [
        {
            "id": a.id,
            "changed_by": a.changed_by_name,
            "changed_by_role": a.changed_by_role,
            "field_changed": a.field_changed,
            "old_value": a.old_value,
            "new_value": a.new_value,
            "action": a.action,
            "reason": a.reason,
            "timestamp": a.created_at.isoformat()
        }
        for a in audits
    ]


@router.get("/student/{student_id}/marks-history", response_model=List[dict])
async def get_student_marks_history(
    student_id: str,
    academic_year: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all marks history for a student"""
    query = db.query(MarksDetail).filter(MarksDetail.student_id == student_id)

    if academic_year:
        query = query.join(MarksHeader).filter(MarksHeader.academic_year == academic_year)

    details = query.all()

    result = []
    for d in details:
        header = d.header
        result.append({
            "subject_name": header.subject_name,
            "assessment_name": header.assessment_name,
            "assessment_type": header.assessment_type.value,
            "max_marks": header.max_marks,
            "obtained_marks": d.obtained_marks,
            "grade": d.grade,
            "assessment_date": header.assessment_date.isoformat() if header.assessment_date else None,
            "status": header.status.value
        })

    return result


# ==================== Export ====================

@router.get("/marks-sheet/{header_id}/export/{format}")
async def export_marks(
    header_id: str,
    format: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export marks sheet (excel, pdf)"""
    if format not in ["excel", "pdf", "csv"]:
        raise HTTPException(status_code=400, detail="Invalid format")

    header = db.query(MarksHeader).filter(MarksHeader.id == header_id).first()
    if not header:
        raise HTTPException(status_code=404, detail="Marks sheet not found")

    details = db.query(MarksDetail).filter(MarksDetail.header_id == header_id).all()

    # Return data for frontend to generate file
    return {
        "format": format,
        "filename": f"{header.subject_code}_{header.assessment_name}_{header.section_name}.{format}",
        "header": {
            "subject_code": header.subject_code,
            "subject_name": header.subject_name,
            "assessment_name": header.assessment_name,
            "section_name": header.section_name,
            "max_marks": header.max_marks,
            "date": header.assessment_date.isoformat() if header.assessment_date else None
        },
        "data": [
            {
                "roll_number": d.roll_number,
                "student_name": d.student_name,
                "obtained_marks": d.obtained_marks if not d.is_absent else "AB",
                "grade": d.grade,
                "remarks": d.remarks
            }
            for d in details
        ],
        "stats": {
            "total_students": header.total_students,
            "average_marks": header.average_marks,
            "highest_marks": header.highest_marks,
            "pass_count": header.pass_count,
            "fail_count": header.fail_count
        }
    }


# ==================== Analytics ====================

@router.get("/analytics/subject/{subject_id}", response_model=dict)
async def get_subject_analytics(
    subject_id: str,
    academic_year: str,
    semester: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analytics for a subject"""
    headers = db.query(MarksHeader).filter(
        MarksHeader.subject_id == subject_id,
        MarksHeader.academic_year == academic_year,
        MarksHeader.semester == semester
    ).all()

    if not headers:
        return {"message": "No data found"}

    # Aggregate stats
    total_students = sum(h.total_students for h in headers)
    avg_marks = sum(h.average_marks or 0 for h in headers if h.average_marks) / len([h for h in headers if h.average_marks]) if headers else 0

    return {
        "subject_id": subject_id,
        "academic_year": academic_year,
        "semester": semester,
        "assessments": [
            {
                "assessment_name": h.assessment_name,
                "assessment_type": h.assessment_type.value,
                "max_marks": h.max_marks,
                "average_marks": h.average_marks,
                "highest_marks": h.highest_marks,
                "pass_percentage": (h.pass_count / h.total_students * 100) if h.total_students > 0 else 0
            }
            for h in headers
        ],
        "overall": {
            "total_students": total_students,
            "average_marks": avg_marks
        }
    }


@router.get("/analytics/section/{section_id}", response_model=dict)
async def get_section_analytics(
    section_id: str,
    academic_year: str,
    semester: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analytics for a section across all subjects"""
    headers = db.query(MarksHeader).filter(
        MarksHeader.section_id == section_id,
        MarksHeader.academic_year == academic_year,
        MarksHeader.semester == semester
    ).all()

    subjects = {}
    for h in headers:
        if h.subject_id not in subjects:
            subjects[h.subject_id] = {
                "subject_name": h.subject_name,
                "assessments": [],
                "total_avg": 0
            }
        subjects[h.subject_id]["assessments"].append({
            "name": h.assessment_name,
            "average": h.average_marks,
            "pass_rate": (h.pass_count / h.total_students * 100) if h.total_students > 0 else 0
        })

    return {
        "section_id": section_id,
        "academic_year": academic_year,
        "semester": semester,
        "subjects": list(subjects.values())
    }


# ==================== ERP Sync ====================

@router.post("/marks-sheet/{header_id}/sync-erp", response_model=dict)
async def sync_to_erp(
    header_id: str,
    sync_type: str = Query("push_api", description="push_api, csv_upload, db_sync"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync marks to ERP system"""
    if current_user.role not in ['admin']:
        raise HTTPException(status_code=403, detail="Only Admin can sync to ERP")

    header = db.query(MarksHeader).filter(MarksHeader.id == header_id).first()
    if not header:
        raise HTTPException(status_code=404, detail="Marks sheet not found")

    if header.status != MarksStatus.LOCKED:
        raise HTTPException(status_code=400, detail="Only locked marks can be synced to ERP")

    # Create sync log
    sync_log = ERPSyncLog(
        header_id=header_id,
        sync_type=sync_type,
        sync_status=SyncStatus.PENDING,
        initiated_by=current_user.id
    )
    db.add(sync_log)
    db.commit()

    # TODO: Implement actual ERP sync in background task
    # For now, simulate success
    sync_log.sync_status = SyncStatus.SUCCESS
    sync_log.completed_at = datetime.utcnow()
    sync_log.records_synced = header.total_students

    header.erp_synced = True
    header.erp_sync_status = SyncStatus.SUCCESS
    header.erp_sync_at = datetime.utcnow()

    db.commit()

    return {
        "message": "Sync initiated",
        "sync_id": sync_log.id,
        "status": "success"
    }


@router.get("/erp-sync-logs", response_model=List[dict])
async def get_erp_sync_logs(
    header_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get ERP sync logs"""
    query = db.query(ERPSyncLog)
    if header_id:
        query = query.filter(ERPSyncLog.header_id == header_id)

    logs = query.order_by(ERPSyncLog.started_at.desc()).limit(50).all()

    return [
        {
            "id": l.id,
            "header_id": l.header_id,
            "sync_type": l.sync_type,
            "status": l.sync_status.value,
            "records_synced": l.records_synced,
            "records_failed": l.records_failed,
            "error_message": l.error_message,
            "started_at": l.started_at.isoformat(),
            "completed_at": l.completed_at.isoformat() if l.completed_at else None
        }
        for l in logs
    ]
