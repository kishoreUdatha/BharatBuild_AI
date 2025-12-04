"""
Sandbox Models - Container/VM instance tracking and logs
Used for: Docker container management, terminal sessions, build logs
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Index, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


class SandboxStatus(str, enum.Enum):
    """Sandbox container status"""
    PENDING = "pending"
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    TERMINATED = "terminated"


class LogType(str, enum.Enum):
    """Types of sandbox logs"""
    STDOUT = "stdout"
    STDERR = "stderr"
    DOCKER = "docker"
    NPM = "npm"
    BUILD = "build"
    ERROR = "error"
    SYSTEM = "system"


class SandboxInstance(Base):
    """
    Tracks Docker container instances for projects.

    Use cases:
    - Container lifecycle management
    - Port mapping for preview
    - Resource tracking
    - Container status display in UI
    """
    __tablename__ = "sandbox_instances"

    __table_args__ = (
        Index('ix_sandbox_instances_project_id', 'project_id'),
        Index('ix_sandbox_instances_status', 'status'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Container info
    docker_container_id = Column(String(100), nullable=True)
    image_name = Column(String(255), nullable=True)
    status = Column(String(50), default="pending")

    # Port mappings
    port_mappings = Column(JSON, nullable=True)  # {"3000": 32768, "5173": 32769}
    exposed_port = Column(Integer, nullable=True)  # Main app port
    host_port = Column(Integer, nullable=True)  # Mapped host port

    # Environment
    node_version = Column(String(20), nullable=True)
    python_version = Column(String(20), nullable=True)
    working_directory = Column(String(500), nullable=True)

    # Resource limits
    memory_limit = Column(String(20), nullable=True)  # "512m"
    cpu_limit = Column(String(20), nullable=True)  # "0.5"

    # Error tracking
    last_error = Column(Text, nullable=True)
    restart_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="sandbox_instances")
    logs = relationship("SandboxLog", back_populates="sandbox", cascade="all, delete-orphan")
    terminal_sessions = relationship("TerminalSession", back_populates="sandbox", cascade="all, delete-orphan")
    preview_sessions = relationship("LivePreviewSession", back_populates="sandbox", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SandboxInstance {self.id} ({self.status})>"


class SandboxLog(Base):
    """
    Stores logs from sandbox containers.

    Use cases:
    - Terminal output display
    - Build log viewer
    - Error tracking for fixer agent
    - npm install progress
    """
    __tablename__ = "sandbox_logs"

    __table_args__ = (
        Index('ix_sandbox_logs_sandbox_id', 'sandbox_id'),
        Index('ix_sandbox_logs_log_type', 'log_type'),
        Index('ix_sandbox_logs_created_at', 'created_at'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    sandbox_id = Column(GUID, ForeignKey("sandbox_instances.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # Log content
    log_type = Column(String(50), default="stdout")
    content = Column(Text, nullable=False)

    # Source tracking
    source = Column(String(100), nullable=True)  # "npm", "vite", "node", etc.
    command = Column(String(500), nullable=True)  # Command that generated this log

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    sandbox = relationship("SandboxInstance", back_populates="logs")

    def __repr__(self):
        return f"<SandboxLog {self.log_type}: {self.content[:50]}...>"


class TerminalSession(Base):
    """
    Tracks terminal/shell sessions.

    Use cases:
    - WebSocket session management
    - Terminal history (up arrow)
    - Session restoration
    """
    __tablename__ = "terminal_sessions"

    __table_args__ = (
        Index('ix_terminal_sessions_project_id', 'project_id'),
        Index('ix_terminal_sessions_sandbox_id', 'sandbox_id'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    sandbox_id = Column(GUID, ForeignKey("sandbox_instances.id", ondelete="CASCADE"), nullable=True)

    # Session info
    ws_session_id = Column(String(255), nullable=True)  # WebSocket session ID
    shell_type = Column(String(50), default="bash")  # bash, sh, zsh

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    sandbox = relationship("SandboxInstance", back_populates="terminal_sessions")
    history = relationship("TerminalHistory", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TerminalSession {self.id} (active={self.is_active})>"


class TerminalHistory(Base):
    """
    Stores terminal command history.

    Use cases:
    - Command history (up arrow navigation)
    - Audit trail
    - Replay commands
    """
    __tablename__ = "terminal_history"

    __table_args__ = (
        Index('ix_terminal_history_session_id', 'session_id'),
        Index('ix_terminal_history_created_at', 'created_at'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    session_id = Column(GUID, ForeignKey("terminal_sessions.id", ondelete="CASCADE"), nullable=False)

    # Command and output
    command = Column(Text, nullable=False)
    output = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    session = relationship("TerminalSession", back_populates="history")

    def __repr__(self):
        return f"<TerminalHistory: {self.command[:50]}>"


class LivePreviewSession(Base):
    """
    Tracks live preview URLs and ports.

    Use cases:
    - Preview URL management
    - Port mapping display
    - Public URL generation
    """
    __tablename__ = "live_preview_sessions"

    __table_args__ = (
        Index('ix_live_preview_sessions_project_id', 'project_id'),
        Index('ix_live_preview_sessions_sandbox_id', 'sandbox_id'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    sandbox_id = Column(GUID, ForeignKey("sandbox_instances.id", ondelete="CASCADE"), nullable=True)

    # Preview URLs
    public_url = Column(String(500), nullable=True)  # https://preview-xxx.bharatbuild.ai
    local_url = Column(String(200), nullable=True)  # http://localhost:3000
    local_port = Column(Integer, nullable=True)
    host_port = Column(Integer, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sandbox = relationship("SandboxInstance", back_populates="preview_sessions")

    def __repr__(self):
        return f"<LivePreviewSession {self.public_url}>"
