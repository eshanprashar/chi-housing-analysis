"""Matplotlib renderers. Each takes a tidy frame from analysis/sales_descriptives.py
and draws it. Never computes — pass an ax to overlay populations (entity vs non-entity).
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from chicago_housing import constants as K

# entity-vs-individual palette — validated CVD-safe pair (dataviz skill).
# Colour follows the POPULATION, not its rank; used identically across every chart.
NON_ENTITY_COLOR = "#2a78d6"   # blue  — individuals
ENTITY_COLOR = "#eb6834"       # orange — entities
_SPLIT = {"non_entity": NON_ENTITY_COLOR, "entity": ENTITY_COLOR}

# single-series "total" charts (no entity split) reuse the blue as the one hue.
TOTAL_COLOR = NON_ENTITY_COLOR
INK = "#33322f"; MUTED = "#8a8a8a"; ALERT = "#c94f2e"   # text/accents (never a series)

# N/W/S region palette — a SEPARATE categorical trio (kept off the entity/individual
# blue+orange so the two semantic dimensions never collide). Validated CVD-safe
# (dataviz validator: worst adjacent ΔE 15.9 deutan / 24.2 normal). Loop = neutral.
REGION_COLORS = {"North": "#2f9e8f", "West": "#8a5fd6", "South": "#c78f2a",
                 "Central": "#b5476b"}   # Central (rose) = the CONDO-only downtown region
LOOP_COLOR = "#cfccc6"   # downtown / Central — no single-family sales (SF map only)

# then-vs-now price bars: a light->dark ramp of the blue (earlier = light, later =
# dark). NOT the entity/individual pair — this is one measure across two periods.
PRIOR_COLOR = "#a9cbf0"   # the earlier year (2022)
UP_COLOR = "#2f8f4e"; DOWN_COLOR = ALERT   # delta direction (redundant with the +/- sign)


def _titlecase_area(name: str) -> str:
    """Neighborhood ALL-CAPS -> Title Case, fixing the names .title() mangles."""
    return (str(name).title().replace("Mckinley", "McKinley").replace("Ohare", "O'Hare"))


def plot_median_price_2yr(table, order, title, money_max=None, ax=None):
    """Paired horizontal bars — median price in the earlier vs later year, one pair
    per neighborhood, with the % change labelled at the right. `table` is
    sd.median_price_two_year (index = neighborhood, med_*/n_* + delta_pct); `order`
    is the neighborhoods to show, top-of-list drawn at the top.

    Bar colours are a light→dark 'then→now' ramp (not the entity palette). Delta
    colour AND its +/- sign both encode direction, so it stays CVD-safe.
    """
    med_cols = [c for c in table.columns if c.startswith("med_")]
    (ca, cb) = med_cols[0], med_cols[1]                     # earlier, later
    ya, yb = ca.split("_")[1], cb.split("_")[1]
    d = table.loc[list(order)][::-1]                        # first in `order` -> top
    y = np.arange(len(d)); h = 0.38
    ax = ax or plt.subplots(figsize=(9, 6))[1]
    ax.barh(y + h / 2, d[ca], height=h, color=PRIOR_COLOR, label=ya, zorder=3)
    ax.barh(y - h / 2, d[cb], height=h, color=TOTAL_COLOR, label=yb, zorder=3)
    xmax = money_max or d[[ca, cb]].max().max()
    for i, (_, r) in enumerate(d.iterrows()):
        ax.text(r[cb] + xmax * 0.01, i - h / 2, f"${r[cb]/1000:,.0f}k", va="center", fontsize=8, color=INK)
        ax.text(r[ca] + xmax * 0.01, i + h / 2, f"${r[ca]/1000:,.0f}k", va="center", fontsize=8, color="#9aa0a6")
        dv = r["delta_pct"]
        ax.text(xmax * 1.15, i, f"{dv:+.0f}%", va="center", ha="right", fontsize=9,
                fontweight="bold", color=(DOWN_COLOR if dv < 0 else UP_COLOR))
    ax.set_yticks(y); ax.set_yticklabels([_titlecase_area(n) for n in d.index], fontsize=9)
    ax.set_xlim(0, xmax * 1.30)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))
    ax.text(xmax * 1.15, len(d) - 0.3, f"Δ {ya[-2:]}→{yb[-2:]}", ha="right", fontsize=8, color=MUTED)
    ax.set_title(title, fontsize=12, fontweight="bold", color=INK, loc="left", pad=10)
    ax.spines[["top", "right"]].set_visible(False); ax.tick_params(left=False)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    return ax


def _thousands(ax, axis: str = "y"):
    """Format an axis as $k (thousands) — kills the scientific-notation default."""
    fmt = FuncFormatter(lambda v, _: f"${v/1000:,.0f}k")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def _annotate_yoy(ax, xs, ys, fontsize: int = 8, color: str = "#52514e"):
    """Label each point (from the 2nd on) with its % change vs the previous point."""
    ys = list(ys)
    for i in range(1, len(ys)):
        prev, cur = ys[i - 1], ys[i]
        if prev and prev == prev and cur == cur:          # non-zero, non-nan
            ax.annotate(f"{(cur / prev - 1) * 100:+.0f}%", (xs[i], cur),
                        textcoords="offset points", xytext=(0, 7), ha="center",
                        fontsize=fontsize, color=color)


def plot_by_year(tidy, ax=None, label=None, partial_years=()):
    ax = ax or plt.subplots(figsize=(7, 4))[1]
    ax.plot(tidy["meta_year"], tidy["n_sales"], "o-", label=label)
    for y in partial_years:                      # annotate any incomplete year
        ax.axvspan(y - 0.15, y + 0.15, color="grey", alpha=0.1)
    ax.set_xlabel("year"); ax.set_ylabel("sales"); ax.set_title("Sales by year")
    if label: ax.legend()
    return ax


def plot_total_sales_by_year(tidy, ax=None, title=None, alert_below=-10.0):
    """Newspaper-style volume bars — TOTAL sales per year (no entity split).

    tidy is sd.sales_by_year (meta_year, n_sales). Each bar carries its count on
    top and its YoY % centred inside; a drop past `alert_below`% is coloured to
    flag the cliff. Single hue, no legend, no y-axis furniture — the numbers ARE
    the axis. Title should state the takeaway (the answer to the trivia question).
    """
    ax = ax or plt.subplots(figsize=(7.5, 4.4))[1]
    years = tidy["meta_year"].astype(str).tolist()
    vals = tidy["n_sales"].to_numpy()
    bars = ax.bar(years, vals, width=0.62, color=TOTAL_COLOR, zorder=3)
    for i, (b, v) in enumerate(zip(bars, vals)):
        ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.012, f"{int(v):,}",
                ha="center", va="bottom", fontsize=12, fontweight="bold", color=INK)
        if i:                                              # YoY inside the bar, from year 2 on
            yoy = (v / vals[i - 1] - 1) * 100
            ax.text(b.get_x() + b.get_width() / 2, v / 2, f"{yoy:+.0f}%",
                    ha="center", va="center", fontsize=10, fontweight="bold", color="white")
    ax.set_ylim(0, max(vals) * 1.15)
    ax.set_title(title or "Sales by year", fontsize=12, fontweight="bold",
                 color=INK, loc="left", pad=12)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_yticks([]); ax.tick_params(left=False, axis="x", labelsize=11, colors=INK)
    ax.margins(x=0.02)
    return ax


def plot_by_month(tidy, ax=None, label=None):
    ax = ax or plt.subplots(figsize=(7, 4))[1]
    ax.bar(tidy["sale_month"], tidy["n_sales"], alpha=0.7, label=label)
    ax.set_xlabel("month"); ax.set_ylabel("sales"); ax.set_title("Seasonality")
    if label: ax.legend()
    return ax


def plot_median_price_trend(tidy, ax=None, title="Median price by neighborhood",
                            annotate=True, show_counts=True):
    """One line per neighborhood, median price over years.

    $k y-axis (no sci-notation), legend OUTSIDE the plot area. Each dot is labelled
    with its YoY % (above) and, when `tidy` carries n_sales, the transaction count
    n=… (below). Call once per population (all / entity / non-entity).
    """
    ax = ax or plt.subplots(figsize=(11, 6.5))[1]
    for nb, grp in tidy.groupby(K.REPORT_GEO):
        grp = grp.sort_values("meta_year")
        line, = ax.plot(grp["meta_year"].astype(str), grp["median_price"], "o-", lw=1.8, label=nb)
        if annotate:
            _annotate_yoy(ax, range(len(grp)), grp["median_price"], fontsize=7, color=line.get_color())
        if show_counts and "n_sales" in grp:
            m = len(grp)
            for xi, (yv, nv) in enumerate(zip(grp["median_price"], grp["n_sales"])):
                if yv == yv and xi in (0, m - 1):     # counts only at first & last year
                    ax.annotate(f"n={int(nv)}", (xi, yv), textcoords="offset points",
                                xytext=(0, -12), ha="center", fontsize=6, color="#8a8a8a")
    _thousands(ax)
    ax.set_xlabel("year"); ax.set_ylabel("median price")
    ax.set_title(title)
    ax.legend(fontsize=8, loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False)
    ax.margins(y=0.12)
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


# ---------------------------------------------------------------------------
# Entity-vs-individual insight charts (01_02)
# ---------------------------------------------------------------------------
def plot_top_entities(tidy, title=None, color=ENTITY_COLOR, ax=None):
    """Horizontal bar of the top entities (tidy: entity, n_sales), largest at top."""
    ax = ax or plt.subplots(figsize=(8, 5))[1]
    d = tidy.iloc[::-1]                            # so the largest sits on top
    bars = ax.barh(d["entity"], d["n_sales"], color=color)
    ax.bar_label(bars, padding=3, fontsize=8)
    ax.set_xlabel("sales"); ax.set_title(title or "Top entities")
    ax.margins(x=0.13)
    return ax


def plot_entity_metric_by_group(sub, order, metric="ppsf", title=None, money="k", ax=None):
    """Grouped horizontal bars — entity-buyer vs individual on one metric (`price`
    or `ppsf`), one pair per group, the entity-minus-individual % gap labelled at
    the right. Entity = orange, individual = blue (the reserved pair). Groups with
    too few entity buys (`reliable` == False) are drawn muted with an n= flag and
    no gap, so a swing off n=2 never reads as signal.

    `sub` is one year of sd.entity_individual_split; `order` lists the groups,
    first drawn at the top. `money`: 'k' ($k) for price, 'plain' ($) for $/sqft.
    """
    ce, ci = f"{metric}_ent", f"{metric}_ind"
    d = sub.set_index("group").loc[list(order)][::-1]
    y = np.arange(len(d)); h = 0.38
    ax = ax or plt.subplots(figsize=(8.5, 6))[1]
    fmt = (lambda v: f"${v/1000:,.0f}k") if money == "k" else (lambda v: f"${v:,.0f}")
    xmax = float(np.nanmax(d[[ce, ci]].to_numpy()))
    for i, (_, r) in enumerate(d.iterrows()):
        rel = bool(r["reliable"])
        ax.barh(i + h / 2, r[ci], height=h, color=NON_ENTITY_COLOR, zorder=3,
                alpha=1.0 if rel else 0.35)
        ax.barh(i - h / 2, r[ce], height=h, color=ENTITY_COLOR, zorder=3,
                alpha=1.0 if rel else 0.35)
        if pd.notna(r[ci]):
            ax.text(r[ci] + xmax * 0.01, i + h / 2, fmt(r[ci]), va="center", fontsize=7.5, color=INK)
        if pd.notna(r[ce]):
            ax.text(r[ce] + xmax * 0.01, i - h / 2, fmt(r[ce]), va="center", fontsize=7.5, color=INK)
        if rel and pd.notna(r[f"{metric}_diff_pct"]):
            dv = r[f"{metric}_diff_pct"]
            ax.text(xmax * 1.17, i, f"{dv:+.0f}%", va="center", ha="right", fontsize=9,
                    fontweight="bold", color=(UP_COLOR if dv > 0 else DOWN_COLOR))
        else:
            ax.text(xmax * 1.17, i, f"n={int(r['n_ent'])}", va="center", ha="right",
                    fontsize=8, style="italic", color=MUTED)
    ax.set_yticks(y); ax.set_yticklabels([_titlecase_area(n) for n in d.index], fontsize=9)
    ax.set_xlim(0, xmax * 1.32)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: fmt(v)))
    ax.text(xmax * 1.17, len(d) - 0.3, "entity Δ", ha="right", fontsize=8, color=MUTED)
    ax.set_title(title or f"Entity vs individual — {metric}", fontsize=12,
                 fontweight="bold", color=INK, loc="left", pad=10)
    ax.spines[["top", "right"]].set_visible(False); ax.tick_params(left=False)
    ax.barh(0, 0, color=ENTITY_COLOR, label="entity buyer")     # legend proxies
    ax.barh(0, 0, color=NON_ENTITY_COLOR, label="individual")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, frameon=False, fontsize=9)
    return ax


def plot_sales_by_year(split, ax=None):
    """Entity vs non-entity sales over years; total in the title, YoY% on each dot."""
    ax = ax or plt.subplots(figsize=(8, 4.5))[1]
    x = split["meta_year"].astype(str).tolist()
    for col in ("non_entity", "entity"):
        ax.plot(x, split[col], "o-", color=_SPLIT[col], lw=2, label=col.replace("_", "-"))
        _annotate_yoy(ax, range(len(x)), split[col], color=_SPLIT[col])
    ax.set_xlabel("year"); ax.set_ylabel("sales")
    ax.set_title(f"Sales by year — total sales = {int(split['total'].sum()):,}")
    ax.legend(); ax.margins(y=0.18)
    return ax


def plot_seasonality(split, ax=None):
    """Entity vs non-entity sales by calendar month (seasonality)."""
    ax = ax or plt.subplots(figsize=(8, 4.5))[1]
    for col in ("non_entity", "entity"):
        ax.plot(split["sale_month"], split[col], "o-", color=_SPLIT[col], lw=2,
                label=col.replace("_", "-"))
    ax.set_xlabel("month"); ax.set_ylabel("sales")
    ax.set_title("Seasonality — sales by month")
    ax.set_xticks(range(1, 13)); ax.legend()
    return ax


def plot_neighborhood_split(split, n=20, bottom=False, ax=None):
    """Stacked horizontal bar (non-entity + entity) for the top/bottom-n
    neighborhoods, sorted by total sales."""
    ax = ax or plt.subplots(figsize=(9, 8))[1]
    d = split.sort_values("total", ascending=False)
    d = (d.tail(n) if bottom else d.head(n)).iloc[::-1]     # most on top
    y = d[K.REPORT_GEO]
    ax.barh(y, d["non_entity"], color=NON_ENTITY_COLOR, label="non-entity")
    ax.barh(y, d["entity"], left=d["non_entity"], color=ENTITY_COLOR, label="entity")
    ne, en, tot = d["non_entity"].to_numpy(), d["entity"].to_numpy(), d["total"].to_numpy()
    for yi in range(len(d)):
        t = tot[yi]
        if not t:
            continue
        if ne[yi] / t >= 0.05:                             # non-entity % centered in its segment
            ax.text(ne[yi] / 2, yi, f"{ne[yi]/t*100:.0f}%", ha="center", va="center",
                    fontsize=7, color="white")
        if en[yi] / t >= 0.05:                             # entity % centered in its segment
            ax.text(ne[yi] + en[yi] / 2, yi, f"{en[yi]/t*100:.0f}%", ha="center", va="center",
                    fontsize=7, color="white")
        ax.annotate(f"{int(t):,}", (t, yi), textcoords="offset points",   # total at bar end
                    xytext=(3, 0), va="center", fontsize=7, color="#333")
    which = "Bottom" if bottom else "Top"
    ax.set_xlabel("sales"); ax.margins(x=0.08)
    ax.set_title(f"{which} {n} neighborhoods by sales (entity vs non-entity)")
    ax.legend(loc="lower right")
    return ax


def plot_median_price_by_month(split, ax=None, annotate=True):
    """Median price by month, entity vs non-entity (seasonal price); dots labelled
    with the median price ($k)."""
    ax = ax or plt.subplots(figsize=(9, 5))[1]
    for col in ("non_entity", "entity"):
        ax.plot(split["sale_month"], split[col], "o-", color=_SPLIT[col], lw=2,
                label=col.replace("_", "-"))
        if annotate:
            for xm, yv in zip(split["sale_month"], split[col]):
                if yv == yv:
                    ax.annotate(f"${yv/1000:,.0f}k", (xm, yv), textcoords="offset points",
                                xytext=(0, 7), ha="center", fontsize=7, color=_SPLIT[col])
    _thousands(ax)
    ax.margins(y=0.15)
    ax.set_xlabel("month"); ax.set_ylabel("median price")
    ax.set_title("Median price by month (entity vs non-entity)")
    ax.set_xticks(range(1, 13)); ax.legend()
    return ax


def plot_flipper_leaderboard(tbl, n=12, ax=None, title=None):
    """Horizontal bars of the most active flipper entities (sd.top_flippers), bars
    coloured by home-turf region, labelled with flip count, median uplift and turf
    neighborhood — continuing the neighborhood story into 'who does the flipping'."""
    d = tbl.head(n).iloc[::-1]
    colors = [REGION_COLORS.get(r, MUTED) for r in d["region"]] if "region" in d else TOTAL_COLOR
    ax = ax or plt.subplots(figsize=(9.5, 6))[1]
    ax.barh(range(len(d)), d["flips"], color=colors, zorder=3)
    xmax = float(d["flips"].max())
    for i, (_, r) in enumerate(d.iterrows()):
        ax.text(r["flips"] + xmax * 0.015, i,
                f"{int(r['flips'])} flips · +{r['med_return']*100:.0f}% · {_titlecase_area(r['turf'])}",
                va="center", fontsize=8, color=INK)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels([_titlecase_area(f) for f in d["flipper"]], fontsize=8.5)
    ax.set_xlim(0, xmax * 1.5); ax.set_xlabel("flips (bought & resold within a year), 2022–25")
    ax.set_title(title or "Who's doing the flipping — most active flipper entities",
                 fontsize=12, fontweight="bold", color=INK, loc="left", pad=10)
    ax.spines[["top", "right"]].set_visible(False); ax.tick_params(left=False)
    if "region" in d:
        present = [s for s in ("North", "West", "South", "Central") if s in set(d["region"])]
        handles = [plt.Rectangle((0, 0), 1, 1, color=REGION_COLORS[s]) for s in present]
        ax.legend(handles, [f"{s} Side" for s in present], loc="lower right", frameon=False, fontsize=9)
    return ax


def plot_flips_by_year(tidy, partial_years=(), ax=None, title=None):
    """Flip count per year (bars), the median resale uplift labelled inside each bar.
    `tidy` = sd.flips_by_year. Any `partial_years` (truncated by the data window) are
    greyed and marked 'partial' so a short bar isn't misread as a real decline."""
    ax = ax or plt.subplots(figsize=(7.5, 4.4))[1]
    years = [int(y) for y in tidy["year"]]
    n = tidy["n_flips"].to_numpy()
    colors = [MUTED if y in partial_years else TOTAL_COLOR for y in years]
    ax.bar([str(y) for y in years], n, width=0.62, color=colors, zorder=3)
    for i, y in enumerate(years):
        ax.text(i, n[i] + max(n) * 0.012, f"{int(n[i]):,}", ha="center", va="bottom",
                fontsize=12, fontweight="bold", color=INK)
        if "med_return" in tidy:
            ax.text(i, n[i] / 2, f"+{tidy['med_return'].iloc[i]*100:.0f}%", ha="center",
                    va="center", fontsize=9, fontweight="bold", color="white")
        if y in partial_years:
            ax.text(i, n[i] + max(n) * 0.07, "partial", ha="center", fontsize=8,
                    style="italic", color=MUTED)
    ax.set_ylim(0, max(n) * 1.18)
    ax.set_title(title or "Flips by year", fontsize=12, fontweight="bold",
                 color=INK, loc="left", pad=12)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_yticks([]); ax.tick_params(left=False, axis="x", labelsize=11, colors=INK)
    ax.margins(x=0.02)
    return ax


