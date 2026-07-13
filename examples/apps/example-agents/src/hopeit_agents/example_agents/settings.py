"""Application-owned run settings for the example agents."""

from pathlib import Path

from hopeit.dataobjects import dataclass, dataobject
from pydantic_ai import UsageLimits


@dataobject
@dataclass
class AgentRunSettings:
    """Instructions and usage limits for one agent."""

    instructions_path: str
    request_limit: int = 10
    tool_calls_limit: int = 20


def load_instructions(settings: AgentRunSettings) -> str:
    """Load agent instructions from the configured repository-relative path."""
    return Path(settings.instructions_path).read_text(encoding="utf-8")


def usage_limits(settings: AgentRunSettings) -> UsageLimits:
    """Convert application settings into native agent usage limits."""
    return UsageLimits(
        request_limit=settings.request_limit,
        tool_calls_limit=settings.tool_calls_limit,
    )
