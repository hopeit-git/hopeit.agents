"""Agent prompt configuration utilities."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Mapping

_PLACEHOLDER_PATTERN = re.compile(r"\{([A-Za-z0-9_]+)\}")
_PLACEHOLDER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


@dataclass(frozen=True)
class AgentConfig:
    """Immutable data structure holding an agent prompt configuration."""

    name: str
    version: str
    prompt_template: str
    variables: Mapping[str, str]
    prompt: str

    @property
    def qualified_name(self) -> str:
        """Return a version-qualified identifier for the agent configuration."""

        return f"{self.name}:{self.version}"


def create_agent_config(name: str, prompt_template: str, variables: Mapping[str, Any]) -> AgentConfig:
    """Create an :class:`AgentConfig` for the provided template and variables.

    Parameters
    ----------
    name:
        Free-form identifier for the agent configuration.
    prompt_template:
        Prompt template text containing placeholders wrapped in ``{}``.
    variables:
        Mapping containing the values to interpolate in the template.

    Returns
    -------
    AgentConfig
        Frozen configuration containing the rendered prompt and version.

    Raises
    ------
    TypeError
        If a variable name is not a string.
    ValueError
        If a variable name is invalid or a placeholder is missing.
    """

    normalized_variables = _normalize_variables(variables)
    expected_placeholders = set(_PLACEHOLDER_PATTERN.findall(prompt_template))

    missing_placeholders = expected_placeholders - normalized_variables.keys()
    if missing_placeholders:
        missing = ", ".join(sorted(missing_placeholders))
        raise ValueError(f"Missing values for placeholders: {missing}")

    rendered_prompt = _render_prompt(prompt_template, normalized_variables)
    version = compute_agent_config_version(prompt_template, normalized_variables)

    return AgentConfig(
        name=name,
        version=version,
        prompt_template=prompt_template,
        variables=normalized_variables,
        prompt=rendered_prompt,
    )


def compute_agent_config_version(prompt_template: str, variables: Mapping[str, str]) -> str:
    """Compute a deterministic version identifier for an agent configuration."""

    canonical_payload = {
        "prompt_template": prompt_template,
        "variables": _sorted_dict(variables),
    }
    canonical_json = json.dumps(canonical_payload, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return f"acv-{digest[:12]}"


def _normalize_variables(variables: Mapping[str, Any]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for key, value in variables.items():
        if not isinstance(key, str):
            raise TypeError("Variable names must be strings.")
        if not _PLACEHOLDER_NAME_PATTERN.fullmatch(key):
            raise ValueError(
                f"Invalid variable name '{key}'. Only alphanumeric characters and underscores are allowed."
            )
        normalized[key] = str(value)
    return normalized


def _render_prompt(prompt_template: str, variables: Mapping[str, str]) -> str:
    rendered = prompt_template
    for key, value in variables.items():
        rendered = rendered.replace(f"{{{key}}}", value)

    unresolved = set(_PLACEHOLDER_PATTERN.findall(rendered))
    if unresolved:
        missing = ", ".join(sorted(unresolved))
        raise ValueError(f"Missing values for placeholders: {missing}")

    return rendered


def _sorted_dict(variables: Mapping[str, str]) -> Dict[str, str]:
    return {key: variables[key] for key in sorted(variables)}
