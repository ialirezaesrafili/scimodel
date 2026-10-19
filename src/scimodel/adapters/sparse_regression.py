"""Sparse regression over a library of candidate terms (SINDy-style discovery).

The engine builds interpretable features of the predictors (powers, logs,
reciprocals, square roots, pairwise products) and selects the smallest subset
that explains the target, using exhaustive search for small subsets and BIC
to stop adding terms. It runs twice: on the raw target, and on ``log(target)``
when the target is strictly positive. The log variant finds multiplicative
laws such as power laws and Arrhenius relationships, ``k = A·exp(-E/RT)·C^n``,
as linear combinations of ``1/T`` and ``log C``.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

import numpy as np
import numpy.typing as npt

from scimodel.domain.discovery import CandidateProposal
from scimodel.domain.formula import ModelFormula, ParameterSpec

FloatArray: TypeAlias = npt.NDArray[np.float64]


@dataclass(frozen=True)
class Term:
    expression: str
    values: FloatArray


@dataclass(frozen=True)
class SparseSettings:
    max_terms: int = 3
    exhaustive_limit: int = 40
    include_products: bool = True


class SparseRegressor:
    """Best-subset regression over interpretable features with BIC selection."""

    def __init__(self, settings: SparseSettings | None = None) -> None:
        self.settings = settings or SparseSettings()

    def propose(
        self, variables: dict[str, FloatArray], y: FloatArray, *, target: str = "y"
    ) -> list[CandidateProposal]:
        terms = build_library(variables, include_products=self.settings.include_products)
        proposals: list[CandidateProposal] = []
        names = list(variables)
        for log_target in (False, True):
            if log_target and not np.all(y > 0):
                continue
            response = np.log(y) if log_target else y
            for selected, coefficients in self._best_subsets(terms, response):
                proposal = _proposal(
                    selected,
                    coefficients,
                    names,
                    target,
                    log_target,
                    len(proposals) + 1,
                    search_space=2 * math.comb(len(terms), len(selected)),
                )
                if proposal is not None:
                    proposals.append(proposal)
        return proposals

    def _best_subsets(
        self, terms: Sequence[Term], y: FloatArray
    ) -> list[tuple[tuple[Term, ...], FloatArray]]:
        """Return the best model for each subset size up to the BIC stopping point."""
        n = len(y)
        results: list[tuple[tuple[Term, ...], FloatArray]] = []
        previous_bic = math.inf
        max_terms = min(self.settings.max_terms, max(1, n - 3))
        for size in range(1, max_terms + 1):
            combinations = math.comb(len(terms), size)
            if combinations <= 20000 and len(terms) <= self.settings.exhaustive_limit:
                subsets: Sequence[tuple[Term, ...]] = list(itertools.combinations(terms, size))
            elif results:
                # Greedy forward extension of the previous best subset.
                base = results[-1][0]
                subsets = [(*base, term) for term in terms if term not in base]
            else:
                subsets = [(term,) for term in terms]
            best: tuple[float, tuple[Term, ...], FloatArray] | None = None
            for subset in subsets:
                fitted = _least_squares(subset, y)
                if fitted is None:
                    continue
                rss, coefficients = fitted
                if best is None or rss < best[0]:
                    best = (rss, subset, coefficients)
            if best is None:
                break
            rss = max(best[0], 1e-300)
            bic = n * math.log(rss / n) + (size + 1) * math.log(n)
            if bic > previous_bic - 2.0:
                break
            previous_bic = bic
            results.append((best[1], best[2]))
        return results


def build_library(variables: dict[str, FloatArray], *, include_products: bool = True) -> list[Term]:
    """Return finite, non-constant candidate features for each predictor."""
    terms: list[Term] = []
    with np.errstate(all="ignore"):
        for name, x in variables.items():
            candidates = [
                (name, x),
                (f"{name}**2", x**2),
                (f"{name}**3", x**3),
            ]
            if np.all(x >= 0):
                candidates.append((f"sqrt({name})", np.sqrt(x)))
            if np.all(x > 0):
                candidates.append((f"log({name})", np.log(x)))
            if np.all(x != 0):
                candidates.append((f"(1/{name})", 1.0 / x))
            scale = float(np.max(np.abs(x))) or 1.0
            if scale > 0:
                candidates.append((f"exp(-{name}/{scale:.6g})", np.exp(-x / scale)))
            terms.extend(Term(expr, values) for expr, values in candidates)
        if include_products and len(variables) > 1:
            for (first, x1), (second, x2) in itertools.combinations(variables.items(), 2):
                terms.append(Term(f"{first}*{second}", x1 * x2))
                if np.all(x2 != 0):
                    terms.append(Term(f"{first}/{second}", x1 / x2))
    unique: dict[bytes, Term] = {}
    for term in terms:
        values = np.asarray(term.values, dtype=np.float64)
        if not np.all(np.isfinite(values)) or float(np.ptp(values)) == 0.0:
            continue
        unique.setdefault(np.round(values, 12).tobytes(), Term(term.expression, values))
    return list(unique.values())


def _least_squares(subset: Sequence[Term], y: FloatArray) -> tuple[float, FloatArray] | None:
    design = np.column_stack([np.ones_like(y), *[term.values for term in subset]])
    if np.linalg.matrix_rank(design) < design.shape[1]:
        return None
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    residual = y - design @ coefficients
    return float(residual @ residual), coefficients


def _proposal(
    subset: Sequence[Term],
    coefficients: FloatArray,
    names: Sequence[str],
    target: str,
    log_target: bool,
    index: int,
    *,
    search_space: int = 1,
) -> CandidateProposal | None:
    taken = set(names)
    parameter_names: list[str] = []
    for position in range(len(subset) + 1):
        candidate, suffix = f"w{position}", 2
        while candidate in taken:
            candidate = f"w{position}_{suffix}"
            suffix += 1
        taken.add(candidate)
        parameter_names.append(candidate)
    linear = " + ".join(
        [parameter_names[0]]
        + [f"{parameter_names[i + 1]}*{term.expression}" for i, term in enumerate(subset)]
    )
    expression = f"exp({linear})" if log_target else linear
    start = {name: float(value) for name, value in zip(parameter_names, coefficients, strict=True)}
    try:
        formula = ModelFormula(
            name=f"sparse_{'log_' if log_target else ''}{index}",
            expression=expression,
            parameters=[
                ParameterSpec(name, lower_bound=-np.inf, upper_bound=np.inf, initial_guess=value)
                for name, value in start.items()
            ],
            independent_vars=list(names),
            dependent_var=target,
        )
    except ValueError:
        return None
    space = "log-scale target (multiplicative law)" if log_target else "linear-in-terms model"
    return CandidateProposal(
        formula=formula,
        origin="sparse",
        rationale=(
            f"Selected by best-subset sparse regression ({len(subset)} term(s), {space}) "
            "from a library of powers, logarithms, reciprocals, and products."
        ),
        starts=(start,),
        search_space=max(search_space, 1),
    )
