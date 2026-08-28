"""Programmatic Codex SDK driver for an OpenMontage checkout.

Codex SDK is a library API (`thread.run(...)`) but it still spawns the Codex
app-server/CLI under the hood. That is the closest official 'not the command
line' path for Codex. Point `working_directory` at the OpenMontage clone so
repo skills (`.agents/skills`, `AGENTS.md`, `CODEX.md`) load.

OpenRouter as the Codex model endpoint is possible via `baseUrl` /
`openai_base_url`, but Codex's tool protocol is OpenAI-shaped. Use an
OpenRouter model with reliable tool use (typically OpenAI or Claude SKUs).
Generation tools inside OpenMontage still use OPENROUTER_API_KEY separately.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULT_SANDBOX = "workspace_write"


def thread_config(
    montage_root: Path,
    *,
    model: str | None = None,
    skip_git_repo_check: bool = True,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Config payload for openai_codex.Codex / @openai/codex-sdk."""
    config: dict[str, Any] = {
        "working_directory": str(Path(montage_root).resolve()),
        "skip_git_repo_check": skip_git_repo_check,
        "sandbox": DEFAULT_SANDBOX,
    }
    if model:
        config["model"] = model
    if base_url:
        config["base_url"] = base_url
    return config


def production_input(prompt: str) -> str:
    return (
        "Follow AGENT_GUIDE.md and the OpenMontage pipeline contract. "
        "Do not improvise stages. Use the tool registry for preflight. "
        "When generating video/image/speech, prefer OpenRouter if "
        "OPENROUTER_API_KEY is set.\n\nUser request:\n"
        f"{prompt}"
    )


def skill_mentions(montage_root: Path) -> list[dict[str, str]]:
    """Explicit Codex SkillInput-style mentions for core OpenMontage skills."""
    root = Path(montage_root)
    candidates = [
        root / "AGENT_GUIDE.md",
        root / "skills" / "INDEX.md",
        root / "CODEX.md",
    ]
    mentions = []
    for path in candidates:
        if path.is_file():
            mentions.append({"name": path.stem, "path": str(path)})
    return mentions
