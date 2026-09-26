"""
Sample usage unit tests for jimmy-openai.

These tests are mocked (no live network) and mirror the common OpenAI-style
workflows: chat, streaming, tools, agent loop, JSON mode, and Pydantic parse.
Copy any block into your own code and swap the mocked responses for real calls.
"""

from __future__ import annotations

import json
from typing import List, Literal

import httpx
import pytest
import respx
from pydantic import BaseModel, Field

from jimmy import AsyncJimmy, Jimmy, OpenAI


CHAT_URL = "https://chatjimmy.ai/api/chat"
MODELS_URL = "https://chatjimmy.ai/api/models"


# ---------------------------------------------------------------------------
# Sample domain models (structured output)
# ---------------------------------------------------------------------------


class CalendarEvent(BaseModel):
    name: str
    date: str = Field(description="ISO date YYYY-MM-DD")
    participants: List[str]
    location: str = "TBD"


class Sentiment(BaseModel):
    label: Literal["positive", "neutral", "negative"]
    confidence: float = Field(ge=0, le=1)
    rationale: str


# ---------------------------------------------------------------------------
# Sample tools
# ---------------------------------------------------------------------------

WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"},
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "default": "celsius",
                },
            },
            "required": ["city"],
        },
    },
}

ADD_TOOL = {
    "type": "function",
    "function": {
        "name": "add",
        "description": "Add two numbers",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
        },
    },
}


def get_weather(city: str, unit: str = "celsius") -> dict:
    """Sample tool implementation."""
    temp = 22 if unit == "celsius" else 72
    return {"city": city, "temp": temp, "unit": unit, "conditions": "sunny"}


def add(a: float, b: float) -> float:
    return a + b


def _stats(text: str, *, prompt: int = 10, completion: int = 5) -> str:
    payload = {
        "prefill_tokens": prompt,
        "decode_tokens": completion,
        "total_tokens": prompt + completion,
        "created_at": 1700000000,
        "done_reason": "stop",
    }
    return f"{text}\n<|stats|>{json.dumps(payload)}<|/stats|>"


# ---------------------------------------------------------------------------
# 1) Basic chat — OpenAI drop-in style
# ---------------------------------------------------------------------------


@respx.mock
def test_sample_basic_chat():
    """
    Sample::

        from jimmy import Jimmy  # or: from jimmy import OpenAI

        client = Jimmy()
        completion = client.chat.completions.create(
            model="llama3.1-8B",
            messages=[
                {"role": "system", "content": "You are a concise assistant."},
                {"role": "user", "content": "Explain what an LLM is in one sentence."},
            ],
        )
        print(completion.choices[0].message.content)
    """
    respx.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            text=_stats("An LLM is a neural network trained to predict and generate text."),
        )
    )

    client = Jimmy()  # OpenAI() also works
    completion = client.chat.completions.create(
        model="llama3.1-8B",
        messages=[
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "Explain what an LLM is in one sentence."},
        ],
    )

    assert completion.model == "llama3.1-8B"
    assert "LLM" in (completion.choices[0].message.content or "")
    assert completion.usage is not None
    assert completion.usage.total_tokens == 15
    client.close()


@respx.mock
def test_sample_openai_alias():
    """``from jimmy import OpenAI`` is an alias of Jimmy."""
    respx.post(CHAT_URL).mock(return_value=httpx.Response(200, text=_stats("hi")))
    client = OpenAI()
    r = client.chat.completions.create(
        messages=[{"role": "user", "content": "Hi"}],
    )
    assert r.choices[0].message.content == "hi"
    client.close()


# ---------------------------------------------------------------------------
# 2) Streaming
# ---------------------------------------------------------------------------


@respx.mock
def test_sample_streaming():
    """
    Sample::

        stream = client.chat.completions.create(
            model="llama3.1-8B",
            messages=[{"role": "user", "content": "Count to 5"}],
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                print(delta, end="", flush=True)
    """
    body = "1\n2\n3\n4\n5" + '\n<|stats|>{"total_tokens":20}<|/stats|>'
    respx.post(CHAT_URL).mock(return_value=httpx.Response(200, text=body))

    client = Jimmy()
    stream = client.chat.completions.create(
        model="llama3.1-8B",
        messages=[{"role": "user", "content": "Count to 5"}],
        stream=True,
    )

    parts: list[str] = []
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            parts.append(delta)

    assert "".join(parts).startswith("1")
    assert "5" in "".join(parts)
    client.close()


# ---------------------------------------------------------------------------
# 3) Models list
# ---------------------------------------------------------------------------


