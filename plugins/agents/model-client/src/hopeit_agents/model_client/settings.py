"""Settings helpers for the model client plugin."""

import os
from collections.abc import Mapping
from typing import Any

from hopeit.dataobjects import dataclass, dataobject, field

from hopeit_agents.model_client.models import CompletionConfig

SETTINGS_KEY = "model_client"


@dataobject
@dataclass
class ModelClientSettings:
    """Configuration loaded from hopeit.app context settings."""

    api_base: str
    default_model: str
    api_key_env: str | None = None
    deployment_name: str | None = None
    api_version: str | None = None
    timeout_seconds: float = 30.0
    extra_headers: dict[str, str] = field(default_factory=dict)
    default_config: CompletionConfig = field(
        default_factory=lambda: CompletionConfig(enable_tool_expansion=True)
    )

    def resolve_api_key(self, env: Mapping[str, Any]) -> str | None:
        """Return the API key found in context env using api_key_env."""
        if self.api_key_env is None:
            return None
        api_key = env.get(self.api_key_env)
        if isinstance(api_key, str) and api_key:
            return api_key
        return os.getenv(self.api_key_env)


def merge_config(
    settings: ModelClientSettings,
    override: CompletionConfig | None,
) -> CompletionConfig:
    """Merge request config with defaults defined in settings."""
    base = settings.default_config
    if override is None:
        target = CompletionConfig(
            model=base.model or settings.default_model,
            temperature=base.temperature,
            max_output_tokens=base.max_output_tokens,
            response_format=base.response_format,
            tool_choice=base.tool_choice,
            enable_tool_expansion=base.enable_tool_expansion,
            available_tools=base.available_tools,
        )
    else:
        target = CompletionConfig(
            model=override.model or base.model or settings.default_model,
            temperature=override.temperature
            if override.temperature is not None
            else base.temperature,
            max_output_tokens=override.max_output_tokens
            if override.max_output_tokens is not None
            else base.max_output_tokens,
            response_format=override.response_format or base.response_format,
            tool_choice=override.tool_choice or base.tool_choice,
            enable_tool_expansion=override.enable_tool_expansion
            if override.enable_tool_expansion is not None
            else base.enable_tool_expansion,
            available_tools=override.available_tools or base.available_tools,
        )
    if target.enable_tool_expansion is None:
        target.enable_tool_expansion = True
    return target
