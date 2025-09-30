"""Utilities to help agents describe and invoke MCP tools."""

from __future__ import annotations

import json
import uuid
from typing import Any

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit_agents.mcp_client.client import MCPClient, MCPClientError
from hopeit_agents.mcp_client.models import (
    MCPClientConfig,
    ToolCallRecord,
    ToolCallRequestLog,
    ToolDescriptor,
    ToolExecutionResult,
    ToolInvocation,
)
from hopeit_agents.mcp_client.settings import build_environment

logger, extra = app_extra_logger()

__all__ = [
    "resolve_tools",
    "tool_descriptions",
    "call_tool",
    "execute_tool_calls",
]


async def resolve_tools(
    config: MCPClientConfig,
    context: EventContext,
    *,
    agent_id: str,
    allowed_tools: list[str] | None = None,
) -> list[ToolDescriptor]:
    """Return a tool-aware prompt based on the MCP tool inventory."""
    env = build_environment(config, context.env)
    client = MCPClient(config=config, env=env)
    try:
        tools = await client.list_tools()
        if allowed_tools:
            return [tool for tool in tools if tool.name in allowed_tools]
        return tools
    except MCPClientError as exc:
        logger.warning(
            context,
            "agent_tool_prompt_list_failed",
            extra=extra(agent_id=agent_id, error=str(exc), details=exc.details),
        )
        return []
    except Exception as exc:  # pragma: no cover - defensive guardrail
        logger.error(
            context,
            "agent_tool_prompt_unexpected_error",
            extra=extra(agent_id=agent_id, error=repr(exc)),
        )
        return []


def tool_descriptions(
    tools: list[ToolDescriptor],
    *,
    include_schemas: bool,
) -> str:
    """Render tool metadata as bullet points for LLM consumption."""
    lines: list[str] = []
    lines.append("\nAvailable tools:")
    for tool in tools:
        description = (tool.description or "No description provided.").strip()
        lines.append(f"- {tool.name}: {description}")
        if include_schemas and tool.input_schema:
            schema = json.dumps(tool.input_schema, indent=2, sort_keys=True)
            lines.append("  JSON schema:")
            lines.extend(f"    {schema_line}" for schema_line in schema.splitlines())
    return "\n".join(lines).strip()


async def call_tool(
    config: MCPClientConfig,
    context: EventContext,
    *,
    call_id: str,
    tool_name: str,
    payload: dict[str, Any],
    session_id: str | None = None,
) -> ToolExecutionResult:
    """Execute an MCP tool through the client using the provided payload."""
    env = build_environment(config, context.env)
    client = MCPClient(config=config, env=env)
    args = ToolInvocation(
        call_id=call_id,
        tool_name=tool_name,
        payload=payload,
        session_id=session_id,
    )
    try:
        return await client.call_tool(
            args.tool_name, args.payload, call_id=args.call_id, session_id=args.session_id
        )
    except MCPClientError as exc:
        logger.error(
            context,
            "mcp_invoke_tool_error",
            extra=extra(tool_name=args.tool_name, details=exc.details),
        )
        raise


async def execute_tool_calls(
    config: MCPClientConfig,
    context: EventContext,
    *,
    tool_calls: list[ToolInvocation],
    session_id: str | None = None,
) -> list[ToolCallRecord]:
    """Execute multiple tool calls capturing request and response data."""
    records: list[ToolCallRecord] = []
    for tool_call in tool_calls:
        result = await call_tool(
            config,
            context,
            call_id=tool_call.call_id or f"call_{uuid.uuid4().hex[-10:]}",
            tool_name=tool_call.tool_name,
            payload=tool_call.payload,
            session_id=session_id,
        )
        request_log = ToolCallRequestLog(
            tool_call_id=result.call_id,
            tool_name=tool_call.tool_name,
            payload=tool_call.payload,
        )
        records.append(ToolCallRecord(request=request_log, response=result))
    return records
