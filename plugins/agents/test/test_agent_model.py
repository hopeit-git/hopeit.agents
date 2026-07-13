"""Tests for the shared agent model factory."""

from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.models.openai import OpenAIChatModel

from hopeit_agents.agent_model import (
    SETTINGS_KEY,
    AgentModelProvider,
    AgentModelSettings,
    build_agent_model,
)


def test_agent_model_settings_key_is_provider_neutral() -> None:
    assert SETTINGS_KEY == "agent_model"


def test_build_openai_model_from_configuration() -> None:
    settings = AgentModelSettings(
        provider=AgentModelProvider.OPENAI,
        model_name="gpt-5.2",
        api_key_env="TEST_OPENAI_API_KEY",
    )

    model = build_agent_model(settings, env={"TEST_OPENAI_API_KEY": "test-key"})

    assert isinstance(model, OpenAIChatModel)
    assert model.system == "openai"
    assert str(model.base_url) == "https://api.openai.com/v1/"


def test_build_ollama_model_from_configuration() -> None:
    settings = AgentModelSettings(
        provider=AgentModelProvider.OLLAMA,
        model_name="qwen3",
    )

    model = build_agent_model(settings, env={"OLLAMA_BASE_URL": "http://localhost:11434/v1"})

    assert isinstance(model, OllamaModel)
    assert model.system == "ollama"
    assert str(model.base_url) == "http://localhost:11434/v1/"
