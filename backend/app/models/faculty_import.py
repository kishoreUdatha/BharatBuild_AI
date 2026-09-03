"""
Import Models - roster imports and their audit trail.

This is the portal's actual data entry point: a Student List import creates the
User and StudentEnrollment rows every other faculty screen counts. Each run
keeps the original file, a per-row issue list and a step timeline, so an import
can be traced back to its source and retried.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class ImportType(str, enum.Enum):
    STUDENT_LIST = "student_list"
    BATCH_ALLOCATION = "batch_allocation"
    PROJECT_DETAILS = "project_details"
    BASE_PAPER_METADATA = "base_paper_metadata"


IMPORT_TYPE_LABELS = {
    ImportType.STUDENT_LIST: "Student List",
    ImportType.BATCH_ALLOCATION: "Batch Allocation",
    ImportType.PROJECT_DETAILS: "Project Details",
    ImportType.BASE_PAPER_METADATA: "Base Paper Metadata",
}


class ImportStatus(str, enum.Enum):
    PROCESSING = "processing"
    SUCCESSFUL = "successful"
    PARTIALLY_IMPORTED = "partially_imported"
    FAILED = "failed"


IMPORT_STATUS_LABELS = {
    ImportStatus.PROCESSING: "Processing",
    ImportStatus.SUCCESSFUL: "Successful",
    ImportStatus.PARTIALLY_IMPORTED: "Partially Imported",
    ImportStatus.FAILED: "Failed",
}


class IssueSeverity(str, enum.Enum):
    ERROR = "error"          # the row was rejected
    DUPLICATE = "duplicate"  # the row was skipped, not an error


class ImportRun(Base):
    """One upload and everything that happened to it."""
    __tablename__ = "import_runs"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    import_code = Column(String(32), unique=True, nullable=False, index=True)  # IMP-2026-018

    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, default=0)
    # The original bytes are kept so "Download Original" returns exactly what
    # was uploaded and a failed run can be corrected and re-uploaded.
    file_content = Column(LargeBinary, nullable=True)

    import_type = Column(SQLEnum(ImportType), nullable=False, index=True)
    department = Column(String(100), nullable=True, index=True)
    academic_year = Column(String(20), nullable=False, index=True)

    status = Column(SQLEnum(ImportStatus), default=ImportStatus.PROCESSING, nullable=False, index=True)

    rows_total = Column(Integer, default=0)
    rows_imported = Column(Integer, default=0)
    rows_failed = Column(Integer, default=0)
    rows_duplicate = Column(Integer, default=0)

    imported_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # Whose data this run touched.
    #
    # A run rewrites one college's rosters and keeps the uploaded file, so it
    # is that college's record. Without the column the history query had
    # nothing to filter on and every college's imports - and, through the
    # detail panel, every college's uploaded roster - were readable by any
    # faculty account.
    college_id = Column(GUID, ForeignKey("colleges.id", ondelete="SET NULL"),
                        nullable=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)

    is_archived = Column(Boolean, default=False, index=True)

    imported_by = relationship("User", foreign_keys=[imported_by_id])
    issues = relationship("ImportRowIssue", back_populates="run", cascade="all, delete-orphan")
    events = relationship("ImportEvent", back_populates="run", cascade="all, delete-orphan")

    @property
    def duration_seconds(self) -> int:
        if not self.completed_at:
            return 0
        return int((self.completed_at - self.started_at).total_seconds())

    def __repr__(self):
        return f"<ImportRun {self.import_code} {self.status}>"


class ImportRowIssue(Base):
    """A row that could not be imported, or was skipped as a duplicate."""
    __tablename__ = "import_row_issues"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    run_id = Column(GUID, ForeignKey("import_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    row_number = Column(Integer, nullable=False)   # 1-based, as the file numbers it
    field = Column(String(64), nullable=True)
    message = Column(String(255), nullable=False)
    raw_value = Column(Text, nullable=True)
    severity = Column(SQLEnum(IssueSeverity), default=IssueSeverity.ERROR, nullable=False)

    run = relationship("ImportRun", back_populates="issues")

    def __repr__(self):
        return f"<ImportRowIssue row {self.row_number}: {self.message}>"


class ImportEvent(Base):
    """A step in the run's timeline, for the activity strip."""
    __tablename__ = "import_events"

    id = Column(GUID, primary_key=True, default=generate_uuid)
    run_id = Column(GUID, ForeignKey("import_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    step = Column(String(64), nullable=False)      # Uploaded, File Validated, ...
    actor = Column(String(120), nullable=True)     # a person's name, or "System"
    note = Column(String(255), nullable=True)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_warning = Column(Boolean, default=False)

    run = relationship("ImportRun", back_populates="events")

    def __repr__(self):
        return f"<ImportEvent {self.step}>"
