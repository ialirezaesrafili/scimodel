"""Domain equations for the approved enzyme-kinetics workflow."""

from __future__ import annotations

import numpy as np


def michaelis_menten(substrate: np.ndarray, vmax: float, km: float) -> np.ndarray:
    """Calculate reaction velocity using the Michaelis–Menten equation."""
    return (vmax * substrate) / (km + substrate)
