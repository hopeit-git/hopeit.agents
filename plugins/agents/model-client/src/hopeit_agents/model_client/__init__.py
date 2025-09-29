"""Public API for the hopeit_agents model client plugin."""

from .api.generate import generate
from .client import AsyncModelClient, ModelClientError
from .conversation import build_conversation
from .models import (
    CompletionConfig,
    CompletionRequest,
    CompletionResponse,
    Conversation,
    Message,
    Role,
    ToolCall,
    ToolFunctionCall,
    ToolResult,
    ToolSpec,
    Usage,
)
from .settings import ModelClientSettings, merge_config

__all__ = [
    "AsyncModelClient",
    "CompletionConfig",
    "CompletionRequest",
    "CompletionResponse",
    "Conversation",
    "Message",
    "ModelClientError",
    "ModelClientSettings",
    "Role",
    "ToolCall",
    "ToolFunctionCall",
    "ToolResult",
    "ToolSpec",
    "Usage",
    "build_conversation",
    "generate",
    "merge_config",
]
