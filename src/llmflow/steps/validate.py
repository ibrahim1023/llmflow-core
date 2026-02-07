from __future__ import annotations

from typing import Any

from ..errors import ValidationRuleError
from ..registry import ValidatorRegistry
from ..workflow import StepDef, StepValidateConfig
from .base import Step


class ValidateStep(Step):
    def __init__(self, definition: StepDef, *, validators: ValidatorRegistry) -> None:
        super().__init__(definition)
        if not definition.validate_config:
            raise ValidationRuleError("validate step requires 'validate' config")
        self._config = definition.validate_config
        self._validators = validators

    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        _check_required(inputs, self._config)
        _check_non_empty(inputs, self._config)
        _check_allowed_values(inputs, self._config)
        _run_validators(inputs, self._config, self._validators)
        return dict(inputs)


def _check_required(inputs: dict[str, Any], config: StepValidateConfig) -> None:
    for key in config.required:
        if key not in inputs:
            raise ValidationRuleError(f"missing required field '{key}'")


def _check_non_empty(inputs: dict[str, Any], config: StepValidateConfig) -> None:
    for key in config.non_empty:
        value = inputs.get(key)
        if value in (None, ""):
            raise ValidationRuleError(f"field '{key}' must be non-empty")
        if isinstance(value, (list, dict)) and len(value) == 0:
            raise ValidationRuleError(f"field '{key}' must be non-empty")


def _check_allowed_values(inputs: dict[str, Any], config: StepValidateConfig) -> None:
    for key, allowed in config.allowed_values.items():
        if key not in inputs:
            continue
        if inputs[key] not in allowed:
            allowed_str = ", ".join(str(item) for item in allowed)
            raise ValidationRuleError(
                f"field '{key}' must be one of: {allowed_str}")


def _run_validators(
    inputs: dict[str, Any],
    config: StepValidateConfig,
    validators: ValidatorRegistry,
) -> None:
    for name in config.validators:
        validators.validate(name, inputs)
