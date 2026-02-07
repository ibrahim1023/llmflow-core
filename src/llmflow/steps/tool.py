from __future__ import annotations

from typing import Any

from ..errors import ToolExecutionError
from ..registry import ToolRegistry
from ..workflow import StepDef
from .base import Step


class ToolStep(Step):
    def __init__(self, definition: StepDef, *, tools: ToolRegistry) -> None:
        super().__init__(definition)
        if not definition.tool:
            raise ToolExecutionError("tool step requires 'tool' config")
        self._tool_name = definition.tool.name
        self._tools = tools

    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return self._tools.call(self._tool_name, inputs)
