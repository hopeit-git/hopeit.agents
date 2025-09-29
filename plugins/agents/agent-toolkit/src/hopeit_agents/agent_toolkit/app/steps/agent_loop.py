"""Hopeit event step that runs an agent loop capable of executing MCP tools."""

from typing import Any

from hopeit.app.context import EventContext
from hopeit.dataobjects import dataclass, dataobject
from hopeit.dataobjects.payload import Payload

from hopeit_agents.agent_toolkit.mcp.agent_tools import (
    execute_tool_calls,
)
from hopeit_agents.agent_toolkit.settings import AgentSettings
from hopeit_agents.mcp_client.models import (
    MCPClientConfig,
    ToolCallRecord,
    ToolExecutionResult,
    ToolInvocation,
)
from hopeit_agents.model_client.api import generate as model_generate
from hopeit_agents.model_client.client import ModelClientError
from hopeit_agents.model_client.models import (
    CompletionConfig,
    CompletionRequest,
    Conversation,
    Message,
    Role,
)


@dataobject
@dataclass
class AgentLoopConfig:
    """Configuration describing how many iterations the loop can run."""

    max_iterations: int


@dataobject
@dataclass
class AgentLoopPayload:
    """Input payload required to run the agent loop."""

    conversation: Conversation
    completion_config: CompletionConfig
    loop_config: AgentLoopConfig
    agent_settings: AgentSettings
    mcp_settings: MCPClientConfig


@dataobject
@dataclass
class AgentLoopResult:
    """Outcome of the agent loop including the final conversation and tool log."""

    conversation: Conversation
    tool_call_log: list[ToolCallRecord]


async def agent_with_tools_loop(
    payload: AgentLoopPayload, context: EventContext
) -> AgentLoopResult:
    """Execute the agent reasoning loop using an LLM with optional tool calls.

    The loop keeps requesting completions from the model until it either produces
    a final assistant message or reaches the configured maximum number of
    iterations. When the model returns tool calls and tools are enabled, the
    calls are executed using the MCP client and the results appended to the
    conversation, allowing the model to observe tool responses in subsequent
    turns.

    Args:
        payload: Aggregated configuration, conversation state, and MCP settings.
        context: Hopeit event context used to execute the model and tools.

    Returns:
        AgentLoopResult containing the updated conversation and executed tool log.
    """

    conversation = payload.conversation
    completion_config = payload.completion_config
    loop_config = payload.loop_config
    agent_settings = payload.agent_settings
    mcp_settings = payload.mcp_settings

    tool_call_log: list[ToolCallRecord] = []

    for n_turn in range(0, loop_config.max_iterations):
        model_request = CompletionRequest(conversation=conversation, config=completion_config)

        try:
            completion = await model_generate.generate(model_request, context)
            conversation = completion.conversation

            print("===========================================================")
            print(n_turn, len(conversation.messages))
            print("\n".join(f"{x.role}: {x.content}" for x in conversation.messages))
            print("===========================================================")

            if agent_settings.enable_tools and completion.tool_calls:
                tool_call_records = await execute_tool_calls(
                    mcp_settings,
                    context,
                    tool_calls=[
                        ToolInvocation(
                            tool_name=tc.function.name,
                            payload=Payload.from_json(
                                tc.function.arguments, datatype=dict[str, Any]
                            ),
                            call_id=tc.id,
                            session_id=conversation.conversation_id,  # TODO: session_id?
                        )
                        for tc in completion.tool_calls
                    ],
                    session_id=conversation.conversation_id,  # TODO: session_id?
                )

                for record in tool_call_records:
                    conversation = conversation.with_message(
                        Message(
                            role=Role.TOOL,
                            content=_format_tool_result(record.response),
                            tool_call_id=record.request.tool_call_id,
                            name=record.request.tool_name,
                        ),
                    )

                tool_call_log.extend(tool_call_records)

            elif not completion.message.content:
                # Keep going if last assistant message is empty
                continue
            else:
                # Finish tool call loop an return assistant response
                conversation = conversation.with_message(
                    Message(role=Role.ASSISTANT, content=completion.message.content or "")
                )
                break

        # In case of error, usually parsing LLM response, keep looping to fix it
        except ModelClientError as e:
            conversation = conversation.with_message(
                Message(role=Role.SYSTEM, content=f"Error parsing response: {e}")
            )
    # end loop
    return AgentLoopResult(conversation=conversation, tool_call_log=tool_call_log)


def _format_tool_result(result: ToolExecutionResult) -> str:
    """Return a JSON-formatted string for tool execution results."""

    if result.structured_content is not None:
        return Payload.to_json(result.structured_content, indent=2)
    return Payload.to_json(result.content, indent=2)
