"""List available MCP tools."""

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit_agents.mcp_client.client import MCPClient, MCPClientError
from hopeit_agents.mcp_client.models import MCPClientConfig, ToolDescriptor
from hopeit_agents.mcp_client.settings import build_environment

__steps__ = ["list_tools"]

__api__ = event_api(
    summary="hopeit_agents MCP client: list tools",
    responses={
        200: (list[ToolDescriptor], "Available tools"),
        500: (str, "MCP client error"),
    },
)

logger, extra = app_extra_logger()


async def list_tools(
    payload: None,
    context: EventContext,
) -> list[ToolDescriptor]:
    """Return tool descriptors using the configured MCP server."""
    config = context.settings(key="mcp_client", datatype=MCPClientConfig)
    env = build_environment(config, context.env)
    client = MCPClient(config=config, env=env)

    try:
        tools = await client.list_tools()
    except MCPClientError as exc:
        logger.error(context, "mcp_list_tools_error", extra=extra(details=exc.details))
        raise

    logger.info(context, "mcp_list_tools_success", extra=extra(tool_count=len(tools)))
    return tools
