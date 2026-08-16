"""
FailureReport — the typed contract between Tester, Triage, Fixer and Reviewer.

One object does three jobs:
  * routing input   — `category` and `tier` decide which model (if any) is used
  * cache key       — `fingerprint` normalises volatile paths and line numbers
  * rollback context — `checkpoint_sha` and `baseline` gate accept/reject

Fourteen fixer implementations exist in this codebase partly because nothing
agreed on what a fixer receives. This is that agreement.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ── who found it ────────────────────────────────────────────────────────
class Source(str, Enum):
    CODER_SELF  = "coder_self"    # the coder's own build / unit test
    INTEGRATION = "integration"   # backend + frontend meet
    TESTER      = "tester"        # independent, requirements-derived
    REVIEWER    = "reviewer"      # read-only inspection
    RUNTIME     = "runtime"       # smoke run / preview boot


class Signal(str, Enum):
    BUILD     = "build"
    TEST      = "test"
    TYPECHECK = "typecheck"
    LINT      = "lint"
    CONTRACT  = "contract"
    SECURITY  = "security"
    RUNTIME   = "runtime"


class Category(str, Enum):
    """Mirrors app.services.unified_fixer.classifier.ErrorCategory, plus CONTRACT."""
    DEPENDENCY = "dependency"
    IMPORT     = "import"
    SYNTAX     = "syntax"
    TYPE       = "type"
    CONFIG     = "config"
    PORT       = "port"
    PERMISSION = "permission"
    ENV        = "env"
    RUNTIME    = "runtime"
    BUILD      = "build"
    CONTRACT   = "contract"     # producer/consumer payload mismatch
    UNKNOWN    = "unknown"


class Tier(str, Enum):
    """Capability tier, not a model. Concrete IDs live in app.core.models."""
    CACHED        = "cached"
    DETERMINISTIC = "deterministic"
    CHEAP         = "cheap"
    STANDARD      = "standard"
    FRONTIER      = "frontier"


# Categories whose remedy is project-level rather than file-local. The fix for
# a missing dependency lives in package.json / pom.xml regardless of which file
# triggered it, so the filename must not participate in the cache key.
PROJECT_SCOPED: frozenset[Category] = frozenset({
    Category.DEPENDENCY,
    Category.CONFIG,
    Category.ENV,
    Category.PORT,
    Category.PERMISSION,
})


# ── the gate ────────────────────────────────────────────────────────────
class QualityScore(BaseModel):
    """
    Hard gates must never regress; scored dimensions are summed.

    A single total is not sufficient: a patch that fixes the build (+30) and
    introduces a vulnerability (-4) sums positive and must still be rejected.
    """
    model_config = ConfigDict(frozen=True)

    compiles:            bool = False
    tests_passing:       int  = 0
    tests_total:         int  = 0
    contract_violations: int  = 0
    security_findings:   int  = 0
    lint_errors:         int  = 0
    type_errors:         int  = 0

    def regressed_against(self, before: "QualityScore") -> list[str]:
        """Non-empty result rejects the patch outright."""
        bad: list[str] = []
        if before.compiles and not self.compiles:
            bad.append("compile")
        if self.tests_passing < before.tests_passing:
            bad.append(f"tests {before.tests_passing}->{self.tests_passing}")
        if self.contract_violations > before.contract_violations:
            bad.append("contract")
        if self.security_findings > before.security_findings:
            bad.append("security")
        return bad

    @property
    def scored_total(self) -> int:
        """Soft dimensions only — never gates on its own."""
        return -(self.lint_errors + self.type_errors)


# ── detail ──────────────────────────────────────────────────────────────
class Location(BaseModel):
    file: str | None = None
    line: int | None = None
    column: int | None = None
    symbol: str | None = Field(None, description="method/class, e.g. getUser(Long)")
    module: str | None = Field(None, description="package name for dependency errors")


class ContractMismatch(BaseModel):
    """Populated when signal == CONTRACT."""
    field: str
    producer: str = Field(description='e.g. backend: "productName"')
    consumer: str = Field(description='e.g. frontend: "name"')
    endpoint: str | None = None


class Attempt(BaseModel):
    n: int
    tier: Tier
    diff: str
    outcome: Literal["reverted", "no_change", "partial"]
    reason: str
    cost_usd: float = 0.0


# ── the contract ────────────────────────────────────────────────────────
class FailureReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    project_id: str
    task_id: str | None = None

    source: Source
    signal: Signal
    detected_at: datetime

    command: str
    exit_code: int | None = None
    message: str = Field(description="the single error, not the whole log")
    stack_trace: str | None = None
    log_path: str | None = Field(None, description="full untruncated log in workspace")

    location: Location = Location()
    category: Category = Category.UNKNOWN
    tier: Tier = Tier.FRONTIER
    confidence: float = 0.5

    failing_test: str | None = None
    expected: str | None = None
    actual: str | None = None
    mismatch: ContractMismatch | None = None

    checkpoint_sha: str
    baseline: QualityScore

    attempt: int = 1
    max_attempts: int = 3
    previous: list[Attempt] = Field(default_factory=list)

    cost_spent_usd: float = 0.0
    cost_cap_usd: float = 0.50

    @property
    def fingerprint(self) -> str:
        """
        Cache key. Raw messages make useless keys — they carry absolute paths
        and line numbers that differ on every occurrence of the same bug.

        Location is included only for categories whose fix is *file-local*.
        A missing npm package is repaired in package.json no matter which file
        imported it, so including the filename there would split one cache
        entry across every importer and never hit.
        """
        parts = [self.category.value, normalize_message(self.message)]
        if self.category not in PROJECT_SCOPED:
            parts.append(self.location.symbol or basename(self.location.file) or "")
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]

    @property
    def exhausted(self) -> bool:
        return self.attempt > self.max_attempts or self.cost_spent_usd >= self.cost_cap_usd


# ── normalisation ───────────────────────────────────────────────────────
_DIR = re.compile(r"(?:[A-Za-z]:)?[\\/][\w\\/.\-]*[\\/]")
_HEX = re.compile(r"\b[0-9a-f]{7,}\b", re.I)
_NUM = re.compile(r"\b\d+\b")
# Leading "file.ext(1,39):" / "File.java:[12,5]" / "file.ts:3:1:" prefix, after
# digits have already been collapsed to '#'.
_LEADING_LOC = re.compile(r"^[\w.\-]+\.[a-z]{1,6}\s*(?:\(#(?:,\s*#)?\)|:\[?#(?:,\s*#)?\]?)\s*:?\s*")


def basename(path: str | None) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1] if path else ""


def normalize_message(msg: str) -> str:
    """
    Strip the volatile parts so the same bug reported from a different file or
    line still produces one cache key.

    The leading `file(line,col):` prefix is removed entirely — file identity is
    decided once, in `fingerprint`, via PROJECT_SCOPED. Leaving it embedded in
    the message would silently reintroduce per-file keys for project-level
    fixes and defeat the cache.
    """
    s = _DIR.sub("", msg.strip().lower())   # directories, keep basenames
    s = _HEX.sub("<hash>", s)               # commit shas, build ids
    s = _NUM.sub("#", s)                    # line/column/port numbers
    s = _LEADING_LOC.sub("", s)             # leading file(line,col): prefix
    return " ".join(s.split())


__all__ = [
    "PROJECT_SCOPED",
    "Source", "Signal", "Category", "Tier", "QualityScore", "Location",
    "ContractMismatch", "Attempt", "FailureReport",
    "basename", "normalize_message",
]
