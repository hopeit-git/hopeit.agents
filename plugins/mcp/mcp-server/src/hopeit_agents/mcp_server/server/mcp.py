"""HTTP-facing MCP server that exposes hopeit events as tools."""

import asyncio
import gc
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from hopeit.app.config import AppConfig, EventType, parse_app_config_json
from hopeit.server import runtime
from hopeit.server.config import ServerConfig, parse_server_config_json
from hopeit.server.logger import EngineLoggerWrapper, engine_logger, extra_logger
from mcp import types
from mcp.server.lowlevel.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route

from hopeit_agents.mcp_server.server import handler
from hopeit_agents.mcp_server.tools import api as tools_api

logger: EngineLoggerWrapper = logging.getLogger(__name__)  # type: ignore
extra = extra_logger()

# ServerInitializationOptions was removed in recent MCP releases; fall back to Any.
InitOptions = Any

HTTP_ENDPOINT = "/mcp"

mcp_server = Server(
    name="hopeit-agents-mcp-server",
    instructions="Expose hopeit agents tool plugins as MCP tools.",
)


def run_app(
    host: str,
    port: int,
    config_files: list[str],
    # api_file: str,
    # api_auto: list[str],
    start_streams: bool,
    enabled_groups: list[str],
    workers: int,
    worker_class: str,
    worker_timeout: int,
) -> None:
    """Start the MCP HTTP server using the provided runtime configuration."""
    init_logger()
    endpoint = f"http://{host}:{port}{HTTP_ENDPOINT}"
    logger.info(__name__, f"Starting MCP Server (transport=http, endpoint={endpoint}).")
    try:
        run_http(
            host,
            port,
            config_files=config_files,
            enabled_groups=enabled_groups,
            start_streams=start_streams,
        )
    except KeyboardInterrupt:  # pragma: no cover - manual interrupt
        logger.info(__name__, "Received interruption, shutting down...")
    logger.info(__name__, "Stopped MCP Server.")


