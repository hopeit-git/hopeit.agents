"""Tests for main-agent planning and random dependency injection."""

import pytest
from pydantic_ai.models.test import TestModel

from hopeit_agents.example_agents.agents.main_agent import ExpressionPlan, create_main_agent
from hopeit_agents.example_agents.tools import random_integer


def test_random_integer_is_deterministic_and_normalizes_bounds() -> None:
    calls: list[tuple[int, int]] = []

    def source(minimum: int, maximum: int) -> int:
        calls.append((minimum, maximum))
        return 7

    assert random_integer(10, 2, source=source) == 7
    assert calls == [(2, 10)]


@pytest.mark.asyncio
async def test_main_agent_returns_typed_expression_plan_without_tools() -> None:
    main_model = TestModel(
        custom_output_args={"expression": "x + 2"},
    )
    agent = create_main_agent(
        main_model,
        "Return a typed expression plan without evaluating it.",
    )
    result = await agent.run("Add 2 to a random integer.")

    assert isinstance(result.output, ExpressionPlan)
    assert result.output.expression == "x + 2"
    assert main_model.last_model_request_parameters is not None
    assert main_model.last_model_request_parameters.function_tools == []
