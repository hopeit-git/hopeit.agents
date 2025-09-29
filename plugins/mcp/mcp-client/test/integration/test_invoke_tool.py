"""Integration tests for the invoke_tool API event."""

import pytest
from hopeit.testing.apps import config, execute_event

from hopeit_agents.mcp_client.api import invoke_tool as invoke_tool_module
from hopeit_agents.mcp_client.models import (
    MCPClientConfig,
    ToolExecutionResult,
    ToolExecutionStatus,
    ToolInvocation,
)


@pytest.mark.asyncio
async def test_invoke_tool_returns_execution_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """invoke_tool event should pass payload to MCP client and return its result."""

    captured: dict[str, object] = {}
    expected_result = ToolExecutionResult(
        call_id="call-123",
        tool_name="demo/tool.sum",
        status=ToolExecutionStatus.SUCCESS,
        structured_content={"result": 3},
    )

    def fake_build_environment(
        config_value: MCPClientConfig, env_value: dict[str, str]
    ) -> dict[str, str]:
        captured["build_env_args"] = (config_value, env_value)
        return {"ENV_FLAG": "invoke"}

    class FakeClient:
        def __init__(
            self,
            *,
            config: MCPClientConfig,
            env: dict[str, str],
        ) -> None:
            captured["client_config"] = config
            captured["client_env"] = env

        async def call_tool(
            self,
            tool_name: str,
            payload: dict[str, object] | None,
            *,
            call_id: str | None,
            session_id: str | None,
        ) -> ToolExecutionResult:
            captured["call_args"] = {
                "tool_name": tool_name,
                "payload": payload,
                "call_id": call_id,
                "session_id": session_id,
            }
            return expected_result

    monkeypatch.setattr(invoke_tool_module, "build_environment", fake_build_environment)
    monkeypatch.setattr(invoke_tool_module, "MCPClient", FakeClient)

    app_config = config("plugins/mcp/mcp-client/config/plugin-config.json")
    payload = ToolInvocation(
        tool_name="demo/tool.sum",
        payload={"a": 1, "b": 2},
        call_id="call-123",
        session_id="session-1",
    )

    response = await execute_event(app_config, "api.invoke_tool", payload)

    assert response == expected_result
    assert captured["call_args"] == {
        "tool_name": "demo/tool.sum",
        "payload": {"a": 1, "b": 2},
        "call_id": "call-123",
        "session_id": "session-1",
    }
    assert captured["client_env"] == {"ENV_FLAG": "invoke"}
