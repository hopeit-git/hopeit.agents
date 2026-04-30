"""Utilities to help agents describe and invoke MCP skills."""

from __future__ import annotations

import json
import uuid
from typing import Any

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit_agents.skills import registry, runner
from hopeit_agents.skills.api import SkillEventInfo
from hopeit_agents.skills.models import (
    SkillCallRecord,
    SkillCallRequestLog,
    SkillExecutionResult,
    SkillExecutionStatus,
    SkillInvocation,
    SkillsSettings,
)

logger, extra = app_extra_logger()


async def resolve_skills(
    context: EventContext,
    *,
    agent_id: str,
    allowed_skills: list[str] | None = None,
) -> list[SkillEventInfo]:
    """Return a skill-aware prompt based on the MCP skill inventory."""
    skills = registry.list_skills()
    if allowed_skills:
        return [skill for skill in skills if skill.skill_name in allowed_skills]
    return skills


def skill_descriptions(
    skills: list[SkillEventInfo],
    *,
    include_schemas: bool,
) -> str:
    """Render skill metadata as bullet points for LLM consumption."""
    lines: list[str] = []
    lines.append("\nAvailable skills:")
    for skill in skills:
        description = (skill.description or "No description provided.").strip()
        lines.append(f"- {skill.skill_name}: {description}")
        if include_schemas and skill.input_schema:
            schema = json.dumps(skill.input_schema, indent=2, sort_keys=True)
            lines.append("  JSON schema:")
            lines.extend(f"    {schema_line}" for schema_line in schema.splitlines())
    return "\n".join(lines).strip()


async def call_skill(
    config: SkillsSettings,
    context: EventContext,
    *,
    call_id: str,
    skill_name: str,
    payload: dict[str, Any],
    session_id: str | None = None,
) -> SkillExecutionResult:
    """Execute a skill through the skills plugin runner using the provided payload."""
    skill = registry.find_skill(skill_name)
    if skill is None:
        logger.error(
            context,
            "call_skill_error",
            extra=extra(skill_name=skill_name),
        )
        raise RuntimeError(f"Skill not found: {skill_name}")

    result = await runner.execute_skill(skill, payload, context)
    return SkillExecutionResult(
        call_id=call_id,
        skill_name=skill_name,
        status=SkillExecutionStatus.SUCCESS,
        content=list(result) if isinstance(result, (list, set)) else [result],
        structured_content=list(result) if isinstance(result, (list, set)) else result,
    )


async def execute_skill_calls(
    config: SkillsSettings,
    context: EventContext,
    *,
    skill_calls: list[SkillInvocation],
    session_id: str | None = None,
) -> list[SkillCallRecord]:
    """Execute multiple skill calls capturing request and response data."""
    records: list[SkillCallRecord] = []
    for skill_call in skill_calls:
        result = await call_skill(
            config,
            context,
            call_id=skill_call.call_id or f"call_{uuid.uuid4().hex[-10:]}",
            skill_name=skill_call.skill_name,
            payload=skill_call.payload,
            session_id=session_id,
        )
        request_log = SkillCallRequestLog(
            skill_call_id=result.call_id,
            skill_name=skill_call.skill_name,
            payload=skill_call.payload,
        )
        records.append(SkillCallRecord(request=request_log, response=result))
    return records