@respx.mock
def test_sample_list_models():
    """
    Sample::

        models = client.models.list()
        for m in models.data:
            print(m.id)
    """
    respx.get(MODELS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "object": "list",
                "data": [
                    {
                        "id": "llama3.1-8B",
                        "object": "model",
                        "created": 1690000000,
                        "owned_by": "Taalas Inc.",
                    }
                ],
            },
        )
    )

    client = Jimmy()
    models = client.models.list()
    assert models.data[0].id == "llama3.1-8B"
    assert client.models.retrieve("llama3.1-8B").id == "llama3.1-8B"
    client.close()


# ---------------------------------------------------------------------------
# 4) Tool calling
# ---------------------------------------------------------------------------


@respx.mock
def test_sample_tool_calling():
    """
    Sample::

        response = client.chat.completions.create(
            model="llama3.1-8B",
            messages=[{"role": "user", "content": "What's the weather in Paris?"}],
            tools=[WEATHER_TOOL],
            tool_choice="auto",
        )
        msg = response.choices[0].message
        if msg.tool_calls:
            for call in msg.tool_calls:
                print(call.function.name, call.function.arguments)
    """
    tool_body = (
        '<tool_call>\n'
        '{"name": "get_weather", "arguments": {"city": "Paris", "unit": "celsius"}}\n'
        "</tool_call>"
    )
    respx.post(CHAT_URL).mock(return_value=httpx.Response(200, text=_stats(tool_body)))

    client = Jimmy()
    response = client.chat.completions.create(
        model="llama3.1-8B",
        messages=[{"role": "user", "content": "What's the weather in Paris?"}],
        tools=[WEATHER_TOOL],
        tool_choice="auto",
    )

    msg = response.choices[0].message
    assert response.choices[0].finish_reason == "tool_calls"
    assert msg.tool_calls is not None
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0].function.name == "get_weather"
    args = json.loads(msg.tool_calls[0].function.arguments)
    assert args["city"] == "Paris"
    client.close()


@respx.mock
def test_sample_run_tools_agent_loop():
    """
    Sample::

        final = client.chat.completions.run_tools(
            model="llama3.1-8B",
            messages=[{"role": "user", "content": "What's 41 + 1, then weather in Tokyo?"}],
            tools=[ADD_TOOL, WEATHER_TOOL],
            functions={"add": add, "get_weather": get_weather},
            max_rounds=5,
        )
        print(final.choices[0].message.content)
    """
    first = (
        '<tool_call>\n{"name": "add", "arguments": {"a": 41, "b": 1}}\n</tool_call>\n'
        '<tool_call>\n{"name": "get_weather", "arguments": {"city": "Tokyo"}}\n</tool_call>'
    )
    second = "41 + 1 = 42. Tokyo is sunny at 22C."
    respx.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(200, text=_stats(first)),
            httpx.Response(200, text=_stats(second)),
        ]
    )

    client = Jimmy()
    final = client.chat.completions.run_tools(
        model="llama3.1-8B",
        messages=[{"role": "user", "content": "What's 41 + 1, then weather in Tokyo?"}],
        tools=[ADD_TOOL, WEATHER_TOOL],
        functions={"add": add, "get_weather": get_weather},
        max_rounds=5,
    )

    assert final.choices[0].finish_reason == "stop"
    assert "42" in (final.choices[0].message.content or "")
    assert "Tokyo" in (final.choices[0].message.content or "")
    client.close()


# ---------------------------------------------------------------------------
# 5) Structured outputs
# ---------------------------------------------------------------------------


@respx.mock
def test_sample_json_object_mode():
    """
    Sample::

        r = client.chat.completions.create(
            model="llama3.1-8B",
            messages=[{
                "role": "user",
                "content": 'Return JSON with keys "city" and "country" for France\\'s capital.',
            }],
            response_format={"type": "json_object"},
        )
        print(r.choices[0].message.parsed)  # dict
    """
    respx.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            text=_stats('Here you go:\n```json\n{"city": "Paris", "country": "France"}\n```'),
        )
    )

    client = Jimmy()
    r = client.chat.completions.create(
        model="llama3.1-8B",
        messages=[
            {
                "role": "user",
                "content": 'Return JSON with keys "city" and "country" for France\'s capital.',
            }
        ],
        response_format={"type": "json_object"},
    )

    assert r.choices[0].message.parsed == {"city": "Paris", "country": "France"}
    assert json.loads(r.choices[0].message.content or "{}")["city"] == "Paris"
    client.close()