@mcp_server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Return the MCP tool definitions currently registered with the server."""
    return handler.tool_list()


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    """Invoke a registered tool by name, forwarding the optional arguments payload."""
    return await handler.invoke_tool(name, arguments or {}, headers={})


def _create_http_app(
    *,
    config_files: list[str],
    enabled_groups: list[str],
    start_streams: bool,
) -> Starlette:
    """Construct the Starlette application that fronts the MCP session manager."""
    session_manager = StreamableHTTPSessionManager(mcp_server)

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncGenerator[None, None]:
        """Manage engine lifecycle events during Starlette startup and shutdown."""
        init_logger()

        async with session_manager.run():
            logger.info(__name__, "Starting hopeit.engine...")
            await prepare_engine(
                config_files=config_files,
                enabled_groups=enabled_groups,
                start_streams=start_streams,
            )
            logger.info(__name__, "Started hopeit.engine.")
            yield
            await stop_server()

    async def streamable_http_app(scope, receive, send) -> None:  # type: ignore[no-untyped-def]
        """Process HTTP requests using the MCP streamable session manager."""
        if scope["type"] == "lifespan":
            await send({"type": "lifespan.startup.complete"})
            await send({"type": "lifespan.shutdown.complete"})
            return

        if scope["type"] != "http":  # pragma: no cover - ignored during HTTP routing
            raise RuntimeError(f"Unsupported scope type: {scope['type']}")
        await session_manager.handle_request(scope, receive, send)

    async def health(_: Request) -> PlainTextResponse:
        """Answer the HTTP health probe with the server name."""
        return PlainTextResponse(mcp_server.name)

    return Starlette(
        routes=[
            Route("/", endpoint=health, methods=["GET"]),
            Mount(HTTP_ENDPOINT, app=streamable_http_app),
        ],
        lifespan=lifespan,
    )


def run_http(
    host: str,
    port: int,
    *,
    config_files: list[str],
    enabled_groups: list[str],
    start_streams: bool,
) -> None:
    """Run the MCP Starlette application using Uvicorn."""
    app = _create_http_app(
        config_files=config_files, enabled_groups=enabled_groups, start_streams=start_streams
    )
    uvicorn.run(app, host=host, port=port, log_level="debug")


async def prepare_engine(
    *,
    config_files: list[str],
    enabled_groups: list[str],
    start_streams: bool,
) -> None:
    """Load server and app configs, start the engine, and register available tools."""
    logger.info(__name__, f"Loading engine config file: {config_files[0]}")
    server_config: ServerConfig = _load_engine_config(config_files[0])
    await server_startup_hook(server_config)

    apps_config = []
    for config_file in config_files[1:]:
        logger.info(__name__, f"Loading app config file={config_file}...")
        config = _load_app_config(config_file)
        config.server = server_config
        apps_config.append(config)

    # Register and add startup hooks to start configured apps
    for config in apps_config:
        await app_startup_hook(config, enabled_groups)

    # Add hooks to start streams and service
    if start_streams:
        for config in apps_config:
            stream_startup_hook(config)

    # Register MCP tools
    logger.info(__name__, "Registering tools...")
    handler.reset()
    register_tool_handlers(apps_config, enabled_groups=enabled_groups)

    # web_server.on_shutdown.append(_shutdown_hook)
    logger.debug(__name__, "Performing forced garbage collection...")
    gc.collect()


def init_logger() -> None:
    """Configure the engine logger and initialise the tool handler logging."""
    global logger
    logger = engine_logger()
    handler.init_logger()


def register_tool_handlers(apps_config: list[AppConfig], *, enabled_groups: list[str]) -> None:
    """Register tool handlers for app and plugin events exposed through MCP."""
    apps_config_by_key = {config.app.app_key(): config for config in apps_config}
    for app_config in apps_config:
        app_engine = runtime.server.app_engine(app_key=app_config.app_key())
        for info in tools_api.extract_app_tool_specs(app_config, enabled_groups=enabled_groups):
            handler.register_tool(
                info.tool,
                app_engine,
                plugin=None,
                event_name=info.event_name,
                event_info=info.event_info,
            )
        for plugin in app_config.plugins:
            plugin_config = apps_config_by_key[plugin.app_key()]
            plugin_engine = runtime.server.app_engine(app_key=plugin_config.app_key())
            for info in tools_api.extract_app_tool_specs(
                app_config, plugin=plugin_config, enabled_groups=enabled_groups
            ):
                handler.register_tool(
                    info.tool,
                    app_engine,
                    plugin=plugin_engine,
                    event_name=info.event_name,
                    event_info=info.event_info,
                )


async def server_startup_hook(config: ServerConfig) -> None:
    """Start the hopeit runtime server using the parsed server configuration."""
    await runtime.server.start(config=config)


async def stop_server() -> None:
    """Shut down the hopeit runtime server."""
    await runtime.server.stop()
    handler.reset()


async def app_startup_hook(config: AppConfig, enabled_groups: list[str]) -> None:
    """
    Start Hopeit app specified by config

    :param config: AppConfig, configuration for the app to start
    :param enabled_groups: list of event groups names to enable. If empty,
        all events will be enabled.
    """
    _ = await runtime.server.start_app(app_config=config, enabled_groups=enabled_groups)
    for plugin in config.plugins:
        _ = runtime.server.app_engine(app_key=plugin.app_key())


def stream_startup_hook(app_config: AppConfig) -> None:
    """Start configured stream and service events for a running app."""
    app_engine = runtime.server.app_engines[app_config.app_key()]
    for event_name, event_info in app_engine.effective_events.items():
        if event_info.type == EventType.STREAM:
            assert event_info.read_stream
            logger.info(
                __name__,
                f"STREAM start event_name={event_name} read_stream={event_info.read_stream.name}",
            )
            asyncio.create_task(app_engine.read_stream(event_name=event_name))
        elif event_info.type == EventType.SERVICE:
            logger.info(__name__, f"SERVICE start event_name={event_name}")
            asyncio.create_task(app_engine.service_loop(event_name=event_name))


def _load_engine_config(path: str) -> ServerConfig:
    """Load the hopeit server configuration from the provided JSON file."""
    with open(path, encoding="utf-8") as f:
        return parse_server_config_json(f.read())


def _load_app_config(path: str) -> AppConfig:
    """Load an app configuration from the provided JSON file."""
    with open(path, encoding="utf-8") as f:
        return parse_app_config_json(f.read())
