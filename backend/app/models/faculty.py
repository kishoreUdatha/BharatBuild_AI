"""
Faculty Portal Models - Sections, project batches, reviews, attendance and
base papers behind the faculty dashboard.

Students and guides are `User` rows (role student / faculty); nothing here
duplicates identity. Note this deliberately does NOT build on
`app/models/college.py`: that module's `Batch` means an admission cohort
("2021-2025") while a project batch here is a project group of 3-5 students,
and its `Faculty`/`Student` tables restate columns `User` already carries.
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class ProjectStage(str, enum.Enum):
    """The eight tracked stages of an academic project, in order."""
    TOPIC_APPROVAL = "topic_approval"
    BASE_PAPER = "base_paper"
    REQUIREMENTS = "requirements"
    SYSTEM_DESIGN = "system_design"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    FINAL_REVIEW = "final_review"


# Display order and labels, kept next to the enum so the API and any report
# generator agree on how stages are sequenced.
STAGE_ORDER = [
    ProjectStage.TOPIC_APPROVAL,
    ProjectStage.BASE_PAPER,
    ProjectStage.REQUIREMENTS,
    ProjectStage.SYSTEM_DESIGN,
    ProjectStage.DEVELOPMENT,
    ProjectStage.TESTING,
    ProjectStage.DOCUMENTATION,
    ProjectStage.FINAL_REVIEW,
]

STAGE_LABELS = {
    ProjectStage.TOPIC_APPROVAL: "Topic Approval",
    ProjectStage.BASE_PAPER: "Base Paper",
    ProjectStage.REQUIREMENTS: "Requirements",
    ProjectStage.SYSTEM_DESIGN: "System Design",
    ProjectStage.DEVELOPMENT: "Development",
    ProjectStage.TESTING: "Testing",
    ProjectStage.DOCUMENTATION: "Documentation",
    ProjectStage.FINAL_REVIEW: "Final Review",
}


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    # Away with a reason the college accepted. Counts as attended, so it does
    # not punish a student for a medical leave the office already approved.
    EXCUSED = "excused"


class AttendanceSession(str, enum.Enum):
    """
    The half of the day being marked.

    A student who attends the morning and leaves after lunch is present for
    one and absent for the other, and a single row per day cannot say that.
    """
    FORENOON = "forenoon"      # 09:30 - 12:30
    AFTERNOON = "afternoon"    # 13:30 - 16:30


class ReviewStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BasePaperStatus(str, enum.Enum):
    VERIFIED = "verified"
    # The student has uploaded a paper but a guide has not verified it yet.
    PENDING = "pending"
    MISSING = "missing"


class BatchRegistrationStatus(str, enum.Enum):
    """Where a batch sits in the registration workflow."""
    DRAFT = "draft"                          # started, nothing submitted
    INCOMPLETE = "incomplete"                # missing members / base paper / guide
    SUBMITTED = "submitted"                  # sent in, not yet in the queue
    PENDING_APPROVAL = "pending_approval"    # waiting on a guide
    CHANGES_REQUESTED = "changes_requested"  # guide sent it back
    APPROVED = "approved"
    REJECTED = "rejected"


class StudentProfileStatus(str, enum.Enum):
    """Verification state of a student's registration profile."""
    VERIFIED = "verified"
    VERIFICATION_PENDING = "verification_pending"
    PROFILE_INCOMPLETE = "profile_incomplete"


