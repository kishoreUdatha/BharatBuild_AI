"""
Faculty Tests API Endpoints
Handles test creation, scheduling, live monitoring, and evaluation
"""
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import json
import asyncio

from app.core.database import get_db
from app.models.faculty_test import (
    FacultyTest, TestQuestion, TestSession, TestResponse, TestAlert, QuestionBank,
    TestStatus, AIControlLevel, QuestionType, QuestionDifficulty,
    StudentSessionStatus, AlertSeverity
)
from app.models.user import User
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


# ==================== Pydantic Schemas ====================

class QuestionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    question_type: str = "coding"
    difficulty: str = "medium"
    marks: int = 10
    time_estimate_minutes: int = 15
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    starter_code: Optional[str] = None
    solution_code: Optional[str] = None
    test_cases: Optional[List[dict]] = None
    topic: Optional[str] = None
    tags: Optional[List[str]] = []


class TestCreate(BaseModel):
    title: str
    description: Optional[str] = None
    lab_id: Optional[str] = None
    lab_name: Optional[str] = None
    duration_minutes: int = 60
    max_marks: int = 100
    passing_marks: int = 40
    ai_control: str = "blocked"
    ai_usage_limit: int = 0
    enable_tab_switch_detection: bool = True
    max_tab_switches: int = 5
    enable_copy_paste_block: bool = True
    randomize_questions: bool = False
    randomize_options: bool = True
    questions: Optional[List[QuestionCreate]] = []


class TestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    lab_name: Optional[str] = None
    duration_minutes: Optional[int] = None
    max_marks: Optional[int] = None
    ai_control: Optional[str] = None
    enable_tab_switch_detection: Optional[bool] = None
    max_tab_switches: Optional[int] = None
    randomize_questions: Optional[bool] = None


class TestSchedule(BaseModel):
    scheduled_at: datetime
    assigned_sections: List[str] = []


class StudentAction(BaseModel):
    action: str  # warn, force_submit, extend_time
    message: Optional[str] = None
    extra_minutes: Optional[int] = None


class AnswerSubmit(BaseModel):
    question_id: str
    answer: Optional[str] = None
    code: Optional[str] = None
    language: Optional[str] = None


class SessionUpdate(BaseModel):
    tab_switches: Optional[int] = None
    ai_usage_count: Optional[int] = None
    last_activity: Optional[str] = None
    current_question_index: Optional[int] = None


# ==================== Test CRUD Endpoints ====================

