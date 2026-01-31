"""
Faculty Service Layer
Provides business logic for faculty operations with database integration
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, UserRole
from app.models.college_management import (
    Department, Section, FacultyAssignment, StudentSection,
    StudentProject, ProjectMilestone, College, CollegeAnnouncement
)
from app.models.lab_assistance import (
    Lab, LabEnrollment, LabTopic, LabCodingSubmission, LabMCQResponse,
    LabTopicProgress, SubmissionStatus
)
from app.models.project_review import (
    ReviewProject, ProjectReview, ReviewPanelMember, ReviewStatus
)


class FacultyService:
    """Service for faculty-related operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =====================================================
    # PROFILE MANAGEMENT
    # =====================================================

    async def get_faculty_profile(self, user_id: str) -> Dict[str, Any]:
        """Get complete faculty profile with assignments"""
        # Get user details
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        # Get faculty assignment
        assignment_result = await self.db.execute(
            select(FacultyAssignment)
            .options(selectinload(FacultyAssignment.department))
            .where(FacultyAssignment.user_id == user_id, FacultyAssignment.is_active == True)
        )
        assignment = assignment_result.scalar_one_or_none()

        # Get assigned labs
        labs_result = await self.db.execute(
            select(Lab).where(Lab.faculty_id == user_id, Lab.is_active == True)
        )
        labs = labs_result.scalars().all()

        # Get review panel memberships
        panel_result = await self.db.execute(
            select(ReviewPanelMember).where(ReviewPanelMember.user_id == user_id)
        )
        panel_memberships = panel_result.scalars().all()

        # Build profile response
        profile = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value if user.role else "faculty",
            "avatar_url": user.avatar_url,
            "phone": user.phone,
            "organization": user.organization,
            "bio": user.bio,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "assignment": None,
            "assigned_labs": [],
            "panel_memberships": len(panel_memberships),
            "is_guide": False,
            "max_students": 0,
            "current_students": 0
        }

        if assignment:
            profile["assignment"] = {
                "id": str(assignment.id),
                "department_id": str(assignment.department_id),
                "department_name": assignment.department.name if assignment.department else None,
                "department_code": assignment.department.code if assignment.department else None,
                "designation": assignment.designation,
                "specialization": assignment.specialization,
                "is_guide": assignment.is_guide,
                "max_students": assignment.max_students,
                "current_students": assignment.current_students,
                "joined_at": assignment.joined_at
            }
            profile["is_guide"] = assignment.is_guide
            profile["max_students"] = assignment.max_students
            profile["current_students"] = assignment.current_students

        profile["assigned_labs"] = [
            {
                "id": str(lab.id),
                "name": lab.name,
                "code": lab.code,
                "branch": lab.branch.value if lab.branch else None,
                "semester": lab.semester.value if lab.semester else None
            }
            for lab in labs
        ]

        return profile

    async def update_faculty_profile(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update faculty profile"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        # Update user fields
        allowed_fields = ['full_name', 'phone', 'bio', 'avatar_url']
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])

        user.updated_at = datetime.utcnow()

        # Update faculty assignment if provided
        if 'designation' in data or 'specialization' in data:
            assignment_result = await self.db.execute(
                select(FacultyAssignment).where(
                    FacultyAssignment.user_id == user_id,
                    FacultyAssignment.is_active == True
                )
            )
            assignment = assignment_result.scalar_one_or_none()
            if assignment:
                if 'designation' in data:
                    assignment.designation = data['designation']
                if 'specialization' in data:
                    assignment.specialization = data['specialization']

        await self.db.commit()
        return await self.get_faculty_profile(user_id)

    # =====================================================
    # SUBJECT & LAB MANAGEMENT
    # =====================================================

    async def get_assigned_labs(self, faculty_id: str) -> List[Dict[str, Any]]:
        """Get all labs assigned to faculty"""
        result = await self.db.execute(
            select(Lab).where(
                Lab.faculty_id == faculty_id,
                Lab.is_active == True
            ).order_by(Lab.semester, Lab.name)
        )
        labs = result.scalars().all()

        lab_details = []
        for lab in labs:
            # Get enrollment count
            enrollment_result = await self.db.execute(
                select(func.count(LabEnrollment.id)).where(
                    LabEnrollment.lab_id == lab.id
                )
            )
            enrollment_count = enrollment_result.scalar() or 0

            lab_details.append({
                "id": str(lab.id),
                "name": lab.name,
                "code": lab.code,
                "description": lab.description,
                "branch": lab.branch.value if lab.branch else None,
                "semester": lab.semester.value if lab.semester else None,
                "technologies": lab.technologies,
                "total_topics": lab.total_topics,
                "total_mcqs": lab.total_mcqs,
                "total_coding_problems": lab.total_coding_problems,
                "enrolled_students": enrollment_count,
                "is_active": lab.is_active,
                "created_at": lab.created_at
            })

        return lab_details

    async def get_semester_sections(self, faculty_id: str) -> List[Dict[str, Any]]:
        """Get semester/section mappings for faculty"""
        # Get faculty's department
        assignment_result = await self.db.execute(
            select(FacultyAssignment)
            .options(selectinload(FacultyAssignment.department))
            .where(FacultyAssignment.user_id == faculty_id, FacultyAssignment.is_active == True)
        )
        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
            return []

        # Get sections in the department
        sections_result = await self.db.execute(
            select(Section).where(
                Section.department_id == assignment.department_id,
                Section.is_active == True
            ).order_by(Section.year, Section.semester, Section.name)
        )
        sections = sections_result.scalars().all()

        return [
            {
                "id": str(section.id),
                "name": section.name,
                "year": section.year,
                "semester": section.semester,
                "student_count": section.student_count,
                "is_coordinator": str(section.coordinator_id) == faculty_id if section.coordinator_id else False
            }
            for section in sections
        ]

    # =====================================================
    # STUDENT MANAGEMENT
    # =====================================================

    async def get_classes(self, faculty_id: str) -> List[Dict[str, Any]]:
        """Get classes/sections assigned to or coordinated by faculty"""
        # Get faculty assignment
        assignment_result = await self.db.execute(
            select(FacultyAssignment).where(
                FacultyAssignment.user_id == faculty_id,
                FacultyAssignment.is_active == True
            )
        )
        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
            return []

        # Get sections where faculty is coordinator or in the same department
        sections_result = await self.db.execute(
            select(Section)
            .options(selectinload(Section.department))
            .where(
                or_(
                    Section.coordinator_id == faculty_id,
                    Section.department_id == assignment.department_id
                ),
                Section.is_active == True
            ).order_by(Section.year, Section.semester, Section.name)
        )
        sections = sections_result.scalars().all()

        classes = []
        for section in sections:
            # Get student count
            student_count_result = await self.db.execute(
                select(func.count(StudentSection.id)).where(
                    StudentSection.section_id == section.id,
                    StudentSection.is_active == True
                )
            )
            student_count = student_count_result.scalar() or 0

            classes.append({
                "id": str(section.id),
                "name": f"Year {section.year} - Section {section.name}",
                "year": section.year,
                "semester": section.semester,
                "section": section.name,
                "department": section.department.name if section.department else None,
                "department_code": section.department.code if section.department else None,
                "student_count": student_count,
                "is_coordinator": str(section.coordinator_id) == faculty_id if section.coordinator_id else False
            })

        return classes

    async def get_class_students(
        self,
        class_id: str,
        status_filter: Optional[str] = None,
        performance_tier: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get students in a class with filtering options"""
        # Get student sections
        query = select(StudentSection, User).join(
            User, StudentSection.user_id == User.id
        ).where(
            StudentSection.section_id == class_id,
            StudentSection.is_active == True
        )

        if search:
            query = query.where(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    StudentSection.roll_number.ilike(f"%{search}%")
                )
            )

        if status_filter == "active":
            query = query.where(User.is_active == True)
        elif status_filter == "inactive":
            query = query.where(User.is_active == False)

        result = await self.db.execute(query.order_by(StudentSection.roll_number))
        student_data = result.all()

        students = []
        for student_section, user in student_data:
            # Get lab progress for this student
            lab_progress = await self._get_student_lab_summary(str(user.id))

            # Get project status
            project_status = await self._get_student_project_status(str(user.id))

            # Calculate performance tier
            avg_score = lab_progress.get("avg_score", 0)
            if avg_score >= 80:
                tier = "top"
            elif avg_score >= 50:
                tier = "average"
            else:
                tier = "weak"

            # Apply performance filter
            if performance_tier and tier != performance_tier:
                continue

            students.append({
                "id": str(user.id),
                "roll_number": student_section.roll_number,
                "name": user.full_name or user.email,
                "email": user.email,
                "is_active": user.is_active,
                "enrolled_at": student_section.enrolled_at,
                "lab_progress": lab_progress,
                "project_status": project_status,
                "performance_tier": tier,
                "last_active": user.last_login
            })

        return students

    async def get_student_detail(self, student_id: str) -> Dict[str, Any]:
        """Get detailed information about a student"""
        # Get user
        user_result = await self.db.execute(
            select(User).where(User.id == student_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return None

        # Get section assignment
        section_result = await self.db.execute(
            select(StudentSection)
            .options(selectinload(StudentSection.section))
            .where(StudentSection.user_id == student_id, StudentSection.is_active == True)
        )
        section_assignment = section_result.scalar_one_or_none()

        # Get lab enrollments
        labs_result = await self.db.execute(
            select(LabEnrollment, Lab)
            .join(Lab, LabEnrollment.lab_id == Lab.id)
            .where(LabEnrollment.user_id == student_id)
            .order_by(Lab.semester)
        )
        lab_enrollments = labs_result.all()

        # Get project
        project_result = await self.db.execute(
            select(StudentProject).where(StudentProject.student_id == student_id)
        )
        project = project_result.scalar_one_or_none()

        # Get recent submissions
        submissions_result = await self.db.execute(
            select(LabCodingSubmission)
            .where(LabCodingSubmission.user_id == student_id)
            .order_by(LabCodingSubmission.submitted_at.desc())
            .limit(10)
        )
        recent_submissions = submissions_result.scalars().all()

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "roll_number": user.roll_number,
            "college_name": user.college_name,
            "department": user.department,
            "course": user.course,
            "year_semester": user.year_semester,
            "batch": user.batch,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "section": {
                "id": str(section_assignment.section_id),
                "name": section_assignment.section.name if section_assignment and section_assignment.section else None,
                "year": section_assignment.section.year if section_assignment and section_assignment.section else None,
                "semester": section_assignment.section.semester if section_assignment and section_assignment.section else None
            } if section_assignment else None,
            "lab_enrollments": [
                {
                    "lab_id": str(enrollment.lab_id),
                    "lab_name": lab.name,
                    "lab_code": lab.code,
                    "semester": lab.semester.value if lab.semester else None,
                    "overall_progress": enrollment.overall_progress,
                    "mcq_score": enrollment.mcq_score,
                    "coding_score": enrollment.coding_score,
                    "total_score": enrollment.total_score,
                    "topics_completed": enrollment.topics_completed,
                    "class_rank": enrollment.class_rank
                }
                for enrollment, lab in lab_enrollments
            ],
            "project": {
                "id": str(project.id),
                "title": project.title,
                "current_phase": project.current_phase.value if project.current_phase else None,
                "guide_name": project.guide_name,
                "is_approved": project.is_approved,
                "plagiarism_score": project.plagiarism_score,
                "ai_detection_score": project.ai_detection_score
            } if project else None,
            "recent_submissions": [
                {
                    "id": str(sub.id),
                    "problem_id": str(sub.problem_id),
                    "status": sub.status.value if sub.status else "pending",
                    "score": sub.score,
                    "submitted_at": sub.submitted_at
                }
                for sub in recent_submissions
            ]
        }

    async def _get_student_lab_summary(self, student_id: str) -> Dict[str, Any]:
        """Get summary of student's lab performance"""
        result = await self.db.execute(
            select(LabEnrollment).where(LabEnrollment.user_id == student_id)
        )
        enrollments = result.scalars().all()

        if not enrollments:
            return {
                "enrolled_labs": 0,
                "avg_progress": 0,
                "avg_score": 0,
                "total_problems_solved": 0
            }

        return {
            "enrolled_labs": len(enrollments),
            "avg_progress": sum(e.overall_progress for e in enrollments) / len(enrollments),
            "avg_score": sum(e.total_score for e in enrollments) / len(enrollments),
            "total_problems_solved": sum(e.problems_solved for e in enrollments)
        }

    async def _get_student_project_status(self, student_id: str) -> Dict[str, Any]:
        """Get student's project status"""
        result = await self.db.execute(
            select(StudentProject).where(StudentProject.student_id == student_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            return {"status": "no_project", "phase": None, "is_approved": False}

        return {
            "status": "active" if project.current_phase else "pending",
            "phase": project.current_phase.value if project.current_phase else None,
            "is_approved": project.is_approved
        }

    # =====================================================
    # ANALYTICS
    # =====================================================

    async def get_dashboard_analytics(self, faculty_id: str) -> Dict[str, Any]:
        """Get dashboard analytics for faculty"""
        # Get assigned labs
        labs_result = await self.db.execute(
            select(Lab).where(Lab.faculty_id == faculty_id, Lab.is_active == True)
        )
        labs = labs_result.scalars().all()
        lab_ids = [str(lab.id) for lab in labs]

        # Total students across labs
        total_students = 0
        total_submissions = 0
        total_mcq_attempts = 0
        avg_scores = []

        for lab_id in lab_ids:
            # Enrollments
            enrollment_result = await self.db.execute(
                select(func.count(LabEnrollment.id), func.avg(LabEnrollment.total_score))
                .where(LabEnrollment.lab_id == lab_id)
            )
            count, avg_score = enrollment_result.first()
            total_students += count or 0
            if avg_score:
                avg_scores.append(avg_score)

            # Submissions
            sub_result = await self.db.execute(
                select(func.count(LabCodingSubmission.id))
                .join(Lab, LabCodingSubmission.problem_id.in_(
                    select(LabTopic.id).where(LabTopic.lab_id == lab_id)
                ))
            )

        # Get review stats
        review_result = await self.db.execute(
            select(func.count(ProjectReview.id))
            .where(
                or_(
                    ProjectReview.reviewed_by == faculty_id,
                    ProjectReview.status == ReviewStatus.PENDING
                )
            )
        )
        pending_reviews = review_result.scalar() or 0

        # Get guided students
        assignment_result = await self.db.execute(
            select(FacultyAssignment).where(
                FacultyAssignment.user_id == faculty_id,
                FacultyAssignment.is_active == True
            )
        )
        assignment = assignment_result.scalar_one_or_none()

        guided_students = assignment.current_students if assignment else 0

        return {
            "total_students": total_students,
            "total_labs": len(labs),
            "total_submissions": total_submissions,
            "avg_score": sum(avg_scores) / len(avg_scores) if avg_scores else 0,
            "pending_reviews": pending_reviews,
            "guided_students": guided_students,
            "completion_rate": 0  # Calculate based on completed topics
        }

    async def get_lab_analytics(self, lab_id: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific lab"""
        # Get lab
        lab_result = await self.db.execute(
            select(Lab).where(Lab.id == lab_id)
        )
        lab = lab_result.scalar_one_or_none()
        if not lab:
            return None

        # Get enrollments
        enrollments_result = await self.db.execute(
            select(LabEnrollment).where(LabEnrollment.lab_id == lab_id)
        )
        enrollments = enrollments_result.scalars().all()

        total_students = len(enrollments)

        if total_students == 0:
            return {
                "lab_id": str(lab.id),
                "lab_name": lab.name,
                "total_students": 0,
                "avg_progress": 0,
                "avg_mcq_score": 0,
                "avg_coding_score": 0,
                "performance_distribution": {},
                "topic_completion": []
            }

        # Calculate averages
        avg_progress = sum(e.overall_progress for e in enrollments) / total_students
        avg_mcq_score = sum(e.mcq_score for e in enrollments) / total_students
        avg_coding_score = sum(e.coding_score for e in enrollments) / total_students

        # Performance distribution
        performance_dist = {
            "excellent": len([e for e in enrollments if e.total_score >= 90]),
            "good": len([e for e in enrollments if 75 <= e.total_score < 90]),
            "average": len([e for e in enrollments if 60 <= e.total_score < 75]),
            "below_average": len([e for e in enrollments if 40 <= e.total_score < 60]),
            "needs_help": len([e for e in enrollments if e.total_score < 40])
        }

        # Topic completion
        topics_result = await self.db.execute(
            select(LabTopic).where(LabTopic.lab_id == lab_id, LabTopic.is_active == True)
        )
        topics = topics_result.scalars().all()

        topic_completion = []
        for topic in topics:
            completed_result = await self.db.execute(
                select(func.count(LabTopicProgress.id)).where(
                    LabTopicProgress.topic_id == topic.id,
                    LabTopicProgress.status == "completed"
                )
            )
            completed_count = completed_result.scalar() or 0

            topic_completion.append({
                "topic_id": str(topic.id),
                "topic_title": topic.title,
                "week_number": topic.week_number,
                "completed_count": completed_count,
                "completion_rate": (completed_count / total_students * 100) if total_students > 0 else 0
            })

        return {
            "lab_id": str(lab.id),
            "lab_name": lab.name,
            "total_students": total_students,
            "avg_progress": round(avg_progress, 2),
            "avg_mcq_score": round(avg_mcq_score, 2),
            "avg_coding_score": round(avg_coding_score, 2),
            "performance_distribution": performance_dist,
            "topic_completion": topic_completion
        }

    # =====================================================
    # COMMUNICATION
    # =====================================================

    async def create_announcement(
        self,
        faculty_id: str,
        title: str,
        content: str,
        department_id: Optional[str] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Create a college announcement"""
        # Get faculty's college
        assignment_result = await self.db.execute(
            select(FacultyAssignment)
            .options(selectinload(FacultyAssignment.department))
            .where(FacultyAssignment.user_id == faculty_id, FacultyAssignment.is_active == True)
        )
        assignment = assignment_result.scalar_one_or_none()

        if not assignment or not assignment.department:
            return None

        college_id = assignment.department.college_id

        from app.core.types import generate_uuid

        announcement = CollegeAnnouncement(
            id=generate_uuid(),
            college_id=college_id,
            department_id=department_id,
            title=title,
            content=content,
            priority=priority,
            created_by=faculty_id,
            is_active=True
        )

        self.db.add(announcement)
        await self.db.commit()
        await self.db.refresh(announcement)

        return {
            "id": str(announcement.id),
            "title": announcement.title,
            "content": announcement.content,
            "priority": announcement.priority,
            "created_at": announcement.created_at
        }

    async def get_announcements(
        self,
        faculty_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get announcements created by or relevant to faculty"""
        # Get faculty's department
        assignment_result = await self.db.execute(
            select(FacultyAssignment).where(
                FacultyAssignment.user_id == faculty_id,
                FacultyAssignment.is_active == True
            )
        )
        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
            return []

        # Get announcements
        result = await self.db.execute(
            select(CollegeAnnouncement).where(
                or_(
                    CollegeAnnouncement.created_by == faculty_id,
                    CollegeAnnouncement.department_id == assignment.department_id,
                    CollegeAnnouncement.department_id == None  # College-wide
                ),
                CollegeAnnouncement.is_active == True
            ).order_by(CollegeAnnouncement.created_at.desc()).limit(limit)
        )
        announcements = result.scalars().all()

        return [
            {
                "id": str(a.id),
                "title": a.title,
                "content": a.content,
                "priority": a.priority,
                "is_mine": str(a.created_by) == faculty_id,
                "created_at": a.created_at,
                "expires_at": a.expires_at
            }
            for a in announcements
        ]


# Factory function
def get_faculty_service(db: AsyncSession) -> FacultyService:
    return FacultyService(db)
