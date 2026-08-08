"""Step 0a: scope filters, sale-validity handling, column profiling, sample build.

The public parquet is COUNTYWIDE, all property types, ~9 years. We carve a clean
Chicago / single-family / 2022-25 cross-section before any modeling, then split
sale validity (drop non-arm's-length, keep price-extreme) and log the target.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from chicago_housing import config as C
from chicago_housing import constants as K
from chicago_housing.constants import (
    TARGET_RAW, 
    CITY_COL,
    MODELING_GROUP_COL, 
    MULTICARD_COL, 
    PRORATED_COL,
    SELLER_NAME,
    BUYER_NAME,
    SALE_DATE_COLS,
    SV_REASON_COLS,
    BLOCK_A_STRUCTURE,
    BLOCK_B_LOCATION,
    ENGINEERED,
    DERIVE_INPUTS,
    DEMOGRAPHICS,
    KEYS,
    GEO_COORDS,
    REPORT_GEO
)

# every column the analytic pipeline needs to read
def analysis_columns() -> list[str]:
    cols = (
        [TARGET_RAW, CITY_COL, MODELING_GROUP_COL, MULTICARD_COL, PRORATED_COL,
         SELLER_NAME, BUYER_NAME]
        + SALE_DATE_COLS
        + SV_REASON_COLS
        + BLOCK_A_STRUCTURE
        + [c for c in BLOCK_B_LOCATION if c not in ENGINEERED]
        + DERIVE_INPUTS
        + DEMOGRAPHICS
        + KEYS + GEO_COORDS + [REPORT_GEO]
    )
    seen, out = set(), []
    for c in cols:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def _as_bool(s: pd.Series) -> pd.Series:
    """Robust boolean coercion (handles python bools OR 'True'/'False' strings)."""
    return s.astype("string").str.strip().str.lower().isin(["true", "1", "t", "yes"])

# ---------------------------------------------------------------------------
# Scope filters
# ---------------------------------------------------------------------------
def scope_filter(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """Chicago + single-family + 2022-25 + single-card / non-prorated."""
    n0 = len(df)
    # Filter for Chicago
    out = df[df[C.CITY_COL].astype("string").str.upper() == C.CITY]
    # Filter for Single Family
    out = out[out[C.MODELING_GROUP_COL].astype("string") == C.MODELING_GROUP]
    # Filter for years 2022,2023, 2024 and 2025
    out = out[out[C.SALE_YEAR].astype("string").isin(C.YEARS)]

    # Multi-card refers to parcels with multiple structures; we will drop them for simplicity
    if C.SINGLE_CARD_ONLY:
        out = out[~_as_bool(out[C.MULTICARD_COL])]
        out = out[~_as_bool(out[C.PRORATED_COL])]
    # Drop redundant columns after filtering
    out = out.drop(columns=[C.CITY_COL, C.MODELING_GROUP_COL, C.MULTICARD_COL, C.PRORATED_COL])
    if verbose:
        print(f"scope_filter:        {n0:>8,} -> {len(out):>8,} rows")
    return out.copy()

# ---------------------------------------------------------------------------
# Wrangling fixes — dtype correction + redundant-column drops
# Both are driven by lists in constants.py that you populate FROM the profile
# output, then feed back into profile_columns(...) to re-audit the fixed frame.
# ---------------------------------------------------------------------------
def convert_float_to_int(
    df: pd.DataFrame, columns: list[str] | None = None, verbose: bool = True
) -> pd.DataFrame:
    """Coerce integer-valued float columns (counts, years) to nullable Int64.

    Driven by constants.CHANGE_DTYPE_FROM_FLOAT_TO_INT unless `columns` is passed.
    We use pandas' nullable "Int64" (not numpy int) so NaNs survive the cast.
    Silently skips columns not present in the frame.
    """
    cols = columns if columns is not None else K.CHANGE_DTYPE_FROM_FLOAT_TO_INT
    out = df.copy()
    changed = []
    for c in cols:
        if c not in out.columns:
            continue
        out[c] = pd.to_numeric(out[c], errors="coerce").round().astype("Int64")
        changed.append(c)
    if verbose:
        print(f"convert_float_to_int:  {len(changed)} col(s) -> Int64: {changed}")
    return out


def drop_redundant_columns(
    df: pd.DataFrame, columns: list[str] | None = None, verbose: bool = True
) -> pd.DataFrame:
    """Drop columns flagged redundant during wrangling.

    Driven by constants.DROP_REDUNDANT_COLS_WRANGLING unless `columns` is passed.
    Silently ignores columns already absent (idempotent / re-run safe).
    """
    cols = columns if columns is not None else K.DROP_REDUNDANT_COLS_WRANGLING
    present = [c for c in cols if c in df.columns]
    out = df.drop(columns=present)
    if verbose:
        print(f"drop_redundant_columns: dropped {len(present)}: {present}")
    return out


# ---------------------------------------------------------------------------
# Column profiling (audit) — missingness AND degeneracy AND cardinality
# ---------------------------------------------------------------------------
def profile_columns(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    *,
    convert_dtypes: bool = False,
    drop_columns: bool = False,
) -> pd.DataFrame:
    """Per-column audit. A column can be 0% missing yet useless (one value in
    >95% of rows), so we report degeneracy (pct_modal) alongside missingness.

    The workflow (notebooks/01_01_data_prep.ipynb): profile once with the defaults
    to SEE the raw dtypes/missingness, record the fixes in constants.py, then
    re-profile with the flags to audit the CLEANED frame:

        convert_dtypes=True -> apply convert_float_to_int() before profiling
        drop_columns=True   -> apply drop_redundant_columns() before profiling

    (columns you list in `columns` but that get dropped will show as
    'COLUMN NOT FOUND' — a useful signal the drop took effect.)
    """
    work = df
    if convert_dtypes:
        work = convert_float_to_int(work, verbose=False)
    if drop_columns:
        work = drop_redundant_columns(work, verbose=False)

    cols = columns if columns is not None else list(work.columns)
    rows = []
    for c in cols:
        if c not in work.columns:
            rows.append({"column": c, "role": c.split("_")[0], "dtype": "MISSING",
                         "pct_missing": None, "n_unique": None,
                         "pct_modal": None, "modal_value": "COLUMN NOT FOUND"})
            continue
        s = work[c]
        nonnull = int(s.notna().sum())
        vc = s.value_counts(dropna=True)
        rows.append({
            "column": c,
            "role": c.split("_")[0],
            "dtype": str(s.dtype),
            "pct_missing": round(float(s.isna().mean()), 3),
            "n_unique": int(s.nunique(dropna=True)),
            "pct_modal": round(float(vc.iloc[0] / nonnull), 3) if nonnull else None,
            "modal_value": vc.index[0] if len(vc) else None,
        })
    return (
        pd.DataFrame(rows)
        .sort_values(["role", "pct_missing"], ascending=[True, False])
        .reset_index(drop=True)
    )

# ---------------------------------------------------------------------------
# Sale validity: non-arm's-length (drop) vs price-extreme (keep)
# ---------------------------------------------------------------------------

def _is_legal_entity(name: pd.Series) -> pd.Series:
    """True where the name matches CCAO's legal-entity keyword regex."""
    n = name.astype("string").str.lower().fillna("")
    return n.str.contains(C.ENTITY_KEYWORDS, na=False, regex=True)

