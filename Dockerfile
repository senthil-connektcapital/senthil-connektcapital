# Jimmy OpenAI-compatible proxy for chatjimmy.ai
# Build: docker build -t jimmy-proxy .
# Run:   docker run --rm -p 8787:8787 jimmy-proxy

FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="jimmy-proxy" \
      org.opencontainers.image.description="OpenAI-shaped CORS proxy for chatjimmy.ai (Llama 3.1)" \
      org.opencontainers.image.source="https://github.com/senthil-connektcapital/senthil-connektcapital"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8787

WORKDIR /app

RUN groupadd --system jimmy && useradd --system --gid jimmy jimmy

COPY singlefile/jimmy-proxy.py /app/jimmy-proxy.py
COPY openapi.yaml /app/openapi.yaml
COPY openapi.json /app/openapi.json

RUN chown -R jimmy:jimmy /app

USER jimmy

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/health', timeout=3)" || exit 1

CMD ["python", "/app/jimmy-proxy.py"]