class MemberInviteStatus(str, enum.Enum):
    """Whether a student has actually taken up their seat in a batch."""
    INVITED = "invited"
    JOINED = "joined"
    DECLINED = "declined"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class SubmissionStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class StudentEnrollment(Base):
    """
    A student's placement in a department/section for one academic year.

    Section is nullable on purpose - students who have registered but have not
    been mapped to a section yet are the dashboard's "Unassigned" row.
    """
    __tablename__ = "student_enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "academic_year", name="uq_enrollment_student_year"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    # Which institution this row belongs to. See the add_tenant_isolation migration.
    college_id = Column(GUID, ForeignKey("colleges.id"), nullable=False, index=True)
    
    student_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    department = Column(String(100), nullable=False, index=True)
    section = Column(String(10), nullable=True, index=True)
    year = Column(String(20), nullable=False)          # "4th Year"
    semester = Column(String(10), nullable=True)       # "I" / "II"
    academic_year = Column(String(20), nullable=False, index=True)  # "2026-27"

    is_registered = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    # Registration-desk state, tracked per academic year rather than on the
    # User, so re-enrolling next year starts clean.
    profile_status = Column(
        SQLEnum(StudentProfileStatus),
        default=StudentProfileStatus.VERIFICATION_PENDING,
        nullable=False,
        index=True,
    )
    last_reminder_at = Column(DateTime, nullable=True)
    contact_verified = Column(Boolean, default=False)     # mobile/email confirmed
    declaration_signed = Column(Boolean, default=False)   # anti-plagiarism undertaking
    invitation_accepted = Column(Boolean, default=False)  # accepted a batch invite

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("User", foreign_keys=[student_id])

    def __repr__(self):
        return f"<StudentEnrollment {self.student_id} {self.department}-{self.section}>"


