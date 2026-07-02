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
# Scope filters
# ---------------------------------------------------------------------------
def scope_filter(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """Chicago + single-family + 2022-24 + single-card / non-prorated."""
    n0 = len(df)
    # Filter for Chicago
    out = df[df[C.CITY_COL].astype("string").str.upper() == C.CITY]
    # Filter for Single Family
    out = out[out[C.MODELING_GROUP_COL].astype("string") == C.MODELING_GROUP]
    # Filter for years 2022,2023 and 2024
    out = out[out[C.YEAR_COL].astype("string").isin(C.YEARS)]
    
    if C.SINGLE_CARD_ONLY:
        out = out[~_as_bool(out[C.MULTICARD_COL])]
        out = out[~_as_bool(out[C.PRORATED_COL])]
    if verbose:
        print(f"scope_filter:        {n0:>8,} -> {len(out):>8,} rows")
    return out.copy()


# ---------------------------------------------------------------------------
# Sale validity: non-arm's-length (drop) vs price-extreme (keep)
# ---------------------------------------------------------------------------
def flag_non_arms_length(df: pd.DataFrame) -> pd.Series:
    """True where ANY sv_outlier_reason marks a non-market transfer.

    Deliberately does NOT use sv_is_outlier directly — that also flags genuine
    price-extreme sales, which we KEEP for inference.
    """
    mask = pd.Series(False, index=df.index)
    for col in C.SV_REASON_COLS:
        if col not in df.columns:
            continue
        vals = df[col].astype("string").fillna("")
        for token in C.NON_ARMS_LENGTH_REASONS:
            mask |= vals.str.contains(token, case=False, na=False)
    return mask

def _reason_sets(df):
    cols = [c for c in C.SV_REASON_COLS if c in df.columns]
    return df[cols].apply(
        lambda r: {v for v in r.tolist() if isinstance(v, str) and v.strip()}, axis=1
    )

def drop_non_market(df, price_floor=C.PRICE_FLOOR, use_name_rule=True, verbose=True):
    n0 = len(df)
    reasons = _reason_sets(df)
    price   = pd.to_numeric(df[C.TARGET_RAW], errors="coerce")

    always  = reasons.map(lambda s: bool(s & C.SV_ALWAYS_DROP))
    entity  = reasons.map(lambda s: bool(s & C.SV_ENTITY))
    nominal = reasons.map(lambda s: bool(s & C.SV_NOMINAL_PRICE))
    below   = price < price_floor

    entity_nonmarket = entity & (nominal | below)     # <- the corroboration rule
    drop = always | below | entity_nonmarket

    name_hit = pd.Series(False, index=df.index)
    if use_name_rule:
        
        names = (df["meta_sale_seller_name"].astype("string").fillna("") + " | "
                 + df["meta_sale_buyer_name"].astype("string").fillna("")).str.upper()
        for tok in C.NONMARKET_NAME_TOKENS:
            name_hit |= names.str.contains(tok, na=False)
        name_nonmarket = name_hit & (nominal | below)   # corroborate, like the entity rule
        drop |= name_nonmarket

    out = df[~drop].copy()
    if verbose:
        print(f"drop_non_market: {n0:,} -> {len(out):,}")
        print(f"  always (PTAX/family):   {int(always.sum()):,}")
        print(f"  below ${price_floor:,} floor:  {int(below.sum()):,}")
        print(f"  entity + nominal/low:   {int(entity_nonmarket.sum()):,}")
        if use_name_rule:
            print(f"  land-trust/title kept (market price): {int((name_hit & ~name_nonmarket).sum()):,}")
    return out


def drop_non_arms_length(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    n0 = len(df)
    mask = flag_non_arms_length(df)
    out = df[~mask].copy()
    if verbose:
        print(f"drop_non_arms_length:{n0:>8,} -> {len(out):>8,} rows "
              f"({int(mask.sum()):,} non-market removed)")
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
    out = drop_non_arms_length(out, verbose=verbose)
    out = add_log_target(out)
    out = out[out[C.TARGET].notna()].copy()
    if verbose:
        print(f"analytic sample:              {len(out):>8,} rows")
    return out
