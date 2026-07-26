# HTTP API

Base URL: `http://<host>:8787` (default Docker port)

OpenAPI spec: [openapi.yaml](../openapi.yaml) · live at `/openapi.yaml` and `/openapi.json`

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/v1/models` | List models |
| `POST` | `/v1/chat/completions` | Chat completion |
| `GET` | `/openapi.yaml` | OpenAPI document (YAML) |
| `GET` | `/openapi.json` | OpenAPI document (JSON) |

All responses include CORS headers (`Access-Control-Allow-Origin: *`).

---

## 1. Health

```bash
curl http://localhost:8787/health
```

```json
{"ok": true, "proxy": "chatjimmy.ai", "model": "llama3.1-8B"}
```

---

## 2. List models

```bash
curl http://localhost:8787/v1/models
```

```json
{
  "object": "list",
  "data": [
    {
      "id": "llama3.1-8B",
      "object": "model",
      "created": 1690000000,
      "owned_by": "Taalas Inc."
    }
  ]
}
```

---

## 3. Chat completion

```bash
curl http://localhost:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1-8B",
    "messages": [
      {"role": "user", "content": "Say hello in one sentence."}
    ]
  }'
```

### Response

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1700000000,
  "model": "llama3.1-8B",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 8,
    "total_tokens": 20
  }
}
```

### Request fields

| Field | Type | Required | Description |
|---|---|---|---|
| `messages` | array | ✅ | Chat messages (`system`, `user`, `assistant`, `tool`) |
| `model` | string | | Default `llama3.1-8B` |
| `top_k` | integer | | 1–8, default `8` |
| `system_prompt` | string | | Extra system instructions |
| `tools` | array | | OpenAI-style function tools |
| `tool_choice` | string\|object | | `none`, `auto`, `required`, or forced function |
| `response_format` | object | | `json_object` or `json_schema` |
| `stream` | boolean | | **Not supported** in Docker proxy (400) |

---

## 4. Tool calling

```bash
curl http://localhost:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1-8B",
    "messages": [{"role": "user", "content": "Weather in Paris?"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather for a city",
        "parameters": {
          "type": "object",
          "properties": {"city": {"type": "string"}},
          "required": ["city"]
        }
      }
    }],
    "tool_choice": "auto"
  }'
```

When the model calls a tool, `finish_reason` is `tool_calls`:

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "id": "call_abc",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\": \"Paris\"}"
        }
      }]
    },
    "finish_reason": "tool_calls"
  }]
}
```

---

## 5. Structured output (`response_format`)

### JSON object

```bash
curl http://localhost:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1-8B",
    "messages": [{"role": "user", "content": "Capital of France as JSON with city and country keys"}],
    "response_format": {"type": "json_object"}
  }'
```

`message.content` is JSON text; `message.parsed` is the parsed object.

### JSON Schema

```bash
curl http://localhost:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1-8B",
    "messages": [{"role": "user", "content": "Classify: I love this!"}],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "sentiment",
        "strict": true,
        "schema": {
          "type": "object",
          "properties": {
            "label": {"type": "string", "enum": ["positive", "neutral", "negative"]},
            "confidence": {"type": "number"}
          },
          "required": ["label", "confidence"],
          "additionalProperties": false
        }
      }
    }
  }'
```

---

## 6. Browser (fetch)

Works because the proxy adds CORS headers:

```html
<script>
async function chat() {
  const res = await fetch("http://localhost:8787/v1/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "llama3.1-8B",
      messages: [{ role: "user", content: "Hi" }],
    }),
  });
  const data = await res.json();
  console.log(data.choices[0].message.content);
}
chat();
</script>
```

---

## 7. OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8787/v1",
    api_key="unused",
)

completion = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[{"role": "user", "content": "Hello"}],
)
print(completion.choices[0].message.content)
```

---

## Errors

```json
{
  "error": {
    "message": "Human-readable description",
    "type": "invalid_request_error"
  }
}
```

| HTTP | `type` | When |
|---|---|---|
| 400 | `invalid_request_error` | Bad JSON, `stream: true`, invalid body |
| 404 | `invalid_request_error` | Unknown path |
| 502 | `api_error` | chatjimmy.ai upstream failure |
