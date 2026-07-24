#!/usr/bin/env python3
"""
jimmy-proxy.py — single-file stdlib proxy for chatjimmy.ai (no pip deps).

CORS: browsers cannot call chatjimmy.ai directly (no ACAO headers).
Run this on localhost / a tiny VPS / Railway / Fly and point the browser at it.

  python3 jimmy-proxy.py                  # http://127.0.0.1:8787
  PORT=8080 python3 jimmy-proxy.py

Endpoints:
  GET  /health
  GET  /v1/models
  POST /v1/chat/completions   (OpenAI-shaped; tools + response_format supported)
"""

from __future__ import annotations

import json
import os
import re
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.request import Request, urlopen

JIMMY_CHAT = "https://chatjimmy.ai/api/chat"
JIMMY_MODELS = "https://chatjimmy.ai/api/models"
DEFAULT_MODEL = "llama3.1-8B"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8787"))

STATS_RE = re.compile(r"<\|stats\|>([\s\S]*?)<\|/stats\|>")
TOOL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL | re.I)
FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.I)


def jimmy_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "jimmy-proxy-py/1.0",
        "Referer": "https://chatjimmy.ai/",
        "Origin": "https://chatjimmy.ai",
    }


def http_json(url: str, payload: dict | None = None) -> tuple[int, str, str]:
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(url, data=data, headers=jimmy_headers(), method="GET" if data is None else "POST")
    with urlopen(req, timeout=120) as res:  # noqa: S310 — intentional upstream
        body = res.read().decode("utf-8", errors="replace")
        return res.status, res.headers.get("Content-Type", "application/json"), body


def split_stats(body: str) -> tuple[str, dict | None]:
    m = STATS_RE.search(body)
    if not m:
        return body.strip(), None
    try:
        stats = json.loads(m.group(1))
    except json.JSONDecodeError:
        stats = {"raw": m.group(1)}
    return body[: m.start()].strip(), stats if isinstance(stats, dict) else None


