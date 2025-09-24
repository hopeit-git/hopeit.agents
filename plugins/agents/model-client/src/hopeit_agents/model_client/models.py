"""Typed data objects used by the model client plugin."""

import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from hopeit.dataobjects import dataclass, dataobject, field


class Role(str, Enum):
    """Supported message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataobject
@dataclass
class ToolCall:
    """Represents a tool call issued by the assistant."""

    call_id: str
    name: str
    arguments: dict[str, Any]


@dataobject
@dataclass
class ToolResult:
    """Represents the result of executing a tool call."""

    call_id: str
    output: dict[str, Any] | str
    is_error: bool = False
    error_message: str | None = None


@dataobject
@dataclass
class Message:
    """Single message within a conversation."""

    role: Role
    content: str
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataobject
@dataclass
class Conversation:
    """Ordered list of messages forming the conversation context."""

    messages: list[Message]
    agent_id: str | None = None
    session_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def with_message(self, message: Message) -> "Conversation":
        """Return a new conversation with an additional message."""
        return Conversation(
            messages=[*self.messages, message],
            agent_id=self.agent_id,
            session_id=self.session_id,
            created_at=self.created_at,
        )


@dataobject
@dataclass
class Usage:
    """Token usage details reported by the provider."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataobject
@dataclass
class CompletionConfig:
    """Configuration overrides for a completion request."""

    model: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    response_format: dict[str, Any] | None = None
    tool_choice: str | None = None
    enable_tool_expansion: bool | None = None


@dataobject
@dataclass
class CompletionRequest:
    """Input payload for the generate event."""

    conversation: Conversation
    config: CompletionConfig | None = None


@dataobject
@dataclass
class CompletionResponse:
    """Normalized completion response."""

    response_id: str
    model: str
    created_at: datetime
    message: Message
    tool_calls: list[ToolCall]
    conversation: Conversation
    usage: Usage | None = None
    finish_reason: str | None = None


def message_to_openai_dict(message: Message) -> dict[str, Any]:
    """Convert a Message into the OpenAI-compatible dict structure."""
    result: dict[str, Any] = {
        "role": message.role.value,
        "content": message.content,
    }
    if message.tool_call_id is not None:
        result["tool_call_id"] = message.tool_call_id
    if message.metadata:
        result["metadata"] = message.metadata
    return result


def tool_call_from_openai_dict(tool: dict[str, Any]) -> ToolCall:
    """Create a ToolCall from a dict returned by OpenAI-compatible APIs."""
    arguments_data = tool.get("function", {}).get("arguments")
    parsed_args: dict[str, Any]
    if isinstance(arguments_data, str):
        try:
            parsed_args = json.loads(arguments_data)
        except json.JSONDecodeError:
            parsed_args = {"raw": arguments_data}
    elif isinstance(arguments_data, dict):
        parsed_args = arguments_data
    else:
        parsed_args = {"raw": arguments_data}
    return ToolCall(
        call_id=str(tool.get("id", "")),
        name=str(tool.get("function", {}).get("name", "")),
        arguments=parsed_args,
    )


def message_from_openai_dict(data: dict[str, Any]) -> Message:
    """Convert an OpenAI-compatible message dict into a Message object."""
    role = Role(data.get("role", Role.ASSISTANT.value))
    content = data.get("content", "")
    tool_call_id = data.get("tool_call_id")
    metadata_raw = data.get("metadata")
    metadata = metadata_raw if isinstance(metadata_raw, dict) else {}
    return Message(role=role, content=content, tool_call_id=tool_call_id, metadata=metadata)
