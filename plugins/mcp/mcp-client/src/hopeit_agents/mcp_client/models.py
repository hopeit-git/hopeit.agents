"""Typed data objects for the MCP bridge plugin."""

from enum import Enum
from typing import Any

from hopeit.dataobjects import dataclass, dataobject, field


class Transport(str, Enum):
    """Supported MCP transport mechanisms."""

    STDIO = "stdio"
    HTTP = "http"


class ToolExecutionStatus(str, Enum):
    """Outcome of a tool invocation."""

    SUCCESS = "success"
    ERROR = "error"


@dataobject
@dataclass
class ToolAnnotations:
    """
    Additional properties describing a Tool to clients.

    NOTE: all properties in ToolAnnotations are **hints**.
    They are not guaranteed to provide a faithful description of
    tool behavior (including descriptive properties like `title`).

    Clients should never make tool use decisions based on ToolAnnotations
    received from untrusted servers.
    """

    title: str | None = None
    """A human-readable title for the tool."""

    readOnlyHint: bool | None = None
    """
    If true, the tool does not modify its environment.
    Default: false
    """

    destructiveHint: bool | None = None
    """
    If true, the tool may perform destructive updates to its environment.
    If false, the tool performs only additive updates.
    (This property is meaningful only when `readOnlyHint == false`)
    Default: true
    """

    idempotentHint: bool | None = None
    """
    If true, calling the tool repeatedly with the same arguments
    will have no additional effect on the its environment.
    (This property is meaningful only when `readOnlyHint == false`)
    Default: false
    """

    openWorldHint: bool | None = None
    """
    If true, this tool may interact with an "open world" of external
    entities. If false, the tool's domain of interaction is closed.
    For example, the world of a web search tool is open, whereas that
    of a memory tool is not.
    Default: true
    """


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
    annotations: ToolAnnotations | None = None
    """Optional additional tool information."""
    meta: dict[str, Any] | None = field(alias="_meta", default=None)
    """
    See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
    for notes on _meta usage.
    """


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
class BridgeConfig:
    """Configuration required to communicate with an MCP server."""

    command: str | None = None
    args: list[str] = field(default_factory=list)
    transport: Transport = Transport.STDIO
    url: str | None = None
    host: str | None = None
    port: int | None = None
    env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None
    tool_cache_seconds: float = 30.0
    list_timeout_seconds: float = 10.0
    call_timeout_seconds: float = 60.0

    def transport_enum(self) -> Transport:
        """Return the transport as enum."""
        if isinstance(self.transport, Transport):
            return self.transport

        value = str(self.transport)
        if value == "tcp":  # Backwards compatibility for previous configs
            value = Transport.HTTP.value

        return Transport(value)
