"""Minimal OpenRouter client for catalog discovery and async video jobs.

One key (`OPENROUTER_API_KEY`) talks to video, image, speech, and LLM
endpoints. Video generation is asynchronous: submit → poll → download.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

BASE = "https://openrouter.ai/api/v1"
USER_AGENT = "openmontage-openrouter-sdk/0.1"


class OpenRouterError(RuntimeError):
    pass


def _headers(api_key: str | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def request(
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    api_key: str | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    url = path if path.startswith("http") else f"{BASE}{path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(api_key), method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise OpenRouterError(f"{method} {url} -> HTTP {exc.code}: {body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise OpenRouterError(f"{method} {url} failed: {exc}") from exc


def list_models(output_modalities: str = "all") -> list[dict[str, Any]]:
    data = request(f"/models?output_modalities={output_modalities}")
    return list(data.get("data") or [])


def list_video_models() -> list[dict[str, Any]]:
    data = request("/videos/models")
    return list(data.get("data") or [])


def model_ids(models: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for model in models:
        for key in ("id", "canonical_slug"):
            value = model.get(key)
            if value:
                ids.add(str(value))
    return ids


def output_modalities(model: dict[str, Any]) -> list[str]:
    arch = model.get("architecture") or {}
    return [str(x).lower() for x in (arch.get("output_modalities") or [])]


@dataclass
class VideoJob:
    id: str
    status: str
    polling_url: str
    raw: dict[str, Any]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "VideoJob":
        job_id = str(payload.get("id") or "")
        if not job_id:
            raise OpenRouterError(f"Video submit missing id: {payload}")
        return cls(
            id=job_id,
            status=str(payload.get("status") or "pending"),
            polling_url=str(payload.get("polling_url") or f"{BASE}/videos/{job_id}"),
            raw=payload,
        )


def submit_video(
    *,
    model: str,
    prompt: str,
    duration: int | None = None,
    resolution: str | None = None,
    aspect_ratio: str | None = None,
    generate_audio: bool | None = None,
    api_key: str | None = None,
) -> VideoJob:
    payload: dict[str, Any] = {"model": model, "prompt": prompt}
    if duration is not None:
        payload["duration"] = duration
    if resolution:
        payload["resolution"] = resolution
    if aspect_ratio:
        payload["aspect_ratio"] = aspect_ratio
    if generate_audio is not None:
        payload["generate_audio"] = generate_audio
    return VideoJob.from_payload(request("/videos", method="POST", payload=payload, api_key=api_key))


def poll_video(job: VideoJob, *, api_key: str | None = None) -> VideoJob:
    payload = request(job.polling_url, api_key=api_key)
    return VideoJob.from_payload(payload)


def wait_for_video(
    job: VideoJob,
    *,
    api_key: str | None = None,
    interval_seconds: float = 15.0,
    timeout_seconds: float = 600.0,
) -> VideoJob:
    deadline = time.time() + timeout_seconds
    current = job
    while time.time() < deadline:
        if current.status in {"completed", "failed", "cancelled", "expired"}:
            return current
        time.sleep(interval_seconds)
        current = poll_video(current, api_key=api_key)
    raise OpenRouterError(f"Timed out waiting for video job {job.id} (last status={current.status})")
