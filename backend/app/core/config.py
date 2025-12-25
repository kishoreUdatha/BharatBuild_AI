from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Dict, Any, Optional
import os
import json
from pathlib import Path


def parse_cors_origins(v: Any) -> List[str]:
    """Parse CORS origins from string or list"""
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        # Try JSON parsing first
        if v.startswith('['):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        # Fall back to comma-separated
        return [origin.strip() for origin in v.split(',') if origin.strip()]
    return []


def parse_extensions(v: Any) -> List[str]:
    """Parse allowed extensions from string or list"""
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        if v.startswith('['):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        return [ext.strip() for ext in v.split(',') if ext.strip()]
    return []


def parse_promo_codes(v: str) -> Dict[str, int]:
    """Parse promo codes from environment variable format: CODE1:tokens,CODE2:tokens"""
    if not v:
        return {}
    codes = {}
    for item in v.split(','):
        if ':' in item:
            code, tokens = item.strip().split(':')
            codes[code.strip()] = int(tokens.strip())
    return codes


def parse_token_package(v: str) -> Dict[str, Any]:
    """Parse token package from format: tokens,price_in_paise,name"""
    if not v:
        return {}
    parts = v.split(',')
    if len(parts) >= 3:
        return {
            "tokens": int(parts[0].strip()),
            "price": int(parts[1].strip()),
            "name": parts[2].strip()
        }
    return {}


