"""Typed data objects used by the model client plugin."""

import json
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from hopeit.dataobjects import dataclass, dataobject, field
from hopeit.dataobjects.payload import Payload
from hopeit.server.names import spinalcase

from hopeit_agents.mcp_client.models import ToolDescriptor


class Role(str, Enum):
    """Supported message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataobject
@dataclass
class ToolSpec:
    """Available tool specification."""

    tool_name: str
    schema: dict[str, Any]


@dataobject
@dataclass
class ToolFunctionCall:
    """Function payload included in a tool call."""

    name: str
    arguments: str


@dataobject
@dataclass
class ToolCall:
    """Represents a tool call issued by the assistant."""

    id: str
    type: str
    function: ToolFunctionCall


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
    content: str | None
    tool_call_id: str | None = None
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> "Message":
        """Return a placeholder system message used for initialisation."""
        return cls(role=Role.SYSTEM, content="")


@dataobject
@dataclass
class Conversation:
    """Ordered list of messages forming the conversation context."""

    conversation_id: str
    messages: list[Message]
    session_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def with_message(self, message: Message) -> "Conversation":
        """Return a new conversation with an additional message."""
        return Conversation(
            conversation_id=self.conversation_id,
            messages=[*self.messages, message],
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
    available_tools: list[ToolDescriptor] | None = None


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
    return Payload.to_obj(message, exclude_none=True)  # type: ignore[return-value]


def messages_from_tool_calls(tool_calls: list[ToolCall]) -> list[Message]:
    """Represent tool calls as assistant messages for conversation continuity."""
    return [
        Message(
            role=Role.ASSISTANT,
            content="",
            tool_calls=tool_calls,
        )
        # for t in tool_calls
    ]


def tool_call_from_openai_dict(
    tool: dict[str, Any], available_tools: list[ToolDescriptor] | None = None
) -> ToolCall:
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

    tool_name = _resolve_tool_name(
        str(tool.get("function", {}).get("name", "")), parsed_args, available_tools or []
    )
    tool_name, arguments = _resolve_arguments(tool_name, parsed_args, available_tools or [])

    return ToolCall(
        id=f"call_{uuid.uuid4().hex[-10:]}",
        type="function",
        function=ToolFunctionCall(
            name=tool_name,
            arguments=Payload.to_json(arguments),
        ),
    )


def _resolve_tool_name(
    extracted_name: str, parsed_args: dict[str, Any], available_tools: list[ToolDescriptor]
) -> str:
    """Resolve the best matching tool name using extracted data and known descriptors."""
    tool_names = {t.name for t in available_tools}
    # Resolve tool name
    if spinalcase(extracted_name) not in tool_names:
        for t in available_tools:
            if t.name in spinalcase(extracted_name):
                return t.name
            for k, v in parsed_args.items():
                if t.name in spinalcase(str(k)) or t.name in spinalcase(str(v)):
                    return t.name
    return spinalcase(extracted_name)


def _resolve_arguments(
    tool_name: str, parsed_args: dict[str, Any], available_tools: list[ToolDescriptor]
) -> tuple[str, dict[str, Any]]:
    """Normalize arguments to match the resolved tool schema when possible."""
    for t in available_tools:
        if tool_name == t.name:
            if parsed_args.keys() == t.input_schema["properties"].keys():
                return t.name, parsed_args
            for _k, v in parsed_args.items():
                if isinstance(v, dict) and v.keys() == t.input_schema["properties"].keys():
                    return t.name, v
    for t in available_tools:
        if parsed_args.keys() == t.input_schema["properties"].keys():
            return t.name, parsed_args
        for _k, v in parsed_args.items():
            if isinstance(v, dict) and v.keys() == t.input_schema["properties"].keys():
                return t.name, v
    return tool_name, parsed_args


def message_from_openai_dict(data: dict[str, Any]) -> Message:
    """Convert an OpenAI-compatible message dict into a Message object."""
    role = Role(data.get("role", Role.ASSISTANT.value))
    content = data.get("content", "")
    tool_call_id = data.get("tool_call_id")
    metadata_raw = data.get("metadata")
    metadata = metadata_raw if isinstance(metadata_raw, dict) else {}
    return Message(role=role, content=content, tool_call_id=tool_call_id, metadata=metadata)
