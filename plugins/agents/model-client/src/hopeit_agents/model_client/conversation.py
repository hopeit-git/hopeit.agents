"""Helpers to build chat conversations for model completion requests."""

from __future__ import annotations

import uuid

from hopeit_agents.model_client.models import Conversation, Message, Role

__all__ = ["build_conversation"]


def build_conversation(
    existing: Conversation | None,
    *,
    user_message: str,
    system_prompt: str | None = None,
    tool_prompt: str | None = None,
) -> Conversation:
    """Return a conversation ensuring optional system and user prompts are present."""
    base_messages = list(existing.messages) if existing else []
    if not base_messages:
        system_parts = []
        if system_prompt:
            system_parts.append(system_prompt.strip())
        if tool_prompt:
            system_parts.append(tool_prompt)
        if system_parts:
            base_messages.append(
                Message(
                    role=Role.SYSTEM,
                    content="\n\n".join(part for part in system_parts if part),
                )
            )

    base_messages.append(Message(role=Role.USER, content=user_message))
    return Conversation(
        conversation_id=existing.conversation_id if existing else str(uuid.uuid4()),
        messages=base_messages,
    )
