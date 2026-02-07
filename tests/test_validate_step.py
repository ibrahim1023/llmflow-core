import pytest

from llmflow.errors import ValidationRuleError
from llmflow import ValidateStep, ValidatorRegistry
from llmflow.workflow import StepDef


def test_validate_step_required_failure() -> None:
    validators = ValidatorRegistry()

    step_def = StepDef(
        id="validate",
        type="validate",
        validate={"required": ["name"]},
    )

    step = ValidateStep(step_def, validators=validators)

    with pytest.raises(ValidationRuleError):
        step.execute({"age": 10})


def test_validate_step_custom_validator_failure() -> None:
    def must_have_id(inputs: dict) -> bool:
        return "id" in inputs

    validators = ValidatorRegistry()
    validators.register("has_id", must_have_id)

    step_def = StepDef(
        id="validate",
        type="validate",
        validate={"validators": ["has_id"]},
    )

    step = ValidateStep(step_def, validators=validators)

    with pytest.raises(ValidationRuleError):
        step.execute({"name": "test"})


def test_validate_step_validator_returns_invalid_type() -> None:
    def bad_validator(_: dict) -> str:
        return "nope"

    validators = ValidatorRegistry()
    validators.register("bad", bad_validator)

    step_def = StepDef(
        id="validate",
        type="validate",
        validate={"validators": ["bad"]},
    )

    step = ValidateStep(step_def, validators=validators)

    with pytest.raises(ValidationRuleError):
        step.execute({"name": "ok"})
