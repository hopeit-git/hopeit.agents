"""Invoke an MCP tool and return its result."""

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit_agents.mcp_client.client import MCPClient, MCPClientError
from hopeit_agents.mcp_client.models import MCPClientConfig, ToolExecutionResult, ToolInvocation
from hopeit_agents.mcp_client.settings import build_environment

__steps__ = ["invoke_tool"]

__api__ = event_api(
    summary="hopeit_agents MCP client: invoke tool",
    payload=(ToolInvocation, "Tool invocation payload"),
    responses={
        200: (ToolExecutionResult, "Tool execution result"),
        404: (ToolExecutionResult, "Tool not found"),
        500: (str, "MCP client error"),
    },
)

logger, extra = app_extra_logger()


async def invoke_tool(args: ToolInvocation, context: EventContext) -> ToolExecutionResult:
    """Invoke the requested tool using MCP."""
    config = context.settings(key="mcp_client", datatype=MCPClientConfig)
    env = build_environment(config, context.env)
    client = MCPClient(config=config, env=env)

    try:
        result = await client.call_tool(
            args.tool_name, args.payload, call_id=args.call_id, session_id=args.session_id
        )
    except MCPClientError as exc:
        logger.error(
            context,
            "mcp_invoke_tool_error",
            extra=extra(tool_name=args.tool_name, details=exc.details),
        )
        raise

    logger.info(
        context,
        "mcp_invoke_tool_success",
        extra=extra(tool_name=args.tool_name, status=result.status.value),
    )
    return result
