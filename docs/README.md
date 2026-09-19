# Documentation

| Doc | What it covers |
|---|---|
| [DEPLOY.md](./DEPLOY.md) | Docker image, env vars, deployment |
| [HTTP-API.md](./HTTP-API.md) | REST API usage (`curl`, JS, Python) |
| [../SDK.md](../SDK.md) | Python `jimmy` library (pip install) |
| [../openapi.yaml](../openapi.yaml) | **OpenAPI 3.0** specification |
| [../tests/test_sample_usage.py](../tests/test_sample_usage.py) | Runnable Python examples |

## Quick links

- **Docker image:** `ghcr.io/senthil-connektcapital/jimmy-proxy:latest`
- **OpenAPI (live):** `GET /openapi.yaml` or `GET /openapi.json` on your running proxy
- **Health:** `GET /health`
- **Chat:** `POST /v1/chat/completions`
- **Models:** `GET /v1/models`

## OpenAPI tools

Import `openapi.yaml` into:

- [Swagger Editor](https://editor.swagger.io/)
- Postman (Import → OpenAPI 3.0)
- Insomnia
- `openapi-generator` for client SDKs

```bash
# View spec from a running container
curl http://localhost:8787/openapi.yaml
curl http://localhost:8787/openapi.json
```
