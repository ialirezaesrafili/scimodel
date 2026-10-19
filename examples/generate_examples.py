"""Regenerate SciModel's synthetic benchmark datasets with documented ground truth.

Run from the repository root:  python examples/generate_examples.py

Every dataset mimics a real laboratory export: units in headers, replicates,
heteroscedastic noise, metadata columns, a missing value, and occasionally an
outlier. Ground-truth parameters are listed in examples/README.md and checked
by the scientific test suite. The seed is fixed, so output is reproducible.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
R_GAS = 8.314462618


def write(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def arrhenius(rng: np.random.Generator) -> None:
    """Catalytic rate vs temperature and catalyst loading: k = A·exp(-Ea/RT)·C^0.8."""
    a_factor, ea, order = 2.4e7, 58_000.0, 0.8
    temperatures = np.linspace(298.15, 368.15, 8)
    loadings = (0.5, 1.0, 2.0, 4.0)
    rows: list[list[object]] = []
    run = 1
    for temperature in temperatures:
        for loading in loadings:
            for replicate in (1, 2):
                rate = a_factor * np.exp(-ea / (R_GAS * temperature)) * loading**order
                observed = rate * rng.lognormal(0.0, 0.04)
                rows.append(
                    [
                        f"R{run:03d}",
                        round(float(temperature), 2),
                        loading,
                        replicate,
                        f"{observed:.5g}",
                        rng.choice(["AK", "MB", "JS"]),
                    ]
                )
                run += 1
    rows[17][4] = ""  # a failed measurement
    rows[40][4] = f"{float(rows[40][4]) * 1.6:.5g}"  # one transcription outlier
    write(
        ROOT / "catalysis_arrhenius.csv",
        [
            "run_id",
            "temperature [K]",
            "catalyst_loading [mol%]",
            "replicate",
            "rate [mmol/(g*h)]",
            "operator",
        ],
        rows,
    )


def bacterial_growth(rng: np.random.Generator) -> None:
    """OD600 growth curves: Gompertz y = y0 + A·exp(-exp(-k(t - t_mid)))."""
    y0, amplitude, k, t_mid = 0.05, 1.32, 0.42, 9.5
    rows: list[list[object]] = []
    for well in ("A1", "A2", "A3"):
        for t in np.arange(0.0, 24.01, 0.75):
            mean = y0 + amplitude * np.exp(-np.exp(-k * (t - t_mid)))
            observed = mean + rng.normal(0.0, 0.006 + 0.025 * mean)
            rows.append([round(float(t), 2), well, f"{max(observed, 0.001):.4f}", 37.0])
    write(
        ROOT / "bacterial_growth_od600.csv",
        ["time [h]", "well", "od600", "incubator_temp [C]"],
        rows,
    )


def damped_oscillator(rng: np.random.Generator) -> None:
    """Mass–spring–damper displacement: x = A·exp(-γt)·cos(ωt + φ) + offset."""
    amplitude, gamma, omega, phase, offset = 12.0, 0.18, 2.6, 0.4, 0.3
    rows: list[list[object]] = []
    for t in np.linspace(0.0, 20.0, 160):
        x = offset + amplitude * np.exp(-gamma * t) * np.cos(omega * t + phase)
        rows.append([round(float(t), 4), f"{x + rng.normal(0.0, 0.25):.4f}"])
    write(ROOT / "damped_oscillator.csv", ["time [s]", "displacement [mm]"], rows)


def main() -> None:
    rng = np.random.default_rng(20261019)
    arrhenius(rng)
    bacterial_growth(rng)
    damped_oscillator(rng)


if __name__ == "__main__":
    main()