def plot_flip_buysell(tbl, n=10, ax=None, title=None):
    """Paired horizontal bars — median BUY vs median RESALE per neighborhood among
    flips, with the % uplift and median hold labelled at the right. `tbl` =
    sd.flip_returns_by_neighborhood. Light→dark 'buy→sell' ramp (same then/now blue
    as the price charts); uplift is green + a '+' sign (redundant, CVD-safe)."""
    d = tbl.head(n).iloc[::-1]
    y = np.arange(len(d)); h = 0.38
    ax = ax or plt.subplots(figsize=(9.2, 6))[1]
    ax.barh(y + h / 2, d["med_buy"], height=h, color=PRIOR_COLOR, label="median buy", zorder=3)
    ax.barh(y - h / 2, d["med_sell"], height=h, color=TOTAL_COLOR, label="median resale", zorder=3)
    xmax = float(d["med_sell"].max())
    for i, (_, r) in enumerate(d.iterrows()):
        ax.text(r["med_sell"] + xmax * 0.01, i - h / 2, f"${r['med_sell']/1000:,.0f}k", va="center", fontsize=8, color=INK)
        ax.text(r["med_buy"] + xmax * 0.01, i + h / 2, f"${r['med_buy']/1000:,.0f}k", va="center", fontsize=8, color="#9aa0a6")
        if "n_flips" in d:
            ax.text(xmax * 1.15, i, f"{int(r['n_flips'])}", va="center", ha="right", fontsize=8.5, color=INK)
        ax.text(xmax * 1.30, i, f"+{r['uplift_pct']:.0f}%", va="center", ha="right",
                fontsize=9, fontweight="bold", color=UP_COLOR)
        ax.text(xmax * 1.45, i, f"{int(r['med_hold'])}d", va="center", ha="right", fontsize=8, color=MUTED)
    ax.set_yticks(y); ax.set_yticklabels([_titlecase_area(g) for g in d[d.columns[0]]], fontsize=9)
    ax.set_xlim(0, xmax * 1.55)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))
    if "n_flips" in d:
        ax.text(xmax * 1.15, len(d) - 0.35, "n", ha="right", fontsize=8, color=MUTED)
    ax.text(xmax * 1.30, len(d) - 0.35, "uplift", ha="right", fontsize=8, color=MUTED)
    ax.text(xmax * 1.45, len(d) - 0.35, "hold", ha="right", fontsize=8, color=MUTED)
    ax.set_title(title or "Flip economics by neighborhood — median buy vs resale",
                 fontsize=12, fontweight="bold", color=INK, loc="left", pad=10)
    ax.spines[["top", "right"]].set_visible(False); ax.tick_params(left=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=2, frameon=False, fontsize=9)
    return ax


