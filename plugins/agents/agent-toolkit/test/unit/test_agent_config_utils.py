"""Additional unit tests for agent configuration helpers."""

from collections.abc import Mapping
from typing import Any, cast

import pytest

from hopeit_agents.agent_toolkit.agents.agent_config import (
    AgentConfig,
    _compute_agent_config_version,
    create_agent_config,
)


def test_create_agent_config_normalizes_values_and_builds_key() -> None:
    """Variable values are normalized and the config exposes a qualified key."""

    config = create_agent_config(
        name="demo-agent",
        prompt_template="Hello {user}!",
        variables={"user": "Ada", "visits": 3, "active": True},
        enable_tools=True,
        tools=["alpha", "beta"],
        tool_prompt_template="Use tools wisely",
    )

    assert isinstance(config, AgentConfig)
    assert config.variables == {"user": "Ada", "visits": "3", "active": "True"}

    expected_version = _compute_agent_config_version(
        "Hello {user}!", {"active": "True", "user": "Ada", "visits": "3"}
    )
    assert config.version == expected_version
    assert config.key == f"{config.name}:{config.version}"
    assert config.enable_tools is True
    assert config.tools == ["alpha", "beta"]
    assert config.tool_prompt_template == "Use tools wisely"


def test_create_agent_config_rejects_invalid_variable_names() -> None:
    """Variable names must be valid placeholder identifiers."""

    with pytest.raises(TypeError):
        _ = create_agent_config(
            name="invalid",
            prompt_template="Hi",
            variables=cast(Mapping[str, Any], {1: "value"}),
        )

    with pytest.raises(ValueError):
        _ = create_agent_config(
            name="invalid",
            prompt_template="Hi",
            variables={"user-name": "value"},
        )


def test_compute_agent_config_version_includes_tool_configuration() -> None:
    """Changing tool metadata influences the computed deterministic version."""

    template = "Hello {user}!"
    variables = {"user": "Ada"}

    base = _compute_agent_config_version(template, variables)
    with_tools = _compute_agent_config_version(template, variables, tools=["summarize"])
    with_prompt = _compute_agent_config_version(
        template, variables, tool_prompt_template="Invoke {{tool}}"
    )

    assert base != with_tools
    assert base != with_prompt
    assert with_tools != with_prompt
