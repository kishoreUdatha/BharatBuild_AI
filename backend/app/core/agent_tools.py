"""
Tool vocabulary for agent capability scoping.

`capabilities:` in agent_config.yml is descriptive — free-text tags nothing
checks. `tools:` is an *allowlist*: an agent that does not list `terminal`
cannot run shell commands, and an agent that does not list `write` cannot
modify files, regardless of what its prompt says.

This is the mechanism that makes a read-only Reviewer read-only. Prompting an
agent not to edit files is a request; omitting `write` from its tool list is a
constraint.

Names deliberately match the runtime's tool names 1:1, so a config entry maps
straight onto the tools handed to an agent with no translation layer.
"""
from __future__ import annotations

from typing import Final, Iterable


class Tool:
    """Canonical tool names. Values mirror the agent runtime's tool identifiers."""

    READ        = "read"          # view file contents
    GLOB        = "glob"          # match paths by pattern
    GREP        = "grep"          # search file contents
    GIT_READ    = "git_read"      # git diff / status — inspection only

    WRITE       = "write"         # create a file
    EDIT        = "edit"          # modify an existing file
    APPLY_PATCH = "apply_patch"   # apply a unified diff

    TERMINAL    = "terminal"      # execute shell commands


ALL: Final[frozenset[str]] = frozenset({
    Tool.READ, Tool.GLOB, Tool.GREP, Tool.GIT_READ,
    Tool.WRITE, Tool.EDIT, Tool.APPLY_PATCH, Tool.TERMINAL,
})

#: Tools that cannot change the workspace. An agent restricted to these can be
#: run against a project without a checkpoint.
READ_ONLY: Final[frozenset[str]] = frozenset({
    Tool.READ, Tool.GLOB, Tool.GREP, Tool.GIT_READ,
})

#: Tools that mutate the workspace. Any agent granted one of these must run
#: behind a git checkpoint so its work can be rolled back.
MUTATING: Final[frozenset[str]] = ALL - READ_ONLY

#: Common presets, so config stays readable.
PRESET_INSPECT: Final[tuple[str, ...]] = (Tool.READ, Tool.GLOB, Tool.GREP)
PRESET_AUTHOR:  Final[tuple[str, ...]] = (Tool.READ, Tool.WRITE, Tool.EDIT,
                                          Tool.GLOB, Tool.GREP)
PRESET_BUILD:   Final[tuple[str, ...]] = PRESET_AUTHOR + (Tool.TERMINAL,)
PRESET_REPAIR:  Final[tuple[str, ...]] = PRESET_BUILD + (Tool.APPLY_PATCH,
                                                         Tool.GIT_READ)


def validate(names: Iterable[str], *, context: str = "") -> list[str]:
    """
    Return the recognised subset, discarding unknown names.

    Unknown entries are dropped rather than raising: a typo in config should
    narrow an agent's permissions, never widen them or crash startup.
    """
    from app.core.logging_config import logger

    kept, unknown = [], []
    for n in names:
        (kept if n in ALL else unknown).append(n)
    if unknown:
        logger.warning(
            "[agent_tools] Unknown tool(s) %s in %s — ignored. Valid: %s",
            sorted(unknown), context or "config", sorted(ALL),
        )
    return kept


def is_read_only(names: Iterable[str]) -> bool:
    """True if this tool set cannot modify the workspace."""
    return not (set(names) & MUTATING)


def requires_checkpoint(names: Iterable[str]) -> bool:
    """True if an agent with these tools must run behind a git checkpoint."""
    return bool(set(names) & MUTATING)


__all__ = [
    "Tool", "ALL", "READ_ONLY", "MUTATING",
    "PRESET_INSPECT", "PRESET_AUTHOR", "PRESET_BUILD", "PRESET_REPAIR",
    "validate", "is_read_only", "requires_checkpoint",
]
