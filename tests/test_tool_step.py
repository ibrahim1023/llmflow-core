import pytest

from llmflow.errors import ToolExecutionError
from llmflow import ToolRegistry, ToolStep
from llmflow.workflow import StepDef


def test_tool_step_invokes_tool() -> None:
    def echo(inputs: dict) -> dict:
        return {"echo": inputs["value"]}

    tools = ToolRegistry()
    tools.register("echo", echo)

    step_def = StepDef(
        id="tool",
        type="tool",
        tool={"name": "echo"},
    )

    step = ToolStep(step_def, tools=tools)
    output = step.execute({"value": "hello"})
    assert output == {"echo": "hello"}


def test_tool_step_requires_dict_output() -> None:
    def bad_tool(_: dict) -> str:
        return "nope"

    tools = ToolRegistry()
    tools.register("bad", bad_tool)

    step_def = StepDef(
        id="tool",
        type="tool",
        tool={"name": "bad"},
    )

    step = ToolStep(step_def, tools=tools)

    with pytest.raises(ToolExecutionError):
        step.execute({"value": "hello"})
