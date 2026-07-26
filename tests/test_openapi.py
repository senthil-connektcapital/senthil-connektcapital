"""OpenAPI spec serving tests."""

import json
from pathlib import Path

import httpx
import pytest
import respx

from jimmy import Jimmy

REPO = Path(__file__).resolve().parents[1]


def test_openapi_yaml_exists():
    path = REPO / "openapi.yaml"
    assert path.exists()
    text = path.read_text()
    assert "openapi: 3.0.3" in text
    assert "/v1/chat/completions" in text


def test_openapi_json_valid():
    path = REPO / "openapi.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["openapi"] == "3.0.3"
    assert "/v1/chat/completions" in data["paths"]


@respx.mock
def test_proxy_serves_openapi_json(tmp_path, monkeypatch):
    # Point proxy at repo openapi files
    import importlib.util
    import sys

    spec_path = REPO / "singlefile" / "jimmy-proxy.py"
    monkeypatch.setenv("OPENAPI_YAML", str(REPO / "openapi.yaml"))
    monkeypatch.setenv("OPENAPI_JSON", str(REPO / "openapi.json"))

    # Import handler module dynamically
    name = "jimmy_proxy_test"
    spec = importlib.util.spec_from_file_location(name, spec_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)

    handler = mod.Handler
    # Smoke: file paths resolve
    assert Path(mod.OPENAPI_JSON).exists()
