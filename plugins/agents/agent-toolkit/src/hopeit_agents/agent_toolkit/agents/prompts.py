"""Agent prompt configuration utilities."""

import re

from hopeit_agents.agent_toolkit.agents.agent_config import AgentConfig

_PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")


def render_prompt(
    agent_config: AgentConfig, extra_variables: dict[str, str], *, include_tools: bool = False
) -> str:
    rendered = agent_config.prompt_template
    if include_tools:
        if agent_config.tool_prompt_template is None:
            raise ValueError("Missing tool_prompt_template")
        rendered += "\n" + agent_config.tool_prompt_template
    all_variables = {**agent_config.variables, **extra_variables}
    for key, value in all_variables.items():
        rendered = rendered.replace("{{" + key + "}}", value)

    unresolved = set(_PLACEHOLDER_PATTERN.findall(rendered))
    if unresolved:
        missing = ", ".join(sorted(unresolved))
        raise ValueError(f"Missing values for placeholders: {missing}")

    return rendered
