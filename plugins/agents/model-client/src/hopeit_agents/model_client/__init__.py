"""Public API for the hopeit_agents model client plugin."""

from hopeit_agents.model_client.api.generate import generate
from hopeit_agents.model_client.client import AsyncModelClient, ModelClientError
from hopeit_agents.model_client.conversation import build_conversation
from hopeit_agents.model_client.models import (
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
from hopeit_agents.model_client.settings import ModelClientSettings, merge_config

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
