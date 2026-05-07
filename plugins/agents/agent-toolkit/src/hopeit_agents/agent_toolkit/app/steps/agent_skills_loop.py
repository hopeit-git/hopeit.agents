"""Hopeit event step that runs an agent loop capable of executing skills."""

from typing import Any

from hopeit.app.context import EventContext
from hopeit.dataobjects import dataclass, dataobject, field
from hopeit.dataobjects.payload import Payload

from hopeit_agents.agent_toolkit.settings import AgentSettings
from hopeit_agents.agent_toolkit.skills.agent_skills import execute_skill_calls
from hopeit_agents.model_client.api import generate as model_generate
from hopeit_agents.model_client.client import ModelClientError
from hopeit_agents.model_client.models import (
    CompletionConfig,
    CompletionRequest,
    Conversation,
    Message,
    Role,
)
from hopeit_agents.skills.models import (
    SkillCallRecord,
    SkillExecutionResult,
    SkillInvocation,
    SkillsSettings,
)


@dataobject
@dataclass
class AgentLoopConfig:
    """Configuration on how the loop can run."""

    max_iterations: int
    append_last_assistant_message: bool = False


@dataobject
@dataclass
class AgentLoopPayload:
    """Input payload required to run the agent loop."""

    conversation: Conversation
    user_context: dict[str, Any]
    completion_config: CompletionConfig
    loop_config: AgentLoopConfig
    agent_settings: AgentSettings
    skills_settings: SkillsSettings
    metadata: dict[str, str] = field(default_factory=dict)


@dataobject
@dataclass
class AgentLoopResult:
    """Outcome of the agent loop including the final conversation and skill log."""

    conversation: Conversation
    user_context: dict[str, Any]
    tool_call_log: list[SkillCallRecord]
    metadata: dict[str, str] = field(default_factory=dict)


async def agent_with_skills_loop(
    payload: AgentLoopPayload, context: EventContext
) -> AgentLoopResult:
    """Execute the agent reasoning loop using an LLM with optional skill calls.

    The loop keeps requesting completions from the model until it either produces
    a final assistant message or reaches the configured maximum number of
    iterations. When the model returns skill calls and skills are enabled, the
    calls are executed using the skills client and the results appended to the
    conversation, allowing the model to observe skill responses in subsequent
    turns.

    Args:
        payload: Aggregated configuration, conversation state, and skills settings.
        context: Hopeit event context used to execute the model and skills.

    Returns:
        AgentLoopResult containing the updated conversation and executed skill log.
    """

    conversation = payload.conversation
    completion_config = payload.completion_config
    loop_config = payload.loop_config
    agent_settings = payload.agent_settings
    skills_settings = payload.skills_settings

    tool_call_log: list[SkillCallRecord] = []

    for _ in range(0, loop_config.max_iterations):
        model_request = CompletionRequest(conversation=conversation, config=completion_config)

        try:
            completion = await model_generate.generate(model_request, context)
            conversation = completion.conversation

            if agent_settings.enable_tools and completion.tool_calls:
                tool_call_records = await execute_skill_calls(
                    skills_settings,
                    context,
                    skill_calls=[
                        SkillInvocation(
                            skill_name=tc.function.name,
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
                            tool_call_id=record.request.skill_call_id,
                            name=record.request.skill_name,
                        ),
                    )

                tool_call_log.extend(tool_call_records)

            elif not completion.message.content:
                # Keep going if last assistant message is empty
                continue
            else:
                if payload.loop_config.append_last_assistant_message:
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
    return AgentLoopResult(
        conversation=conversation,
        user_context=payload.user_context,
        tool_call_log=tool_call_log,
        metadata=payload.metadata,
    )


def _format_tool_result(result: SkillExecutionResult) -> str:
    """Return a JSON-formatted string for skill execution results."""

    if result.structured_content is not None:
        return Payload.to_json(result.structured_content, indent=2)
    return Payload.to_json(result.content, indent=2)
