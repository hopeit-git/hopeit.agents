"""Unit tests for helpers in `hopeit_agents.mcp_server.tools.api`."""

from hopeit.app.config import AppDescriptor

from hopeit_agents.mcp_server.tools import api


def test_app_tool_name_without_plugin() -> None:
    app = AppDescriptor(name="demo-app", version="0.1")

    tool_name = api.app_tool_name(app, event_name="tool.sum_two_numbers")

    assert tool_name == "demo-app/tool.sum_two_numbers"


def test_app_tool_name_with_plugin() -> None:
    app = AppDescriptor(name="demo-app", version="0.1")
    plugin = AppDescriptor(name="plugin", version="0.1")

    tool_name = api.app_tool_name(
        app,
        event_name="tool.sum_two_numbers",
        plugin=plugin,
    )

    assert tool_name == "demo-app/plugin/tool.sum_two_numbers"


def test_app_tool_name_uses_override_route() -> None:
    app = AppDescriptor(name="demo-app", version="0.1")

    tool_name = api.app_tool_name(
        app,
        event_name="tool.sum_two_numbers",
        override_route_name="/custom/route",
    )

    assert tool_name == "custom/route"
