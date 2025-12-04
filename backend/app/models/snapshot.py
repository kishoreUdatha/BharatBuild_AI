"""
Snapshot Model - Project checkpoints for restore/undo
Used for: Save points, project restoration, version history
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class Snapshot(Base):
    """
    Stores full project state snapshots.

    Use cases:
    - "Save Checkpoint" feature (like Bolt.new)
    - Project restoration after errors
    - Undo to previous state
    - Share specific project versions

    snapshot_json contains:
    {
        "files": [{"path": "src/App.tsx", "content": "...", "version": 2}],
        "plan": {...},
        "file_tree": {...},
        "dependencies": {"package.json": {...}},
        "agent_state": {...}
    }
    """
    __tablename__ = "snapshots"

    __table_args__ = (
        Index('ix_snapshots_project_id', 'project_id'),
        Index('ix_snapshots_created_at', 'created_at'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Snapshot data
    name = Column(String(255), nullable=True)  # "Before adding auth", "Working version"
    description = Column(Text, nullable=True)
    snapshot_json = Column(JSON, nullable=False)  # Full project state

    # Metadata
    file_count = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)

    # Creator
    created_by = Column(String(50), default="user")  # "user", "auto", "agent"
    trigger = Column(String(100), nullable=True)  # "manual", "before_fix", "auto_save"

    # S3 backup (optional, for large snapshots)
    s3_key = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="snapshots")

    def __repr__(self):
        return f"<Snapshot {self.name or self.id} ({self.file_count} files)>"

    @property
    def file_list(self):
        """Get list of file paths in snapshot"""
        if self.snapshot_json and 'files' in self.snapshot_json:
            return [f.get('path') for f in self.snapshot_json['files']]
        return []
