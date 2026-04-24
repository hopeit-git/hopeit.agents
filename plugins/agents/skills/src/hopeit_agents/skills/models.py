"""Typed data objects for the MCP client plugin."""

from enum import StrEnum
from typing import Any

from hopeit.dataobjects import dataclass, dataobject, field


class ToolExecutionStatus(StrEnum):
    """Outcome of a tool invocation."""

    SUCCESS = "success"
    ERROR = "error"


@dataobject
@dataclass
class ToolDescriptor:
    """Definition for a tool the client can call."""

    name: str
    """The programmatic name of the entity."""
    title: str | None
    """Tool title."""
    description: str | None
    """A human-readable description of the tool."""
    input_schema: dict[str, Any]
    """A JSON Schema object defining the expected parameters for the tool."""
    output_schema: dict[str, Any] | None
    """
    An optional JSON Schema object defining the structure of the tool's output
    returned in the structuredContent field of a CallToolResult.
    """

    def to_openai_dict(self) -> dict[str, Any]:
        """
        Convert this ToolDescriptor to an OpenAI tool definition dictionary.
        """
        tool_def: dict[str, Any] = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description or "",
                "parameters": self.input_schema,
            },
        }
        if self.title:
            tool_def["function"]["title"] = self.title
        if self.output_schema is not None:
            tool_def["function"]["response"] = {
                "type": "json_schema",
                "json_schema": self.output_schema,
            }
        return tool_def


@dataobject
@dataclass
class ToolInvocation:
    """Payload to invoke a tool."""

    tool_name: str
    payload: dict[str, Any] = field(default_factory=dict)
    call_id: str | None = None
    session_id: str | None = None


@dataobject
@dataclass
class ToolExecutionResult:
    """Result of calling a tool through MCP."""

    call_id: str
    tool_name: str
    status: ToolExecutionStatus
    content: list[dict[str, Any]] = field(default_factory=list)
    structured_content: dict[str, Any] | list[Any] | None = None
    error_message: str | None = None
    raw_result: dict[str, Any] | None = None
    session_id: str | None = None


@dataobject
@dataclass
class ToolCallRequestLog:
    """Captured request details for a tool call."""

    tool_call_id: str
    tool_name: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataobject
@dataclass
class ToolCallRecord:
    """Aggregated tool call request and response for logging/telemetry."""

    request: ToolCallRequestLog
    response: ToolExecutionResult


@dataobject
@dataclass
class SkillsConfig:
    skills_generation_path: str = "./_skills"
