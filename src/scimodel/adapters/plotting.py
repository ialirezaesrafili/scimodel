"""Optional figure rendering with matplotlib (install ``scimodel[plots]``)."""

from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

import numpy as np
import numpy.typing as npt

FloatArray: TypeAlias = npt.NDArray[np.float64]


def plotting_available() -> bool:
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        return False
    return True


def render_figures(
    output_dir: Path,
    *,
    x: FloatArray | None,
    x_label: str,
    y: FloatArray,
    y_label: str,
    fitted: FloatArray,
    curve_x: FloatArray | None,
    curve_y: FloatArray | None,
    pareto: list[tuple[int, float, str]],
) -> dict[str, str]:
    """Write fit, residual, and Pareto figures; return name→relative path."""
    if not plotting_available():
        return {}
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures: dict[str, str] = {}
    output_dir.mkdir(parents=True, exist_ok=True)

    if x is not None and curve_x is not None and curve_y is not None:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(x, y, s=18, color="#2b6cb0", label="observations")
        ax.plot(curve_x, curve_y, color="#c05621", linewidth=2, label="best model")
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.legend(frameon=False)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(output_dir / "fit.png", dpi=150)
        plt.close(fig)
        figures["fit"] = "figures/fit.png"

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(fitted, y - fitted, s=18, color="#2b6cb0")
    ax.axhline(0.0, color="#4a5568", linewidth=1)
    ax.set_xlabel(f"fitted {y_label}")
    ax.set_ylabel("residual")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "residuals.png", dpi=150)
    plt.close(fig)
    figures["residuals"] = "figures/residuals.png"

    if len(pareto) > 1:
        fig, ax = plt.subplots(figsize=(6, 4))
        complexity = [item[0] for item in pareto]
        error = [item[1] for item in pareto]
        ax.plot(complexity, error, marker="o", color="#2f855a")
        for c, e, name in pareto:
            ax.annotate(name, (c, e), fontsize=7, xytext=(3, 3), textcoords="offset points")
        ax.set_xlabel("complexity (expression nodes)")
        ax.set_ylabel("cross-validated RMSE")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(output_dir / "pareto.png", dpi=150)
        plt.close(fig)
        figures["pareto"] = "figures/pareto.png"
    return figures
