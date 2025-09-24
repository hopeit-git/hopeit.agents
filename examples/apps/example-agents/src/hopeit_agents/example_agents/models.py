"""Run an agent conversation combining model completions and MCP tool calls."""

from typing import Any

from hopeit.app.logger import app_extra_logger
from hopeit.dataobjects import dataclass, dataobject, field

from hopeit_agents.mcp_client.agent_tooling import (
    ToolCallRecord,
)
from hopeit_agents.model_client.models import Conversation, Message

logger, extra = app_extra_logger()


@dataobject
@dataclass
class AgentRequest:
    """Incoming agent instruction."""

    agent_id: str
    user_message: str
    conversation: Conversation | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataobject
@dataclass
class AgentResponse:
    """Agent execution output."""

    agent_id: str
    conversation: Conversation
    assistant_message: Message
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
