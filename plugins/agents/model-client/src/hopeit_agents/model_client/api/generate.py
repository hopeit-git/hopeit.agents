"""Generate completions using an OpenAI-compatible model endpoint."""

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit_agents.model_client.client import AsyncModelClient, ModelClientError
from hopeit_agents.model_client.models import CompletionRequest, CompletionResponse
from hopeit_agents.model_client.settings import ModelClientSettings, merge_config

__steps__ = ["generate"]

__api__ = event_api(
    summary="hopeit_agents model client generate",
    payload=(CompletionRequest, "Conversation and overrides"),
    responses={
        200: (CompletionResponse, "Completion result"),
        500: (str, "Provider error"),
    },
)

logger, extra = app_extra_logger()


async def generate(payload: CompletionRequest, context: EventContext) -> CompletionResponse:
    """Call the provider using defaults from settings and request overrides."""
    settings = context.settings(key="model_client", datatype=ModelClientSettings)

    config = merge_config(settings, payload.config)
    api_key = settings.resolve_api_key(context.env)

    client = AsyncModelClient(
        base_url=settings.api_base,
        api_key=api_key,
        timeout_seconds=settings.timeout_seconds,
        default_headers=settings.extra_headers,
        deployment_name=settings.deployment_name,
        api_version=settings.api_version,
    )

    try:
        response = await client.complete(payload, config)
    except ModelClientError as exc:
        logger.error(
            context, "model_client_error", extra=extra(status=exc.status, details=exc.details)
        )
        raise

    logger.info(
        context,
        "model_client_completion",
        extra=extra(model=response.model, finish_reason=response.finish_reason),
    )
    return response
