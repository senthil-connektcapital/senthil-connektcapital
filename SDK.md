# jimmy-openai

OpenAI SDK-compatible Python client for [chatjimmy.ai](https://chatjimmy.ai) (Llama 3.1 8B).

Drop-in style API for chat completions, streaming, models listing, **tool / function calling**, and **structured outputs** (`response_format` / Pydantic `.parse()`).

## Install

```bash
pip install -e .
# or with test deps
pip install -e ".[dev]"
```

## Quick start

```python
from jimmy import Jimmy

client = Jimmy()

completion = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello in one sentence."},
    ],
)

print(completion.choices[0].message.content)
```

Same surface as OpenAI:

```python
from jimmy import OpenAI  # alias of Jimmy

client = OpenAI()
```

## Tool calling

Llama 3.1 does not expose native OpenAI tool APIs on this endpoint, so the SDK injects a tool schema into the prompt and parses tool calls from the model output into OpenAI-shaped `tool_calls`.

```python
from jimmy import Jimmy

client = Jimmy()

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                },
                "required": ["city"],
            },
        },
    }
]

response = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[{"role": "user", "content": "What's the weather in Paris?"}],
    tools=tools,
    tool_choice="auto",
)

msg = response.choices[0].message
if msg.tool_calls:
    for call in msg.tool_calls:
        print(call.function.name, call.function.arguments)
else:
    print(msg.content)
```

## Structured outputs

OpenAI-compatible `response_format` and `.parse()` — JSON is prompted + validated client-side (Jimmy has no native structured-output endpoint).

### JSON object mode

```python
r = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[{"role": "user", "content": 'Return {"city","country"} for France\'s capital'}],
    response_format={"type": "json_object"},
)
print(r.choices[0].message.parsed)  # dict
```

### JSON Schema

```python
r = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[{"role": "user", "content": "Classify: I love this"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "sentiment",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "enum": ["positive", "neutral", "negative"]},
                    "confidence": {"type": "number"},
                },
                "required": ["label", "confidence"],
                "additionalProperties": False,
            },
        },
    },
)
print(r.choices[0].message.parsed)
```

### Pydantic `.parse()` (OpenAI-style)

```python
from pydantic import BaseModel, Field
from typing import List

class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: List[str]

r = client.chat.completions.parse(
    model="llama3.1-8B",
    messages=[{"role": "user", "content": "Alice and Bob meet on 2026-08-01 for sync"}],
    response_format=CalendarEvent,
)
event: CalendarEvent = r.choices[0].message.parsed
print(event.name, event.participants)
```

Notes:
- `message.content` is normalized JSON text; `message.parsed` is the dict / Pydantic instance.
- `response_format` cannot be combined with tool calling or `stream=True`.

### Agentic loop helper

```python
def get_weather(city: str) -> str:
    return f"Sunny, 22C in {city}"

final = client.chat.completions.run_tools(
    model="llama3.1-8B",
    messages=[{"role": "user", "content": "Weather in Tokyo?"}],
    tools=tools,
    functions={"get_weather": get_weather},
    max_rounds=5,
)
print(final.choices[0].message.content)
```

## Streaming

```python
stream = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[{"role": "user", "content": "Count to 5"}],
    stream=True,
)

for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
```

## Models

```python
models = client.models.list()
for m in models.data:
    print(m.id)
```

## Async

```python
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
```

## ChatJimmy options

Extra knobs map to chatjimmy.ai `chatOptions`:

| OpenAI-style / SDK arg | Maps to |
|---|---|
| `model` | `chatOptions.selectedModel` (default `llama3.1-8B`) |
| `top_k` / `extra_body["top_k"]` | `chatOptions.topK` (default `8`) |
| system message / `system_prompt` | `chatOptions.systemPrompt` + leading system message |

## Response shape

Responses mirror OpenAI `ChatCompletion`:

- `id`, `object`, `created`, `model`
- `choices[].message.role/content/tool_calls`
- `choices[].finish_reason` (`stop` | `tool_calls`)
- `usage` (from `<|stats|>` when present)
- `jimmy_stats` / `jimmy_raw` for raw endpoint data

## Endpoint

Server-side client posts to `https://chatjimmy.ai/api/chat` (no browser CORS). No API key is required by the public endpoint today.
