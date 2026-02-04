from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..workflow import StepDef


class Step(ABC):
    def __init__(self, definition: StepDef, **_: Any) -> None:
        self.definition = definition

    @property
    def step_id(self) -> str:
        return self.definition.id

    @property
    def step_type(self) -> str:
        return self.definition.type

    @property
    def depends_on(self) -> list[str]:
        return list(self.definition.depends_on)

    @abstractmethod
    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Run the step and return a JSON-serializable output mapping."""
