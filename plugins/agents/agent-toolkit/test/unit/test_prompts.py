"""Unit tests for agent prompt configuration helpers."""

import pytest

from hopeit_agents.agent_toolkit.agents.prompts import (
    AgentConfig,
    compute_agent_config_version,
    create_agent_config,
)


def test_create_agent_config_renders_prompt_and_sets_version() -> None:
    """The created agent config renders the prompt and exposes a qualified name."""

    template = "Welcome {user}, today we will use the {tool} toolkit."
    variables = {
        "user": "Ada",
        "tool": "analysis",
    }

    config = create_agent_config(
        name="analysis-helper", prompt_template=template, variables=variables
    )

    assert isinstance(config, AgentConfig)
    assert config.prompt == "Welcome Ada, today we will use the analysis toolkit."
    assert config.version == compute_agent_config_version(
        template, {"tool": "analysis", "user": "Ada"}
    )
    assert config.qualified_name == f"{config.name}:{config.version}"


def test_create_agent_config_missing_placeholder() -> None:
    """Requesting a config without providing all placeholders raises a ValueError."""

    template = "Hi {user}, run {tool}."

    with pytest.raises(ValueError):
        create_agent_config(name="demo", prompt_template=template, variables={"user": "Grace"})


def test_compute_agent_config_version_reflects_variable_changes() -> None:
    """Changing variable values yields a different deterministic version."""

    template = "Hello {user}."
    version_one = compute_agent_config_version(template, {"user": "one"})
    version_two = compute_agent_config_version(template, {"user": "two"})

    assert version_one != version_two
    assert version_one.startswith("acv-")
    assert version_two.startswith("acv-")
