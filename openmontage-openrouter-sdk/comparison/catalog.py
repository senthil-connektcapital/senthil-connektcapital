"""Live OpenRouter catalog vs OpenMontage capability matrix."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from comparison.matrix import CAPABILITIES
from gateway.openrouter import list_models, list_video_models, model_ids, output_modalities


@dataclass
class CapabilityResult:
    capability: str
    coverage: str
    openmontage: str
    expected_models: list[str]
    found_models: list[str]
    missing_models: list[str]
    live_ok: bool
    notes: str


@dataclass
class ComparisonReport:
    video_model_count: int
    image_model_count: int
    speech_model_count: int
    transcription_model_count: int
    video_ids: list[str]
    results: list[CapabilityResult]
    summary: dict[str, int] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["results"] = [asdict(r) for r in self.results]
        return payload


def _present(expected: str, catalog: set[str]) -> bool:
    if expected in catalog:
        return True
    # Allow prefix matches so recraft/recraft-v4.1 hits recraft/recraft-v4.1-pro etc.
    return any(item == expected or item.startswith(expected + "-") or item.startswith(expected + "/") for item in catalog)


def run_comparison() -> ComparisonReport:
    video_models = list_video_models()
    all_models = list_models("all")
    video_ids = sorted(model_ids(video_models))
    all_ids = model_ids(all_models)

    image_ids = {m["id"] for m in all_models if "image" in output_modalities(m) and m.get("id")}
    speech_ids = {m["id"] for m in all_models if any(x in output_modalities(m) for x in ("speech", "audio")) and m.get("id")}
    transcription_ids = {m["id"] for m in all_models if "transcription" in output_modalities(m) and m.get("id")}

    catalog = all_ids | set(video_ids)
    results: list[CapabilityResult] = []
    summary: dict[str, int] = {}

    for row in CAPABILITIES:
        expected = list(row["openrouter_models"])
        found = [model for model in expected if _present(model, catalog)]
        missing = [model for model in expected if model not in found]
        if row["coverage"] in {"no", "local_only"}:
            live_ok = not expected
        elif row["coverage"] == "bonus":
            live_ok = bool(found)
        elif row["coverage"] == "partial":
            live_ok = bool(found) or not expected
        else:
            live_ok = bool(found) and not missing
        result = CapabilityResult(
            capability=row["capability"],
            coverage=row["coverage"],
            openmontage=row["openmontage"],
            expected_models=expected,
            found_models=found,
            missing_models=missing,
            live_ok=live_ok,
            notes=row["notes"],
        )
        results.append(result)
        summary[row["coverage"]] = summary.get(row["coverage"], 0) + 1

    extras = {
        "heygen_on_openrouter": sorted(i for i in catalog if i.startswith("heygen/")),
        "kling_on_openrouter": sorted(i for i in catalog if "kling" in i),
        "higgsfield_on_openrouter": sorted(i for i in catalog if "higgs" in i),
        "elevenlabs_on_openrouter": sorted(i for i in catalog if "eleven" in i),
        "suno_on_openrouter": sorted(i for i in catalog if "suno" in i),
        "live_failures": [r.capability for r in results if not r.live_ok],
    }

    return ComparisonReport(
        video_model_count=len(video_ids),
        image_model_count=len(image_ids),
        speech_model_count=len(speech_ids),
        transcription_model_count=len(transcription_ids),
        video_ids=video_ids,
        results=results,
        summary=summary,
        extras=extras,
    )
