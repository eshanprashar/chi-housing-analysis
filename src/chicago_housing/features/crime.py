"""Crime features — EXTERNAL dataset join (own spatial grain + time axis).

STUB. Built when the crime teaser lands (Post 1.1 teaser -> standalone post).
Unlike derive.py / spatial.py, integrating crime means joining a SECOND source
with its own geography and date axis, and aligning each sale's date to a crime
window. That join will leave unmatched rows (no geography / outside time
coverage); the drop-vs-flag decision for those is CLEANING's job and should be
handed back to clean.py rather than done here — see context.md.
"""

from __future__ import annotations

import pandas as pd


def add_crime_features(df: pd.DataFrame) -> pd.DataFrame:
    """TODO: join community-area/tract crime rate onto each sale (1.1 teaser)."""
    raise NotImplementedError("crime features arrive with the crime teaser")