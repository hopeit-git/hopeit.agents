"""Tests for the sum-two-numbers example skill."""

import pytest
from hopeit.testing.apps import config, execute_event

from hopeit_agents.example_skills.models import SumTwoNumberRequest, SumTwoNumberResponse


@pytest.mark.asyncio
async def test_sum_two_numbers_basic() -> None:
    """Verify the sum-two-numbers skill returns result."""
    app_config = config("examples/plugins/example-skills/config/plugin-config.json")
    response = await execute_event(
        app_config, "skills.math.sum_two_numbers", SumTwoNumberRequest(a=1, b=2)
    )

    assert response == SumTwoNumberResponse(result=3)
