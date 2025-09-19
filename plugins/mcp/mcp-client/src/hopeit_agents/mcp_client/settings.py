"""Settings helpers for the MCP bridge plugin."""

import re
from collections.abc import Mapping
from typing import Any

from hopeit_agents.mcp_client.models import BridgeConfig

SETTINGS_KEY = "mcp_client"
_PLACEHOLDER_RE = re.compile(r"^\$\{(?P<name>[A-Z0-9_]+)\}$")


def build_environment(settings: BridgeConfig, context_env: Mapping[str, Any]) -> dict[str, str]:
    """Resolve environment variables combining config and context env."""
    resolved: dict[str, str] = {}
    for key, value in settings.env.items():
        if isinstance(value, str):
            match = _PLACEHOLDER_RE.match(value)
            if match:
                env_value = context_env.get(match.group("name"))
                if isinstance(env_value, str):
                    resolved[key] = env_value
                continue
        if isinstance(value, (str, int, float)):
            resolved[key] = str(value)
    return resolved
