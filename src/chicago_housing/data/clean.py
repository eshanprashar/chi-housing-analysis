"""Cleaning & filtering: residential subset, sale-date window, sanity checks.

Step 0a lives largely here. Fill in as the audit reveals what needs handling.
"""

import pandas as pd


def audit_missingness(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Return % missing per column — the first thing to run in Step 0a."""
    miss = df[columns].isna().mean().sort_values(ascending=False)
    return miss.rename("pct_missing").to_frame()


def basic_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Drop junk sales / impossible values. TODO: define thresholds in 0a."""
    ...
