# llmflow-core

Deterministic LLM workflow engine for file-defined, schema-validated pipelines.

## Overview

`llmflow-core` executes explicit workflow DAGs from YAML and prompt files.
It is designed for predictable execution, strict output contracts, and replayable
artifacts.

Core guarantees:

- Stable topological execution order
- Fail-fast behavior on first step error
- JSON-schema validation for LLM outputs
- Run artifacts for audit and replay

## Why this exists

Production LLM pipelines often fail on three basics:

- Step order is implicit and hard to reason about
- Outputs drift from expected structure
- Runs are difficult to reproduce and debug

`llmflow-core` addresses this with file-defined workflows, strict validation,
and deterministic run traces.

## Installation

```bash
python -m pip install -e .
```

Install with test dependencies:

```bash
python -m pip install -e .[dev]
```

## Quickstart
### 1) Run with Python API

```python
from llmflow import MockProvider, RunConfig, Runner, Workflow

workflow = Workflow.load("examples/blog_pipeline/workflow.yaml")

runner = Runner(
    provider=MockProvider(default_output="{}", strict=False),
    config=RunConfig(artifacts_dir=".runs", provider_name="mock"),
)

result = runner.run(
    workflow,
    inputs={"topic": "Deterministic AI", "audience": "Engineering managers"},
)

print(result.outputs)
print(result.run_dir)
```

Note:

- `MockProvider(default_output=...)` returns the same JSON for every LLM step.
- If your workflow has different per-step schemas, use per-prompt mock responses
  (see Example Workflow below).

### 2) Run with CLI

```bash
llmflow run examples/blog_pipeline/workflow.yaml \
  --input topic="Deterministic AI" \
  --input audience="Engineering managers" \
  --mock-output '{"title":"Draft","summary":"S","body":"B"}'
```

### 3) Inspect and replay

```bash
llmflow graph examples/blog_pipeline/workflow.yaml
llmflow replay .runs/run_YYYYMMDD_HHMMSS_<shortid>
```

## CLI

The CLI is a thin wrapper over the library API.

Commands:

- `llmflow run <workflow.yaml> --input key=value ...`
- `llmflow graph <workflow.yaml>`
- `llmflow replay <run_dir>`

Example:

```bash
llmflow run examples/blog_pipeline/workflow.yaml \
  --input topic="Deterministic AI" \
  --input audience="Engineering managers" \
  --mock-output '{"title":"Draft","summary":"S","body":"B"}'

llmflow graph examples/blog_pipeline/workflow.yaml
llmflow replay .runs/run_YYYYMMDD_HHMMSS_<shortid>
```

CLI mock behavior:

- `--mock-output` and `--mock-output-file` are applied to all LLM steps in the run.
- For workflows with heterogeneous per-step schemas, prefer Python API tests with
  prompt-specific mock responses.

## Example workflow

Repository example: `examples/blog_pipeline`

Contents:

- `examples/blog_pipeline/workflow.yaml`
- `examples/blog_pipeline/prompts/outline.md`
- `examples/blog_pipeline/prompts/critique.md`
- `examples/blog_pipeline/prompts/revise.md`
- `examples/blog_pipeline/schemas/outline.json`
- `examples/blog_pipeline/schemas/critique.json`
- `examples/blog_pipeline/schemas/final_article.json`
- `examples/blog_pipeline/tools.py`

The end-to-end deterministic example run is validated by:

- `tests/test_examples_blog_pipeline.py`

## Workflow YAML format
Minimal shape:

```yaml
workflow:
  name: blog_post_pipeline
  version: "1.0"

inputs:
  topic:
    type: string
  audience:
    type: string

steps:
  - id: outline
    type: llm
    prompt: prompts/outline.md
    output_schema: schemas/outline.json
    llm:
      model: mock-model
      temperature: 0

  - id: critique
    type: llm
    depends_on: [outline]
    prompt: prompts/critique.md
    output_schema: schemas/critique.json
    llm:
      model: mock-model
      temperature: 0

outputs:
  article: critique
```

Rules:
- `workflow.name` and `workflow.version` are required.
- `inputs` is a mapping of input names to type declarations.
- Each step needs a unique `id` and `type`.
- `depends_on` must reference existing step ids.
- `outputs` maps final output names to step ids.
- For `llm` steps, `prompt`, `output_schema`, and `llm.model` are required.

## Replay

Replay reconstructs outputs from recorded artifacts and verifies they match the
recorded `outputs.json` exactly.

```python
from llmflow import replay

result = replay(".runs/run_YYYYMMDD_HHMMSS_<shortid>")
print(result.outputs)
```

Optional workflow override:

```python
result = replay(
    ".runs/run_YYYYMMDD_HHMMSS_<shortid>",
    workflow_path="examples/blog_pipeline/workflow.yaml",
)
```

## Artifacts

Each run writes a folder under `.runs/`:

```text
.runs/
  run_YYYYMMDD_HHMMSS_<shortid>/
    metadata.json
    inputs.json
    outputs.json
    steps/
      <step_id>/
        output.json
        rendered_prompt.md
        llm_call.json
    logs.txt
```

`metadata.json` includes:

- `artifacts_version`
- engine version
- workflow name, version, and hash
- provider name
- execution order
- prompt hashes and step output hashes
- timestamps

Typical step artifacts:

- `steps/<step_id>/output.json`: Validated step output payload
- `steps/<step_id>/rendered_prompt.md`: Rendered prompt text for LLM steps
- `steps/<step_id>/llm_call.json`: Provider request/response metadata for LLM steps

## Extending the engine

Extension points:

- Providers: implement `Provider.call(request) -> ProviderResponse`
- Tools: register Python callables in `ToolRegistry`
- Validators: register custom checks in `ValidatorRegistry`
- Steps: register new step implementations in `StepRegistry`

## Testing

Run all tests:

```bash
pytest
```

Run tests with coverage for core modules:

```bash
pytest --cov=llmflow --cov-report=term-missing
```

Determinism and replay checks:

```bash
pytest tests/test_replay.py tests/test_examples_blog_pipeline.py
```

Run a local command equivalent to CI:

```bash
python -m pip install -e .[dev]
pytest --cov=llmflow --cov-report=term-missing
```

## Current status

Implemented through Phase 11:

- Core workflow loading and validation
- Graph ordering and cycle detection
- LLM/tool/validate steps
- Artifacts and metadata
- Runner and replay
- CLI (`run`, `graph`, `replay`)
- Example workflow (`examples/blog_pipeline`)
- CI workflow and coverage command (`pytest --cov=llmflow`)
