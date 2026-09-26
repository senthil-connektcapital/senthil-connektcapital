# Deploy jimmy-proxy (Docker)

OpenAI-compatible proxy for chatjimmy.ai. Adds CORS headers so browsers can call it.

## Pull & run

```bash
docker pull ghcr.io/senthil-connektcapital/jimmy-proxy:latest
docker run --rm -p 8787:8787 ghcr.io/senthil-connektcapital/jimmy-proxy:latest
```

Verify:

```bash
curl http://localhost:8787/health
# {"ok": true, "proxy": "chatjimmy.ai", "model": "llama3.1-8B"}
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8787` | Listen port |

Example — custom port:

```bash
docker run --rm -p 8080:8080 -e PORT=8080 ghcr.io/senthil-connektcapital/jimmy-proxy:latest
```

## Build locally

```bash
git clone https://github.com/senthil-connektcapital/senthil-connektcapital.git
cd senthil-connektcapital
docker build -t jimmy-proxy .
docker run --rm -p 8787:8787 jimmy-proxy
```

## Docker Compose

```yaml
services:
  jimmy-proxy:
    image: ghcr.io/senthil-connektcapital/jimmy-proxy:latest
    ports:
      - "8787:8787"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/health', timeout=3)"]
      interval: 30s
      timeout: 5s
      retries: 3
```

## Kubernetes (minimal)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jimmy-proxy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jimmy-proxy
  template:
    metadata:
      labels:
        app: jimmy-proxy
    spec:
      containers:
        - name: jimmy-proxy
          image: ghcr.io/senthil-connektcapital/jimmy-proxy:latest
          ports:
            - containerPort: 8787
          env:
            - name: PORT
              value: "8787"
          livenessProbe:
            httpGet:
              path: /health
              port: 8787
            initialDelaySeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: jimmy-proxy
spec:
  selector:
    app: jimmy-proxy
  ports:
    - port: 80
      targetPort: 8787
```

## Use from your app

Point any OpenAI-compatible client at your proxy base URL:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8787/v1",
    api_key="not-needed",  # chatjimmy has no key today
)
r = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[{"role": "user", "content": "Hi"}],
)
print(r.choices[0].message.content)
```

```javascript
const r = await fetch("http://localhost:8787/v1/chat/completions", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: "llama3.1-8B",
    messages: [{ role: "user", content: "Hi" }],
  }),
});
const data = await r.json();
console.log(data.choices[0].message.content);
```

## API reference

- Human-readable: [HTTP-API.md](./HTTP-API.md)
- Machine-readable: [openapi.yaml](../openapi.yaml)
- Live spec: `GET http://<host>:8787/openapi.yaml`

## CI / image updates

Images are built on push to `main` / `cursor/**` via `.github/workflows/docker-publish.yml`.

Tags: `latest`, branch name, git sha.

## Limitations (Docker proxy)

| Feature | Supported |
|---|---|
| Chat completions | ✅ |
| Models list | ✅ |
| Tool calling | ✅ |
| `response_format` (JSON) | ✅ |
| CORS for browsers | ✅ |
| `stream: true` (SSE) | ❌ use `singlefile/jimmy-worker.js` |
| API key auth | ❌ not implemented (add your own reverse proxy if needed) |
