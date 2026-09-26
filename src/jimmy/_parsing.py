"""Parse chatjimmy.ai text + <|stats|> payloads into OpenAI shapes."""

from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any, Dict, Optional, Tuple, Type

from pydantic import BaseModel

from .exceptions import APIError
from .structured import parse_structured_content
from .tools import parse_tool_calls, strip_tool_call_markup
from .types import (
    ChatCompletion,
    ChatCompletionMessage,
    Choice,
    Usage,
)

STATS_RE = re.compile(r"<\|stats\|>([\s\S]*?)<\|/stats\|>")


def split_stats(body: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    match = STATS_RE.search(body)
    if not match:
        return body.strip(), None
    text = body[: match.start()].strip()
    raw_stats = match.group(1).strip()
    try:
        stats = json.loads(raw_stats)
    except json.JSONDecodeError:
        stats = {"raw": raw_stats}
    return text, stats if isinstance(stats, dict) else {"raw": stats}


def usage_from_stats(stats: Optional[Dict[str, Any]]) -> Optional[Usage]:
    if not stats:
        return None
    prompt = int(stats.get("prefill_tokens") or stats.get("prompt_tokens") or 0)
    completion = int(stats.get("decode_tokens") or stats.get("completion_tokens") or 0)
    total = int(stats.get("total_tokens") or (prompt + completion))
    return Usage(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)


def build_completion(
    *,
    model: str,
    text: str,
    raw_body: str,
    stats: Optional[Dict[str, Any]] = None,
    enable_tools: bool = False,
    response_format: Optional[Dict[str, Any]] = None,
    pydantic_model: Optional[Type[BaseModel]] = None,
) -> ChatCompletion:
    tool_calls = parse_tool_calls(text) if enable_tools else []
    created = int(stats.get("created_at") or time.time()) if stats else int(time.time())
    if isinstance(created, float):
        created = int(created)

    finish_reason = "stop"
    if stats and stats.get("done_reason") == "length":
        finish_reason = "length"

    if tool_calls:
        content = strip_tool_call_markup(text) or None
        message = ChatCompletionMessage(
            role="assistant",
            content=content,
            tool_calls=tool_calls,
        )
        finish_reason = "tool_calls"
    elif response_format is not None or pydantic_model is not None:
        if finish_reason == "length":
            raise APIError(
                "Could not parse structured response because finish_reason was 'length'"
            )
        content, parsed = parse_structured_content(
            text,
            fmt=response_format,
            pydantic_model=pydantic_model,
        )
        message = ChatCompletionMessage(
            role="assistant",
            content=content,
            parsed=parsed,
        )
    else:
        message = ChatCompletionMessage(role="assistant", content=text)

    return ChatCompletion(
        id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
        created=created,
        model=model,
        choices=[Choice(index=0, message=message, finish_reason=finish_reason)],
        usage=usage_from_stats(stats),
        jimmy_stats=stats,
        jimmy_raw=raw_body,
    )
