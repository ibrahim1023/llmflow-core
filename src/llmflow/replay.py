from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import ReplayError
from .runner import RunResult
from .workflow import Workflow


def replay(run_dir: str | Path, *, workflow_path: str | Path | None = None) -> RunResult:
    run_path = Path(run_dir)
    if not run_path.exists():
        raise ReplayError(f"run directory not found: {run_path}")

    metadata = _load_json(run_path / "metadata.json")
    resolved_workflow_path = (
        workflow_path if workflow_path is not None else _workflow_path(metadata)
    )
    workflow = _load_workflow(resolved_workflow_path)

    execution_order = metadata.get("execution_order")
    if not isinstance(execution_order, list) or not execution_order:
        raise ReplayError("metadata execution_order is missing or invalid")

    step_outputs: dict[str, dict[str, Any]] = {}
    for step_id in execution_order:
        step_outputs[step_id] = _load_step_output(run_path, step_id)

    outputs = _resolve_outputs(workflow, step_outputs)
    recorded_outputs = _load_json(run_path / "outputs.json")
    if outputs != recorded_outputs:
        raise ReplayError("replay outputs do not match recorded outputs.json")

    return RunResult(outputs=outputs, run_dir=run_path, metadata=metadata)


def _workflow_path(metadata: dict[str, Any]) -> str:
    workflow = metadata.get("workflow")
    if not isinstance(workflow, dict):
        raise ReplayError("metadata workflow section is missing")
    path = workflow.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ReplayError("metadata workflow.path is missing or invalid")
    return path


def _load_workflow(path: str | Path) -> Workflow:
    workflow_path = Path(path)
    if not workflow_path.exists():
        raise ReplayError(
            "workflow path from metadata does not exist; "
            "pass workflow_path to replay()"
        )
    return Workflow.load(workflow_path)


def _load_step_output(run_path: Path, step_id: str) -> dict[str, Any]:
    step_path = run_path / "steps" / step_id / "output.json"
    payload = _load_json(step_path)
    if not isinstance(payload, dict):
        raise ReplayError(f"step output for '{step_id}' must be an object")
    return payload


def _resolve_outputs(
    workflow: Workflow,
    step_outputs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for name, step_id in workflow.spec.outputs.items():
        if step_id not in step_outputs:
            raise ReplayError(
                f"missing output for workflow output '{name}'"
            )
        outputs[name] = step_outputs[step_id]
    return outputs


def _load_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReplayError(f"failed to read '{path}': {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReplayError(f"invalid JSON in '{path}': {exc}") from exc
