"""Step 0a: scope filters, sale-validity handling, column profiling, sample build.

The public parquet is COUNTYWIDE, all property types, ~9 years. We carve a clean
Chicago / single-family / 2022-24 cross-section before any modeling, then split
sale validity (drop non-arm's-length, keep price-extreme) and log the target.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from chicago_housing import config as C


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
    
    if C.SINGLE_CARD_ONLY:
        out = out[~_as_bool(out[C.MULTICARD_COL])]
        out = out[~_as_bool(out[C.PRORATED_COL])]
    if verbose:
        print(f"scope_filter:        {n0:>8,} -> {len(out):>8,} rows")
    return out.copy()

# ---------------------------------------------------------------------------
# Column profiling (audit) — missingness AND degeneracy AND cardinality
# ---------------------------------------------------------------------------
def profile_columns(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Per-column audit. A column can be 0% missing yet useless (one value in
    >95% of rows), so we report degeneracy (pct_modal) alongside missingness."""
    cols = columns if columns is not None else list(df.columns)
    rows = []
    for c in cols:
        if c not in df.columns:
            rows.append({"column": c, "role": c.split("_")[0], "dtype": "MISSING",
                         "pct_missing": None, "n_unique": None,
                         "pct_modal": None, "modal_value": "COLUMN NOT FOUND"})
            continue
        s = df[c]
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

    Returns a boolean DataFrame aligned to df.index, one column per flag. This is
    the object EDA slices on (is_entity, is_stale, ...); the drop POLICY lives in
    drop_non_market. Separating them means we can explore populations freely
    without re-running (or being entangled with) the drop logic.
    """
    reasons = _reason_sets(df)                       # one set of sv reasons per row
    price   = pd.to_numeric(df[C.TARGET_RAW], errors="coerce")

    flags = pd.DataFrame(index=df.index)
    flags["is_statutory"] = reasons.map(lambda s: bool(s & C.SV_ALWAYS_DROP))   # PTAX / Family
    flags["is_entity"]    = reasons.map(lambda s: bool(s & C.SV_ENTITY))        # Non-person sale
    flags["is_nominal"]   = reasons.map(lambda s: bool(s & C.SV_NOMINAL_PRICE)) # low price / $sqft / raw
    flags["is_stale"]     = reasons.map(lambda s: bool(s & C.SV_STALE))         # short-term / flip
    flags["is_below_floor"] = price < C.PRICE_FLOOR

    # holding-vehicle names (land trust / title co) — detected once, fully
    names = (df["meta_sale_seller_name"].astype("string").fillna("") + " | "
             + df["meta_sale_buyer_name"].astype("string").fillna("")).str.upper()
    name_hit = pd.Series(False, index=df.index)
    for tok in C.NONMARKET_NAME_TOKENS:              # e.g. "LAND TRUST", "TITLE"
        name_hit = name_hit | names.str.contains(tok, na=False)
    flags["is_name_hit"] = name_hit

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
    name_nonmarket   = flags["is_name_hit"] & price_corroborated   # same rule for names

    drop = (
        flags["is_statutory"]
        | flags["is_below_floor"]
        | entity_nonmarket
        | name_nonmarket
    )

    out = df[~drop].copy()
    if verbose:
        print(f"drop_non_market: {len(df):,} -> {len(out):,}")
        print(f"  statutory (PTAX/family): {int(flags['is_statutory'].sum()):,}")
        print(f"  below ${C.PRICE_FLOOR:,} floor:    {int(flags['is_below_floor'].sum()):,}")
        print(f"  entity + price-corrob.:  {int(entity_nonmarket.sum()):,}")
        print(f"  name + price-corrob.:    {int(name_nonmarket.sum()):,}")
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
    out, kept_entity = drop_non_market(out, price_floor=C.PRICE_FLOOR, use_name_rule=True, verbose=verbose)
    out = add_log_target(out)
    out = out[out[C.TARGET].notna()].copy()
    if verbose:
        print(f"analytic sample:              {len(out):>8,} rows")
    return out, kept_entity
