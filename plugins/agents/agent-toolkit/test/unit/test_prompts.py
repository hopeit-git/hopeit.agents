"""Unit tests for agent prompt configuration helpers."""

import pytest

from hopeit_agents.agent_toolkit.agents.agent_config import AgentConfig, create_agent_config
from hopeit_agents.agent_toolkit.agents.prompts import render_prompt


def test_create_agent_config_renders_prompt_and_sets_version() -> None:
    """The created agent config renders the prompt and exposes a qualified name."""

    template = "Welcome {{user}}, today we will use the {{tool}} toolkit to perform {{task}}!"
    variables = {
        "user": "Ada",
        "tool": "analysis",
    }

    config = create_agent_config(
        name="analysis-helper", prompt_template=template, variables=variables
    )

    assert isinstance(config, AgentConfig)

    # version computed using _compute_agent_config_version(
    #    template, {"tool": "analysis", "user": "Ada"}
    # )"
    assert config.version == "901694b68a41"
    assert config.key == "analysis-helper:901694b68a41"
    assert config.prompt_template == template
    assert config.variables == variables

    prompt = render_prompt(config, {"task": "data analysis"})
    assert prompt == "Welcome Ada, today we will use the analysis toolkit to perform data analysis!"

    prompt = render_prompt(config, {"user": "John", "task": "data analysis"})
    assert (
        prompt == "Welcome John, today we will use the analysis toolkit to perform data analysis!"
    )


def test_render_prompt_missing_placeholder_raises_error() -> None:
    """Requesting a config without providing all placeholders leave placeholders untouched"""

    template = "Hi {{user}}, this is your task: {{task_name}}."

    config = create_agent_config(name="demo", prompt_template=template, variables={"user": "Grace"})

    with pytest.raises(ValueError) as e:
        try:
            _ = render_prompt(config, {})
        except ValueError as e:
            assert "task_name" in str(e)
            raise


def test_compute_agent_config_version_reflects_variable_changes() -> None:
    """Changing variable values yields a different deterministic version."""

    name = "test-agent"
    template = "Hello {user}."
    version_one = create_agent_config(name, template, {"user": "one"})
    version_two = create_agent_config(name, template, {"user": "two"})

    assert version_one.version != version_two.version


def test_render_prompt_with_tools_appends_tool_section() -> None:
    """When include_tools is true the tool prompt template is appended and rendered."""

    config = create_agent_config(
        name="tool-agent",
        prompt_template="Instructions for {{agent}}.",
        variables={"agent": "Ada"},
        enable_tools=True,
        tools=["summarize"],
        tool_prompt_template="Tools:\n- {{tool_name}}",
    )

    prompt = render_prompt(config, {"tool_name": "summarize"}, include_tools=True)

    assert prompt == "Instructions for Ada.\nTools:\n- summarize"


def test_render_prompt_with_tools_requires_tool_template() -> None:
    """Including tools without a tool prompt template raises an error."""

    config = create_agent_config(
        name="tool-agent",
        prompt_template="Hello {{agent}}",
        variables={"agent": "Ada"},
        enable_tools=True,
    )

    with pytest.raises(ValueError):
        render_prompt(config, {}, include_tools=True)
