"""Agent prompt configuration utilities."""

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from hopeit.dataobjects import dataclass, dataobject

_PLACEHOLDER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


@dataobject
@dataclass
class AgentConfig:
    """Immutable data structure holding an agent prompt configuration."""

    name: str
    version: str
    prompt_template: str
    variables: Mapping[str, str]
    enable_tools: bool = False
    tools: list[str] | None = None
    tool_prompt_template: str | None = None

    @property
    def key(self) -> str:
        """Return a version-qualified identifier for the agent configuration."""

        return f"{self.name}:{self.version}"


def create_agent_config(
    name: str,
    prompt_template: str,
    variables: Mapping[str, Any],
    *,
    enable_tools: bool = False,
    tools: list[str] | None = None,
    tool_prompt_template: str | None = None,
) -> AgentConfig:
    """Create an :class:`AgentConfig` for the provided template and variables."""

    normalized_variables = _normalize_variables(variables)
    version = _compute_agent_config_version(prompt_template, normalized_variables)

    return AgentConfig(
        name=name,
        version=version,
        prompt_template=prompt_template,
        variables=normalized_variables,
        enable_tools=enable_tools,
        tools=tools,
        tool_prompt_template=tool_prompt_template,
    )


def _compute_agent_config_version(
    prompt_template: str,
    variables: dict[str, str],
    *,
    tools: list[str] | None = None,
    tool_prompt_template: str | None = None,
) -> str:
    """Compute a deterministic version identifier for an agent configuration."""

    canonical_payload = {
        "prompt_template": prompt_template,
        "variables": _sorted_dict(variables),
        "tools": sorted(tools or []),
        "tool_prompt_template": tool_prompt_template or "",
    }
    canonical_json = json.dumps(canonical_payload, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return f"{digest[:12]}"


def _normalize_variables(variables: Mapping[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in variables.items():
        if not isinstance(key, str):
            raise TypeError("Variable names must be strings.")
        if not _PLACEHOLDER_NAME_PATTERN.fullmatch(key):
            raise ValueError(
                f"Invalid variable name '{key}'. Only alphanumeric and underscores allowed."
            )
        normalized[key] = str(value)
    return normalized


def _sorted_dict(variables: Mapping[str, str]) -> dict[str, str]:
    return {key: variables[key] for key in sorted(variables)}
