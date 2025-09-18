"""Generate completions using an OpenAI-compatible model endpoint."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from ..client import AsyncModelClient, ModelClientError
from ..models import CompletionRequest, CompletionResponse
from ..settings import ModelClientSettings, load_settings, merge_config

__steps__ = ["generate"]

__api__ = event_api(
    summary="hopeit.agents model client generate",
    payload=(CompletionRequest, "Conversation and overrides"),
    responses={
        200: (CompletionResponse, "Completion result"),
        500: (str, "Provider error"),
    },
)

logger, extra = app_extra_logger()


async def generate(payload: CompletionRequest, context: EventContext) -> CompletionResponse:
    """Call the provider using defaults from settings and request overrides."""
    settings = _load_model_settings(context)
    config = merge_config(settings, payload.config)
    api_key = settings.resolve_api_key(context.env)

    client = AsyncModelClient(
        base_url=settings.api_base,
        api_key=api_key,
        timeout_seconds=settings.timeout_seconds,
        default_headers=settings.extra_headers,
    )

    try:
        response = await client.complete(payload, config)
    except ModelClientError as exc:
        logger.error("model_client_error", extra=extra(status=exc.status, details=exc.details))
        raise

    logger.info(
        "model_client_completion",
        extra=extra(model=response.model, finish_reason=response.finish_reason),
    )
    return response


def _load_model_settings(context: EventContext) -> ModelClientSettings:
    settings_map = cast(Mapping[str, Any], context.settings)
    try:
        return load_settings(settings_map)
    except KeyError:
        logger.error(
            "missing_model_client_settings",
            extra=extra(keys=list(settings_map.keys())),
        )
        raise
