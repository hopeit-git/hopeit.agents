"""Dataclasses that configure the example agent behaviour."""

from hopeit.dataobjects import dataclass, dataobject


@dataobject
@dataclass
class AgentSettings:
    """Configurable defaults for the example agent."""

    system_prompt: str | None = "You are a helpful agent built with hopeit_agents."
    enable_tools: bool = True
    tool_prompt_template: str | None = (
        "You can call the following MCP tools when helpful. "
        "Return tool calls with arguments that match the provided JSON schema.\n"
        "{tool_descriptions}"
    )
    include_tool_schemas_in_prompt: bool = True
