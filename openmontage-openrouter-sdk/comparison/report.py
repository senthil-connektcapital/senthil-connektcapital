"""Render comparison reports as markdown."""

from __future__ import annotations

from comparison.catalog import ComparisonReport
from comparison.matrix import KEYS_OPENMONTAGE_REPLACES_WITH_OPENROUTER, KEYS_STILL_REQUIRED

COVERAGE_LABEL = {
    "yes": "covered",
    "partial": "partial",
    "no": "not on OpenRouter",
    "bonus": "OpenRouter extra",
    "local_only": "local studio (not an API)",
}


def render_markdown(report: ComparisonReport) -> str:
    lines = [
        "# OpenMontage × Agent SDK × OpenRouter — live comparison",
        "",
        f"- Video models on OpenRouter: **{report.video_model_count}**",
        f"- Image-output models: **{report.image_model_count}**",
        f"- Speech/audio-output models: **{report.speech_model_count}**",
        f"- Transcription models: **{report.transcription_model_count}**",
        f"- Capability rows: **{len(report.results)}** "
        f"(yes={report.summary.get('yes', 0)}, "
        f"partial={report.summary.get('partial', 0)}, "
        f"no={report.summary.get('no', 0)}, "
        f"bonus={report.summary.get('bonus', 0)}, "
        f"local_only={report.summary.get('local_only', 0)})",
        "",
        "## Verdict",
        "",
        "You can drive OpenMontage **from Claude Agent SDK or Codex SDK** (not the interactive CLI) "
        "because those SDKs are the same file/shell agent loop with a Python/TypeScript API. "
        "You can replace **most generation API keys** with one `OPENROUTER_API_KEY`. "
        "You cannot collapse the whole studio into OpenRouter: composition, stock, local GPU, "
        "ElevenLabs, Higgsfield, and HeyGen's multi-model workflow stay outside it.",
        "",
        "## Capability matrix (live catalog)",
        "",
        "| Capability | Coverage | Live match | OpenMontage today | OpenRouter models found |",
        "|---|---|---|---|---|",
    ]
    for row in report.results:
        found = ", ".join(f"`{m}`" for m in row.found_models) or "—"
        live = "ok" if row.live_ok else "DRIFT"
        lines.append(
            f"| `{row.capability}` | {COVERAGE_LABEL[row.coverage]} | {live} | "
            f"{row.openmontage} | {found} |"
        )
    lines += [
        "",
        "## Keys one OpenRouter credential can replace",
        "",
    ]
    lines += [f"- {item}" for item in KEYS_OPENMONTAGE_REPLACES_WITH_OPENROUTER]
    lines += ["", "## Keys / runtimes you still need", ""]
    lines += [f"- {item}" for item in KEYS_STILL_REQUIRED]
    lines += [
        "",
        "## Live catalog probes",
        "",
        f"- HeyGen on OpenRouter: {report.extras.get('heygen_on_openrouter') or 'none'}",
        f"- Kling on OpenRouter: {report.extras.get('kling_on_openrouter') or 'none'}",
        f"- Higgsfield on OpenRouter: {report.extras.get('higgsfield_on_openrouter') or 'none'}",
        f"- ElevenLabs on OpenRouter: {report.extras.get('elevenlabs_on_openrouter') or 'none'}",
        f"- Suno on OpenRouter: {report.extras.get('suno_on_openrouter') or 'none'}",
        f"- Live matrix failures: {report.extras.get('live_failures') or 'none'}",
        "",
        "## Video models currently listed",
        "",
    ]
    for vid in report.video_ids:
        lines.append(f"- `{vid}`")
    lines.append("")
    return "\n".join(lines)
