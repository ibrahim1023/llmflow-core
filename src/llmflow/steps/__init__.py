from .base import Step
from .llm import LLMStep

__all__ = ["LLMStep", "Step", "ToolStep", "ValidateStep"]


def __getattr__(name: str):
    if name == "ToolStep":
        from .tool import ToolStep

        return ToolStep
    if name == "ValidateStep":
        from .validate import ValidateStep

        return ValidateStep
    raise AttributeError(f"module 'llmflow.steps' has no attribute '{name}'")
