from typing import Any

from hopeit.app.context import EventContext
from hopeit.dataobjects import dataclass, dataobject
from hopeit.dataobjects.payload import Payload

from hopeit_agents.agent_toolkit.mcp.agent_tools import (
    execute_tool_calls,
)
from hopeit_agents.agent_toolkit.settings import AgentSettings
from hopeit_agents.mcp_client.models import (
    BridgeConfig,
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
    max_iterations: int


@dataobject
@dataclass
class AgentLoopPayload:
    conversation: Conversation
    completion_config: CompletionConfig
    loop_config: AgentLoopConfig
    agent_settings: AgentSettings
    mcp_settings: BridgeConfig


@dataobject
@dataclass
class AgentLoopResult:
    conversation: Conversation
    tool_call_log: list[ToolCallRecord]


async def agent_with_tools_loop(
    payload: AgentLoopPayload, context: EventContext
) -> AgentLoopResult:
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
    if result.structured_content is not None:
        return Payload.to_json(result.structured_content, indent=2)
    return Payload.to_json(result.content, indent=2)
