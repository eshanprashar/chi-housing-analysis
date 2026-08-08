"""Row-local feature derivation — columns built purely from existing parquet columns.

Scope discipline: every function takes a frame and RETURNS it with columns added.
No row drops (that's clean.py), no external data (that's crime.py), no geometry
(that's spatial.py). If a transform needs any of those, it doesn't belong here.
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from chicago_housing import constants as K

# curved-effect predictors -> log. Distances use log1p (they contain zeros).
LOG_PLAIN = [
    "char_bldg_sf", 
    "char_land_sf", 
    "acs5_median_income_household_past_year"
    ]
LOG_1P = [c for c in K.BLOCK_B_LOCATION if c == "dist_to_loop_ft" or c.endswith("_dist_ft")]


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
    rated_count = pd.to_numeric(out[K.SCHOOL_RATED_COUNT], errors="coerce")
    out[K.NO_RATED_SCHOOL_FLAG] = (rated_count == 0).astype(int)
    out[K.SCHOOL_RATING] = out[K.SCHOOL_RATING].fillna(out[K.SCHOOL_RATING].median())
    return out

def add_gar1_exists_flag(df: pd.DataFrame) -> pd.DataFrame:
    """Add `char_gar1_exists`: 1 if the parcel has a garage, 0 if not, <NA> if unknown.

    CCAO codes "no garage" as the recoded label "0 cars" (raw code 7), so existence
    is "anything but '0 cars'". Run this AFTER clean.recode_categoricals — it reads
    the human-readable label, not the raw numeric code.

    Nullable ON PURPOSE: ~15 rows have a NULL garage size and char_gar1_att can't
    disambiguate them — its "No" means "not *attached*", which covers both no-garage
    AND detached-garage homes (20k two-car garages are also "No"). So we do NOT
    assert 0 there; existence is genuinely unknown and stays <NA> (pandas nullable
    Int64) for the caller to impute if the flag ever enters the model.
    """
    out = df.copy()
    size = out[K.GAR1_SIZE].astype("string")
    # StringDtype comparison propagates NA, so a null size becomes <NA> automatically.
    out[K.GAR1_EXISTS_FLAG] = size.ne(K.GAR1_NO_GARAGE_LABEL).astype("Int64")
    return out


def add_log_features(df):
    """Add log_* versions of the curved-effect continuous predictors.

    Rule: log for CURVATURE (diminishing returns), not for skew. Distances use
    log1p because several are exactly 0.
    """
    out = df.copy()
    for c in LOG_PLAIN:
        out[f"log_{c}"] = np.log(out[c].where(out[c] > 0))
    for c in LOG_1P:
        out[f"log_{c}"] = np.log1p(out[c].clip(lower=0))
    return out