def plot_flip_share(tbl, n=12, ax=None, title=None, value="flip_share"):
    """Horizontal bars of flip intensity per neighborhood, coloured by region.
    `value='flip_share'` plots the % of sales that were flips (labelled with the
    count); `value='flips'` plots the raw flip COUNT (labelled with the share). Feed
    `tbl` sorted to match (sd.flip_geography(sort_by=...)). '1 in N is a flip' /
    'most flips' from the same renderer."""
    is_share = value == "flip_share"
    d = tbl.head(n).iloc[::-1]
    colors = [REGION_COLORS.get(r, MUTED) for r in d["region"]] if "region" in d else TOTAL_COLOR
    ax = ax or plt.subplots(figsize=(9, 6))[1]
    ax.barh(range(len(d)), d[value], color=colors, zorder=3)
    xmax = float(d[value].max())
    for i, (_, r) in enumerate(d.iterrows()):
        lab = (f"{r['flip_share']:.0f}%  ({int(r['flips'])} flips)" if is_share
               else f"{int(r['flips'])} flips  ({r['flip_share']:.0f}%)")
        ax.text(r[value] + xmax * 0.015, i, lab, va="center", fontsize=8, color=INK)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels([_titlecase_area(g) for g in d[d.columns[0]]], fontsize=9)
    ax.set_xlim(0, xmax * (1.28 if is_share else 1.34))
    if is_share:
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
        ax.set_xlabel("share of the neighborhood's 2022–25 sales that were flips")
    else:
        ax.set_xlabel("number of flips, 2022–25")
    ax.set_title(title or ("Where Chicago flips concentrate" if is_share
                           else "Neighborhoods with the most flips"),
                 fontsize=12, fontweight="bold", color=INK, loc="left", pad=10)
    ax.spines[["top", "right"]].set_visible(False); ax.tick_params(left=False)
    if "region" in d:
        present = [s for s in ("North", "West", "South", "Central") if s in set(d["region"])]
        handles = [plt.Rectangle((0, 0), 1, 1, color=REGION_COLORS[s]) for s in present]
        ax.legend(handles, [f"{s} Side" for s in present], loc="lower right", frameon=False, fontsize=9)
    return ax


