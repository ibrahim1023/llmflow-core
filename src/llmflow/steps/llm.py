from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateError
from jsonschema import Draft7Validator, ValidationError as JsonSchemaError

from ..errors import (
    LLMConfigError,
    LLMOutputSchemaError,
    LLMOutputValidationError,
    LLMRenderError,
)
from ..providers import Provider, ProviderRequest
from ..workflow import StepDef
from .base import Step


class LLMStep(Step):
    def __init__(self, definition: StepDef, *, provider: Provider) -> None:
        super().__init__(definition)
        self._provider = provider
        self._prompt_path = _require_path(definition.prompt, "prompt")
        self._schema_path = _require_path(definition.output_schema, "output_schema")
        self._llm_config = _load_llm_config(definition)

    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        rendered_prompt = _render_prompt(self._prompt_path, inputs)
        request = _build_request(rendered_prompt, self._llm_config)
        response = self._provider.call(request)
        output = _parse_output(response.output_text)
        _validate_output(self._schema_path, output)
        return output


def _require_path(value: str | None, label: str) -> Path:
    if not value:
        raise LLMConfigError(f"llm step requires '{label}'")
    return Path(value)


def _load_llm_config(definition: StepDef) -> dict[str, Any]:
    if definition.llm is None:
        return {}
    return definition.llm.model_dump()


def _render_prompt(prompt_path: Path, inputs: dict[str, Any]) -> str:
    try:
        template_text = prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LLMRenderError(
            f"failed to read prompt file: {prompt_path}") from exc

    env = Environment(undefined=StrictUndefined)
    try:
        template = env.from_string(template_text)
        return template.render(inputs=inputs)
    except TemplateError as exc:
        raise LLMRenderError(
            f"failed to render prompt '{prompt_path}': {exc}") from exc


def _build_request(rendered_prompt: str, config: dict[str, Any]) -> ProviderRequest:
    model = config.pop("model", None)
    if not model:
        raise LLMConfigError("llm config requires 'model'")

    parameters = config.pop("parameters", {})
    if parameters is None:
        parameters = {}
    if not isinstance(parameters, dict):
        raise LLMConfigError("llm config 'parameters' must be a mapping")

    temperature = config.pop("temperature", None)
    max_tokens = config.pop("max_tokens", None)
    seed = config.pop("seed", None)

    if config:
        parameters = {**parameters, **config}

    return ProviderRequest(
        model=model,
        prompt=rendered_prompt,
        parameters=parameters,
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
    )


def _parse_output(output_text: str) -> dict[str, Any]:
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise LLMOutputValidationError(
            f"llm output is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise LLMOutputValidationError("llm output must be a JSON object")

    return payload


def _validate_output(schema_path: Path, output: dict[str, Any]) -> None:
    try:
        schema_text = schema_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LLMOutputSchemaError(
            f"failed to read output schema: {schema_path}") from exc

    try:
        schema = json.loads(schema_text)
    except json.JSONDecodeError as exc:
        raise LLMOutputSchemaError(
            f"output schema is not valid JSON: {schema_path}") from exc

    try:
        Draft7Validator(schema).validate(output)
    except JsonSchemaError as exc:
        raise LLMOutputValidationError(
            f"llm output failed schema validation: {exc.message}") from exc
