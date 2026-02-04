from __future__ import annotations

from typing import Any

from .errors import StepNotFoundError, StepRegistrationError
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
