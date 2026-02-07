from __future__ import annotations

from typing import Any

from ..errors import ProviderError
from .base import Provider, ProviderRequest, ProviderResponse


class MockProvider(Provider):
    def __init__(
        self,
        responses: dict[str, str] | None = None,
        *,
        default_output: str | None = None,
        strict: bool = True,
    ) -> None:
        self._responses = dict(responses or {})
        self._default_output = default_output
        self._strict = strict

    def call(self, request: ProviderRequest) -> ProviderResponse:
        key = _request_key(request)
        if key in self._responses:
            output = self._responses[key]
        elif self._default_output is not None:
            output = self._default_output
        elif self._strict:
            raise ProviderError(f"mock provider has no response for key: {key}")
        else:
            output = ""

        return ProviderResponse(
            model=request.model,
            output_text=output,
            raw={"mock_key": key},
        )


def _request_key(request: ProviderRequest) -> str:
    if request.prompt is not None:
        return f"prompt:{request.prompt}"

    messages = request.messages or []
    parts: list[str] = []
    for message in messages:
        chunk = f"{message.role}|{message.content}"
        if message.name:
            chunk = f"{chunk}|name={message.name}"
        if message.tool_call_id:
            chunk = f"{chunk}|tool={message.tool_call_id}"
        parts.append(chunk)

    joined = "\n".join(parts)
    return f"messages:{joined}"
