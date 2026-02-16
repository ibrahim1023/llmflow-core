# llmflow-core

Deterministic LLM workflow engine for file-defined, schema-validated pipelines.

## Why
LLM "agents" are hard to trust in production due to implicit ordering,
unstructured outputs, and limited replayability. This project provides explicit,
auditable workflows with deterministic execution and replayable artifacts.

## Quickstart (placeholder)
- Install: `pip install llmflow-core`
- Load and run a workflow file.

```python
from llmflow import MockProvider, RunConfig, Runner, Workflow

workflow = Workflow.load("examples/blog_pipeline/workflow.yaml")

runner = Runner(
    provider=MockProvider(default_output="{}"),
    config=RunConfig(artifacts_dir=".runs", provider_name="mock"),
)
result = runner.run(workflow, inputs={"topic": "Deterministic AI", "audience": "EMs"})
print(result.outputs)
```

## Replay
Replay verifies recorded outputs without re-running providers:

```python
from llmflow import replay

result = replay(".runs/run_YYYYMMDD_HHMMSS_<shortid>")
result = replay(
    ".runs/run_YYYYMMDD_HHMMSS_<shortid>",
    workflow_path="examples/blog_pipeline/workflow.yaml",
)
print(result.outputs)
```

## CLI
The CLI is a thin wrapper around the library API. It uses the deterministic
mock provider and requires a JSON object for LLM outputs.
`--mock-output` (or `--mock-output-file`) is applied to every LLM step in the
run, so workflows with different per-step schemas should use a payload that
passes all schema checks.

```bash
llmflow run examples/blog_pipeline/workflow.yaml \
  --input topic="Deterministic AI" \
  --input audience="Engineering managers" \
  --mock-output '{"outline":"..."}'

llmflow graph examples/blog_pipeline/workflow.yaml
llmflow replay .runs/run_YYYYMMDD_HHMMSS_<shortid>
```

## Example workflow
The repository includes `examples/blog_pipeline`:

- `workflow.yaml`: 3-step LLM DAG (`outline -> critique -> revise`)
- `prompts/`: step prompt templates
- `schemas/`: per-step output schemas
- `tools.py`: placeholder for future tool steps

Run it via the Python API with deterministic per-step mock responses:

```python
import json

from llmflow import MockProvider, RunConfig, Runner, Workflow

workflow = Workflow.load("examples/blog_pipeline/workflow.yaml")

provider = MockProvider(
    responses={
        "prompt:<rendered outline prompt>": json.dumps(
            {"title": "Deterministic AI workflows", "sections": ["A", "B", "C"]}
        ),
        "prompt:<rendered critique prompt>": json.dumps(
            {
                "strengths": ["Clear structure"],
                "weaknesses": ["Needs concrete examples"],
                "revision_goals": ["Add failure semantics"],
            }
        ),
        "prompt:<rendered revise prompt>": json.dumps(
            {
                "title": "Deterministic AI workflows",
                "summary": "Practical guide",
                "body": "Full article body",
            }
        ),
    }
)

runner = Runner(
    provider=provider,
    config=RunConfig(artifacts_dir=".runs", provider_name="mock"),
)
result = runner.run(
    workflow,
    inputs={"topic": "Deterministic AI", "audience": "Engineering managers"},
)
print(result.outputs["article"])
```

## Artifacts layout
Each run writes a timestamped folder under `.runs/`:

```
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
- start/end timestamps

## Extension points (placeholder)
This section will document providers, tools, and validators.
Provider adapters are defined via a small `Provider` interface with
typed request/response models, plus a deterministic `MockProvider` for tests.
LLM steps render Jinja prompts and validate JSON outputs against draft-07
schemas before returning results.
Tool steps call registered Python functions, and validate steps apply simple
rules plus optional custom validators.
