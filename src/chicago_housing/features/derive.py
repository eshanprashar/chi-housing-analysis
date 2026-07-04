"""Row-local feature derivation — columns built purely from existing parquet columns.

Scope discipline: every function takes a frame and RETURNS it with columns added.
No row drops (that's clean.py), no external data (that's crime.py), no geometry
(that's spatial.py). If a transform needs any of those, it doesn't belong here.
"""

from __future__ import annotations

import pandas as pd

from chicago_housing import config as C


def add_no_rated_school_flag(df: pd.DataFrame) -> pd.DataFrame:
    """Add `no_rated_school_nearby` and fill the raw school-rating column.

    Mechanism (verified in EDA): the rating is null IFF there are zero *rated*
    schools within a half-mile. So the flag is a POSITIVE FACT derived from the
    rated-school count, not from the null. The raw rating is then filled with a
    constant purely so the regression has a number — the flag absorbs the
    difference for those rows, so the fill value is immaterial (median keeps the
    observed distribution readable).
    """
    out = df.copy()
    rated_count = pd.to_numeric(out[C.SCHOOL_RATED_COUNT], errors="coerce")
    out[C.NO_RATED_SCHOOL_FLAG] = (rated_count == 0).astype(int)
    out[C.SCHOOL_RATING] = out[C.SCHOOL_RATING].fillna(out[C.SCHOOL_RATING].median())
    return out