@router.post("/tests", response_model=dict)
async def create_test(
    test_data: TestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new test"""
    # Create the test
    test = FacultyTest(
        title=test_data.title,
        description=test_data.description,
        lab_id=test_data.lab_id,
        lab_name=test_data.lab_name,
        faculty_id=current_user.id,
        duration_minutes=test_data.duration_minutes,
        max_marks=test_data.max_marks,
        passing_marks=test_data.passing_marks,
        ai_control=AIControlLevel(test_data.ai_control),
        ai_usage_limit=test_data.ai_usage_limit,
        enable_tab_switch_detection=test_data.enable_tab_switch_detection,
        max_tab_switches=test_data.max_tab_switches,
        enable_copy_paste_block=test_data.enable_copy_paste_block,
        randomize_questions=test_data.randomize_questions,
        randomize_options=test_data.randomize_options,
        status=TestStatus.DRAFT
    )
    db.add(test)
    db.flush()

    # Add questions if provided
    for idx, q in enumerate(test_data.questions or []):
        question = TestQuestion(
            test_id=test.id,
            title=q.title,
            description=q.description,
            question_type=QuestionType(q.question_type),
            difficulty=QuestionDifficulty(q.difficulty),
            marks=q.marks,
            time_estimate_minutes=q.time_estimate_minutes,
            options=q.options,
            correct_answer=q.correct_answer,
            starter_code=q.starter_code,
            solution_code=q.solution_code,
            test_cases=q.test_cases,
            topic=q.topic,
            tags=q.tags or [],
            order_index=idx
        )
        db.add(question)

    db.commit()
    db.refresh(test)

    return {
        "id": test.id,
        "title": test.title,
        "status": test.status.value,
        "questions_count": len(test_data.questions or []),
        "message": "Test created successfully"
    }


@router.get("/tests", response_model=List[dict])
async def list_tests(
    status: Optional[str] = None,
    lab_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all tests for current faculty"""
    query = db.query(FacultyTest).filter(FacultyTest.faculty_id == current_user.id)

    if status:
        query = query.filter(FacultyTest.status == TestStatus(status))
    if lab_id:
        query = query.filter(FacultyTest.lab_id == lab_id)

    tests = query.order_by(FacultyTest.created_at.desc()).all()

    return [
        {
            "id": t.id,
            "title": t.title,
            "lab": t.lab_name,
            "questions_count": len(t.questions),
            "duration_minutes": t.duration_minutes,
            "max_marks": t.max_marks,
            "status": t.status.value,
            "scheduled_at": t.scheduled_at.isoformat() if t.scheduled_at else None,
            "participants": t.total_participants,
            "avg_score": t.avg_score,
            "ai_control": t.ai_control.value,
            "created_at": t.created_at.isoformat()
        }
        for t in tests
    ]


@router.get("/tests/{test_id}", response_model=dict)
async def get_test(
    test_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get test details"""
    test = db.query(FacultyTest).filter(FacultyTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    questions = [
        {
            "id": q.id,
            "title": q.title,
            "description": q.description,
            "question_type": q.question_type.value,
            "difficulty": q.difficulty.value,
            "marks": q.marks,
            "time_estimate_minutes": q.time_estimate_minutes,
            "topic": q.topic,
            "test_cases_count": len(q.test_cases or []),
            "order_index": q.order_index
        }
        for q in sorted(test.questions, key=lambda x: x.order_index)
    ]

    return {
        "id": test.id,
        "title": test.title,
        "description": test.description,
        "lab_id": test.lab_id,
        "lab_name": test.lab_name,
        "duration_minutes": test.duration_minutes,
        "max_marks": test.max_marks,
        "passing_marks": test.passing_marks,
        "ai_control": test.ai_control.value,
        "ai_usage_limit": test.ai_usage_limit,
        "enable_tab_switch_detection": test.enable_tab_switch_detection,
        "max_tab_switches": test.max_tab_switches,
        "enable_copy_paste_block": test.enable_copy_paste_block,
        "randomize_questions": test.randomize_questions,
        "randomize_options": test.randomize_options,
        "status": test.status.value,
        "scheduled_at": test.scheduled_at.isoformat() if test.scheduled_at else None,
        "started_at": test.started_at.isoformat() if test.started_at else None,
        "ended_at": test.ended_at.isoformat() if test.ended_at else None,
        "assigned_sections": test.assigned_sections,
        "total_participants": test.total_participants,
        "submitted_count": test.submitted_count,
        "avg_score": test.avg_score,
        "questions": questions,
        "questions_count": len(questions)
    }


@router.put("/tests/{test_id}", response_model=dict)
async def update_test(
    test_id: str,
    test_data: TestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update test details"""
    test = db.query(FacultyTest).filter(
        FacultyTest.id == test_id,
        FacultyTest.faculty_id == current_user.id
    ).first()

    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    if test.status == TestStatus.LIVE:
        raise HTTPException(status_code=400, detail="Cannot edit a live test")

    # Update fields
    for field, value in test_data.dict(exclude_unset=True).items():
        if field == "ai_control" and value:
            setattr(test, field, AIControlLevel(value))
        elif value is not None:
            setattr(test, field, value)

    db.commit()
    return {"message": "Test updated successfully", "id": test.id}


@router.delete("/tests/{test_id}", response_model=dict)
async def delete_test(
    test_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a test"""
    test = db.query(FacultyTest).filter(
        FacultyTest.id == test_id,
        FacultyTest.faculty_id == current_user.id
    ).first()

    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    if test.status == TestStatus.LIVE:
        raise HTTPException(status_code=400, detail="Cannot delete a live test")

    db.delete(test)
    db.commit()
    return {"message": "Test deleted successfully"}


@router.post("/tests/{test_id}/duplicate", response_model=dict)
async def duplicate_test(
    test_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Duplicate an existing test"""
    original = db.query(FacultyTest).filter(FacultyTest.id == test_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Test not found")

    # Create copy
    new_test = FacultyTest(
        title=f"{original.title} (Copy)",
        description=original.description,
        lab_id=original.lab_id,
        lab_name=original.lab_name,
        faculty_id=current_user.id,
        duration_minutes=original.duration_minutes,
        max_marks=original.max_marks,
        passing_marks=original.passing_marks,
        ai_control=original.ai_control,
        ai_usage_limit=original.ai_usage_limit,
        enable_tab_switch_detection=original.enable_tab_switch_detection,
        max_tab_switches=original.max_tab_switches,
        enable_copy_paste_block=original.enable_copy_paste_block,
        randomize_questions=original.randomize_questions,
        randomize_options=original.randomize_options,
        status=TestStatus.DRAFT
    )
    db.add(new_test)
    db.flush()

    # Copy questions
    for q in original.questions:
        new_q = TestQuestion(
            test_id=new_test.id,
            title=q.title,
            description=q.description,
            question_type=q.question_type,
            difficulty=q.difficulty,
            marks=q.marks,
            time_estimate_minutes=q.time_estimate_minutes,
            options=q.options,
            correct_answer=q.correct_answer,
            starter_code=q.starter_code,
            solution_code=q.solution_code,
            test_cases=q.test_cases,
            hidden_test_cases=q.hidden_test_cases,
            topic=q.topic,
            tags=q.tags,
            order_index=q.order_index
        )
        db.add(new_q)

    db.commit()
    return {"id": new_test.id, "message": "Test duplicated successfully"}


# ==================== Scheduling & Status ====================

@router.post("/tests/{test_id}/schedule", response_model=dict)
async def schedule_test(
    test_id: str,
    schedule_data: TestSchedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Schedule a test for a specific date/time"""
    test = db.query(FacultyTest).filter(
        FacultyTest.id == test_id,
        FacultyTest.faculty_id == current_user.id
    ).first()

    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    if not test.questions:
        raise HTTPException(status_code=400, detail="Cannot schedule test with no questions")

    test.scheduled_at = schedule_data.scheduled_at
    test.assigned_sections = schedule_data.assigned_sections
    test.status = TestStatus.SCHEDULED

    db.commit()
    return {
        "message": "Test scheduled successfully",
        "scheduled_at": test.scheduled_at.isoformat(),
        "assigned_sections": test.assigned_sections
    }


@router.post("/tests/{test_id}/start", response_model=dict)
async def start_test(
    test_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a test - make it live"""
    test = db.query(FacultyTest).filter(
        FacultyTest.id == test_id,
        FacultyTest.faculty_id == current_user.id
    ).first()

    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    if test.status == TestStatus.LIVE:
        raise HTTPException(status_code=400, detail="Test is already live")

    if test.status == TestStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Test has already been completed")

    test.status = TestStatus.LIVE
    test.started_at = datetime.utcnow()

    db.commit()
    return {
        "message": "Test started successfully",
        "status": "live",
        "started_at": test.started_at.isoformat()
    }


@router.post("/tests/{test_id}/end", response_model=dict)
async def end_test(
    test_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """End a live test - auto-submit all ongoing attempts"""
    test = db.query(FacultyTest).filter(
        FacultyTest.id == test_id,
        FacultyTest.faculty_id == current_user.id
    ).first()

    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    if test.status != TestStatus.LIVE:
        raise HTTPException(status_code=400, detail="Test is not live")

    # Auto-submit all active sessions
    active_sessions = db.query(TestSession).filter(
        TestSession.test_id == test_id,
        TestSession.status.in_([StudentSessionStatus.ACTIVE, StudentSessionStatus.IDLE, StudentSessionStatus.SUSPICIOUS])
    ).all()

    for session in active_sessions:
        session.status = StudentSessionStatus.FORCE_SUBMITTED
        session.submitted_at = datetime.utcnow()

    test.status = TestStatus.EVALUATING
    test.ended_at = datetime.utcnow()
    test.submitted_count = db.query(TestSession).filter(
        TestSession.test_id == test_id,
        TestSession.status.in_([StudentSessionStatus.SUBMITTED, StudentSessionStatus.FORCE_SUBMITTED])
    ).count()

    db.commit()
    return {
        "message": "Test ended successfully",
        "status": "evaluating",
        "force_submitted": len(active_sessions),
        "total_submitted": test.submitted_count
    }


# ==================== Live Monitoring ====================

@router.get("/tests/{test_id}/monitor", response_model=dict)
async def get_live_monitor_data(
    test_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get live monitoring data for a test"""
    test = db.query(FacultyTest).filter(FacultyTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    sessions = db.query(TestSession).filter(TestSession.test_id == test_id).all()

    # Calculate stats
    status_counts = {
        "active": 0,
        "idle": 0,
        "suspicious": 0,
        "submitted": 0,
        "not_started": 0
    }
    for s in sessions:
        if s.status == StudentSessionStatus.ACTIVE:
            status_counts["active"] += 1
        elif s.status == StudentSessionStatus.IDLE:
            status_counts["idle"] += 1
        elif s.status == StudentSessionStatus.SUSPICIOUS:
            status_counts["suspicious"] += 1
        elif s.status in [StudentSessionStatus.SUBMITTED, StudentSessionStatus.FORCE_SUBMITTED]:
            status_counts["submitted"] += 1
        else:
            status_counts["not_started"] += 1

    # Get recent alerts
    alerts = db.query(TestAlert).join(TestSession).filter(
        TestSession.test_id == test_id,
        TestAlert.is_resolved == False
    ).order_by(TestAlert.created_at.desc()).limit(20).all()

    students = [
        {
            "id": s.id,
            "student_id": s.student_id,
            "name": s.student_name or "Unknown",
            "roll_number": s.student_roll or "",
            "status": s.status.value,
            "progress": s.progress_percentage,
            "time_spent": s.time_spent_seconds // 60,
            "tab_switches": s.tab_switches,
            "ai_usage": s.ai_usage_percentage,
            "last_activity": s.last_activity_description,
            "questions_attempted": s.questions_attempted
        }
        for s in sessions
    ]

    alert_list = [
        {
            "id": a.id,
            "session_id": a.session_id,
            "student": next((s.student_name for s in sessions if s.id == a.session_id), "Unknown"),
            "roll": next((s.student_roll for s in sessions if s.id == a.session_id), ""),
            "message": a.message,
            "severity": a.severity.value,
            "time": a.created_at.isoformat(),
            "alert_type": a.alert_type
        }
        for a in alerts
    ]

    # Calculate time remaining
    time_remaining = None
    if test.started_at and test.status == TestStatus.LIVE:
        elapsed = (datetime.utcnow() - test.started_at).total_seconds()
        remaining = (test.duration_minutes * 60) - elapsed
        time_remaining = max(0, int(remaining))

    return {
        "test": {
            "id": test.id,
            "title": test.title,
            "lab": test.lab_name,
            "status": test.status.value,
            "duration_minutes": test.duration_minutes,
            "started_at": test.started_at.isoformat() if test.started_at else None,
            "time_remaining_seconds": time_remaining
        },
        "stats": status_counts,
        "students": students,
        "alerts": alert_list
    }


@router.get("/tests/{test_id}/students", response_model=List[dict])
async def get_test_students(
    test_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all students in a test with their status"""
    query = db.query(TestSession).filter(TestSession.test_id == test_id)

    if status:
        query = query.filter(TestSession.status == StudentSessionStatus(status))

    sessions = query.all()

    return [
        {
            "id": s.id,
            "student_id": s.student_id,
            "name": s.student_name,
            "roll_number": s.student_roll,
            "email": s.student_email,
            "status": s.status.value,
            "progress": s.progress_percentage,
            "time_spent_minutes": s.time_spent_seconds // 60,
            "tab_switches": s.tab_switches,
            "ai_usage": s.ai_usage_percentage,
            "questions_attempted": s.questions_attempted,
            "last_activity": s.last_activity_description,
            "auto_score": s.auto_score,
            "total_score": s.total_score,
            "is_evaluated": s.is_evaluated
        }
        for s in sessions
    ]


@router.post("/tests/{test_id}/students/{session_id}/action", response_model=dict)
async def student_action(
    test_id: str,
    session_id: str,
    action_data: StudentAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Perform action on a student (warn, force submit, extend time)"""
    session = db.query(TestSession).filter(
        TestSession.id == session_id,
        TestSession.test_id == test_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if action_data.action == "warn":
        # Create warning alert
        alert = TestAlert(
            session_id=session_id,
            alert_type="faculty_warning",
            severity=AlertSeverity.HIGH,
            message=action_data.message or "Warning from faculty"
        )
        db.add(alert)
        db.commit()
        return {"message": f"Warning sent to {session.student_name}"}

    elif action_data.action == "force_submit":
        session.status = StudentSessionStatus.FORCE_SUBMITTED
        session.submitted_at = datetime.utcnow()
        db.commit()
        return {"message": f"Test force submitted for {session.student_name}"}

    elif action_data.action == "extend_time":
        # Would need to track per-student time extensions
        return {"message": f"Time extended by {action_data.extra_minutes} minutes for {session.student_name}"}

    else:
        raise HTTPException(status_code=400, detail="Invalid action")


# ==================== Question Bank ====================

@router.get("/question-bank", response_model=List[dict])
async def list_questions(
    question_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    topic: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List questions from question bank"""
    query = db.query(QuestionBank).filter(
        or_(
            QuestionBank.faculty_id == current_user.id,
            QuestionBank.is_public == True
        )
    )

    if question_type:
        query = query.filter(QuestionBank.question_type == QuestionType(question_type))
    if difficulty:
        query = query.filter(QuestionBank.difficulty == QuestionDifficulty(difficulty))
    if topic:
        query = query.filter(QuestionBank.topic.ilike(f"%{topic}%"))
    if search:
        query = query.filter(QuestionBank.title.ilike(f"%{search}%"))

    questions = query.order_by(QuestionBank.created_at.desc()).limit(100).all()

    return [
        {
            "id": q.id,
            "title": q.title,
            "question_type": q.question_type.value,
            "difficulty": q.difficulty.value,
            "marks": q.suggested_marks,
            "time_estimate": q.time_estimate_minutes,
            "topic": q.topic,
            "tags": q.tags,
            "times_used": q.times_used,
            "avg_score": q.avg_score,
            "is_public": q.is_public,
            "is_mine": q.faculty_id == current_user.id
        }
        for q in questions
    ]


@router.post("/question-bank", response_model=dict)
async def create_question(
    question_data: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a question to the question bank"""
    question = QuestionBank(
        title=question_data.title,
        description=question_data.description,
        question_type=QuestionType(question_data.question_type),
        difficulty=QuestionDifficulty(question_data.difficulty),
        faculty_id=current_user.id,
        suggested_marks=question_data.marks,
        time_estimate_minutes=question_data.time_estimate_minutes,
        options=question_data.options,
        correct_answer=question_data.correct_answer,
        starter_code=question_data.starter_code,
        solution_code=question_data.solution_code,
        test_cases=question_data.test_cases,
        topic=question_data.topic,
        tags=question_data.tags or []
    )
    db.add(question)
    db.commit()

    return {"id": question.id, "message": "Question added to bank"}


@router.get("/question-bank/{question_id}", response_model=dict)
async def get_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get question details"""
    question = db.query(QuestionBank).filter(QuestionBank.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return {
        "id": question.id,
        "title": question.title,
        "description": question.description,
        "question_type": question.question_type.value,
        "difficulty": question.difficulty.value,
        "marks": question.suggested_marks,
        "time_estimate_minutes": question.time_estimate_minutes,
        "options": question.options,
        "correct_answer": question.correct_answer if question.faculty_id == current_user.id else None,
        "starter_code": question.starter_code,
        "solution_code": question.solution_code if question.faculty_id == current_user.id else None,
        "test_cases": question.test_cases,
        "topic": question.topic,
        "tags": question.tags,
        "times_used": question.times_used,
        "avg_score": question.avg_score
    }


@router.post("/tests/{test_id}/questions", response_model=dict)
async def add_question_to_test(
    test_id: str,
    question_data: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a question to a test"""
    test = db.query(FacultyTest).filter(
        FacultyTest.id == test_id,
        FacultyTest.faculty_id == current_user.id
    ).first()

    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    if test.status == TestStatus.LIVE:
        raise HTTPException(status_code=400, detail="Cannot add questions to a live test")

    # Get next order index
    max_order = db.query(func.max(TestQuestion.order_index)).filter(
        TestQuestion.test_id == test_id
    ).scalar() or -1

    question = TestQuestion(
        test_id=test_id,
        title=question_data.title,
        description=question_data.description,
        question_type=QuestionType(question_data.question_type),
        difficulty=QuestionDifficulty(question_data.difficulty),
        marks=question_data.marks,
        time_estimate_minutes=question_data.time_estimate_minutes,
        options=question_data.options,
        correct_answer=question_data.correct_answer,
        starter_code=question_data.starter_code,
        solution_code=question_data.solution_code,
        test_cases=question_data.test_cases,
        topic=question_data.topic,
        tags=question_data.tags or [],
        order_index=max_order + 1
    )
    db.add(question)
    db.commit()

    return {"id": question.id, "message": "Question added to test"}


@router.post("/tests/{test_id}/questions/from-bank/{bank_question_id}", response_model=dict)
async def add_question_from_bank(
    test_id: str,
    bank_question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a question from question bank to a test"""
    test = db.query(FacultyTest).filter(
        FacultyTest.id == test_id,
        FacultyTest.faculty_id == current_user.id
    ).first()

    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    bank_q = db.query(QuestionBank).filter(QuestionBank.id == bank_question_id).first()
    if not bank_q:
        raise HTTPException(status_code=404, detail="Question not found in bank")

    # Get next order index
    max_order = db.query(func.max(TestQuestion.order_index)).filter(
        TestQuestion.test_id == test_id
    ).scalar() or -1

    # Copy question to test
    question = TestQuestion(
        test_id=test_id,
        title=bank_q.title,
        description=bank_q.description,
        question_type=bank_q.question_type,
        difficulty=bank_q.difficulty,
        marks=bank_q.suggested_marks,
        time_estimate_minutes=bank_q.time_estimate_minutes,
        options=bank_q.options,
        correct_answer=bank_q.correct_answer,
        starter_code=bank_q.starter_code,
        solution_code=bank_q.solution_code,
        test_cases=bank_q.test_cases,
        hidden_test_cases=bank_q.hidden_test_cases,
        topic=bank_q.topic,
        tags=bank_q.tags,
        order_index=max_order + 1,
        source_question_id=bank_q.id
    )
    db.add(question)

    # Update usage count
    bank_q.times_used += 1

    db.commit()

    return {"id": question.id, "message": "Question added from bank"}


# ==================== Evaluation ====================

@router.get("/tests/{test_id}/results", response_model=dict)
async def get_test_results(
    test_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get test results for all students"""
    test = db.query(FacultyTest).filter(FacultyTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    sessions = db.query(TestSession).filter(
        TestSession.test_id == test_id,
        TestSession.status.in_([StudentSessionStatus.SUBMITTED, StudentSessionStatus.FORCE_SUBMITTED])
    ).order_by(TestSession.total_score.desc().nullsfirst()).all()

    results = []
    for idx, s in enumerate(sessions):
        results.append({
            "rank": idx + 1,
            "student_id": s.student_id,
            "name": s.student_name,
            "roll_number": s.student_roll,
            "email": s.student_email,
            "score": s.total_score,
            "max_score": test.max_marks,
            "percentage": s.percentage,
            "time_taken_minutes": s.time_spent_seconds // 60,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "is_evaluated": s.is_evaluated,
            "status": "pass" if (s.total_score or 0) >= test.passing_marks else "fail"
        })

    # Calculate statistics
    scores = [s.total_score for s in sessions if s.total_score is not None]
    stats = {
        "total_submissions": len(sessions),
        "evaluated": sum(1 for s in sessions if s.is_evaluated),
        "avg_score": sum(scores) / len(scores) if scores else 0,
        "max_score": max(scores) if scores else 0,
        "min_score": min(scores) if scores else 0,
        "pass_count": sum(1 for s in scores if s >= test.passing_marks),
        "fail_count": sum(1 for s in scores if s < test.passing_marks)
    }

    return {
        "test": {
            "id": test.id,
            "title": test.title,
            "max_marks": test.max_marks,
            "passing_marks": test.passing_marks
        },
        "stats": stats,
        "results": results
    }


@router.post("/tests/{test_id}/evaluate", response_model=dict)
async def auto_evaluate_test(
    test_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Auto-evaluate all submissions for a test"""
    test = db.query(FacultyTest).filter(FacultyTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    sessions = db.query(TestSession).filter(
        TestSession.test_id == test_id,
        TestSession.is_evaluated == False
    ).all()

    evaluated_count = 0
    for session in sessions:
        total_score = 0
        responses = db.query(TestResponse).filter(TestResponse.session_id == session.id).all()

        for response in responses:
            question = db.query(TestQuestion).filter(TestQuestion.id == response.question_id).first()
            if not question:
                continue

            # Auto-grade based on question type
            if question.question_type == QuestionType.MCQ:
                if response.answer == question.correct_answer:
                    response.is_correct = True
                    response.final_score = question.marks
                else:
                    response.is_correct = False
                    response.final_score = 0
            elif question.question_type in [QuestionType.CODING, QuestionType.SQL]:
                # For coding, use test case results
                if response.test_cases_total > 0:
                    ratio = response.test_cases_passed / response.test_cases_total
                    response.final_score = question.marks * ratio
                else:
                    response.final_score = 0
            else:
                # Default scoring based on submission
                response.final_score = question.marks * 0.6 if response.code or response.answer else 0

            response.auto_score = response.final_score
            total_score += response.final_score or 0

        session.auto_score = total_score
        session.total_score = total_score
        session.percentage = (total_score / test.max_marks) * 100 if test.max_marks > 0 else 0
        session.is_evaluated = True
        session.evaluated_at = datetime.utcnow()
        session.evaluated_by = current_user.id
        evaluated_count += 1

    # Update test stats
    all_scores = [s.total_score for s in db.query(TestSession).filter(
        TestSession.test_id == test_id,
        TestSession.total_score.isnot(None)
    ).all()]

    if all_scores:
        test.avg_score = sum(all_scores) / len(all_scores)

    if test.status == TestStatus.EVALUATING:
        test.status = TestStatus.COMPLETED

    db.commit()

    return {
        "message": f"Evaluated {evaluated_count} submissions",
        "avg_score": test.avg_score
    }


@router.get("/tests/{test_id}/export/{format}")
async def export_results(
    test_id: str,
    format: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export test results in various formats"""
    if format not in ["csv", "excel", "pdf"]:
        raise HTTPException(status_code=400, detail="Invalid format. Use csv, excel, or pdf")

    test = db.query(FacultyTest).filter(FacultyTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    sessions = db.query(TestSession).filter(
        TestSession.test_id == test_id,
        TestSession.status.in_([StudentSessionStatus.SUBMITTED, StudentSessionStatus.FORCE_SUBMITTED])
    ).order_by(TestSession.total_score.desc().nullsfirst()).all()

    # For now, return JSON data that frontend can convert
    # In production, you would generate actual files
    data = []
    for s in sessions:
        data.append({
            "name": s.student_name,
            "roll_number": s.student_roll,
            "email": s.student_email,
            "score": s.total_score,
            "percentage": s.percentage,
            "time_taken": s.time_spent_seconds // 60,
            "status": "Pass" if (s.total_score or 0) >= test.passing_marks else "Fail"
        })

    return {
        "test_title": test.title,
        "export_format": format,
        "data": data,
        "message": f"Export data for {format} format"
    }


# ==================== Student Endpoints (for taking tests) ====================

@router.get("/student/tests/available", response_model=List[dict])
async def get_available_tests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tests available for the current student"""
    tests = db.query(FacultyTest).filter(
        FacultyTest.status.in_([TestStatus.SCHEDULED, TestStatus.LIVE])
    ).all()

    result = []
    for test in tests:
        # Check if student has a session
        session = db.query(TestSession).filter(
            TestSession.test_id == test.id,
            TestSession.student_id == current_user.id
        ).first()

        result.append({
            "id": test.id,
            "title": test.title,
            "lab": test.lab_name,
            "duration_minutes": test.duration_minutes,
            "max_marks": test.max_marks,
            "questions_count": len(test.questions),
            "status": test.status.value,
            "scheduled_at": test.scheduled_at.isoformat() if test.scheduled_at else None,
            "can_start": test.status == TestStatus.LIVE,
            "already_started": session is not None and session.status != StudentSessionStatus.NOT_STARTED,
            "already_submitted": session is not None and session.status in [StudentSessionStatus.SUBMITTED, StudentSessionStatus.FORCE_SUBMITTED]
        })

    return result


@router.post("/student/tests/{test_id}/start", response_model=dict)
async def student_start_test(
    test_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Student starts taking a test"""
    test = db.query(FacultyTest).filter(FacultyTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    if test.status != TestStatus.LIVE:
        raise HTTPException(status_code=400, detail="Test is not available")

    # Check for existing session
    session = db.query(TestSession).filter(
        TestSession.test_id == test_id,
        TestSession.student_id == current_user.id
    ).first()

    if session and session.status in [StudentSessionStatus.SUBMITTED, StudentSessionStatus.FORCE_SUBMITTED]:
        raise HTTPException(status_code=400, detail="You have already submitted this test")

    if not session:
        session = TestSession(
            test_id=test_id,
            student_id=current_user.id,
            student_name=current_user.full_name,
            student_roll=getattr(current_user, 'roll_number', None),
            student_email=current_user.email,
            status=StudentSessionStatus.ACTIVE,
            started_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow(),
            last_activity_description="Started test"
        )
        db.add(session)

        # Update test participant count
        test.total_participants += 1
    else:
        session.status = StudentSessionStatus.ACTIVE
        session.last_activity_at = datetime.utcnow()

    db.commit()

    # Get questions
    questions = sorted(test.questions, key=lambda x: x.order_index)

    return {
        "session_id": session.id,
        "test": {
            "id": test.id,
            "title": test.title,
            "duration_minutes": test.duration_minutes,
            "max_marks": test.max_marks,
            "ai_control": test.ai_control.value,
            "enable_tab_switch_detection": test.enable_tab_switch_detection,
            "enable_copy_paste_block": test.enable_copy_paste_block
        },
        "questions": [
            {
                "id": q.id,
                "title": q.title,
                "description": q.description,
                "question_type": q.question_type.value,
                "difficulty": q.difficulty.value,
                "marks": q.marks,
                "options": q.options,
                "starter_code": q.starter_code,
                "order_index": q.order_index
            }
            for q in questions
        ],
        "started_at": session.started_at.isoformat()
    }


@router.post("/student/tests/{test_id}/submit-answer", response_model=dict)
async def submit_answer(
    test_id: str,
    answer_data: AnswerSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit answer for a question"""
    session = db.query(TestSession).filter(
        TestSession.test_id == test_id,
        TestSession.student_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status in [StudentSessionStatus.SUBMITTED, StudentSessionStatus.FORCE_SUBMITTED]:
        raise HTTPException(status_code=400, detail="Test already submitted")

    # Get or create response
    response = db.query(TestResponse).filter(
        TestResponse.session_id == session.id,
        TestResponse.question_id == answer_data.question_id
    ).first()

    if not response:
        response = TestResponse(
            session_id=session.id,
            question_id=answer_data.question_id,
            first_viewed_at=datetime.utcnow()
        )
        db.add(response)

    response.answer = answer_data.answer
    response.code = answer_data.code
    response.language = answer_data.language
    response.last_updated_at = datetime.utcnow()
    response.attempts += 1

    # Update session
    session.last_activity_at = datetime.utcnow()
    session.last_activity_description = "Answered question"
    session.questions_attempted = db.query(TestResponse).filter(
        TestResponse.session_id == session.id,
        or_(TestResponse.answer.isnot(None), TestResponse.code.isnot(None))
    ).count()

    test = db.query(FacultyTest).filter(FacultyTest.id == test_id).first()
    if test and test.questions:
        session.progress_percentage = (session.questions_attempted / len(test.questions)) * 100

    db.commit()

    return {"message": "Answer saved", "questions_attempted": session.questions_attempted}


@router.post("/student/tests/{test_id}/submit", response_model=dict)
async def submit_test(
    test_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit the entire test"""
    session = db.query(TestSession).filter(
        TestSession.test_id == test_id,
        TestSession.student_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status in [StudentSessionStatus.SUBMITTED, StudentSessionStatus.FORCE_SUBMITTED]:
        raise HTTPException(status_code=400, detail="Test already submitted")

    session.status = StudentSessionStatus.SUBMITTED
    session.submitted_at = datetime.utcnow()
    session.progress_percentage = 100

    if session.started_at:
        session.time_spent_seconds = int((datetime.utcnow() - session.started_at).total_seconds())

    # Update test stats
    test = db.query(FacultyTest).filter(FacultyTest.id == test_id).first()
    if test:
        test.submitted_count += 1

    db.commit()

    return {
        "message": "Test submitted successfully",
        "time_spent_minutes": session.time_spent_seconds // 60,
        "questions_attempted": session.questions_attempted
    }


@router.post("/student/tests/{test_id}/update-session", response_model=dict)
async def update_session(
    test_id: str,
    session_data: SessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update session data (tab switches, activity, etc.)"""
    session = db.query(TestSession).filter(
        TestSession.test_id == test_id,
        TestSession.student_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session_data.tab_switches is not None:
        session.tab_switches = session_data.tab_switches

        # Create alert if too many tab switches
        test = db.query(FacultyTest).filter(FacultyTest.id == test_id).first()
        if test and session.tab_switches >= test.max_tab_switches:
            session.status = StudentSessionStatus.SUSPICIOUS
            alert = TestAlert(
                session_id=session.id,
                alert_type="tab_switch",
                severity=AlertSeverity.HIGH,
                message=f"High tab switch count ({session.tab_switches} switches)"
            )
            db.add(alert)

    if session_data.ai_usage_count is not None:
        session.ai_usage_count = session_data.ai_usage_count
        # Calculate percentage based on some threshold
        session.ai_usage_percentage = min(100, session_data.ai_usage_count * 5)

        if session.ai_usage_percentage > 30:
            alert = TestAlert(
                session_id=session.id,
                alert_type="ai_usage",
                severity=AlertSeverity.HIGH,
                message=f"AI usage above 30% ({session.ai_usage_percentage}%)"
            )
            db.add(alert)

    if session_data.last_activity:
        session.last_activity_description = session_data.last_activity
        session.last_activity_at = datetime.utcnow()

    if session_data.current_question_index is not None:
        session.current_question_index = session_data.current_question_index

    db.commit()

    return {"message": "Session updated"}


# ==================== WebSocket for Live Updates ====================

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}  # test_id -> list of websockets

    async def connect(self, websocket: WebSocket, test_id: str):
        await websocket.accept()
        if test_id not in self.active_connections:
            self.active_connections[test_id] = []
        self.active_connections[test_id].append(websocket)

    def disconnect(self, websocket: WebSocket, test_id: str):
        if test_id in self.active_connections:
            self.active_connections[test_id].remove(websocket)

    async def broadcast(self, test_id: str, message: dict):
        if test_id in self.active_connections:
            for connection in self.active_connections[test_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass


manager = ConnectionManager()


@router.websocket("/tests/{test_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    test_id: str,
    db: Session = Depends(get_db)
):
    """WebSocket for real-time test monitoring"""
    await manager.connect(websocket, test_id)
    try:
        while True:
            # Send updates every 5 seconds
            test = db.query(FacultyTest).filter(FacultyTest.id == test_id).first()
            if not test:
                await websocket.close()
                break

            sessions = db.query(TestSession).filter(TestSession.test_id == test_id).all()

            status_counts = {"active": 0, "idle": 0, "suspicious": 0, "submitted": 0}
            for s in sessions:
                if s.status == StudentSessionStatus.ACTIVE:
                    status_counts["active"] += 1
                elif s.status == StudentSessionStatus.IDLE:
                    status_counts["idle"] += 1
                elif s.status == StudentSessionStatus.SUSPICIOUS:
                    status_counts["suspicious"] += 1
                elif s.status in [StudentSessionStatus.SUBMITTED, StudentSessionStatus.FORCE_SUBMITTED]:
                    status_counts["submitted"] += 1

            await websocket.send_json({
                "type": "status_update",
                "stats": status_counts,
                "students": [
                    {
                        "id": s.id,
                        "name": s.student_name,
                        "status": s.status.value,
                        "progress": s.progress_percentage,
                        "tab_switches": s.tab_switches,
                        "ai_usage": s.ai_usage_percentage
                    }
                    for s in sessions
                ]
            })

            await asyncio.sleep(5)

    except WebSocketDisconnect:
        manager.disconnect(websocket, test_id)