def tools_prompt(tools: list, tool_choice: Any) -> str:
    schema = []
    for t in tools:
        fn = t.get("function") if isinstance(t, dict) else None
        fn = fn or t
        schema.append(
            {
                "name": fn.get("name"),
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    extra = ""
    if tool_choice == "required":
        extra = "\nYou MUST call at least one tool using <tool_call>."
    elif isinstance(tool_choice, dict) and tool_choice.get("function", {}).get("name"):
        extra = f"\nYou MUST call `{tool_choice['function']['name']}` using <tool_call>."
    return (
        "You are a function-calling assistant.\n"
        "Tools:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "When calling a tool respond ONLY with:\n"
        "<tool_call>\n"
        '{"name": "TOOL_NAME", "arguments": {"arg": "value"}}\n'
        "</tool_call>"
        f"{extra}"
    )


def structured_prompt(fmt: dict) -> str:
    if fmt.get("type") == "json_object":
        return "Respond with a single JSON object only. No markdown fences. No prose."
    if fmt.get("type") == "json_schema":
        js = fmt.get("json_schema") or {}
        return (
            "Respond with JSON only that matches this schema. No markdown fences. No prose.\n"
            f"Schema ({js.get('name') or 'response'}):\n"
            f"{json.dumps(js.get('schema') or {}, indent=2)}"
        )
    return ""


def prepare_messages(body: dict) -> tuple[list, str, str]:
    tools = body.get("tools") or []
    tool_choice = body.get("tool_choice", "auto")
    response_format = body.get("response_format")
    model = body.get("model") or DEFAULT_MODEL
    systems: list[str] = []
    rest: list[dict] = []
    for m in body.get("messages") or []:
        role = m.get("role")
        if role == "system":
            if m.get("content"):
                systems.append(m["content"])
            continue
        if role == "tool":
            rest.append(
                {
                    "role": "user",
                    "content": f"[tool_result name={m.get('name') or 'tool'}]\n{m.get('content') or ''}",
                }
            )
            continue
        rest.append({"role": role, "content": m.get("content") or ""})

    if body.get("system_prompt"):
        systems.append(body["system_prompt"])
    if tools and tool_choice != "none":
        systems.append(tools_prompt(tools, tool_choice))
    if response_format:
        systems.append(structured_prompt(response_format))

    sys = "\n\n".join(s for s in systems if s).strip()
    messages = ([{"role": "system", "content": sys}] if sys else []) + rest
    return messages, sys, model


def parse_tool_calls(text: str) -> list[dict]:
    out = []
    for m in TOOL_RE.finditer(text):
        try:
            obj = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        name = obj.get("name")
        args = obj.get("arguments", obj.get("parameters", {}))
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {"_raw": args}
        if name:
            out.append(
                {
                    "id": f"call_{uuid.uuid4().hex[:24]}",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(args)},
                }
            )
    return out


def extract_json(text: str) -> Any:
    raw = text.strip()
    fence = FENCE_RE.search(raw)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = raw.find(opener)
        if start < 0:
            continue
        depth = 0
        in_str = esc = False
        for i, ch in enumerate(raw[start:], start):
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw[start : i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError("Could not parse JSON from model response")


def to_completion(text: str, model: str, stats: dict | None, body: dict) -> dict:
    tools = body.get("tools") or []
    tool_choice = body.get("tool_choice", "auto")
    response_format = body.get("response_format")
    enable_tools = bool(tools and tool_choice != "none")
    message: dict[str, Any] = {"role": "assistant", "content": text}
    finish = "stop"
    if enable_tools:
        calls = parse_tool_calls(text)
        if calls:
            message = {
                "role": "assistant",
                "content": TOOL_RE.sub("", text).strip() or None,
                "tool_calls": calls,
            }
            finish = "tool_calls"
    elif response_format and response_format.get("type") in ("json_object", "json_schema"):
        parsed = extract_json(text)
        message = {"role": "assistant", "content": json.dumps(parsed), "parsed": parsed}

    created = int(stats.get("created_at") or 0) if stats else 0
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        "usage": {
            "prompt_tokens": int((stats or {}).get("prefill_tokens") or 0),
            "completion_tokens": int((stats or {}).get("decode_tokens") or 0),
            "total_tokens": int((stats or {}).get("total_tokens") or 0),
        },
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[jimmy-proxy] {self.address_string()} {fmt % args}")

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, obj: Any) -> None:
        self._send(status, json.dumps(obj).encode(), "application/json; charset=utf-8")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path in ("/", "/health"):
            return self._json(200, {"ok": True, "proxy": "chatjimmy.ai", "model": DEFAULT_MODEL})
        if path in ("/v1/models", "/api/models"):
            try:
                status, _, body = http_json(JIMMY_MODELS)
                return self._send(status, body.encode(), "application/json")
            except Exception as exc:  # noqa: BLE001
                return self._json(502, {"error": {"message": str(exc), "type": "api_error"}})
        return self._json(404, {"error": {"message": f"Not found: {path}", "type": "invalid_request_error"}})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path not in ("/v1/chat/completions", "/api/chat", "/chat"):
            return self._json(404, {"error": {"message": f"Not found: {path}", "type": "invalid_request_error"}})

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": {"message": "Invalid JSON", "type": "invalid_request_error"}})

        if body.get("stream"):
            return self._json(
                400,
                {
                    "error": {
                        "message": "Use jimmy-worker.js for streaming; this stdlib proxy is non-streaming.",
                        "type": "invalid_request_error",
                    }
                },
            )

        try:
            messages, system_prompt, model = prepare_messages(body)
            payload = {
                "messages": messages,
                "chatOptions": {
                    "selectedModel": model,
                    "systemPrompt": system_prompt,
                    "topK": body.get("top_k", body.get("topK", 8)),
                },
                "attachment": body.get("attachment"),
            }
            status, _, text = http_json(JIMMY_CHAT, payload)
            if status >= 400:
                return self._json(status, {"error": {"message": text[:200], "type": "api_error"}})
            content, stats = split_stats(text)
            return self._json(200, to_completion(content, model, stats, body))
        except Exception as exc:  # noqa: BLE001
            return self._json(502, {"error": {"message": str(exc), "type": "api_error"}})


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"jimmy-proxy listening on http://{HOST}:{PORT}")
    print("  GET  /health")
    print("  GET  /v1/models")
    print("  POST /v1/chat/completions")
    server.serve_forever()


if __name__ == "__main__":
    main()
