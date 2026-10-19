"""Known-answer benchmarks: discovery must recover documented ground truth.

Ground truth is documented in examples/README.md and examples/generate_examples.py.
"""

import math
from pathlib import Path

import pytest

from scimodel.adapters.tabular_reader import read_table
from scimodel.application.discovery import DiscoveryOptions, discover
from scimodel.domain.discovery import DiscoveryResult

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
R_GAS = 8.314462618
FAST = DiscoveryOptions(engines=("library", "sparse", "symbolic"), time_budget=5)


def run(name: str, target: str, predictors: list[str], **options: object) -> DiscoveryResult:
    settings = DiscoveryOptions(**{**FAST.__dict__, **options})  # type: ignore[arg-type]
    return discover(
        read_table(EXAMPLES / name), target=target, predictors=predictors, options=settings
    )


def test_puromycin_recommends_michaelis_menten_with_certified_parameters() -> None:
    result = run("enzyme_kinetics_puromycin.csv", "reaction_velocity", ["substrate_conc"])
    best = result.best
    assert best is not None and best.name == "saturation_hyperbolic" and best.mechanistic
    assert abs(best.fit.parameters["Vmax"] - 212.684) < 0.5
    assert abs(best.fit.parameters["K"] - 0.06412) < 0.005
    assert abs(best.fit.metrics["rss"] - 1195.45) < 1.0
    assert result.quality[best.name].grade in ("A", "B")


def test_catalysis_rediscovers_arrhenius_activation_energy_and_order() -> None:
    result = run("catalysis_arrhenius.csv", "rate", ["temperature", "catalyst_loading"])
    best = result.best
    assert best is not None and "1/temperature" in best.expression
    assert "log(catalyst_loading)" in best.expression
    weights = best.fit.parameters
    activation = -min(weights.values()) * R_GAS  # coefficient of 1/T is -Ea/R
    order = next(v for k, v in weights.items() if 0.5 < v < 1.2)
    assert abs(activation - 58_000) / 58_000 < 0.03
    assert abs(order - 0.8) < 0.05
    assert result.dropped_rows == 1


def test_bacterial_growth_selects_gompertz_and_flags_heteroscedasticity() -> None:
    result = run("bacterial_growth_od600.csv", "od600", ["time"])
    best = result.best
    assert best is not None and best.name == "gompertz"
    values = sorted(best.fit.parameters.values())
    for truth in (0.05, 0.42, 1.32, 9.5):
        assert min(abs(v - truth) / truth for v in values) < 0.05
    statuses = {c.name: c.status for c in result.quality[best.name].checks}
    assert statuses["constant_variance"] == "warn"  # noise grows with OD by construction


def test_damped_oscillator_recovers_damping_and_frequency() -> None:
    result = run("damped_oscillator.csv", "displacement", ["time"])
    best = result.best
    assert best is not None and best.name == "damped_oscillation"
    assert abs(best.fit.parameters["gamma"] - 0.18) < 0.01
    assert abs(best.fit.parameters["omega"] - 2.6) < 0.01


def test_kepler_third_law_from_real_planetary_data() -> None:
    result = run("kepler_planets.csv", "orbital_period", ["semi_major_axis"])
    best = result.best
    assert best is not None and best.name == "power_law"
    assert abs(best.fit.parameters["k"] - 1.5) < 0.001
    assert abs(best.fit.parameters["A"] - 1.0) < 0.002


def test_kepler_flags_planet_mass_as_practically_irrelevant() -> None:
    result = run("kepler_planets.csv", "orbital_period", ["semi_major_axis", "mass"])
    best = result.best
    assert best is not None
    checks = {c.name: c for c in result.quality[best.name].checks}
    assert checks["predictor_relevance"].status == "warn"
    assert "mass" in str(checks["predictor_relevance"].value)


def test_exponential_decay_negative_control() -> None:
    result = run("non_kinetics_exponential_decay.csv", "concentration", ["time"])
    best = result.best
    assert best is not None and "exp" in best.expression
    rate = next(v for v in best.fit.parameters.values() if v < 0)
    assert abs(rate + 0.3) < 0.01


def test_discovery_is_reproducible_for_a_fixed_seed() -> None:
    first = run("damped_oscillator.csv", "displacement", ["time"], seed=7)
    second = run("damped_oscillator.csv", "displacement", ["time"], seed=7)
    assert [c.expression for c in first.candidates] == [c.expression for c in second.candidates]
    assert math.isclose(first.candidates[0].aicc, second.candidates[0].aicc)


def test_neural_ceiling_and_quality_on_full_pipeline() -> None:
    result = run(
        "enzyme_kinetics_advanced.csv",
        "reaction_velocity",
        ["substrate_conc"],
        engines=("library", "neural"),
    )
    assert result.neural_baseline is not None and result.neural_baseline["status"] == "ok"
    assert result.neural_baseline["cv_r_squared"] > 0.95
    names = {c.name for c in result.quality[result.best.name].checks}  # type: ignore[union-attr]
    assert "neural_ceiling_gap" in names


@pytest.mark.parametrize("engines", [("bogus",)])
def test_unknown_engine_is_rejected(engines: tuple[str, ...]) -> None:
    from scimodel.domain.dataset import DatasetError

    with pytest.raises(DatasetError, match="Unknown engine"):
        run("kepler_planets.csv", "orbital_period", ["semi_major_axis"], engines=engines)
