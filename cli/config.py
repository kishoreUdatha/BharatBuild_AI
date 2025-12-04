"""
CLI Configuration Management
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


@dataclass
class CLIConfig:
    """Configuration for BharatBuild CLI"""

    # Model settings
    model: str = "haiku"
    max_tokens: int = 4096
    temperature: float = 0.7

    # Output settings
    output_format: str = "text"  # text, json, stream-json
    verbose: bool = False

    # Execution settings
    max_turns: int = 20  # Increased to allow for Generate→Run→Fix→Rerun loops
    working_directory: str = "."
    permission_mode: str = "ask"  # ask, auto, deny

    # Tool settings
    allowed_tools: Optional[List[str]] = None
    disallowed_tools: Optional[List[str]] = None

    # Prompt customization
    system_prompt: Optional[str] = None
    append_system_prompt: Optional[str] = None

    # Session settings
    non_interactive: bool = False
    continue_session: bool = False
    session_file: str = ".bharatbuild_session.json"

    # History settings
    history_file: str = ".bharatbuild_history"
    max_history: int = 1000

    # Theme settings
    theme: str = "auto"  # auto, dark, light
    syntax_theme: str = "monokai"

    # API settings
    api_base_url: str = "http://localhost:8000/api/v1"
    api_key: Optional[str] = None
    timeout: int = 300  # 5 minutes

    # Authentication (populated after login)
    auth_token: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    # Paths
    config_dir: str = field(default_factory=lambda: str(Path.home() / ".bharatbuild"))
    projects_dir: str = field(default_factory=lambda: str(Path.home() / ".bharatbuild" / "projects"))

    def __post_init__(self):
        """Initialize paths and directories"""
        # Ensure config directory exists
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)
        Path(self.projects_dir).mkdir(parents=True, exist_ok=True)

        # Set full paths for history and session files
        if not os.path.isabs(self.history_file):
            self.history_file = str(Path(self.config_dir) / self.history_file)
        if not os.path.isabs(self.session_file):
            self.session_file = str(Path(self.config_dir) / self.session_file)

    def load_from_file(self, config_path: str) -> None:
        """Load configuration from JSON file"""
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                for key, value in data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)

    def save_to_file(self, config_path: Optional[str] = None) -> None:
        """Save configuration to JSON file"""
        path = Path(config_path or (Path(self.config_dir) / "config.json"))
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load_default(cls) -> "CLIConfig":
        """Load default configuration from user config directory"""
        config = cls()
        default_config_path = Path(config.config_dir) / "config.json"
        if default_config_path.exists():
            config.load_from_file(str(default_config_path))

        # Override with environment variables
        config._load_from_env()

        return config

    def _load_from_env(self) -> None:
        """Load configuration from environment variables"""
        env_mappings = {
            "BHARATBUILD_MODEL": "model",
            "BHARATBUILD_API_URL": "api_base_url",
            "BHARATBUILD_API_KEY": "api_key",
            "BHARATBUILD_WORKING_DIR": "working_directory",
            "BHARATBUILD_PERMISSION_MODE": "permission_mode",
            "BHARATBUILD_MAX_TURNS": ("max_turns", int),
            "BHARATBUILD_VERBOSE": ("verbose", lambda x: x.lower() == "true"),
            "ANTHROPIC_API_KEY": "api_key",  # Also support Anthropic's env var
        }

        for env_var, mapping in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                if isinstance(mapping, tuple):
                    attr, converter = mapping
                    setattr(self, attr, converter(value))
                else:
                    setattr(self, mapping, value)

    def get_tool_permissions(self, tool_name: str) -> bool:
        """Check if a tool is allowed"""
        # Check disallowed first
        if self.disallowed_tools and tool_name in self.disallowed_tools:
            return False

        # If allowed_tools is set, tool must be in the list
        if self.allowed_tools:
            return tool_name in self.allowed_tools

        # Default: allow
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return asdict(self)
