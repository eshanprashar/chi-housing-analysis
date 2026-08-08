"""Matplotlib renderers. Each takes a tidy frame from analysis/sales_descriptives.py
and draws it. Never computes — pass an ax to overlay populations (entity vs non-entity).
"""

from __future__ import annotations
import matplotlib.pyplot as plt
from chicago_housing import constants as K


def plot_by_year(tidy, ax=None, label=None, partial_years=()):
    ax = ax or plt.subplots(figsize=(7, 4))[1]
    ax.plot(tidy["meta_year"], tidy["n_sales"], "o-", label=label)
    for y in partial_years:                      # annotate any incomplete year
        ax.axvspan(y - 0.15, y + 0.15, color="grey", alpha=0.1)
    ax.set_xlabel("year"); ax.set_ylabel("sales"); ax.set_title("Sales by year")
    if label: ax.legend()
    return ax


def plot_by_month(tidy, ax=None, label=None):
    ax = ax or plt.subplots(figsize=(7, 4))[1]
    ax.bar(tidy["sale_month"], tidy["n_sales"], alpha=0.7, label=label)
    ax.set_xlabel("month"); ax.set_ylabel("sales"); ax.set_title("Seasonality")
    if label: ax.legend()
    return ax


def plot_median_price_trend(tidy, ax=None):
    """One line per neighborhood, median price over years."""
    ax = ax or plt.subplots(figsize=(8, 5))[1]
    for nb, grp in tidy.groupby(K.REPORT_GEO):
        ax.plot(grp["meta_year"], grp["median_price"], "o-", label=nb)
    ax.set_xlabel("year"); ax.set_ylabel("median price ($)")
    ax.set_title("Median price by neighborhood"); ax.legend(fontsize=8)
    return ax


def plot_price_gap_distribution(gaps, ax=None):
    """Distribution of intra-parcel price ratios, split by transaction count."""
    ax = ax or plt.subplots(figsize=(7, 4))[1]
    for n, grp in gaps.groupby("n_sales"):
        if len(grp) >= 5:
            ax.hist(grp["price_ratio"].clip(upper=5), bins=30, alpha=0.4, label=f"sold {n}×")
    ax.set_xlabel("max/min price ratio"); ax.set_ylabel("parcels")
    ax.set_title("Intra-parcel price swings"); ax.legend()
    return ax