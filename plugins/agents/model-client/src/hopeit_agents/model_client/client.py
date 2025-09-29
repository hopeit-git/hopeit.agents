"""Async client to call OpenAI-compatible chat completion endpoints."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientResponse

from hopeit_agents.model_client.models import (
    CompletionConfig,
    CompletionRequest,
    CompletionResponse,
    Conversation,
    Message,
    ToolCall,
    Usage,
    message_from_openai_dict,
    message_to_openai_dict,
    messages_from_tool_calls,
    tool_call_from_openai_dict,
)


@dataclass
class ModelClientError(RuntimeError):
    """Raised when the model client cannot complete the request."""

    status: int
    message: str
    details: Mapping[str, Any] | None = None

    def __str__(self) -> str:
        return f"ModelClientError(status={self.status}, message={self.message})"


class AsyncModelClient:
    """Minimal OpenAI-compatible async client."""

    def __init__(
        self,
        *,
        base_url: str,
        api_version: str | None,
        deployment_name: str | None,
        api_key: str | None,
        timeout_seconds: float,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._default_headers = dict(default_headers or {})
        self._api_version = api_version
        self._deployment_name = deployment_name

    def _build_url(self) -> str:
        """Return the chat completions endpoint URL including optional deployment params."""
        url = f"{self._base_url.strip('/')}/chat/completions"
        if self._deployment_name:
            url = url.replace("{DEPLOYMENT_NAME}", self._deployment_name)
        if self._api_version:
            url = url + f"?api-version={self._api_version}"
        return url

    async def complete(
        self,
        request: CompletionRequest,
        config: CompletionConfig,
    ) -> CompletionResponse:
        """Execute a completion call and normalize the response."""
        payload = self._build_payload(request.conversation, config)
        headers = self._build_headers()
        url = self._build_url()
        timeout = aiohttp.ClientTimeout(total=self._timeout_seconds)
        print()
        print("URL", url)
        print()

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                print()
                print("REQUEST", request)
                print()
                print("RESPONSE", await response.text())
                print()

                return await self._parse_response(request.conversation, response, config)

    def _build_headers(self) -> Mapping[str, str]:
        """Compose the HTTP headers required by the target provider."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["api-key"] = self._api_key
            headers["Authorization"] = f"Bearer {self._api_key}"
        headers.update(self._default_headers)
        return headers

    def _build_payload(
        self,
        conversation: Conversation,
        config: CompletionConfig,
    ) -> dict[str, Any]:
        """Convert the conversation and completion config into an OpenAI-compatible payload."""
        body: dict[str, Any] = {
            "model": config.model,
            "messages": [message_to_openai_dict(msg) for msg in conversation.messages],
        }

        # Standard optional params
        if config.temperature is not None:
            body["temperature"] = config.temperature
        if config.max_output_tokens is not None:
            body["max_tokens"] = config.max_output_tokens
        if config.response_format is not None:
            body["response_format"] = config.response_format

        # Tools payload (OpenAI requires tools to be present)
        tools_spec: list[dict[str, Any]] = []
        for tool in config.available_tools or []:
            tools_spec.append(tool.to_openai_dict())

        if tools_spec:
            body["tools"] = tools_spec
            # Only include tool_choice when tools are present
            if config.tool_choice is not None:
                body["tool_choice"] = config.tool_choice
            # Only include parallel_tool_calls when tools are present AND explicitly configured
            # (OpenAI rejects this param if tools are missing and may reject it for some models)
            if config.enable_tool_expansion is not None:
                body["parallel_tool_calls"] = bool(config.enable_tool_expansion)

        return body

    async def _parse_response(
        self,
        conversation: Conversation,
        response: ClientResponse,
        config: CompletionConfig,
    ) -> CompletionResponse:
        """Validate the HTTP response and map it to internal completion objects."""
        try:
            payload = await response.json()
        except ClientError as exc:  # pragma: no cover - network issues mapped once
            raise ModelClientError(status=500, message="Invalid JSON response") from exc

        if response.status >= 400:
            message = payload.get("error", {}).get("message") if isinstance(payload, dict) else None
            raise ModelClientError(
                status=response.status,
                message=message or "Model provider returned an error",
                details=payload if isinstance(payload, Mapping) else None,
            )

        if not isinstance(payload, Mapping):
            raise ModelClientError(
                status=response.status,
                message="Unexpected response payload type",
                details={"payload": payload},
            )

        choices = payload.get("choices")
        if not choices:
            raise ModelClientError(
                status=response.status,
                message="Missing choices in completion response",
                details=payload,
            )

        used_choice = {}
        message = Message.empty()
        updated_conversation = conversation
        for choice in choices:
            message_data = choice.get("message", {})
            message = message_from_openai_dict(message_data)
            used_choice = choice
            if message.content:
                updated_conversation = updated_conversation.with_message(message)
                break

        tool_calls_raw = message_data.get("tool_calls") or []
        tool_calls: list[ToolCall] = []
        if isinstance(tool_calls_raw, list) and len(tool_calls_raw):
            tool_calls = [
                tool_call_from_openai_dict(item, config.available_tools)
                for item in tool_calls_raw
                if isinstance(item, dict)
            ]
            for tool_call_msg in messages_from_tool_calls(tool_calls):
                updated_conversation = updated_conversation.with_message(tool_call_msg)

        usage_data = payload.get("usage")
        usage = None
        if isinstance(usage_data, Mapping):
            usage = Usage(
                prompt_tokens=int(usage_data.get("prompt_tokens", 0)),
                completion_tokens=int(usage_data.get("completion_tokens", 0)),
                total_tokens=int(usage_data.get("total_tokens", 0)),
            )

        created_raw = payload.get("created")
        created_at = (
            datetime.fromtimestamp(created_raw, tz=UTC)
            if isinstance(created_raw, (int, float))
            else datetime.now(UTC)
        )

        return CompletionResponse(
            response_id=str(payload.get("id", "")),
            model=str(payload.get("model", config.model or "")),
            created_at=created_at,
            message=message,
            tool_calls=tool_calls,
            conversation=updated_conversation,
            usage=usage,
            finish_reason=used_choice.get("finish_reason"),
        )
