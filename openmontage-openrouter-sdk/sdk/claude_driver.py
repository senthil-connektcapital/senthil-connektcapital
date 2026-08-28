"""Programmatic Claude Agent SDK driver for an OpenMontage checkout.

This is the in-app equivalent of running Claude Code in the OpenMontage repo.
It does not use the interactive CLI. The SDK still boots the Claude Code
runtime so the agent can Read/Write/Bash against pipeline_defs/, skills/, and tools/.

OpenRouter for the *orchestrator LLM*:
    ANTHROPIC_BASE_URL=https://openrouter.ai/api
    ANTHROPIC_AUTH_TOKEN=$OPENROUTER_API_KEY
    ANTHROPIC_API_KEY=   # must be explicitly empty

OpenRouter for *generation tools* is a separate concern: point OpenMontage
tools at OPENROUTER_API_KEY (see gateway/openrouter.py) instead of FAL/HeyGen/etc.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

OPENROUTER_ANTHROPIC_BASE = "https://openrouter.ai/api"

DEFAULT_ALLOWED_TOOLS = ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "Skill"]


def openrouter_orchestrator_env(api_key: str | None = None) -> dict[str, str]:
    """Env vars that route Claude Agent SDK traffic through OpenRouter."""
    key = api_key or os.environ.get("OPENROUTER_API_KEY") or ""
    env = os.environ.copy()
    env["ANTHROPIC_BASE_URL"] = OPENROUTER_ANTHROPIC_BASE
    env["ANTHROPIC_AUTH_TOKEN"] = key
    env["ANTHROPIC_API_KEY"] = ""
    env["OPENROUTER_API_KEY"] = key
    return env


def claude_options(
    montage_root: Path,
    *,
    model: str | None = None,
    max_turns: int = 40,
) -> dict[str, Any]:
    """Options dict compatible with claude_agent_sdk.ClaudeAgentOptions(**kwargs)."""
    root = Path(montage_root).resolve()
    options: dict[str, Any] = {
        "cwd": str(root),
        "allowed_tools": DEFAULT_ALLOWED_TOOLS,
        "skills": "all",
        "setting_sources": ["project"],
        "max_turns": max_turns,
        "system_prompt": (
            "You are the OpenMontage executive producer running inside an application, "
            "not an interactive IDE. Follow AGENT_GUIDE.md. Use pipeline_defs/, "
            "skills/, and the Python tool registry. Prefer OpenRouter-backed generation "
            "when OPENROUTER_API_KEY is set. Stop at human approval gates."
        ),
    }
    if model:
        options["model"] = model
    return options


async def run_production(
    prompt: str,
    montage_root: Path,
    *,
    use_openrouter_orchestrator: bool = True,
    model: str | None = None,
) -> AsyncIterator[Any]:
    """Yield Claude Agent SDK messages for one production request.

    Requires `pip install claude-agent-sdk` and a cloned OpenMontage tree.
    """
    try:
        from claude_agent_sdk import ClaudeAgentOptions, query
    except ImportError as exc:  # pragma: no cover - exercised only when SDK is installed
        raise RuntimeError(
            "claude-agent-sdk is not installed. pip install claude-agent-sdk"
        ) from exc

    if use_openrouter_orchestrator:
        os.environ.update(openrouter_orchestrator_env())

    options = ClaudeAgentOptions(**{k: v for k, v in claude_options(montage_root, model=model).items() if v is not None})
    async for message in query(prompt=prompt, options=options):
        yield message


def can_embed_openmontage(montage_root: Path) -> dict[str, bool]:
    """Cheap filesystem preflight used by tests — no SDK required."""
    root = Path(montage_root)
    return {
        "agent_guide": (root / "AGENT_GUIDE.md").is_file(),
        "pipeline_defs": (root / "pipeline_defs").is_dir(),
        "skills": (root / "skills").is_dir(),
        "tools": (root / "tools" / "tool_registry.py").is_file(),
        "claude_skills": (root / ".claude" / "skills").is_dir() or (root / "skills").is_dir(),
    }
