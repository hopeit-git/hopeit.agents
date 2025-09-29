"""Unit tests for the agent loop step."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from hopeit.dataobjects.payload import Payload
from pytest import MonkeyPatch

from hopeit_agents.agent_toolkit.app.steps import agent_loop
from hopeit_agents.agent_toolkit.app.steps.agent_loop import AgentLoopConfig, AgentLoopPayload
from hopeit_agents.agent_toolkit.settings import AgentSettings
from hopeit_agents.mcp_client.models import (
    MCPClientConfig,
    ToolCallRecord,
    ToolCallRequestLog,
    ToolExecutionResult,
    ToolExecutionStatus,
)
from hopeit_agents.model_client.models import (
    CompletionConfig,
    CompletionRequest,
    CompletionResponse,
    Conversation,
    Message,
    Role,
    ToolCall,
    ToolFunctionCall,
)


@pytest.mark.asyncio
async def test_agent_loop_executes_tool_calls(monkeypatch: MonkeyPatch) -> None:
    """When the model returns tool calls, they are executed and logged."""

    initial_conversation = Conversation(
        conversation_id="conv-1",
        messages=[Message(role=Role.USER, content="help")],
    )

    tool_call = ToolCall(
        id="call-1",
        type="function",
        function=ToolFunctionCall(name="demo_tool", arguments='{"foo": "bar"}'),
    )

    assistant_message = Message(role=Role.ASSISTANT, content="", tool_calls=[tool_call])
    conversation_after_completion = initial_conversation.with_message(assistant_message)

    completion_response = CompletionResponse(
        response_id="resp-1",
        model="test-model",
        created_at=datetime.now(UTC),
        message=assistant_message,
        tool_calls=[tool_call],
        conversation=conversation_after_completion,
        usage=None,
        finish_reason="tool_calls",
    )

    generate_mock = AsyncMock(return_value=completion_response)
    monkeypatch.setattr(
        "hopeit_agents.agent_toolkit.app.steps.agent_loop.model_generate.generate",
        generate_mock,
    )

    tool_result = ToolExecutionResult(
        call_id="call-1",
        tool_name="demo_tool",
        status=ToolExecutionStatus.SUCCESS,
        structured_content={"status": "ok"},
        content=[{"type": "text", "text": "succeeded"}],
    )
    record = ToolCallRecord(
        request=ToolCallRequestLog(
            tool_call_id="call-1", tool_name="demo_tool", payload={"foo": "bar"}
        ),
        response=tool_result,
    )
    execute_mock = AsyncMock(return_value=[record])
    monkeypatch.setattr(agent_loop, "execute_tool_calls", execute_mock)

    payload = AgentLoopPayload(
        conversation=initial_conversation,
        completion_config=CompletionConfig(model="test-model"),
        loop_config=AgentLoopConfig(max_iterations=1),
        agent_settings=AgentSettings(enable_tools=True),
        mcp_settings=MCPClientConfig(command="demo"),
    )

    context = MagicMock()

    result = await agent_loop.agent_with_tools_loop(payload, context)

    generate_mock.assert_awaited_once()
    awaited_request, awaited_context = generate_mock.await_args_list[0].args
    assert isinstance(awaited_request, CompletionRequest)
    assert awaited_request.conversation == initial_conversation
    assert awaited_context is context

    execute_mock.assert_awaited_once()
    execute_kwargs: Mapping[str, Any] = execute_mock.await_args_list[0].kwargs
    assert execute_kwargs["session_id"] == conversation_after_completion.conversation_id
    assert execute_kwargs["tool_calls"][0].tool_name == "demo_tool"

    final_messages = result.conversation.messages
    assert len(final_messages) == 3
    assert final_messages[-1].role is Role.TOOL
    assert final_messages[-1].content == Payload.to_json(tool_result.structured_content, indent=2)
    assert final_messages[-1].tool_call_id == "call-1"
    assert result.tool_call_log == [record]


@pytest.mark.asyncio
async def test_agent_loop_returns_assistant_message(monkeypatch: MonkeyPatch) -> None:
    """When the model responds with text, the loop returns it as assistant message."""

    initial_conversation = Conversation(
        conversation_id="conv-42",
        messages=[Message(role=Role.USER, content="hello")],
    )

    completion_response = CompletionResponse(
        response_id="resp-2",
        model="test-model",
        created_at=datetime.now(UTC),
        message=Message(role=Role.ASSISTANT, content="Sure!"),
        tool_calls=[],
        conversation=initial_conversation,
        usage=None,
        finish_reason="stop",
    )

    generate_mock = AsyncMock(return_value=completion_response)
    monkeypatch.setattr(
        "hopeit_agents.agent_toolkit.app.steps.agent_loop.model_generate.generate",
        generate_mock,
    )

    execute_mock = AsyncMock()
    monkeypatch.setattr(agent_loop, "execute_tool_calls", execute_mock)

    payload = AgentLoopPayload(
        conversation=initial_conversation,
        completion_config=CompletionConfig(),
        loop_config=AgentLoopConfig(max_iterations=2),
        agent_settings=AgentSettings(enable_tools=True),
        mcp_settings=MCPClientConfig(),
    )

    context = MagicMock()

    result = await agent_loop.agent_with_tools_loop(payload, context)

    generate_mock.assert_awaited_once()
    execute_mock.assert_not_called()

    final_messages = result.conversation.messages
    assert len(final_messages) == 2
    assert final_messages[-1].role is Role.ASSISTANT
    assert final_messages[-1].content == "Sure!"
    assert result.tool_call_log == []


def test_format_tool_result_prefers_structured_content() -> None:
    """Structured content should be rendered before raw content."""

    result = ToolExecutionResult(
        call_id="call-structured",
        tool_name="demo",
        status=ToolExecutionStatus.SUCCESS,
        structured_content={"foo": "bar"},
        content=[{"type": "text", "text": "fallback"}],
    )

    formatted = agent_loop._format_tool_result(result)

    assert formatted == Payload.to_json(result.structured_content, indent=2)


def test_format_tool_result_falls_back_to_content() -> None:
    """When no structured content is present, fall back to raw content."""

    content_payload = [{"type": "text", "text": "value"}]
    result = ToolExecutionResult(
        call_id="call-content",
        tool_name="demo",
        status=ToolExecutionStatus.SUCCESS,
        structured_content=None,
        content=content_payload,
    )

    formatted = agent_loop._format_tool_result(result)

    assert formatted == Payload.to_json(content_payload, indent=2)
