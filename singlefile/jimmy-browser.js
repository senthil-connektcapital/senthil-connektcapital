/**
 * jimmy-browser.js — single-file browser client (ESM).
 *
 * CORS: you cannot call chatjimmy.ai from the browser. Point baseURL at
 * your deployed jimmy-worker.js (Cloudflare Worker).
 *
 *   import { Jimmy } from "./jimmy-browser.js";
 *   const client = new Jimmy({ baseURL: "https://jimmy-proxy.<you>.workers.dev" });
 *   const r = await client.chat.completions.create({
 *     model: "llama3.1-8B",
 *     messages: [{ role: "user", content: "Hi" }],
 *   });
 *   console.log(r.choices[0].message.content);
 */

const DEFAULT_MODEL = "llama3.1-8B";

export class JimmyError extends Error {
  constructor(message, { status, body } = {}) {
    super(message);
    this.name = "JimmyError";
    this.status = status;
    this.body = body;
  }
}

class Completions {
  constructor(client) {
    this._client = client;
  }

  async create(opts = {}) {
    const {
      messages,
      model = this._client.defaultModel,
      stream = false,
      tools,
      tool_choice,
      response_format,
      top_k,
      system_prompt,
      ...rest
    } = opts;

    if (!messages?.length) throw new JimmyError("messages is required");

    const res = await fetch(this._client._url("/v1/chat/completions"), {
      method: "POST",
      headers: this._client._headers(),
      body: JSON.stringify({
        model,
        messages,
        stream,
        tools,
        tool_choice,
        response_format,
        top_k,
        system_prompt,
        ...rest,
      }),
    });

    if (stream) {
      if (!res.ok) {
        const t = await res.text().catch(() => "");
        throw new JimmyError(`Jimmy proxy error ${res.status}: ${t.slice(0, 200)}`, {
          status: res.status,
          body: t,
        });
      }
      return this._iterSSE(res);
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new JimmyError(data?.error?.message || `HTTP ${res.status}`, {
        status: res.status,
        body: data,
      });
    }
    return data;
  }

  /** Structured parse — pass OpenAI-style response_format (json_object / json_schema). */
  async parse(opts = {}) {
    if (!opts.response_format) throw new JimmyError("parse() requires response_format");
    return this.create({ ...opts, stream: false });
  }

  async *_iterSSE(res) {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n");
      buf = parts.pop() || "";
      for (const line of parts) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data:")) continue;
        const payload = trimmed.slice(5).trim();
        if (payload === "[DONE]") return;
        try {
          yield JSON.parse(payload);
        } catch {
          /* ignore */
        }
      }
    }
  }
}

class Chat {
  constructor(client) {
    this.completions = new Completions(client);
  }
}

class Models {
  constructor(client) {
    this._client = client;
  }
  async list() {
    const res = await fetch(this._client._url("/v1/models"), {
      headers: this._client._headers(),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new JimmyError(data?.error?.message || `HTTP ${res.status}`, {
        status: res.status,
        body: data,
      });
    }
    return data;
  }
}

export class Jimmy {
  /**
   * @param {object} [opts]
   * @param {string} opts.baseURL  Your Worker URL (NOT chatjimmy.ai — CORS blocked)
   * @param {string} [opts.apiKey]
   * @param {string} [opts.defaultModel]
   */
  constructor(opts = {}) {
    this.baseURL = String(opts.baseURL || opts.baseUrl || "").replace(/\/+$/, "");
    this.apiKey = opts.apiKey || opts.api_key || null;
    this.defaultModel = opts.defaultModel || DEFAULT_MODEL;
    this.defaultHeaders = opts.defaultHeaders || {};

    if (!this.baseURL) {
      console.warn(
        "[Jimmy] No baseURL. Direct browser calls to chatjimmy.ai are blocked by CORS. " +
          "Deploy singlefile/jimmy-worker.js and pass its URL."
      );
    } else if (/chatjimmy\.ai/i.test(this.baseURL)) {
      console.warn(
        "[Jimmy] baseURL points at chatjimmy.ai — browsers will block this. Use your Worker URL."
      );
    }

    this.chat = new Chat(this);
    this.models = new Models(this);
  }

  _url(path) {
    if (!this.baseURL) {
      throw new JimmyError(
        "Jimmy baseURL is required in the browser. Deploy jimmy-worker.js and pass its URL."
      );
    }
    return `${this.baseURL}${path}`;
  }

  _headers() {
    const h = {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...this.defaultHeaders,
    };
    if (this.apiKey) h.Authorization = `Bearer ${this.apiKey}`;
    return h;
  }

  async ping() {
    const t0 = performance.now();
    await this.chat.completions.create({
      model: this.defaultModel,
      messages: [{ role: "user", content: "Reply with exactly: PONG" }],
    });
    return performance.now() - t0;
  }
}

/** Drop-in alias */
export const OpenAI = Jimmy;
