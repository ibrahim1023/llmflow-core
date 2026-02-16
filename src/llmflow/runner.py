from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifacts import ArtifactsWriter
from .errors import StepExecutionError
from .providers import Provider
from .registry import StepRegistry, ToolRegistry, ValidatorRegistry
from .steps import LLMStep
from .steps.tool import ToolStep
from .steps.validate import ValidateStep
from .workflow import StepDef, Workflow


@dataclass(frozen=True)
class RunConfig:
    artifacts_dir: str | Path = ".runs"
    provider_name: str = "unknown"
    run_id: str | None = None


@dataclass(frozen=True)
class RunResult:
    outputs: dict[str, Any]
    run_dir: Path
    metadata: dict[str, Any]


class Runner:
    def __init__(
        self,
        *,
        provider: Provider,
        config: RunConfig | None = None,
        steps: StepRegistry | None = None,
        tools: ToolRegistry | None = None,
        validators: ValidatorRegistry | None = None,
    ) -> None:
        self._provider = provider
        self._config = config or RunConfig()
        self._tools = tools or ToolRegistry()
        self._validators = validators or ValidatorRegistry()
        self._steps = steps or _default_step_registry()

    def run(self, workflow: Workflow, inputs: dict[str, Any]) -> RunResult:
        _validate_inputs(workflow, inputs)
        graph = workflow.graph()
        step_defs = {step.id: step for step in workflow.spec.steps}

        writer = ArtifactsWriter(
            workflow,
            execution_order=graph.order,
            provider_name=self._config.provider_name,
            artifacts_dir=self._config.artifacts_dir,
            run_id=self._config.run_id,
        )
        writer.write_inputs(inputs)

        step_outputs: dict[str, dict[str, Any]] = {}
        for step_id in graph.order:
            definition = step_defs[step_id]
            step = self._create_step(definition)
            step_inputs = _build_step_inputs(inputs, step_outputs, definition.depends_on)
            output = step.execute(step_inputs)
            writer.write_step_output(step_id, output)
            step_outputs[step_id] = output

        outputs = _resolve_outputs(workflow, step_outputs)
        writer.write_outputs(outputs)
        metadata = writer.finalize()
        return RunResult(outputs=outputs, run_dir=writer.run_dir, metadata=metadata)

    def _create_step(self, definition: StepDef) -> Any:
        if definition.type == "llm":
            return LLMStep(definition, provider=self._provider)
        if definition.type == "tool":
            return ToolStep(definition, tools=self._tools)
        if definition.type == "validate":
            return ValidateStep(definition, validators=self._validators)
        return self._steps.create(definition)


def _default_step_registry() -> StepRegistry:
    registry = StepRegistry()
    registry.register("llm", LLMStep)
    registry.register("tool", ToolStep)
    registry.register("validate", ValidateStep)
    return registry


def _validate_inputs(workflow: Workflow, inputs: dict[str, Any]) -> None:
    missing = [
        name for name in workflow.spec.inputs.keys() if name not in inputs
    ]
    if missing:
        missing_str = ", ".join(missing)
        raise StepExecutionError(f"missing required inputs: {missing_str}")


def _build_step_inputs(
    workflow_inputs: dict[str, Any],
    step_outputs: dict[str, dict[str, Any]],
    dependencies: list[str],
) -> dict[str, Any]:
    resolved = dict(workflow_inputs)
    for dep in dependencies:
        output = step_outputs.get(dep)
        if output is None:
            raise StepExecutionError(
                f"missing output for dependency '{dep}'"
            )
        resolved.update(output)
    return resolved


def _resolve_outputs(
    workflow: Workflow,
    step_outputs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for name, step_id in workflow.spec.outputs.items():
        if step_id not in step_outputs:
            raise StepExecutionError(
                f"missing output for workflow output '{name}'"
            )
        outputs[name] = step_outputs[step_id]
    return outputs
