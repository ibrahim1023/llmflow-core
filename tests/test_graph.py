from __future__ import annotations

import pytest

from llmflow.errors import GraphCycleError, GraphDependencyError
from llmflow.graph import build_graph, topo_sort
from llmflow.workflow import StepDef


def _step(step_id: str, *, depends_on: list[str] | None = None) -> StepDef:
    return StepDef(
        id=step_id,
        type="tool",
        depends_on=depends_on or [],
    )


def test_topo_sort_stable_order() -> None:
    steps = [
        _step("alpha"),
        _step("bravo"),
        _step("charlie", depends_on=["alpha"]),
    ]
    assert topo_sort(steps) == ["alpha", "bravo", "charlie"]


def test_build_graph_edges() -> None:
    steps = [
        _step("one"),
        _step("two", depends_on=["one"]),
        _step("three", depends_on=["one"]),
    ]
    graph = build_graph(steps)
    assert graph.order == ["one", "two", "three"]
    assert graph.edges == {"one": ["two", "three"], "two": [], "three": []}


def test_topo_sort_cycle_detection() -> None:
    steps = [
        _step("a", depends_on=["b"]),
        _step("b", depends_on=["a"]),
    ]
    with pytest.raises(GraphCycleError):
        topo_sort(steps)


def test_topo_sort_missing_dependency() -> None:
    steps = [
        _step("a", depends_on=["missing"]),
    ]
    with pytest.raises(GraphDependencyError):
        topo_sort(steps)
