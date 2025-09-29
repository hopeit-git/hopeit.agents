"""Integration test that exercises the MCP server over HTTP with example tools."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import suppress

import pytest
import uvicorn
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client

from hopeit_agents.mcp_client.client import MCPClient
from hopeit_agents.mcp_client.models import (
    MCPClientConfig,
    ToolExecutionStatus,
    Transport,
)
from hopeit_agents.mcp_server.server import mcp as mcp_server

pytestmark = pytest.mark.asyncio

_CONFIG_FILES = [
    "plugins/mcp/mcp-server/config/dev-noauth.json",
    "plugins/mcp/mcp-server/config/plugin-config.json",
    "examples/plugins/example-tool/config/plugin-config.json",
]
# _REPO_ROOT = Path(__file__).resolve().parents[4]


async def _wait_for_server_start(server: uvicorn.Server, timeout: float = 10.0) -> None:
    """Poll the uvicorn server until it signals readiness or a timeout expires."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not server.started:
        if loop.time() >= deadline:
            raise TimeoutError("Timed out waiting for MCP server startup.")
        await asyncio.sleep(0.05)


def _server_port(server: uvicorn.Server) -> int:
    """Return the bound TCP port for the given uvicorn server instance."""
    sockets = [sock for http_server in server.servers or [] for sock in (http_server.sockets or [])]
    if not sockets:
        raise RuntimeError("MCP server sockets not bound.")
    return int(sockets[0].getsockname()[1])


@pytest.fixture
async def mcp_http_endpoint() -> AsyncGenerator[tuple[str, int], None]:
    """Host the MCP HTTP app on an ephemeral port for the duration of a test."""
    app = mcp_server._create_http_app(
        config_files=_CONFIG_FILES,
        enabled_groups=[],
        start_streams=False,
    )
    server_config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8765,
        log_level="error",
        loop="asyncio",
    )
    server = uvicorn.Server(server_config)
    server_task = asyncio.create_task(server.serve())
    try:
        await asyncio.sleep(0)
        if server_task.done():
            exc = server_task.exception()
            if isinstance(exc, SystemExit):  # pragma: no cover - sandbox restriction
                pytest.skip("Uvicorn could not bind required port inside sandboxed environment")
        try:
            await _wait_for_server_start(server)
        except SystemExit as exc:  # pragma: no cover - environment-specific safeguard
            server_task.cancel()
            with suppress(asyncio.CancelledError):
                await server_task
            pytest.skip(f"MCP server could not start: {exc}")
        port = _server_port(server)
        yield "127.0.0.1", port
    finally:
        server.should_exit = True
        if not server_task.done():
            try:
                await asyncio.wait_for(server_task, timeout=5)
            except TimeoutError:
                server_task.cancel()
                with suppress(asyncio.CancelledError):
                    await server_task
        else:
            with suppress(asyncio.CancelledError, SystemExit):
                await server_task


async def test_mcp_server_serves_example_tools(mcp_http_endpoint: tuple[str, int]) -> None:
    """Verify the MCP server can list and invoke the bundled example tools."""
    host, port = mcp_http_endpoint
    client_config = MCPClientConfig(
        transport=Transport.HTTP,
        host=host,
        port=port,
        tool_cache_seconds=0.0,
        list_timeout_seconds=5.0,
        call_timeout_seconds=10.0,
    )
    client = MCPClient(config=client_config, env={"MCP_RANDOM_SEED": "1234"})

    tools = await client.list_tools()
    names = {tool.name for tool in tools}
    assert "tool-sum-two-numbers" in names
    assert "tool-generate-random" in names

    sum_result = await client.call_tool(
        tool_name="tool-sum-two-numbers",
        payload={"a": 1, "b": 2},
        call_id="sum-integration",
    )
    assert sum_result.status == ToolExecutionStatus.SUCCESS
    assert sum_result.structured_content == {"result": 3}

    random_result = await client.call_tool(
        tool_name="tool-generate-random",
        payload={"range": {"min": 123, "max": 123}},
        call_id="random-integration",
    )
    assert random_result.status == ToolExecutionStatus.SUCCESS
    assert isinstance(random_result.structured_content, dict)
    result_payload = random_result.structured_content.get("result")
    assert isinstance(result_payload, dict)
    value = result_payload.get("value")
    assert isinstance(value, int)
    assert value == 123


async def test_mcp_server_returns_method_not_found_for_unknown_tool(
    mcp_http_endpoint: tuple[str, int],
) -> None:
    """Ensure the server returns an error when clients call an unknown tool."""
    host, port = mcp_http_endpoint
    url = f"http://{host}:{port}/mcp"

    async with streamablehttp_client(
        url,
        timeout=5.0,
        sse_read_timeout=5.0,
    ) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            result = await session.call_tool(
                "tool-does-not-exist",
                {},
            )

            assert result.isError is True
            assert any(
                isinstance(block, types.TextContent) and "Invalid tool name" in block.text
                for block in result.content
            )
