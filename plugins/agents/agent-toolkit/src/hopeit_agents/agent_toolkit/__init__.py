"""Top-level exports for the agent toolkit plugin."""

from .agents import AgentConfig, create_agent_config, render_prompt
from .app import (
    AgentLoopConfig,
    AgentLoopPayload,
    AgentLoopResult,
    AgentSettings,
    agent_with_tools_loop,
)
from .mcp import (
    call_tool,
    execute_tool_calls,
    tool_descriptions,
)

__all__ = [
    "AgentConfig",
    "AgentLoopConfig",
    "AgentLoopPayload",
    "AgentLoopResult",
    "AgentSettings",
    "agent_with_tools_loop",
    "build_tool_prompt",
    "call_tool",
    "render_prompt",
    "create_agent_config",
    "execute_tool_calls",
    "tool_descriptions",
]
