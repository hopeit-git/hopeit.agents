"""Application-owned run settings for the example agents."""

from pathlib import Path

from hopeit.dataobjects import dataclass, dataobject
from pydantic_ai import AgentRetries, UsageLimits


@dataobject
@dataclass
class AgentRunSettings:
    """Instructions, retry budgets, and usage limits for one agent."""

    instructions_path: str
    request_limit: int = 10
    tool_calls_limit: int = 20
    tool_retries: int = 1
    output_retries: int = 3


def load_instructions(settings: AgentRunSettings) -> str:
    """Load agent instructions from the configured repository-relative path."""
    return Path(settings.instructions_path).read_text(encoding="utf-8")


def usage_limits(settings: AgentRunSettings) -> UsageLimits:
    """Convert application settings into native agent usage limits."""
    return UsageLimits(
        request_limit=settings.request_limit,
        tool_calls_limit=settings.tool_calls_limit,
    )


def agent_retries(settings: AgentRunSettings) -> AgentRetries:
    """Convert application settings into native Pydantic AI retry budgets."""
    return {
        "tools": settings.tool_retries,
        "output": settings.output_retries,
    }
