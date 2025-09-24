"""Sum two numbers tool event."""

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit_agents.mcp_server.tools.api import event_tool_api

from ..models import SumTwoNumberRequest, SumTwoNumberResponse

__steps__ = ["sum_two_numbers"]

__mcp__ = event_tool_api(
    summary="hopeit_agents example tool: sum two numbers",
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
