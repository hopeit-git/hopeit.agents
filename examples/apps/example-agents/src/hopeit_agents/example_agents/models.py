"""Public Hopeit payloads for the example agents application."""

from typing import Any

from hopeit.dataobjects import dataclass, dataobject, field
from pydantic_ai.usage import RunUsage


@dataobject
@dataclass
class AgentRequest:
    """Incoming natural-language task for an agent."""

    user_message: str
    conversation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataobject
@dataclass
class ExpressionValue:
    """One expression evaluated by the expert agent."""

    expr: str
    value: int


@dataobject
@dataclass
class ExpertAgentResults:
    """Structured output produced by the expert agent."""

    expr_values: list[ExpressionValue]


@dataobject
@dataclass
class AgentUsage:
    """Stable projection of model and tool usage for an API response."""

    requests: int
    tool_calls: int
    input_tokens: int
    output_tokens: int


@dataobject
@dataclass
class AgentResponse:
    """Human-readable output from the main agent."""

    conversation_id: str
    output: str
    history_json: str
    usage: AgentUsage


@dataobject
@dataclass
class ExpertAgentResponse:
    """Structured output from the standalone expert-agent endpoint."""

    conversation_id: str
    results: ExpertAgentResults
    history_json: str
    usage: AgentUsage


def agent_usage(usage: RunUsage) -> AgentUsage:
    """Project native usage into the public Hopeit response shape."""
    return AgentUsage(
        requests=usage.requests,
        tool_calls=usage.tool_calls,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
    )


def combine_usage(*items: AgentUsage) -> AgentUsage:
    """Combine usage projections from sequential agent workflow steps."""
    return AgentUsage(
        requests=sum(item.requests for item in items),
        tool_calls=sum(item.tool_calls for item in items),
        input_tokens=sum(item.input_tokens for item in items),
        output_tokens=sum(item.output_tokens for item in items),
    )
