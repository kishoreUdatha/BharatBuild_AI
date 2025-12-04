"""
Project File Tree Model - Stores directory structure for instant UI rebuild
Used for: Fast file explorer rendering, no need to traverse S3
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class ProjectFileTree(Base):
    """
    Stores the complete file/folder tree structure as JSON.

    Use cases:
    - Instant file explorer rendering (20ms)
    - No need to query S3 for directory listing
    - Track file metadata without loading content

    Example tree_json:
    {
        "src": {
            "_type": "folder",
            "components": {
                "_type": "folder",
                "Navbar.tsx": {"_type": "file", "size": 1234, "language": "typescript"},
                "Footer.tsx": {"_type": "file", "size": 890, "language": "typescript"}
            },
            "App.tsx": {"_type": "file", "size": 2456, "language": "typescript"}
        },
        "package.json": {"_type": "file", "size": 567, "language": "json"},
        "README.md": {"_type": "file", "size": 234, "language": "markdown"}
    }
    """
    __tablename__ = "project_file_trees"

    __table_args__ = (
        Index('ix_project_file_trees_project_id', 'project_id'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)

    # The complete file tree as JSON
    tree_json = Column(JSON, nullable=False, default=dict)

    # Flattened file list for quick lookups
    # [{path: "src/App.tsx", size: 1234, language: "typescript", s3_key: "..."}, ...]
    files_index = Column(JSON, nullable=True)

    # Statistics
    total_files = Column(String(20), default="0")
    total_folders = Column(String(20), default="0")
    total_size_bytes = Column(String(50), default="0")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ProjectFileTree project={self.project_id} files={self.total_files}>"


class ProjectPlan(Base):
    """
    Stores the AI-generated project plan (plan.json).

    Use cases:
    - Restore project context
    - Show plan in UI
    - Resume generation from where it left off

    Example plan_json:
    {
        "project_name": "Todo App",
        "description": "A modern todo app with React",
        "tech_stack": ["React", "TypeScript", "Tailwind"],
        "features": [...],
        "files_to_generate": [...],
        "architecture": {...}
    }
    """
    __tablename__ = "project_plans"

    __table_args__ = (
        Index('ix_project_plans_project_id', 'project_id'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)

    # The complete plan
    plan_json = Column(JSON, nullable=False)

    # Plan version (for iterative refinement)
    version = Column(String(20), default="1.0")

    # Status
    status = Column(String(50), default="draft")  # draft, approved, executing, completed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ProjectPlan project={self.project_id} status={self.status}>"


class AgentState(Base):
    """
    Stores the state of each agent for a project.

    Use cases:
    - Resume generation from where it stopped
    - Show progress in UI
    - Debug agent behavior

    Example state_json:
    {
        "current_file": "src/components/Header.tsx",
        "files_completed": ["App.tsx", "index.tsx"],
        "files_pending": ["Header.tsx", "Footer.tsx"],
        "last_action": "writing",
        "context": {...}
    }
    """
    __tablename__ = "agent_states"

    __table_args__ = (
        Index('ix_agent_states_project_id', 'project_id'),
        Index('ix_agent_states_agent_type', 'agent_type'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Agent identification
    agent_type = Column(String(50), nullable=False)  # planner, writer, fixer, runner, reviewer

    # Agent state
    state_json = Column(JSON, nullable=False, default=dict)

    # Current status
    status = Column(String(50), default="idle")  # idle, running, paused, completed, failed
    current_action = Column(String(255), nullable=True)
    progress = Column(String(10), default="0")  # 0-100

    # Error tracking
    last_error = Column(Text, nullable=True)
    retry_count = Column(String(10), default="0")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<AgentState {self.agent_type} status={self.status}>"
