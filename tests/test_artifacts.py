from datetime import datetime, timezone

import json
import pytest

from llmflow.artifacts import ArtifactsWriter
from llmflow.errors import ArtifactsError
from llmflow.hashing import sha256_text
from llmflow.workflow import InputDef, StepDef, Workflow, WorkflowMeta, WorkflowSpec


def _build_workflow(tmp_path) -> Workflow:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("Hello {{ inputs.topic }}", encoding="utf-8")

    schema_path = tmp_path / "schema.json"
    schema_path.write_text("{}", encoding="utf-8")

    steps = [
        StepDef(
            id="draft",
            type="llm",
            prompt=str(prompt_path),
            output_schema=str(schema_path),
            llm={"model": "mock"},
        ),
        StepDef(
            id="final",
            type="tool",
            depends_on=["draft"],
            tool={"name": "noop"},
        ),
    ]

    spec = WorkflowSpec(
        workflow=WorkflowMeta(name="demo", version="1.0"),
        inputs={"topic": InputDef(type="string")},
        steps=steps,
        outputs={"result": "final"},
    )

    return Workflow(
        spec=spec,
        path=tmp_path / "workflow.yaml",
        workflow_hash="abc123",
    )


def test_artifacts_writer_creates_run(tmp_path) -> None:
    workflow = _build_workflow(tmp_path)
    start_time = datetime(2026, 2, 16, 12, 30, 45, tzinfo=timezone.utc)
    end_time = datetime(2026, 2, 16, 12, 31, 10, tzinfo=timezone.utc)

    writer = ArtifactsWriter(
        workflow,
        execution_order=["draft", "final"],
        provider_name="mock",
        artifacts_dir=tmp_path / ".runs",
        run_id="abc123",
        started_at=start_time,
    )

    writer.write_inputs({"topic": "Testing"})
    writer.write_rendered_prompt("draft", "Rendered prompt")
    writer.write_step_output("draft", {"draft": "ok"})
    writer.write_step_output("final", {"result": "ok"})
    writer.write_outputs({"result": {"result": "ok"}})
    metadata = writer.finalize(ended_at=end_time)

    run_dir = tmp_path / ".runs" / "run_20260216_123045_abc123"
    assert run_dir.exists()
    assert (run_dir / "inputs.json").exists()
    assert (run_dir / "outputs.json").exists()
    assert (run_dir / "metadata.json").exists()
    assert (run_dir / "steps" / "draft" / "rendered_prompt.md").exists()
    assert (run_dir / "steps" / "draft" / "output.json").exists()
    assert (run_dir / "steps" / "final" / "output.json").exists()

    loaded_metadata = json.loads(
        (run_dir / "metadata.json").read_text(encoding="utf-8")
    )

    assert metadata == loaded_metadata
    assert loaded_metadata["workflow"]["name"] == "demo"
    assert loaded_metadata["workflow"]["hash"] == "abc123"
    assert loaded_metadata["execution_order"] == ["draft", "final"]
    assert loaded_metadata["prompt_hashes"]["draft"] == sha256_text(
        "Rendered prompt"
    )
    assert loaded_metadata["inputs_hash"]
    assert loaded_metadata["outputs_hash"]
    assert loaded_metadata["step_output_hashes"]["draft"]
    assert loaded_metadata["step_output_hashes"]["final"]
    assert loaded_metadata["started_at"] == "2026-02-16T12:30:45Z"
    assert loaded_metadata["ended_at"] == "2026-02-16T12:31:10Z"


def test_artifacts_writer_rejects_unknown_step(tmp_path) -> None:
    workflow = _build_workflow(tmp_path)
    writer = ArtifactsWriter(
        workflow,
        execution_order=["draft"],
        provider_name="mock",
        artifacts_dir=tmp_path / ".runs",
        run_id="reject",
        started_at=datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(ArtifactsError):
        writer.write_step_output("missing", {})


def test_artifacts_writer_rejects_invalid_components(tmp_path) -> None:
    workflow = _build_workflow(tmp_path)
    writer = ArtifactsWriter(
        workflow,
        execution_order=["draft"],
        provider_name="mock",
        artifacts_dir=tmp_path / ".runs",
        run_id="safe",
        started_at=datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(ArtifactsError):
        writer.write_step_output("../escape", {})

    with pytest.raises(ArtifactsError):
        ArtifactsWriter(
            workflow,
            execution_order=["draft"],
            provider_name="mock",
            artifacts_dir=tmp_path / ".runs",
            run_id="../escape",
            started_at=datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
        )
