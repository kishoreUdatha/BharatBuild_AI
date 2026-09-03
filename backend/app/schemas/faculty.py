"""
Faculty Portal Schemas - response shapes for the faculty dashboard.

Field names mirror what the dashboard renders so the frontend can drop these
straight into its components.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class FacultyProfile(BaseModel):
    """Who the dashboard is greeting."""
    name: str
    department: Optional[str] = None
    sections: Optional[str] = None
    academic_year: str


class GuideOption(BaseModel):
    """A guide the dashboard can be filtered to. The dropdown shows `name`
    and submits `id`, since two guides can share a display name."""
    id: str
    name: str


class FilterOptions(BaseModel):
    """Values available in each filter dropdown, derived from live data."""
    departments: List[str] = []
    years: List[str] = []
    semesters: List[str] = []
    sections: List[str] = []
    project_types: List[str] = []
    guides: List[GuideOption] = []
    academic_years: List[str] = []


class Kpi(BaseModel):
    id: str
    value: str
    label: str


class StageSummary(BaseModel):
    """One of the eight stages, averaged across the filtered batches."""
    key: str
    label: str
    percent: int


class StagePoint(BaseModel):
    """Per-section averages at one stage, for the trend chart."""
    stage: str
    values: Dict[str, int] = Field(default_factory=dict)


class AttentionItem(BaseModel):
    id: str
    label: str
    count: int


class UpcomingReview(BaseModel):
    id: str
    date: str
    time: str
    batch_code: str
    review_type: str
    scheduled_at: datetime


class SectionRow(BaseModel):
    section: str
    students: int
    batches: Optional[int] = None
    registration: Optional[int] = None
    attendance: Optional[int] = None
    progress: Optional[int] = None
    pending_reviews: int = 0
    status: str


class ProjectRow(BaseModel):
    batch_id: str
    batch_code: str
    title: str
    issue: str
    progress: int
    risk: str


class AttendanceToday(BaseModel):
    present: int = 0
    absent: int = 0
    late: int = 0


class SubmissionsSummary(BaseModel):
    count: int = 0
    caption: str = "Documents awaiting verification"


class WorkloadSummary(BaseModel):
    assigned_batches: int = 0
    reviews_this_week: int = 0


class BasePaperRow(BaseModel):
    count: int
    label: str


class BasePaperSummary(BaseModel):
    rows: List[BasePaperRow] = []


class FacultyDashboardResponse(BaseModel):
    """Everything the dashboard screen needs, in one round trip."""
    faculty: FacultyProfile
    filters_applied: Dict[str, Optional[str]] = {}
    kpis: List[Kpi] = []
    stages: List[StageSummary] = []
    progress_series: List[StagePoint] = []
    series_names: List[str] = []
    attention_items: List[AttentionItem] = []
    upcoming_reviews: List[UpcomingReview] = []
    section_rows: List[SectionRow] = []
    project_rows: List[ProjectRow] = []
    attendance_today: AttendanceToday
    recent_submissions: SubmissionsSummary
    faculty_workload: WorkloadSummary
    base_paper_status: BasePaperSummary
    ai_insight: Optional[str] = None
