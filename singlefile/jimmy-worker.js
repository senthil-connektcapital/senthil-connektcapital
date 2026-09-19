/**
 * jimmy-worker.js — single-file Cloudflare Worker proxy for chatjimmy.ai
 *
 * WHY THIS EXISTS
 * ---------------
 * chatjimmy.ai does NOT send Access-Control-Allow-Origin. Browsers therefore
 * block direct fetch() from your site (CORS). A tiny same-origin / edge proxy
 * is required. This Worker is that proxy — deploy once, call from the browser.
 *
 * Deploy (Cloudflare, free):
 *   npx wrangler deploy singlefile/jimmy-worker.js --name jimmy-proxy --compatibility-date 2024-11-01
 *
 * Or paste into Workers dashboard → Quick edit → Save & Deploy.
 *
 * Endpoints (OpenAI-shaped):
 *   GET  /v1/models
 *   POST /v1/chat/completions
 *   GET  /health
 *
 * Browser:
 *   const r = await fetch("https://jimmy-proxy.<you>.workers.dev/v1/chat/completions", {
 *     method: "POST",
 *     headers: { "Content-Type": "application/json" },
 *     body: JSON.stringify({
 *       model: "llama3.1-8B",
 *       messages: [{ role: "user", content: "Hi" }],
 *     }),
 *   });
 */

const JIMMY_CHAT = "https://chatjimmy.ai/api/chat";
const JIMMY_MODELS = "https://chatjimmy.ai/api/models";
const DEFAULT_MODEL = "llama3.1-8B";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
  "Access-Control-Max-Age": "86400",
};

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS });
    }

    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";

    try {
      if (request.method === "GET" && (path === "/health" || path === "/")) {
        return json({ ok: true, proxy: "chatjimmy.ai", model: DEFAULT_MODEL });
      }
      if (request.method === "GET" && (path === "/v1/models" || path === "/api/models")) {
        return await proxyModels();
      }
      if (
        request.method === "POST" &&
        (path === "/v1/chat/completions" || path === "/api/chat" || path === "/chat")
      ) {
        return await proxyChat(request);
      }
      return json({ error: { message: `Not found: ${path}`, type: "invalid_request_error" } }, 404);
    } catch (err) {
      return json(
        { error: { message: String(err?.message || err), type: "api_error" } },
        500
      );
    }
  },
};

async function proxyModels() {
  const res = await fetch(JIMMY_MODELS, {
    headers: jimmyHeaders(),
    cf: { cacheTtl: 60 },
  });
  const data = await res.json();
  return json(data, res.status);
}

async function proxyChat(request) {
  const body = await request.json();
  const model = body.model || DEFAULT_MODEL;
  const stream = !!body.stream;
  const topK = body.top_k ?? body.topK ?? 8;
  const tools = body.tools || null;
  const toolChoice = body.tool_choice || "auto";
  const responseFormat = body.response_format || null;

  if (stream && responseFormat) {
    return json(
      { error: { message: "stream + response_format not supported together", type: "invalid_request_error" } },
      400
    );
  }
  if (tools?.length && responseFormat) {
    return json(
      { error: { message: "tools + response_format not supported together", type: "invalid_request_error" } },
      400
    );
  }

  const { messages, systemPrompt } = buildMessages(body.messages || [], {
    tools,
    toolChoice,
    responseFormat,
    systemPrompt: body.system_prompt || "",
  });

  const jimmyBody = {
    messages,
    chatOptions: {
      selectedModel: model,
      systemPrompt,
      topK,
    },
    attachment: body.attachment ?? null,
  };

  const upstream = await fetch(JIMMY_CHAT, {
    method: "POST",
    headers: jimmyHeaders(),
    body: JSON.stringify(jimmyBody),
  });

  if (!upstream.ok) {
    const t = await upstream.text();
    return json(
      { error: { message: `Jimmy API error ${upstream.status}: ${t.slice(0, 200)}`, type: "api_error" } },
      upstream.status
    );
  }

  if (stream) {
    return streamOpenAI(upstream, model);
  }

  const raw = await upstream.text();
  const { text, stats } = splitStats(raw);
  const completion = toChatCompletion(text, model, stats, {
    enableTools: !!(tools && tools.length && toolChoice !== "none"),
    responseFormat,
  });
  return json(completion);
}

function jimmyHeaders() {
  return {
    "Content-Type": "application/json",
    Accept: "*/*",
    "User-Agent": "jimmy-worker/1.0",
    Referer: "https://chatjimmy.ai/",
    Origin: "https://chatjimmy.ai",
  };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...CORS },
  });
}

