"""
Triage — the single fix path.

STATUS: not yet wired. This package is the designated replacement for the
fourteen fixer implementations currently live in this codebase:

    services/simple_fixer.py            services/universal_autofixer.py
    services/bolt_fixer.py              services/terminal_error_fixer.py
    services/production_autofixer.py    services/sdk_fixer.py
    services/fix_executor.py            services/auto_fixer.py
    services/unified_fixer/             modules/agents/fixer_agent.py
    modules/agents/production_fixer_agent.py
    modules/agents/docker_infra_fixer_agent.py
    modules/sdk_agents/sdk_fixer_agent.py
    modules/orchestrator/auto_fix_orchestrator.py

Adding this without retiring those makes it the fifteenth. The migration is
not complete until they are deleted — see the ordering in `dispatcher.py`.

Before it can run, three collaborators need implementations (all are Protocols
in `dispatcher.py`, so they can be built and tested independently):

    Scorer         runs build/tests/lint/typecheck -> QualityScore   [new]
    AgentRuntime   thin wrapper returning measured cost              [new]
    Workspace      execute_command against the project sandbox       [adapt existing]

FixCache and DeterministicFixer are already satisfied by
`services/unified_fixer/cache.py` and `strategies/deterministic.py`.
"""

from app.services.triage.dispatcher import (  # noqa: F401
    FixResult,
    Outcome,
    TriageDispatcher,
)

__all__ = ["FixResult", "Outcome", "TriageDispatcher"]
