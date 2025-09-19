"""Async client that delegates MCP tool operations to the official SDK."""

import asyncio
import uuid
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from time import monotonic
from typing import Any, cast

from mcp import ClientSession, McpError, StdioServerParameters, stdio_client, types
from mcp.client.streamable_http import streamablehttp_client

from hopeit_agents.mcp_client.models import (
    BridgeConfig,
    ToolAnnotations,
    ToolDescriptor,
    ToolExecutionResult,
    ToolExecutionStatus,
    Transport,
)


@dataclass
class MCPClientError(RuntimeError):
    """Raised when bridge operations fail."""

    message: str
    details: Mapping[str, Any] | None = None

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"MCPClientError(message={self.message})"


class MCPClient:
    """High-level wrapper over the official MCP SDK."""

    def __init__(self, config: BridgeConfig, env: Mapping[str, str] | None = None) -> None:
        self._config = config
        self._env = dict(env or {})
        self._tools_cache: tuple[float, list[ToolDescriptor]] | None = None

    async def list_tools(self) -> list[ToolDescriptor]:
        """Return cached list of tools when possible, otherwise query MCP server."""
        cache = self._tools_cache
        now = monotonic()
        if cache and now - cache[0] < self._config.tool_cache_seconds:
            return cache[1]

        async with self._session() as session:
            try:
                result = await asyncio.wait_for(
                    session.list_tools(),
                    timeout=self._config.list_timeout_seconds,
                )
            except TimeoutError as exc:
                raise MCPClientError("Timed out listing tools") from exc
            except McpError as exc:  # pragma: no cover - depends on SDK runtime
                raise MCPClientError(
                    "MCP protocol error while listing tools",
                    details={
                        "code": exc.error.code,
                        "message": exc.error.message,
                        "data": exc.error.data,
                    },
                ) from exc

        descriptors = [self._tool_from_mcp(tool) for tool in result.tools]
        self._tools_cache = (monotonic(), descriptors)
        return descriptors

    async def call_tool(
        self,
        tool_name: str,
        payload: dict[str, Any] | None,
        *,
        call_id: str | None = None,
        session_id: str | None = None,
    ) -> ToolExecutionResult:
        """Invoke a tool by name passing the provided arguments."""
        call_id = call_id or str(uuid.uuid4())

        async with self._session() as session:
            try:
                result = await asyncio.wait_for(
                    session.call_tool(tool_name, payload),
                    timeout=self._config.call_timeout_seconds,
                )
            except TimeoutError as exc:
                raise MCPClientError(f"Timed out calling tool '{tool_name}'") from exc
            except McpError as exc:  # pragma: no cover - depends on SDK runtime
                raise MCPClientError(
                    f"MCP protocol error calling tool '{tool_name}'",
                    details={
                        "code": exc.error.code,
                        "message": exc.error.message,
                        "data": exc.error.data,
                    },
                ) from exc

        return self._tool_result_from_mcp(tool_name, result, call_id=call_id, session_id=session_id)

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[ClientSession]:
        transport = self._config.transport_enum()
        if transport is Transport.HTTP:
            url = self._config.url
            if not url:
                host = self._config.host
                port = self._config.port
                if not host or port is None:
                    raise MCPClientError("HTTP transport requires either a URL or host and port")
                url = f"http://{host}:{int(port)}/mcp"

            async with streamablehttp_client(
                url,
                timeout=self._config.list_timeout_seconds,
                sse_read_timeout=self._config.call_timeout_seconds,
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session
            return

        if transport is not Transport.STDIO:
            raise MCPClientError(f"Transport '{transport.value}' not supported yet")

        command = self._config.command
        if not command:
            raise MCPClientError("STDIO transport requires a command to launch the server")

        params = StdioServerParameters(
            command=command,
            args=self._config.args,
            env=self._env or None,
            cwd=self._config.cwd,
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    @staticmethod
    def _tool_from_mcp(tool: types.Tool) -> ToolDescriptor:
        return ToolDescriptor(
            name=tool.name,
            title=tool.title,
            description=tool.description,
            input_schema=tool.inputSchema,
            output_schema=tool.outputSchema,
            annotations=(
                None
                if tool.annotations is None
                else ToolAnnotations(**tool.annotations.model_dump())
            ),
            _meta=tool.meta,
        )

    @staticmethod
    def _tool_result_from_mcp(
        tool_name: str, result: types.CallToolResult, *, call_id: str, session_id: str | None
    ) -> ToolExecutionResult:
        content: list[dict[str, Any]] = []
        for item in result.content:
            if hasattr(item, "model_dump"):
                content.append(item.model_dump(mode="json"))
            else:
                content.append({"type": item.__class__.__name__})

        structured: dict[str, Any] | list[Any] | None
        structured_raw = getattr(result, "structuredContent", None)
        if structured_raw is None:
            structured = None
        elif hasattr(structured_raw, "model_dump"):
            structured = cast(dict[str, Any] | list[Any], structured_raw.model_dump(mode="json"))
        else:
            structured = cast(dict[str, Any] | list[Any], structured_raw)

        error_message: str | None = None
        if result.isError:
            for item in result.content:
                if isinstance(item, types.TextContent):
                    error_message = item.text
                    break

        return ToolExecutionResult(
            call_id=call_id,
            tool_name=tool_name,
            status=ToolExecutionStatus.ERROR if result.isError else ToolExecutionStatus.SUCCESS,
            content=content,
            structured_content=structured,
            error_message=error_message,
            raw_result=result.model_dump(mode="json"),
            session_id=session_id,
        )
