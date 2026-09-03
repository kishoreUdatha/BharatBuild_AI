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

CURRENT ROUTING (audited; every one of these is live, none are dead code).
This is the call graph the migration has to redirect — each entry point below
must end up calling TriageDispatcher instead:

    api/errors.py           -> simple_fixer, auto_fixer.get_auto_fixer
    api/execution.py        -> production_fixer_agent, BoltFixer,
                               terminal_error_fixer.get_terminal_fixer
    api/log_stream.py       -> auto_fixer.get_auto_fixer
    api/projects.py         -> agents/fixer_agent.FixerAgent
    api/sdk_agents.py       -> sdk_agents/sdk_fixer_agent
    api/autofixer_metrics.py-> production_autofixer
    main.py                 -> fix_executor.execute_fix
    services/container_executor.py -> BoltFixer (x5), sdk_fixer,
                               docker_infra_fixer_agent
    modules/execution/docker_executor.py -> universal_autofixer,
                               production_autofixer, simple_fixer
    modules/orchestrator/dynamic_orchestrator.py -> universal_autofixer,
                               fixer_agent, production_fixer_agent
    services/terminal_error_fixer.py -> unified_fixer (the only consumer of it)

Note docker_executor.py imports THREE different fixers and container_executor.py
imports three more; a bug in the fix loop currently has to be fixed in up to a
dozen places. That is the cost this package is meant to remove.
"""

from app.services.triage.dispatcher import (  # noqa: F401
    FixResult,
    Outcome,
    TriageDispatcher,
)

__all__ = ["FixResult", "Outcome", "TriageDispatcher"]
