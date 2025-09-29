"""End-to-end tests for the example tool exposed via the expert agent."""

import pytest
from hopeit.testing.apps import config, execute_event

from hopeit_agents.example_tool.models import SumTwoNumberRequest, SumTwoNumberResponse


@pytest.mark.asyncio
async def test_sum_two_numbers_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the sum-two-numbers tool returns result."""
    app_config = config("examples/plugins/example-tool/config/plugin-config.json")
    response = await execute_event(
        app_config, "tool.sum_two_numbers", SumTwoNumberRequest(a=1, b=2)
    )

    assert response == SumTwoNumberResponse(result=3)
