"""hopeit_agents MCP bridge plugin."""

from hopeit_agents.mcp_client.client import MCPClient, MCPClientError
from hopeit_agents.mcp_client.models import (
    BridgeConfig,
    ToolCallRecord,
    ToolCallRequestLog,
    ToolDescriptor,
    ToolExecutionResult,
    ToolExecutionStatus,
    ToolInvocation,
)

__all__ = [
    "BridgeConfig",
    "MCPClient",
    "MCPClientError",
    "ToolCallRecord",
    "ToolCallRequestLog",
    "ToolDescriptor",
    "ToolExecutionResult",
    "ToolExecutionStatus",
    "ToolInvocation",
]
