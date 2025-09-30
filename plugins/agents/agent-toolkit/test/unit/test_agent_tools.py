"""Unit tests for MCP agent tool helpers."""

import uuid
from types import SimpleNamespace
from typing import Any, cast

import pytest
from hopeit.app.context import EventContext

from hopeit_agents.agent_toolkit.mcp import agent_tools
from hopeit_agents.mcp_client.client import MCPClientError
from hopeit_agents.mcp_client.models import (
    MCPClientConfig,
    ToolCallRecord,
    ToolDescriptor,
    ToolExecutionResult,
    ToolExecutionStatus,
    ToolInvocation,
)


def _stub_context(env: dict[str, Any] | None = None) -> tuple[EventContext, SimpleNamespace]:
    namespace = SimpleNamespace(env=env or {})
    return cast(EventContext, namespace), namespace


@pytest.mark.asyncio
async def test_resolve_tools_returns_inventory(monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_tools should call the MCP client and return available tools."""

    tools = [
        ToolDescriptor(
            name="alpha", title=None, description="First", input_schema={}, output_schema=None
        ),
        ToolDescriptor(
            name="beta", title=None, description="Second", input_schema={}, output_schema=None
        ),
    ]
    captured: dict[str, Any] = {}

    def fake_build_environment(
        config: MCPClientConfig, context_env: dict[str, Any]
    ) -> dict[str, str]:
        captured["config"] = config
        captured["context_env"] = context_env
        return {"TOKEN": "secret"}

    class DummyClient:
        def __init__(self, config: MCPClientConfig, env: dict[str, str]) -> None:
            captured["client_env"] = env

        async def list_tools(self) -> list[ToolDescriptor]:
            captured["list_tools_called"] = True
            return tools

    monkeypatch.setattr(agent_tools, "build_environment", fake_build_environment)
    monkeypatch.setattr(agent_tools, "MCPClient", DummyClient)

    context, raw_context = _stub_context({"TOKEN": "from-context"})
    config = MCPClientConfig(command="demo")

    result = await agent_tools.resolve_tools(
        config,
        context,
        agent_id="agent-1",
    )

    assert result == tools
    assert captured["context_env"] == raw_context.env
    assert captured["client_env"] == {"TOKEN": "secret"}
    assert captured["list_tools_called"] is True


@pytest.mark.asyncio
async def test_resolve_tools_filters_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Allowed tools filter should limit the returned inventory."""

    tools = [
        ToolDescriptor(
            name="alpha", title=None, description="First", input_schema={}, output_schema=None
        ),
        ToolDescriptor(
            name="beta", title=None, description="Second", input_schema={}, output_schema=None
        ),
    ]

    class DummyClient:
        def __init__(
            self, config: MCPClientConfig, env: dict[str, str]
        ) -> None:  # pragma: no cover
            self._env = env

        async def list_tools(self) -> list[ToolDescriptor]:
            return tools

    monkeypatch.setattr(agent_tools, "build_environment", lambda config, ctx_env: ctx_env)
    monkeypatch.setattr(agent_tools, "MCPClient", DummyClient)

    context, _ = _stub_context({})
    config = MCPClientConfig()

    result = await agent_tools.resolve_tools(
        config,
        context,
        agent_id="agent-2",
        allowed_tools=["beta"],
    )

    assert [tool.name for tool in result] == ["beta"]


@pytest.mark.asyncio
async def test_resolve_tools_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Client errors should be swallowed and return an empty inventory."""

    stub_logger = SimpleNamespace(
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
    )

    class FailingClient:
        def __init__(self, config: MCPClientConfig, env: dict[str, str]) -> None:
            pass

        async def list_tools(self) -> list[ToolDescriptor]:
            raise MCPClientError("boom", details={"error": "failure"})

    monkeypatch.setattr(agent_tools, "build_environment", lambda config, ctx_env: {})
    monkeypatch.setattr(agent_tools, "MCPClient", FailingClient)
    monkeypatch.setattr(agent_tools, "logger", stub_logger)

    context, _ = _stub_context({})
    config = MCPClientConfig()

    result = await agent_tools.resolve_tools(
        config,
        context,
        agent_id="agent-3",
    )

    assert result == []


def test_tool_descriptions_renders_schemas() -> None:
    """tool_descriptions should render a human friendly bullet list."""

    tool = ToolDescriptor(
        name="alpha",
        title="Alpha",
        description="  Example tool  ",
        input_schema={"type": "object", "properties": {"foo": {"type": "string"}}},
        output_schema=None,
    )

    rendered = agent_tools.tool_descriptions([tool], include_schemas=True)

    assert rendered.startswith("Available tools:\n- alpha: Example tool")
    assert "JSON schema:" in rendered
    assert '\n    {\n      "properties": {' in rendered

    rendered_no_schema = agent_tools.tool_descriptions([tool], include_schemas=False)

    assert "JSON schema" not in rendered_no_schema


@pytest.mark.asyncio
async def test_call_tool_invokes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """call_tool should delegate invocation to the MCP client and return its result."""

    expected_result = ToolExecutionResult(
        call_id="call-123",
        tool_name="alpha",
        status=ToolExecutionStatus.SUCCESS,
        content=[{"type": "text", "text": "ok"}],
    )
    captured: dict[str, Any] = {}

    def fake_build_environment(
        config: MCPClientConfig, context_env: dict[str, Any]
    ) -> dict[str, str]:
        captured["context_env"] = context_env
        return {"TOKEN": "secret"}

    class DummyClient:
        def __init__(self, config: MCPClientConfig, env: dict[str, str]) -> None:
            captured["client_env"] = env

        async def call_tool(
            self,
            tool_name: str,
            payload: dict[str, Any],
            *,
            call_id: str | None = None,
            session_id: str | None = None,
        ) -> ToolExecutionResult:
            captured["call_args"] = {
                "tool_name": tool_name,
                "payload": payload,
                "call_id": call_id,
                "session_id": session_id,
            }
            return expected_result

    monkeypatch.setattr(agent_tools, "build_environment", fake_build_environment)
    monkeypatch.setattr(agent_tools, "MCPClient", DummyClient)

    context, raw_context = _stub_context({"TOKEN": "from-context"})
    config = MCPClientConfig(command="demo")

    result = await agent_tools.call_tool(
        config,
        context,
        call_id="call-123",
        tool_name="alpha",
        payload={"foo": "bar"},
        session_id="session-1",
    )

    assert result is expected_result
    assert captured["client_env"] == {"TOKEN": "secret"}
    assert captured["context_env"] == raw_context.env
    assert captured["call_args"] == {
        "tool_name": "alpha",
        "payload": {"foo": "bar"},
        "call_id": "call-123",
        "session_id": "session-1",
    }


@pytest.mark.asyncio
async def test_call_tool_propagates_client_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """MCP client failures should bubble up to the caller."""

    stub_logger = SimpleNamespace(
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
    )

    class FailingClient:
        def __init__(self, config: MCPClientConfig, env: dict[str, str]) -> None:
            pass

        async def call_tool(
            self,
            tool_name: str,
            payload: dict[str, Any],
            *,
            call_id: str | None = None,
            session_id: str | None = None,
        ) -> ToolExecutionResult:
            raise MCPClientError("failed")

    monkeypatch.setattr(agent_tools, "build_environment", lambda config, ctx_env: {})
    monkeypatch.setattr(agent_tools, "MCPClient", FailingClient)
    monkeypatch.setattr(agent_tools, "logger", stub_logger)

    context, _ = _stub_context({})
    config = MCPClientConfig()

    with pytest.raises(MCPClientError):
        await agent_tools.call_tool(
            config,
            context,
            call_id="call-1",
            tool_name="alpha",
            payload={},
        )


@pytest.mark.asyncio
async def test_execute_tool_calls_invokes_each_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """execute_tool_calls should invoke call_tool for each ToolInvocation."""

    calls: list[dict[str, Any]] = []

    async def fake_call_tool(
        config: MCPClientConfig,
        context: EventContext,
        *,
        call_id: str,
        tool_name: str,
        payload: dict[str, Any],
        session_id: str | None,
    ) -> ToolExecutionResult:
        calls.append(
            {
                "call_id": call_id,
                "tool_name": tool_name,
                "payload": payload,
                "session_id": session_id,
            }
        )
        return ToolExecutionResult(
            call_id=call_id,
            tool_name=tool_name,
            status=ToolExecutionStatus.SUCCESS,
        )

    monkeypatch.setattr(agent_tools, "call_tool", fake_call_tool)

    uuid_values = iter([uuid.UUID(int=1), uuid.UUID(int=2)])
    monkeypatch.setattr(
        agent_tools,
        "uuid",
        SimpleNamespace(uuid4=lambda: next(uuid_values)),
    )

    config = MCPClientConfig()
    context, _ = _stub_context({})
    tool_calls = [
        ToolInvocation(tool_name="alpha", payload={"foo": "bar"}, call_id="explicit"),
        ToolInvocation(tool_name="beta", payload={"baz": "qux"}),
    ]

    records = await agent_tools.execute_tool_calls(
        config,
        context,
        tool_calls=tool_calls,
        session_id="session-2",
    )

    assert len(records) == 2
    assert isinstance(records[0], ToolCallRecord)
    assert calls[0] == {
        "call_id": "explicit",
        "tool_name": "alpha",
        "payload": {"foo": "bar"},
        "session_id": "session-2",
    }
    assert records[0].request.tool_call_id == "explicit"
    assert records[0].request.payload == {"foo": "bar"}

    generated_call_id = "call_0000000001"
    assert calls[1]["call_id"] == generated_call_id
    assert calls[1]["tool_name"] == "beta"
    assert records[1].request.tool_call_id == generated_call_id
    assert records[1].request.payload == {"baz": "qux"}
