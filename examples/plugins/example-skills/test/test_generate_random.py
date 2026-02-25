"""Tests for the random-number MCP example tool."""

import pytest
from hopeit.testing.apps import config, execute_event

from hopeit_agents.example_tool.models import (
    MinMaxRange,
    RandomNumberRequest,
    RandomNumberResponse,
    RandomNumberResult,
)
from hopeit_agents.example_tool.tool import generate_random


@pytest.mark.asyncio
async def test_generate_random_returns_expected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the random tool returns the stubbed randint result."""
    monkeypatch.setattr(
        generate_random.random,  # type: ignore[attr-defined]
        "randint",
        lambda *_args, **_kwargs: 7,
    )

    app_config = config("examples/plugins/example-tool/config/plugin-config.json")
    response = await execute_event(
        app_config, "tool.generate_random", RandomNumberRequest(MinMaxRange(min=0, max=10))
    )

    assert response == RandomNumberResponse(result=RandomNumberResult(value=7))