def _reason_sets(df):
    """Collapse the three sv_outlier_reason columns into ONE set per row.
    Each sale can trip up to three flags, spread across reason1/reason2/reason3
    (e.g. reason1="Non-person sale", reason2="Statistical Anomaly", reason3=NaN).
    Working with three separate columns is awkward — we want to ask "does this
    sale's set of reasons intersect my drop list?" So we build, per row, a Python
    set like {"Non-person sale", "Statistical Anomaly"} that we can test with `&`.
    """
    cols = [c for c in C.SV_REASON_COLS if c in df.columns]
    # For each row r (its three reason cells), keep only real, non-empty strings
    # and put them in a set. `isinstance(v, str)` drops NaN/None; `v.strip()`
    # drops blank/whitespace cells. Result: one set of flags per row.
    #   r.tolist() -> ["Non-person sale", "Statistical Anomaly", nan]
    #   -> {"Non-person sale", "Statistical Anomaly"}
    return df[cols].apply(
        lambda r: {v for v in r.tolist() if isinstance(v, str) and v.strip()}, axis=1
    )

def classify_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Label each sale by the flags it carries — pure classification, no dropping.

    Returns a boolean DataFrame aligned to df.index. Entity + short-term-owner are
    RECOMPUTED to match CCAO's published methodology (see notes above); statutory
    (PTAX/Family) and the statistical price/anomaly flags are consumed from the
    County's pre-computed `sv` reason columns (we don't replicate their isolation
    forest or last-name parser — we're a consumer of those outputs).
    """
    reasons = _reason_sets(df)
    price   = pd.to_numeric(df[C.TARGET_RAW], errors="coerce")

    flags = pd.DataFrame(index=df.index)

    # --- consumed from CCAO's pre-computed reason columns ---
    flags["is_statutory"] = reasons.map(lambda s: bool(s & C.SV_ALWAYS_DROP))    # PTAX / Family
    flags["is_nominal"]   = reasons.map(lambda s: bool(s & C.SV_NOMINAL_PRICE))  # low price / $sqft / raw
    flags["is_below_floor"] = price < C.PRICE_FLOOR

    # --- entity: RECOMPUTED with CCAO's keyword regex, per side ---
    # A sale is "Non-person" if EITHER party is a legal entity (their
    # sv_buyer_category / sv_seller_category .eq("legal_entity").any(axis=1)).
    flags["entity_buyer"]  = _is_legal_entity(df["meta_sale_buyer_name"])
    flags["entity_seller"] = _is_legal_entity(df["meta_sale_seller_name"])
    flags["is_entity"]     = flags["entity_buyer"] | flags["entity_seller"]

    # --- short-term owner: RECOMPUTED with the 365-day rule ---
    # days since this parcel last transacted; < 365 => short-term (a flip window).
    d = df[["meta_pin", "meta_sale_date"]].copy()
    d["meta_sale_date"] = pd.to_datetime(d["meta_sale_date"])
    d = d.sort_values("meta_sale_date")
    days_since_last = d.groupby("meta_pin")["meta_sale_date"].diff().dt.days
    flags["is_stale"] = (days_since_last.reindex(df.index) < C.SHORT_TERM_OWNER_DAYS).fillna(False)

    return flags

def drop_non_market(df: pd.DataFrame, flags: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """Apply the drop POLICY to pre-computed flags. Returns the filtered frame only.

    Policy (see context.md §3):
      - statutory (PTAX/family)      -> always drop (non-market by definition)
      - sub-floor price              -> always drop
      - entity / holding-name        -> drop ONLY IF price-corroborated (nominal | below)
      - price-extreme, stale, etc.   -> KEEP (diagnostics handle influence)
    """
    price_corroborated = flags["is_nominal"] | flags["is_below_floor"]

    entity_nonmarket = flags["is_entity"]   & price_corroborated   # corroboration rule
    # We are already replicating CCAO's logic to identify entities 
    # So no need to have a separate name_hit logic 
    #name_nonmarket   = flags["is_name_hit"] & price_corroborated   # same rule for names

    drop = (
        flags["is_statutory"]
        | flags["is_below_floor"]
        | entity_nonmarket
    #    | name_nonmarket
    )

    out = df[~drop].copy()
    if verbose:
        print(f"drop_non_market: {len(df):,} -> {len(out):,}")
        print(f"  statutory (PTAX/family): {int(flags['is_statutory'].sum()):,}")
        print(f"  below ${C.PRICE_FLOOR:,} floor:    {int(flags['is_below_floor'].sum()):,}")
        print(f"  entity + price-corrob.:  {int(entity_nonmarket.sum()):,}")
        #print(f"  name + price-corrob.:    {int(name_nonmarket.sum()):,}")
    return out
# ---------------------------------------------------------------------------
# Target + assembly
# ---------------------------------------------------------------------------
def add_log_target(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    price = pd.to_numeric(out[C.TARGET_RAW], errors="coerce")
    out[C.TARGET] = np.log(price.where(price > 0))
    return out


def build_analytic_sample(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """Full Step 0a pipeline: scope -> validity -> log target -> drop null target."""
    out = scope_filter(df, verbose=verbose)
    flags = classify_sales(out)                       # label each sale by its flags
    out = drop_non_market(out, flags, verbose=verbose)  # apply the drop policy
    out = add_log_target(out)
    out = out[out[C.TARGET].notna()].copy()
    if verbose:
        print(f"analytic sample:              {len(out):>8,} rows")
    return out
