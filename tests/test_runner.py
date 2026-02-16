import pytest

from llmflow.errors import StepExecutionError
from llmflow.providers import MockProvider
from llmflow.registry import ToolRegistry
from llmflow.runner import RunConfig, Runner
from llmflow.workflow import InputDef, StepDef, Workflow, WorkflowMeta, WorkflowSpec


def _build_workflow(tmp_path) -> Workflow:
    steps = [
        StepDef(
            id="echo",
            type="tool",
            tool={"name": "echo"},
        )
    ]

    spec = WorkflowSpec(
        workflow=WorkflowMeta(name="demo", version="1.0"),
        inputs={"topic": InputDef(type="string")},
        steps=steps,
        outputs={"result": "echo"},
    )

    return Workflow(
        spec=spec,
        path=tmp_path / "workflow.yaml",
        workflow_hash="abc123",
    )


def test_runner_executes_tool_step(tmp_path) -> None:
    workflow = _build_workflow(tmp_path)
    tools = ToolRegistry()
    tools.register("echo", lambda inputs: {"value": inputs["topic"]})

    runner = Runner(
        provider=MockProvider(default_output="{}"),
        tools=tools,
        config=RunConfig(
            artifacts_dir=tmp_path / ".runs",
            provider_name="mock",
            run_id="runner",
        ),
    )

    result = runner.run(workflow, inputs={"topic": "Testing"})

    assert result.outputs == {"result": {"value": "Testing"}}
    assert result.run_dir.name.startswith("run_")
    assert (result.run_dir / "outputs.json").exists()
    assert (result.run_dir / "metadata.json").exists()


def test_runner_requires_inputs(tmp_path) -> None:
    workflow = _build_workflow(tmp_path)
    runner = Runner(
        provider=MockProvider(default_output="{}"),
        config=RunConfig(
            artifacts_dir=tmp_path / ".runs",
            provider_name="mock",
            run_id="missing-input",
        ),
    )

    with pytest.raises(StepExecutionError):
        runner.run(workflow, inputs={})


def test_runner_writes_error_artifacts_on_step_failure(tmp_path) -> None:
    workflow = _build_workflow(tmp_path)
    tools = ToolRegistry()

    def _boom(_: dict[str, object]) -> dict[str, object]:
        raise ValueError("boom")

    tools.register("echo", _boom)

    runner = Runner(
        provider=MockProvider(default_output="{}"),
        tools=tools,
        config=RunConfig(
            artifacts_dir=tmp_path / ".runs",
            provider_name="mock",
            run_id="failure",
        ),
    )

    with pytest.raises(StepExecutionError):
        runner.run(workflow, inputs={"topic": "Testing"})

    runs_dir = tmp_path / ".runs"
    run_dirs = [path for path in runs_dir.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert (run_dir / "error.json").exists()
    assert (run_dir / "steps" / "echo" / "error.json").exists()