function buildMessages(messages, { tools, toolChoice, responseFormat, systemPrompt }) {
  const systems = [];
  const rest = [];

  for (const m of messages) {
    if (m.role === "system") {
      if (m.content) systems.push(m.content);
      continue;
    }
    if (m.role === "tool") {
      rest.push({
        role: "user",
        content: `[tool_result name=${m.name || "tool"} tool_call_id=${m.tool_call_id || ""}]\n${m.content || ""}`,
      });
      continue;
    }
    if (m.role === "assistant" && m.tool_calls?.length) {
      const parts = [];
      if (m.content) parts.push(m.content);
      for (const tc of m.tool_calls) {
        let args = tc.function?.arguments ?? "{}";
        try {
          args = typeof args === "string" ? JSON.parse(args) : args;
        } catch {
          args = { _raw: args };
        }
        parts.push(
          `<tool_call>\n${JSON.stringify({ name: tc.function?.name, arguments: args })}\n</tool_call>`
        );
      }
      rest.push({ role: "assistant", content: parts.join("\n") });
      continue;
    }
    rest.push({ role: m.role, content: m.content || "" });
  }

  if (systemPrompt) systems.push(systemPrompt);
  if (tools?.length && toolChoice !== "none") {
    systems.push(toolsSystemPrompt(tools, toolChoice));
  }
  if (responseFormat) {
    systems.push(structuredSystemPrompt(responseFormat));
  }

  const sys = systems.filter(Boolean).join("\n\n");
  const out = [];
  if (sys) out.push({ role: "system", content: sys });
  out.push(...rest);
  return { messages: out, systemPrompt: sys };
}

function toolsSystemPrompt(tools, toolChoice) {
  const schema = tools.map((t) => {
    const fn = t.function || t;
    return {
      name: fn.name,
      description: fn.description || "",
      parameters: fn.parameters || { type: "object", properties: {} },
    };
  });
  let extra = "";
  if (toolChoice === "required") {
    extra = "\nYou MUST call at least one tool using <tool_call>. Do not answer in plain text.";
  } else if (toolChoice && typeof toolChoice === "object" && toolChoice.function?.name) {
    extra = `\nYou MUST call the tool named \`${toolChoice.function.name}\` using <tool_call>.`;
  }
  return `You are a function-calling assistant.
You have access to the following tools (JSON Schema):

${JSON.stringify(schema, null, 2)}

When you need to call a tool, respond with ONLY one or more tool calls in this exact format:

<tool_call>
{"name": "TOOL_NAME", "arguments": {"arg": "value"}}
</tool_call>

Rules:
- Use only the tools listed above.
- Put JSON arguments as an object (not a string).
- If you can answer without tools, reply with normal assistant text and do NOT emit <tool_call>.${extra}`;
}

function structuredSystemPrompt(responseFormat) {
  if (responseFormat.type === "json_object") {
    return `You must respond with a single valid JSON object only.
Do not wrap it in markdown fences. Do not include any prose before or after the JSON.`;
  }
  if (responseFormat.type === "json_schema") {
    const js = responseFormat.json_schema || {};
    return `You must respond with a single valid JSON value that conforms to this JSON Schema.
Do not wrap it in markdown fences. Do not include any prose before or after the JSON.

JSON Schema (${js.name || "response"}):
${JSON.stringify(js.schema || {}, null, 2)}`;
  }
  return "";
}

function splitStats(body) {
  const m = body.match(/<\|stats\|>([\s\S]*?)<\|\/stats\|>/);
  if (!m) return { text: body.trim(), stats: null };
  let stats = null;
  try {
    stats = JSON.parse(m[1]);
  } catch {
    stats = { raw: m[1] };
  }
  return { text: body.slice(0, m.index).trim(), stats };
}

function parseToolCalls(text) {
  const re = /<tool_call>\s*(\{[\s\S]*?\})\s*<\/tool_call>/gi;
  const out = [];
  let match;
  while ((match = re.exec(text))) {
    try {
      const obj = JSON.parse(match[1]);
      const name = obj.name;
      let args = obj.arguments ?? obj.parameters ?? {};
      if (typeof args === "string") {
        try {
          args = JSON.parse(args);
        } catch {
          args = { _raw: args };
        }
      }
      if (name) {
        out.push({
          id: `call_${crypto.randomUUID().replace(/-/g, "").slice(0, 24)}`,
          type: "function",
          function: { name, arguments: JSON.stringify(args) },
        });
      }
    } catch {
      /* skip */
    }
  }
  return out;
}

