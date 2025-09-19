"""Integration tests for the list_tools API event."""

from __future__ import annotations

import pytest
from hopeit.testing.apps import config, execute_event

from hopeit_agents.mcp_client.api import list_tools as list_tools_module
from hopeit_agents.mcp_client.models import BridgeConfig, ToolDescriptor


@pytest.mark.asyncio
async def test_list_tools_returns_descriptors(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_tools event should proxy MCP client results."""

    captured: dict[str, object] = {}
    expected_tools = [
        ToolDescriptor(
            name="demo/tool.sum",
            title="Sum",
            description="Adds numbers",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )
    ]

    def fake_build_environment(
        config_value: BridgeConfig, env_value: dict[str, str]
    ) -> dict[str, str]:
        captured["build_env_args"] = (config_value, env_value)
        return {"ENV_FLAG": "test"}

    class FakeClient:
        def __init__(self, *, config: BridgeConfig, env: dict[str, str]) -> None:
            captured["client_config"] = config
            captured["client_env"] = env

        async def list_tools(self) -> list[ToolDescriptor]:
            captured["list_tools_called"] = True
            return expected_tools

    monkeypatch.setattr(list_tools_module, "build_environment", fake_build_environment)
    monkeypatch.setattr(list_tools_module, "MCPClient", FakeClient)

    app_config = config("plugins/mcp/mcp-client/config/plugin-config.json")
    response = await execute_event(app_config, "api.list_tools", None)

    assert response == expected_tools
    assert captured["list_tools_called"] is True
    assert captured["client_env"] == {"ENV_FLAG": "test"}
