"""Domain equations for the approved enzyme-kinetics workflow."""

from __future__ import annotations

from typing import cast

import numpy as np
import numpy.typing as npt


def michaelis_menten(
    substrate: npt.NDArray[np.float64], vmax: float, km: float
) -> npt.NDArray[np.float64]:
    """Calculate reaction velocity using the Michaelis–Menten equation."""
    values = (vmax * substrate) / (km + substrate)
    return cast(npt.NDArray[np.float64], values)
