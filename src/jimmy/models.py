"""Models resource (OpenAI-compatible)."""

from __future__ import annotations

from typing import Any

import httpx

from ._http import raise_for_status, wrap_request_error
from .types import Model, ModelList


class Models:
    def __init__(self, client: Any):
        self._client = client

    def list(self) -> ModelList:
        url = self._client._models_url()
        try:
            response = self._client._http.get(url, headers=self._client._headers())
            raise_for_status(response)
        except httpx.HTTPError as exc:
            raise wrap_request_error(exc) from exc

        data = response.json()
        # Already OpenAI-shaped from chatjimmy
        if isinstance(data, dict) and "data" in data:
            return ModelList.model_validate(data)
        if isinstance(data, list):
            return ModelList(data=[Model.model_validate(m) for m in data])
        return ModelList(data=[Model(id="llama3.1-8B", owned_by="Taalas Inc.")])

    def retrieve(self, model: str) -> Model:
        for m in self.list().data:
            if m.id == model:
                return m
        return Model(id=model, owned_by="jimmy")


class AsyncModels:
    def __init__(self, client: Any):
        self._client = client

    async def list(self) -> ModelList:
        url = self._client._models_url()
        try:
            response = await self._client._http.get(url, headers=self._client._headers())
            raise_for_status(response)
        except httpx.HTTPError as exc:
            raise wrap_request_error(exc) from exc

        data = response.json()
        if isinstance(data, dict) and "data" in data:
            return ModelList.model_validate(data)
        if isinstance(data, list):
            return ModelList(data=[Model.model_validate(m) for m in data])
        return ModelList(data=[Model(id="llama3.1-8B", owned_by="Taalas Inc.")])

    async def retrieve(self, model: str) -> Model:
        for m in (await self.list()).data:
            if m.id == model:
                return m
        return Model(id=model, owned_by="jimmy")
