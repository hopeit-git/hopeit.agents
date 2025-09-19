import logging
import uuid
from collections.abc import Coroutine
from datetime import UTC, datetime
from functools import partial
from typing import Any

import mcp.types
from hopeit.app.config import EventDescriptor, EventSettings
from hopeit.app.context import EventContext
from hopeit.dataobjects import DataObject
from hopeit.dataobjects.payload import Payload
from hopeit.server.engine import AppEngine
from hopeit.server.events import get_event_settings
from hopeit.server.logger import EngineLoggerWrapper, engine_logger, extra_logger
from hopeit.server.metrics import metrics
from hopeit.server.names import snakecase
from hopeit.server.steps import find_datatype_handler

from hopeit_agents.mcp_server.tools import api

logger: EngineLoggerWrapper = logging.getLogger(__name__)  # type: ignore
extra = extra_logger()


type CallableHandler = partial[Coroutine[Any, Any, dict[str, Any]]]


class Server:
    def __init__(self) -> None:
        self.tools: list[mcp.types.Tool] = []
        self.handlers: dict[str, CallableHandler] = {}


_server = Server()
auth_info_default: dict[str, str] = {}


def init_logger() -> None:
    global logger
    logger = engine_logger()


def register_tool(
    tool: mcp.types.Tool,
    app_engine: AppEngine,
    *,
    plugin: AppEngine | None = None,
    event_name: str,
    event_info: EventDescriptor,
) -> None:
    """
    Creates route for handling POST event
    """
    datatype = find_datatype_handler(
        app_config=app_engine.app_config, event_name=event_name, event_info=event_info
    )
    tool_name = api.app_tool_name(
        app_engine.app_config.app,
        event_name=event_name,
        plugin=None if plugin is None else plugin.app_config.app,
        override_route_name=event_info.route,
    )
    logger.info(__name__, f"Tool: {tool_name} input={str(datatype)}")
    impl = plugin if plugin else app_engine
    handler = partial(
        _handle_tool_invocation,
        app_engine,
        impl,
        event_name,
        datatype,
        # _auth_types(impl, event_name),
    )
    # handler.__closure__ = None
    # handler.__code__ = _handle_tool_invocation.__code__
    _server.tools.append(tool)
    _server.handlers[tool_name] = handler


def tool_list() -> list[mcp.types.Tool]:
    return _server.tools


async def invoke_tool(
    tool_name: str,
    # auth_types: list[AuthType],
    payload_raw: dict[str, Any],
    headers: dict[str, str] | None,
) -> dict[str, Any]:
    handler = _server.handlers.get(tool_name)
    if handler is None:
        raise ValueError(f"Tool {tool_name} not registered.")
    return await handler(payload_raw, headers)


async def _handle_tool_invocation(
    app_engine: AppEngine,
    impl: AppEngine,
    event_name: str,
    datatype: type[DataObject],
    # auth_types: list[AuthType],
    payload_raw: dict[str, Any],
    headers: dict[str, str] | None,
) -> dict[str, Any]:
    """
    Handler to execute tool calls
    """
    context = None
    try:
        event_settings = get_event_settings(app_engine.settings, event_name)
        context = _request_start(app_engine, impl, event_name, event_settings, headers)
        # _validate_authorization(app_engine.app_config, context, auth_types, request)
        payload = Payload.from_obj(payload_raw, datatype)
        result = await _request_execute(
            impl,
            event_name,
            context,
            payload,
        )
        return Payload.to_obj(result)  # type: ignore[return-value]
    except Exception as e:  # pylint: disable=broad-except
        logger.error(__name__, e)
        raise


def _request_start(
    app_engine: AppEngine,
    plugin: AppEngine,
    event_name: str,
    event_settings: EventSettings[DataObject],
    headers: dict[str, str] | None,
) -> EventContext:
    """
    Extracts context and track information from a request and logs start of event
    """
    context = EventContext(
        app_config=app_engine.app_config,
        plugin_config=plugin.app_config,
        event_name=event_name,
        settings=event_settings,
        track_ids=_track_ids(headers or {}),
        auth_info=auth_info_default,
    )
    logger.start(context)
    return context


async def _request_execute(
    app_engine: AppEngine,
    event_name: str,
    context: EventContext,
    payload: DataObject,
) -> DataObject:
    """
    Executes request using engine event handler
    """
    result = await app_engine.execute(context=context, query_args=None, payload=payload)
    logger.done(context, extra=metrics(context))
    return result  # type: ignore[return-value]


# def _auth_types(app_engine: AppEngine, event_name: str):
#     assert app_engine.app_config.server
#     event_info = app_engine.app_config.events[event_name]
#     if event_info.auth:
#         return event_info.auth
#     return app_engine.app_config.server.auth.default_auth_methods


def _track_ids(headers: dict[str, str]) -> dict[str, str]:
    return {
        "track.operation_id": str(uuid.uuid4()),
        "track.request_id": str(uuid.uuid4()),
        "track.request_ts": datetime.now(tz=UTC).isoformat(),
        **{
            "track." + snakecase(k[8:].lower()): v
            for k, v in headers.items()
            if k.lower().startswith("x-track-")
        },
    }
