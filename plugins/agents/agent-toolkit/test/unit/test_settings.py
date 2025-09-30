"""Unit tests for agent toolkit settings dataclasses."""

from hopeit_agents.agent_toolkit.settings import AgentSettings


def test_agent_settings_defaults() -> None:
    """Defaults provide safe baseline values for optional settings."""

    settings = AgentSettings(
        agent_name="example-agent",
        system_prompt_template="system.md",
    )

    assert settings.tool_prompt_template is None
    assert settings.enable_tools is False
    assert settings.allowed_tools == []
    assert settings.include_tool_schemas_in_prompt is True


def test_agent_settings_custom_allowed_tools() -> None:
    """Custom allowed tools are preserved without sharing mutable defaults."""

    custom_tools = ["alpha", "beta"]
    settings = AgentSettings(
        agent_name="example-agent",
        system_prompt_template="system.md",
        enable_tools=True,
        allowed_tools=custom_tools,
    )

    assert settings.allowed_tools == custom_tools
    custom_tools.append("gamma")
    assert settings.allowed_tools == ["alpha", "beta"]
