"""Sum two numbers skill event."""

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit_agents.skills.api import agent_skill

from ...models import SumTwoNumberRequest, SumTwoNumberResponse

__steps__ = ["sum_two_numbers"]

__skill__ = agent_skill(
    summary="hopeit_agents example skill: sum two numbers",
    description="Skill to sum two integers",
    payload=(SumTwoNumberRequest, "Sum two numbers request"),
    response=(SumTwoNumberResponse, "Sum two numbers response"),
)

logger, extra = app_extra_logger()


async def sum_two_numbers(
    payload: SumTwoNumberRequest,
    context: EventContext,
) -> SumTwoNumberResponse:
    """Return the sum of two integer numbers a + b."""

    value = payload.a + payload.b
    return SumTwoNumberResponse(result=value)
