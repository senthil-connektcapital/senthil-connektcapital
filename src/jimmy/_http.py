"""HTTP helpers for chatjimmy.ai."""

from __future__ import annotations

from typing import Any, Dict, Iterator, Mapping, Optional

import httpx

from .exceptions import APIConnectionError, APIStatusError

DEFAULT_BASE_URL = "https://chatjimmy.ai"
DEFAULT_CHAT_PATH = "/api/chat"
DEFAULT_MODELS_PATH = "/api/models"

DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "User-Agent": "jimmy-openai-python/0.1.0",
    "Referer": "https://chatjimmy.ai/",
    "Origin": "https://chatjimmy.ai",
}


def merge_headers(*parts: Optional[Mapping[str, str]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in parts:
        if part:
            out.update(dict(part))
    return out


def raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    body = response.text
    raise APIStatusError(
        f"Jimmy API error {response.status_code}: {body[:400]}",
        status_code=response.status_code,
        body=body,
    )


def wrap_request_error(exc: Exception) -> APIConnectionError:
    return APIConnectionError(str(exc) or "Connection error.", request=getattr(exc, "request", None))


def iter_text_stream(response: httpx.Response, *, chunk_size: int = 64) -> Iterator[str]:
    for chunk in response.iter_text(chunk_size=chunk_size):
        if chunk:
            yield chunk


def build_chat_body(
    *,
    messages: list,
    model: str,
    system_prompt: str = "",
    top_k: int = 8,
    attachment: Any = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "messages": messages,
        "chatOptions": {
            "selectedModel": model,
            "systemPrompt": system_prompt or "",
            "topK": top_k,
        },
        "attachment": attachment,
    }
    if extra:
        body.update(extra)
    return body
