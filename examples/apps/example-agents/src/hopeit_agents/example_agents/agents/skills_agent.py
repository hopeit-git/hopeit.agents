"""Main agent event that coordinates the skill-enabled agent loop."""

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit_agents.agent_toolkit.agents.agent_config import create_agent_config
from hopeit_agents.agent_toolkit.agents.prompts import render_prompt
from hopeit_agents.agent_toolkit.app.steps.agent_skills_loop import (
    AgentLoopConfig,
    AgentLoopPayload,
    AgentLoopResult,
    agent_with_skills_loop,
)
from hopeit_agents.agent_toolkit.settings import AgentSettings
from hopeit_agents.agent_toolkit.skills.agent_skills import (
    resolve_skills,
    skill_descriptions,
)
from hopeit_agents.example_agents.models import AgentRequest, SkillsAgentResponse
from hopeit_agents.model_client.conversation import build_conversation
from hopeit_agents.model_client.models import CompletionConfig
from hopeit_agents.skills.models import SkillsSettings

logger, extra = app_extra_logger()


__steps__ = ["init_conversation", agent_with_skills_loop.__name__, "result"]


__api__ = event_api(
    summary="example-agents: skills agent",
    payload=(AgentRequest, "Agent task description"),
    responses={200: (SkillsAgentResponse, "Aggregated agent response")},
)


async def init_conversation(payload: AgentRequest, context: EventContext) -> AgentLoopPayload:
    """Build the initial conversation and skill prompt for the main agent."""
    agent_settings: AgentSettings = context.settings(key="skills_agent_llm", datatype=AgentSettings)
    skills_settings: SkillsSettings = context.settings(key="skills", datatype=SkillsSettings)
    assert agent_settings.system_prompt_template, "missing system_prompt_template"
    assert agent_settings.tool_prompt_template, "missing tool_prompt_template"

    with open(agent_settings.system_prompt_template) as f:
        system_prompt_template = f.read()
    with open(agent_settings.tool_prompt_template) as f:
        tool_prompt_template = f.read()

    agent_config = create_agent_config(
        name=agent_settings.agent_name,
        prompt_template=system_prompt_template,
        variables={},
        enable_tools=True,
        tools=agent_settings.allowed_tools,
        tool_prompt_template=tool_prompt_template,
    )
    tools = await resolve_skills(
        context,
        agent_id=agent_config.key,
        allowed_skills=agent_config.tools,
    )
    completion_config = CompletionConfig(available_skills=tools)
    conversation = build_conversation(
        existing=None,
        message=payload.user_message,
        system_prompt=render_prompt(
            agent_config,
            {
                "tool_descriptions": skill_descriptions(
                    tools, include_schemas=agent_settings.include_tool_schemas_in_prompt
                )
            },
            include_tools=agent_config.enable_tools,
        ),
    )
    return AgentLoopPayload(
        conversation=conversation,
        user_context={},
        completion_config=completion_config,
        loop_config=AgentLoopConfig(max_iterations=3),
        agent_settings=agent_settings,
        skills_settings=skills_settings,
    )


async def result(payload: AgentLoopResult, context: EventContext) -> SkillsAgentResponse:
    """Wrap the final loop message and skill call log into a response object."""
    last_message = payload.conversation.messages[-1]
    response = SkillsAgentResponse(
        conversation=payload.conversation,
        assistant_message=last_message,
        skill_calls=payload.tool_call_log,
    )
    return response
