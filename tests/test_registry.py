from __future__ import annotations

import pytest

from llmflow.errors import StepNotFoundError, StepRegistrationError
from llmflow.registry import StepRegistry
from llmflow.steps.base import Step
from llmflow.workflow import StepDef


class DummyStep(Step):
    def execute(self, inputs: dict[str, object]) -> dict[str, object]:
        return {"ok": True}


def _definition(step_type: str) -> StepDef:
    return StepDef(id="step", type=step_type)


def test_registry_register_and_get() -> None:
    registry = StepRegistry()
    registry.register("dummy", DummyStep)
    assert registry.get("dummy") is DummyStep


def test_registry_duplicate_registration() -> None:
    registry = StepRegistry()
    registry.register("dummy", DummyStep)
    with pytest.raises(StepRegistrationError):
        registry.register("dummy", DummyStep)


def test_registry_missing_step_type() -> None:
    registry = StepRegistry()
    with pytest.raises(StepNotFoundError):
        registry.get("missing")


def test_registry_create() -> None:
    registry = StepRegistry()
    registry.register("dummy", DummyStep)
    step = registry.create(_definition("dummy"))
    assert isinstance(step, DummyStep)
