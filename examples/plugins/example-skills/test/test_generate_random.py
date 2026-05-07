"""Tests for the random-number example skill."""

import pytest
from hopeit.testing.apps import config, execute_event

from hopeit_agents.example_skills.models import (
    MinMaxRange,
    RandomNumberRequest,
    RandomNumberResponse,
    RandomNumberResult,
)
from hopeit_agents.example_skills.skills.data_generation import generate_random


@pytest.mark.asyncio
async def test_generate_random_returns_expected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the random skill returns the stubbed randint result."""
    monkeypatch.setattr(
        generate_random.random,  # type: ignore[attr-defined]
        "randint",
        lambda *_args, **_kwargs: 7,
    )

    app_config = config("examples/plugins/example-skills/config/plugin-config.json")
    response = await execute_event(
        app_config,
        "skills.data_generation.generate_random",
        RandomNumberRequest(MinMaxRange(min=0, max=10)),
    )

    assert response == RandomNumberResponse(result=RandomNumberResult(value=7))
