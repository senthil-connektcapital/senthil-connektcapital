"""Jimmy / OpenAI-compatible client entrypoints."""

from __future__ import annotations

from typing import Mapping, Optional

import httpx

from ._http import (
    DEFAULT_BASE_URL,
    DEFAULT_CHAT_PATH,
    DEFAULT_HEADERS,
    DEFAULT_MODELS_PATH,
    merge_headers,
)
from .chat import AsyncChat, Chat
from .models import AsyncModels, Models


class Jimmy:
    """
    Sync OpenAI-style client for chatjimmy.ai.

        from jimmy import Jimmy
        client = Jimmy()
        r = client.chat.completions.create(
            model="llama3.1-8B",
            messages=[{"role": "user", "content": "Hi"}],
        )
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        default_headers: Optional[Mapping[str, str]] = None,
        timeout: float = 120.0,
        default_model: str = "llama3.1-8B",
        top_k: int = 8,
        http_client: Optional[httpx.Client] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.top_k = top_k
        self._default_headers = dict(default_headers or {})
        self._owns_http = http_client is None
        self._http = http_client or httpx.Client(timeout=timeout, follow_redirects=True)

        self.chat = Chat(self)
        self.models = Models(self)

    def _headers(self) -> dict:
        headers = merge_headers(DEFAULT_HEADERS, self._default_headers)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _chat_url(self) -> str:
        return f"{self.base_url}{DEFAULT_CHAT_PATH}"

    def _models_url(self) -> str:
        return f"{self.base_url}{DEFAULT_MODELS_PATH}"

    def ping(self) -> float:
        """Round-trip latency in milliseconds for a tiny chat call."""
        import time

        t0 = time.time()
        self.chat.completions.create(
            model=self.default_model,
            messages=[{"role": "user", "content": "Reply with exactly: PONG"}],
        )
        return (time.time() - t0) * 1000.0

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> "Jimmy":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class AsyncJimmy:
    """Async OpenAI-style client for chatjimmy.ai."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        default_headers: Optional[Mapping[str, str]] = None,
        timeout: float = 120.0,
        default_model: str = "llama3.1-8B",
        top_k: int = 8,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.top_k = top_k
        self._default_headers = dict(default_headers or {})
        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=timeout, follow_redirects=True)

        self.chat = AsyncChat(self)
        self.models = AsyncModels(self)

    def _headers(self) -> dict:
        headers = merge_headers(DEFAULT_HEADERS, self._default_headers)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _chat_url(self) -> str:
        return f"{self.base_url}{DEFAULT_CHAT_PATH}"

    def _models_url(self) -> str:
        return f"{self.base_url}{DEFAULT_MODELS_PATH}"

    async def ping(self) -> float:
        import time

        t0 = time.time()
        await self.chat.completions.create(
            model=self.default_model,
            messages=[{"role": "user", "content": "Reply with exactly: PONG"}],
        )
        return (time.time() - t0) * 1000.0

    async def close(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> "AsyncJimmy":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


# Drop-in alias for OpenAI SDK familiarity
OpenAI = Jimmy
AsyncOpenAI = AsyncJimmy
