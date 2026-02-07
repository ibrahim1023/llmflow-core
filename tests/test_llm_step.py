import json

import pytest

from llmflow.errors import LLMOutputValidationError, LLMRenderError
from llmflow.providers import MockProvider
from llmflow.steps import LLMStep
from llmflow.workflow import StepDef


def test_llm_step_render_failure(tmp_path) -> None:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("Hello {{ inputs.topic }}", encoding="utf-8")

    schema_path = tmp_path / "schema.json"
    schema_path.write_text("{}", encoding="utf-8")

    step_def = StepDef(
        id="draft",
        type="llm",
        prompt=str(prompt_path),
        output_schema=str(schema_path),
        llm={"model": "mock"},
    )

    step = LLMStep(step_def, provider=MockProvider(default_output="{}"))

    with pytest.raises(LLMRenderError):
        step.execute({})


def test_llm_step_schema_failure(tmp_path) -> None:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("Hello {{ inputs.topic }}", encoding="utf-8")

    schema = {
        "type": "object",
        "required": ["title"],
        "properties": {"title": {"type": "string"}},
    }
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    step_def = StepDef(
        id="draft",
        type="llm",
        prompt=str(prompt_path),
        output_schema=str(schema_path),
        llm={"model": "mock"},
    )

    provider = MockProvider(default_output=json.dumps({"wrong": "field"}))
    step = LLMStep(step_def, provider=provider)

    with pytest.raises(LLMOutputValidationError):
        step.execute({"topic": "Testing"})
