"""
Memory Agent - Context and File Awareness Management

Similar to Claude Code's Memory Agent that manages:
- File awareness (which files exist, their content summaries)
- Context tracking (what was discussed, decisions made)
- Conversation memory across turns
- Project state management

This agent helps other agents understand:
1. What files exist in the project
2. What changes have been made
3. What the user has discussed previously
4. Key decisions and context from the conversation
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import deque

from app.core.logging_config import logger
from app.utils.claude_client import claude_client


@dataclass
class FileInfo:
    """Information about a tracked file"""
    path: str
    exists: bool = True
    size: int = 0
    last_modified: Optional[str] = None
    content_hash: Optional[str] = None
    summary: Optional[str] = None  # AI-generated summary
    language: Optional[str] = None
    is_new: bool = False
    is_modified: bool = False


@dataclass
class ConversationTurn:
    """A turn in the conversation"""
    role: str  # user, assistant, system
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    files_mentioned: List[str] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)


@dataclass
class ProjectContext:
    """Overall project context"""
    project_id: str
    project_path: str
    project_type: Optional[str] = None
    tech_stack: Dict[str, str] = field(default_factory=dict)
    files: Dict[str, FileInfo] = field(default_factory=dict)
    directories: List[str] = field(default_factory=list)
    key_files: List[str] = field(default_factory=list)  # Important files
    recent_changes: List[Dict[str, Any]] = field(default_factory=list)
    conversation_summary: Optional[str] = None
    goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


class MemoryAgent:
    """
    Memory Agent - Manages context and file awareness across the conversation.

    Responsibilities:
    1. Track project files and their summaries
    2. Maintain conversation context
    3. Remember key decisions and goals
    4. Provide relevant context to other agents
    """

    # File extensions to track
    TRACKED_EXTENSIONS = {
        '.py', '.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte',
        '.html', '.css', '.scss', '.json', '.yaml', '.yml',
        '.md', '.txt', '.sql', '.sh', '.bat', '.env',
        '.java', '.kt', '.go', '.rs', '.rb', '.php',
        '.c', '.cpp', '.h', '.hpp', '.cs'
    }

    # Files to always include as key files
    KEY_FILE_PATTERNS = [
        'package.json', 'requirements.txt', 'pyproject.toml',
        'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
        '.env.example', 'README.md', 'main.py', 'app.py',
        'index.js', 'index.ts', 'App.js', 'App.tsx',
        'settings.py', 'config.py', 'config.js', 'config.ts'
    ]

    # Directories to ignore
    IGNORED_DIRS = {
        'node_modules', '__pycache__', '.git', '.venv', 'venv',
        'env', '.env', 'dist', 'build', '.next', '.nuxt',
        'coverage', '.pytest_cache', '.mypy_cache', 'eggs',
        '*.egg-info', '.tox', '.cache'
    }

    # Max files to track (prevent memory explosion)
    MAX_FILES = 500
    MAX_CONVERSATION_TURNS = 50
    MAX_RECENT_CHANGES = 20

    def __init__(self, project_id: str, project_path: str):
        self.project_id = project_id
        self.project_path = Path(project_path).resolve()

        # Initialize context
        self.context = ProjectContext(
            project_id=project_id,
            project_path=str(self.project_path)
        )

        # Conversation history (limited size)
        self.conversation_history: deque = deque(maxlen=self.MAX_CONVERSATION_TURNS)

        # Cache for file summaries
        self._summary_cache: Dict[str, str] = {}

        logger.info(f"[MemoryAgent] Initialized for project: {project_id} at {project_path}")

    async def initialize(self) -> Dict[str, Any]:
        """
        Initialize memory agent by scanning the project.
        Call this when starting a new session.
        """
        logger.info(f"[MemoryAgent] Scanning project: {self.project_path}")

        # Scan project files
        await self._scan_project_files()

        # Identify key files
        self._identify_key_files()

        # Detect project type and tech stack
        await self._detect_project_type()

        return {
            "project_id": self.project_id,
            "project_path": str(self.project_path),
            "total_files": len(self.context.files),
            "key_files": self.context.key_files,
            "project_type": self.context.project_type,
            "tech_stack": self.context.tech_stack
        }

    async def _scan_project_files(self):
        """Scan and track project files"""
        file_count = 0

        for root, dirs, files in os.walk(self.project_path):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]

            rel_root = Path(root).relative_to(self.project_path)
            if str(rel_root) != '.':
                self.context.directories.append(str(rel_root))

            for file in files:
                if file_count >= self.MAX_FILES:
                    logger.warning(f"[MemoryAgent] Max files ({self.MAX_FILES}) reached, stopping scan")
                    return

                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.project_path)

                # Only track relevant file types
                if file_path.suffix.lower() in self.TRACKED_EXTENSIONS:
                    try:
                        stat = file_path.stat()

                        # Calculate content hash for change detection
                        content_hash = None
                        if stat.st_size < 100000:  # Only hash files < 100KB
                            content = file_path.read_bytes()
                            content_hash = hashlib.md5(content).hexdigest()[:12]

                        self.context.files[str(rel_path)] = FileInfo(
                            path=str(rel_path),
                            exists=True,
                            size=stat.st_size,
                            last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            content_hash=content_hash,
                            language=self._detect_language(file_path)
                        )
                        file_count += 1

                    except Exception as e:
                        logger.warning(f"[MemoryAgent] Error scanning {rel_path}: {e}")

        logger.info(f"[MemoryAgent] Scanned {file_count} files in {len(self.context.directories)} directories")

    def _identify_key_files(self):
        """Identify important files in the project"""
        key_files = []

        for pattern in self.KEY_FILE_PATTERNS:
            for file_path in self.context.files:
                if Path(file_path).name == pattern:
                    key_files.append(file_path)

        # Also add entry point files
        entry_points = ['main.py', 'app.py', 'index.js', 'index.ts', 'server.js', 'server.ts']
        for entry in entry_points:
            for file_path in self.context.files:
                if Path(file_path).name == entry and file_path not in key_files:
                    key_files.append(file_path)

        self.context.key_files = key_files[:20]  # Limit to 20 key files
        logger.info(f"[MemoryAgent] Identified {len(self.context.key_files)} key files")

    async def _detect_project_type(self):
        """Detect project type and tech stack"""
        tech_stack = {}
        project_type = "Unknown"

        files = self.context.files

        # Check for package managers / project files
        if 'package.json' in files:
            tech_stack['package_manager'] = 'npm'
            # Read package.json for dependencies
            try:
                pkg_path = self.project_path / 'package.json'
                if pkg_path.exists():
                    pkg = json.loads(pkg_path.read_text())
                    deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}

                    if 'react' in deps:
                        tech_stack['frontend'] = 'React'
                        project_type = 'React Application'
                    elif 'vue' in deps:
                        tech_stack['frontend'] = 'Vue.js'
                        project_type = 'Vue.js Application'
                    elif 'next' in deps:
                        tech_stack['frontend'] = 'Next.js'
                        project_type = 'Next.js Application'
                    elif 'express' in deps:
                        tech_stack['backend'] = 'Express.js'
                        project_type = 'Express.js API'
            except Exception as e:
                logger.warning(f"[MemoryAgent] Error reading package.json: {e}")

        if 'requirements.txt' in files or 'pyproject.toml' in files:
            tech_stack['language'] = 'Python'
            # Check for frameworks
            for file_path in files:
                if 'fastapi' in file_path.lower() or 'main.py' in file_path:
                    tech_stack['backend'] = 'FastAPI'
                    project_type = 'FastAPI Application'
                    break
                elif 'django' in file_path.lower() or 'settings.py' in file_path:
                    tech_stack['backend'] = 'Django'
                    project_type = 'Django Application'
                    break
                elif 'flask' in file_path.lower():
                    tech_stack['backend'] = 'Flask'
                    project_type = 'Flask Application'
                    break

        # Check for database
        if any('models' in f or 'schema' in f for f in files):
            if any('.sql' in f for f in files):
                tech_stack['database'] = 'SQL'
            elif 'prisma' in str(files):
                tech_stack['database'] = 'Prisma'

        # Check for Docker
        if 'Dockerfile' in files or 'docker-compose.yml' in files:
            tech_stack['containerization'] = 'Docker'

        self.context.project_type = project_type
        self.context.tech_stack = tech_stack

        logger.info(f"[MemoryAgent] Detected project type: {project_type}, tech stack: {tech_stack}")

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension"""
        ext_to_lang = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript (React)',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript (React)',
            '.vue': 'Vue.js',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.sql': 'SQL',
            '.java': 'Java',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
        }
        return ext_to_lang.get(file_path.suffix.lower(), 'Unknown')

    def add_conversation_turn(
        self,
        role: str,
        content: str,
        files_mentioned: List[str] = None,
        actions_taken: List[str] = None,
        key_decisions: List[str] = None
    ):
        """Add a turn to conversation history"""
        turn = ConversationTurn(
            role=role,
            content=content[:2000],  # Limit content size
            files_mentioned=files_mentioned or [],
            actions_taken=actions_taken or [],
            key_decisions=key_decisions or []
        )
        self.conversation_history.append(turn)

        # Update goals/constraints if mentioned
        if key_decisions:
            self.context.goals.extend([d for d in key_decisions if 'goal' in d.lower()])
            self.context.constraints.extend([d for d in key_decisions if 'constraint' in d.lower() or 'must' in d.lower()])

    def record_file_change(
        self,
        file_path: str,
        change_type: str,  # created, modified, deleted
        summary: Optional[str] = None
    ):
        """Record a file change"""
        change = {
            "file": file_path,
            "type": change_type,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": summary
        }

        # Add to recent changes (limited)
        if len(self.context.recent_changes) >= self.MAX_RECENT_CHANGES:
            self.context.recent_changes.pop(0)
        self.context.recent_changes.append(change)

        # Update file info
        if change_type == "deleted":
            if file_path in self.context.files:
                self.context.files[file_path].exists = False
        elif change_type == "created":
            self.context.files[file_path] = FileInfo(
                path=file_path,
                exists=True,
                is_new=True,
                language=self._detect_language(Path(file_path))
            )
        elif change_type == "modified":
            if file_path in self.context.files:
                self.context.files[file_path].is_modified = True

        logger.info(f"[MemoryAgent] Recorded file change: {change_type} {file_path}")

    async def get_file_summary(self, file_path: str) -> Optional[str]:
        """Get AI-generated summary of a file"""
        # Check cache
        if file_path in self._summary_cache:
            return self._summary_cache[file_path]

        full_path = self.project_path / file_path
        if not full_path.exists():
            return None

        try:
            content = full_path.read_text()[:5000]  # Limit content

            # Generate summary using Claude
            response = await claude_client.generate(
                prompt=f"Summarize this file in 2-3 sentences. What does it do?\n\nFile: {file_path}\n\n```\n{content}\n```",
                system_prompt="You are a code summarizer. Be concise and focus on the main purpose.",
                model="haiku",
                max_tokens=200
            )

            summary = response.get("content", "")
            self._summary_cache[file_path] = summary

            # Update file info
            if file_path in self.context.files:
                self.context.files[file_path].summary = summary

            return summary

        except Exception as e:
            logger.warning(f"[MemoryAgent] Error summarizing {file_path}: {e}")
            return None

    def get_context_for_agent(self, agent_type: str) -> Dict[str, Any]:
        """
        Get relevant context for a specific agent.
        Different agents need different context.
        """
        base_context = {
            "project_id": self.project_id,
            "project_type": self.context.project_type,
            "tech_stack": self.context.tech_stack,
            "total_files": len(self.context.files),
            "key_files": self.context.key_files,
        }

        if agent_type == "planner":
            # Planner needs overview + recent changes + goals
            return {
                **base_context,
                "directories": self.context.directories[:20],
                "recent_changes": self.context.recent_changes[-10:],
                "goals": self.context.goals,
                "constraints": self.context.constraints,
                "conversation_summary": self._get_conversation_summary()
            }

        elif agent_type == "writer":
            # Writer needs file structure + recent context
            return {
                **base_context,
                "existing_files": list(self.context.files.keys())[:50],
                "recent_changes": self.context.recent_changes[-5:],
                "file_summaries": {
                    f: self.context.files[f].summary
                    for f in self.context.key_files
                    if f in self.context.files and self.context.files[f].summary
                }
            }

        elif agent_type == "fixer":
            # Fixer needs recent errors + modified files
            modified_files = [
                f for f, info in self.context.files.items()
                if info.is_modified or info.is_new
            ]
            return {
                **base_context,
                "modified_files": modified_files[-10:],
                "recent_changes": self.context.recent_changes[-10:],
            }

        elif agent_type == "runner":
            # Runner needs tech stack + commands context
            return {
                **base_context,
                "has_package_json": "package.json" in self.context.files,
                "has_requirements": "requirements.txt" in self.context.files,
                "has_docker": "Dockerfile" in self.context.files or "docker-compose.yml" in self.context.files,
            }

        else:
            return base_context

    def _get_conversation_summary(self) -> str:
        """Get a summary of recent conversation"""
        if not self.conversation_history:
            return "No previous conversation."

        recent = list(self.conversation_history)[-5:]
        summary_parts = []

        for turn in recent:
            if turn.role == "user":
                summary_parts.append(f"User asked: {turn.content[:100]}...")
            elif turn.actions_taken:
                summary_parts.append(f"Actions: {', '.join(turn.actions_taken[:3])}")
            elif turn.key_decisions:
                summary_parts.append(f"Decisions: {', '.join(turn.key_decisions[:3])}")

        return " | ".join(summary_parts) if summary_parts else "Recent activity tracked."

    def get_relevant_files(self, query: str, limit: int = 10) -> List[str]:
        """
        Get files relevant to a query/task.
        Simple keyword matching for now.
        """
        query_lower = query.lower()
        relevant = []

        for file_path in self.context.files:
            # Check if file path contains query terms
            if any(term in file_path.lower() for term in query_lower.split()):
                relevant.append(file_path)
            # Check if it's a key file
            elif file_path in self.context.key_files:
                relevant.append(file_path)

        return relevant[:limit]

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory state to dictionary (for persistence)"""
        return {
            "project_id": self.project_id,
            "project_path": str(self.project_path),
            "context": asdict(self.context),
            "conversation_history": [asdict(t) for t in self.conversation_history],
            "timestamp": datetime.utcnow().isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryAgent":
        """Restore memory agent from dictionary"""
        agent = cls(data["project_id"], data["project_path"])

        # Restore context
        ctx_data = data.get("context", {})
        agent.context.project_type = ctx_data.get("project_type")
        agent.context.tech_stack = ctx_data.get("tech_stack", {})
        agent.context.key_files = ctx_data.get("key_files", [])
        agent.context.goals = ctx_data.get("goals", [])
        agent.context.constraints = ctx_data.get("constraints", [])
        agent.context.recent_changes = ctx_data.get("recent_changes", [])

        # Restore files
        for file_path, file_data in ctx_data.get("files", {}).items():
            agent.context.files[file_path] = FileInfo(**file_data)

        # Restore conversation
        for turn_data in data.get("conversation_history", []):
            agent.conversation_history.append(ConversationTurn(**turn_data))

        return agent


# Singleton instance cache
_memory_agents: Dict[str, MemoryAgent] = {}


def get_memory_agent(project_id: str, project_path: str) -> MemoryAgent:
    """Get or create a memory agent for a project"""
    if project_id not in _memory_agents:
        _memory_agents[project_id] = MemoryAgent(project_id, project_path)
    return _memory_agents[project_id]


def clear_memory_agent(project_id: str):
    """Clear memory agent for a project"""
    if project_id in _memory_agents:
        del _memory_agents[project_id]
