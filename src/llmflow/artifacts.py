from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

from .errors import ArtifactsError, ArtifactsWriteError
from .hashing import sha256_text
from .workflow import Workflow

ARTIFACTS_VERSION = "1"


@dataclass(frozen=True)
class RunMetadata:
    artifacts_version: str
    engine_version: str
    workflow_name: str
    workflow_version: str
    workflow_hash: str
    workflow_path: str
    provider: str
    execution_order: list[str]
    prompt_hashes: dict[str, str]
    step_output_hashes: dict[str, str]
    inputs_hash: str | None
    outputs_hash: str | None
    started_at: str
    ended_at: str
    run_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifacts_version": self.artifacts_version,
            "engine_version": self.engine_version,
            "workflow": {
                "name": self.workflow_name,
                "version": self.workflow_version,
                "hash": self.workflow_hash,
                "path": self.workflow_path,
            },
            "provider": self.provider,
            "execution_order": list(self.execution_order),
            "prompt_hashes": dict(self.prompt_hashes),
            "step_output_hashes": dict(self.step_output_hashes),
            "inputs_hash": self.inputs_hash,
            "outputs_hash": self.outputs_hash,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "run_id": self.run_id,
        }


class ArtifactsWriter:
    def __init__(
        self,
        workflow: Workflow,
        *,
        execution_order: list[str],
        provider_name: str,
        artifacts_dir: str | Path = ".runs",
        run_id: str | None = None,
        started_at: datetime | None = None,
        engine_version: str | None = None,
    ) -> None:
        if not execution_order:
            raise ArtifactsError("execution_order must be non-empty")
        if len(execution_order) != len(set(execution_order)):
            raise ArtifactsError("execution_order must not contain duplicates")
        provider_name = str(provider_name).strip()
        if not provider_name:
            raise ArtifactsError("provider_name must be non-empty")

        self._workflow = workflow
        self._execution_order = list(execution_order)
        self._provider_name = provider_name
        self._started_at = started_at or _utc_now()
        self._engine_version = engine_version or _load_engine_version()
        self._prompt_hashes: dict[str, str] = {}
        self._step_output_hashes: dict[str, str] = {}
        self._inputs_hash: str | None = None
        self._outputs_hash: str | None = None

        self._run_dir = _create_run_dir(
            Path(artifacts_dir), self._started_at, run_id
        )
        self._steps_dir = self._run_dir / "steps"
        self._steps_dir.mkdir(parents=True, exist_ok=True)
        (self._run_dir / "logs.txt").write_text("", encoding="utf-8")

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    def write_inputs(self, inputs: dict[str, Any]) -> None:
        self._inputs_hash = _write_json(self._run_dir / "inputs.json", inputs)

    def write_outputs(self, outputs: dict[str, Any]) -> None:
        self._outputs_hash = _write_json(self._run_dir / "outputs.json", outputs)

    def write_step_output(self, step_id: str, output: dict[str, Any]) -> None:
        step_path = self._ensure_step_dir(step_id)
        output_hash = _write_json(step_path / "output.json", output)
        self._step_output_hashes[step_id] = output_hash

    def write_rendered_prompt(self, step_id: str, rendered_prompt: str) -> None:
        step_path = self._ensure_step_dir(step_id)
        try:
            step_path.joinpath("rendered_prompt.md").write_text(
                rendered_prompt, encoding="utf-8"
            )
        except OSError as exc:
            raise ArtifactsWriteError(
                f"failed to write rendered prompt for step '{step_id}': {exc}"
            ) from exc
        self._prompt_hashes[step_id] = sha256_text(rendered_prompt)

    def write_llm_call(self, step_id: str, payload: dict[str, Any]) -> None:
        step_path = self._ensure_step_dir(step_id)
        _write_json(step_path / "llm_call.json", payload)

    def write_error(
        self,
        *,
        step_id: str | None,
        error_type: str,
        message: str,
        stage: str,
    ) -> None:
        payload = {
            "step_id": step_id,
            "error_type": error_type,
            "message": message,
            "stage": stage,
        }
        _write_json(self._run_dir / "error.json", payload)
        if step_id is not None:
            step_path = self._ensure_step_dir(step_id)
            _write_json(step_path / "error.json", payload)

    def finalize(self, *, ended_at: datetime | None = None) -> dict[str, Any]:
        end_time = ended_at or _utc_now()
        metadata = RunMetadata(
            artifacts_version=ARTIFACTS_VERSION,
            engine_version=self._engine_version,
            workflow_name=self._workflow.spec.workflow.name,
            workflow_version=self._workflow.spec.workflow.version,
            workflow_hash=self._workflow.workflow_hash,
            workflow_path=str(self._workflow.path),
            provider=self._provider_name,
            execution_order=self._execution_order,
            prompt_hashes=self._prompt_hashes,
            step_output_hashes=self._step_output_hashes,
            inputs_hash=self._inputs_hash,
            outputs_hash=self._outputs_hash,
            started_at=_format_timestamp(self._started_at),
            ended_at=_format_timestamp(end_time),
            run_id=self._run_dir.name,
        )
        payload = metadata.as_dict()
        _write_json(self._run_dir / "metadata.json", payload)
        return payload

    def _ensure_step_dir(self, step_id: str) -> Path:
        step_id = _validate_component("step_id", step_id)
        if step_id not in self._execution_order:
            raise ArtifactsError(f"unknown step_id '{step_id}'")
        step_path = self._steps_dir / step_id
        step_path.mkdir(parents=True, exist_ok=True)
        return step_path


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc).replace(microsecond=0)
    return value.isoformat().replace("+00:00", "Z")


def _create_run_dir(
    artifacts_dir: Path,
    started_at: datetime,
    run_id: str | None,
) -> Path:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    run_stamp = _run_stamp(started_at)
    short_id = (
        _validate_component("run_id", run_id) if run_id else uuid.uuid4().hex[:6]
    )
    if not short_id:
        short_id = uuid.uuid4().hex[:6]
    run_dir = artifacts_dir / f"run_{run_stamp}_{short_id}"
    if run_dir.exists():
        raise ArtifactsError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _run_stamp(started_at: datetime) -> str:
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    return started_at.astimezone(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _load_engine_version() -> str:
    try:
        return metadata.version("llmflow-core")
    except metadata.PackageNotFoundError:
        return "0.0.0"


def _validate_component(label: str, value: str | None) -> str:
    if value is None:
        raise ArtifactsError(f"{label} must be non-empty")
    component = str(value).strip()
    if not component:
        raise ArtifactsError(f"{label} must be non-empty")
    if component in {".", ".."}:
        raise ArtifactsError(f"{label} must not be '.' or '..'")
    if component != Path(component).name:
        raise ArtifactsError(f"{label} must not contain path separators")
    return component


def _stable_json_dumps(payload: Any) -> str:
    return json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
    )


def _write_json(path: Path, payload: Any) -> str:
    try:
        text = _stable_json_dumps(payload)
    except TypeError as exc:
        raise ArtifactsWriteError(
            f"payload for '{path.name}' is not JSON-serializable: {exc}"
        ) from exc
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise ArtifactsWriteError(f"failed to write '{path}': {exc}") from exc
    return sha256_text(text)
