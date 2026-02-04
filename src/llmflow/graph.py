from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .errors import GraphCycleError, GraphDependencyError

if TYPE_CHECKING:
    from .workflow import StepDef


@dataclass(frozen=True)
class Graph:
    order: list[str]
    edges: dict[str, list[str]]


def build_graph(steps: list[StepDef]) -> Graph:
    step_ids = [step.id for step in steps]
    step_id_set = set(step_ids)

    edges: dict[str, list[str]] = {step_id: [] for step_id in step_ids}
    for step in steps:
        for dep in step.depends_on:
            if dep not in step_id_set:
                raise GraphDependencyError(f"unknown dependency '{dep}' in step '{step.id}'")
            edges[dep].append(step.id)

    order = topo_sort(steps)
    return Graph(order=order, edges=edges)


def topo_sort(steps: list[StepDef]) -> list[str]:
    step_ids = [step.id for step in steps]
    step_id_set = set(step_ids)

    indegree = {step_id: 0 for step_id in step_ids}
    dependents: dict[str, list[str]] = {step_id: [] for step_id in step_ids}

    for step in steps:
        for dep in step.depends_on:
            if dep not in step_id_set:
                raise GraphDependencyError(f"unknown dependency '{dep}' in step '{step.id}'")
            indegree[step.id] += 1
            dependents[dep].append(step.id)

    order: list[str] = []
    queue = deque(step_id for step_id in step_ids if indegree[step_id] == 0)

    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in dependents[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(step_ids):
        remaining = [step_id for step_id in step_ids if step_id not in order]
        raise GraphCycleError(f"cycle detected among steps: {remaining}")

    return order
