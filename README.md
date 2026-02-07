# llmflow-core

Deterministic LLM workflow engine for file-defined, schema-validated pipelines.

## Why
LLM "agents" are hard to trust in production due to implicit ordering,
unstructured outputs, and limited replayability. This project provides explicit,
auditable workflows with deterministic execution and replayable artifacts.

## Quickstart (placeholder)
- Install: `pip install llmflow-core`
- Load a workflow file (execution coming in later phases).

```python
from llmflow import Workflow

workflow = Workflow.load("examples/blog_pipeline/workflow.yaml")
print(workflow.spec.workflow.name)
```

## Example workflow (placeholder)
This section will show a minimal YAML workflow, prompt files, and schema.

## Artifacts layout (placeholder)
This section will document the run directory structure and metadata fields.

## Extension points (placeholder)
This section will document providers, tools, and validators.
Provider adapters are defined via a small `Provider` interface with
typed request/response models, plus a deterministic `MockProvider` for tests.
LLM steps render Jinja prompts and validate JSON outputs against draft-07
schemas before returning results.
