"""Descriptive sales-market summaries — each takes a frame, returns a tidy
DataFrame ready to plot. Population-agnostic: pass all sales, or a slice (entity,
stale, a neighborhood). Pure aggregation, no plotting (renderers live in
viz/charts.py). Column-shape diagnostics live in data/distributions.py.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from chicago_housing import constants as K


def sales_by_year(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("meta_year").size()
              .rename("n_sales").reset_index())


def sales_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Seasonality — counts by calendar month, pooled across years."""
    return (df.groupby("sale_month").size()
              .rename("n_sales").reset_index())


def top_neighborhoods(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return (df.groupby(K.REPORT_GEO).size()
              .rename("n_sales").sort_values(ascending=False)
              .head(n).reset_index())


def sales_by_neighborhood_wide(df: pd.DataFrame, years=("2022", "2023", "2024", "2025"),
                               group_by = 'both',
                               sort_by: str | None = None) -> pd.DataFrame:
    """Per-neighborhood sale VOLUME, one column per year + the first→last %change.

    A wide reference table (feeds the Headline-1 neighborhood summary and is the
    data behind the Top-20 bars). `sort_by` defaults to the last year (busiest on
    top); pass a year string or 'delta_pct' to re-rank.

    group_by options: "both", "neighborhood", "region"
    """
    yrs = [str(y) for y in years]
    if group_by == "both":
        g = (df.groupby([K.REPORT_GEO, K.REGION_COL, "meta_year"]).size()
           .unstack("meta_year", fill_value=0))
    elif group_by == "neighborhood":
        g = (df.groupby([K.REPORT_GEO, "meta_year"]).size()
                   .unstack("meta_year", fill_value=0))
    else:
        g = (df.groupby([K.REGION_COL, "meta_year"]).size()
                   .unstack("meta_year", fill_value=0))
    for y in yrs:
        if y not in g.columns:
            g[y] = 0
    g = g[yrs]
    g["delta_pct"] = ((g[yrs[-1]] - g[yrs[0]]) /
                      g[yrs[0]].replace(0, np.nan) * 100).round(1)
    key = sort_by or yrs[-1]
    return g.sort_values(key, ascending=False).reset_index()


def median_price_two_year(df: pd.DataFrame, year_a="2022", year_b="2025") -> pd.DataFrame:
    """Per-neighborhood median price in TWO years (+ counts + % change) — the
    two-point 'then vs now' behind the Q3 paired-bar charts and price table.

    Index = neighborhood; columns med_{a}/n_{a}, med_{b}/n_{b}, delta_pct. Keep the
    counts so callers can guard thin cells (a median off <10 sales is noise).
    """
    ya, yb = str(year_a), str(year_b)
    yr = df["meta_year"].astype("string")
    a = df[yr == ya].groupby(K.REPORT_GEO)[K.TARGET_RAW].agg(**{f"med_{ya}": "median", f"n_{ya}": "size"})
    b = df[yr == yb].groupby(K.REPORT_GEO)[K.TARGET_RAW].agg(**{f"med_{yb}": "median", f"n_{yb}": "size"})
    m = a.join(b, how="outer")
    m[[f"n_{ya}", f"n_{yb}"]] = m[[f"n_{ya}", f"n_{yb}"]].fillna(0).astype(int)
    m["delta_pct"] = ((m[f"med_{yb}"] - m[f"med_{ya}"]) / m[f"med_{ya}"] * 100).round(1)
    return m


def median_price_by_neighborhood_year(df: pd.DataFrame, neighborhoods=None) -> pd.DataFrame:
    """Median sale price AND sale count per neighborhood per year (long form)."""
    d = df if neighborhoods is None else df[df[K.REPORT_GEO].isin(neighborhoods)]
    return (d.groupby([K.REPORT_GEO, "meta_year"])[K.TARGET_RAW]
              .agg(median_price="median", n_sales="size").reset_index())


def price_and_volume_by_neighborhood_year(df: pd.DataFrame, value_col: str | None = None,
                                          neighborhoods=None) -> pd.DataFrame:
    """Per neighborhood per year: sale VOLUME (count) and the MEDIAN of `value_col`
    (default sale price; pass 'price_per_bldg_sqft' or 'price_per_bed'). Feeds the
    volume<->price connected-scatter grid — 'as price rose, did volume rise too?'.
    """
    col = value_col or K.TARGET_RAW
    d = df if neighborhoods is None else df[df[K.REPORT_GEO].isin(neighborhoods)]
    v = pd.to_numeric(d[col], errors="coerce")
    return (d.assign(_v=v).groupby([K.REPORT_GEO, "meta_year"])
              .agg(volume=("_v", "size"), median_value=("_v", "median")).reset_index())


def neighborhoods_by_year_price(df: pd.DataFrame, year="2022", min_sales: int = 20) -> pd.Series:
    """Neighborhoods ranked by median sale price IN `year` (descending).

    Keeps only neighborhoods with >= min_sales that year, so a single luxury sale
    can't top the ranking. Slice .head(n) for most-expensive, .tail(n) for least.
    """
    d = df[df["meta_year"].astype("string") == str(year)]
    g = d.groupby(K.REPORT_GEO)[K.TARGET_RAW].agg(median_price="median", n_sales="size")
    return g[g["n_sales"] >= min_sales]["median_price"].sort_values(ascending=False)


def top_sales(df: pd.DataFrame, year=None, n: int = 5, include_size: bool = True) -> pd.DataFrame:
    """The n most expensive individual sales (optionally within one `year`) — the
    Q4 'trophy homes' leaderboard.

    Tidy, reader-ready columns: year, price, [$/sqft, sqft, beds, baths],
    year_built, neighborhood, address, side. `include_size=False` drops the
    sqft/beds/baths columns — used for CONDOS, where those fields are ~70% null.
    Sorted by price, priciest first.
    """
    d = df if year is None else df[df["meta_year"].astype("string") == str(year)]
    d = d.nlargest(n, K.TARGET_RAW)
    price = pd.to_numeric(d[K.TARGET_RAW])
    out = pd.DataFrame({"year": d["meta_year"].astype("string").values,
                        "price": price.round().astype("Int64").values})
    if include_size:
        sqft = pd.to_numeric(d["char_bldg_sf"])
        out["$/sqft"] = (price / sqft).round().astype("Int64").values
        out["sqft"] = sqft.round().astype("Int64").values
        out["beds"] = pd.to_numeric(d["char_beds"]).astype("Int64").values
        out["baths"] = pd.to_numeric(d["char_fbath"]).astype("Int64").values
    out["year_built"] = pd.to_numeric(d["char_yrblt"]).round().astype("Int64").values
    out["neighborhood"] = d[K.REPORT_GEO].str.title().values
    out["address"] = d[K.ADDRESS].astype("string").values
    if K.REGION_COL in d.columns:
        out["side"] = d[K.REGION_COL].astype("string").values
    return out.reset_index(drop=True)


def entity_individual_split(df: pd.DataFrame, by, flag: str = "entity_buyer",
                            years=("2022", "2025"), min_entity_n: int = 10) -> pd.DataFrame:
    """Entity-BUYER vs individual medians — both PRICE and $/sqft — per `by` group
    per year. The Q5 'do investors pay less?' table.

    For each (group, year): entity & individual sale counts, entity share, median
    price and median $/sqft for each, and the entity-minus-individual % gap on each.
    `$/sqft` is the median of the per-sale ratio (not median price / median sqft).
    `reliable` = entity n >= min_entity_n, so callers can guard thin cells (a gap
    off n=2 is noise). Default flag is entity_BUYER (a buying story) — NOT is_entity.
    """
    d = df.copy()
    price = pd.to_numeric(d[K.TARGET_RAW], errors="coerce")
    sqft = pd.to_numeric(d["char_bldg_sf"], errors="coerce").replace(0, np.nan)
    d["_price"], d["_ppsf"] = price, price / sqft
    d["_grp"] = np.where(d[flag].fillna(False), "ent", "ind")
    yr = d["meta_year"].astype("string")

    rows = []
    for y in (str(x) for x in years):
        for g, sub in d[yr == y].groupby(by, observed=True):
            ent, ind = sub[sub["_grp"] == "ent"], sub[sub["_grp"] == "ind"]
            rows.append({
                "group": g, "year": y, "n_ent": len(ent), "n_ind": len(ind),
                "ent_share": round(len(ent) / max(len(sub), 1) * 100, 1),
                "price_ent": ent["_price"].median(), "price_ind": ind["_price"].median(),
                "ppsf_ent": ent["_ppsf"].median(), "ppsf_ind": ind["_ppsf"].median(),
            })
    r = pd.DataFrame(rows)
    r["price_diff_pct"] = ((r["price_ent"] - r["price_ind"]) / r["price_ind"] * 100).round(1)
    r["ppsf_diff_pct"] = ((r["ppsf_ent"] - r["ppsf_ind"]) / r["ppsf_ind"] * 100).round(1)
    r["reliable"] = r["n_ent"] >= min_entity_n
    return r


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
    g = df.groupby("meta_pin")[K.TARGET_RAW].agg(["min", "max", "size"])
    g = g[g["size"] > 1].copy()
    g["price_ratio"] = g["max"] / g["min"]
    return g.reset_index().rename(columns={"size": "n_sales"})


def flips(df: pd.DataFrame, max_hold_days: int = 365) -> pd.DataFrame:
    """Flip pairs: the SAME parcel bought then resold within `max_hold_days`.

    Pairs each sale with that parcel's NEXT sale (buy -> sell), keeping pairs held
    <= max_hold_days. Columns: neighborhood, region, buy/sell date & price,
    hold_days, gross_return (sell/buy - 1), entity_buyer (was the buyer of the BUY
    leg — the flipper — an entity). Both legs are arm's-length (non-market already
    dropped), so returns are market-to-market. NOTE: a 3-4yr window only catches
    flips whose buy AND sell both fall inside it — a floor, not a census.
    """
    d = df.copy()
    d["meta_sale_date"] = pd.to_datetime(d["meta_sale_date"])
    d = d.sort_values(["meta_pin", "meta_sale_date"])
    price = pd.to_numeric(d[K.TARGET_RAW], errors="coerce")
    g = d.groupby("meta_pin", sort=False)
    out = pd.DataFrame({
        K.REPORT_GEO: d[K.REPORT_GEO].values,
        "buy_date": d["meta_sale_date"].values, "buy_price": price.values,
        "sell_date": g["meta_sale_date"].shift(-1).values,
        "sell_price": price.groupby(d["meta_pin"], sort=False).shift(-1).values,
        "entity_buyer": d["entity_buyer"].values if "entity_buyer" in d else False,
        "meta_pin": d["meta_pin"].values,
        # the FLIPPER, named on both ends: who BOUGHT it (buy leg) & who SOLD it (sell leg)
        "buyer_name": d[K.BUYER_NAME].astype("string").values,
        "seller_name": g[K.SELLER_NAME].shift(-1).values,
        # the EXIT: who the flipper resold to, and whether that end buyer is an entity
        # (another investor) or an individual (retail) — from the sell-leg buyer
        "sold_to_name": g[K.BUYER_NAME].shift(-1).values,
        "sold_to_entity": g["entity_buyer"].shift(-1).values if "entity_buyer" in d else False,
    })
    if K.REGION_COL in d.columns:
        out[K.REGION_COL] = d[K.REGION_COL].values
    if K.ADDRESS in d.columns:
        out["address"] = d[K.ADDRESS].astype("string").values
    out = out.dropna(subset=["sell_date", "buy_price", "sell_price"])
    out["hold_days"] = (out["sell_date"] - out["buy_date"]).dt.days
    out["gross_return"] = out["sell_price"] / out["buy_price"] - 1
    return out[(out["hold_days"] >= 0) & (out["hold_days"] <= max_hold_days)].reset_index(drop=True)


def flip_geography(df: pd.DataFrame, flip_df: pd.DataFrame, by: str = None,
                   min_sales: int = 100, n: int = 15, sort_by: str = "flip_share") -> pd.DataFrame:
    """Per-area flip intensity: total sales, flip count, flip SHARE (%), median flip
    return, region. `df` = all sales (denominator), `flip_df` = sd.flips output.
    Keeps areas with >= min_sales so a share isn't off a tiny base; `sort_by`
    ('flip_share' or 'flips') picks the ranking. `by` defaults to neighborhood
    (pass REGION_COL for the 3/4-region cut)."""
    by = by or K.REPORT_GEO
    tot = df.groupby(by, observed=True).size().rename("total")
    fc = flip_df.groupby(by, observed=True).size().rename("flips")
    ret = flip_df.groupby(by, observed=True)["gross_return"].median().rename("med_return")
    out = pd.concat([tot, fc, ret], axis=1)
    out["flips"] = out["flips"].fillna(0).astype(int)
    out = out[out["total"] >= min_sales].copy()
    out["flip_share"] = (out["flips"] / out["total"] * 100).round(1)
    if by == K.REPORT_GEO and K.REGION_COL in df.columns:
        out["region"] = df.drop_duplicates(K.REPORT_GEO).set_index(K.REPORT_GEO)[K.REGION_COL]
    return out.sort_values(sort_by, ascending=False).head(n).reset_index()


def flips_by_year(flip_df: pd.DataFrame, by: str = "buy") -> pd.DataFrame:
    """Flip count + median return per year, attributed by the `by`='buy' (acquisition)
    or 'sell' (exit) date. Tidy (year, n_flips, med_return). NOTE the 4-year window
    truncates an endpoint — by buy-year the LAST year is partial (its flips may not
    resell until after the data ends); by sell-year the FIRST year is partial."""
    col = "buy_date" if by == "buy" else "sell_date"
    yr = pd.to_datetime(flip_df[col]).dt.year
    return (flip_df.assign(_y=yr).groupby("_y")
            .agg(n_flips=("gross_return", "size"), med_return=("gross_return", "median"))
            .reset_index().rename(columns={"_y": "year"}).sort_values("year"))


def top_flippers(flip_df: pd.DataFrame, n: int = 12, entity_only: bool = True) -> pd.DataFrame:
    """Most active FLIPPERS: the entity that bought a parcel and resold it within a
    year (buy-leg buyer, normalized). Per flipper: flip count, median resale uplift,
    median hold, home-turf neighborhood + region. `entity_only` keeps LLC/entity
    flippers (the ~73% that are). Sorted by flip count."""
    d = flip_df[flip_df["entity_buyer"]] if entity_only else flip_df
    d = d.assign(flipper=normalize_entity_name(d["buyer_name"]))
    g = d.groupby("flipper").agg(flips=("gross_return", "size"),
                                 med_return=("gross_return", "median"),
                                 med_hold=("hold_days", "median"))
    g["turf"] = d.groupby("flipper")[K.REPORT_GEO].agg(lambda x: x.value_counts().index[0])
    if K.REGION_COL in d.columns:
        g["region"] = d.groupby("flipper")[K.REGION_COL].agg(lambda x: x.value_counts().index[0])
    return g.sort_values("flips", ascending=False).head(n).reset_index()


def flip_returns_by_neighborhood(flip_df: pd.DataFrame, df: pd.DataFrame = None,
                                 min_flips: int = 20, n: int = 12) -> pd.DataFrame:
    """Per-neighborhood flip economics (Q8): flip count, median buy & sell price,
    median % uplift and median hold. Keeps neighborhoods with >= min_flips so a
    median isn't off a handful; highest median uplift first. `df` (optional) adds
    the region for colouring."""
    g = flip_df.groupby(K.REPORT_GEO, observed=True).agg(
        n_flips=("gross_return", "size"),
        med_buy=("buy_price", "median"), med_sell=("sell_price", "median"),
        med_return=("gross_return", "median"), med_hold=("hold_days", "median"))
    g = g[g["n_flips"] >= min_flips].copy()
    g["uplift_pct"] = (g["med_return"] * 100).round(0)
    if df is not None and K.REGION_COL in df.columns:
        g["region"] = df.drop_duplicates(K.REPORT_GEO).set_index(K.REPORT_GEO)[K.REGION_COL]
    return g.sort_values("med_return", ascending=False).head(n).reset_index()


# ---------------------------------------------------------------------------
# Entity-name handling + entity-vs-individual splits (for 01_02 insights)
# ---------------------------------------------------------------------------
# trailing legal-form tokens to strip (only at the END — 'LAND TRUST' mid-name stays)
_TRAILING_SUFFIXES = {"LLC", "INC", "LP", "LLP", "PLLC", "LC", "LTD", "CORP", "CORPORATION"}

# curated brand-prefix -> canonical group. Extend as you spot the SAME firm split
# across naming variants (the pure-algorithmic first-word merge over-collapses
# generic prefixes like 'CHICAGO'/'CONSTRUCTION', so we fold only known groups).
ENTITY_ALIASES = {
    "GRANDVIEW": "GRANDVIEW",   # GRANDVIEW CAPITAL + GRANDVIEW HOMES are one group
}


def normalize_entity_name(names: pd.Series, aliases: dict | None = None) -> pd.Series:
    """Canonicalize holding-company names for grouping.

    Uppercase -> strip punctuation, a 'THE', and digits -> drop TRAILING legal
    forms (LLC/INC/...). That alone merges pure punctuation/suffix variants
    ('GRANDVIEW CAPITAL, LLC' == 'GRANDVIEW CAPITAL LLC'). Then `aliases` folds
    known split-groups by prefix, so 'GRANDVIEW HOMES' also joins 'GRANDVIEW'.

    We deliberately DON'T collapse to the first word — that would merge every
    unrelated 'CHICAGO …' / 'CONSTRUCTION …' firm. Extend ENTITY_ALIASES instead.
    """
    aliases = ENTITY_ALIASES if aliases is None else aliases
    s = names.astype("string").str.upper()
    s = s.str.replace(r"[^A-Z0-9 ]", " ", regex=True)   # punctuation -> space
    s = s.str.replace(r"\bTHE\b", " ", regex=True)       # drop 'THE'
    s = s.str.replace(r"\d+", " ", regex=True)           # drop digits
    # strip verbose legal-form tails ('... AN ILLINOIS LIMITED LIABILITY COMPANY',
    # '... A DELAWARE CORPORATION') — common on condo deeds, generic (no state list)
    s = s.str.replace(r"\b(A|AN)\s+\w+\s+(LIMITED\s+LIABILITY\s+(COMPANY|CO)|"
                      r"LIMITED\s+PARTNERSHIP|CORPORATION|CORP)\b", " ", regex=True)
    s = s.str.replace(r"\bLIMITED\s+LIABILITY\s+(COMPANY|CO)\b", " ", regex=True)
    s = s.str.replace(r"\bLIMITED\s+PARTNERSHIP\b", " ", regex=True)
    s = s.str.replace(r"\s+", " ", regex=True).str.strip()

    def _canon(x):
        toks = x.split(" ")
        while toks and toks[-1] in _TRAILING_SUFFIXES:   # peel trailing legal forms
            toks.pop()
        name = " ".join(toks) if toks else x
        for prefix, canon in aliases.items():            # fold known brand groups
            if name.startswith(prefix):
                return canon
        return name
    return s.map(_canon, na_action="ignore")


def top_entities(df: pd.DataFrame, side: str = "buyer", n: int = 10,
                 normalize: bool = True) -> pd.DataFrame:
    """Top-n entity BUYERS (side='buyer') or SELLERS by sale count.

    Restricts to rows flagged as an entity on that side, then counts (normalized)
    names. Returns tidy (entity, n_sales), most active first.
    """
    flag = "entity_buyer" if side == "buyer" else "entity_seller"
    namecol = K.BUYER_NAME if side == "buyer" else K.SELLER_NAME
    d = df[df[flag]]
    names = normalize_entity_name(d[namecol]) if normalize else d[namecol].astype("string")
    return (names.value_counts().head(n)
            .rename("n_sales").rename_axis("entity").reset_index())


def entity_price_table(df: pd.DataFrame, neighborhoods, year_a="2022", year_b="2025",
                       flag: str = "is_entity") -> pd.DataFrame:
    """Per-neighborhood entity-vs-individual comparison between two years.

    Neighborhoods are kept in the order passed (i.e. volume rank). Columns: entity
    and non-entity SALE COUNTS in year_a & year_b with their % change; entity and
    non-entity MEDIAN PRICE in each year with their % change; and finally the
    year_b entity-minus-non-entity price gap. NaN where a group had no sales that
    year (so a % off a zero base is NaN, not inf).
    """
    idx = list(neighborhoods)

    def _snap(year):
        d = df[df[K.REPORT_GEO].isin(idx) &
               (df["meta_year"].astype("string") == str(year))].copy()
        d["_grp"] = np.where(d[flag].fillna(False), "entity", "non_entity")
        cnt = d.groupby([K.REPORT_GEO, "_grp"]).size().unstack("_grp", fill_value=0)
        med = d.groupby([K.REPORT_GEO, "_grp"])[K.TARGET_RAW].median().unstack("_grp")
        for c in ("entity", "non_entity"):
            if c not in cnt.columns: cnt[c] = 0
            if c not in med.columns: med[c] = np.nan
        return cnt.reindex(idx).fillna(0), med.reindex(idx)

    ca, ma = _snap(year_a)
    cb, mb = _snap(year_b)
    pct = lambda a, b: ((b - a) / a.replace(0, np.nan) * 100).round(1)

    out = pd.DataFrame(index=pd.Index(idx, name="neighborhood"))
    out[f"{year_a}_entity_sales"] = ca["entity"].astype(int)
    out[f"{year_b}_entity_sales"] = cb["entity"].astype(int)
    out["entity_sales_%"] = pct(ca["entity"], cb["entity"])
    out[f"{year_a}_non_entity_sales"] = ca["non_entity"].astype(int)
    out[f"{year_b}_non_entity_sales"] = cb["non_entity"].astype(int)
    out["non_entity_sales_%"] = pct(ca["non_entity"], cb["non_entity"])
    out[f"{year_a}_price_entity"] = ma["entity"]
    out[f"{year_b}_price_entity"] = mb["entity"]
    out["entity_price_%"] = pct(ma["entity"], mb["entity"])
    out[f"{year_a}_price_non_entity"] = ma["non_entity"]
    out[f"{year_b}_price_non_entity"] = mb["non_entity"]
    out["non_entity_price_%"] = pct(ma["non_entity"], mb["non_entity"])
    out[f"{year_b}_entity_minus_non_entity_price"] = mb["entity"] - mb["non_entity"]

    # $ columns -> whole dollars (nullable Int64 keeps NaN); % columns keep 1 decimal
    for c in (f"{year_a}_price_entity", f"{year_b}_price_entity",
              f"{year_a}_price_non_entity", f"{year_b}_price_non_entity",
              f"{year_b}_entity_minus_non_entity_price"):
        out[c] = out[c].round().astype("Int64")
    return out.reset_index()


def _entity_split(df: pd.DataFrame, by, flag: str = "is_entity") -> pd.DataFrame:
    """Counts pivoted into entity / non_entity / total columns, grouped by `by`."""
    grp = np.where(df[flag].fillna(False), "entity", "non_entity")
    out = (df.assign(_grp=grp).groupby([by, "_grp"]).size()
             .unstack("_grp", fill_value=0))
    for c in ("entity", "non_entity"):
        if c not in out.columns:
            out[c] = 0
    out["total"] = out["entity"] + out["non_entity"]
    return out.reset_index()


def sales_by_year_split(df: pd.DataFrame, flag: str = "is_entity") -> pd.DataFrame:
    """Sales per year split entity / non_entity / total."""
    return _entity_split(df, "meta_year", flag).sort_values("meta_year")


def sales_by_month_split(df: pd.DataFrame, flag: str = "is_entity") -> pd.DataFrame:
    """Sales per calendar month split entity / non_entity / total (seasonality)."""
    return _entity_split(df, "sale_month", flag).sort_values("sale_month")


def neighborhood_sales_split(df: pd.DataFrame, flag: str = "is_entity") -> pd.DataFrame:
    """Sales per neighborhood split entity / non_entity / total, most active first."""
    return _entity_split(df, K.REPORT_GEO, flag).sort_values("total", ascending=False)


def median_price_by_month_split(df: pd.DataFrame, flag: str = "is_entity") -> pd.DataFrame:
    """Median sale price per month: entity, non_entity, total (seasonal price)."""
    grp = np.where(df[flag].fillna(False), "entity", "non_entity")
    out = (df.assign(_grp=grp).groupby(["sale_month", "_grp"])[K.TARGET_RAW]
             .median().unstack("_grp"))
    out["total"] = df.groupby("sale_month")[K.TARGET_RAW].median()
    return out.reset_index()


def entity_buyer_leaderboard(df: pd.DataFrame, n: int = 15, normalize: bool = True) -> pd.DataFrame:
    """The n most active entity BUYERS with the detail Q6 needs (2022–25 pooled).

    Per buyer: homes bought, median price, total $ spent, dominant side, and the
    home-turf neighborhood ('X of Y buys'). Names are canonicalized via
    normalize_entity_name so split naming variants fold together. Sorted by count.
    """
    d = df[df["entity_buyer"]].copy()
    d["_name"] = normalize_entity_name(d[K.BUYER_NAME]) if normalize else d[K.BUYER_NAME].astype("string")
    d["_price"] = pd.to_numeric(d[K.TARGET_RAW], errors="coerce")

    def _turf(s):
        vc = s.value_counts()
        return f"{s.name if False else vc.index[0]} ({vc.iloc[0]}/{vc.sum()})"

    g = d.groupby("_name").agg(homes=("_price", "size"),
                               median_price=("_price", "median"),
                               total_spent=("_price", "sum"))
    if K.REGION_COL in d.columns:
        g["top_side"] = d.groupby("_name")[K.REGION_COL].apply(lambda s: s.value_counts().index[0])
    g["home_turf"] = d.groupby("_name")[K.REPORT_GEO].apply(_turf)
    return (g.sort_values("homes", ascending=False).head(n)
              .reset_index().rename(columns={"_name": "entity"}))


def entity_neighborhood_matrix(df: pd.DataFrame, side: str = "buyer",
                               top_entities_n: int = 5, top_neighborhoods_n: int = 15,
                               normalize: bool = True) -> pd.DataFrame:
    """Counts matrix: top-n entity buyers (rows) x their most-active neighborhoods
    (cols). Feeds the entity x neighborhood heatmap ('who buys where')."""
    flag = "entity_buyer" if side == "buyer" else "entity_seller"
    namecol = K.BUYER_NAME if side == "buyer" else K.SELLER_NAME
    d = df[df[flag]].copy()
    d["_ent"] = normalize_entity_name(d[namecol]) if normalize else d[namecol].astype("string")
    top_ents = d["_ent"].value_counts().head(top_entities_n).index
    d = d[d["_ent"].isin(top_ents)]
    mat = pd.crosstab(d["_ent"], d[K.REPORT_GEO]).reindex(top_ents)
    cols = mat.sum().sort_values(ascending=False).head(top_neighborhoods_n).index
    return mat[cols]