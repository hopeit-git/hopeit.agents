"""Dataclasses that configure the example agent behaviour."""

from hopeit.dataobjects import dataclass, dataobject, field


@dataobject
@dataclass
class AgentSettings:
    """Configurable defaults for the example agent."""

    agent_name: str
    system_prompt_template: str
    tool_prompt_template: str | None = None
    answer_prompt_template: str | None = None
    enable_tools: bool = False
    allowed_tools: list[str] = field(default_factory=list)
    include_tool_schemas_in_prompt: bool = True
