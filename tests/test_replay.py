import json
from pathlib import Path

import pytest

from llmflow.errors import ReplayError
from llmflow.providers import MockProvider
from llmflow.registry import ToolRegistry
from llmflow.replay import replay
from llmflow.runner import RunConfig, Runner
from llmflow.workflow import Workflow


def _build_workflow(tmp_path) -> Workflow:
    workflow_path = tmp_path / "workflow.yaml"
    workflow_path.write_text(
        "\n".join(
            [
                "workflow:",
                "  name: demo",
                "  version: \"1.0\"",
                "",
                "inputs:",
                "  topic:",
                "    type: string",
                "",
                "steps:",
                "  - id: echo",
                "    type: tool",
                "    tool:",
                "      name: echo",
                "",
                "outputs:",
                "  result: echo",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return Workflow.load(workflow_path)


def _run_workflow(tmp_path) -> str:
    workflow = _build_workflow(tmp_path)
    tools = ToolRegistry()
    tools.register("echo", lambda inputs: {"value": inputs["topic"]})

    runner = Runner(
        provider=MockProvider(default_output="{}"),
        tools=tools,
        config=RunConfig(
            artifacts_dir=tmp_path / ".runs",
            provider_name="mock",
            run_id="replay",
        ),
    )

    result = runner.run(workflow, inputs={"topic": "Testing"})
    return str(result.run_dir)


def test_replay_matches_recorded_outputs(tmp_path) -> None:
    run_dir = _run_workflow(tmp_path)

    result = replay(run_dir)

    assert result.outputs == {"result": {"value": "Testing"}}


def test_replay_detects_output_mismatch(tmp_path) -> None:
    run_dir = _run_workflow(tmp_path)

    outputs_file = Path(run_dir) / "outputs.json"
    outputs_file.write_text(json.dumps({"result": {"value": "changed"}}), encoding="utf-8")

    with pytest.raises(ReplayError):
        replay(run_dir)


def test_replay_allows_workflow_override(tmp_path) -> None:
    run_dir = _run_workflow(tmp_path)
    metadata_path = Path(run_dir) / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["workflow"]["path"] = str(tmp_path / "missing.yaml")
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    result = replay(run_dir, workflow_path=tmp_path / "workflow.yaml")

    assert result.outputs == {"result": {"value": "Testing"}}
