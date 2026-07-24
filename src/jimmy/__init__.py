"""OpenAI SDK-compatible client for chatjimmy.ai."""

from .client import AsyncJimmy, AsyncOpenAI, Jimmy, OpenAI
from .exceptions import APIConnectionError, APIError, APIStatusError, JimmyError
from .types import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessage,
    Choice,
    Function,
    Model,
    ModelList,
    ToolCall,
    Usage,
)

__all__ = [
    "Jimmy",
    "AsyncJimmy",
    "OpenAI",
    "AsyncOpenAI",
    "JimmyError",
    "APIError",
    "APIStatusError",
    "APIConnectionError",
    "ChatCompletion",
    "ChatCompletionChunk",
    "ChatCompletionMessage",
    "Choice",
    "Function",
    "Model",
    "ModelList",
    "ToolCall",
    "Usage",
]

__version__ = "0.2.0"
