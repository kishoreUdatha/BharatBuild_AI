"""
Stage 07 — triage dispatcher.

Every failure walks three tiers in cost order: cache replay, deterministic
template, then the agent runtime. All three converge on the same verification
gate: re-score, compare against the baseline, accept or `git reset --hard`.

The runtime is behind a Protocol on purpose — swapping OpenHands for something
else should not touch this file.
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Protocol, runtime_checkable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.failure import (
    Attempt, Category, FailureReport, QualityScore, Tier,
)

log = logging.getLogger(__name__)


# ── outcome ─────────────────────────────────────────────────────────────
class Outcome(str, Enum):
    ACCEPTED   = "accepted"     # gates held, committed
    REVERTED   = "reverted"     # regression, rolled back
    NO_CHANGE  = "no_change"    # tier produced no edit
    EXHAUSTED  = "exhausted"    # attempts or budget spent
    ERROR      = "error"        # runtime blew up


class FixResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    outcome: Outcome
    report_id: str
    tier: Tier | None = None
    diff: str = ""
    files_changed: list[str] = Field(default_factory=list)
    score_before: QualityScore | None = None
    score_after: QualityScore | None = None
    regressions: list[str] = Field(default_factory=list)
    cost_usd: float = 0.0
    attempts: int = 0
    detail: str = ""

    @property
    def resolved(self) -> bool:
        return self.outcome is Outcome.ACCEPTED


# ── collaborators (implement these against whatever runtime you use) ────
@runtime_checkable
class Workspace(Protocol):
    def execute_command(self, cmd: str) -> "CommandResult": ...


class CommandResult(Protocol):
    exit_code: int
    stdout: str
    stderr: str


@runtime_checkable
class AgentRuntime(Protocol):
    async def run(self, *, prompt: str, model: str, workspace: Workspace,
                  max_iterations: int) -> "RunResult": ...


class RunResult(Protocol):
    cost_usd: float
    error: str | None


@runtime_checkable
class Scorer(Protocol):
    """Runs build / tests / lint / typecheck / contract checks."""
    async def score(self, workspace: Workspace) -> QualityScore: ...


@runtime_checkable
class FixCache(Protocol):
    def get(self, fingerprint: str) -> str | None: ...          # returns a patch
    def put(self, fingerprint: str, patch: str) -> None: ...
    def invalidate(self, fingerprint: str) -> None: ...


@runtime_checkable
class DeterministicFixer(Protocol):
    def can_fix(self, report: FailureReport) -> bool: ...
    async def apply(self, report: FailureReport, workspace: Workspace) -> list[str]: ...


@runtime_checkable
class ModelRouter(Protocol):
    def pick(self, tier: Tier, category: Category) -> str: ...  # returns a model id


@runtime_checkable
class Budget(Protocol):
    def remaining(self) -> float: ...
    def charge(self, usd: float) -> None: ...


# ── prompt ──────────────────────────────────────────────────────────────
FIXER_PROMPT = """\
You are the BharatBuild Fixer. Repair one verified failure with the smallest
safe change.

Rules:
1. Read the error, then inspect the relevant existing files before editing.
2. Identify the root cause. Do not guess.
3. Make the minimum modification that resolves it. Do not rewrite working code,
   reformat unrelated lines, or refactor.
4. Preserve the existing architecture and the API contract.
5. Creating a file is allowed when the fix genuinely requires one.
6. Never weaken the check to pass it: do not disable type checking, loosen
   tsconfig/compiler strictness, delete assertions, or skip tests.
7. Re-run the failing command to confirm before you finish.

FAILURE
  signal:   {signal}
  command:  {command}
  category: {category}
  file:     {file}:{line}
  symbol:   {symbol}
  test:     {failing_test}

MESSAGE
{message}