class Settings(BaseSettings):
    """Application settings - all configurable via environment variables"""

    # ==========================================
    # Application
    # ==========================================
    APP_NAME: str = "BharatBuild AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str
    API_VERSION: str = "v1"

    # Server Configuration
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # ==========================================
    # Database
    # ==========================================
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 0
    DB_ECHO: bool = False

    # ==========================================
    # Redis
    # ==========================================
    REDIS_URL: str
    REDIS_CACHE_DB: int = 1

    # ==========================================
    # Celery
    # ==========================================
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_TIME_LIMIT: int = 3600  # 1 hour
    CELERY_TASK_SOFT_TIME_LIMIT: int = 3000  # 50 minutes
    CELERY_RESULT_EXPIRES: int = 86400  # 24 hours

    # ==========================================
    # Claude AI
    # ==========================================
    ANTHROPIC_API_KEY: str
    ANTHROPIC_BASE_URL: str = ""  # Empty means use default Anthropic URL
    USE_MOCK_CLAUDE: bool = False
    CLAUDE_HAIKU_MODEL: str = "claude-3-5-haiku-20241022"
    CLAUDE_SONNET_MODEL: str = "claude-sonnet-4-20250514"
    CLAUDE_MAX_TOKENS: int = 4096
    CLAUDE_TEMPERATURE: float = 0.7
    USE_PLAIN_TEXT_RESPONSES: bool = True
    CLAUDE_REQUEST_TIMEOUT: int = 300  # 5 minutes for large document generations
    CLAUDE_CONNECT_TIMEOUT: int = 60  # seconds
    CLAUDE_MAX_RETRIES: int = 5
    CLAUDE_RETRY_BASE_DELAY: float = 2.0  # seconds
    CLAUDE_RETRY_MAX_DELAY: float = 30.0  # seconds

    # ==========================================
    # Storage Configuration
    # ==========================================
    STORAGE_MODE: str = "local"  # "local", "s3", or "minio"

    # AWS S3 / MinIO
    USE_MINIO: bool = True
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = ""  # Primary bucket name
    S3_BUCKET: str = ""  # Alias for S3_BUCKET_NAME (used in ECS task definition)
    MINIO_ENDPOINT: str = "localhost:9000"
    STORAGE_URL_EXPIRY: int = 3600  # 1 hour

    @property
    def effective_bucket_name(self) -> str:
        """Get the effective S3 bucket name (supports both S3_BUCKET and S3_BUCKET_NAME)"""
        return self.S3_BUCKET or self.S3_BUCKET_NAME or "bharatbuild-projects"

    # ==========================================
    # Authentication
    # ==========================================
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours - long sessions for better UX
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days refresh token
    BCRYPT_ROUNDS: int = 12  # 4 for dev (fast), 12 for prod (secure)

    # ==========================================
    # Google OAuth
    # ==========================================
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/auth/callback/google"

    # ==========================================
    # GitHub OAuth
    # ==========================================
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://localhost:3000/auth/callback/github"

    # ==========================================
    # Frontend URL (for OAuth callbacks)
    # ==========================================
    FRONTEND_URL: str = "http://localhost:3000"

    # ==========================================
    # Payment Gateway
    # ==========================================
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    PAYMENT_BASE_URL: str = "https://payment.example.com"

    # ==========================================
    # Email
    # ==========================================
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@bharatbuild.ai"
    EMAIL_FROM_NAME: str = "BharatBuild AI"

    # SendGrid Configuration (preferred for bulk emails)
    SENDGRID_API_KEY: str = ""
    USE_SENDGRID: bool = True  # Use SendGrid when API key is available

    # ==========================================
    # Frontend
    # ==========================================
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000/api/v1"
    NEXT_PUBLIC_WS_URL: str = "ws://localhost:8000/ws"

    # ==========================================
    # CORS (stored as comma-separated string, parsed to list)
    # ==========================================
    CORS_ORIGINS_STR: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,http://localhost:3004,http://localhost:3005,http://localhost:3006,http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002,http://127.0.0.1:3003,http://127.0.0.1:3004,http://127.0.0.1:3005,http://127.0.0.1:3006"

    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return parse_cors_origins(self.CORS_ORIGINS_STR)

    # ==========================================
    # Rate Limiting
    # ==========================================
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # ==========================================
    # File Upload
    # ==========================================
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    ALLOWED_EXTENSIONS_STR: str = "pdf,doc,docx,txt,png,jpg,jpeg"

    @property
    def ALLOWED_EXTENSIONS(self) -> List[str]:
        """Parse allowed extensions from comma-separated string"""
        return parse_extensions(self.ALLOWED_EXTENSIONS_STR)

    # ==========================================
    # Logging
    # ==========================================
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # ==========================================
    # Token System Configuration
    # ==========================================
    # Free Tier Settings
    FREE_TIER_TOKENS: int = 10000
    FREE_TIER_MONTHLY_ALLOWANCE: int = 10000

    # Token Limits
    MAX_TOKENS_PER_REQUEST: int = 8192
    MAX_REQUESTS_PER_DAY: int = 100

    # Mock Token Data (for development)
    DEV_MOCK_TOTAL_TOKENS: int = 100000
    DEV_MOCK_USED_TOKENS: int = 5000
    DEV_MOCK_MONTHLY_ALLOWANCE: int = 50000

    # Token Packages (parsed from environment)
    TOKEN_PACKAGE_STARTER: str = "50000,9900,Starter Pack"
    TOKEN_PACKAGE_PRO: str = "200000,34900,Pro Pack"
    TOKEN_PACKAGE_UNLIMITED: str = "1000000,149900,Unlimited Pack"
    TOKEN_PACKAGE_COMPLETE: str = "500000,449900,Premium"  # ₹4,499 one-time

    # Monthly Plans
    MONTHLY_PLAN_FREE: str = "10000,0,Free Tier"
    MONTHLY_PLAN_BASIC: str = "50000,29900,Basic"
    MONTHLY_PLAN_PRO: str = "250000,99900,Pro"

    # Promo Codes (format: CODE1:tokens,CODE2:tokens)
    PROMO_CODES: str = "WELCOME2024:10000,LAUNCH50:50000,BETA100:100000"

    # ==========================================
    # Container Execution - CENTRALIZED TIMEOUT CONFIGURATION
    # Single source of truth for all container lifecycle settings
    # ==========================================
    CONTAINER_MEMORY_LIMIT: str = "512m"
    CONTAINER_CPU_LIMIT: float = 0.5
    CONTAINER_CPU_PERIOD: int = 100000
    CONTAINER_CPU_QUOTA: int = 50000
    DEFAULT_CONTAINER_PORT: int = 3000
    BACKEND_DEFAULT_PORT: int = 8001
    CONTAINER_PORT_RANGE_START: int = 10000
    CONTAINER_PORT_RANGE_END: int = 60000

    # Container Lifecycle Timeouts (CENTRALIZED - used by all cleanup services)
    CONTAINER_IDLE_TIMEOUT_SECONDS: int = 1800  # 30 minutes - idle before cleanup
    CONTAINER_MAX_LIFETIME_SECONDS: int = 86400  # 24 hours - absolute max lifetime
    CONTAINER_COMMAND_TIMEOUT: int = 300  # 5 minutes - single command timeout
    CONTAINER_PAUSE_AFTER_IDLE_SECONDS: int = 300  # 5 minutes - pause (not delete) after idle
    CONTAINER_CLEANUP_INTERVAL_SECONDS: int = 60  # 1 minute - how often to check for expired

    # Legacy aliases for backwards compatibility
    CONTAINER_MAX_LIFETIME: int = 86400  # Deprecated: use CONTAINER_MAX_LIFETIME_SECONDS

    # Container Reuse Settings
    CONTAINER_REUSE_ENABLED: bool = True  # Reuse existing containers instead of creating new
    CONTAINER_HEALTH_CHECK_TIMEOUT: int = 5  # Seconds to wait for health check

    # Docker TLS Settings (for secure remote Docker API)
    DOCKER_TLS_ENABLED: bool = True  # Enable TLS for Docker API
    DOCKER_TLS_VERIFY: bool = True  # Verify TLS certificates
    DOCKER_TLS_CA_CERT: str = "/certs/ca.pem"
    DOCKER_TLS_CLIENT_CERT: str = "/certs/client-cert.pem"
    DOCKER_TLS_CLIENT_KEY: str = "/certs/client-key.pem"

    # Redis Container State Settings
    REDIS_CONTAINER_STATE_PREFIX: str = "container:"
    REDIS_CONTAINER_STATE_TTL: int = 86400  # 24 hours

    # Sandbox Cleanup Settings
    SANDBOX_PATH: str = "C:/tmp/sandbox/workspace"  # Default for Windows, override in env
    SANDBOX_MIN_AGE_MINUTES: int = 5  # Don't delete projects younger than this

    # ==========================================
    # Shared Database Infrastructure (Production)
    # ==========================================
    # When USE_SHARED_DB_INFRASTRUCTURE=True:
    # - All projects share a central database cluster
    # - Each project gets its own database/schema dynamically
    # - No per-project database containers needed
    # - Much more efficient for 100K+ users
    #
    # Database Isolation Strategy:
    # - PostgreSQL: Separate database per project (project_abc123)
    # - MySQL: Separate database per project
    # - MongoDB: Separate database per project
    # - Redis: Key prefix per project (project_abc123:*)
    # ==========================================
    USE_SHARED_DB_INFRASTRUCTURE: bool = False  # Set True in production

    # PostgreSQL Infrastructure
    INFRA_POSTGRES_HOST: str = "localhost"
    INFRA_POSTGRES_PORT: int = 5432
    INFRA_POSTGRES_USER: str = "postgres"
    INFRA_POSTGRES_PASSWORD: str = "postgres"

    # MySQL Infrastructure
    INFRA_MYSQL_HOST: str = "localhost"
    INFRA_MYSQL_PORT: int = 3306
    INFRA_MYSQL_USER: str = "root"
    INFRA_MYSQL_PASSWORD: str = "password"

    # MongoDB Infrastructure
    INFRA_MONGO_HOST: str = "localhost"
    INFRA_MONGO_PORT: int = 27017
    INFRA_MONGO_USER: str = ""
    INFRA_MONGO_PASSWORD: str = ""

    # Redis Infrastructure
    INFRA_REDIS_HOST: str = "localhost"
    INFRA_REDIS_PORT: int = 6379

    # Database Password Secret (for generating per-project passwords)
    DB_PASSWORD_SECRET: str = "bharatbuild-secret-key-change-in-production"

    # ==========================================
    # Ephemeral Database Cleanup (Cost Optimization)
    # ==========================================
    # Delete inactive project databases to save costs
    # Without cleanup: 100K users = $1,500-3,000/month
    # With cleanup: 100K users = $25-100/month
    # ==========================================
    EPHEMERAL_CLEANUP_ENABLED: bool = True

    # Cleanup intervals by user tier (in minutes)
    EPHEMERAL_FREE_TIER_MINUTES: int = 30       # Free users: 30 min
    EPHEMERAL_BASIC_TIER_MINUTES: int = 120     # Basic users: 2 hours
    EPHEMERAL_PRO_TIER_MINUTES: int = 1440      # Pro users: 24 hours

    # Cleanup check interval (how often to scan for expired databases)
    EPHEMERAL_CLEANUP_INTERVAL_SECONDS: int = 60  # Check every minute

    # Warning before cleanup (notify user X minutes before deletion)
    EPHEMERAL_WARNING_MINUTES: int = 5

    # ==========================================
    # Health Monitor Settings
    # ==========================================
    HEALTH_RESTART_DELAY: int = 5  # seconds
    HEALTH_RESET_AFTER: int = 300  # seconds
    HEALTH_CHECK_INTERVAL: int = 30  # seconds
    HEALTH_MAX_FAILURES: int = 3

    # ==========================================
    # Cache TTL Settings (in seconds)
    # ==========================================
    CACHE_TTL_PROJECT_META: int = 3600  # 1 hour
    CACHE_TTL_PROJECT_FILES: int = 900  # 15 minutes
    CACHE_TTL_FILE_CONTENT: int = 300  # 5 minutes
    CACHE_TTL_USER_SESSION: int = 1800  # 30 minutes

    # ==========================================
    # Session Storage Settings
    # ==========================================
    SESSION_TTL_SECONDS: int = 3600  # 1 hour
    SESSION_CLEANUP_INTERVAL: int = 300  # 5 minutes

    # ==========================================
    # File Storage Settings
    # ==========================================
    FILE_INLINE_THRESHOLD: int = 10240  # 10KB - files below this stored inline in PostgreSQL
    MAX_CONCURRENT_FILE_OPS: int = 10  # Max parallel file operations

    # ==========================================
    # Agent Settings
    # ==========================================
    AGENT_BATCH_SIZE: int = 3
    AGENT_MAX_RETRIES: int = 3
    AGENT_MAX_AUTO_FIXES: int = 3

    # ==========================================
    # Auto-Fixer Settings
    # ==========================================
    AUTOFIXER_MAX_ATTEMPTS: int = 10  # Max fix attempts before giving up
    AUTOFIXER_COOLDOWN_SECONDS: int = 10  # Cooldown between fixes
    AUTOFIXER_FIX_COOLDOWN_SECONDS: int = 30  # Min seconds between fix attempts
    AUTOFIXER_FIX_WINDOW_SECONDS: int = 300  # 5 min window for max attempts
    AUTOFIXER_INSTALL_TIMEOUT: int = 120  # Timeout for install commands
    LOG_RETENTION_MINUTES: int = 30  # Log bus retention

    # ==========================================
    # Timeouts and Intervals (in seconds/milliseconds as noted)
    # ==========================================
    SESSION_TTL: int = 3600  # 1 hour in seconds
    CACHE_TTL: int = 3600  # 1 hour in seconds
    API_REQUEST_TIMEOUT: int = 30  # seconds
    HEALTH_CHECK_TIMEOUT: int = 5  # seconds
    RECONNECTION_MAX_RETRIES: int = 5
    RECONNECTION_BASE_DELAY: int = 1000  # milliseconds
    HEARTBEAT_INTERVAL: int = 30000  # milliseconds

    # ==========================================
    # Buffer Sizes
    # ==========================================
    MAX_BUFFER_SIZE: int = 50000
    MAX_CONTEXT_TOKENS: int = 50000

    # ==========================================
    # API Key Settings
    # ==========================================
    API_KEY_RATE_LIMIT_PER_DAY: int = 10000

    # ==========================================
    # Agentic Defaults
    # ==========================================
    DEFAULT_AI_MODEL: str = "sonnet"
    DEFAULT_MAX_RESPONSE_TOKENS: int = 8192

    # ==========================================
    # Domain Configuration
    # ==========================================
    APP_DOMAIN: str = "bharatbuild.ai"
    SHARE_URL_BASE: str = "https://bharatbuild.ai/share"

    # ==========================================
    # Project Cleanup
    # ==========================================
    PROJECT_CLEANUP_DAYS: int = 7

    # ==========================================
    # Project Complexity File Limits
    # ==========================================
    FILE_LIMIT_MINIMAL: int = 8
    FILE_LIMIT_SIMPLE: int = 15
    FILE_LIMIT_INTERMEDIATE: int = 30
    FILE_LIMIT_INTERMEDIATE_BACKEND: int = 45
    FILE_LIMIT_COMPLEX: int = 60

    # Technology-specific limits
    FILE_LIMIT_FLUTTER_SIMPLE: int = 20
    FILE_LIMIT_FLUTTER_COMPLEX: int = 40
    FILE_LIMIT_SPRING_BOOT_SIMPLE: int = 20
    FILE_LIMIT_SPRING_BOOT_COMPLEX: int = 50
    FILE_LIMIT_DJANGO_SIMPLE: int = 18
    FILE_LIMIT_DJANGO_COMPLEX: int = 35
    FILE_LIMIT_AI_ML: int = 18

    # ==========================================
    # Per-User Project Quotas (for 100K+ users scale)
    # ==========================================
    # Free tier limits
    MAX_PROJECTS_FREE_TIER: int = 5  # Max projects for free users
    MAX_STORAGE_FREE_TIER_MB: int = 100  # 100MB storage per free user
    MAX_CONCURRENT_BUILDS_FREE: int = 1  # 1 concurrent build

    # Basic tier limits
    MAX_PROJECTS_BASIC_TIER: int = 25  # Max projects for basic users
    MAX_STORAGE_BASIC_TIER_MB: int = 500  # 500MB storage per basic user
    MAX_CONCURRENT_BUILDS_BASIC: int = 2  # 2 concurrent builds

    # Pro tier limits
    MAX_PROJECTS_PRO_TIER: int = 100  # Max projects for pro users
    MAX_STORAGE_PRO_TIER_MB: int = 2048  # 2GB storage per pro user
    MAX_CONCURRENT_BUILDS_PRO: int = 5  # 5 concurrent builds

    # Unlimited tier limits
    MAX_PROJECTS_UNLIMITED_TIER: int = 500  # Max projects for unlimited users
    MAX_STORAGE_UNLIMITED_TIER_MB: int = 10240  # 10GB storage per unlimited user
    MAX_CONCURRENT_BUILDS_UNLIMITED: int = 10  # 10 concurrent builds

    # Per-project limits
    MAX_FILES_PER_PROJECT: int = 200  # Max files in any single project
    MAX_FILE_SIZE_MB: int = 10  # Max single file size
    MAX_PROJECT_SIZE_MB: int = 50  # Max total size per project

    # ==========================================
    # Sandbox Cleanup Settings (Bolt.new style ephemeral storage)
    # ==========================================
    SANDBOX_PATH: str = "C:/tmp/sandbox/workspace"  # Ephemeral storage path
    SANDBOX_IDLE_TIMEOUT_MINUTES: int = 120  # Delete projects after 2 hours idle (development mode)
    SANDBOX_CLEANUP_INTERVAL_MINUTES: int = 5  # Check every 5 minutes
    SANDBOX_MIN_AGE_MINUTES: int = 5  # Don't delete projects younger than 5 min
    SANDBOX_CLEANUP_ENABLED: bool = True  # Enable/disable auto-cleanup

    # ==========================================
    # Storage Paths (configurable via env)
    # ==========================================
    USER_PROJECTS_PATH: str  # External path for generated projects (required)
    DOCUMENTS_PATH: str = "C:/tmp/documents"  # Separate path for documents (reports, SRS, PPT)
    DIAGRAMS_PATH: str = "C:/tmp/diagrams"  # Separate path for UML diagrams

    # ==========================================
    # Paths (computed, not from env)
    # ==========================================

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env that aren't defined in Settings

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize paths after pydantic validation
        self._base_dir = Path(__file__).resolve().parent.parent.parent
        self._upload_dir = self._base_dir / "uploads"
        self._temp_dir = self._base_dir / "temp"
        self._generated_dir = self._base_dir / "generated"
        self._user_projects_dir = Path(self.USER_PROJECTS_PATH)
        self._documents_dir = Path(self.DOCUMENTS_PATH)
        self._diagrams_dir = Path(self.DIAGRAMS_PATH)

        # Create directories if they don't exist
        self._upload_dir.mkdir(exist_ok=True, parents=True)
        self._temp_dir.mkdir(exist_ok=True, parents=True)
        self._generated_dir.mkdir(exist_ok=True, parents=True)
        self._user_projects_dir.mkdir(exist_ok=True, parents=True)
        self._documents_dir.mkdir(exist_ok=True, parents=True)
        self._diagrams_dir.mkdir(exist_ok=True, parents=True)
        Path(self.LOG_FILE).parent.mkdir(exist_ok=True, parents=True)

    @property
    def BASE_DIR(self) -> Path:
        return self._base_dir

    @property
    def UPLOAD_DIR(self) -> Path:
        return self._upload_dir

    @property
    def TEMP_DIR(self) -> Path:
        return self._temp_dir

    @property
    def GENERATED_DIR(self) -> Path:
        return self._generated_dir

    @property
    def USER_PROJECTS_DIR(self) -> Path:
        return self._user_projects_dir

    @property
    def DOCUMENTS_DIR(self) -> Path:
        return self._documents_dir

    @property
    def DIAGRAMS_DIR(self) -> Path:
        return self._diagrams_dir

    def get_project_docs_dir(self, project_id: str, user_id: str = None) -> Path:
        """
        Get the docs directory for a specific project - stored OUTSIDE sandbox.
        Now supports user isolation: /documents/<user_id>/<project_id>/
        """
        if user_id:
            docs_dir = self._documents_dir / user_id / project_id
        else:
            docs_dir = self._documents_dir / project_id
        docs_dir.mkdir(parents=True, exist_ok=True)
        return docs_dir

    def get_project_diagrams_dir(self, project_id: str, user_id: str = None) -> Path:
        """
        Get the diagrams directory for a specific project - stored OUTSIDE sandbox.
        Now supports user isolation: /diagrams/<user_id>/<project_id>/
        """
        if user_id:
            diagrams_dir = self._diagrams_dir / user_id / project_id
        else:
            diagrams_dir = self._diagrams_dir / project_id
        diagrams_dir.mkdir(parents=True, exist_ok=True)
        return diagrams_dir

    # ==========================================
    # Helper Methods for Token Configuration
    # ==========================================
    def get_token_packages(self) -> Dict[str, Dict[str, Any]]:
        """Get token packages as a dictionary"""
        return {
            "starter": parse_token_package(self.TOKEN_PACKAGE_STARTER),
            "pro": parse_token_package(self.TOKEN_PACKAGE_PRO),
            "unlimited": parse_token_package(self.TOKEN_PACKAGE_UNLIMITED),
            "complete": parse_token_package(self.TOKEN_PACKAGE_COMPLETE)
        }

    def get_monthly_plans(self) -> Dict[str, Dict[str, Any]]:
        """Get monthly plans as a dictionary"""
        return {
            "free": parse_token_package(self.MONTHLY_PLAN_FREE),
            "basic": parse_token_package(self.MONTHLY_PLAN_BASIC),
            "pro": parse_token_package(self.MONTHLY_PLAN_PRO)
        }

    def get_promo_codes(self) -> Dict[str, int]:
        """Get promo codes as a dictionary"""
        return parse_promo_codes(self.PROMO_CODES)

    def get_mock_token_data(self) -> Dict[str, Any]:
        """Get mock token data for development mode"""
        return {
            "total_tokens": self.DEV_MOCK_TOTAL_TOKENS,
            "used_tokens": self.DEV_MOCK_USED_TOKENS,
            "remaining_tokens": self.DEV_MOCK_TOTAL_TOKENS - self.DEV_MOCK_USED_TOKENS,
            "monthly_allowance": self.DEV_MOCK_MONTHLY_ALLOWANCE,
            "monthly_used": self.DEV_MOCK_USED_TOKENS,
            "monthly_remaining": self.DEV_MOCK_MONTHLY_ALLOWANCE - self.DEV_MOCK_USED_TOKENS,
        }

    def is_dev_mode(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT == "development" or self.DEBUG

    def get_payment_url(self, purchase_id: str) -> str:
        """Get payment URL for a purchase"""
        return f"{self.PAYMENT_BASE_URL}/pay/{purchase_id}"

    def get_share_url(self, project_id: str) -> str:
        """Get share URL for a project"""
        return f"{self.SHARE_URL_BASE}/{project_id}"

    def get_complexity_config(self) -> Dict[str, Any]:
        """
        Load complexity configuration from agent_config.yml with .env overrides.
        Returns file limits, keywords, and tech stacks for project complexity detection.
        """
        import yaml

        config_path = self.BASE_DIR / "app" / "config" / "agent_config.yml"
        complexity_config = {}

        # Load from YAML
        try:
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)
                complexity_config = yaml_config.get('complexity', {})
        except Exception as e:
            print(f"Warning: Could not load agent_config.yml: {e}")

        # Override with .env values (environment takes priority)
        file_limits = complexity_config.get('file_limits', {})
        file_limits['minimal'] = self.FILE_LIMIT_MINIMAL
        file_limits['simple'] = self.FILE_LIMIT_SIMPLE
        file_limits['intermediate'] = self.FILE_LIMIT_INTERMEDIATE
        file_limits['intermediate_with_backend'] = self.FILE_LIMIT_INTERMEDIATE_BACKEND
        file_limits['complex'] = self.FILE_LIMIT_COMPLEX
        complexity_config['file_limits'] = file_limits

        # Technology-specific overrides
        tech_limits = complexity_config.get('technology_limits', {})
        tech_limits['flutter'] = {
            'simple': self.FILE_LIMIT_FLUTTER_SIMPLE,
            'complex': self.FILE_LIMIT_FLUTTER_COMPLEX
        }
        tech_limits['react_native'] = {
            'simple': self.FILE_LIMIT_FLUTTER_SIMPLE,  # Same as Flutter
            'complex': self.FILE_LIMIT_FLUTTER_COMPLEX
        }
        tech_limits['spring_boot'] = {
            'simple': self.FILE_LIMIT_SPRING_BOOT_SIMPLE,
            'complex': self.FILE_LIMIT_SPRING_BOOT_COMPLEX
        }
        tech_limits['django'] = {
            'simple': self.FILE_LIMIT_DJANGO_SIMPLE,
            'complex': self.FILE_LIMIT_DJANGO_COMPLEX
        }
        tech_limits['ai_ml'] = {
            'default': self.FILE_LIMIT_AI_ML
        }
        complexity_config['technology_limits'] = tech_limits

        return complexity_config


# Create settings instance
settings = Settings()
