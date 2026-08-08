"""Distribution diagnostics — the last step of the wrangling loop.

After profiling, fixing dtypes, and dropping redundant columns (clean.py), you
look at the *shapes* of what's left to decide transforms and spot suspicious
tails. Two complementary views, meant to be used together:

    summarize_distributions(df, cols)  -> a tidy table: moments + a transform hint
                                          (read this to DECIDE log / flag tails)
    plot_distributions(df, cols)       -> a histogram grid
                                          (eyeball this to CONFIRM the shape)

Both are numeric-only and NaN-safe. Non-numeric columns are skipped, not errored.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def _numeric_columns(df: pd.DataFrame, columns: list[str] | None) -> list[str]:
    """Numeric columns only. Even when `columns` is given explicitly we skip
    non-numeric ones (category codes like char_roof_cnst, strings) — a skew/tail
    summary of a nominal code is meaningless. Nullable Int64 counts as numeric.
    """
    if columns is None:
        return df.select_dtypes(include="number").columns.tolist()
    return [
        c for c in columns
        if c in df.columns and pd.api.types.is_numeric_dtype(df[c])
    ]


def summarize_distributions(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    skew_threshold: float = 1.0,
    tail_threshold: float = 10.0,
) -> pd.DataFrame:
    """Per-column moments + percentiles + a transform hint.

    One row per (numeric) column: mean/std, the 1/50/99 percentiles and min/max,
    skew, kurtosis, and `tail_ratio` = p99 / median (how far the upper tail runs
    above the middle). `transform_hint` is a heuristic nudge, not a verdict:

        'log candidate'     non-negative and right-skewed beyond skew_threshold
        'left-skew'         skewed the other way (log won't help)
        'heavy upper tail'  tail_ratio beyond tail_threshold — inspect for outliers

    Sorted by |skew| descending so the columns most in need of attention float up.
    """
    rows = []
    for c in _numeric_columns(df, columns):
        s = pd.to_numeric(df[c], errors="coerce").dropna()
        if s.empty:
            continue
        skew = float(s.skew())
        q01, q50, q99 = (float(v) for v in s.quantile([0.01, 0.50, 0.99]))
        tail_ratio = q99 / q50 if q50 not in (0.0,) else np.nan
        nonneg = bool((s >= 0).all())

        hints = []
        if nonneg and skew > skew_threshold:
            hints.append("log candidate")
        elif skew < -skew_threshold:
            hints.append("left-skew")
        if np.isfinite(tail_ratio) and tail_ratio > tail_threshold:
            hints.append("heavy upper tail")

        rows.append({
            "column": c,
            "n": int(s.size),
            "mean": float(s.mean()),
            "std": float(s.std()),
            "min": float(s.min()),
            "p01": q01,
            "median": q50,
            "p99": q99,
            "max": float(s.max()),
            "skew": round(skew, 2),
            "kurtosis": round(float(s.kurtosis()), 2),
            "tail_ratio": round(float(tail_ratio), 2) if np.isfinite(tail_ratio) else None,
            "transform_hint": " + ".join(hints),
        })

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return (
        out.reindex(out["skew"].abs().sort_values(ascending=False).index)
        .reset_index(drop=True)
    )


def plot_distributions(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    bins: int = 40,
    clip_upper_quantile: float | None = 0.99,
    ncols: int = 3,
    panel_size: tuple[float, float] = (4.0, 3.0),
):
    """Histogram grid to eyeball shapes. Returns the matplotlib Figure.

    `clip_upper_quantile` trims the top tail per panel (default 99th pct) so a few
    extreme values don't flatten the bulk into one bar — set to None to see the
    raw tails. Pair the shape you see here with the `transform_hint` from
    summarize_distributions().
    """
    cols = _numeric_columns(df, columns)
    if not cols:
        raise ValueError("no numeric columns to plot")

    ncols = min(ncols, len(cols))
    nrows = int(np.ceil(len(cols) / ncols))
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(panel_size[0] * ncols, panel_size[1] * nrows)
    )
    axes = np.atleast_1d(axes).ravel()

    for ax, c in zip(axes, cols):
        s = pd.to_numeric(df[c], errors="coerce").dropna()
        if clip_upper_quantile is not None and not s.empty:
            s = s.clip(upper=s.quantile(clip_upper_quantile))
        ax.hist(s, bins=bins)
        ax.set_title(c, fontsize=9)
        ax.tick_params(labelsize=8)

    for ax in axes[len(cols):]:      # blank any unused panels
        ax.set_visible(False)

    fig.tight_layout()
    return fig