def plot_entity_buyer_leaderboard(tbl, n=12, ax=None, title=None):
    """Horizontal bars of the most active entity buyers (sd.entity_buyer_leaderboard),
    each bar coloured by the buyer's home-turf SIDE (region palette) so the
    South-investor tilt is visible at a glance. Bar labelled with homes bought and
    median price; a side legend keyed to the colours."""
    d = tbl.head(n).iloc[::-1]                         # most active on top
    colors = [REGION_COLORS.get(s, MUTED) for s in d["top_side"]] if "top_side" in d else MUTED
    ax = ax or plt.subplots(figsize=(9, 6))[1]
    bars = ax.barh(range(len(d)), d["homes"], color=colors, zorder=3)
    xmax = d["homes"].max()
    for i, (_, r) in enumerate(d.iterrows()):
        ax.text(r["homes"] + xmax * 0.012, i, f"{int(r['homes'])} homes · ${r['median_price']/1000:,.0f}k med",
                va="center", fontsize=8, color=INK)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels([_titlecase_area(e) for e in d["entity"]], fontsize=8.5)
    ax.set_xlim(0, xmax * 1.32); ax.set_xlabel("single-family homes bought, 2022–25")
    ax.set_title(title or "Chicago's most active single-family investors", fontsize=12,
                 fontweight="bold", color=INK, loc="left", pad=10)
    ax.spines[["top", "right"]].set_visible(False); ax.tick_params(left=False)
    if "top_side" in d:
        present = set(d["top_side"])
        seen = [s for s in ("North", "West", "South") if s in present]   # canonical N→W→S
        handles = [plt.Rectangle((0, 0), 1, 1, color=REGION_COLORS[s]) for s in seen]
        ax.legend(handles, [f"{s} Side" for s in seen], loc="lower right", frameon=False, fontsize=9)
    return ax


