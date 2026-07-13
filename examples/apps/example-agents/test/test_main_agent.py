"""Tests for main-to-expert delegation and random dependency injection."""

import pytest
from pydantic_ai import UsageLimits
from pydantic_ai.messages import ModelRequest, ToolReturnPart
from pydantic_ai.models.test import TestModel

from hopeit_agents.example_agents.agents.main_agent import run_main_agent
from hopeit_agents.example_agents.tools import ExpertAgentDeps, random_integer


def test_random_integer_is_deterministic_and_normalizes_bounds() -> None:
    calls: list[tuple[int, int]] = []

    def source(minimum: int, maximum: int) -> int:
        calls.append((minimum, maximum))
        return 7

    assert random_integer(10, 2, source=source) == 7
    assert calls == [(2, 10)]


@pytest.mark.asyncio
async def test_main_agent_delegates_to_expert_that_calls_tools() -> None:
    main_model = TestModel(
        call_tools=["solve_expression"],
        custom_output_text="The delegated result is 9.",
    )
    expert_model = TestModel(
        call_tools=["generate_random", "sum_two_numbers"],
        custom_output_args={
            "expr_values": [
                {"expr": "x", "value": 7},
                {"expr": "x + 2", "value": 9},
            ]
        },
    )

    result = await run_main_agent(
        "Add 2 to a random integer.",
        main_model=main_model,
        expert_model=expert_model,
        main_instructions="Delegate the expression and summarize the result.",
        expert_instructions="Use the tools and return structured results.",
        expert_deps=ExpertAgentDeps(random_number=lambda _minimum, _maximum: 7),
        limits=UsageLimits(request_limit=10, tool_calls_limit=10),
    )

    assert result.output == "The delegated result is 9."
    assert result.usage.requests >= 4
    assert result.usage.tool_calls == 3
    assert any(
        isinstance(part, ToolReturnPart) and part.tool_name == "solve_expression"
        for message in result.all_messages()
        if isinstance(message, ModelRequest)
        for part in message.parts
    )
    assert main_model.last_model_request_parameters is not None
    assert {tool.name for tool in main_model.last_model_request_parameters.function_tools} == {
        "solve_expression"
    }
    assert expert_model.last_model_request_parameters is not None
    assert {tool.name for tool in expert_model.last_model_request_parameters.function_tools} == {
        "generate_random",
        "sum_two_numbers",
    }
