from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import typer
from rich.console import Console

from .errors import (
    ArtifactsError,
    GraphError,
    ProviderError,
    ReplayError,
    StepExecutionError,
    WorkflowError,
)
from .providers import MockProvider
from .replay import replay
from .runner import RunConfig, Runner
from .workflow import Workflow


app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


@app.command()
def run(
    workflow: Path,
    input_items: list[str] = typer.Option(
        None,
        "--input",
        "-i",
        help="Workflow input in key=value form. Repeat for multiple inputs.",
    ),
    artifacts_dir: Path = typer.Option(
        Path(".runs"),
        "--artifacts-dir",
        help="Directory to store run artifacts.",
    ),
    run_id: str | None = typer.Option(
        None,
        "--run-id",
        help="Optional run id to include in the artifacts path.",
    ),
    provider_name: str = typer.Option(
        "mock",
        "--provider-name",
        help="Provider name recorded in metadata.",
    ),
    mock_output: str | None = typer.Option(
        None,
        "--mock-output",
        help="JSON object used as the mock provider output.",
    ),
    mock_output_file: Path | None = typer.Option(
        None,
        "--mock-output-file",
        help="Path to a JSON file used as the mock provider output.",
    ),
) -> None:
    """Run a workflow using the deterministic mock provider."""
    try:
        workflow_obj = Workflow.load(workflow)
        inputs = _parse_inputs(input_items or [])
        output_text = _load_mock_output(mock_output, mock_output_file)
        if _has_llm_steps(workflow_obj) and output_text is None:
            raise typer.BadParameter(
                "LLM steps require --mock-output or --mock-output-file."
            )

        provider = MockProvider(
            default_output=output_text or "{}",
            strict=False,
        )
        runner = Runner(
            provider=provider,
            config=RunConfig(
                artifacts_dir=artifacts_dir,
                provider_name=provider_name,
                run_id=run_id,
            ),
        )
        result = runner.run(workflow_obj, inputs)
    except typer.BadParameter:
        raise
    except (WorkflowError, GraphError, StepExecutionError, ProviderError, ArtifactsError) as exc:
        _exit_with_error(str(exc))

    console.print(f"Run completed: {result.run_dir}")
    console.print("Outputs:")
    console.print_json(json.dumps(result.outputs, sort_keys=True))


@app.command()
def graph(workflow: Path) -> None:
    """Print the execution order for a workflow."""
    try:
        workflow_obj = Workflow.load(workflow)
        order = workflow_obj.graph().order
    except (WorkflowError, GraphError) as exc:
        _exit_with_error(str(exc))

    console.print("Execution order:")
    for index, step_id in enumerate(order, start=1):
        console.print(f"{index}. {step_id}")


@app.command("replay")
def replay_cmd(
    run_dir: Path,
    workflow: Path | None = typer.Option(
        None,
        "--workflow",
        help="Optional workflow file to use instead of metadata.",
    ),
) -> None:
    """Replay a run directory and verify outputs."""
    try:
        result = replay(run_dir, workflow_path=workflow)
    except ReplayError as exc:
        _exit_with_error(str(exc))

    console.print(f"Replay completed: {run_dir}")
    console.print("Outputs:")
    console.print_json(json.dumps(result.outputs, sort_keys=True))


def _parse_inputs(items: Iterable[str]) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise typer.BadParameter(f"input must be key=value, got '{item}'")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise typer.BadParameter(f"input key is missing in '{item}'")
        if key in inputs:
            raise typer.BadParameter(f"duplicate input key '{key}'")
        inputs[key] = _parse_value(value.strip())
    return inputs


def _parse_value(raw: str) -> Any:
    if raw == "":
        return ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _load_mock_output(
    mock_output: str | None,
    mock_output_file: Path | None,
) -> str | None:
    if mock_output and mock_output_file:
        raise typer.BadParameter(
            "use only one of --mock-output or --mock-output-file"
        )
    if mock_output_file is not None:
        try:
            mock_output = mock_output_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise typer.BadParameter(
                f"failed to read mock output file: {exc}"
            ) from exc
    if mock_output is None:
        return None
    try:
        payload = json.loads(mock_output)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(
            f"mock output must be valid JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise typer.BadParameter("mock output must be a JSON object")
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _has_llm_steps(workflow: Workflow) -> bool:
    return any(step.type == "llm" for step in workflow.spec.steps)


def _exit_with_error(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(code=1)
