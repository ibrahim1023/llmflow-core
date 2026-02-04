from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError, field_validator, model_validator

from .errors import WorkflowLoadError, WorkflowValidationError
from .hashing import sha256_text


class WorkflowMeta(BaseModel):
    name: str
    version: str

    @field_validator("name", "version")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = str(value).strip()
        if not value:
            raise ValueError("must be non-empty")
        return value


class InputDef(BaseModel):
    type: str

    @field_validator("type")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = str(value).strip()
        if not value:
            raise ValueError("must be non-empty")
        return value


class StepLLMConfig(BaseModel):
    model_config = {"extra": "allow"}


class StepDef(BaseModel):
    id: str
    type: str
    depends_on: list[str] = []
    prompt: str | None = None
    output_schema: str | None = None
    llm: StepLLMConfig | None = None

    @field_validator("id", "type")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = str(value).strip()
        if not value:
            raise ValueError("must be non-empty")
        return value

    @field_validator("depends_on", mode="before")
    @classmethod
    def _ensure_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        raise ValueError("must be a list of step ids")

    @model_validator(mode="after")
    def _validate_llm_fields(self) -> "StepDef":
        if self.type == "llm":
            if not self.prompt:
                raise ValueError("llm steps require 'prompt'")
            if not self.output_schema:
                raise ValueError("llm steps require 'output_schema'")
        return self


class WorkflowSpec(BaseModel):
    workflow: WorkflowMeta
    inputs: dict[str, InputDef]
    steps: list[StepDef]
    outputs: dict[str, str]

    @model_validator(mode="after")
    def _validate_references(self) -> "WorkflowSpec":
        step_ids = [step.id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("step ids must be unique")

        step_id_set = set(step_ids)
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in step_id_set:
                    raise ValueError(
                        f"unknown dependency '{dep}' in step '{step.id}'")

        for output_name, step_id in self.outputs.items():
            if step_id not in step_id_set:
                raise ValueError(
                    f"output '{output_name}' references unknown step '{step_id}'")

        return self


@dataclass(frozen=True)
class Workflow:
    spec: WorkflowSpec
    path: Path
    workflow_hash: str

    @classmethod
    def load(cls, path: str | Path) -> "Workflow":
        workflow_path = Path(path)
        if not workflow_path.exists():
            raise WorkflowLoadError(
                f"workflow file not found: {workflow_path}")

        try:
            raw_text = workflow_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise WorkflowLoadError(
                f"failed to read workflow file: {workflow_path}") from exc

        try:
            payload = yaml.safe_load(raw_text)
        except yaml.YAMLError as exc:
            raise WorkflowLoadError(
                f"invalid YAML in workflow file: {workflow_path}") from exc

        if not isinstance(payload, dict):
            raise WorkflowValidationError(
                "workflow YAML must be a mapping at the top level")

        resolved_payload = _resolve_prompt_paths(payload, workflow_path.parent)

        try:
            spec = WorkflowSpec.model_validate(resolved_payload)
        except ValidationError as exc:
            raise WorkflowValidationError(
                _format_validation_error(exc)) from exc

        return cls(
            spec=spec,
            path=workflow_path,
            workflow_hash=sha256_text(raw_text),
        )


def _resolve_prompt_paths(payload: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    steps = payload.get("steps")
    if not isinstance(steps, list):
        return payload

    normalized = dict(payload)
    normalized_steps: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            normalized_steps.append(step)
            continue

        updated = dict(step)
        prompt = updated.get("prompt")
        if isinstance(prompt, str):
            updated["prompt"] = _resolve_path(prompt, base_dir)

        output_schema = updated.get("output_schema")
        if isinstance(output_schema, str):
            updated["output_schema"] = _resolve_path(output_schema, base_dir)

        normalized_steps.append(updated)

    normalized["steps"] = normalized_steps
    return normalized


def _resolve_path(value: str, base_dir: Path) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = base_dir / path
    return str(path.resolve())


def _format_validation_error(error: ValidationError) -> str:
    lines = ["Workflow validation failed:"]
    for detail in error.errors():
        loc = ".".join(str(item) for item in detail.get("loc", []))
        msg = detail.get("msg", "invalid value")
        if loc:
            lines.append(f"- {loc}: {msg}")
        else:
            lines.append(f"- {msg}")
    return "\n".join(lines)
