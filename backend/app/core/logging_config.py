"""
BharatBuild AI - Centralized Logging Configuration
Supports both development (plain text) and production (JSON structured) logging
"""

import logging
import sys
import json
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional
from contextvars import ContextVar

from app.core.config import settings


# Context variables for request tracing
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')
project_id_var: ContextVar[str] = ContextVar('project_id', default='')


def get_request_id() -> str:
    """Get current request ID from context"""
    return request_id_var.get() or ''


def set_request_id(request_id: str) -> None:
    """Set request ID in context"""
    request_id_var.set(request_id)


def get_user_id() -> str:
    """Get current user ID from context"""
    return user_id_var.get() or ''


def set_user_id(user_id: str) -> None:
    """Set user ID in context"""
    user_id_var.set(user_id)


def get_project_id() -> str:
    """Get current project ID from context"""
    return project_id_var.get() or ''


def set_project_id(project_id: str) -> None:
    """Set project ID in context"""
    project_id_var.set(project_id)


def generate_request_id() -> str:
    """Generate a unique request ID"""
    return str(uuid.uuid4())[:8]


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging in production
    Outputs logs in a format easily parsed by log aggregation tools (ELK, CloudWatch, etc.)
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context from context variables
        request_id = get_request_id()
        if request_id:
            log_data["request_id"] = request_id

        user_id = get_user_id()
        if user_id:
            log_data["user_id"] = user_id

        project_id = get_project_id()
        if project_id:
            log_data["project_id"] = project_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info) if record.exc_info[0] else None
            }

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'pathname', 'process', 'processName', 'relativeCreated',
                          'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
                          'message', 'taskName']:
                if not key.startswith('_'):
                    log_data[key] = value

        return json.dumps(log_data, default=str)


class ContextualFormatter(logging.Formatter):
    """
    Enhanced formatter that includes context variables (request_id, user_id, etc.)
    Used for development with readable output
    """

    def format(self, record: logging.LogRecord) -> str:
        # Add context to the record
        record.request_id = get_request_id() or '-'
        record.user_id = get_user_id() or '-'
        record.project_id = get_project_id() or '-'

        return super().format(record)


class BharatBuildLogger(logging.Logger):
    """
    Custom logger with convenience methods for structured logging
    """

    def log_request(self, method: str, path: str, status_code: int,
                    duration_ms: float, **kwargs) -> None:
        """Log HTTP request details"""
        self.info(
            f"HTTP {method} {path} - {status_code} ({duration_ms:.2f}ms)",
            extra={
                "event_type": "http_request",
                "http_method": method,
                "http_path": path,
                "http_status": status_code,
                "duration_ms": duration_ms,
                **kwargs
            }
        )

    def log_db_query(self, operation: str, table: str, duration_ms: float,
                     rows_affected: int = 0, **kwargs) -> None:
        """Log database query details"""
        self.debug(
            f"DB {operation} on {table} - {rows_affected} rows ({duration_ms:.2f}ms)",
            extra={
                "event_type": "db_query",
                "db_operation": operation,
                "db_table": table,
                "duration_ms": duration_ms,
                "rows_affected": rows_affected,
                **kwargs
            }
        )

    def log_auth_event(self, event: str, success: bool, user_email: str = None,
                       reason: str = None, **kwargs) -> None:
        """Log authentication events"""
        level = logging.INFO if success else logging.WARNING
        self.log(
            level,
            f"Auth {event}: {'success' if success else 'failed'}" +
            (f" - {user_email}" if user_email else "") +
            (f" - {reason}" if reason else ""),
            extra={
                "event_type": "auth",
                "auth_event": event,
                "auth_success": success,
                "user_email": user_email,
                "failure_reason": reason,
                **kwargs
            }
        )

    def log_agent_event(self, agent_name: str, event: str,
                        tokens_used: int = 0, **kwargs) -> None:
        """Log AI agent events"""
        self.info(
            f"Agent {agent_name}: {event}" +
            (f" (tokens: {tokens_used})" if tokens_used else ""),
            extra={
                "event_type": "agent",
                "agent_name": agent_name,
                "agent_event": event,
                "tokens_used": tokens_used,
                **kwargs
            }
        )

    def log_error_with_context(self, error: Exception, context: str = None,
                               **kwargs) -> None:
        """Log error with full context"""
        self.error(
            f"Error in {context}: {type(error).__name__}: {str(error)}",
            exc_info=True,
            extra={
                "event_type": "error",
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_context": context,
                **kwargs
            }
        )

    def log_performance(self, operation: str, duration_ms: float,
                        threshold_ms: float = 1000, **kwargs) -> None:
        """Log performance metrics, warn if over threshold"""
        level = logging.WARNING if duration_ms > threshold_ms else logging.DEBUG
        self.log(
            level,
            f"Performance: {operation} took {duration_ms:.2f}ms" +
            (f" (threshold: {threshold_ms}ms)" if duration_ms > threshold_ms else ""),
            extra={
                "event_type": "performance",
                "operation": operation,
                "duration_ms": duration_ms,
                "threshold_ms": threshold_ms,
                "exceeded_threshold": duration_ms > threshold_ms,
                **kwargs
            }
        )


def setup_logging() -> BharatBuildLogger:
    """Setup logging configuration based on environment"""

    # Register custom logger class
    logging.setLoggerClass(BharatBuildLogger)

    # Create logger
    logger = logging.getLogger("bharatbuild")
    logger.__class__ = BharatBuildLogger  # Ensure it's our custom class
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Clear existing handlers
    logger.handlers.clear()

    # Determine if production (use JSON) or development (use plain text)
    is_production = settings.ENVIRONMENT == "production"

    if is_production:
        # Production: JSON formatted logs for log aggregation
        json_formatter = JSONFormatter()

        # Console handler - JSON format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(json_formatter)
        logger.addHandler(console_handler)

        # File handler - JSON format
        if settings.LOG_FILE:
            log_file = Path(settings.LOG_FILE)
            log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10485760,  # 10MB
                backupCount=10
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(json_formatter)
            logger.addHandler(file_handler)

    else:
        # Development: Human-readable format with colors
        detailed_format = (
            "%(asctime)s | %(levelname)-8s | "
            "[%(request_id)s] [%(user_id)s] | "
            "%(funcName)s:%(lineno)d | %(message)s"
        )
        simple_format = "%(levelname)-8s | %(message)s"

        detailed_formatter = ContextualFormatter(detailed_format)
        simple_formatter = ContextualFormatter(simple_format)

        # Console handler - simple format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)

        # File handler - detailed format
        if settings.LOG_FILE:
            log_file = Path(settings.LOG_FILE)
            log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10485760,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger.info(
        f"Logging initialized",
        extra={
            "environment": settings.ENVIRONMENT,
            "log_level": settings.LOG_LEVEL,
            "json_logging": is_production
        }
    )

    return logger


# Create logger instance
logger: BharatBuildLogger = setup_logging()


# Convenience exports
__all__ = [
    'logger',
    'setup_logging',
    'get_request_id',
    'set_request_id',
    'get_user_id',
    'set_user_id',
    'get_project_id',
    'set_project_id',
    'generate_request_id',
    'BharatBuildLogger',
]
