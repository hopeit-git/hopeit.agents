import inspect
import re
from collections.abc import Callable, Generator
from functools import partial
from typing import Any, NamedTuple, get_origin

from hopeit.app.config import AppConfig, AppDescriptor, EventDescriptor, EventPlugMode, EventType
from hopeit.server.imports import find_event_handler
from hopeit.server.logger import engine_logger
from hopeit.server.names import spinalcase
from mcp import types
from pydantic import TypeAdapter

logger = engine_logger()

METHOD_MAPPING = {
    EventType.POST: "post",
    EventType.MULTIPART: "post",
}

PayloadDef = type | tuple[type, str]


def event_tool_api(
    *,
    summary: str | None = None,
    description: str | None = None,
    payload: PayloadDef,
    response: PayloadDef,
) -> Callable[..., dict[str, Any]]:
    """Build an event tool handler that exposes Hopeit events through MCP."""
    return partial(_event_tool_api, summary, description, payload, response)


def _event_tool_api(
    summary: str | None,
    description: str | None,
    payload: PayloadDef,
    response: PayloadDef,
    module: str,
    app_config: AppConfig,
    event_name: str,
    plugin: AppConfig | None,
) -> dict[str, Any]:
    """
    Handler returned by event_tool_api(...)
    """
    method_spec: dict[str, Any] = {
        "summary": _method_summary(module, summary),
        "description": _method_description(module, description, summary),
    }

    event_config = app_config.events[event_name]
    content_type = (
        "multipart/form-data" if event_config.type == EventType.MULTIPART else "application/json"
    )
    if payload is not None:
        method_spec["requestBody"] = {
            "description": _payload_description(payload),
            "required": True,
            "content": {content_type: {"schema": _payload_schema(event_name, payload)}},
        }

    def _payload_content_type(arg: PayloadDef) -> tuple[PayloadDef, str]:
        return arg, "application/json"

    def _response_content(arg: PayloadDef) -> dict[str, Any]:
        dt, content_type = _payload_content_type(arg)
        return {content_type: {"schema": _payload_schema(event_name, dt)}}

    api_responses = {
        "200": {
            "description": _payload_description(response),
            "content": _response_content(response),
        }
    }
    method_spec["responses"] = api_responses
    return method_spec


def _datatype_schema(event_name: str, datatype: type) -> dict[str, Any]:
    origin = get_origin(datatype)
    if origin is None:
        origin = datatype
    if origin is not None and hasattr(origin, "__data_object__"):
        if origin.__data_object__["schema"]:
            return TypeAdapter(origin).json_schema(
                # schema_generator=GenerateOpenAPI30Schema,
                # ref_template="#/components/schemas/{model}",
            )
    raise TypeError(f"Schema not supported for type: {datatype.__name__}")


def _payload_schema(event_name: str, arg: PayloadDef) -> dict[str, Any]:
    datatype = arg[0] if isinstance(arg, tuple) else arg
    return _datatype_schema(event_name, datatype)


def _payload_description(arg: PayloadDef) -> str:
    if isinstance(arg, tuple):
        return arg[1]
    if hasattr(arg, "__name__"):
        return arg.__name__
    return str(arg)


def _method_summary(module: str, summary: str | None = None) -> str:
    if summary is not None:
        return summary
    doc_str = inspect.getdoc(module)
    if doc_str is not None:
        return doc_str.split("\n", maxsplit=1)[0]
    return ""


def _method_description(
    module: str, description: str | None = None, summary: str | None = None
) -> str:
    if description is not None:
        return description
    doc_str = inspect.getdoc(module)
    if doc_str is not None and doc_str.count("\n") > 1:
        return re.sub(r"^\W+", "", doc_str.split("\n", 1)[1])
    return _method_summary(module, summary)


class ToolEventInfo(NamedTuple):
    event_name: str
    event_info: EventDescriptor
    tool: types.Tool


def extract_app_tool_specs(
    app_config: AppConfig, plugin: AppConfig | None = None
) -> Generator[ToolEventInfo]:
    """Yield MCP tool specifications for standalone or plugin events in an app config."""
    events = (
        {k: v for k, v in app_config.events.items() if v.plug_mode == EventPlugMode.STANDALONE}
        if plugin is None
        else {k: v for k, v in plugin.events.items() if v.plug_mode == EventPlugMode.ON_APP}
    )
    plugin_app = None if plugin is None else plugin.app
    for event_name, event_info in events.items():
        full_tool_name, tool_name = app_tool_name(
            app_config.app,
            event_name=event_name,
            plugin=plugin_app,
            override_route_name=event_info.route,
        )
        method = METHOD_MAPPING.get(event_info.type)
        if method is None:
            continue
        event_spec = _extract_event_tool_spec(
            app_config if plugin is None else plugin, event_name, event_info
        )
        yield ToolEventInfo(
            event_name=event_name,
            event_info=event_info,
            tool=types.Tool(
                name=tool_name,
                title=event_spec["responses"]["200"].get("summary"),
                description=event_spec["responses"]["200"]["description"],
                inputSchema=event_spec["requestBody"]["content"]["application/json"]["schema"],
                outputSchema=event_spec["responses"]["200"]["content"]["application/json"][
                    "schema"
                ],
                annotations=types.ToolAnnotations(title=full_tool_name, readOnlyHint=True),
            ),
        )


def _extract_event_tool_spec(
    app_config: AppConfig, event_name: str, event_info: EventDescriptor
) -> dict[str, Any]:
    """
    Extract __mcp__ definition from event implementation
    """
    module = find_event_handler(app_config=app_config, event_name=event_name, event_info=event_info)
    if hasattr(module, "__mcp__"):
        method_spec = module.__mcp__
        if isinstance(method_spec, dict):
            return method_spec
        return method_spec(module, app_config, event_name, None)  # type: ignore[no-any-return]
    raise TypeError(f"Missing __mcp__ spec for event: {app_config.app_key}.{event_name}")


def app_tool_name(
    app: AppDescriptor,
    *,
    event_name: str,
    plugin: AppDescriptor | None = None,
    override_route_name: str | None = None,
) -> tuple[str, str]:
    """
    Returns the a tuple with the fully qualified tool name, a simplified name for a given tool
    """
    components = [
        app.name,
        *([plugin.name] if plugin else []),
        event_name,
    ]
    return (
        "/".join(spinalcase(x) for x in components),
        spinalcase(components[-1])
        if override_route_name is None
        else (
            spinalcase(override_route_name[1:])
            if override_route_name[0] == "/"
            else spinalcase(override_route_name)
        ),
    )