function extractJson(text) {
  const raw = String(text || "").trim();
  const fence = raw.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
  const candidate = fence ? fence[1].trim() : raw;
  try {
    return JSON.parse(candidate);
  } catch {
    /* fall through */
  }
  const startObj = candidate.indexOf("{");
  const startArr = candidate.indexOf("[");
  let start = -1;
  if (startObj >= 0 && (startArr < 0 || startObj < startArr)) start = startObj;
  else if (startArr >= 0) start = startArr;
  if (start < 0) throw new Error("Could not parse JSON from model response");
  const opener = candidate[start];
  const closer = opener === "{" ? "}" : "]";
  let depth = 0,
    inStr = false,
    esc = false;
  for (let i = start; i < candidate.length; i++) {
    const ch = candidate[i];
    if (inStr) {
      if (esc) esc = false;
      else if (ch === "\\") esc = true;
      else if (ch === '"') inStr = false;
      continue;
    }
    if (ch === '"') inStr = true;
    else if (ch === opener) depth++;
    else if (ch === closer) {
      depth--;
      if (depth === 0) return JSON.parse(candidate.slice(start, i + 1));
    }
  }
  throw new Error("Could not parse JSON from model response");
}

function toChatCompletion(text, model, stats, { enableTools, responseFormat }) {
  const id = `chatcmpl-${crypto.randomUUID().replace(/-/g, "").slice(0, 24)}`;
  const created = Math.floor(stats?.created_at || Date.now() / 1000);
  let message = { role: "assistant", content: text };
  let finish_reason = stats?.done_reason === "length" ? "length" : "stop";

  if (enableTools) {
    const tool_calls = parseToolCalls(text);
    if (tool_calls.length) {
      message = {
        role: "assistant",
        content: text.replace(/<tool_call>[\s\S]*?<\/tool_call>/gi, "").trim() || null,
        tool_calls,
      };
      finish_reason = "tool_calls";
    }
  } else if (responseFormat && (responseFormat.type === "json_object" || responseFormat.type === "json_schema")) {
    const parsed = extractJson(text);
    if (responseFormat.type === "json_object" && (parsed === null || typeof parsed !== "object" || Array.isArray(parsed))) {
      throw new Error("json_object response_format requires a JSON object");
    }
    message = { role: "assistant", content: JSON.stringify(parsed), parsed };
  }

  return {
    id,
    object: "chat.completion",
    created,
    model,
    choices: [{ index: 0, message, finish_reason }],
    usage: {
      prompt_tokens: stats?.prefill_tokens || 0,
      completion_tokens: stats?.decode_tokens || 0,
      total_tokens: stats?.total_tokens || 0,
    },
  };
}

function streamOpenAI(upstream, model) {
  const id = `chatcmpl-${crypto.randomUUID().replace(/-/g, "").slice(0, 24)}`;
  const created = Math.floor(Date.now() / 1000);
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  let buffer = "";
  let started = false;
  let closed = false;

  const stream = new ReadableStream({
    async start(controller) {
      const reader = upstream.body.getReader();
      const send = (obj) => controller.enqueue(encoder.encode(`data: ${JSON.stringify(obj)}\n\n`));

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          let piece = decoder.decode(value, { stream: true });
          buffer += piece;
          if (piece.includes("<|stats|>")) {
            piece = piece.slice(0, piece.indexOf("<|stats|>"));
            closed = true;
          }
          piece = piece.replace(/<\|stats\|>[\s\S]*?<\|\/stats\|>/g, "");
          if (!piece) {
            if (closed) break;
            continue;
          }
          if (!started) {
            started = true;
            send({
              id,
              object: "chat.completion.chunk",
              created,
              model,
              choices: [{ index: 0, delta: { role: "assistant", content: piece }, finish_reason: null }],
            });
          } else {
            send({
              id,
              object: "chat.completion.chunk",
              created,
              model,
              choices: [{ index: 0, delta: { content: piece }, finish_reason: null }],
            });
          }
          if (closed) break;
        }
        send({
          id,
          object: "chat.completion.chunk",
          created,
          model,
          choices: [{ index: 0, delta: {}, finish_reason: "stop" }],
        });
        controller.enqueue(encoder.encode("data: [DONE]\n\n"));
        controller.close();
      } catch (err) {
        controller.error(err);
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      ...CORS,
    },
  });
}
