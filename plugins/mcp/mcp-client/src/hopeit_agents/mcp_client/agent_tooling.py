"""Utilities to help agents describe and invoke MCP tools."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit_agents.mcp_client.api import (
    invoke_tool as bridge_invoke_tool,
)
from hopeit_agents.mcp_client.api import (
    list_tools as bridge_list_tools,
)
from hopeit_agents.mcp_client.client import MCPClientError
from hopeit_agents.mcp_client.models import (
    ToolCallRecord,
    ToolCallRequestLog,
    ToolDescriptor,
    ToolExecutionResult,
    ToolInvocation,
)

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
    context: EventContext,
    *,
    agent_id: str,
    enable_tools: bool,
    template: str | None,
    include_schemas: bool,
) -> str | None:
    """Return a tool-aware prompt based on the MCP tool inventory."""
    if not enable_tools or not template:
        return None

    try:
        tools = await bridge_list_tools.list_tools(None, context)
    except MCPClientError as exc:
        logger.warning(
            context,
            "agent_tool_prompt_list_failed",
            extra=extra(agent_id=agent_id, error=str(exc), details=exc.details),
        )
        return None
    except Exception as exc:  # pragma: no cover - defensive guardrail
        logger.warning(
            context,
            "agent_tool_prompt_unexpected_error",
            extra=extra(agent_id=agent_id, error=repr(exc)),
        )
        return None

    return build_tool_prompt(
        tools,
        template=template,
        include_schemas=include_schemas,
    )


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
    context: EventContext,
    *,
    tool_name: str,
    payload: dict[str, Any],
    session_id: str | None = None,
) -> ToolExecutionResult:
    """Execute an MCP tool through the bridge using the provided payload."""
    invocation = ToolInvocation(
        call_id="call_123",
        tool_name=tool_name,
        payload=payload,
        session_id=session_id,
    )
    return await bridge_invoke_tool.invoke_tool(invocation, context)


async def execute_tool_calls(
    context: EventContext,
    *,
    tool_calls: Sequence[ToolInvocation],
    session_id: str | None = None,
) -> list[ToolCallRecord]:
    """Execute multiple tool calls capturing request and response data."""
    records: list[ToolCallRecord] = []
    for tool_call in tool_calls:
        result = await call_tool(
            context,
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
