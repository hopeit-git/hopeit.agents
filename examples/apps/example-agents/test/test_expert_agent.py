"""Tests for the structured expert agent and its addition tool."""

import pytest
from pydantic_ai import UsageLimits
from pydantic_ai.models.test import TestModel

from hopeit_agents.example_agents.agents.expert_agent import run_expert_agent
from hopeit_agents.example_agents.models import ExpertAgentResults
from hopeit_agents.example_agents.tools import ExpertAgentDeps, sum_two_numbers


def test_sum_two_numbers_basic() -> None:
    assert sum_two_numbers(1, 2) == 3


@pytest.mark.asyncio
async def test_expert_agent_returns_typed_results() -> None:
    model = TestModel(
        call_tools=["generate_random", "sum_two_numbers"],
        custom_output_args={"expr_values": [{"expr": "x + 2", "value": 9}]},
    )

    result = await run_expert_agent(
        "x + 2 where x is between 1 and 10",
        model=model,
        instructions="Use both tools and return structured results.",
        deps=ExpertAgentDeps(random_number=lambda _minimum, _maximum: 7),
        limits=UsageLimits(request_limit=5, tool_calls_limit=5),
    )

    assert isinstance(result.output, ExpertAgentResults)
    assert result.output.expr_values[0].expr == "x + 2"
    assert result.output.expr_values[0].value == 9
    assert result.usage.requests == 2
    assert result.usage.tool_calls == 2
