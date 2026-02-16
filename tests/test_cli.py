from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from llmflow.cli import app


def _write_workflow(tmp_path: Path) -> Path:
    workflow_path = tmp_path / "workflow.yaml"
    prompt_path = tmp_path / "prompts" / "outline.md"
    schema_path = tmp_path / "schemas" / "outline.json"
    prompt_path.parent.mkdir(parents=True)
    schema_path.parent.mkdir(parents=True)
    prompt_path.write_text("Prompt", encoding="utf-8")
    schema_path.write_text("{}", encoding="utf-8")
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
    llm:
      model: mock-model
      temperature: 0

outputs:
  article: outline
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return workflow_path


def test_cli_graph(tmp_path: Path) -> None:
    workflow_path = _write_workflow(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["graph", str(workflow_path)])

    assert result.exit_code == 0
    assert "outline" in result.output


def test_cli_run_and_replay(tmp_path: Path) -> None:
    workflow_path = _write_workflow(tmp_path)
    artifacts_dir = tmp_path / "runs"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "run",
            str(workflow_path),
            "--input",
            "topic=Deterministic",
            "--mock-output",
            '{"outline":"ok"}',
            "--artifacts-dir",
            str(artifacts_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Run completed" in result.output
    run_dirs = [path for path in artifacts_dir.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1

    replay_result = runner.invoke(app, ["replay", str(run_dirs[0])])

    assert replay_result.exit_code == 0
    assert "Replay completed" in replay_result.output
