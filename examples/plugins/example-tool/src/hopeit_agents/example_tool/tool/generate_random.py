"""Random number generator tool event."""

import random

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit_agents.mcp_server.tools.api import event_tool_api

from ..models import RandomNumberRequest, RandomNumberResponse, RandomNumberResult

__steps__ = ["generate_random"]

__mcp__ = event_tool_api(
    summary="hopeit_agents example tool: generate random number",
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
