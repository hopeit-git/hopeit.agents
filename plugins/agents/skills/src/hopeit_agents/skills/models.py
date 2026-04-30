"""Typed data objects for the MCP client plugin."""

from enum import StrEnum
from typing import Any

from hopeit.dataobjects import dataclass, dataobject, field


class SkillExecutionStatus(StrEnum):
    """Outcome of a skill invocation."""

    SUCCESS = "success"
    ERROR = "error"


@dataobject
@dataclass
class SkillDescriptor:
    """Definition for a skill the client can call."""

    name: str
    """The programmatic name of the entity."""
    title: str | None
    """Skill title."""
    description: str | None
    """A human-readable description of the skill."""
    input_schema: dict[str, Any]
    """A JSON Schema object defining the expected parameters for the skill."""
    output_schema: dict[str, Any] | None
    """
    An optional JSON Schema object defining the structure of the skill's output
    returned in the structuredContent field of a CallSkillResult.
    """

    def to_openai_dict(self) -> dict[str, Any]:
        """
        Convert this SkillDescriptor to an OpenAI skill definition dictionary.
        """
        skill_def: dict[str, Any] = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description or "",
                "parameters": self.input_schema,
            },
        }
        if self.title:
            skill_def["function"]["title"] = self.title
        if self.output_schema is not None:
            skill_def["function"]["response"] = {
                "type": "json_schema",
                "json_schema": self.output_schema,
            }
        return skill_def


@dataobject
@dataclass
class SkillInvocation:
    """Payload to invoke a skill."""

    skill_name: str
    payload: dict[str, Any] = field(default_factory=dict)
    call_id: str | None = None
    session_id: str | None = None


@dataobject
@dataclass
class SkillExecutionResult:
    """Result of calling a skill through MCP."""

    call_id: str
    skill_name: str
    status: SkillExecutionStatus
    content: list[dict[str, Any]] = field(default_factory=list)
    structured_content: dict[str, Any] | list[Any] | None = None
    error_message: str | None = None
    raw_result: dict[str, Any] | None = None
    session_id: str | None = None


@dataobject
@dataclass
class SkillCallRequestLog:
    """Captured request details for a skill call."""

    skill_call_id: str
    skill_name: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataobject
@dataclass
class SkillCallRecord:
    """Aggregated skill call request and response for logging/telemetry."""

    request: SkillCallRequestLog
    response: SkillExecutionResult


@dataobject
@dataclass
class SkillsSettings:
    skills_generation_path: str = "./_skills"
