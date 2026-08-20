"""Wrangling: raw parquet -> model-ready analytic sample.

Everything from carving the Chicago / single-family / 2022-25 cross-section
through recoding, feature derivation, sale-validity classification, log
transforms, and the final drops. build_analytic_sample() is the ONE entry point;
each of its steps is also a standalone function the EDA notebook calls directly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from chicago_housing import constants as K
from chicago_housing.features import derive


# every column the analytic pipeline needs to read
def analysis_columns() -> list[str]:
    cols = (
        [K.TARGET_RAW, K.CITY_COL, K.MODELING_GROUP_COL, K.MULTICARD_COL, K.PRORATED_COL,
         K.SELLER_NAME, K.BUYER_NAME]
        + K.SALE_DATE_COLS
        + K.SV_REASON_COLS + [K.SV_IS_OUTLIER_COL]   # sv_is_outlier: regression outlier drop
        + K.BLOCK_A_STRUCTURE
        + [c for c in K.BLOCK_B_LOCATION if c not in K.ENGINEERED]
        + K.DERIVE_INPUTS
        + K.DEMOGRAPHICS
        + K.KEYS + K.GEO_COORDS + [K.REPORT_GEO] + [K.ADDRESS]
    )
    seen, out = set(), []
    for c in cols:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def _as_bool(s: pd.Series) -> pd.Series:
    """Robust boolean coercion (handles python bools OR 'True'/'False' strings)."""
    return s.astype("string").str.strip().str.lower().isin(["true", "1", "t", "yes"])


def add_region(df: pd.DataFrame, ptype=K.SF, col: str = K.REGION_COL,
               verbose: bool = True) -> pd.DataFrame:
    """Attach each sale's 'side' from the PropertyType's region scheme — 3-way
    N/W/S for single/multi-family, 4-way (adds Central) for condo. Ordered
    categorical so plots/tables sort in the config's region_order. Any community
    area absent from the scheme raises loudly (a silent drop would break every
    regional tally); load_sales_sample pre-drops unmapped rows so it won't fire in
    normal use.
    """
    order = list(ptype.region_order)
    out = df.copy()
    region = out[K.REPORT_GEO].map(ptype.region_map)
    missing = sorted(set(out.loc[region.isna(), K.REPORT_GEO].dropna().unique()))
    if missing:
        raise KeyError(f"community areas absent from {ptype.key} region map: {missing}")
    out[col] = pd.Categorical(region, categories=order, ordered=True)
    if verbose:
        print(f"add_region [{ptype.key}]: {out[col].value_counts().reindex(order).to_dict()}")
    return out


# ---------------------------------------------------------------------------
# Scope + columns + assembly — all driven by the PropertyType config
# ---------------------------------------------------------------------------
def scope_filter(df: pd.DataFrame, ptype=K.SF, verbose: bool = True) -> pd.DataFrame:
    """Carve `ptype`'s analytic cross-section: its city + modeling group + years,
    and (SF/MF only) drop multi-card / prorated rows. One function per market —
    condo skips the card filter (no multi-card concept; always prorated)."""
    n0 = len(df)
    out = df[df[K.CITY_COL].astype("string").str.upper() == ptype.city]
    out = out[out[K.MODELING_GROUP_COL].astype("string") == ptype.modeling_group]
    out = out[out[K.SALE_YEAR].astype("string").isin(ptype.years)]
    drop_cols = [K.CITY_COL, K.MODELING_GROUP_COL]
    if ptype.single_card_scope:              # SF/MF want one clean card per sale
        out = out[(~_as_bool(out[K.MULTICARD_COL])) & (~_as_bool(out[K.PRORATED_COL]))]
        drop_cols += [K.MULTICARD_COL, K.PRORATED_COL]
    out = out.drop(columns=[c for c in drop_cols if c in out.columns])
    if verbose:
        print(f"scope_filter [{ptype.key}]: {n0:>8,} -> {len(out):>8,} rows")
    return out.copy()


def sales_columns(ptype=K.SF) -> list[str]:
    """The lean column set the 01_02 sales analysis reads for `ptype`. Requests the
    type's RAW structure names (condo's unit fields via column_rename keys, else the
    canonical char_*) and only the scope columns that parquet actually has."""
    structure = (list(ptype.column_rename) if ptype.column_rename
                 else ["char_bldg_sf", "char_beds", "char_fbath", "char_land_sf"])
    scope = [K.MULTICARD_COL, K.PRORATED_COL] if ptype.single_card_scope else []
    cols = ([K.TARGET_RAW, K.CITY_COL, K.MODELING_GROUP_COL, K.SELLER_NAME, K.BUYER_NAME]
            + K.SALE_DATE_COLS + K.SV_REASON_COLS + scope
            + structure + ["char_yrblt", "meta_pin"]
            + K.GEO_COORDS + [K.REPORT_GEO, K.ADDRESS])
    seen, out = set(), []
    for c in cols:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def rename_columns(df: pd.DataFrame, ptype=K.SF) -> pd.DataFrame:
    """Rename a type's raw structure columns to canonical char_* names
    (PropertyType.column_rename). A no-op when already canonical (SF/MF)."""
    present = {k: v for k, v in ptype.column_rename.items() if k in df.columns}
    return df.rename(columns=present)


def load_sales_sample(ptype, verbose: bool = True) -> pd.DataFrame:
    """One-call setup for the 01_02 sales notebooks. load `ptype`'s parquet -> scope
    -> rename to canonical -> classify + drop non-arm's-length -> derive sale_month
    -> attach region. Every 01_02 notebook is then one line:
    `enriched = wrangling.load_sales_sample(K.MF)`.

    Rows whose community area isn't in this type's region scheme (null geo, or e.g.
    the Loop's ~2 multi-family sales) are dropped up front so every neighborhood /
    region / citywide tally reconciles.
    """
    from chicago_housing.data.load import load_training_data
    raw = load_training_data(ptype.parquet_key, columns=sales_columns(ptype))
    df = rename_columns(scope_filter(raw, ptype, verbose=verbose), ptype)
    flags = classify_sales(df)
    enriched = apply_drop_policy(df.join(flags), flags, verbose=verbose)
    enriched["meta_sale_date"] = pd.to_datetime(enriched["meta_sale_date"])
    enriched["sale_month"] = enriched["meta_sale_date"].dt.month
    n0 = len(enriched)
    enriched = enriched[enriched[K.REPORT_GEO].isin(ptype.region_map)].copy()
    if verbose and n0 != len(enriched):
        print(f"dropped {n0 - len(enriched):,} unmapped / no-geo rows")
    return add_region(enriched, ptype, verbose=verbose)

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


def recode_categoricals(
    df: pd.DataFrame,
    cols: list[str] | None = None,
    code_type: str = "long",
    verbose: bool = True,
) -> pd.DataFrame:
    """Replace CCAO's numeric char_ codes with human-readable labels.

    Wraps ccao.vars_recode + the official vars_dict, e.g. char_air 1/2 ->
    'No Central A/C'/'Central A/C', char_roof_cnst 1 -> 'Shingle/Asphalt'.
    Returns a copy with those columns as pandas Categorical so profiling and plots
    read cleanly from the START (run it right after scope_filter).

    cols=None (default) recodes every CCAO-coded column present and leaves the
    numeric char_ measures (char_beds, char_yrblt, char_bldg_sf, char_fbath,
    char_land_sf, ...) untouched — the vars_dict simply has no entry for them.
    Pass an explicit list to narrow the set; `code_type` is 'long' (full labels),
    'short' (abbreviations), or 'code' (keep codes, just drop invalid ones).

    ccao is an optional dependency; the import is local so clean.py loads without it.
    """
    try:
        from ccao import vars_recode
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "recode_categoricals needs the `ccao` package (pip install ccao)."
        ) from e
    out = vars_recode(df.copy(), cols=cols, code_type=code_type, as_factor=True)
    if verbose:
        candidate = cols if cols is not None else [c for c in df.columns if c.startswith("char_")]
        touched = [
            c for c in candidate
            if c in df.columns and not df[c].astype("string").equals(out[c].astype("string"))
        ]
        print(f"recode_categoricals: {len(touched)} col(s) -> labels: {touched}")
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
                         "pct_missing": None, "n_missing": None, "n_unique": None,
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
            "n_missing": int(s.isna().sum()),   # absolute NULL/None count — the drop-decision basis
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
# Outlier / sanity analysis — REPORT + LABEL, never drops. At the prep stage
# these hunt DATA ERRORS (impossible values), NOT genuine price-extreme tails,
# which we keep for the model and handle later via influence diagnostics.
# ---------------------------------------------------------------------------
def sanity_checks(df: pd.DataFrame, bounds: dict | None = None) -> pd.DataFrame:
    """Count rows outside the plausibility bounds in constants.SANITY_BOUNDS.

    Returns a tidy table — one row per checked column — with counts below the low
    bound, above the high bound, nulls, and the total flagged share. Reports only;
    drops nothing. Columns not in the frame come back with None counts.
    """
    bounds = bounds if bounds is not None else K.SANITY_BOUNDS
    n = len(df)
    rows = []
    for col, (lo, hi) in bounds.items():
        if col not in df.columns:
            rows.append({"column": col, "lo": lo, "hi": hi, "n_below": None,
                         "n_above": None, "n_null": None, "n_flagged": None,
                         "pct_flagged": None})
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        below = int((s < lo).sum()) if lo is not None else 0
        above = int((s > hi).sum()) if hi is not None else 0
        flagged = below + above
        rows.append({
            "column": col, "lo": lo, "hi": hi,
            "n_below": below, "n_above": above, "n_null": int(s.isna().sum()),
            "n_flagged": flagged, "pct_flagged": round(flagged / n, 4) if n else None,
        })
    return pd.DataFrame(rows)


def add_price_ratios(df: pd.DataFrame, flag: bool = True) -> pd.DataFrame:
    """Add price_per_bldg_sqft, price_per_land_sqft, price_per_bed (returns a copy).

    The ratios are a tighter lens than price alone: an absurd $/sqft flags EITHER
    a price error OR a size error, catching joint mistakes a per-column check
    misses. flag=True also adds booleans is_ppsf_outlier / is_ppland_outlier /
    is_ppbed_outlier from the constants bands. Division guards zeros/nulls -> NaN.
    """
    out = df.copy()
    price = pd.to_numeric(out[K.TARGET_RAW], errors="coerce")
    bldg_sqft = pd.to_numeric(out["char_bldg_sf"], errors="coerce").replace(0, np.nan)
    land_sqft = pd.to_numeric(out["char_land_sf"], errors="coerce").replace(0, np.nan)
    beds = pd.to_numeric(out["char_beds"], errors="coerce").replace(0, np.nan)
    out["price_per_bldg_sqft"] = price / bldg_sqft
    out["price_per_land_sqft"] = price / land_sqft
    out["price_per_bed"] = price / beds
    if flag:
        lo_bldg, hi_bldg = K.PRICE_PER_BLDG_SQFT_BOUNDS
        lo_land, hi_land = K.PRICE_PER_LAND_SQFT_BOUNDS
        lo_bed, hi_bed = K.PRICE_PER_BED_BOUNDS
        out["is_ppsf_outlier"]   = (out["price_per_bldg_sqft"] < lo_bldg) | (out["price_per_bldg_sqft"] > hi_bldg)
        out["is_ppland_outlier"] = (out["price_per_land_sqft"] < lo_land) | (out["price_per_land_sqft"] > hi_land)
        out["is_ppbed_outlier"]  = (out["price_per_bed"] < lo_bed) | (out["price_per_bed"] > hi_bed)
    return out


def flag_log_iqr(df: pd.DataFrame, columns: list[str], k: float = 1.5) -> pd.DataFrame:
    """Tukey-fence outlier flags computed on the LOG scale, per column.

    Working in log space keeps genuine right-skew tails (price, sqft) from being
    flagged wholesale. Returns a boolean frame aligned to df.index, one
    '<col>_log_iqr_out' column per input — sum it for counts, keep it to label.
    Only positive values are logged; non-positive/null -> not flagged (they show
    up in sanity_checks instead). `k` widens (3.0) or tightens the fences.
    """
    out = pd.DataFrame(index=df.index)
    for c in columns:
        s = pd.to_numeric(df[c], errors="coerce")
        logv = np.log(s.where(s > 0))
        q1, q3 = logv.quantile([0.25, 0.75])
        iqr = q3 - q1
        lo, hi = q1 - k * iqr, q3 + k * iqr
        out[f"{c}_log_iqr_out"] = ((logv < lo) | (logv > hi)).fillna(False)
    return out


# ---------------------------------------------------------------------------
# Sale validity — two orthogonal axes, applied to two samples:
#   1. Non-arm's-length (invalid observation): PTAX-203 declared non-market, or
#      an entity sale whose price is ALSO non-market. Dropped from BOTH samples.
#   2. Price-extreme (valid sale, high leverage): CCAO's sv_is_outlier. KEPT for
#      the descriptive/01_02 sample (real market events — the flips live here),
#      DROPPED for the 02_* regression sample (stop a few tail prices dominating
#      the fit). Toggled by apply_drop_policy(drop_price_outliers=...).
# ---------------------------------------------------------------------------

def _is_legal_entity(name: pd.Series) -> pd.Series:
    """True where the name matches CCAO's legal-entity keyword regex."""
    n = name.astype("string").str.lower().fillna("")
    return n.str.contains(K.ENTITY_KEYWORDS, na=False, regex=True)

def _reason_sets(df):
    """Collapse the three sv_outlier_reason columns into ONE set per row.
    Each sale can trip up to three flags, spread across reason1/reason2/reason3
    (e.g. reason1="Non-person sale", reason2="Statistical Anomaly", reason3=NaN).
    Working with three separate columns is awkward — we want to ask "does this
    sale's set of reasons intersect my drop list?" So we build, per row, a Python
    set like {"Non-person sale", "Statistical Anomaly"} that we can test with `&`.
    """
    cols = [c for c in K.SV_REASON_COLS if c in df.columns]
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
    price   = pd.to_numeric(df[K.TARGET_RAW], errors="coerce")

    flags = pd.DataFrame(index=df.index)

    # --- consumed from CCAO's pre-computed reason columns ---
    flags["is_statutory"] = reasons.map(lambda s: bool(s & K.SV_ALWAYS_DROP))    # PTAX-203 (declared non-market)
    flags["is_nominal"]   = reasons.map(lambda s: bool(s & K.SV_NOMINAL_PRICE))  # low price / $sqft / raw
    flags["is_below_floor"] = price < K.PRICE_FLOOR

    # CCAO's statistical price-outlier verdict (price-only). Present only when the
    # caller loaded sv_is_outlier (regression path); absent for the lean 01_02 read.
    if K.SV_IS_OUTLIER_COL in df.columns:
        flags["is_price_outlier"] = df[K.SV_IS_OUTLIER_COL].fillna(False).astype(bool)
    else:
        flags["is_price_outlier"] = pd.Series(False, index=df.index)

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
    flags["is_stale"] = (days_since_last.reindex(df.index) < K.SHORT_TERM_OWNER_DAYS).fillna(False)

    return flags

def apply_drop_policy(df: pd.DataFrame, flags: pd.DataFrame, verbose: bool = True,
                      drop_price_outliers: bool = False) -> pd.DataFrame:
    """Apply the non-market drop POLICY to pre-computed flags. Returns the filtered frame.

    Baseline policy (both samples):
      - statutory (PTAX-203)         -> always drop (non-market by declaration)
      - sub-floor price              -> always drop
      - entity / holding-name        -> drop ONLY IF price-corroborated (nominal | below)
      - price-extreme, stale, etc.   -> KEEP (diagnostics handle influence)

    `drop_price_outliers` (regression / 02_* only) ADDS CCAO's sv_is_outlier verdict to
    the drop, trimming the statistical price tail before the hedonic fit. Left False for
    the descriptive 01_02 sample so the extremes (the flips) stay in.
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
    if drop_price_outliers:
        drop = drop | flags["is_price_outlier"]

    out = df[~drop].copy()
    if verbose:
        print(f"apply_drop_policy: {len(df):,} -> {len(out):,}")
        print(f"  statutory (PTAX-203):    {int(flags['is_statutory'].sum()):,}")
        print(f"  below ${K.PRICE_FLOOR:,} floor:    {int(flags['is_below_floor'].sum()):,}")
        print(f"  entity + price-corrob.:  {int(entity_nonmarket.sum()):,}")
        if drop_price_outliers:
            print(f"  sv_is_outlier (price):   {int(flags['is_price_outlier'].sum()):,}")
        #print(f"  name + price-corrob.:    {int(name_nonmarket.sum()):,}")
    return out
# ---------------------------------------------------------------------------
# Target + assembly
# ---------------------------------------------------------------------------
def add_log_target(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    price = pd.to_numeric(out[K.TARGET_RAW], errors="coerce")
    out[K.TARGET] = np.log(price.where(price > 0))
    return out


def build_analytic_sample(
    df: pd.DataFrame,
    *,
    recode: bool = True,
    add_features: bool = True,
    add_logs: bool = True,
    drop_non_market: bool = True,
    drop_price_outliers: bool = True,
    drop_null_target: bool = True,
    verbose: bool = True,
) -> pd.DataFrame:
    """Raw parquet -> model-ready analytic sample. Each step is a keyword toggle,
    so you can build variants for regression iterations (e.g. add_logs=False).

    Order:
      scope_filter (always)
      -> recode            : numeric char_ codes -> readable labels
      -> drop_non_market   : classify sales + drop non-arm's-length; drop_price_outliers
                             (default True here) also trims CCAO's sv_is_outlier tail —
                             the regression trim. 01_02's load_sales_sample leaves it off.
      -> add_features      : dist_to_loop_ft, no_rated_school_nearby, char_gar1_exists
      -> add_logs          : log_sale_price + log_char_bldg_sf / log_char_land_sf / ...
      -> drop_null_target  : drop rows with no (log) sale price

    Features/logs are computed AFTER the non-market drop, so they reflect the final
    sample (e.g. the school-rating median fill). add_features must precede add_logs
    because log_dist_to_loop_ft needs dist_to_loop_ft.
    """
    out = scope_filter(df, verbose=verbose)
    if recode:
        out = recode_categoricals(out, verbose=verbose)
    if drop_non_market:
        flags = classify_sales(out)
        out = apply_drop_policy(out, flags, verbose=verbose,
                                drop_price_outliers=drop_price_outliers)
    if add_features:
        out = derive.add_distance_to_loop(out)
        out = derive.add_no_rated_school_flag(out)
        out = derive.add_gar1_exists_flag(out)
    if add_logs:
        out = derive.add_log_features(out)
        out = add_log_target(out)
    if drop_null_target and K.TARGET in out.columns:
        out = out[out[K.TARGET].notna()].copy()
    if verbose:
        print(f"analytic sample:              {len(out):>8,} rows")
    return out
