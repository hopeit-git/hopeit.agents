"""Executable configuration and workflow contracts for the example agents."""

from pathlib import Path
from types import ModuleType

import pytest
from hopeit.app.context import EventContext
from hopeit.apps_client import AppsClient, ClientAuthStrategy
from hopeit.testing.apps import config, execute_event
from pydantic_ai.models.test import TestModel

from hopeit_agents.agent_model import SETTINGS_KEY, AgentModelProvider, AgentModelSettings
from hopeit_agents.example_agents.agents import expert_agent, main_agent
from hopeit_agents.example_agents.models import (
    AgentRequest,
    AgentResponse,
    AgentUsage,
    ExpertAgentResponse,
    ExpertAgentResults,
    ExpressionValue,
)
from hopeit_agents.example_agents.settings import AgentRunSettings, agent_retries

OPENAI_CONFIG = Path("examples/apps/example-agents/config/app-config.json")
OLLAMA_CONFIG = Path("examples/apps/example-agents/config/app-config-ollama.json")
EXPECTED_AGENT_EVENTS = {"agents.main_agent", "agents.expert_agent"}


def test_events_use_sequential_hopeit_workflows() -> None:
    assert main_agent.__steps__ == [
        "prepare_agent",
        "plan_expression",
        "call_expert_agent",
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
    assert openai_config.app_connections["expert-agent"].client == "hopeit.apps_client.AppsClient"
    assert ollama_config.app_connections["expert-agent"].client == "hopeit.apps_client.AppsClient"
    for app_config in (openai_config, ollama_config):
        assert app_config.settings["main_agent"]["tool_retries"] == 1
        assert app_config.settings["main_agent"]["output_retries"] == 3
        assert app_config.settings["expert_agent"]["tool_retries"] == 1
        assert app_config.settings["expert_agent"]["output_retries"] == 3
        connection = app_config.events["agents.main_agent"].connections[0]
        assert connection.app_connection == "expert-agent"
        assert connection.event == "agents.expert_agent"
        client = AppsClient(app_config, "expert-agent")
        assert client.settings.auth_strategy == ClientAuthStrategy.UNSECURED
        assert client.settings.ssl is False


def test_agent_retry_settings_map_to_pydantic_ai_categories() -> None:
    settings = AgentRunSettings(
        instructions_path="instructions.md",
        tool_retries=2,
        output_retries=4,
    )

    assert agent_retries(settings) == {"tools": 2, "output": 4}


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
    calls: list[tuple[str, str, AgentRequest]] = []

    def use_test_models(module: ModuleType, context: EventContext, **_kwargs: object) -> None:
        module.__dict__["build_agent_model"] = lambda _settings: TestModel(
            custom_output_args={"expression": "2 + 3"},
        )

        async def call_expert(
            app_connection: str,
            *,
            event: str,
            datatype: type[object],
            payload: object,
            context: EventContext,
            **_call_kwargs: object,
        ) -> ExpertAgentResponse:
            assert datatype is ExpertAgentResponse
            assert isinstance(payload, AgentRequest)
            calls.append((app_connection, event, payload))
            return ExpertAgentResponse(
                conversation_id=payload.conversation_id or "expert-conversation",
                results=ExpertAgentResults(expr_values=[ExpressionValue(expr="2 + 3", value=5)]),
                history_json="[]",
                usage=AgentUsage(
                    requests=2,
                    tool_calls=2,
                    input_tokens=10,
                    output_tokens=5,
                ),
            )

        module.__dict__["app_call"] = call_expert

    response = await execute_event(
        app_config,
        "agents.main_agent",
        AgentRequest(user_message="Evaluate 2 + 3"),
        mocks=[use_test_models],
    )

    assert isinstance(response, AgentResponse)
    assert response.output == "Expression `2 + 3` evaluated to: 2 + 3 = 5"
    assert response.usage.tool_calls == 2
    assert len(calls) == 1
    app_connection, event, request = calls[0]
    assert app_connection == "expert-agent"
    assert event == "agents.expert_agent"
    assert request.user_message == "2 + 3"


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
