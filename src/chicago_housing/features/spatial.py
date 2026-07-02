"""Spatial features. distance-to-Loop is our monocentric differentiator — CCAO
has no explicit CBD distance, so this column is original to our analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
from pyproj import Transformer

# Loop reference point (Chicago CBD)
LOOP_LAT, LOOP_LON = 41.8786, -87.6359
# NAD83 / Illinois East (ftUS) — the CRS of loc_x_3435 / loc_y_3435 in the data
EPSG_ISP_EAST = 3435


def _loop_xy_3435() -> tuple[float, float]:
    """Project the Loop point into the same state-plane CRS as the parcel coords."""
    tf = Transformer.from_crs(4326, EPSG_ISP_EAST, always_xy=True)
    return tf.transform(LOOP_LON, LOOP_LAT)


def add_distance_to_loop(
    df: pd.DataFrame, x: str = "loc_x_3435", y: str = "loc_y_3435"
) -> pd.DataFrame:
    """Add `dist_to_loop_ft`: straight-line distance (feet) to the Loop.

    Uses the projected coords already in the data, so units match the other
    prox_*_dist_ft features (feet).
    """
    out = df.copy()
    lx, ly = _loop_xy_3435()
    out["dist_to_loop_ft"] = np.sqrt(
        (pd.to_numeric(out[x], errors="coerce") - lx) ** 2
        + (pd.to_numeric(out[y], errors="coerce") - ly) ** 2
    )
    return out
