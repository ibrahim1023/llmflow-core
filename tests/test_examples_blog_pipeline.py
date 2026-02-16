from __future__ import annotations

import json
import time
from pathlib import Path

from jinja2 import Environment, StrictUndefined

from llmflow import MockProvider, RunConfig, Runner, Workflow


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = ROOT / "examples" / "blog_pipeline"


def _render_prompt(path: Path, inputs: dict[str, object]) -> str:
    template_text = path.read_text(encoding="utf-8")
    env = Environment(undefined=StrictUndefined)
    template = env.from_string(template_text)
    return template.render(inputs=inputs).strip()


def test_blog_pipeline_example_runs_end_to_end_under_two_minutes(tmp_path: Path) -> None:
    workflow = Workflow.load(EXAMPLE_DIR / "workflow.yaml")

    workflow_inputs: dict[str, object] = {
        "topic": "Deterministic AI workflows",
        "audience": "Engineering managers",
    }
    outline_output = {
        "title": "Deterministic AI workflows for production",
        "sections": [
            "Why determinism matters",
            "Designing file-defined DAGs",
            "Replay and audit trails",
        ],
    }
    critique_output = {
        "strengths": ["Clear structure", "Concrete audience fit"],
        "weaknesses": ["Needs clearer failure semantics"],
        "revision_goals": ["Add fail-fast examples", "Tighten conclusion"],
    }
    final_output = {
        "title": "Deterministic AI workflows for production",
        "summary": "A practical guide to building reliable LLM pipelines.",
        "body": "Determinism reduces drift, improves debuggability, and enables replay.",
    }

    prompts_dir = EXAMPLE_DIR / "prompts"
    outline_prompt = _render_prompt(prompts_dir / "outline.md", workflow_inputs)
    critique_prompt = _render_prompt(
        prompts_dir / "critique.md",
        {**workflow_inputs, **outline_output},
    )
    revise_prompt = _render_prompt(
        prompts_dir / "revise.md",
        {**workflow_inputs, **critique_output},
    )

    provider = MockProvider(
        responses={
            f"prompt:{outline_prompt}": json.dumps(outline_output),
            f"prompt:{critique_prompt}": json.dumps(critique_output),
            f"prompt:{revise_prompt}": json.dumps(final_output),
        }
    )
    runner = Runner(
        provider=provider,
        config=RunConfig(
            artifacts_dir=tmp_path / ".runs",
            provider_name="mock",
            run_id="blog-example",
        ),
    )

    start = time.perf_counter()
    result = runner.run(workflow, workflow_inputs)
    duration = time.perf_counter() - start

    assert duration < 120
    assert result.outputs == {"article": final_output}
    assert result.run_dir.exists()
    assert (result.run_dir / "outputs.json").exists()
