"""Tool-calling helpers for Llama 3.1 via prompt + parse."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from .types import Function, ToolCall, ToolChoice, ToolDict


TOOL_CALL_SYSTEM = """You are a function-calling assistant.
You have access to the following tools (JSON Schema):

{tools_json}

When you need to call a tool, respond with ONLY one or more tool calls in this exact format
(no prose before or after):

<tool_call>
{{"name": "TOOL_NAME", "arguments": {{"arg": "value"}}}}
</tool_call>

Rules:
- Use only the tools listed above.
- Put JSON arguments as an object (not a string).
- If multiple tools are needed, emit multiple <tool_call> blocks.
- If you can answer without tools, reply with normal assistant text and do NOT emit <tool_call>.
"""


_TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*(\{.*?\})\s*</tool_call>",
    re.DOTALL | re.IGNORECASE,
)
_PYTHON_TAG_RE = re.compile(
    r"<\|python_tag\|>\s*(\{.*?\})(?:<\|eom_id\|>|$)",
    re.DOTALL,
)
_JSON_OBJECT_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)


def normalize_tools(tools: Optional[Sequence[ToolDict]]) -> List[Dict[str, Any]]:
    if not tools:
        return []
    out: List[Dict[str, Any]] = []
    for t in tools:
        if not isinstance(t, dict):
            continue
        if t.get("type") == "function" and isinstance(t.get("function"), dict):
            out.append(t)
        elif "name" in t and "parameters" in t:
            # bare function schema
            out.append({"type": "function", "function": dict(t)})
        elif "function" in t and isinstance(t["function"], dict):
            out.append({"type": "function", "function": t["function"]})
    return out


def tools_to_llama_schema(tools: Sequence[ToolDict]) -> List[Dict[str, Any]]:
    schema: List[Dict[str, Any]] = []
    for t in normalize_tools(tools):
        fn = t["function"]
        schema.append(
            {
                "name": fn["name"],
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    return schema


def build_tools_system_prompt(tools: Sequence[ToolDict]) -> str:
    schema = tools_to_llama_schema(tools)
    return TOOL_CALL_SYSTEM.format(tools_json=json.dumps(schema, indent=2))


def _parse_call_payload(obj: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    name = obj.get("name") or obj.get("function")
    if not isinstance(name, str):
        return None

    args: Any = (
        obj.get("arguments")
        if "arguments" in obj
        else obj.get("parameters")
        if "parameters" in obj
        else obj.get("args")
    )
    if args is None:
        args = {}
    if isinstance(args, str):
        try:
            args = json.loads(args) if args.strip() else {}
        except json.JSONDecodeError:
            args = {"_raw": args}
    if not isinstance(args, dict):
        args = {"value": args}
    return name, args


def parse_tool_calls(text: str) -> List[ToolCall]:
    """Extract OpenAI-shaped tool_calls from model text."""
    if not text or not text.strip():
        return []

    found: List[ToolCall] = []
    seen: set[str] = set()

    def _add(name: str, arguments: Dict[str, Any]) -> None:
        key = f"{name}:{json.dumps(arguments, sort_keys=True)}"
        if key in seen:
            return
        seen.add(key)
        found.append(
            ToolCall(
                id=f"call_{uuid.uuid4().hex[:24]}",
                type="function",
                function=Function(name=name, arguments=json.dumps(arguments)),
            )
        )

    for pattern in (_TOOL_CALL_RE, _PYTHON_TAG_RE):
        for match in pattern.finditer(text):
            try:
                payload = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                parsed = _parse_call_payload(payload)
                if parsed:
                    _add(*parsed)

    # Fallback: whole response is a single JSON tool call
    stripped = text.strip()
    if not found and stripped.startswith("{") and stripped.endswith("}"):
        try:
            payload = json.loads(stripped)
            if isinstance(payload, dict):
                parsed = _parse_call_payload(payload)
                if parsed and parsed[0]:
                    # only accept if it looks like a tool call (has name + args/params)
                    if any(k in payload for k in ("arguments", "parameters", "args")):
                        _add(*parsed)
        except json.JSONDecodeError:
            pass

    # Fallback: scan for JSON objects that look like tool calls
    if not found:
        for match in _JSON_OBJECT_RE.finditer(text):
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            if "name" in payload and any(k in payload for k in ("arguments", "parameters", "args")):
                parsed = _parse_call_payload(payload)
                if parsed:
                    _add(*parsed)

    return found


def strip_tool_call_markup(text: str) -> str:
    """Remove tool-call markup so leftover prose can be returned as content."""
    cleaned = _TOOL_CALL_RE.sub("", text)
    cleaned = _PYTHON_TAG_RE.sub("", cleaned)
    return cleaned.strip()


def resolve_tool_choice(
    tool_choice: Optional[ToolChoice],
    tools: Sequence[ToolDict],
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Returns (mode, forced_tool) where mode is none|auto|required|forced.
    """
    if not tools:
        return "none", None
    if tool_choice is None or tool_choice == "auto":
        return "auto", None
    if tool_choice == "none":
        return "none", None
    if tool_choice == "required":
        return "required", None
    if isinstance(tool_choice, dict):
        # {"type":"function","function":{"name":"..."}}
        fn = tool_choice.get("function") or {}
        name = fn.get("name") if isinstance(fn, dict) else None
        if name:
            return "forced", {"name": name}
    return "auto", None


def apply_tool_choice_instruction(mode: str, forced: Optional[Dict[str, Any]]) -> str:
    if mode == "required":
        return (
            "\nYou MUST call at least one tool using the <tool_call> format. "
            "Do not answer in plain text."
        )
    if mode == "forced" and forced:
        return (
            f"\nYou MUST call the tool named `{forced['name']}` using the <tool_call> format. "
            "Do not answer in plain text."
        )
    return ""


def format_tool_result_message(tool_call_id: str, name: str, content: Union[str, Any]) -> Dict[str, Any]:
    if not isinstance(content, str):
        content = json.dumps(content)
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": name,
        "content": content,
    }


def assistant_tool_call_message(tool_calls: List[ToolCall], content: Optional[str] = None) -> Dict[str, Any]:
    return {
        "role": "assistant",
        "content": content,
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in tool_calls
        ],
    }
