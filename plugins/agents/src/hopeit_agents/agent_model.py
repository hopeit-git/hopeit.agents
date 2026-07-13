"""Configuration-driven model construction for Hopeit agents."""

import os
from collections.abc import Mapping
from enum import StrEnum

from hopeit.dataobjects import dataclass, dataobject
from pydantic_ai.models import Model
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.providers.openai import OpenAIProvider

SETTINGS_KEY = "agent_model"


class AgentModelProvider(StrEnum):
    """Model providers supported by the common Hopeit configuration."""

    OPENAI = "openai"
    OLLAMA = "ollama"


@dataobject
@dataclass
class AgentModelSettings:
    """Settings used to construct the model shared by Hopeit agent events."""

    provider: AgentModelProvider
    model_name: str
    base_url: str | None = None
    api_key_env: str | None = None

    def resolve_api_key(self, env: Mapping[str, str] | None = None) -> str | None:
        """Resolve a provider API key from the configured environment variable."""
        source = os.environ if env is None else env
        env_name = self.api_key_env
        if env_name is None:
            env_name = (
                "OPENAI_API_KEY" if self.provider == AgentModelProvider.OPENAI else "OLLAMA_API_KEY"
            )
        value = source.get(env_name)
        return value if value else None

    def resolve_base_url(self, env: Mapping[str, str] | None = None) -> str | None:
        """Resolve an explicit base URL, with Ollama environment fallback."""
        if self.base_url:
            return self.base_url
        if self.provider != AgentModelProvider.OLLAMA:
            return None
        source = os.environ if env is None else env
        return source.get("OLLAMA_BASE_URL")


def build_agent_model(
    settings: AgentModelSettings,
    *,
    env: Mapping[str, str] | None = None,
) -> Model:
    """Build an OpenAI or Ollama model without leaking provider checks into agents."""
    api_key = settings.resolve_api_key(env)
    base_url = settings.resolve_base_url(env)

    match settings.provider:
        case AgentModelProvider.OPENAI:
            return OpenAIChatModel(
                settings.model_name,
                provider=OpenAIProvider(base_url=base_url, api_key=api_key),
            )
        case AgentModelProvider.OLLAMA:
            return OllamaModel(
                settings.model_name,
                provider=OllamaProvider(base_url=base_url, api_key=api_key),
            )

    raise ValueError(f"Unsupported agent model provider: {settings.provider}")
