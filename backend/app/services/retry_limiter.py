"""
Retry Limiter - Controls retry behavior for auto-fixer

Prevents:
1. Infinite retry loops
2. Runaway API costs
3. Repeated failed fix attempts

Bolt.new pattern: N retries max (usually 2-3)
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import threading

from app.core.logging_config import logger


@dataclass
class RetryState:
    """State for a single error fix attempt"""
    error_hash: str
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    fixed: bool = False
    errors_seen: list = field(default_factory=list)


@dataclass
class ProjectRetryState:
    """Retry state for an entire project"""
    project_id: str
    total_attempts: int = 0
    total_tokens_used: int = 0
    errors: Dict[str, RetryState] = field(default_factory=dict)
    session_start: datetime = field(default_factory=datetime.utcnow)
    last_successful_fix: Optional[datetime] = None


class RetryLimiter:
    """
    Manages retry limits for the auto-fixer.

    Prevents:
    - More than MAX_RETRIES_PER_ERROR attempts on same error
    - More than MAX_RETRIES_PER_SESSION total attempts per session
    - More than MAX_TOKENS_PER_SESSION tokens per session
    """

    # Configuration
    MAX_RETRIES_PER_ERROR = 3  # Bolt uses 2-3
    MAX_RETRIES_PER_SESSION = 10  # Total retries per build session
    MAX_TOKENS_PER_SESSION = 50000  # Token limit per session
    SESSION_TIMEOUT = timedelta(minutes=30)  # Session expires after 30 min

    def __init__(self):
        self._projects: Dict[str, ProjectRetryState] = {}
        self._lock = threading.Lock()

    def can_retry(
        self,
        project_id: str,
        error_hash: str
    ) -> Tuple[bool, str]:
        """
        Check if a retry is allowed for this error.

        Args:
            project_id: Project ID
            error_hash: Hash of the error message

        Returns:
            Tuple of (can_retry, reason)
        """
        with self._lock:
            state = self._get_or_create_state(project_id)

            # Check session timeout
            if datetime.utcnow() - state.session_start > self.SESSION_TIMEOUT:
                # Reset session
                logger.info(f"[RetryLimiter:{project_id}] Session expired, resetting")
                self._projects[project_id] = ProjectRetryState(project_id=project_id)
                state = self._projects[project_id]

            # Check total session attempts
            if state.total_attempts >= self.MAX_RETRIES_PER_SESSION:
                logger.warning(f"[RetryLimiter:{project_id}] Session retry limit reached ({state.total_attempts})")
                return False, f"Session retry limit reached ({self.MAX_RETRIES_PER_SESSION})"

            # Check token limit
            if state.total_tokens_used >= self.MAX_TOKENS_PER_SESSION:
                logger.warning(f"[RetryLimiter:{project_id}] Token limit reached ({state.total_tokens_used})")
                return False, f"Token limit reached ({self.MAX_TOKENS_PER_SESSION})"

            # Check per-error attempts
            error_state = state.errors.get(error_hash)
            if error_state and error_state.attempts >= self.MAX_RETRIES_PER_ERROR:
                logger.warning(f"[RetryLimiter:{project_id}] Per-error retry limit reached for {error_hash[:20]}")
                return False, f"Already tried {self.MAX_RETRIES_PER_ERROR} times for this error"

            # Check if already fixed
            if error_state and error_state.fixed:
                return False, "Error was already fixed"

            return True, "Retry allowed"

    def record_attempt(
        self,
        project_id: str,
        error_hash: str,
        tokens_used: int = 0,
        fixed: bool = False
    ) -> None:
        """
        Record a fix attempt.

        Args:
            project_id: Project ID
            error_hash: Hash of the error message
            tokens_used: Tokens consumed by this attempt
            fixed: Whether the error was fixed
        """
        with self._lock:
            state = self._get_or_create_state(project_id)

            # Update totals
            state.total_attempts += 1
            state.total_tokens_used += tokens_used

            # Update per-error state
            if error_hash not in state.errors:
                state.errors[error_hash] = RetryState(error_hash=error_hash)

            error_state = state.errors[error_hash]
            error_state.attempts += 1
            error_state.last_attempt = datetime.utcnow()
            error_state.fixed = fixed

            if fixed:
                state.last_successful_fix = datetime.utcnow()

            logger.info(
                f"[RetryLimiter:{project_id}] Recorded attempt: "
                f"error={error_hash[:20]}, attempt={error_state.attempts}/{self.MAX_RETRIES_PER_ERROR}, "
                f"session_total={state.total_attempts}/{self.MAX_RETRIES_PER_SESSION}, "
                f"tokens={state.total_tokens_used}/{self.MAX_TOKENS_PER_SESSION}, "
                f"fixed={fixed}"
            )

    def reset_session(self, project_id: str) -> None:
        """Reset retry state for a project (e.g., on new build)"""
        with self._lock:
            if project_id in self._projects:
                del self._projects[project_id]
            logger.info(f"[RetryLimiter:{project_id}] Session reset")

    def reset_error(self, project_id: str, error_hash: str) -> None:
        """Reset retry state for a specific error"""
        with self._lock:
            state = self._projects.get(project_id)
            if state and error_hash in state.errors:
                del state.errors[error_hash]
                logger.info(f"[RetryLimiter:{project_id}] Error state reset: {error_hash[:20]}")

    def get_stats(self, project_id: str) -> Dict:
        """Get retry statistics for a project"""
        with self._lock:
            state = self._projects.get(project_id)
            if not state:
                return {
                    "total_attempts": 0,
                    "total_tokens": 0,
                    "errors_tracked": 0,
                    "session_age_seconds": 0
                }

            return {
                "total_attempts": state.total_attempts,
                "total_tokens": state.total_tokens_used,
                "errors_tracked": len(state.errors),
                "session_age_seconds": (datetime.utcnow() - state.session_start).total_seconds(),
                "last_successful_fix": state.last_successful_fix.isoformat() if state.last_successful_fix else None,
                "remaining_attempts": self.MAX_RETRIES_PER_SESSION - state.total_attempts,
                "remaining_tokens": self.MAX_TOKENS_PER_SESSION - state.total_tokens_used
            }

    def _get_or_create_state(self, project_id: str) -> ProjectRetryState:
        """Get or create project retry state"""
        if project_id not in self._projects:
            self._projects[project_id] = ProjectRetryState(project_id=project_id)
        return self._projects[project_id]

    @staticmethod
    def hash_error(error_message: str) -> str:
        """Create a hash for an error message (for deduplication)"""
        import hashlib
        # Normalize the message
        normalized = error_message.lower().strip()
        # Remove line numbers and paths that might differ
        import re
        normalized = re.sub(r':\d+:\d+', '', normalized)  # Remove :line:col
        normalized = re.sub(r'\d+', '', normalized)  # Remove all numbers
        return hashlib.md5(normalized.encode()).hexdigest()[:16]


# Singleton instance
retry_limiter = RetryLimiter()
