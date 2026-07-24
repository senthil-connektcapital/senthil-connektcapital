# Single-file chatjimmy clients / proxies

## Does chatjimmy block CORS?

**Yes — for browsers.**

Probed `https://chatjimmy.ai/api/chat`:

- Request succeeds on the server (HTTP 200) from any `Origin`
- Response has **no** `Access-Control-Allow-Origin`
- OPTIONS preflight returns 204 with `Allow: OPTIONS, POST` but **no CORS allow headers**

So a pure client-side JS class that `fetch`es chatjimmy **from your website will fail** with a CORS error. Spoofing `Origin` / `Referer` only works from a **server** (Python, Go, Worker, Node) — browsers set those headers themselves and enforce CORS.

```
Browser ──X──> chatjimmy.ai/api/chat     ❌ CORS blocked
Browser ──✓──> your Worker/proxy ──✓──> chatjimmy.ai   ✅
```

Your original TS note was right: *“Server-side client — bypasses CORS entirely.”*

---

## Fastest thing to host: Cloudflare Worker (1 JS file)

File: [`jimmy-worker.js`](./jimmy-worker.js)

```bash
npx wrangler deploy singlefile/jimmy-worker.js \
  --name jimmy-proxy \
  --compatibility-date 2024-11-01
```

Or paste the file into the Cloudflare Workers dashboard → Deploy.

Gives you:

- `GET  /health`
- `GET  /v1/models`
- `POST /v1/chat/completions` (tools + `response_format` + SSE streaming)
- CORS `*` so **browsers can call the Worker**

Edge, free tier, no container, cold-start is tiny.

---

## Browser class (talks to your Worker, not chatjimmy)

File: [`jimmy-browser.js`](./jimmy-browser.js)

```html
<script type="module">
  import { Jimmy } from "./jimmy-browser.js";

  const client = new Jimmy({
    baseURL: "https://jimmy-proxy.<you>.workers.dev", // NOT chatjimmy.ai
  });

  const r = await client.chat.completions.create({
    model: "llama3.1-8B",
    messages: [{ role: "user", content: "Hi" }],
  });
  console.log(r.choices[0].message.content);
</script>
```

---

## Alternative: one Python file (stdlib only)

File: [`jimmy-proxy.py`](./jimmy-proxy.py)

```bash
python3 singlefile/jimmy-proxy.py   # http://0.0.0.0:8787
```

No pip. Good for localhost / a tiny VPS. Non-streaming (use the Worker for SSE).

---

## Can I skip the proxy entirely?

| Runtime | Direct to chatjimmy? |
|---|---|
| Browser JS on your site | ❌ CORS |
| Browser extension / Electron (no CORS) | ⚠️ possible, not recommended |
| Python / Go / Node / Cloudflare Worker | ✅ |

There is no safe pure-browser workaround without chatjimmy adding CORS headers (or you hosting a proxy).
