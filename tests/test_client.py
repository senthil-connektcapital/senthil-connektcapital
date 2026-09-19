import json

import httpx
import pytest
import respx

from jimmy import Jimmy, AsyncJimmy
from jimmy.exceptions import APIStatusError


CHAT_URL = "https://chatjimmy.ai/api/chat"
MODELS_URL = "https://chatjimmy.ai/api/models"


@respx.mock
def test_chat_completion_basic():
    respx.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            text='PONG\n<|stats|>{"prefill_tokens":5,"decode_tokens":1,"total_tokens":6,"created_at":1700000000}<|/stats|>',
        )
    )
    client = Jimmy()
    r = client.chat.completions.create(
        model="llama3.1-8B",
        messages=[{"role": "user", "content": "Reply with exactly: PONG"}],
    )
    assert r.choices[0].message.content == "PONG"
    assert r.usage.total_tokens == 6
    assert r.model == "llama3.1-8B"
    client.close()


@respx.mock
def test_chat_sends_jimmy_payload():
    route = respx.post(CHAT_URL).mock(return_value=httpx.Response(200, text="ok"))
    client = Jimmy()
    client.chat.completions.create(
        model="llama3.1-8B",
        messages=[
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": "Hi"},
        ],
        top_k=4,
    )
    sent = json.loads(route.calls[0].request.content.decode())
    assert sent["chatOptions"]["selectedModel"] == "llama3.1-8B"
    assert sent["chatOptions"]["topK"] == 4
    assert sent["messages"][0]["role"] == "system"
    assert "Be brief." in sent["messages"][0]["content"]
    client.close()


@respx.mock
def test_tools_injected_and_parsed():
    body = '<tool_call>\n{"name": "add", "arguments": {"a": 2, "b": 3}}\n</tool_call>\n<|stats|>{"total_tokens":20}<|/stats|>'
    respx.post(CHAT_URL).mock(return_value=httpx.Response(200, text=body))
    client = Jimmy()
    r = client.chat.completions.create(
        model="llama3.1-8B",
        messages=[{"role": "user", "content": "2+3?"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "description": "Add",
                    "parameters": {
                        "type": "object",
                        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                        "required": ["a", "b"],
                    },
                },
            }
        ],
    )
    assert r.choices[0].finish_reason == "tool_calls"
    assert r.choices[0].message.tool_calls[0].function.name == "add"
    client.close()


@respx.mock
def test_run_tools_loop():
    responses = [
        httpx.Response(
            200,
            text='<tool_call>\n{"name": "add", "arguments": {"a": 2, "b": 2}}\n</tool_call>',
        ),
        httpx.Response(200, text="The sum is 4."),
    ]
    respx.post(CHAT_URL).mock(side_effect=responses)
    client = Jimmy()
    final = client.chat.completions.run_tools(
        messages=[{"role": "user", "content": "What is 2+2?"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "description": "Add two numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                        "required": ["a", "b"],
                    },
                },
            }
        ],
        functions={"add": lambda a, b: a + b},
    )
    assert final.choices[0].message.content == "The sum is 4."
    client.close()


@respx.mock
def test_models_list():
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
    client.close()


@respx.mock
def test_api_error():
    respx.post(CHAT_URL).mock(return_value=httpx.Response(500, text="boom"))
    client = Jimmy()
    with pytest.raises(APIStatusError) as ei:
        client.chat.completions.create(messages=[{"role": "user", "content": "x"}])
    assert ei.value.status_code == 500
    client.close()


@respx.mock
@pytest.mark.asyncio
async def test_async_chat():
    respx.post(CHAT_URL).mock(return_value=httpx.Response(200, text="hello async"))
    client = AsyncJimmy()
    r = await client.chat.completions.create(messages=[{"role": "user", "content": "hi"}])
    assert r.choices[0].message.content == "hello async"
    await client.close()
