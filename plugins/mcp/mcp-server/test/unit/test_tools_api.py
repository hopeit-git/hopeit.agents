"""Unit tests for helpers in `hopeit_agents.mcp_server.tools.api`."""

from hopeit.app.config import AppDescriptor

from hopeit_agents.mcp_server.tools import api


def test_app_tool_name_without_plugin() -> None:
    """Default tool names omitting plugin namespaces."""
    app = AppDescriptor(name="demo-app", version="0.1")

    full_tool_name, tool_name = api.app_tool_name(app, event_name="tool.sum_two_numbers")

    assert full_tool_name == "demo-app/tool-sum-two-numbers"
    assert tool_name == "tool-sum-two-numbers"


def test_app_tool_name_with_plugin() -> None:
    """Ensure plugin-qualified names include the plugin descriptor."""
    app = AppDescriptor(name="demo-app", version="0.1")
    plugin = AppDescriptor(name="plugin", version="0.1")

    full_tool_name, tool_name = api.app_tool_name(
        app,
        event_name="tool.sum_two_numbers",
        plugin=plugin,
    )

    assert full_tool_name == "demo-app/plugin/tool-sum-two-numbers"
    assert tool_name == "tool-sum-two-numbers"


def test_app_tool_name_uses_override_route() -> None:
    """Confirm overriding the route adjusts the simplified tool name."""
    app = AppDescriptor(name="demo-app", version="0.1")

    full_tool_name, tool_name = api.app_tool_name(
        app,
        event_name="tool.sum_two_numbers",
        override_route_name="/custom/route",
    )

    assert full_tool_name == "demo-app/tool-sum-two-numbers"
    assert tool_name == "custom/route"