class ProjectBatch(Base):
    """A project group (3-5 students) working on one academic project."""
    __tablename__ = "project_batches"
    __table_args__ = (
        UniqueConstraint("college_id", "batch_code", name="uq_batch_code_per_college"),
    )


    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Which institution this row belongs to. See the add_tenant_isolation migration.
    college_id = Column(GUID, ForeignKey("colleges.id"), nullable=False, index=True)
    
    batch_code = Column(String(50), nullable=False, index=True)  # "CSE-A-001"
    title = Column(String(255), nullable=True)

    department = Column(String(100), nullable=False, index=True)
    section = Column(String(10), nullable=True, index=True)
    year = Column(String(20), nullable=True)
    semester = Column(String(10), nullable=True)
    academic_year = Column(String(20), nullable=False, index=True)
    project_type = Column(String(50), default="Major Project", index=True)

    # What a student types on the join screen. Kept separate from batch_code
    # because batch_code is the faculty-facing identifier and is printed on
    # reports; the join code can be rotated if it leaks without renaming the
    # batch everywhere else.
    join_code = Column(String(40), nullable=True, unique=True, index=True)
    team_size = Column(Integer, default=4, nullable=False)
    # Whole-batch fee in rupees. Each student pays fee / team_size.
    project_fee = Column(Integer, default=15000, nullable=False)

    registration_status = Column(
        SQLEnum(BatchRegistrationStatus),
        default=BatchRegistrationStatus.DRAFT,
        nullable=False,
        index=True,
    )

    guide_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Approval workflow. submitted_at starts the SLA clock; review_due_at is
    # when the queue calls the review overdue.
    abstract = Column(Text, nullable=True)
    domain = Column(String(160), nullable=True)
    problem_statement = Column(Text, nullable=True)
    keywords = Column(String(400), nullable=True)          # comma separated
    internal_note = Column(Text, nullable=True)            # private to faculty
    start_date = Column(Date, nullable=True)
    target_completion = Column(Date, nullable=True)
    weekly_effort_hours = Column(Integer, nullable=True)
    submitted_at = Column(DateTime, nullable=True, index=True)
    review_due_at = Column(DateTime, nullable=True, index=True)
    reviewer_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    faculty_note = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    last_reminder_at = Column(DateTime, nullable=True)

    # Cached roll-up of stage_progress so list views avoid an aggregate per row.
    overall_progress = Column(Float, default=0.0)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    guide = relationship("User", foreign_keys=[guide_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    members = relationship("ProjectBatchMember", back_populates="batch", cascade="all, delete-orphan")
    stage_progress = relationship("BatchStageProgress", back_populates="batch", cascade="all, delete-orphan")
    reviews = relationship("ProjectReview", back_populates="batch", cascade="all, delete-orphan")
    base_paper = relationship("BasePaper", back_populates="batch", uselist=False, cascade="all, delete-orphan")
    submissions = relationship("ProjectSubmission", back_populates="batch", cascade="all, delete-orphan")

    # Batch Registration Details tabs
    objectives = relationship("ProjectObjective", back_populates="batch", cascade="all, delete-orphan")
    methodology = relationship("ProjectMethodologyStep", back_populates="batch", cascade="all, delete-orphan")
    scope_items = relationship("ProjectScopeItem", back_populates="batch", cascade="all, delete-orphan")
    technologies = relationship("ProjectTechnology", back_populates="batch", cascade="all, delete-orphan")
    supporting_papers = relationship("SupportingPaper", back_populates="batch", cascade="all, delete-orphan")
    contributions = relationship("NovelContribution", back_populates="batch", cascade="all, delete-orphan")
    documents = relationship("BatchDocument", back_populates="batch", cascade="all, delete-orphan",
                             foreign_keys="BatchDocument.batch_id")
    approval_events = relationship("ApprovalEvent", back_populates="batch", cascade="all, delete-orphan")
    activities = relationship("ActivityLog", back_populates="batch", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProjectBatch {self.batch_code}>"


class ProjectBatchMember(Base):
    """Membership of a student in a project batch."""
    __tablename__ = "project_batch_members"
    __table_args__ = (
        UniqueConstraint("batch_id", "student_id", name="uq_batch_member"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    is_lead = Column(Boolean, default=False)
    responsibility = Column(String(120), nullable=True)   # "ML Lead", "Data Engineer", ...
    joined_at = Column(DateTime, default=datetime.utcnow)

    # A seat can be allocated before the student accepts it, so invitation and
    # confirmation are tracked separately from membership itself.
    invite_status = Column(
        SQLEnum(MemberInviteStatus), default=MemberInviteStatus.JOINED, nullable=False, index=True
    )
    seat_confirmed = Column(Boolean, default=True, nullable=False)
    invited_at = Column(DateTime, nullable=True)
    invite_reminded_at = Column(DateTime, nullable=True)
    # Cleared when a member stops contributing; drives "batches with inactive members".
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    batch = relationship("ProjectBatch", back_populates="members")
    student = relationship("User", foreign_keys=[student_id])

    def __repr__(self):
        return f"<ProjectBatchMember {self.batch_id}/{self.student_id}>"


class BatchStageProgress(Base):
    """Percent complete for one of the eight stages of one batch."""
    __tablename__ = "batch_stage_progress"
    __table_args__ = (
        UniqueConstraint("batch_id", "stage", name="uq_batch_stage"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    stage = Column(SQLEnum(ProjectStage), nullable=False, index=True)
    percent = Column(Float, default=0.0)
    # When this stage was meant to land. `completed_at` records when it
    # actually did - a milestone timeline needs both to be worth showing.
    planned_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batch = relationship("ProjectBatch", back_populates="stage_progress")

    def __repr__(self):
        return f"<BatchStageProgress {self.batch_id} {self.stage} {self.percent}%>"


class ProjectReview(Base):
    """A scheduled review of a batch. Overdue = scheduled and in the past."""
    __tablename__ = "project_reviews"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    review_type = Column(String(100), nullable=False)   # "Progress Review"
    scheduled_at = Column(DateTime, nullable=False, index=True)
    # How long the slot runs. Without it nothing can tell whether two bookings
    # overlap, and a back-to-back round reads as a pile of double-bookings.
    slot_minutes = Column(Integer, default=20, nullable=False)
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.SCHEDULED, index=True)

    reviewer_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    remarks = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batch = relationship("ProjectBatch", back_populates="reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id])

    def __repr__(self):
        return f"<ProjectReview {self.batch_id} {self.review_type}>"


class AttendanceRecord(Base):
    """One student's attendance on one day."""
    __tablename__ = "attendance_records"
    __table_args__ = (
        # One row per student per session, not per day: the register is a
        # statement about a session, and marking one must not overwrite the
        # other half of the day.
        UniqueConstraint("student_id", "attendance_date", "session",
                         name="uq_attendance_student_session"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    # Which institution this row belongs to. See the add_tenant_isolation migration.
    college_id = Column(GUID, ForeignKey("colleges.id"), nullable=False, index=True)
    
    student_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    attendance_date = Column(Date, nullable=False, index=True)
    # Rows written before sessions existed are forenoon: that is when a single
    # daily register was taken, so it is the honest reading of them.
    session = Column(SQLEnum(AttendanceSession), nullable=False,
                     default=AttendanceSession.FORENOON, index=True)
    status = Column(SQLEnum(AttendanceStatus), nullable=False)

    # Denormalised so section-level rates do not need a join to enrollments.
    department = Column(String(100), nullable=True, index=True)
    section = Column(String(10), nullable=True, index=True)
    academic_year = Column(String(20), nullable=True, index=True)

    # Why, when the status alone does not say it: "hospital appointment",
    # "left after lunch". Free text on purpose - a fixed list of reasons is
    # always missing the one that actually happened.
    remarks = Column(String(300), nullable=True)

    marked_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("User", foreign_keys=[student_id])

    def __repr__(self):
        return (f"<AttendanceRecord {self.student_id} {self.attendance_date} "
                f"{self.session.value} {self.status}>")


class AttendanceSessionLog(Base):
    """
    A trainer's register for one session, and whether it has been submitted.

    Marking and submitting are different acts. Marks are saved as they are
    clicked so nothing is lost; submitting is the trainer saying the session
    is finished, which is what a coordinator chasing a missing register needs
    to see. A submitted session still accepts corrections - a register that
    cannot be fixed just gets a wrong one filed instead.
    """
    __tablename__ = "attendance_session_logs"
    __table_args__ = (
        UniqueConstraint("trainer_id", "attendance_date", "session",
                         name="uq_session_log_per_trainer"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    college_id = Column(GUID, ForeignKey("colleges.id"), nullable=False, index=True)
    trainer_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    attendance_date = Column(Date, nullable=False, index=True)
    session = Column(SQLEnum(AttendanceSession), nullable=False)

    # When the trainer first marked somebody, not when the window opened.
    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    trainer = relationship("User", foreign_keys=[trainer_id])

    @property
    def submitted(self) -> bool:
        return self.submitted_at is not None

    def __repr__(self):
        return (f"<AttendanceSessionLog {self.attendance_date} "
                f"{self.session.value} submitted={self.submitted}>")


class BasePaper(Base):
    """The reference paper a batch builds on, and its verification state."""
    __tablename__ = "base_papers"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    title = Column(String(500), nullable=True)
    authors = Column(String(500), nullable=True)
    publication = Column(String(255), nullable=True)
    year = Column(Integer, nullable=True)
    url = Column(Text, nullable=True)

    publisher = Column(String(160), nullable=True)
    publication_type = Column(String(80), nullable=True)   # Journal Article, Conference
    volume = Column(String(40), nullable=True)
    pages = Column(String(60), nullable=True)
    doi = Column(String(160), nullable=True)
    indexing = Column(String(160), nullable=True)          # Scopus, Web of Science
    quartile = Column(String(16), nullable=True)           # Q1..Q4
    # The PDF itself. file_name/file_size stay as the displayed metadata so
    # a paper recorded by DOI alone still reads correctly with no upload.
    file_id = Column(GUID, ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True, index=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    abstract_summary = Column(Text, nullable=True)
    dataset = Column(Text, nullable=True)
    improvement_note = Column(Text, nullable=True)
    current_limitation = Column(Text, nullable=True)
    similarity_percent = Column(Float, nullable=True)
    relevance_score = Column(Integer, nullable=True)
    methodology_score = Column(Integer, nullable=True)
    recency_score = Column(Integer, nullable=True)
    credibility_score = Column(Integer, nullable=True)
    faculty_note = Column(Text, nullable=True)
    uploaded_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime, nullable=True)

    status = Column(SQLEnum(BasePaperStatus), default=BasePaperStatus.MISSING, index=True)
    verified_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batch = relationship("ProjectBatch", back_populates="base_paper")
    file = relationship("StoredFile", foreign_keys=[file_id])
    metrics = relationship("PaperMetric", back_populates="base_paper", cascade="all, delete-orphan")
    key_methods = relationship("PaperKeyMethod", back_populates="base_paper", cascade="all, delete-orphan")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

    def __repr__(self):
        return f"<BasePaper {self.batch_id} {self.status}>"


class ProjectSubmission(Base):
    """A document a batch submitted, awaiting faculty verification."""
    __tablename__ = "project_submissions"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"), nullable=False, index=True)

    document_type = Column(String(100), nullable=False)  # "SRS", "Report", "PPT"
    title = Column(String(500), nullable=True)
    # An uploaded file, or a link when the work lives elsewhere (a repository,
    # a shared drive). One of the two, not both.
    file_id = Column(GUID, ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True, index=True)
    file_url = Column(Text, nullable=True)

    # Which of the eight project stages this deliverable belongs to. Without it
    # a submission is a loose file; with it, accepting one is what moves the
    # batch's tracked progress forward.
    stage = Column(SQLEnum(ProjectStage), nullable=True, index=True)
    version = Column(String(16), default="v1.0")

    status = Column(SQLEnum(SubmissionStatus), default=SubmissionStatus.PENDING, index=True)
    submitted_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, index=True)

    # A rejected submission is answered with a reason and resubmitted as a new
    # row, so the earlier attempt and what was said about it both survive.
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    faculty_note = Column(Text, nullable=True)
    superseded_by_id = Column(GUID, ForeignKey("project_submissions.id", ondelete="SET NULL"),
                              nullable=True)

    batch = relationship("ProjectBatch", back_populates="submissions")
    file = relationship("StoredFile", foreign_keys=[file_id])
    submitted_by = relationship("User", foreign_keys=[submitted_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    def __repr__(self):
        return f"<ProjectSubmission {self.batch_id} {self.document_type}>"


class RegistrationPayment(Base):
    """
    One student's share of their batch's registration fee.

    Per student rather than per batch: each member pays from their own account,
    so a batch can sit part-paid and the screen has to say exactly who is
    outstanding.
    """
    __tablename__ = "registration_payments"
    __table_args__ = (
        UniqueConstraint("batch_id", "student_id", name="uq_registration_payment"),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    batch_id = Column(GUID, ForeignKey("project_batches.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    student_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    amount = Column(Integer, nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING,
                    nullable=False, index=True)
    method = Column(String(40), nullable=True)          # "UPI", "Card", ...
    # The order stays put once opened, because the webhook arrives naming the
    # order and has to find this row - overwriting it with the payment id left
    # a captured payment with nothing to match against.
    reference = Column(String(80), nullable=True)       # gateway order id
    gateway_payment_id = Column(String(80), nullable=True, index=True)
    receipt_number = Column(String(40), nullable=True, index=True)
    paid_at = Column(DateTime, nullable=True)

    # Who entered it. Null for a payment the student made online - the gateway
    # recorded that one - and set when a coordinator enters a cash or transfer
    # payment on the student's behalf. The screen shows the difference because
    # "who took my money" is the first question when one goes missing.
    recorded_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"),
                            nullable=True)
    note = Column(String(200), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batch = relationship("ProjectBatch")
    student = relationship("User", foreign_keys=[student_id])

    def __repr__(self):
        return f"<RegistrationPayment {self.student_id} {self.status}>"
