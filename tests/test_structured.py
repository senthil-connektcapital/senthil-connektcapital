import json

import httpx
import pytest
import respx
from pydantic import BaseModel, Field

from jimmy import Jimmy
from jimmy.exceptions import APIError
from jimmy.structured import (
    extract_json_value,
    normalize_response_format,
    parse_structured_content,
    validate_json_schema,
)


CHAT_URL = "https://chatjimmy.ai/api/chat"


class Event(BaseModel):
    name: str
    date: str
    participants: list[str] = Field(default_factory=list)


def test_extract_json_from_fence():
    text = 'Sure!\n```json\n{"a": 1}\n```\n'
    assert extract_json_value(text) == {"a": 1}


def test_extract_json_with_prose():
    text = 'Here you go: {"city": "Paris", "country": "France"} thanks'
    assert extract_json_value(text)["city"] == "Paris"


def test_validate_schema_required():
    schema = {
        "type": "object",
        "properties": {"x": {"type": "string"}},
        "required": ["x"],
        "additionalProperties": False,
    }
    validate_json_schema({"x": "ok"}, schema)
    with pytest.raises(APIError):
        validate_json_schema({}, schema)
    with pytest.raises(APIError):
        validate_json_schema({"x": "ok", "y": 1}, schema)


def test_normalize_pydantic_model():
    fmt, model = normalize_response_format(Event)
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["name"] == "Event"
    assert model is Event


def test_parse_structured_pydantic():
    content, parsed = parse_structured_content(
        '{"name": "Sync", "date": "2026-08-01", "participants": ["A"]}',
        fmt=None,
        pydantic_model=Event,
    )
    assert isinstance(parsed, Event)
    assert parsed.name == "Sync"
    assert json.loads(content)["date"] == "2026-08-01"


@respx.mock
def test_create_json_object():
    route = respx.post(CHAT_URL).mock(
        return_value=httpx.Response(200, text='{"city":"Paris","country":"France"}')
    )
    client = Jimmy()
    r = client.chat.completions.create(
        messages=[{"role": "user", "content": "capital of France as JSON"}],
        response_format={"type": "json_object"},
    )
    assert r.choices[0].message.parsed == {"city": "Paris", "country": "France"}
    sent = json.loads(route.calls[0].request.content.decode())
    assert "JSON object" in sent["messages"][0]["content"]
    client.close()


@respx.mock
def test_parse_pydantic():
    respx.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            text='```json\n{"name":"Launch","date":"2026-09-01","participants":["Ada"]}\n```',
        )
    )
    client = Jimmy()
    r = client.chat.completions.parse(
        messages=[{"role": "user", "content": "extract event"}],
        response_format=Event,
    )
    event = r.choices[0].message.parsed
    assert isinstance(event, Event)
    assert event.participants == ["Ada"]
    client.close()


@respx.mock
def test_json_schema_strict():
    respx.post(CHAT_URL).mock(
        return_value=httpx.Response(200, text='{"label":"positive","score":0.9}')
    )
    client = Jimmy()
    r = client.chat.completions.create(
        messages=[{"role": "user", "content": "classify"}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "cls",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "score": {"type": "number"},
                    },
                    "required": ["label", "score"],
                    "additionalProperties": False,
                },
            },
        },
    )
    assert r.choices[0].message.parsed.label == "positive"  # type: ignore[union-attr]
    client.close()


@respx.mock
def test_structured_rejects_stream():
    client = Jimmy()
    with pytest.raises(APIError):
        client.chat.completions.create(
            messages=[{"role": "user", "content": "x"}],
            response_format={"type": "json_object"},
            stream=True,
        )
    client.close()


@respx.mock
def test_structured_rejects_tools_combo():
    client = Jimmy()
    with pytest.raises(APIError):
        client.chat.completions.create(
            messages=[{"role": "user", "content": "x"}],
            response_format={"type": "json_object"},
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "noop",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
        )
    client.close()
