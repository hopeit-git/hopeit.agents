"""Random number generator skill event."""

import random

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit_agents.skills.api import agent_skill

from ...models import RandomNumberRequest, RandomNumberResponse, RandomNumberResult

__steps__ = ["generate_random"]

__skill__ = agent_skill(
    summary="hopeit_agents example skill: generate random number",
    description="Skill to generate a random integer withing a given range",
    payload=(RandomNumberRequest, "Random number request"),
    response=(RandomNumberResponse, "Random number response"),
)

logger, extra = app_extra_logger()


async def generate_random(
    payload: RandomNumberRequest,
    context: EventContext,
) -> RandomNumberResponse:
    """Return a random integer between minimum and maximum (inclusive)."""
    minimum, maximum = payload.range.min, payload.range.max
    if minimum > maximum:
        minimum, maximum = maximum, minimum

    value = random.randint(minimum, maximum)
    return RandomNumberResponse(result=RandomNumberResult(value=value))
