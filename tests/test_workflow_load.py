from __future__ import annotations

from pathlib import Path

import pytest

from llmflow import Workflow
from llmflow.errors import WorkflowLoadError, WorkflowValidationError
from llmflow.hashing import sha256_text


def _write_workflow(
    path: Path,
    *,
    prompt_path: str = "prompts/outline.md",
    schema_path: str = "schemas/outline.json",
) -> str:
    content = f"""
workflow:
  name: demo
  version: "1.0"

inputs:
  topic:
    type: string

steps:
  - id: outline
    type: llm
    prompt: {prompt_path}
    output_schema: {schema_path}
    llm:
      temperature: 0

outputs:
  article: outline
"""
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return content.strip() + "\n"


def test_workflow_load_happy_path(tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.yaml"
    prompt_path = tmp_path / "prompts" / "outline.md"
    schema_path = tmp_path / "schemas" / "outline.json"
    prompt_path.parent.mkdir(parents=True)
    schema_path.parent.mkdir(parents=True)
    prompt_path.write_text("Prompt", encoding="utf-8")
    schema_path.write_text("{}", encoding="utf-8")

    raw = _write_workflow(workflow_path)

    workflow = Workflow.load(workflow_path)

    assert workflow.spec.workflow.name == "demo"
    assert workflow.spec.steps[0].prompt == str(prompt_path.resolve())
    assert workflow.spec.steps[0].output_schema == str(schema_path.resolve())
    assert workflow.workflow_hash == sha256_text(raw)


def test_workflow_load_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.yaml"
    with pytest.raises(WorkflowLoadError):
        Workflow.load(missing_path)


def test_workflow_load_invalid_yaml(tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.yaml"
    workflow_path.write_text("workflow: [", encoding="utf-8")
    with pytest.raises(WorkflowLoadError):
        Workflow.load(workflow_path)


def test_workflow_load_validation_error(tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.yaml"
    workflow_path.write_text(
        """
workflow:
  name: demo
  version: "1.0"

inputs:
  topic:
    type: string

steps:
  - id: outline
    type: llm
    prompt: prompts/outline.md
    output_schema: schemas/outline.json
  - id: outline
    type: llm
    prompt: prompts/outline.md
    output_schema: schemas/outline.json

outputs:
  article: outline
""".strip()
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(WorkflowValidationError):
        Workflow.load(workflow_path)
