from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ProviderMessage(BaseModel):
    model_config = {"extra": "forbid"}

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None
    tool_call_id: str | None = None

    @field_validator("content")
    @classmethod
    def _non_empty_content(cls, value: str) -> str:
        value = str(value).strip()
        if not value:
            raise ValueError("content must be non-empty")
        return value


class ProviderUsage(BaseModel):
    model_config = {"extra": "forbid"}

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class ProviderRequest(BaseModel):
    model_config = {"extra": "forbid"}

    model: str
    prompt: str | None = None
    messages: list[ProviderMessage] | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    seed: int | None = None
    temperature: float | None = None
    max_tokens: int | None = None

    @field_validator("model")
    @classmethod
    def _non_empty_model(cls, value: str) -> str:
        value = str(value).strip()
        if not value:
            raise ValueError("model must be non-empty")
        return value

    @field_validator("prompt")
    @classmethod
    def _non_empty_prompt(cls, value: str | None) -> str | None:
        if value is None:
            return value
        trimmed = str(value).strip()
        if not trimmed:
            raise ValueError("prompt must be non-empty when provided")
        return trimmed

    @model_validator(mode="after")
    def _require_prompt_or_messages(self) -> "ProviderRequest":
        if self.prompt and self.messages:
            raise ValueError("provide either prompt or messages, not both")
        if not self.prompt and not self.messages:
            raise ValueError("prompt or messages must be provided")
        return self


class ProviderResponse(BaseModel):
    model_config = {"extra": "forbid"}

    model: str
    output_text: str
    finish_reason: str | None = None
    usage: ProviderUsage | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("model", "output_text")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = str(value).strip()
        if not value:
            raise ValueError("must be non-empty")
        return value


class Provider(ABC):
    @abstractmethod
    def call(self, request: ProviderRequest) -> ProviderResponse:
        """Execute the provider call and return a normalized response."""
