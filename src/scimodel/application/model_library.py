"""Library of established scientific model families with data-driven initialization.

Each template turns a predictor/target pair into a fit-ready
:class:`CandidateProposal`. Starting values are derived from the data
(linearizations, plateaus, half-maximum points, dominant frequencies), and
several starts are supplied where the likelihood surface is multimodal.
Templates are proposed only when the data satisfy their mathematical domain
(e.g. positivity for power laws), never on name alone.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Sequence
from typing import TypeAlias

import numpy as np
import numpy.typing as npt

from scimodel.application.profiling import RelationshipSummary, dominant_frequency
from scimodel.domain.discovery import CandidateProposal
from scimodel.domain.formula import ModelFormula, ParameterSpec

FloatArray: TypeAlias = npt.NDArray[np.float64]
INF = math.inf


class _Names:
    """Allocate parameter names that never collide with variable names."""

    def __init__(self, taken: Sequence[str]) -> None:
        self.taken = set(taken)

    def __call__(self, base: str) -> str:
        candidate, suffix = base, 2
        while candidate in self.taken:
            candidate = f"{base}_{suffix}"
            suffix += 1
        self.taken.add(candidate)
        return candidate


def _proposal(
    name: str,
    expression: str,
    parameters: list[ParameterSpec],
    variables: Sequence[str],
    target: str,
    rationale: str,
    assumptions: Sequence[str],
    starts: Sequence[dict[str, float]] = (),
    *,
    mechanistic: bool = True,
) -> CandidateProposal | None:
    try:
        formula = ModelFormula(
            name=name,
            expression=expression,
            parameters=parameters,
            independent_vars=list(variables),
            dependent_var=target,
            assumptions=tuple(assumptions),
        )
    except ValueError:
        return None
    clean_starts = tuple(
        start for start in starts if all(math.isfinite(value) for value in start.values())
    )
    return CandidateProposal(formula, "library", rationale, clean_starts, mechanistic)


def _free(name: str, guess: float) -> ParameterSpec:
    return ParameterSpec(name, -INF, INF, guess if math.isfinite(guess) else 1.0)


def _positive(name: str, guess: float, upper: float = INF) -> ParameterSpec:
    value = guess if math.isfinite(guess) and guess > 0 else 1.0
    return ParameterSpec(name, 0.0, upper, min(value, upper * 0.999) if upper < INF else value)


def _half_point(x: FloatArray, y: FloatArray) -> float:
    order = np.argsort(x)
    xs, ys = x[order], y[order]
    middle = ys.min() + 0.5 * np.ptp(ys)
    index = int(np.argmin(np.abs(ys - middle)))
    return float(xs[index])


def univariate_templates(
    x_name: str,
    x: FloatArray,
    y: FloatArray,
    target: str,
    relationship: RelationshipSummary | None = None,
    role: str = "measurement",
) -> list[CandidateProposal]:
    """Return applicable single-predictor model families for ``target = f(x)``."""
    names = _Names([x_name])
    hints = set(relationship.hints) if relationship else set()
    x_range = float(np.ptp(x)) or 1.0
    y_range = float(np.ptp(y)) or 1.0
    positive_x = bool(np.all(x > 0))
    nonnegative_x = bool(np.all(x >= 0))
    positive_y = bool(np.all(y > 0))
    order = np.argsort(x)
    y_first = float(np.mean(y[order][: max(2, len(y) // 8)]))
    y_last = float(np.mean(y[order][-max(2, len(y) // 8) :]))
    proposals: list[CandidateProposal | None] = []
    builders: list[Callable[[], CandidateProposal | None]] = []

    def linear() -> CandidateProposal | None:
        b1, b0 = np.polyfit(x, y, 1)
        p0, p1 = names("b0"), names("b1")
        return _proposal(
            "linear",
            f"{p0} + {p1}*{x_name}",
            [_free(p0, b0), _free(p1, b1)],
            [x_name],
            target,
            "Straight-line baseline; every richer model should beat it convincingly.",
            ("The response changes at a constant rate.",),
            mechanistic=False,
        )

    def quadratic() -> CandidateProposal | None:
        b2, b1, b0 = np.polyfit(x, y, 2)
        p0, p1, p2 = names("b0"), names("b1"), names("b2")
        return _proposal(
            "quadratic",
            f"{p0} + {p1}*{x_name} + {p2}*{x_name}**2",
            [_free(p0, b0), _free(p1, b1), _free(p2, b2)],
            [x_name],
            target,
            "Second-order polynomial; captures curvature or a single optimum.",
            ("Empirical approximation; parameters rarely have physical meaning.",),
            mechanistic=False,
        )

    builders += [linear, quadratic]

    if positive_x:

        def power_law() -> CandidateProposal | None:
            if positive_y:
                k, log_a = np.polyfit(np.log(x), np.log(y), 1)
                amplitude = math.exp(log_a)
            else:
                k, amplitude = 1.0, float(np.mean(y) / np.mean(x))
            pa, pk = names("A"), names("k")
            return _proposal(
                "power_law",
                f"{pa} * {x_name}**{pk}",
                [_free(pa, amplitude), _free(pk, k)],
                [x_name],
                target,
                "Scale-free power law y = A·x^k (allometry, Kepler, Freundlich, flow laws).",
                ("Relative change in y is proportional to relative change in x.",),
            )

        def logarithmic() -> CandidateProposal | None:
            b1, b0 = np.polyfit(np.log(x), y, 1)
            p0, p1 = names("b0"), names("b1")
            return _proposal(
                "logarithmic",
                f"{p0} + {p1}*log({x_name})",
                [_free(p0, b0), _free(p1, b1)],
                [x_name],
                target,
                "Logarithmic response (Weber–Fechner, Nernst-type relationships).",
                ("Each multiplicative increase in x adds a constant amount to y.",),
                mechanistic=False,
            )

        def reciprocal() -> CandidateProposal | None:
            b1, b0 = np.polyfit(1.0 / x, y, 1)
            p0, p1 = names("b0"), names("b1")
            return _proposal(
                "reciprocal",
                f"{p0} + {p1}/{x_name}",
                [_free(p0, b0), _free(p1, b1)],
                [x_name],
                target,
                "Inverse relationship approaching an asymptote at large x.",
                ("The effect of x diminishes as 1/x.",),
                mechanistic=False,
            )

        builders += [power_law, logarithmic, reciprocal]
        if positive_y and len(np.unique(x)) >= 4:

            def power_offset() -> CandidateProposal | None:
                k, log_a = np.polyfit(np.log(x), np.log(y), 1)
                py, pa, pk = names("y0"), names("A"), names("k")
                return _proposal(
                    "power_law_offset",
                    f"{py} + {pa} * {x_name}**{pk}",
                    [_free(py, 0.0), _free(pa, math.exp(log_a)), _free(pk, k)],
                    [x_name],
                    target,
                    "Power law with a baseline offset.",
                    ("A constant background adds to a scale-free response.",),
                    mechanistic=False,
                )

            builders.append(power_offset)

    def exponential() -> CandidateProposal | None:
        if positive_y:
            k, log_a = np.polyfit(x, np.log(y), 1)
            amplitude = math.exp(log_a)
        else:
            k, amplitude = 0.0, float(np.mean(y))
        pa, pk = names("A"), names("k")
        return _proposal(
            "exponential",
            f"{pa} * exp({pk}*{x_name})",
            [_free(pa, amplitude), _free(pk, k)],
            [x_name],
            target,
            "Exponential growth or decay (first-order kinetics, radioactive decay, "
            "unconstrained growth).",
            ("The rate of change is proportional to the current value.",),
        )

    def exp_plateau() -> CandidateProposal | None:
        p_inf, p_0, p_k = names("y_inf"), names("y_start"), names("k")
        x_min = float(np.min(x))
        expression = f"{p_inf} + ({p_0} - {p_inf}) * exp(-{p_k}*({x_name} - {x_min:.10g}))"
        starts = [
            {p_inf: y_last, p_0: y_first, p_k: factor / x_range} for factor in (0.5, 2.0, 6.0)
        ]
        return _proposal(
            "exponential_plateau",
            expression,
            [_free(p_inf, y_last), _free(p_0, y_first), _positive(p_k, 2.0 / x_range)],
            [x_name],
            target,
            "First-order approach to a plateau (relaxation, charging, Newton cooling, "
            "drug elimination to baseline, one-phase association).",
            ("A single first-order process governs the approach to equilibrium.",),
            starts,
        )

    builders += [exponential, exp_plateau]

    if nonnegative_x and np.all(y >= 0) and ("saturating" in hints or y_last > y_first):

        def saturation() -> CandidateProposal | None:
            vmax = float(np.max(y)) * 1.2
            half = max(_half_point(x, y), x_range * 0.05)
            pv, pk = names("Vmax"), names("K")
            return _proposal(
                "saturation_hyperbolic",
                f"{pv}*{x_name}/({pk} + {x_name})",
                [_positive(pv, vmax), _positive(pk, half)],
                [x_name],
                target,
                "Rectangular hyperbola: Michaelis–Menten enzyme kinetics, Langmuir adsorption, "
                "Monod growth, receptor binding.",
                (
                    "Single binding site or rate-limiting step; no cooperativity.",
                    "Quasi-steady state holds over the measurement window.",
                ),
                [{pv: vmax, pk: half}, {pv: vmax * 2, pk: half * 3}],
            )

        builders.append(saturation)
        if positive_x and len(np.unique(x)) >= 5:

            def hill() -> CandidateProposal | None:
                vmax = float(np.max(y)) * 1.1
                half = max(_half_point(x, y), x_range * 0.05)
                pv, pk, pn = names("Vmax"), names("K"), names("n")
                return _proposal(
                    "hill",
                    f"{pv}*{x_name}**{pn}/({pk}**{pn} + {x_name}**{pn})",
                    [_positive(pv, vmax), _positive(pk, half), ParameterSpec(pn, 0.1, 10.0, 1.0)],
                    [x_name],
                    target,
                    "Hill equation: cooperative binding or sigmoidal dose response.",
                    ("n > 1 indicates positive cooperativity; n = 1 reduces to a hyperbola.",),
                    [{pv: vmax, pk: half, pn: n} for n in (0.7, 1.0, 2.0, 3.0)],
                )

            builders.append(hill)

    if len(np.unique(x)) >= 6:
        step = y_last - y_first
        mid = _half_point(x, y)

        def logistic() -> CandidateProposal | None:
            py, pl, pk, px = names("y_low"), names("L"), names("k"), names("x_mid")
            starts = [
                {py: min(y_first, y_last), pl: abs(step) or y_range, pk: s * f / x_range, px: mid}
                for s in (1.0, -1.0)
                for f in (4.0, 10.0)
            ]
            return _proposal(
                "logistic",
                f"{py} + {pl}/(1 + exp(-{pk}*({x_name} - {px})))",
                [
                    _free(py, starts[0][py]),
                    _free(pl, starts[0][pl]),
                    _free(pk, 4.0 / x_range),
                    _free(px, mid),
                ],
                [x_name],
                target,
                "Four-parameter logistic: population growth with carrying capacity, "
                "dose–response, phase transitions.",
                ("Growth slows symmetrically as the response approaches its capacity.",),
                starts,
            )

        def gompertz() -> CandidateProposal | None:
            py, pa, pk, px = names("y_low"), names("A"), names("k"), names("x_mid")
            starts = [
                {py: y_first, pa: step or y_range, pk: f / x_range, px: mid} for f in (2.0, 6.0)
            ]
            return _proposal(
                "gompertz",
                f"{py} + {pa}*exp(-exp(-{pk}*({x_name} - {px})))",
                [
                    _free(py, y_first),
                    _free(pa, step or y_range),
                    _free(pk, 3.0 / x_range),
                    _free(px, mid),
                ],
                [x_name],
                target,
                "Gompertz curve: asymmetric sigmoidal growth (microbial growth with lag, "
                "tumour growth).",
                ("Growth decelerates exponentially; the inflection is below half capacity.",),
                starts,
            )

        if "sigmoidal" in hints or "saturating" in hints or abs(np.corrcoef(x, y)[0, 1]) > 0.7:
            builders += [logistic, gompertz]

    if hints & {"peak", "valley"}:

        def gaussian() -> CandidateProposal | None:
            baseline = float(np.median(y))
            extreme = int(np.argmax(np.abs(y - baseline)))
            py, pa, pm, ps = names("y0"), names("A"), names("mu"), names("sigma")
            return _proposal(
                "gaussian_peak",
                f"{py} + {pa}*exp(-({x_name} - {pm})**2/(2*{ps}**2))",
                [
                    _free(py, float(np.min(y)) if "peak" in hints else float(np.max(y))),
                    _free(pa, float(y[extreme] - baseline)),
                    _free(pm, float(x[extreme])),
                    _positive(ps, x_range / 6),
                ],
                [x_name],
                target,
                "Gaussian peak (spectral lines, chromatography, optimum curves).",
                ("The response is symmetric around a single optimum.",),
                mechanistic=False,
            )

        builders.append(gaussian)

    if "oscillating" in hints or (relationship and relationship.scores.get("periodicity", 0) > 0.3):
        omega = dominant_frequency(x, y)
        amplitude = float(np.std(y)) * math.sqrt(2)
        center = float(np.mean(y))
        phases = (0.0, math.pi / 2, math.pi, 3 * math.pi / 2)

        def sinusoid() -> CandidateProposal | None:
            py, pa, pw, pp = names("y0"), names("A"), names("omega"), names("phi")
            return _proposal(
                "sinusoid",
                f"{py} + {pa}*sin({pw}*{x_name} + {pp})",
                [_free(py, center), _free(pa, amplitude), _positive(pw, omega), _free(pp, 0.0)],
                [x_name],
                target,
                "Harmonic oscillation (waves, circadian rhythms, AC signals).",
                ("A single frequency with constant amplitude.",),
                [{py: center, pa: amplitude, pw: omega, pp: phase} for phase in phases],
            )

        def damped() -> CandidateProposal | None:
            py, pa, pg, pw, pp = (
                names("y0"),
                names("A"),
                names("gamma"),
                names("omega"),
                names("phi"),
            )
            starts = [
                {py: center, pa: amplitude * 1.5, pg: g / x_range, pw: omega, pp: phase}
                for g in (0.1, 1.0, 3.0)
                for phase in phases
            ]
            return _proposal(
                "damped_oscillation",
                f"{py} + {pa}*exp(-{pg}*{x_name})*cos({pw}*{x_name} + {pp})",
                [
                    _free(py, center),
                    _free(pa, amplitude),
                    _positive(pg, 1.0 / x_range),
                    _positive(pw, omega),
                    _free(pp, 0.0),
                ],
                [x_name],
                target,
                "Underdamped harmonic oscillator (mechanical vibration, RLC circuits).",
                ("Linear restoring force with viscous damping.",),
                starts,
            )

        builders += [sinusoid, damped]

    if positive_x and positive_y and (role == "temperature" or 150 <= float(np.min(x)) <= 3000):

        def arrhenius() -> CandidateProposal | None:
            t_ref = float(np.mean(x))
            slope, intercept = np.polyfit(1.0 / x - 1.0 / t_ref, np.log(y), 1)
            pk, pe = names("k_ref"), names("Ea_over_R")
            return _proposal(
                "arrhenius",
                f"{pk}*exp(-{pe}*(1/{x_name} - 1/{t_ref:.10g}))",
                [_positive(pk, math.exp(intercept)), _free(pe, -slope)],
                [x_name],
                target,
                "Arrhenius law (centred at the mean temperature for numerical stability); "
                "activation energy Ea = Ea_over_R × 8.314 J/mol when x is in kelvin.",
                (
                    "Temperature is absolute (kelvin).",
                    "A single rate-limiting step with temperature-independent Ea.",
                ),
            )

        builders.append(arrhenius)

    for build in builders:
        names.taken = {x_name}  # fresh parameter names for every template
        try:
            proposals.append(build())
        except (np.linalg.LinAlgError, ValueError, ZeroDivisionError, FloatingPointError):
            continue
    return [proposal for proposal in proposals if proposal is not None]


def multivariate_templates(
    variables: dict[str, FloatArray], y: FloatArray, target: str
) -> list[CandidateProposal]:
    """Return additive and multiplicative baselines that use every predictor."""
    if len(variables) < 2:
        return []
    names = _Names(list(variables))
    proposals: list[CandidateProposal | None] = []
    x = np.column_stack(list(variables.values()))
    design = np.column_stack([np.ones(len(y)), x])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    weights = [names("b0"), *[names(f"b_{name}") for name in variables]]
    terms = " + ".join(f"{w}*{v}" for w, v in zip(weights[1:], variables, strict=True))
    proposals.append(
        _proposal(
            "linear_multivariable",
            f"{weights[0]} + {terms}",
            [_free(w, c) for w, c in zip(weights, coefficients, strict=True)],
            list(variables),
            target,
            "Additive linear model in all predictors (multiple regression baseline).",
            ("Effects of predictors add independently and linearly.",),
            mechanistic=False,
        )
    )
    if np.all(y > 0) and all(np.all(values > 0) for values in variables.values()):
        names.taken = set(variables)
        log_design = np.column_stack([np.ones(len(y)), np.log(x)])
        log_coefficients, *_ = np.linalg.lstsq(log_design, np.log(y), rcond=None)
        pa = names("A")
        exponents = [names(f"k_{name}") for name in variables]
        product = "*".join(f"{v}**{e}" for v, e in zip(variables, exponents, strict=True))
        proposals.append(
            _proposal(
                "power_product",
                f"{pa}*{product}",
                [_free(pa, math.exp(log_coefficients[0]))]
                + [_free(e, c) for e, c in zip(exponents, log_coefficients[1:], strict=True)],
                list(variables),
                target,
                "Multiplicative power law (rate laws with reaction orders, scaling laws, "
                "Cobb–Douglas forms).",
                ("Each predictor acts multiplicatively with a constant elasticity.",),
            )
        )
    for first, second in itertools.combinations(list(variables)[:3], 2):
        names.taken = set(variables)
        b0, b1, b2, b3 = names("b0"), names("b1"), names("b2"), names("b12")
        design = np.column_stack(
            [
                np.ones(len(y)),
                variables[first],
                variables[second],
                variables[first] * variables[second],
            ]
        )
        start, *_ = np.linalg.lstsq(design, y, rcond=None)
        proposals.append(
            _proposal(
                f"interaction_{first}_{second}",
                f"{b0} + {b1}*{first} + {b2}*{second} + {b3}*{first}*{second}",
                [_free(p, c) for p, c in zip((b0, b1, b2, b3), start, strict=True)],
                list(variables),
                target,
                f"Linear model with a {first}×{second} interaction.",
                ("The effect of one predictor depends linearly on the other.",),
                mechanistic=False,
            )
        )
    return [proposal for proposal in proposals if proposal is not None]
