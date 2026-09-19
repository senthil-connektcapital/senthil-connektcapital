"""OpenAI-compatible response / request types."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class Function(BaseModel):
    name: str
    arguments: str  # JSON string, OpenAI-compatible


class ToolCall(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: Function


class ChatCompletionMessage(BaseModel):
    role: Literal["assistant", "user", "system", "tool"]
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    # OpenAI structured outputs / .parse() — BaseModel instance or dict
    parsed: Optional[Any] = None
    refusal: Optional[str] = None


class Choice(BaseModel):
    index: int = 0
    message: ChatCompletionMessage
    finish_reason: Optional[Literal["stop", "tool_calls", "length", "content_filter"]] = "stop"
    logprobs: Optional[Any] = None


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletion(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Optional[Usage] = None
    system_fingerprint: Optional[str] = None
    # Jimmy extras
    jimmy_stats: Optional[Dict[str, Any]] = None
    jimmy_raw: Optional[str] = None

    @property
    def output_text(self) -> str:
        if not self.choices:
            return ""
        return self.choices[0].message.content or ""


class Delta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChunkChoice(BaseModel):
    index: int = 0
    delta: Delta
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChunkChoice]


class Model(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int = 0
    owned_by: str = "jimmy"


class ModelList(BaseModel):
    object: Literal["list"] = "list"
    data: List[Model]


# Loose typing helpers for callers
MessageDict = Dict[str, Any]
ToolDict = Dict[str, Any]
ToolChoice = Union[Literal["none", "auto", "required"], Dict[str, Any]]
ResponseFormatDict = Dict[str, Any]


class JimmyChatOptions(BaseModel):
    model_config = ConfigDict(extra="ignore")

    selected_model: str = Field(default="llama3.1-8B", alias="selectedModel")
    system_prompt: str = Field(default="", alias="systemPrompt")
    top_k: int = Field(default=8, alias="topK")
