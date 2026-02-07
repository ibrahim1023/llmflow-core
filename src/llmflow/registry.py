from __future__ import annotations

from typing import Any, Callable

from .errors import (
    StepNotFoundError,
    StepRegistrationError,
    ToolNotFoundError,
    ToolRegistrationError,
    ToolExecutionError,
    ValidatorNotFoundError,
    ValidatorRegistrationError,
    ValidationRuleError,
)
from .steps.base import Step
from .workflow import StepDef


class StepRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, type[Step]] = {}

    def register(self, step_type: str, step_cls: type[Step]) -> None:
        step_type = str(step_type).strip()
        if not step_type:
            raise StepRegistrationError("step_type must be non-empty")
        if step_type in self._registry:
            raise StepRegistrationError(f"step type '{step_type}' already registered")
        if not issubclass(step_cls, Step):
            raise StepRegistrationError("step_cls must inherit from Step")

        self._registry[step_type] = step_cls

    def get(self, step_type: str) -> type[Step]:
        try:
            return self._registry[step_type]
        except KeyError as exc:
            raise StepNotFoundError(f"step type '{step_type}' is not registered") from exc

    def create(self, definition: StepDef, **kwargs: Any) -> Step:
        step_cls = self.get(definition.type)
        return step_cls(definition, **kwargs)


ToolFn = Callable[[dict[str, Any]], dict[str, Any]]
ValidatorFn = Callable[[dict[str, Any]], bool | None]


class ToolRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, ToolFn] = {}

    def register(self, name: str, fn: ToolFn) -> None:
        name = str(name).strip()
        if not name:
            raise ToolRegistrationError("tool name must be non-empty")
        if name in self._registry:
            raise ToolRegistrationError(f"tool '{name}' already registered")
        if not callable(fn):
            raise ToolRegistrationError("tool must be callable")
        self._registry[name] = fn

    def get(self, name: str) -> ToolFn:
        try:
            return self._registry[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"tool '{name}' is not registered") from exc

    def call(self, name: str, inputs: dict[str, Any]) -> dict[str, Any]:
        fn = self.get(name)
        try:
            result = fn(inputs)
        except Exception as exc:  # pragma: no cover - defensive wrapping
            raise ToolExecutionError(f"tool '{name}' failed: {exc}") from exc
        if not isinstance(result, dict):
            raise ToolExecutionError(f"tool '{name}' must return a dict")
        return result


class ValidatorRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, ValidatorFn] = {}

    def register(self, name: str, fn: ValidatorFn) -> None:
        name = str(name).strip()
        if not name:
            raise ValidatorRegistrationError("validator name must be non-empty")
        if name in self._registry:
            raise ValidatorRegistrationError(f"validator '{name}' already registered")
        if not callable(fn):
            raise ValidatorRegistrationError("validator must be callable")
        self._registry[name] = fn

    def get(self, name: str) -> ValidatorFn:
        try:
            return self._registry[name]
        except KeyError as exc:
            raise ValidatorNotFoundError(
                f"validator '{name}' is not registered") from exc

    def validate(self, name: str, inputs: dict[str, Any]) -> None:
        fn = self.get(name)
        try:
            result = fn(inputs)
        except Exception as exc:  # pragma: no cover - defensive wrapping
            raise ValidationRuleError(
                f"validator '{name}' failed: {exc}") from exc
        if result is False:
            raise ValidationRuleError(
                f"validator '{name}' returned False")
        if result is not None and result is not True:
            raise ValidationRuleError(
                f"validator '{name}' must return True, False, or None")
