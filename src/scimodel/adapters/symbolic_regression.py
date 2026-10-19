"""Genetic-programming symbolic regression for equation discovery.

The search evolves expression trees over the predictors and keeps a Pareto
front of accuracy versus complexity. Every tree is evaluated with *linear
scaling* (``y ≈ a + b·f(x)``, Keijzer 2003), which lets the search focus on
the functional form rather than on scale and offset. Survivors are converted
into :class:`ModelFormula` objects whose numeric constants become fitted
parameters, so they receive the same uncertainty and validation treatment as
any other candidate.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TypeAlias

import numpy as np
import numpy.typing as npt

from scimodel.domain.discovery import CandidateProposal
from scimodel.domain.formula import ModelFormula, ParameterSpec

FloatArray: TypeAlias = npt.NDArray[np.float64]

# Tree encoding: ("x", name) | ("c", value) | ("u", op, child) | ("b", op, left, right)
Tree: TypeAlias = tuple[Any, ...]

BINARY_OPS = ("+", "-", "*", "/")
DEFAULT_UNARY_OPS = ("square", "sqrt", "exp", "log", "inv")
PERIODIC_UNARY_OPS = ("sin", "cos")


@dataclass(frozen=True)
class SymbolicSearchSettings:
    """Tunable search budget; defaults suit interactive use on small datasets."""

    population: int = 300
    generations: int = 40
    max_depth: int = 5
    tournament: int = 5
    parsimony: float = 0.003
    time_budget: float = 15.0
    max_front: int = 8
    unary_ops: tuple[str, ...] = DEFAULT_UNARY_OPS
    seed: int = 0


@dataclass(frozen=True)
class FrontMember:
    expression: str
    size: int
    nrmse: float


class SymbolicRegressor:
    """Seeded, budgeted GP search returning fit-ready candidate proposals."""

    def __init__(self, settings: SymbolicSearchSettings | None = None) -> None:
        self.settings = settings or SymbolicSearchSettings()
        self.front: list[FrontMember] = []

    def propose(
        self,
        variables: dict[str, FloatArray],
        y: FloatArray,
        *,
        target: str = "y",
    ) -> list[CandidateProposal]:
        settings = self.settings
        rng = np.random.default_rng(settings.seed)
        names = tuple(variables)
        y_std = float(np.std(y))
        if y_std == 0.0 or len(y) < 5:
            return []
        deadline = time.monotonic() + settings.time_budget

        hall: dict[str, tuple[int, float, Tree]] = {}

        def score(tree: Tree) -> float:
            key = _render(tree)
            cached = hall.get(key)
            if cached is not None:
                return cached[1] + settings.parsimony * cached[0]
            nrmse = _scaled_nrmse(tree, variables, y, y_std)
            size = _size(tree)
            if np.isfinite(nrmse):
                hall[key] = (size, nrmse, tree)
            return nrmse + settings.parsimony * size

        population = [
            _random_tree(rng, names, settings, depth=int(rng.integers(1, settings.max_depth)))
            for _ in range(settings.population)
        ]
        # Seed with the bare predictors so simple linear relations are always considered.
        population[: len(names)] = [("x", name) for name in names]
        fitness = [score(tree) for tree in population]

        for _ in range(settings.generations):
            if time.monotonic() > deadline:
                break
            elite = int(np.argmin(fitness))
            offspring: list[Tree] = [population[elite]]
            while len(offspring) < settings.population:
                parent = _tournament(rng, population, fitness, settings.tournament)
                roll = rng.random()
                if roll < 0.6:
                    other = _tournament(rng, population, fitness, settings.tournament)
                    child = _crossover(rng, parent, other)
                elif roll < 0.85:
                    child = _subtree_mutation(rng, parent, names, settings)
                else:
                    child = _constant_mutation(rng, parent)
                if _depth(child) > settings.max_depth + 1:
                    child = parent
                offspring.append(child)
            population = offspring
            fitness = [score(tree) for tree in population]

        self.front = _pareto(hall)[: settings.max_front]
        proposals: list[CandidateProposal] = []
        for index, member in enumerate(self.front):
            tree = hall[member.expression][2]
            intercept, slope = _linear_scaling(tree, variables, y)
            formula, start = _to_formula(tree, names, target, index, intercept, slope)
            if formula is None:
                continue
            proposals.append(
                CandidateProposal(
                    formula=formula,
                    origin="symbolic",
                    rationale=(
                        "Discovered by genetic-programming symbolic regression "
                        f"(complexity {member.size}, scaled NRMSE {member.nrmse:.3g})."
                    ),
                    starts=(start,),
                    search_space=max(len(hall), 1),
                )
            )
        return proposals


def _linear_scaling(
    tree: Tree, variables: dict[str, FloatArray], y: FloatArray
) -> tuple[float, float]:
    """Return the least-squares intercept and slope of ``y`` on the tree output."""
    with np.errstate(all="ignore"):
        values = np.broadcast_to(_evaluate(tree, variables), y.shape).astype(np.float64)
    if not np.all(np.isfinite(values)):
        return float("nan"), float("nan")
    variance = float(np.var(values))
    if variance <= 1e-14 * max(1.0, float(np.mean(values**2))):
        return float("nan"), float("nan")
    slope = float(np.mean((values - values.mean()) * (y - y.mean())) / variance)
    return float(y.mean() - slope * values.mean()), slope


def _scaled_nrmse(
    tree: Tree, variables: dict[str, FloatArray], y: FloatArray, y_std: float
) -> float:
    intercept, slope = _linear_scaling(tree, variables, y)
    if not np.isfinite(slope):
        return float("inf")
    with np.errstate(all="ignore"):
        values = np.broadcast_to(_evaluate(tree, variables), y.shape)
    residual = y - (intercept + slope * values)
    return float(np.sqrt(np.mean(residual**2)) / y_std)


def _evaluate(tree: Tree, variables: dict[str, FloatArray]) -> FloatArray | float:
    kind = tree[0]
    if kind == "x":
        return variables[str(tree[1])]
    if kind == "c":
        return float(tree[1])
    if kind == "u":
        child = _evaluate(tree[2], variables)
        op = tree[1]
        if op == "square":
            return np.square(child)
        if op == "sqrt":
            return np.where(np.asarray(child) >= 0, np.sqrt(np.abs(child)), np.nan)
        if op == "exp":
            return np.where(np.asarray(child) < 50, np.exp(np.minimum(child, 50)), np.nan)
        if op == "log":
            return np.where(np.asarray(child) > 0, np.log(np.abs(child) + 1e-300), np.nan)
        if op == "inv":
            return np.where(np.abs(child) > 1e-12, 1.0 / np.where(child == 0, 1, child), np.nan)
        if op == "sin":
            return np.sin(child)
        if op == "cos":
            return np.cos(child)
        raise ValueError(f"Unknown unary operator: {op}")
    left = _evaluate(tree[2], variables)
    right = _evaluate(tree[3], variables)
    op = tree[1]
    if op == "+":
        return np.add(left, right)
    if op == "-":
        return np.subtract(left, right)
    if op == "*":
        return np.multiply(left, right)
    return np.where(np.abs(right) > 1e-12, np.divide(left, np.where(right == 0, 1, right)), np.nan)


def _render(tree: Tree) -> str:
    kind = tree[0]
    if kind == "x":
        return str(tree[1])
    if kind == "c":
        return f"{float(tree[1]):.6g}"
    if kind == "u":
        inner = _render(tree[2])
        op = tree[1]
        if op == "square":
            return f"({inner})**2"
        if op == "inv":
            return f"1/({inner})"
        return f"{op}({inner})"
    return f"({_render(tree[2])} {tree[1]} {_render(tree[3])})"


def _size(tree: Tree) -> int:
    if tree[0] in ("x", "c"):
        return 1
    if tree[0] == "u":
        return 1 + _size(tree[2])
    return 1 + _size(tree[2]) + _size(tree[3])


def _depth(tree: Tree) -> int:
    if tree[0] in ("x", "c"):
        return 1
    if tree[0] == "u":
        return 1 + _depth(tree[2])
    return 1 + max(_depth(tree[2]), _depth(tree[3]))


def _random_leaf(rng: np.random.Generator, names: Sequence[str]) -> Tree:
    if rng.random() < 0.7:
        return ("x", str(names[int(rng.integers(len(names)))]))
    return ("c", float(np.round(rng.choice([0.5, 1.0, 2.0, 3.0]) * rng.choice([-1, 1]), 3)))


def _random_tree(
    rng: np.random.Generator, names: Sequence[str], settings: SymbolicSearchSettings, depth: int
) -> Tree:
    if depth <= 1 or rng.random() < 0.25:
        return _random_leaf(rng, names)
    if rng.random() < 0.35 and settings.unary_ops:
        op = str(settings.unary_ops[int(rng.integers(len(settings.unary_ops)))])
        return ("u", op, _random_tree(rng, names, settings, depth - 1))
    op = BINARY_OPS[int(rng.integers(len(BINARY_OPS)))]
    return (
        "b",
        op,
        _random_tree(rng, names, settings, depth - 1),
        _random_tree(rng, names, settings, depth - 1),
    )


def _subtrees(tree: Tree, path: tuple[int, ...] = ()) -> list[tuple[int, ...]]:
    paths = [path]
    if tree[0] == "u":
        paths.extend(_subtrees(tree[2], (*path, 2)))
    elif tree[0] == "b":
        paths.extend(_subtrees(tree[2], (*path, 2)))
        paths.extend(_subtrees(tree[3], (*path, 3)))
    return paths


def _get(tree: Tree, path: tuple[int, ...]) -> Tree:
    for index in path:
        tree = tree[index]
    return tree


def _replace(tree: Tree, path: tuple[int, ...], new: Tree) -> Tree:
    if not path:
        return new
    items = list(tree)
    items[path[0]] = _replace(tree[path[0]], path[1:], new)
    return tuple(items)


def _pick(rng: np.random.Generator, tree: Tree) -> tuple[int, ...]:
    paths = _subtrees(tree)
    return paths[int(rng.integers(len(paths)))]


def _crossover(rng: np.random.Generator, first: Tree, second: Tree) -> Tree:
    return _replace(first, _pick(rng, first), _get(second, _pick(rng, second)))


def _subtree_mutation(
    rng: np.random.Generator, tree: Tree, names: Sequence[str], settings: SymbolicSearchSettings
) -> Tree:
    return _replace(tree, _pick(rng, tree), _random_tree(rng, names, settings, depth=3))


def _constant_mutation(rng: np.random.Generator, tree: Tree) -> Tree:
    constants = [path for path in _subtrees(tree) if _get(tree, path)[0] == "c"]
    if not constants:
        return tree
    path = constants[int(rng.integers(len(constants)))]
    value = float(_get(tree, path)[1])
    return _replace(tree, path, ("c", float(np.round(value * rng.normal(1.0, 0.3), 4))))


def _tournament(
    rng: np.random.Generator, population: Sequence[Tree], fitness: Sequence[float], size: int
) -> Tree:
    indices = rng.integers(len(population), size=size)
    best = min(indices, key=lambda index: fitness[int(index)])
    return population[int(best)]


def _pareto(hall: dict[str, tuple[int, float, Tree]]) -> list[FrontMember]:
    members = sorted(
        (FrontMember(key, size, nrmse) for key, (size, nrmse, _) in hall.items()),
        key=lambda member: (member.size, member.nrmse),
    )
    front: list[FrontMember] = []
    best_error = float("inf")
    for member in members:
        if member.nrmse < best_error - 1e-9:
            front.append(member)
            best_error = member.nrmse
    # Most accurate first, so a limited front keeps the strongest candidates.
    return sorted(front, key=lambda member: member.nrmse)


def _has_variable(tree: Tree) -> bool:
    if tree[0] == "x":
        return True
    if tree[0] == "c":
        return False
    return any(_has_variable(child) for child in tree[2:])


def _fresh(base: str, taken: set[str]) -> str:
    candidate, suffix = base, 2
    while candidate in taken:
        candidate = f"{base}_{suffix}"
        suffix += 1
    taken.add(candidate)
    return candidate


def _to_formula(
    tree: Tree,
    names: Sequence[str],
    target: str,
    index: int,
    intercept: float = 0.0,
    slope: float = 1.0,
) -> tuple[ModelFormula | None, dict[str, float]]:
    """Convert a tree into ``a + b * f(x; c1..ck)`` with every constant as a parameter."""
    taken = set(names)
    offset_name = _fresh("a", taken)
    scale_name = _fresh("b", taken)
    constants: list[tuple[str, float]] = []

    def lift(node: Tree) -> Tree:
        if node[0] in ("u", "b") and not _has_variable(node):
            with np.errstate(all="ignore"):
                folded = float(np.asarray(_evaluate(node, {})))
            if np.isfinite(folded):
                node = ("c", folded)
        if node[0] == "c":
            name = _fresh(f"c{len(constants) + 1}", taken)
            constants.append((name, float(node[1])))
            return ("x", name)
        if node[0] == "u":
            return ("u", str(node[1]), lift(node[2]))
        if node[0] == "b":
            return ("b", str(node[1]), lift(node[2]), lift(node[3]))
        return node

    body = _render(lift(tree))
    intercept = intercept if np.isfinite(intercept) else 0.0
    slope = slope if np.isfinite(slope) and slope != 0 else 1.0
    expression = f"{offset_name} + {scale_name} * ({body})"
    parameters = [
        ParameterSpec(
            offset_name, lower_bound=-np.inf, upper_bound=np.inf, initial_guess=intercept
        ),
        ParameterSpec(scale_name, lower_bound=-np.inf, upper_bound=np.inf, initial_guess=slope),
    ]
    start = {offset_name: intercept, scale_name: slope}
    for name, value in constants:
        parameters.append(
            ParameterSpec(name, lower_bound=-np.inf, upper_bound=np.inf, initial_guess=value)
        )
        start[name] = value
    try:
        formula = ModelFormula(
            name=f"symbolic_{index + 1}",
            expression=expression,
            parameters=parameters,
            independent_vars=list(names),
            dependent_var=target,
        )
    except ValueError:
        return None, start
    return formula, start
