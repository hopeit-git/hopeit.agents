"""Helpers to build chat conversations for model completion requests."""

from __future__ import annotations

import uuid

from hopeit_agents.model_client.models import Conversation, Message, Role

__all__ = ["build_conversation"]


def build_conversation(
    existing: Conversation | None,
    *,
    message: str,
    role: Role = Role.USER,
    system_prompt: str | None = None,
    tool_prompt: str | None = None,
) -> Conversation:
    """Return a conversation ensuring optional system and user prompts are present."""
    base_messages = list(existing.messages) if existing else []

    system_parts = []
    if system_prompt:
        system_parts.append(system_prompt.strip())
    if tool_prompt:
        system_parts.append(tool_prompt)
    if system_parts:
        content = "\n\n".join(part for part in system_parts if part)
        if not base_messages or base_messages[0].content != content:
            # Creates or updates system prompt
            base_messages.append(
                Message(
                    role=Role.SYSTEM,
                    content=content,
                )
            )

    base_messages.append(Message(role=role, content=message))
    return Conversation(
        conversation_id=existing.conversation_id if existing else str(uuid.uuid4()),
        messages=base_messages,
    )
