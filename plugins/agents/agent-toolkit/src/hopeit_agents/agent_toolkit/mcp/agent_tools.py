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
    "resolve_tool_prompt",
    "build_tool_prompt",
    "format_tool_descriptions",
    "call_tool",
    "execute_tool_calls",
    "ToolCallRecord",
    "ToolCallRequestLog",
]


async def resolve_tool_prompt(
    config: MCPClientConfig,
    context: EventContext,
    *,
    agent_id: str,
    enable_tools: bool,
    template: str | None,
    include_schemas: bool,
) -> tuple[str | None, list[ToolDescriptor]]:
    """Return a tool-aware prompt based on the MCP tool inventory."""
    if not enable_tools or not template:
        return None, []

    env = build_environment(config, context.env)
    client = MCPClient(config=config, env=env)
    try:
        tools = await client.list_tools()
    except MCPClientError as exc:
        logger.warning(
            context,
            "agent_tool_prompt_list_failed",
            extra=extra(agent_id=agent_id, error=str(exc), details=exc.details),
        )
        return None, []
    except Exception as exc:  # pragma: no cover - defensive guardrail
        logger.error(
            context,
            "agent_tool_prompt_unexpected_error",
            extra=extra(agent_id=agent_id, error=repr(exc)),
        )
        return None, []

    return build_tool_prompt(
        tools,
        template=template,
        include_schemas=include_schemas,
    ), tools


def build_tool_prompt(
    tools: list[ToolDescriptor],
    *,
    template: str | None,
    include_schemas: bool,
) -> str | None:
    """Compose a structured system prompt detailing available tools."""
    if not tools or not template:
        return None

    tool_descriptions = format_tool_descriptions(
        tools,
        include_schemas=include_schemas,
    )
    if not tool_descriptions:
        return None

    try:
        prompt = template.format(tool_descriptions=tool_descriptions)
    except (IndexError, KeyError, ValueError):
        prompt = f"{template}\n{tool_descriptions}"
    return prompt.strip()


def format_tool_descriptions(
    tools: list[ToolDescriptor],
    *,
    include_schemas: bool,
) -> str:
    """Render tool metadata as bullet points for LLM consumption."""
    lines: list[str] = []
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
