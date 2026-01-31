"""
Report Generation Service
Generates PDF/Excel reports for faculty dashboard
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from io import BytesIO
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.user import User, UserRole
from app.models.lab_assistance import (
    Lab, LabEnrollment, LabTopic, LabCodingSubmission, LabMCQResponse,
    LabCodingProblem, SubmissionStatus
)
from app.models.college_management import (
    FacultyAssignment, StudentSection, Section, StudentProject
)


class ReportService:
    """Service for generating various reports"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_student_report(self, student_id: str) -> Dict[str, Any]:
        """Generate comprehensive report for a student"""

        # Get student info
        result = await self.db.execute(
            select(User).where(User.id == student_id)
        )
        student = result.scalar_one_or_none()

        if not student:
            return None

        # Get lab enrollments
        enrollments_result = await self.db.execute(
            select(LabEnrollment, Lab).join(
                Lab, LabEnrollment.lab_id == Lab.id
            ).where(LabEnrollment.user_id == student_id)
        )
        enrollments = enrollments_result.all()

        # Get submissions
        submissions_result = await self.db.execute(
            select(LabCodingSubmission).where(
                LabCodingSubmission.user_id == student_id
            ).order_by(LabCodingSubmission.submitted_at.desc()).limit(50)
        )
        submissions = submissions_result.scalars().all()

        # Calculate statistics
        total_submissions = len(submissions)
        passed_submissions = len([s for s in submissions if s.status == SubmissionStatus.PASSED])
        total_score = sum(s.score or 0 for s in submissions)
        avg_score = total_score / total_submissions if total_submissions > 0 else 0

        # Lab progress
        lab_progress = []
        for enrollment, lab in enrollments:
            lab_progress.append({
                "lab_name": lab.title,
                "topics_completed": enrollment.topics_completed,
                "total_topics": enrollment.total_topics,
                "problems_solved": enrollment.problems_solved,
                "mcq_score": enrollment.mcq_score,
                "total_score": enrollment.total_score,
                "progress_percentage": (enrollment.topics_completed / enrollment.total_topics * 100) if enrollment.total_topics > 0 else 0
            })

        return {
            "report_type": "student",
            "generated_at": datetime.utcnow().isoformat(),
            "student": {
                "id": str(student.id),
                "name": student.full_name or student.email,
                "email": student.email,
                "roll_number": student.roll_number
            },
            "summary": {
                "total_labs_enrolled": len(enrollments),
                "total_submissions": total_submissions,
                "passed_submissions": passed_submissions,
                "pass_rate": (passed_submissions / total_submissions * 100) if total_submissions > 0 else 0,
                "average_score": round(avg_score, 2)
            },
            "lab_progress": lab_progress,
            "recent_submissions": [
                {
                    "id": str(s.id),
                    "problem_id": str(s.problem_id),
                    "status": s.status.value if s.status else "pending",
                    "score": s.score,
                    "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None
                }
                for s in submissions[:10]
            ]
        }

    async def generate_class_report(self, class_id: str) -> Dict[str, Any]:
        """Generate class/section report"""

        # Get section info
        section_result = await self.db.execute(
            select(Section).where(Section.id == class_id)
        )
        section = section_result.scalar_one_or_none()

        # Get students in class
        students_result = await self.db.execute(
            select(StudentSection, User).join(
                User, StudentSection.user_id == User.id
            ).where(
                StudentSection.section_id == class_id,
                StudentSection.is_active == True
            )
        )
        students = students_result.all()

        student_data = []
        total_avg_score = 0

        for enrollment, student in students:
            # Get student's lab progress
            lab_result = await self.db.execute(
                select(
                    func.sum(LabEnrollment.total_score).label('total_score'),
                    func.count(LabEnrollment.id).label('labs_count')
                ).where(LabEnrollment.user_id == student.id)
            )
            lab_stats = lab_result.one_or_none()

            score = lab_stats.total_score or 0 if lab_stats else 0
            labs = lab_stats.labs_count or 0 if lab_stats else 0

            student_data.append({
                "id": str(student.id),
                "name": student.full_name or student.email,
                "roll_number": student.roll_number,
                "labs_enrolled": labs,
                "total_score": score,
                "avg_score": score / labs if labs > 0 else 0
            })

            total_avg_score += score / labs if labs > 0 else 0

        # Sort by score
        student_data.sort(key=lambda x: x["total_score"], reverse=True)

        class_avg = total_avg_score / len(students) if students else 0

        # Performance distribution
        top_performers = len([s for s in student_data if s["avg_score"] >= 80])
        average_performers = len([s for s in student_data if 50 <= s["avg_score"] < 80])
        weak_performers = len([s for s in student_data if s["avg_score"] < 50])

        return {
            "report_type": "class",
            "generated_at": datetime.utcnow().isoformat(),
            "class": {
                "id": class_id,
                "name": section.name if section else "Unknown",
                "semester": section.semester if section else None
            },
            "summary": {
                "total_students": len(students),
                "class_average": round(class_avg, 2),
                "top_performers": top_performers,
                "average_performers": average_performers,
                "weak_performers": weak_performers
            },
            "performance_distribution": {
                "excellent": top_performers,
                "good": average_performers,
                "needs_improvement": weak_performers
            },
            "students": student_data,
            "top_5": student_data[:5],
            "bottom_5": student_data[-5:] if len(student_data) >= 5 else student_data
        }

    async def generate_lab_completion_report(self, lab_id: str) -> Dict[str, Any]:
        """Generate lab completion report"""

        # Get lab info
        lab_result = await self.db.execute(
            select(Lab).where(Lab.id == lab_id)
        )
        lab = lab_result.scalar_one_or_none()

        if not lab:
            return None

        # Get enrollments
        enrollments_result = await self.db.execute(
            select(LabEnrollment, User).join(
                User, LabEnrollment.user_id == User.id
            ).where(LabEnrollment.lab_id == lab_id)
        )
        enrollments = enrollments_result.all()

        # Get topics
        topics_result = await self.db.execute(
            select(LabTopic).where(LabTopic.lab_id == lab_id)
        )
        topics = topics_result.scalars().all()

        # Get problems
        problems_result = await self.db.execute(
            select(LabCodingProblem).where(LabCodingProblem.lab_id == lab_id)
        )
        problems = problems_result.scalars().all()

        # Calculate completion stats
        completion_data = []
        for enrollment, student in enrollments:
            completion_pct = (enrollment.topics_completed / enrollment.total_topics * 100) if enrollment.total_topics > 0 else 0
            completion_data.append({
                "student_id": str(student.id),
                "student_name": student.full_name or student.email,
                "topics_completed": enrollment.topics_completed,
                "total_topics": enrollment.total_topics,
                "problems_solved": enrollment.problems_solved,
                "mcq_score": enrollment.mcq_score,
                "total_score": enrollment.total_score,
                "completion_percentage": round(completion_pct, 1),
                "last_activity": enrollment.last_activity.isoformat() if enrollment.last_activity else None
            })

        completion_data.sort(key=lambda x: x["completion_percentage"], reverse=True)

        # Calculate averages
        avg_completion = sum(c["completion_percentage"] for c in completion_data) / len(completion_data) if completion_data else 0
        avg_score = sum(c["total_score"] for c in completion_data) / len(completion_data) if completion_data else 0

        # Completion distribution
        completed = len([c for c in completion_data if c["completion_percentage"] >= 100])
        in_progress = len([c for c in completion_data if 0 < c["completion_percentage"] < 100])
        not_started = len([c for c in completion_data if c["completion_percentage"] == 0])

        return {
            "report_type": "lab_completion",
            "generated_at": datetime.utcnow().isoformat(),
            "lab": {
                "id": str(lab.id),
                "title": lab.title,
                "subject": lab.subject,
                "total_topics": len(topics),
                "total_problems": len(problems)
            },
            "summary": {
                "total_enrolled": len(enrollments),
                "average_completion": round(avg_completion, 1),
                "average_score": round(avg_score, 2),
                "completed_count": completed,
                "in_progress_count": in_progress,
                "not_started_count": not_started
            },
            "completion_distribution": {
                "completed": completed,
                "in_progress": in_progress,
                "not_started": not_started
            },
            "students": completion_data
        }

    async def generate_project_review_report(self, project_id: str) -> Dict[str, Any]:
        """Generate project review report"""

        # Get project info
        project_result = await self.db.execute(
            select(StudentProject, User).join(
                User, StudentProject.student_id == User.id
            ).where(StudentProject.id == project_id)
        )
        data = project_result.one_or_none()

        if not data:
            return None

        project, student = data

        # Get guide info if exists
        guide = None
        if project.guide_id:
            guide_result = await self.db.execute(
                select(User).where(User.id == project.guide_id)
            )
            guide = guide_result.scalar_one_or_none()

        return {
            "report_type": "project_review",
            "generated_at": datetime.utcnow().isoformat(),
            "project": {
                "id": str(project.id),
                "title": project.title,
                "description": project.description,
                "status": project.status,
                "current_phase": project.current_phase
            },
            "student": {
                "id": str(student.id),
                "name": student.full_name or student.email,
                "email": student.email,
                "roll_number": student.roll_number
            },
            "guide": {
                "id": str(guide.id) if guide else None,
                "name": guide.full_name if guide else "Not assigned"
            } if guide else None,
            "timeline": {
                "started_at": project.created_at.isoformat() if project.created_at else None,
                "expected_completion": None,  # Could be added to model
                "last_updated": project.updated_at.isoformat() if project.updated_at else None
            },
            "evaluation": {
                "synopsis_marks": project.synopsis_marks,
                "review1_marks": project.review1_marks,
                "review2_marks": project.review2_marks,
                "final_marks": project.final_marks
            }
        }

    async def export_marks(self, class_id: str, lab_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Export marks for a class in tabular format for Excel export"""

        # Get students in class
        students_result = await self.db.execute(
            select(StudentSection, User).join(
                User, StudentSection.user_id == User.id
            ).where(
                StudentSection.section_id == class_id,
                StudentSection.is_active == True
            ).order_by(User.roll_number)
        )
        students = students_result.all()

        marks_data = []
        for enrollment, student in students:
            row = {
                "roll_number": student.roll_number or "",
                "name": student.full_name or student.email,
                "email": student.email
            }

            # Get lab enrollments
            query = select(LabEnrollment, Lab).join(
                Lab, LabEnrollment.lab_id == Lab.id
            ).where(LabEnrollment.user_id == student.id)

            if lab_id:
                query = query.where(LabEnrollment.lab_id == lab_id)

            labs_result = await self.db.execute(query)
            labs = labs_result.all()

            for lab_enrollment, lab in labs:
                row[f"{lab.title}_topics"] = lab_enrollment.topics_completed
                row[f"{lab.title}_problems"] = lab_enrollment.problems_solved
                row[f"{lab.title}_mcq"] = lab_enrollment.mcq_score
                row[f"{lab.title}_total"] = lab_enrollment.total_score

            marks_data.append(row)

        return marks_data


def get_report_service(db: AsyncSession) -> ReportService:
    """Factory function to get report service instance"""
    return ReportService(db)
