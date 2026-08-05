"""EDA computations — each takes a frame, returns a tidy DataFrame. Population-
agnostic: pass all sales, or a slice (entity, stale, a neighborhood). No plotting.
"""

from __future__ import annotations
import pandas as pd
from chicago_housing import config as C


def sales_by_year(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("meta_year").size()
              .rename("n_sales").reset_index())


def sales_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Seasonality — counts by calendar month, pooled across years."""
    return (df.groupby("sale_month").size()
              .rename("n_sales").reset_index())


def top_neighborhoods(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return (df.groupby(C.REPORT_GEO).size()
              .rename("n_sales").sort_values(ascending=False)
              .head(n).reset_index())


def median_price_by_neighborhood_year(df: pd.DataFrame, neighborhoods=None) -> pd.DataFrame:
    """Median sale price per neighborhood per year (long form, ready to plot)."""
    d = df if neighborhoods is None else df[df[C.REPORT_GEO].isin(neighborhoods)]
    return (d.groupby([C.REPORT_GEO, "meta_year"])[C.TARGET_RAW]
              .median().rename("median_price").reset_index())


def parcel_transaction_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Per-parcel: how many times it sold and the span between first & last sale."""
    g = df.groupby("meta_pin").agg(
        n_sales=("meta_sale_date", "size"),
        first_sale=("meta_sale_date", "min"),
        last_sale=("meta_sale_date", "max"),
    )
    g["span_days"] = (g["last_sale"] - g["first_sale"]).dt.days
    return g.reset_index()


def same_parcel_price_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """For parcels sold >1x: the max/min price ratio — the non-market smoking gun."""
    g = df.groupby("meta_pin")[C.TARGET_RAW].agg(["min", "max", "size"])
    g = g[g["size"] > 1].copy()
    g["price_ratio"] = g["max"] / g["min"]
    return g.reset_index().rename(columns={"size": "n_sales"})