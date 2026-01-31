"""
College Management API Endpoints
- Principal Dashboard
- HOD Dashboard
- Lecturer Dashboard
- Student Management
- Project Oversight
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, get_current_active_user
from app.models.user import User, UserRole
from app.models.college_management import (
    College, Department, Section, Batch, FacultyAssignment,
    StudentSection, StudentProject, ProjectMilestone, CollegeAnnouncement,
    ProjectPhase, CollegeStatus
)

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class CollegeCreate(BaseModel):
    name: str
    code: str
    university: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    email: Optional[str] = None


class DepartmentCreate(BaseModel):
    name: str
    code: str
    hod_name: Optional[str] = None


class DashboardStats(BaseModel):
    total_students: int
    total_faculty: int
    total_departments: int
    total_projects: int
    active_projects: int
    completed_projects: int
    pending_reviews: int
    avg_plagiarism_score: float
    avg_ai_score: float


class StudentOverview(BaseModel):
    id: str
    name: str
    roll_number: str
    department: str
    section: str
    project_title: Optional[str]
    project_phase: Optional[str]
    plagiarism_score: Optional[float]
    ai_score: Optional[float]
    last_activity: Optional[datetime]


class ProjectOverview(BaseModel):
    id: str
    title: str
    student_name: str
    department: str
    phase: str
    progress: int
    guide_name: Optional[str]
    plagiarism_score: Optional[float]
    ai_score: Optional[float]
    last_review: Optional[datetime]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_college_admin(user: User):
    """Check if user has college admin privileges"""
    allowed_roles = [UserRole.PRINCIPAL, UserRole.VICE_PRINCIPAL, UserRole.HOD, UserRole.ADMIN]
    if user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient privileges")


def check_principal(user: User):
    """Check if user is principal or admin"""
    allowed_roles = [UserRole.PRINCIPAL, UserRole.ADMIN]
    if user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only Principal can perform this action")


# ============================================================================
# PRINCIPAL DASHBOARD
# ============================================================================

@router.get("/principal/dashboard")
async def get_principal_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Principal Dashboard - College-wide overview
    Shows all departments, faculty, students, and projects
    """
    check_college_admin(current_user)

    # Get college (for now, use user's college_id or return demo data)
    college_id = current_user.college_id

    # Calculate stats
    # In production, these would be actual database queries
    stats = {
        "overview": {
            "total_students": 1250,
            "total_faculty": 85,
            "total_departments": 8,
            "total_sections": 32,
            "active_batches": 4
        },
        "projects": {
            "total": 450,
            "active": 280,
            "completed": 150,
            "pending_review": 45,
            "overdue": 12
        },
        "compliance": {
            "avg_plagiarism_score": 8.5,  # Lower is better
            "avg_ai_detection": 15.2,      # Lower is better
            "passing_plagiarism": 92,      # % under 10%
            "passing_ai": 88               # % under 20%
        },
        "departments": [
            {"name": "Computer Science", "code": "CSE", "students": 320, "faculty": 22, "projects": 120, "hod": "Dr. Rajesh Kumar"},
            {"name": "Electronics", "code": "ECE", "students": 280, "faculty": 18, "projects": 95, "hod": "Dr. Priya Sharma"},
            {"name": "Mechanical", "code": "MECH", "students": 250, "faculty": 16, "projects": 85, "hod": "Dr. Suresh Reddy"},
            {"name": "Civil", "code": "CIVIL", "students": 200, "faculty": 14, "projects": 70, "hod": "Dr. Anita Rao"},
            {"name": "Information Technology", "code": "IT", "students": 200, "faculty": 15, "projects": 80, "hod": "Dr. Venkat Krishna"}
        ],
        "recent_activities": [
            {"type": "project_submitted", "message": "Rahul submitted final project for review", "department": "CSE", "time": "2 hours ago"},
            {"type": "review_completed", "message": "Dr. Priya reviewed 5 projects", "department": "ECE", "time": "4 hours ago"},
            {"type": "milestone_achieved", "message": "15 students completed documentation phase", "department": "IT", "time": "Today"},
            {"type": "alert", "message": "3 projects flagged for high plagiarism", "department": "MECH", "time": "Yesterday"}
        ],
        "announcements": [
            {"title": "Project Submission Deadline", "content": "Final year project submissions due by March 15", "priority": "high", "date": "2024-02-01"},
            {"title": "Review Schedule", "content": "Mid-semester reviews scheduled for Feb 20-25", "priority": "normal", "date": "2024-02-05"}
        ]
    }

    return {
        "role": "principal",
        "college": {
            "name": current_user.college_name or "Engineering College",
            "code": "EC001"
        },
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/principal/departments")
async def get_all_departments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all departments with details"""
    check_college_admin(current_user)

    departments = [
        {
            "id": "dept-1",
            "name": "Computer Science and Engineering",
            "code": "CSE",
            "hod": {"name": "Dr. Rajesh Kumar", "email": "rajesh@college.edu", "phone": "9876543210"},
            "stats": {
                "total_students": 320,
                "total_faculty": 22,
                "sections": ["A", "B", "C", "D"],
                "active_projects": 120,
                "avg_plagiarism": 7.5,
                "avg_ai_detection": 14.2
            }
        },
        {
            "id": "dept-2",
            "name": "Electronics and Communication",
            "code": "ECE",
            "hod": {"name": "Dr. Priya Sharma", "email": "priya@college.edu", "phone": "9876543211"},
            "stats": {
                "total_students": 280,
                "total_faculty": 18,
                "sections": ["A", "B", "C"],
                "active_projects": 95,
                "avg_plagiarism": 9.2,
                "avg_ai_detection": 16.8
            }
        },
        {
            "id": "dept-3",
            "name": "Mechanical Engineering",
            "code": "MECH",
            "hod": {"name": "Dr. Suresh Reddy", "email": "suresh@college.edu", "phone": "9876543212"},
            "stats": {
                "total_students": 250,
                "total_faculty": 16,
                "sections": ["A", "B", "C"],
                "active_projects": 85,
                "avg_plagiarism": 8.8,
                "avg_ai_detection": 15.5
            }
        }
    ]

    return {"departments": departments, "total": len(departments)}


@router.get("/principal/faculty")
async def get_all_faculty(
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all faculty members"""
    check_college_admin(current_user)

    faculty = [
        {"id": "f1", "name": "Dr. Rajesh Kumar", "department": "CSE", "designation": "Professor & HOD", "email": "rajesh@college.edu", "students_guided": 8, "specialization": "Machine Learning"},
        {"id": "f2", "name": "Dr. Priya Sharma", "department": "ECE", "designation": "Professor & HOD", "email": "priya@college.edu", "students_guided": 6, "specialization": "VLSI Design"},
        {"id": "f3", "name": "Mr. Anil Verma", "department": "CSE", "designation": "Asst. Professor", "email": "anil@college.edu", "students_guided": 5, "specialization": "Web Development"},
        {"id": "f4", "name": "Ms. Sneha Gupta", "department": "CSE", "designation": "Asst. Professor", "email": "sneha@college.edu", "students_guided": 4, "specialization": "Data Science"},
        {"id": "f5", "name": "Dr. Venkat Krishna", "department": "IT", "designation": "Professor & HOD", "email": "venkat@college.edu", "students_guided": 7, "specialization": "Cloud Computing"}
    ]

    if department:
        faculty = [f for f in faculty if f["department"].lower() == department.lower()]

    return {"faculty": faculty, "total": len(faculty)}


# ============================================================================
# HOD DASHBOARD
# ============================================================================

@router.get("/hod/dashboard")
async def get_hod_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    HOD Dashboard - Department-specific overview
    Shows department faculty, students, and project status
    """
    allowed_roles = [UserRole.HOD, UserRole.PRINCIPAL, UserRole.ADMIN]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied")

    department = current_user.department or "Computer Science"

    stats = {
        "department": {
            "name": department,
            "code": "CSE"
        },
        "overview": {
            "total_students": 320,
            "total_faculty": 22,
            "sections": 4,
            "active_projects": 120
        },
        "projects": {
            "total": 120,
            "ideation": 15,
            "planning": 20,
            "development": 45,
            "testing": 18,
            "documentation": 12,
            "review": 8,
            "completed": 12
        },
        "compliance": {
            "passing_plagiarism": 95,  # % under 10%
            "passing_ai": 90,           # % under 20%
            "flagged_projects": 4
        },
        "faculty": [
            {"name": "Mr. Anil Verma", "designation": "Asst. Professor", "students": 5, "pending_reviews": 2},
            {"name": "Ms. Sneha Gupta", "designation": "Asst. Professor", "students": 4, "pending_reviews": 1},
            {"name": "Dr. Amit Patel", "designation": "Assoc. Professor", "students": 6, "pending_reviews": 3},
            {"name": "Ms. Kavita Sharma", "designation": "Asst. Professor", "students": 3, "pending_reviews": 0}
        ],
        "sections": [
            {"name": "4th Year - Section A", "students": 65, "projects": 30, "avg_progress": 72},
            {"name": "4th Year - Section B", "students": 62, "projects": 28, "avg_progress": 68},
            {"name": "4th Year - Section C", "students": 60, "projects": 32, "avg_progress": 75},
            {"name": "4th Year - Section D", "students": 58, "projects": 30, "avg_progress": 65}
        ],
        "alerts": [
            {"type": "deadline", "message": "8 projects approaching deadline", "severity": "warning"},
            {"type": "plagiarism", "message": "2 projects flagged for high plagiarism", "severity": "error"},
            {"type": "review", "message": "12 projects pending review", "severity": "info"}
        ]
    }

    return {
        "role": "hod",
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/hod/students")
async def get_department_students(
    section: Optional[str] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get students in department"""
    allowed_roles = [UserRole.HOD, UserRole.PRINCIPAL, UserRole.LECTURER, UserRole.ADMIN]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied")

    students = [
        {"id": "s1", "name": "Rahul Sharma", "roll": "21CS001", "section": "A", "year": 4, "project": "AI Chatbot", "phase": "development", "progress": 65, "plagiarism": 5.2, "ai_score": 12.5, "guide": "Mr. Anil Verma"},
        {"id": "s2", "name": "Priya Patel", "roll": "21CS002", "section": "A", "year": 4, "project": "E-Commerce App", "phase": "testing", "progress": 80, "plagiarism": 3.1, "ai_score": 8.2, "guide": "Ms. Sneha Gupta"},
        {"id": "s3", "name": "Amit Kumar", "roll": "21CS003", "section": "A", "year": 4, "project": "Hospital Management", "phase": "documentation", "progress": 90, "plagiarism": 7.8, "ai_score": 15.3, "guide": "Dr. Amit Patel"},
        {"id": "s4", "name": "Sneha Reddy", "roll": "21CS004", "section": "B", "year": 4, "project": "Food Delivery App", "phase": "development", "progress": 55, "plagiarism": 4.5, "ai_score": 11.8, "guide": "Mr. Anil Verma"},
        {"id": "s5", "name": "Vikram Singh", "roll": "21CS005", "section": "B", "year": 4, "project": "Online Learning Platform", "phase": "planning", "progress": 30, "plagiarism": 2.1, "ai_score": 9.5, "guide": "Ms. Kavita Sharma"},
        {"id": "s6", "name": "Ananya Gupta", "roll": "21CS006", "section": "C", "year": 4, "project": "Smart Parking System", "phase": "ideation", "progress": 15, "plagiarism": None, "ai_score": None, "guide": "Pending"},
        {"id": "s7", "name": "Rohan Verma", "roll": "21CS007", "section": "C", "year": 4, "project": "Weather Prediction ML", "phase": "development", "progress": 70, "plagiarism": 12.5, "ai_score": 22.1, "guide": "Dr. Amit Patel"},
        {"id": "s8", "name": "Kavya Nair", "roll": "21CS008", "section": "D", "year": 4, "project": "Social Media Analytics", "phase": "testing", "progress": 85, "plagiarism": 6.3, "ai_score": 14.7, "guide": "Ms. Sneha Gupta"}
    ]

    if section:
        students = [s for s in students if s["section"].lower() == section.lower()]
    if year:
        students = [s for s in students if s["year"] == year]

    return {
        "students": students,
        "total": len(students),
        "filters": {"section": section, "year": year}
    }


@router.get("/hod/projects")
async def get_department_projects(
    phase: Optional[str] = None,
    flagged: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all projects in department"""
    allowed_roles = [UserRole.HOD, UserRole.PRINCIPAL, UserRole.ADMIN]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied")

    projects = [
        {"id": "p1", "title": "AI Chatbot for Customer Service", "student": "Rahul Sharma", "guide": "Mr. Anil Verma", "phase": "development", "progress": 65, "plagiarism": 5.2, "ai_score": 12.5, "deadline": "2024-03-15", "status": "on_track"},
        {"id": "p2", "title": "E-Commerce Platform", "student": "Priya Patel", "guide": "Ms. Sneha Gupta", "phase": "testing", "progress": 80, "plagiarism": 3.1, "ai_score": 8.2, "deadline": "2024-03-10", "status": "on_track"},
        {"id": "p3", "title": "Hospital Management System", "student": "Amit Kumar", "guide": "Dr. Amit Patel", "phase": "documentation", "progress": 90, "plagiarism": 7.8, "ai_score": 15.3, "deadline": "2024-03-20", "status": "on_track"},
        {"id": "p4", "title": "Weather Prediction ML", "student": "Rohan Verma", "guide": "Dr. Amit Patel", "phase": "development", "progress": 70, "plagiarism": 12.5, "ai_score": 22.1, "deadline": "2024-03-15", "status": "flagged"},
        {"id": "p5", "title": "Smart Parking System", "student": "Ananya Gupta", "guide": "Pending", "phase": "ideation", "progress": 15, "plagiarism": None, "ai_score": None, "deadline": "2024-04-01", "status": "delayed"}
    ]

    if phase:
        projects = [p for p in projects if p["phase"].lower() == phase.lower()]
    if flagged:
        projects = [p for p in projects if p["status"] == "flagged"]

    return {
        "projects": projects,
        "total": len(projects),
        "summary": {
            "on_track": len([p for p in projects if p["status"] == "on_track"]),
            "flagged": len([p for p in projects if p["status"] == "flagged"]),
            "delayed": len([p for p in projects if p["status"] == "delayed"])
        }
    }


# ============================================================================
# LECTURER DASHBOARD
# ============================================================================

@router.get("/lecturer/dashboard")
async def get_lecturer_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lecturer Dashboard - Personal teaching overview
    Shows assigned students, projects to review, and schedules
    """
    allowed_roles = [UserRole.LECTURER, UserRole.HOD, UserRole.PRINCIPAL, UserRole.FACULTY, UserRole.ADMIN]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied")

    stats = {
        "profile": {
            "name": current_user.full_name or "Faculty Member",
            "designation": "Assistant Professor",
            "department": current_user.department or "CSE",
            "specialization": "Web Development"
        },
        "overview": {
            "students_guided": 5,
            "pending_reviews": 3,
            "completed_reviews": 28,
            "avg_student_progress": 68
        },
        "students": [
            {"id": "s1", "name": "Rahul Sharma", "roll": "21CS001", "project": "AI Chatbot", "phase": "development", "progress": 65, "last_submission": "2024-02-08", "needs_review": True},
            {"id": "s4", "name": "Sneha Reddy", "roll": "21CS004", "project": "Food Delivery App", "phase": "development", "progress": 55, "last_submission": "2024-02-07", "needs_review": True},
            {"id": "s9", "name": "Kiran Reddy", "roll": "21CS009", "project": "Inventory System", "phase": "testing", "progress": 75, "last_submission": "2024-02-09", "needs_review": False},
            {"id": "s10", "name": "Meera Singh", "roll": "21CS010", "project": "Library Management", "phase": "documentation", "progress": 88, "last_submission": "2024-02-06", "needs_review": True},
            {"id": "s11", "name": "Arjun Patel", "roll": "21CS011", "project": "Bus Tracking App", "phase": "planning", "progress": 25, "last_submission": "2024-02-05", "needs_review": False}
        ],
        "pending_reviews": [
            {"student": "Rahul Sharma", "project": "AI Chatbot", "phase": "Development - Week 3", "submitted": "2024-02-08", "type": "code_review"},
            {"student": "Sneha Reddy", "project": "Food Delivery App", "phase": "Development - Week 2", "submitted": "2024-02-07", "type": "documentation"},
            {"student": "Meera Singh", "project": "Library Management", "phase": "Documentation", "submitted": "2024-02-06", "type": "final_review"}
        ],
        "schedule": [
            {"date": "2024-02-12", "time": "10:00 AM", "student": "Rahul Sharma", "type": "Progress Review"},
            {"date": "2024-02-12", "time": "2:00 PM", "student": "Sneha Reddy", "type": "Code Review"},
            {"date": "2024-02-13", "time": "11:00 AM", "student": "Meera Singh", "type": "Final Review"}
        ]
    }

    return {
        "role": "lecturer",
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/lecturer/students")
async def get_guided_students(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get students guided by this lecturer"""
    allowed_roles = [UserRole.LECTURER, UserRole.HOD, UserRole.PRINCIPAL, UserRole.FACULTY, UserRole.ADMIN]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied")

    students = [
        {
            "id": "s1",
            "name": "Rahul Sharma",
            "roll": "21CS001",
            "section": "A",
            "email": "rahul@student.edu",
            "phone": "9876543001",
            "project": {
                "title": "AI Chatbot for Customer Service",
                "phase": "development",
                "progress": 65,
                "plagiarism": 5.2,
                "ai_score": 12.5,
                "deadline": "2024-03-15"
            },
            "milestones": [
                {"phase": "ideation", "status": "completed", "score": 85},
                {"phase": "planning", "status": "completed", "score": 78},
                {"phase": "development", "status": "in_progress", "score": None},
                {"phase": "testing", "status": "pending", "score": None},
                {"phase": "documentation", "status": "pending", "score": None}
            ],
            "last_activity": "2024-02-08T10:30:00"
        },
        {
            "id": "s4",
            "name": "Sneha Reddy",
            "roll": "21CS004",
            "section": "B",
            "email": "sneha@student.edu",
            "phone": "9876543004",
            "project": {
                "title": "Food Delivery App",
                "phase": "development",
                "progress": 55,
                "plagiarism": 4.5,
                "ai_score": 11.8,
                "deadline": "2024-03-15"
            },
            "milestones": [
                {"phase": "ideation", "status": "completed", "score": 90},
                {"phase": "planning", "status": "completed", "score": 82},
                {"phase": "development", "status": "in_progress", "score": None},
                {"phase": "testing", "status": "pending", "score": None},
                {"phase": "documentation", "status": "pending", "score": None}
            ],
            "last_activity": "2024-02-07T14:20:00"
        }
    ]

    return {"students": students, "total": len(students)}


@router.post("/lecturer/review")
async def submit_review(
    student_id: str,
    phase: str,
    score: float,
    comments: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Submit review for student's project phase"""
    allowed_roles = [UserRole.LECTURER, UserRole.HOD, UserRole.PRINCIPAL, UserRole.FACULTY, UserRole.ADMIN]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied")

    # In production, this would update the database
    return {
        "success": True,
        "message": f"Review submitted for student {student_id}",
        "review": {
            "student_id": student_id,
            "phase": phase,
            "score": score,
            "comments": comments,
            "reviewed_by": current_user.full_name,
            "reviewed_at": datetime.utcnow().isoformat()
        }
    }


# ============================================================================
# COMMON ENDPOINTS
# ============================================================================

@router.get("/projects/phases")
async def get_project_phases():
    """Get all project phases with descriptions"""
    return {
        "phases": [
            {"id": "ideation", "name": "Ideation", "description": "Problem identification and solution brainstorming", "order": 1, "weight": 10},
            {"id": "planning", "name": "Planning", "description": "Requirements gathering and project planning", "order": 2, "weight": 15},
            {"id": "development", "name": "Development", "description": "Coding and implementation", "order": 3, "weight": 35},
            {"id": "testing", "name": "Testing", "description": "Unit testing, integration testing, and bug fixes", "order": 4, "weight": 15},
            {"id": "documentation", "name": "Documentation", "description": "Technical documentation and user guides", "order": 5, "weight": 15},
            {"id": "review", "name": "Review", "description": "Final review and presentation", "order": 6, "weight": 10}
        ]
    }


@router.get("/analytics/compliance")
async def get_compliance_analytics(
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get plagiarism and AI detection compliance analytics"""
    check_college_admin(current_user)

    return {
        "plagiarism": {
            "threshold": 10,
            "total_checked": 450,
            "passing": 415,
            "failing": 35,
            "pass_rate": 92.2,
            "distribution": [
                {"range": "0-5%", "count": 280},
                {"range": "5-10%", "count": 135},
                {"range": "10-15%", "count": 25},
                {"range": "15-25%", "count": 8},
                {"range": ">25%", "count": 2}
            ]
        },
        "ai_detection": {
            "threshold": 20,
            "total_checked": 450,
            "passing": 396,
            "failing": 54,
            "pass_rate": 88.0,
            "distribution": [
                {"range": "0-10%", "count": 180},
                {"range": "10-20%", "count": 216},
                {"range": "20-30%", "count": 38},
                {"range": "30-50%", "count": 12},
                {"range": ">50%", "count": 4}
            ]
        },
        "trend": {
            "labels": ["Jan", "Feb", "Mar", "Apr"],
            "plagiarism_avg": [9.2, 8.8, 8.5, 8.1],
            "ai_avg": [18.5, 17.2, 16.1, 15.2]
        }
    }


@router.post("/announcements")
async def create_announcement(
    title: str,
    content: str,
    priority: str = "normal",
    department_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new announcement"""
    check_college_admin(current_user)

    return {
        "success": True,
        "announcement": {
            "id": "ann-new",
            "title": title,
            "content": content,
            "priority": priority,
            "department_id": department_id,
            "created_by": current_user.full_name,
            "created_at": datetime.utcnow().isoformat()
        }
    }


@router.get("/announcements")
async def get_announcements(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get announcements"""
    announcements = [
        {"id": "ann-1", "title": "Project Submission Deadline Extended", "content": "Final year project submissions have been extended to March 20, 2024.", "priority": "high", "created_at": "2024-02-10"},
        {"id": "ann-2", "title": "Mid-Semester Review Schedule", "content": "Mid-semester reviews will be conducted from February 20-25, 2024. Please prepare your presentations.", "priority": "normal", "created_at": "2024-02-08"},
        {"id": "ann-3", "title": "New Plagiarism Guidelines", "content": "All submissions must have plagiarism score below 10%. Please ensure originality.", "priority": "high", "created_at": "2024-02-05"}
    ]

    return {"announcements": announcements[:limit], "total": len(announcements)}


# ============================================================================
# TEST ENDPOINTS (No Auth)
# ============================================================================

@router.get("/test/principal-dashboard")
async def test_principal_dashboard():
    """Test Principal Dashboard (no auth required)"""
    return {
        "role": "principal",
        "college": {"name": "Demo Engineering College", "code": "DEC001"},
        "stats": {
            "overview": {"total_students": 1250, "total_faculty": 85, "total_departments": 8},
            "projects": {"total": 450, "active": 280, "completed": 150, "pending_review": 45},
            "compliance": {"avg_plagiarism_score": 8.5, "avg_ai_detection": 15.2, "passing_plagiarism": 92, "passing_ai": 88}
        },
        "departments": [
            {"name": "Computer Science", "code": "CSE", "students": 320, "faculty": 22, "projects": 120},
            {"name": "Electronics", "code": "ECE", "students": 280, "faculty": 18, "projects": 95},
            {"name": "Mechanical", "code": "MECH", "students": 250, "faculty": 16, "projects": 85}
        ]
    }


@router.get("/test/hod-dashboard")
async def test_hod_dashboard():
    """Test HOD Dashboard (no auth required)"""
    return {
        "role": "hod",
        "department": {"name": "Computer Science and Engineering", "code": "CSE"},
        "stats": {
            "overview": {"total_students": 320, "total_faculty": 22, "sections": 4, "active_projects": 120},
            "projects_by_phase": {"ideation": 15, "planning": 20, "development": 45, "testing": 18, "documentation": 12, "completed": 10},
            "compliance": {"passing_plagiarism": 95, "passing_ai": 90, "flagged_projects": 4}
        },
        "faculty": [
            {"name": "Mr. Anil Verma", "students": 5, "pending_reviews": 2},
            {"name": "Ms. Sneha Gupta", "students": 4, "pending_reviews": 1}
        ]
    }


@router.get("/test/lecturer-dashboard")
async def test_lecturer_dashboard():
    """Test Lecturer Dashboard (no auth required)"""
    return {
        "role": "lecturer",
        "profile": {"name": "Mr. Anil Verma", "designation": "Assistant Professor", "department": "CSE"},
        "stats": {
            "students_guided": 5,
            "pending_reviews": 3,
            "completed_reviews": 28
        },
        "students": [
            {"name": "Rahul Sharma", "roll": "21CS001", "project": "AI Chatbot", "phase": "development", "progress": 65},
            {"name": "Sneha Reddy", "roll": "21CS004", "project": "Food Delivery App", "phase": "development", "progress": 55}
        ],
        "pending_reviews": [
            {"student": "Rahul Sharma", "phase": "Development - Week 3", "submitted": "2024-02-08"}
        ]
    }
