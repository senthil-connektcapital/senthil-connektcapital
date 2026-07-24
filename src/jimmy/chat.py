"""Chat Completions resource (OpenAI-compatible)."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Callable, Dict, Iterator, List, Literal, Optional, Sequence, Union, overload

import httpx

from ._http import build_chat_body, iter_text_stream, raise_for_status, wrap_request_error
from ._parsing import STATS_RE, build_completion, split_stats
from .exceptions import APIError
from .tools import (
    apply_tool_choice_instruction,
    assistant_tool_call_message,
    build_tools_system_prompt,
    format_tool_result_message,
    normalize_tools,
    resolve_tool_choice,
)
from .types import (
    ChatCompletion,
    ChatCompletionChunk,
    ChunkChoice,
    Delta,
    MessageDict,
    ToolChoice,
    ToolDict,
)


def _coerce_messages(messages: Sequence[MessageDict]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in messages:
        if hasattr(m, "model_dump"):
            m = m.model_dump(exclude_none=True)  # type: ignore[assignment]
        role = m.get("role")
        if role not in ("system", "user", "assistant", "tool"):
            raise APIError(f"Unsupported message role: {role!r}")

        item: Dict[str, Any] = {"role": role, "content": m.get("content") or ""}

        # Flatten OpenAI tool messages into user-visible context for Jimmy
        if role == "tool":
            name = m.get("name") or "tool"
            tool_call_id = m.get("tool_call_id") or ""
            item = {
                "role": "user",
                "content": (
                    f"[tool_result name={name} tool_call_id={tool_call_id}]\n"
                    f"{m.get('content') or ''}"
                ),
            }
        elif role == "assistant" and m.get("tool_calls"):
            # Represent prior tool calls so the model can continue
            parts = []
            if m.get("content"):
                parts.append(str(m["content"]))
            for tc in m["tool_calls"]:
                fn = tc.get("function") if isinstance(tc, dict) else None
                if not fn and hasattr(tc, "function"):
                    fn = {"name": tc.function.name, "arguments": tc.function.arguments}
                if not fn:
                    continue
                args = fn.get("arguments", "{}")
                if not isinstance(args, str):
                    args = json.dumps(args)
                try:
                    args_obj = json.loads(args)
                except json.JSONDecodeError:
                    args_obj = {"_raw": args}
                parts.append(
                    "<tool_call>\n"
                    + json.dumps({"name": fn.get("name"), "arguments": args_obj})
                    + "\n</tool_call>"
                )
            item = {"role": "assistant", "content": "\n".join(parts)}

        out.append(item)
    return out


def _extract_system_prompt(messages: List[Dict[str, Any]], explicit: str = "") -> tuple[str, List[Dict[str, Any]]]:
    systems = [m["content"] for m in messages if m.get("role") == "system" and m.get("content")]
    rest = [m for m in messages if m.get("role") != "system"]
    combined = "\n\n".join([*systems, explicit] if explicit else systems).strip()
    return combined, rest


class Stream:
    """Iterator over ChatCompletionChunk, collecting full text."""

    def __init__(self, response: httpx.Response, *, model: str, completion_id: str):
        self._response = response
        self._model = model
        self._id = completion_id
        self._created = int(time.time())
        self._buffer = ""
        self._closed = False
        self._started = False

    def __iter__(self) -> Iterator[ChatCompletionChunk]:
        try:
            for piece in iter_text_stream(self._response):
                self._buffer += piece
                # Don't stream stats tags to the caller
                visible = STATS_RE.sub("", piece)
                # If stats started mid-chunk, trim at tag
                if "<|stats|>" in self._buffer and "<|stats|>" in piece:
                    idx = piece.find("<|stats|>")
                    visible = piece[:idx]
                if not self._started:
                    self._started = True
                    yield ChatCompletionChunk(
                        id=self._id,
                        created=self._created,
                        model=self._model,
                        choices=[ChunkChoice(index=0, delta=Delta(role="assistant", content=visible or None))],
                    )
                elif visible:
                    yield ChatCompletionChunk(
                        id=self._id,
                        created=self._created,
                        model=self._model,
                        choices=[ChunkChoice(index=0, delta=Delta(content=visible))],
                    )
            yield ChatCompletionChunk(
                id=self._id,
                created=self._created,
                model=self._model,
                choices=[ChunkChoice(index=0, delta=Delta(), finish_reason="stop")],
            )
        finally:
            self.close()

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._response.close()

    @property
    def raw_text(self) -> str:
        return self._buffer


class Completions:
    def __init__(self, client: Any):
        self._client = client

    @overload
    def create(
        self,
        *,
        messages: Sequence[MessageDict],
        model: str = ...,
        stream: Literal[False] = False,
        tools: Optional[Sequence[ToolDict]] = ...,
        tool_choice: Optional[ToolChoice] = ...,
        system_prompt: str = ...,
        top_k: Optional[int] = ...,
        temperature: Optional[float] = ...,
        max_tokens: Optional[int] = ...,
        extra_body: Optional[Dict[str, Any]] = ...,
        **kwargs: Any,
    ) -> ChatCompletion: ...

    @overload
    def create(
        self,
        *,
        messages: Sequence[MessageDict],
        model: str = ...,
        stream: Literal[True],
        tools: Optional[Sequence[ToolDict]] = ...,
        tool_choice: Optional[ToolChoice] = ...,
        system_prompt: str = ...,
        top_k: Optional[int] = ...,
        temperature: Optional[float] = ...,
        max_tokens: Optional[int] = ...,
        extra_body: Optional[Dict[str, Any]] = ...,
        **kwargs: Any,
    ) -> Stream: ...

    def create(
        self,
        *,
        messages: Sequence[MessageDict],
        model: str = "llama3.1-8B",
        stream: bool = False,
        tools: Optional[Sequence[ToolDict]] = None,
        tool_choice: Optional[ToolChoice] = None,
        system_prompt: str = "",
        top_k: Optional[int] = None,
        temperature: Optional[float] = None,  # accepted for OpenAI compat; not sent
        max_tokens: Optional[int] = None,  # accepted for OpenAI compat; not sent
        stop: Optional[Union[str, List[str]]] = None,  # noqa: ARG002 - compat noop
        presence_penalty: Optional[float] = None,  # noqa: ARG002
        frequency_penalty: Optional[float] = None,  # noqa: ARG002
        user: Optional[str] = None,  # noqa: ARG002
        extra_body: Optional[Dict[str, Any]] = None,
        attachment: Any = None,
        **kwargs: Any,
    ) -> Union[ChatCompletion, Stream]:
        del temperature, max_tokens, stop, presence_penalty, frequency_penalty, user, kwargs

        tools_n = normalize_tools(tools)
        mode, forced = resolve_tool_choice(tool_choice, tools_n)

        coerced = _coerce_messages(list(messages))
        sys_from_msgs, rest = _extract_system_prompt(coerced, system_prompt)

        if tools_n and mode != "none":
            tool_sys = build_tools_system_prompt(tools_n) + apply_tool_choice_instruction(mode, forced)
            sys_from_msgs = f"{sys_from_msgs}\n\n{tool_sys}".strip() if sys_from_msgs else tool_sys

        payload_messages: List[Dict[str, Any]] = []
        if sys_from_msgs:
            payload_messages.append({"role": "system", "content": sys_from_msgs})
        payload_messages.extend(rest)

        tk = top_k if top_k is not None else self._client.top_k
        if extra_body and "top_k" in extra_body:
            tk = int(extra_body.pop("top_k"))

        body = build_chat_body(
            messages=payload_messages,
            model=model or self._client.default_model,
            system_prompt=sys_from_msgs,
            top_k=tk,
            attachment=attachment,
            extra=extra_body,
        )

        url = self._client._chat_url()
        try:
            if stream:
                req = self._client._http.build_request(
                    "POST",
                    url,
                    json=body,
                    headers=self._client._headers(),
                )
                response = self._client._http.send(req, stream=True)
                raise_for_status(response)
                return Stream(
                    response,
                    model=model or self._client.default_model,
                    completion_id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
                )

            response = self._client._http.post(url, json=body, headers=self._client._headers())
            raise_for_status(response)
        except httpx.HTTPError as exc:
            raise wrap_request_error(exc) from exc

        raw = response.text
        text, stats = split_stats(raw)
        return build_completion(
            model=model or self._client.default_model,
            text=text,
            raw_body=raw,
            stats=stats,
            enable_tools=bool(tools_n and mode != "none"),
        )

    def run_tools(
        self,
        *,
        messages: Sequence[MessageDict],
        functions: Dict[str, Callable[..., Any]],
        tools: Sequence[ToolDict],
        model: str = "llama3.1-8B",
        max_rounds: int = 5,
        system_prompt: str = "",
        top_k: Optional[int] = None,
        tool_choice: Optional[ToolChoice] = "auto",
        **kwargs: Any,
    ) -> ChatCompletion:
        """
        Simple agentic loop: call the model, execute tool_calls via `functions`,
        append tool results, repeat until the model stops calling tools.
        """
        history: List[Dict[str, Any]] = [dict(m) for m in messages]
        last: Optional[ChatCompletion] = None

        for _ in range(max_rounds):
            last = self.create(
                model=model,
                messages=history,
                tools=tools,
                tool_choice=tool_choice,
                system_prompt=system_prompt,
                top_k=top_k,
                stream=False,
                **kwargs,
            )
            msg = last.choices[0].message
            if not msg.tool_calls:
                return last

            history.append(assistant_tool_call_message(msg.tool_calls, msg.content))
            for call in msg.tool_calls:
                fn = functions.get(call.function.name)
                if fn is None:
                    result: Any = {"error": f"Unknown tool: {call.function.name}"}
                else:
                    try:
                        args = json.loads(call.function.arguments or "{}")
                        result = fn(**args) if isinstance(args, dict) else fn(args)
                    except Exception as exc:  # noqa: BLE001 - surface to model
                        result = {"error": str(exc)}
                history.append(
                    format_tool_result_message(call.id, call.function.name, result)
                )

            # After the first forced call, allow the model to finish normally
            tool_choice = "auto"

        assert last is not None
        return last


class Chat:
    def __init__(self, client: Any):
        self.completions = Completions(client)


class AsyncStream:
    def __init__(self, response: httpx.Response, *, model: str, completion_id: str):
        self._response = response
        self._model = model
        self._id = completion_id
        self._created = int(time.time())
        self._buffer = ""
        self._closed = False
        self._started = False

    async def __aiter__(self):
        try:
            async for piece in self._response.aiter_text():
                if not piece:
                    continue
                self._buffer += piece
                visible = piece
                if "<|stats|>" in piece:
                    visible = piece[: piece.find("<|stats|>")]
                visible = STATS_RE.sub("", visible)
                if not self._started:
                    self._started = True
                    yield ChatCompletionChunk(
                        id=self._id,
                        created=self._created,
                        model=self._model,
                        choices=[ChunkChoice(index=0, delta=Delta(role="assistant", content=visible or None))],
                    )
                elif visible:
                    yield ChatCompletionChunk(
                        id=self._id,
                        created=self._created,
                        model=self._model,
                        choices=[ChunkChoice(index=0, delta=Delta(content=visible))],
                    )
            yield ChatCompletionChunk(
                id=self._id,
                created=self._created,
                model=self._model,
                choices=[ChunkChoice(index=0, delta=Delta(), finish_reason="stop")],
            )
        finally:
            await self.close()

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self._response.aclose()


class AsyncCompletions:
    def __init__(self, client: Any):
        self._client = client

    async def create(
        self,
        *,
        messages: Sequence[MessageDict],
        model: str = "llama3.1-8B",
        stream: bool = False,
        tools: Optional[Sequence[ToolDict]] = None,
        tool_choice: Optional[ToolChoice] = None,
        system_prompt: str = "",
        top_k: Optional[int] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        attachment: Any = None,
        **kwargs: Any,
    ) -> Union[ChatCompletion, AsyncStream]:
        del temperature, max_tokens, kwargs

        tools_n = normalize_tools(tools)
        mode, forced = resolve_tool_choice(tool_choice, tools_n)

        coerced = _coerce_messages(list(messages))
        sys_from_msgs, rest = _extract_system_prompt(coerced, system_prompt)

        if tools_n and mode != "none":
            tool_sys = build_tools_system_prompt(tools_n) + apply_tool_choice_instruction(mode, forced)
            sys_from_msgs = f"{sys_from_msgs}\n\n{tool_sys}".strip() if sys_from_msgs else tool_sys

        payload_messages: List[Dict[str, Any]] = []
        if sys_from_msgs:
            payload_messages.append({"role": "system", "content": sys_from_msgs})
        payload_messages.extend(rest)

        tk = top_k if top_k is not None else self._client.top_k
        if extra_body and "top_k" in extra_body:
            tk = int(extra_body.pop("top_k"))

        body = build_chat_body(
            messages=payload_messages,
            model=model or self._client.default_model,
            system_prompt=sys_from_msgs,
            top_k=tk,
            attachment=attachment,
            extra=extra_body,
        )

        url = self._client._chat_url()
        try:
            if stream:
                req = self._client._http.build_request(
                    "POST",
                    url,
                    json=body,
                    headers=self._client._headers(),
                )
                response = await self._client._http.send(req, stream=True)
                raise_for_status(response)
                return AsyncStream(
                    response,
                    model=model or self._client.default_model,
                    completion_id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
                )

            response = await self._client._http.post(url, json=body, headers=self._client._headers())
            raise_for_status(response)
        except httpx.HTTPError as exc:
            raise wrap_request_error(exc) from exc

        raw = response.text
        text, stats = split_stats(raw)
        return build_completion(
            model=model or self._client.default_model,
            text=text,
            raw_body=raw,
            stats=stats,
            enable_tools=bool(tools_n and mode != "none"),
        )

    async def run_tools(
        self,
        *,
        messages: Sequence[MessageDict],
        functions: Dict[str, Callable[..., Any]],
        tools: Sequence[ToolDict],
        model: str = "llama3.1-8B",
        max_rounds: int = 5,
        system_prompt: str = "",
        top_k: Optional[int] = None,
        tool_choice: Optional[ToolChoice] = "auto",
        **kwargs: Any,
    ) -> ChatCompletion:
        history: List[Dict[str, Any]] = [dict(m) for m in messages]
        last: Optional[ChatCompletion] = None

        for _ in range(max_rounds):
            last = await self.create(
                model=model,
                messages=history,
                tools=tools,
                tool_choice=tool_choice,
                system_prompt=system_prompt,
                top_k=top_k,
                stream=False,
                **kwargs,
            )
            msg = last.choices[0].message
            if not msg.tool_calls:
                return last

            history.append(assistant_tool_call_message(msg.tool_calls, msg.content))
            for call in msg.tool_calls:
                fn = functions.get(call.function.name)
                if fn is None:
                    result: Any = {"error": f"Unknown tool: {call.function.name}"}
                else:
                    try:
                        args = json.loads(call.function.arguments or "{}")
                        result = fn(**args) if isinstance(args, dict) else fn(args)
                    except Exception as exc:  # noqa: BLE001
                        result = {"error": str(exc)}
                history.append(format_tool_result_message(call.id, call.function.name, result))
            tool_choice = "auto"

        assert last is not None
        return last


class AsyncChat:
    def __init__(self, client: Any):
        self.completions = AsyncCompletions(client)
