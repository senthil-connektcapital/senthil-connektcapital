"""Structured outputs: response_format + Pydantic parse (OpenAI-compatible)."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError, create_model

from .exceptions import APIError

T = TypeVar("T", bound=BaseModel)

ResponseFormat = Union[Dict[str, Any], Type[BaseModel]]

JSON_OBJECT_INSTRUCTION = """You must respond with a single valid JSON object only.
Do not wrap it in markdown fences. Do not include any prose before or after the JSON."""

JSON_SCHEMA_INSTRUCTION = """You must respond with a single valid JSON value that conforms to this JSON Schema.
Do not wrap it in markdown fences. Do not include any prose before or after the JSON.

JSON Schema ({name}):
{schema_json}
"""

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


class LengthFinishReasonError(APIError):
    """Raised when structured parse fails because the model hit a length stop."""


class ContentFilterFinishReasonError(APIError):
    """Raised when structured parse fails because of a content filter stop."""


def is_pydantic_model(obj: Any) -> bool:
    return isinstance(obj, type) and issubclass(obj, BaseModel)


def normalize_response_format(
    response_format: Optional[ResponseFormat],
) -> tuple[Optional[Dict[str, Any]], Optional[Type[BaseModel]]]:
    """
    Returns (openai_style_dict, pydantic_model).

    Accepts:
      - {"type": "json_object"}
      - {"type": "json_schema", "json_schema": {"name": "...", "schema": {...}, "strict": bool}}
      - a Pydantic BaseModel subclass (converted to json_schema format)
    """
    if response_format is None:
        return None, None

    if is_pydantic_model(response_format):
        model: Type[BaseModel] = response_format  # type: ignore[assignment]
        schema = model.model_json_schema()
        fmt = {
            "type": "json_schema",
            "json_schema": {
                "name": model.__name__,
                "schema": schema,
                "strict": True,
            },
        }
        return fmt, model

    if not isinstance(response_format, dict):
        raise APIError(f"Unsupported response_format: {response_format!r}")

    fmt_type = response_format.get("type")
    if fmt_type == "text":
        return None, None
    if fmt_type == "json_object":
        return {"type": "json_object"}, None
    if fmt_type == "json_schema":
        js = response_format.get("json_schema") or {}
        if not isinstance(js, dict) or "schema" not in js:
            raise APIError("response_format.json_schema.schema is required")
        return {
            "type": "json_schema",
            "json_schema": {
                "name": js.get("name") or "response",
                "schema": js["schema"],
                "strict": bool(js.get("strict", False)),
            },
        }, None

    raise APIError(
        "response_format.type must be one of: text, json_object, json_schema "
        f"(got {fmt_type!r})"
    )


def build_structured_system_prompt(fmt: Dict[str, Any]) -> str:
    if fmt["type"] == "json_object":
        return JSON_OBJECT_INSTRUCTION
    js = fmt["json_schema"]
    return JSON_SCHEMA_INSTRUCTION.format(
        name=js.get("name") or "response",
        schema_json=json.dumps(js["schema"], indent=2),
    )


def extract_json_value(text: str) -> Any:
    """Pull the first JSON value out of model text (fences / surrounding prose OK)."""
    if text is None:
        raise APIError("Empty response; expected JSON")
    raw = text.strip()
    if not raw:
        raise APIError("Empty response; expected JSON")

    fence = _CODE_FENCE_RE.search(raw)
    if fence:
        raw = fence.group(1).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Find first JSON object or array
    for opener, closer in (("{", "}"), ("[", "]")):
        start = raw.find(opener)
        if start < 0:
            continue
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(raw)):
            ch = raw[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    candidate = raw[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break
        # try next shape

    raise APIError(f"Could not parse JSON from model response: {text[:200]!r}")


def _check_type(value: Any, expected: Union[str, List[str]], path: str) -> None:
    mapping = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "null": type(None),
    }
    types = [expected] if isinstance(expected, str) else list(expected)
    if "number" in types and "integer" not in types:
        # integers are valid numbers
        types.append("integer")
    ok = False
    for t in types:
        py = mapping.get(t)
        if py is None:
            continue
        if t == "integer" and isinstance(value, bool):
            continue
        if isinstance(value, py):
            # bool is subclass of int — disallow for integer/number unless boolean allowed
            if t in ("integer", "number") and isinstance(value, bool) and "boolean" not in types:
                continue
            ok = True
            break
    if not ok:
        raise APIError(f"Schema validation failed at {path}: expected {expected}, got {type(value).__name__}")


def validate_json_schema(value: Any, schema: Dict[str, Any], path: str = "$") -> Any:
    """Lightweight JSON Schema subset validator (no extra dependency)."""
    if not isinstance(schema, dict):
        return value

    if "const" in schema and value != schema["const"]:
        raise APIError(f"Schema validation failed at {path}: expected const {schema['const']!r}")

    if "enum" in schema and value not in schema["enum"]:
        raise APIError(f"Schema validation failed at {path}: value not in enum")

    if "type" in schema:
        _check_type(value, schema["type"], path)

    if isinstance(value, dict):
        props = schema.get("properties") or {}
        required = schema.get("required") or []
        for key in required:
            if key not in value:
                raise APIError(f"Schema validation failed at {path}: missing required property {key!r}")
        additional = schema.get("additionalProperties", True)
        for key, child in value.items():
            if key in props:
                validate_json_schema(child, props[key], f"{path}.{key}")
            elif additional is False:
                raise APIError(f"Schema validation failed at {path}: unexpected property {key!r}")
            elif isinstance(additional, dict):
                validate_json_schema(child, additional, f"{path}.{key}")

    if isinstance(value, list) and "items" in schema:
        item_schema = schema["items"]
        if isinstance(item_schema, dict):
            for idx, item in enumerate(value):
                validate_json_schema(item, item_schema, f"{path}[{idx}]")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise APIError(f"Schema validation failed at {path}: string shorter than minLength")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise APIError(f"Schema validation failed at {path}: string longer than maxLength")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise APIError(f"Schema validation failed at {path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise APIError(f"Schema validation failed at {path}: above maximum")

    if "anyOf" in schema:
        errors = []
        for option in schema["anyOf"]:
            try:
                return validate_json_schema(value, option, path)
            except APIError as exc:
                errors.append(str(exc))
        raise APIError(f"Schema validation failed at {path}: no anyOf matched ({'; '.join(errors)})")

    return value


def schema_to_pydantic_model(name: str, schema: Dict[str, Any]) -> Type[BaseModel]:
    """Best-effort: build a pydantic model from a simple object JSON schema."""
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    fields: Dict[str, Any] = {}

    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "object": dict,
        "array": list,
    }

    for key, prop in props.items():
        typ: Any = Any
        if isinstance(prop, dict):
            t = prop.get("type")
            if isinstance(t, str) and t in type_map:
                typ = type_map[t]
                if t == "array" and isinstance(prop.get("items"), dict):
                    item_t = prop["items"].get("type")
                    if isinstance(item_t, str) and item_t in type_map:
                        typ = List[type_map[item_t]]  # type: ignore[valid-type]
        if key in required:
            fields[key] = (typ, ...)
        else:
            fields[key] = (Optional[typ], None)

    safe_name = re.sub(r"[^0-9a-zA-Z_]", "_", name) or "StructuredResponse"
    if safe_name[0].isdigit():
        safe_name = f"Model_{safe_name}"
    return create_model(safe_name, **fields)  # type: ignore[call-overload]


def parse_structured_content(
    text: str,
    *,
    fmt: Optional[Dict[str, Any]],
    pydantic_model: Optional[Type[BaseModel]] = None,
    strict: bool = True,
) -> tuple[str, Any]:
    """
    Returns (content_json_string, parsed_object).
    parsed_object is a BaseModel instance when pydantic_model is set, else a dict/list.
    """
    if fmt is None and pydantic_model is None:
        return text, None

    data = extract_json_value(text)

    if pydantic_model is not None:
        try:
            parsed = pydantic_model.model_validate(data)
        except ValidationError as exc:
            raise APIError(f"Structured output failed Pydantic validation: {exc}") from exc
        content = parsed.model_dump_json()
        return content, parsed

    assert fmt is not None
    if fmt["type"] == "json_object":
        if not isinstance(data, dict):
            raise APIError("json_object response_format requires a JSON object")
        return json.dumps(data), data

    # json_schema
    js = fmt["json_schema"]
    schema = js["schema"]
    do_strict = strict if strict is not None else bool(js.get("strict", False))
    if do_strict or js.get("strict"):
        validate_json_schema(data, schema)
        # Prefer pydantic instance when schema is object-shaped
        if isinstance(data, dict) and (schema.get("type") == "object" or "properties" in schema):
            try:
                model = schema_to_pydantic_model(js.get("name") or "Response", schema)
                parsed_model = model.model_validate(data)
                return json.dumps(data), parsed_model
            except Exception:
                return json.dumps(data), data
    return json.dumps(data), data
