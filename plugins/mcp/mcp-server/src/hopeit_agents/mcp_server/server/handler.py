"""Register hopeit events as MCP tools and dispatch incoming calls."""

import logging
import uuid
from collections.abc import Awaitable, Callable
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


CallableHandler = Callable[[dict[str, Any], dict[str, str] | None], Awaitable[dict[str, Any]]]


class Server:
    """In-memory registry of tool descriptors and their call handlers."""

    def __init__(self) -> None:
        self.tools: list[mcp.types.Tool] = []
        self.handlers: dict[str, CallableHandler] = {}


_server = Server()
auth_info_default: dict[str, str] = {}


def init_logger() -> None:
    """Initialise the module logger using the engine configuration."""
    global logger
    logger = engine_logger()


def reset() -> None:
    """Reset registered tools and handlers.

    Ensures a fresh registry for subsequent server startups (e.g. during tests).
    """
    _server.tools.clear()
    _server.handlers.clear()


def register_tool(
    tool: mcp.types.Tool,
    app_engine: AppEngine,
    *,
    plugin: AppEngine | None = None,
    event_name: str,
    event_info: EventDescriptor,
) -> None:
    """Register a tool handler for the given event and cache it for dispatching."""
    datatype = find_datatype_handler(
        app_config=app_engine.app_config, event_name=event_name, event_info=event_info
    )
    full_tool_name, tool_name = api.app_tool_name(
        app_engine.app_config.app,
        event_name=event_name,
        plugin=None if plugin is None else plugin.app_config.app,
        override_route_name=event_info.route,
    )
    logger.info(__name__, f"Registering tool: {full_tool_name} input={str(datatype)}")
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
    if tool_name in _server.handlers:
        raise RuntimeError(f"Tool name {tool_name} duplicated at runtime.")
    _server.tools.append(tool)
    _server.handlers[tool_name] = handler


def tool_list() -> list[mcp.types.Tool]:
    """Return the list of tools currently registered with the handler."""
    return _server.tools


async def invoke_tool(
    tool_name: str,
    # auth_types: list[AuthType],
    payload_raw: dict[str, Any],
    headers: dict[str, str] | None,
) -> dict[str, Any]:
    """Execute the handler associated with `tool_name` using the provided payload."""
    handler = _server.handlers.get(tool_name)
    if handler is None:
        raise ValueError(f"Invalid tool name: '{tool_name}'.")
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
    """Execute a tool call from MCP by invoking the underlying hopeit event."""
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
    """Build the event context and emit the start log entry for the invocation."""
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
    """Invoke the hopeit engine event and log completion metrics."""
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
    """Generate tracking identifiers, merging any inbound `x-track-*` headers."""
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
