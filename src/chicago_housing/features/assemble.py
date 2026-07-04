"""Assemble the modeling frame: analytic sample + engineered feature columns.

The ONE orchestrator the notebook calls. Cleaning defines the ROWS (upstream, via
clean.build_analytic_sample); this adds the COLUMN transforms and returns the
frame the regression reads. Crime is intentionally NOT wired in yet (stub).
"""

from __future__ import annotations

import pandas as pd

from chicago_housing.features import derive, spatial


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add all engineered columns to an already-cleaned analytic sample."""
    out = spatial.add_distance_to_loop(df)
    out = derive.add_no_rated_school_flag(out)
    return out