{stack}
{history}
"""

_HISTORY_HEADER = """\
PREVIOUS ATTEMPTS — these were tried and rolled back. Do not repeat them.
"""


def _build_prompt(r: FailureReport) -> str:
    stack = f"STACK TRACE\n{r.stack_trace}\n" if r.stack_trace else ""
    history = ""
    if r.previous:
        blocks = "\n\n".join(
            f"--- attempt {a.n} ({a.tier.value}) — {a.outcome}: {a.reason}\n{a.diff}"
            for a in r.previous
        )
        history = f"\n{_HISTORY_HEADER}{blocks}\n"
    return FIXER_PROMPT.format(
        signal=r.signal.value,
        command=r.command,
        category=r.category.value,
        file=r.location.file or "?",
        line=r.location.line or "?",
        symbol=r.location.symbol or "-",
        failing_test=r.failing_test or "-",
        message=r.message,
        stack=stack,
        history=history,
    )


# ── dispatcher ──────────────────────────────────────────────────────────
class TriageDispatcher:
    def __init__(
        self,
        *,
        workspace: Workspace,
        runtime: AgentRuntime,
        scorer: Scorer,
        cache: FixCache,
        deterministic: DeterministicFixer,
        router: ModelRouter,
        budget: Budget,
        max_agent_iterations: int = 25,
    ) -> None:
        self.ws = workspace
        self.runtime = runtime
        self.scorer = scorer
        self.cache = cache
        self.deterministic = deterministic
        self.router = router
        self.budget = budget
        self.max_agent_iterations = max_agent_iterations

    # ---- public ----------------------------------------------------
    async def resolve(self, report: FailureReport) -> FixResult:
        """Drive attempts until the failure clears or the budget/caps run out."""
        current, spent, n = report, 0.0, 0

        while True:
            n += 1
            result = await self.fix(current)
            spent += result.cost_usd

            if result.outcome in (Outcome.ACCEPTED, Outcome.EXHAUSTED, Outcome.ERROR):
                return result.model_copy(update={"attempts": n, "cost_usd": spent})

            # reverted or no-change → next attempt carries the history forward
            current = current.model_copy(update={
                "attempt": current.attempt + 1,
                "cost_spent_usd": spent,
                "previous": [
                    *current.previous,
                    Attempt(
                        n=current.attempt,
                        tier=result.tier or current.tier,
                        diff=result.diff,
                        outcome="reverted" if result.outcome is Outcome.REVERTED
                                else "no_change",
                        reason=", ".join(result.regressions) or result.detail,
                        cost_usd=result.cost_usd,
                    ),
                ],
            })

            if current.exhausted:
                return FixResult(
                    outcome=Outcome.EXHAUSTED, report_id=current.id,
                    attempts=n, cost_usd=spent,
                    detail=f"gave up after {n} attempts (${spent:.4f})",
                )

    async def fix(self, r: FailureReport) -> FixResult:
        """One attempt. Free tiers first; the agent only as a last resort."""
        if r.exhausted:
            return FixResult(outcome=Outcome.EXHAUSTED, report_id=r.id,
                             detail="attempt or cost cap already reached")

        # tier 1 — cache replay (free)
        if (patch := self.cache.get(r.fingerprint)) is not None:
            log.info("[triage:%s] cache hit %s", r.id, r.fingerprint)
            res = await self._attempt(
                r, Tier.CACHED, lambda: self._apply_patch(patch), cost=0.0
            )
            if res.outcome is Outcome.REVERTED:
                self.cache.invalidate(r.fingerprint)   # it stopped working
            return res

        # tier 2 — deterministic template (free)
        if self.deterministic.can_fix(r):
            log.info("[triage:%s] deterministic %s", r.id, r.category.value)
            return await self._attempt(
                r, Tier.DETERMINISTIC,
                lambda: self.deterministic.apply(r, self.ws), cost=0.0,
            )

        # tier 3 — agent runtime (costs money)
        est = 0.05
        if self.budget.remaining() < est:
            return FixResult(outcome=Outcome.EXHAUSTED, report_id=r.id,
                             detail="insufficient budget for an agent attempt")

        model = self.router.pick(r.tier, r.category)
        log.info("[triage:%s] agent tier=%s model=%s", r.id, r.tier.value, model)
        return await self._attempt(r, r.tier, lambda: self._run_agent(r, model))

    # ---- internals -------------------------------------------------
    async def _attempt(self, r, tier, mutate, cost: float | None = None) -> FixResult:
        """checkpoint → mutate → re-score → accept or roll back."""
        before = r.baseline
        sha = self._checkpoint(r)
        spent = 0.0

        try:
            outcome = mutate()
            if hasattr(outcome, "__await__"):
                outcome = await outcome
            if cost is None and isinstance(outcome, float):
                spent = outcome
            elif cost is not None:
                spent = cost
        except Exception as exc:                      # noqa: BLE001
            log.exception("[triage:%s] tier %s raised", r.id, tier)
            self._rollback(sha)
            return FixResult(outcome=Outcome.ERROR, report_id=r.id, tier=tier,
                             cost_usd=spent, detail=f"{type(exc).__name__}: {exc}")

        diff = self._diff_since(sha)
        if not diff.strip():
            return FixResult(outcome=Outcome.NO_CHANGE, report_id=r.id, tier=tier,
                             cost_usd=spent, score_before=before,
                             detail="tier produced no edit")

        after = await self.scorer.score(self.ws)
        regressions = after.regressed_against(before)
        scored_worse = after.scored_total < before.scored_total

        if regressions or scored_worse:
            reasons = regressions or [
                f"scored {before.scored_total}→{after.scored_total}"
            ]
            log.warning("[triage:%s] reverting: %s", r.id, ", ".join(reasons))
            self._rollback(sha)                        # diff captured above
            return FixResult(outcome=Outcome.REVERTED, report_id=r.id, tier=tier,
                             diff=diff, files_changed=self._changed_files(diff),
                             score_before=before, score_after=after,
                             regressions=reasons, cost_usd=spent)

        self._commit(f"fix({r.category.value}): {r.message[:60]}")
        if tier is not Tier.CACHED:
            self.cache.put(r.fingerprint, diff)
        log.info("[triage:%s] accepted via %s ($%.4f)", r.id, tier.value, spent)
        return FixResult(outcome=Outcome.ACCEPTED, report_id=r.id, tier=tier,
                         diff=diff, files_changed=self._changed_files(diff),
                         score_before=before, score_after=after, cost_usd=spent)

    async def _run_agent(self, r: FailureReport, model: str) -> float:
        result = await self.runtime.run(
            prompt=_build_prompt(r), model=model, workspace=self.ws,
            max_iterations=self.max_agent_iterations,
        )
        self.budget.charge(result.cost_usd)
        if result.error:
            raise RuntimeError(result.error)
        return result.cost_usd

    def _apply_patch(self, patch: str) -> None:
        res = self.ws.execute_command(
            f"git apply --whitespace=nowarn - <<'BB_PATCH_EOF'\n{patch}\nBB_PATCH_EOF"
        )
        if res.exit_code != 0:
            raise RuntimeError(f"cached patch did not apply: {res.stderr[:400]}")

    # ---- git -------------------------------------------------------
    def _checkpoint(self, r: FailureReport) -> str:
        self.ws.execute_command(
            f'git add -A && git commit -q --allow-empty -m "checkpoint: {r.id[:8]}"'
        )
        return self.ws.execute_command("git rev-parse HEAD").stdout.strip()

    def _rollback(self, sha: str) -> None:
        # reset alone leaves untracked files the agent created — clean too.
        self.ws.execute_command(f"git reset --hard {sha} && git clean -fdq")

    def _commit(self, msg: str) -> None:
        safe = msg.replace('"', "'").replace("\n", " ")
        self.ws.execute_command(f'git add -A && git commit -q -m "{safe}"')

    def _diff_since(self, sha: str) -> str:
        self.ws.execute_command("git add -A")           # include new files
        return self.ws.execute_command(f"git diff --cached {sha}").stdout

    @staticmethod
    def _changed_files(diff: str) -> list[str]:
        return sorted({
            line.split(" b/", 1)[1].strip()
            for line in diff.splitlines()
            if line.startswith("diff --git ") and " b/" in line
        })
