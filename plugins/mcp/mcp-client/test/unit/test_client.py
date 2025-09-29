"""Unit tests for the MCP client helpers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from mcp import types

from hopeit_agents.mcp_client.client import MCPClient
from hopeit_agents.mcp_client.models import MCPClientConfig, Transport


def _client_config() -> MCPClientConfig:
    """Return a minimal HTTP configuration used in tests."""
    return MCPClientConfig(
        transport=Transport.HTTP,
        host="127.0.0.1",
        port=8765,
        tool_cache_seconds=100.0,
        list_timeout_seconds=1.0,
        call_timeout_seconds=1.0,
    )


class DummySession:
    """Lightweight stub that mimics the MCP client session API."""

    def __init__(self) -> None:
        self.list_calls = 0

    async def initialize(self) -> None:  # pragma: no cover - no-op
        """Pretend to initialise the session."""
        return None

    async def list_tools(self) -> types.ListToolsResult:
        """Return a predictable tool list and track call count."""
        self.list_calls += 1
        tool = types.Tool(
            name="demo/tool.sum",
            title="Sum",
            description="Add two numbers",
            inputSchema={"type": "object"},
            outputSchema={"type": "object"},
            annotations=None,
        )
        return types.ListToolsResult(tools=[tool])

    async def __aexit__(self, *_args: Any) -> None:  # pragma: no cover - compatibility
        return None


@pytest.mark.asyncio
async def test_list_tools_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the client does not re-query the MCP server while the cache is warm."""
    client = MCPClient(config=_client_config())

    session_holder: list[Any] = []

    @asynccontextmanager
    async def fake_session(self: MCPClient) -> AsyncGenerator[DummySession, None]:
        session = DummySession()
        session_holder.append(session)
        yield session

    monkeypatch.setattr(MCPClient, "_session", fake_session, raising=False)

    tools_first = await client.list_tools()
    tools_second = await client.list_tools()

    assert tools_first == tools_second
    assert len(session_holder) == 1
    assert session_holder[0].list_calls == 1