def plot_entity_neighborhood_heatmap(matrix, ax=None):
    """Heatmap: top entity buyers (rows) x neighborhood (cols) sale counts —
    which entity prioritizes which neighborhood. Sequential blue ramp."""
    ax = ax or plt.subplots(figsize=(11, 4))[1]
    im = ax.imshow(matrix.values, cmap="Blues", aspect="auto")
    ax.set_xticks(range(matrix.shape[1]))
    ax.set_xticklabels(matrix.columns, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(matrix.shape[0]))
    ax.set_yticklabels(matrix.index, fontsize=9)
    hi = matrix.values.max() if matrix.size else 0
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            v = matrix.values[i, j]
            if v:
                ax.text(j, i, int(v), ha="center", va="center", fontsize=7,
                        color="white" if v > hi * 0.6 else "#222")
    ax.figure.colorbar(im, ax=ax, shrink=0.8, label="sales")
    ax.set_title("Top entity buyers × neighborhood (who buys where)")
    return ax


def plot_volume_price_grid(pv, neighborhoods, value_label="median price", money="k",
                           ncols=5, panel_size=(2.7, 2.6), suptitle=None):
    """Small-multiple connected scatterplots — one panel per neighborhood, the
    price/quantity plane traced over time: x = sale VOLUME, y = the price metric,
    each year a dot (light→dark = early→late) with an arrow on the last step.

    Reads directly as supply-demand: up-and-RIGHT = price and volume rose together
    (demand); up-and-LEFT = price rose while volume dried up (supply-constrained).
    Per-panel autoscale, so each neighborhood's SHAPE is what you compare.
    """
    order = [n for n in neighborhoods if n in set(pv[K.REPORT_GEO])]
    ncols = min(ncols, len(order)) or 1
    nrows = -(-len(order) // ncols)
    fig, axes = plt.subplots(nrows, ncols, squeeze=False,
                             figsize=(panel_size[0] * ncols, panel_size[1] * nrows))
    axes = axes.ravel()
    for ax, nb in zip(axes, order):
        g = pv[pv[K.REPORT_GEO] == nb].sort_values("meta_year")
        vx, py = g["volume"].to_numpy(), g["median_value"].to_numpy()
        yrs = g["meta_year"].astype(str).tolist()
        ax.plot(vx, py, "-", color="#9ec5f4", lw=1.5, zorder=1)
        ax.scatter(vx, py, c=range(len(vx)), cmap="Blues", s=48,
                   edgecolor="#184f95", linewidth=0.6, zorder=2)
        if len(vx) >= 2:                       # arrowhead on the final segment (direction)
            ax.annotate("", xy=(vx[-1], py[-1]), xytext=(vx[-2], py[-2]),
                        arrowprops=dict(arrowstyle="-|>", color="#184f95", lw=1.5))
        for i in (0, len(yrs) - 1):            # label first & last year
            ax.annotate(yrs[i], (vx[i], py[i]), textcoords="offset points",
                        xytext=(4, 4), fontsize=6, color="#555")
        if money == "k":                       # $k — price / $-per-bed (hundreds of k)
            _thousands(ax)
        elif money == "plain":                 # plain $ — $/sqft (hundreds of dollars)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
        ax.set_title(nb, fontsize=8)
        ax.tick_params(labelsize=6)
        ax.margins(0.18)
        ax.invert_xaxis()          # more sales on the LEFT -> falling-volume path reads left->right
    for ax in axes[len(order):]:
        ax.set_visible(False)
    fig.supxlabel("←  more sales      volume (sales / year)      fewer  →", fontsize=9)
    fig.supylabel(value_label, fontsize=9)
    if suptitle:
        fig.suptitle(suptitle, fontsize=12)
    fig.tight_layout()
    return fig