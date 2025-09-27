"""Sum two numbers tool event."""

from typing import Any

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.dataobjects.payload import Payload

from hopeit_agents.example_agents.models import (
    ExpertAgentRequest,
    ExpertAgentResponse,
    ExpertAgentResults,
)
from hopeit_agents.example_agents.settings import AgentSettings
from hopeit_agents.mcp_client.agent_tooling import (
    ToolCallRecord,
)
from hopeit_agents.mcp_client.agent_tooling import (
    execute_tool_calls as bridge_execute_tool_calls,
)
from hopeit_agents.mcp_client.agent_tooling import (
    resolve_tool_prompt as bridge_resolve_tool_prompt,
)
from hopeit_agents.mcp_client.models import BridgeConfig, ToolExecutionResult, ToolInvocation
from hopeit_agents.mcp_server.tools.api import _datatype_schema, event_tool_api
from hopeit_agents.model_client.api import generate as model_generate
from hopeit_agents.model_client.client import ModelClientError
from hopeit_agents.model_client.conversation import build_conversation
from hopeit_agents.model_client.models import CompletionConfig, CompletionRequest, Message, Role

logger, extra = app_extra_logger()

__steps__ = ["run_agent"]

__api__ = event_api(
    summary="example-agents: expert agent",
    payload=(ExpertAgentRequest, "Agent task description"),
    responses={200: (ExpertAgentResponse, "Aggregated agent response")},
)

__mcp__ = event_tool_api(
    summary="example-agents: expert agent",
    payload=(ExpertAgentRequest, "Agent task description"),
    response=(ExpertAgentResponse, "Aggregated agent response"),
)


async def run_agent(payload: ExpertAgentRequest, context: EventContext) -> ExpertAgentResponse:
    """Execute the agent loop: model completion, optional tool calls."""
    agent_settings = context.settings(key="expert_agent_llm", datatype=AgentSettings)
    mcp_settings = context.settings(key="mcp_client_example_tools", datatype=BridgeConfig)
    tool_prompt, tools = await bridge_resolve_tool_prompt(
        mcp_settings,
        context,
        agent_id=payload.agent_id,
        enable_tools=agent_settings.enable_tools,
        template=agent_settings.tool_prompt_template,
        include_schemas=agent_settings.include_tool_schemas_in_prompt,
    )
    completion_config = CompletionConfig(available_tools=tools)
    result_schema = _datatype_schema("", ExpertAgentResults)
    conversation = build_conversation(
        None,
        user_message=payload.user_message,
        system_prompt=agent_settings.system_prompt.replace(
            "{expert-agent-results-schema}",
            "```" + Payload.to_json(result_schema, indent=2) + "```",
        ),
        tool_prompt=tool_prompt,
    )

    tool_call_log: list[ToolCallRecord] = []

    for n_turn in range(0, 10):
        model_request = CompletionRequest(conversation=conversation, config=completion_config)

        try:
            completion = await model_generate.generate(model_request, context)
            conversation = completion.conversation

            print("===========================================================")
            print(n_turn, len(conversation.messages))
            print("\n".join(f"{x.role}: {x.content}" for x in conversation.messages))
            print("===========================================================")

            if agent_settings.enable_tools and completion.tool_calls:
                tool_call_records = await bridge_execute_tool_calls(
                    mcp_settings,
                    context,
                    tool_calls=[
                        ToolInvocation(
                            tool_name=tc.function.name,
                            payload=Payload.from_json(
                                tc.function.arguments, datatype=dict[str, Any]
                            ),
                            call_id=tc.id,
                            session_id=payload.agent_id,  # TODO: session_id?
                        )
                        for tc in completion.tool_calls
                    ],
                    session_id=payload.agent_id,  # TODO: session_id?
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
                # Finish tool call loop an return response
                break

        # In case of error, usually parsing LLM response, keep looping to fix it
        except ModelClientError as e:
            conversation = conversation.with_message(
                Message(role=Role.SYSTEM, content=f"Error parsing response: {e}")
            )
    # end loop

    try:
        response = ExpertAgentResponse(
            agent_id=payload.agent_id,
            results=Payload.from_json(
                completion.message.content or "", datatype=ExpertAgentResults
            ),
            tool_calls=tool_call_log,
        )
    except Exception as e:
        response = ExpertAgentResponse(
            agent_id=payload.agent_id,
            results=None,
            error=str(e),
            assistant_message=completion.message,
            tool_calls=tool_call_log,
        )

    logger.info(
        context,
        "agent_run_completed",
        extra=extra(
            agent_id=payload.agent_id,
            tool_call_count=len(tool_call_log),
            tool_calls=[
                {
                    "tool_call_id": record.request.tool_call_id,
                    "tool_name": record.request.tool_name,
                    "status": record.response.status.value,
                }
                for record in tool_call_log
            ],
            finish_reason=completion.finish_reason,
        ),
    )
    return response


def _format_tool_result(result: ToolExecutionResult) -> str:
    if result.structured_content is not None:
        return Payload.to_json(result.structured_content, indent=2)
    return Payload.to_json(result.content, indent=2)
