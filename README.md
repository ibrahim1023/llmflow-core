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

## Example workflow (placeholder)
This section will show a minimal YAML workflow, prompt files, and schema.

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
