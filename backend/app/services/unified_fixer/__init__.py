"""
Unified Fixer - Single entry point for all error fixing

Optimized 3-tier architecture:
- Tier 1: Deterministic (FREE, instant, pattern-based)
- Tier 2: Haiku AI ($0.001, fast, simple fixes)
- Tier 3: Sonnet AI ($0.01, smart, complex fixes)

Features:
- Error classification (NO AI, <1ms)
- Fix caching (~40% hit rate)
- Automatic tier selection
- Cost tracking
- Performance metrics
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from app.core.logging_config import logger
from app.services.unified_fixer.classifier import (
    ErrorClassifier, ClassifiedError, ErrorCategory,
    ErrorSeverity, FixTier, error_classifier
)
from app.services.unified_fixer.cache import FixCache, fix_cache
from app.services.unified_fixer.strategies import (
    DeterministicStrategy, HaikuStrategy, SonnetStrategy, FixResult
)


@dataclass
class FixAttempt:
    """Single fix attempt result"""
    tier: FixTier
    result: FixResult
    retried: bool = False


@dataclass
class UnifiedFixResult:
    """Complete fix result with all metadata"""
    success: bool
    error_category: ErrorCategory
    final_tier: FixTier

    # Fix details
    fix_type: str
    files_modified: List[str]
    command_run: Optional[str] = None

    # Performance
    total_time_ms: int = 0
    classification_time_ms: int = 0
    fix_time_ms: int = 0

    # Cost
    total_cost: float = 0.0

    # Attempts
    attempts: List[FixAttempt] = field(default_factory=list)

    # Errors
    error: Optional[str] = None

    # Cache
    from_cache: bool = False


class UnifiedFixer:
    """
    Single entry point for all error fixing.

    Usage:
        fixer = UnifiedFixer(file_manager=file_manager)
        result = await fixer.fix(error_message, project_path, project_id, user_id)

        if result.success:
            print(f"Fixed! Modified: {result.files_modified}")
        else:
            print(f"Failed: {result.error}")
    """

    def __init__(
        self,
        file_manager=None,
        anthropic_client=None,
        enable_cache: bool = True,
        max_retries: int = 2,
        escalate_on_fail: bool = True
    ):
        """
        Initialize UnifiedFixer.

        Args:
            file_manager: UnifiedFileManager instance for file operations
            anthropic_client: Anthropic client for AI calls
            enable_cache: Whether to use fix cache
            max_retries: Max retries per tier
            escalate_on_fail: Whether to escalate to higher tier on failure
        """
        self.file_manager = file_manager
        self.anthropic_client = anthropic_client
        self.enable_cache = enable_cache
        self.max_retries = max_retries
        self.escalate_on_fail = escalate_on_fail

        # Initialize components
        self.classifier = error_classifier
        self.cache = fix_cache if enable_cache else None

        # Initialize strategies
        self.deterministic = DeterministicStrategy(file_manager=file_manager)
        self.haiku = HaikuStrategy(
            file_manager=file_manager,
            anthropic_client=anthropic_client
        )
        self.sonnet = SonnetStrategy(
            file_manager=file_manager,
            anthropic_client=anthropic_client
        )

        # Stats
        self._stats = {
            "total_fixes": 0,
            "tier1_fixes": 0,
            "tier2_fixes": 0,
            "tier3_fixes": 0,
            "cache_hits": 0,
            "total_cost": 0.0,
            "avg_time_ms": 0
        }

    async def fix(
        self,
        error: str,
        project_path: str,
        project_id: str,
        user_id: str,
        file_path: str = None,
        file_content: str = None,
        max_tier: FixTier = FixTier.SONNET
    ) -> UnifiedFixResult:
        """
        Fix an error using the optimal strategy.

        Args:
            error: Error message/output
            project_path: Path to project directory
            project_id: Project ID
            user_id: User ID
            file_path: Optional file path with error
            file_content: Optional file content
            max_tier: Maximum tier to use (for cost control)

        Returns:
            UnifiedFixResult with complete fix details
        """
        total_start = time.time()

        try:
            # Step 1: Classify the error
            classify_start = time.time()
            classified = self.classifier.classify(error, file_path)
            classification_time_ms = int((time.time() - classify_start) * 1000)

            logger.info(
                f"[UnifiedFixer] Classified: {classified.category.value} "
                f"-> Tier {classified.recommended_tier.value} "
                f"({classification_time_ms}ms)"
            )

            # Step 2: Check cache
            if self.enable_cache and self.cache:
                cached = self.cache.get(error, file_path)
                if cached:
                    logger.info(f"[UnifiedFixer] Cache HIT")
                    self._stats["cache_hits"] += 1

                    # Replay cached fix
                    result = await self._replay_cached_fix(
                        cached, project_path, project_id, user_id
                    )

                    if result.success:
                        return UnifiedFixResult(
                            success=True,
                            error_category=classified.category,
                            final_tier=FixTier.DETERMINISTIC,
                            fix_type=cached.fix_type,
                            files_modified=result.files_modified,
                            command_run=result.command_run,
                            total_time_ms=int((time.time() - total_start) * 1000),
                            classification_time_ms=classification_time_ms,
                            fix_time_ms=result.time_ms,
                            total_cost=0.0,
                            from_cache=True
                        )

            # Step 3: Apply fix with escalation
            attempts = []
            current_tier = classified.recommended_tier

            # Respect max_tier limit
            if current_tier.value > max_tier.value:
                current_tier = max_tier

            while current_tier.value <= max_tier.value:
                logger.info(f"[UnifiedFixer] Trying Tier {current_tier.value}")

                result = await self._apply_tier(
                    current_tier, classified,
                    project_path, project_id, user_id,
                    file_content
                )

                attempts.append(FixAttempt(
                    tier=current_tier,
                    result=result,
                    retried=False
                ))

                if result.success:
                    # Cache successful fix
                    if self.enable_cache and self.cache:
                        self._cache_fix(error, result, file_path)

                    # Update stats
                    self._update_stats(current_tier, result)

                    return UnifiedFixResult(
                        success=True,
                        error_category=classified.category,
                        final_tier=current_tier,
                        fix_type=result.fix_type,
                        files_modified=result.files_modified,
                        command_run=result.command_run,
                        total_time_ms=int((time.time() - total_start) * 1000),
                        classification_time_ms=classification_time_ms,
                        fix_time_ms=result.time_ms,
                        total_cost=result.cost,
                        attempts=attempts
                    )

                # Escalate to next tier if enabled
                if not self.escalate_on_fail:
                    break

                if current_tier == FixTier.DETERMINISTIC:
                    current_tier = FixTier.HAIKU
                elif current_tier == FixTier.HAIKU:
                    current_tier = FixTier.SONNET
                else:
                    break  # Already at highest tier

            # All attempts failed
            total_cost = sum(a.result.cost for a in attempts)
            last_error = attempts[-1].result.error if attempts else "Unknown error"

            return UnifiedFixResult(
                success=False,
                error_category=classified.category,
                final_tier=current_tier,
                fix_type="failed",
                files_modified=[],
                total_time_ms=int((time.time() - total_start) * 1000),
                classification_time_ms=classification_time_ms,
                total_cost=total_cost,
                attempts=attempts,
                error=last_error
            )

        except Exception as e:
            logger.error(f"[UnifiedFixer] Unexpected error: {e}")
            return UnifiedFixResult(
                success=False,
                error_category=ErrorCategory.UNKNOWN,
                final_tier=FixTier.SONNET,
                fix_type="error",
                files_modified=[],
                total_time_ms=int((time.time() - total_start) * 1000),
                error=str(e)
            )

    async def _apply_tier(
        self,
        tier: FixTier,
        classified: ClassifiedError,
        project_path: str,
        project_id: str,
        user_id: str,
        file_content: str = None
    ) -> FixResult:
        """Apply fix using specific tier"""
        if tier == FixTier.DETERMINISTIC:
            return await self.deterministic.fix(
                classified, project_path, project_id, user_id
            )

        elif tier == FixTier.HAIKU:
            return await self.haiku.fix(
                classified, project_path, project_id, user_id,
                file_content=file_content
            )

        elif tier == FixTier.SONNET:
            return await self.sonnet.fix(
                classified, project_path, project_id, user_id
            )

        else:
            return FixResult(
                success=False,
                fix_type="unknown_tier",
                files_modified=[],
                error=f"Unknown tier: {tier}"
            )

    async def _replay_cached_fix(
        self,
        cached,
        project_path: str,
        project_id: str,
        user_id: str
    ) -> FixResult:
        """Replay a cached fix"""
        import time
        start = time.time()

        try:
            fix_type = cached.fix_type
            fix_data = cached.fix_data

            if fix_type == "command":
                import asyncio
                command = fix_data.get("command", "")

                if command:
                    process = await asyncio.create_subprocess_shell(
                        command,
                        cwd=project_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await process.communicate()

                    return FixResult(
                        success=process.returncode == 0,
                        fix_type="command",
                        files_modified=fix_data.get("files_modified", []),
                        command_run=command,
                        time_ms=int((time.time() - start) * 1000)
                    )

            elif fix_type in ["file_create", "file_edit"]:
                file_path = fix_data.get("file_path", "")
                content = fix_data.get("content", "")

                if self.file_manager and file_path:
                    success = await self.file_manager.write_file(
                        project_id, user_id, file_path, content
                    )
                    return FixResult(
                        success=success,
                        fix_type=fix_type,
                        files_modified=[file_path] if success else [],
                        time_ms=int((time.time() - start) * 1000)
                    )

            return FixResult(
                success=False,
                fix_type="cache_replay",
                files_modified=[],
                error="Could not replay cached fix",
                time_ms=int((time.time() - start) * 1000)
            )

        except Exception as e:
            return FixResult(
                success=False,
                fix_type="cache_replay",
                files_modified=[],
                error=str(e),
                time_ms=int((time.time() - start) * 1000)
            )

    def _cache_fix(self, error: str, result: FixResult, file_path: str = None):
        """Cache a successful fix"""
        if not self.cache:
            return

        fix_data = {
            "files_modified": result.files_modified
        }

        if result.command_run:
            fix_data["command"] = result.command_run

        # TODO: Store file content for file edits

        self.cache.set(error, result.fix_type, fix_data, file_path)

    def _update_stats(self, tier: FixTier, result: FixResult):
        """Update internal statistics"""
        self._stats["total_fixes"] += 1
        self._stats["total_cost"] += result.cost

        if tier == FixTier.DETERMINISTIC:
            self._stats["tier1_fixes"] += 1
        elif tier == FixTier.HAIKU:
            self._stats["tier2_fixes"] += 1
        elif tier == FixTier.SONNET:
            self._stats["tier3_fixes"] += 1

    def get_stats(self) -> Dict:
        """Get fixer statistics"""
        stats = dict(self._stats)

        # Add cache stats
        if self.cache:
            stats["cache"] = self.cache.get_stats()

        # Calculate cost breakdown
        total = stats["total_fixes"] or 1
        stats["tier1_pct"] = round(stats["tier1_fixes"] / total * 100, 1)
        stats["tier2_pct"] = round(stats["tier2_fixes"] / total * 100, 1)
        stats["tier3_pct"] = round(stats["tier3_fixes"] / total * 100, 1)

        return stats

    def clear_cache(self):
        """Clear the fix cache"""
        if self.cache:
            self.cache.clear()


# Convenience functions
async def fix_error(
    error: str,
    project_path: str,
    project_id: str,
    user_id: str,
    file_manager=None,
    **kwargs
) -> UnifiedFixResult:
    """
    Convenience function to fix an error.

    Usage:
        result = await fix_error(
            error="Cannot find module 'lodash'",
            project_path="/workspace/user123/proj456",
            project_id="proj456",
            user_id="user123"
        )
    """
    fixer = UnifiedFixer(file_manager=file_manager)
    return await fixer.fix(error, project_path, project_id, user_id, **kwargs)


# Singleton instance (optional, for simple usage)
_default_fixer: Optional[UnifiedFixer] = None


def get_fixer(file_manager=None, **kwargs) -> UnifiedFixer:
    """Get or create default UnifiedFixer instance"""
    global _default_fixer

    if _default_fixer is None:
        _default_fixer = UnifiedFixer(file_manager=file_manager, **kwargs)
    elif file_manager and _default_fixer.file_manager is None:
        _default_fixer.file_manager = file_manager

    return _default_fixer


# Exports
__all__ = [
    'UnifiedFixer',
    'UnifiedFixResult',
    'FixAttempt',
    'FixResult',
    'fix_error',
    'get_fixer',
    # Re-export classifier types
    'ErrorClassifier',
    'ClassifiedError',
    'ErrorCategory',
    'ErrorSeverity',
    'FixTier',
    'error_classifier',
    # Re-export cache
    'FixCache',
    'fix_cache',
]