@respx.mock
def test_sample_json_schema_mode():
    """
    Sample::

        r = client.chat.completions.create(
            model="llama3.1-8B",
            messages=[{"role": "user", "content": "Classify: I love this SDK!"}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "sentiment",
                    "strict": True,
                    "schema": Sentiment.model_json_schema(),
                },
            },
        )
        print(r.choices[0].message.parsed)
    """
    respx.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            text=_stats(
                json.dumps(
                    {
                        "label": "positive",
                        "confidence": 0.95,
                        "rationale": "The phrase expresses affection.",
                    }
                )
            ),
        )
    )

    client = Jimmy()
    r = client.chat.completions.create(
        model="llama3.1-8B",
        messages=[{"role": "user", "content": "Classify: I love this SDK!"}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "sentiment",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string",
                            "enum": ["positive", "neutral", "negative"],
                        },
                        "confidence": {"type": "number"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["label", "confidence", "rationale"],
                    "additionalProperties": False,
                },
            },
        },
    )

    parsed = r.choices[0].message.parsed
    assert parsed is not None
    assert parsed.label == "positive"  # type: ignore[union-attr]
    assert parsed.confidence == 0.95  # type: ignore[union-attr]
    client.close()


@respx.mock
def test_sample_pydantic_parse():
    """
    Sample::

        r = client.chat.completions.parse(
            model="llama3.1-8B",
            messages=[{
                "role": "user",
                "content": "Extract event: Alice and Bob meet for Product sync on 2026-08-01 in SF.",
            }],
            response_format=CalendarEvent,
        )
        event: CalendarEvent = r.choices[0].message.parsed
        print(event.model_dump())
    """
    respx.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            text=_stats(
                json.dumps(
                    {
                        "name": "Product sync",
                        "date": "2026-08-01",
                        "participants": ["Alice", "Bob"],
                        "location": "SF",
                    }
                )
            ),
        )
    )

    client = Jimmy()
    r = client.chat.completions.parse(
        model="llama3.1-8B",
        messages=[
            {
                "role": "user",
                "content": "Extract event: Alice and Bob meet for Product sync on 2026-08-01 in SF.",
            }
        ],
        response_format=CalendarEvent,
    )

    event = r.choices[0].message.parsed
    assert isinstance(event, CalendarEvent)
    assert event.name == "Product sync"
    assert event.participants == ["Alice", "Bob"]
    assert event.location == "SF"
    client.close()


# ---------------------------------------------------------------------------
# 6) Async sample
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_sample_async_chat():
    """
    Sample::

        import asyncio
        from jimmy import AsyncJimmy

        async def main():
            client = AsyncJimmy()
            r = await client.chat.completions.create(
                model="llama3.1-8B",
                messages=[{"role": "user", "content": "Hi"}],
            )
            print(r.choices[0].message.content)
            await client.close()

        asyncio.run(main())
    """
    respx.post(CHAT_URL).mock(return_value=httpx.Response(200, text=_stats("hello async")))

    client = AsyncJimmy()
    r = await client.chat.completions.create(
        model="llama3.1-8B",
        messages=[{"role": "user", "content": "Hi"}],
    )
    assert r.choices[0].message.content == "hello async"
    await client.close()


@respx.mock
@pytest.mark.asyncio
async def test_sample_async_pydantic_parse():
    respx.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            text=_stats(
                '{"name":"Standup","date":"2026-08-02","participants":["Cara"],"location":"Zoom"}'
            ),
        )
    )

    client = AsyncJimmy()
    r = await client.chat.completions.parse(
        model="llama3.1-8B",
        messages=[{"role": "user", "content": "Extract the standup event"}],
        response_format=CalendarEvent,
    )
    event = r.choices[0].message.parsed
    assert isinstance(event, CalendarEvent)
    assert event.name == "Standup"
    await client.close()


# ---------------------------------------------------------------------------
# 7) Context-manager + ping sample
# ---------------------------------------------------------------------------


@respx.mock
def test_sample_context_manager_and_ping():
    """
    Sample::

        with Jimmy() as client:
            ms = client.ping()
            print(f"latency: {ms:.0f}ms")
    """
    respx.post(CHAT_URL).mock(return_value=httpx.Response(200, text=_stats("PONG")))

    with Jimmy() as client:
        ms = client.ping()
        assert ms >= 0
        r = client.chat.completions.create(
            messages=[{"role": "user", "content": "Reply with exactly: PONG"}],
        )
        assert "PONG" in (r.choices[0].message.content or "").upper()
