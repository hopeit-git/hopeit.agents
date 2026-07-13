"""Executable configuration and Hopeit-event contract for the migrated example."""

from pathlib import Path
from types import ModuleType

import pytest
from hopeit.app.context import EventContext
from hopeit.testing.apps import config, execute_event
from pydantic_ai.models.test import TestModel

from hopeit_agents.agent_model import SETTINGS_KEY, AgentModelProvider, AgentModelSettings
from hopeit_agents.example_agents.agents import expert_agent, main_agent
from hopeit_agents.example_agents.models import AgentRequest, AgentResponse, ExpertAgentResponse

OPENAI_CONFIG = Path("examples/apps/example-agents/config/app-config.json")
OLLAMA_CONFIG = Path("examples/apps/example-agents/config/app-config-ollama.json")
EXPECTED_AGENT_EVENTS = {"agents.main_agent", "agents.expert_agent"}


def test_events_use_sequential_hopeit_workflows() -> None:
    assert main_agent.__steps__ == [
        "prepare_agents",
        "plan_expression",
        "solve_expression",
        "build_response",
    ]
    assert expert_agent.__steps__ == ["prepare_agent", "execute_agent", "build_response"]


def test_openai_and_ollama_configs_expose_the_same_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_MODEL_NAME", "openai-test-model")
    monkeypatch.setenv("OLLAMA_MODEL_NAME", "ollama-test-model")

    openai_config = config(OPENAI_CONFIG)
    ollama_config = config(OLLAMA_CONFIG)

    assert set(openai_config.events) == EXPECTED_AGENT_EVENTS
    assert set(ollama_config.events) == EXPECTED_AGENT_EVENTS
    assert openai_config.settings[SETTINGS_KEY]["provider"] == "openai"
    assert ollama_config.settings[SETTINGS_KEY]["provider"] == "ollama"


@pytest.mark.asyncio
async def test_expert_hopeit_event_runs_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_MODEL_NAME", "openai-test-model")
    app_config = config(OPENAI_CONFIG)

    def use_test_model(module: ModuleType, context: EventContext, **_kwargs: object) -> None:
        module.__dict__["build_agent_model"] = lambda _settings: TestModel(
            call_tools=["generate_random", "sum_two_numbers"],
            custom_output_args={"expr_values": [{"expr": "2 + 3", "value": 5}]},
        )

    response = await execute_event(
        app_config,
        "agents.expert_agent",
        AgentRequest(user_message="Evaluate 2 + 3"),
        mocks=[use_test_model],
    )

    assert isinstance(response, ExpertAgentResponse)
    assert response.results.expr_values[0].value == 5
    assert response.usage.tool_calls == 2


@pytest.mark.asyncio
async def test_main_hopeit_workflow_runs_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_MODEL_NAME", "openai-test-model")
    app_config = config(OPENAI_CONFIG)
    models = iter(
        [
            TestModel(
                custom_output_args={"expression": "2 + 3"},
            ),
            TestModel(
                call_tools=["generate_random", "sum_two_numbers"],
                custom_output_args={"expr_values": [{"expr": "2 + 3", "value": 5}]},
            ),
        ]
    )

    def use_test_models(module: ModuleType, context: EventContext, **_kwargs: object) -> None:
        module.__dict__["build_agent_model"] = lambda _settings: next(models)

    response = await execute_event(
        app_config,
        "agents.main_agent",
        AgentRequest(user_message="Evaluate 2 + 3"),
        mocks=[use_test_models],
    )

    assert isinstance(response, AgentResponse)
    assert response.output == "Expression `2 + 3` evaluated to: 2 + 3 = 5"
    assert response.usage.tool_calls == 2


def test_model_settings_are_deserialized_from_hopeit_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_MODEL_NAME", "ollama-test-model")
    app_config = config(OLLAMA_CONFIG)
    assert app_config.effective_settings is not None
    event_settings = app_config.effective_settings["agents.main_agent"]
    settings = event_settings["extras"][SETTINGS_KEY]

    parsed = AgentModelSettings(
        provider=AgentModelProvider(settings["provider"]),
        model_name=settings["model_name"],
        base_url=settings["base_url"],
        api_key_env=settings["api_key_env"],
    )

    assert parsed.provider == AgentModelProvider.OLLAMA
    assert parsed.model_name == "ollama-test-model"
