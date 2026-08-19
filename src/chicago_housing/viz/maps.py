"""Folium maps for the sales EDA. Take an enriched frame (df + flags + lat/lon),
render to an interactive map. Sampled for performance — 30K points chokes folium.
"""

from __future__ import annotations
import folium
from folium.plugins import FastMarkerCluster, HeatMap
import pandas as pd
from chicago_housing import constants as K, config as C
from chicago_housing.viz import charts

CHICAGO = [41.8781, -87.6298]


def region_map_static(ptype=K.SF, geojson_path=None, ax=None, title=None,
                      unmapped_label="Loop (downtown)", label_offsets=None, label_size=19):
    """Static (matplotlib) version of the intro side-map — the Substack-ready PNG.

    Reads the PropertyType's region scheme: SF/MF get the 3-side map (Loop unmapped
    -> greyed); condo gets the 4-region map where the Loop joins a coloured Central.
    Areas absent from the scheme are greyed and labelled `unmapped_label`.
    """
    import geopandas as gpd
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.patheffects as pe
    from chicago_housing.viz import charts

    rmap = ptype.region_map
    rorder = list(ptype.region_order)

    g = gpd.read_file(geojson_path or C.COMMUNITY_AREAS_GEOJSON)[["community", "geometry"]].copy()
    g["community"] = g["community"].str.upper()
    g["region"] = g["community"].map(rmap)                # NaN = unmapped (greyed)
    g = g.to_crs(3435)                                    # planar CRS: true shapes + centroids
    g["_c"] = [charts.LOOP_COLOR if r != r else charts.REGION_COLORS[r] for r in g["region"]]

    ax = ax or plt.subplots(figsize=(8, 9))[1]
    g.plot(ax=ax, color=g["_c"], edgecolor="white", linewidth=0.6)
    offsets = label_offsets or {}                         # per-region (dx, dy) in map feet
    for region in rorder:                                 # haloed label at each region centroid
        sub = g[g["region"] == region]
        if sub.empty:
            continue
        c = sub.dissolve().geometry.centroid.iloc[0]
        dx, dy = offsets.get(region, (0, 0))
        ax.annotate(region.upper(), (c.x + dx, c.y + dy), ha="center", va="center",
                    fontsize=label_size, fontweight="bold", color="white",
                    path_effects=[pe.withStroke(linewidth=3.5, foreground=charts.REGION_COLORS[region])])
    ax.set_axis_off()
    ax.set_title(title or "Chicago's three sides — split by the arms of the Chicago River",
                 fontsize=13, fontweight="bold", color=charts.INK, pad=8)
    handles = [mpatches.Patch(color=charts.REGION_COLORS[r], label=f"{r} Side") for r in rorder]
    if g["region"].isna().any():
        handles.append(mpatches.Patch(color=charts.LOOP_COLOR, label=unmapped_label))
    ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=9)
    return ax


def region_map(enriched: pd.DataFrame | None = None, ptype=K.SF, *, geojson_path=None,
               sales_label="sales 22–25:") -> folium.Map:
    """Intro reference map — Chicago's 77 community areas coloured by 'side', read
    from the PropertyType's region scheme (SF/MF 3-side with Loop greyed; condo
    4-region with Loop in Central). Optionally pass `enriched` to add each area's
    sale count to the hover tooltip."""
    import geopandas as gpd

    rmap = ptype.region_map
    g = gpd.read_file(geojson_path or C.COMMUNITY_AREAS_GEOJSON)[["community", "geometry"]].copy()
    g["community"] = g["community"].str.upper()
    g["region"] = g["community"].map(rmap).fillna("—")    # unmapped -> greyed

    counts = {}
    if enriched is not None:
        counts = enriched.groupby(K.REPORT_GEO).size().to_dict()
    g["n_sales"] = g["community"].map(counts).fillna(0).astype(int)

    def _fill(region):
        return charts.REGION_COLORS.get(region, charts.LOOP_COLOR)

    m = folium.Map(location=CHICAGO, zoom_start=11, tiles="cartodbpositron")
    folium.GeoJson(
        g, name="Community areas",
        style_function=lambda feat: {
            "fillColor": _fill(feat["properties"]["region"]),
            "color": "white", "weight": 1, "fillOpacity": 0.62,
        },
        highlight_function=lambda feat: {"weight": 2.5, "color": "#333", "fillOpacity": 0.78},
        tooltip=folium.GeoJsonTooltip(
            fields=["community", "region", "n_sales"],
            aliases=["", "Side:", sales_label], sticky=True),
    ).add_to(m)

    # big side labels at each region's centroid (projected centroid = accurate)
    for region, sub in g[g["region"].isin(charts.REGION_COLORS)].groupby("region"):
        c = sub.to_crs(3435).dissolve().centroid.to_crs(4326).iloc[0]
        folium.map.Marker(
            [c.y, c.x],
            icon=folium.DivIcon(html=(
                f'<div style="font:700 22px system-ui;color:{charts.REGION_COLORS[region]};'
                f'text-shadow:0 0 4px #fff,0 0 4px #fff,0 0 4px #fff;white-space:nowrap;'
                f'transform:translate(-50%,-50%)">{region.upper()}</div>')),
        ).add_to(m)
    return m


def _valid_coords(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows without usable lat/lon (some geocodes are null)."""
    return df.dropna(subset=["loc_latitude", "loc_longitude"])


def entity_vs_individual_map(enriched: pd.DataFrame, sample=4000, seed=0) -> folium.Map:
    """Two coloured layers: entity-buyer sales vs individual-buyer sales.

    The story to look for: geographic CONCENTRATION — entity buying clustered on
    the South/West sides vs. individual buying on the North side.
    """
    d = _valid_coords(enriched)
    ent = d[d["entity_buyer"]]
    ind = d[~d["entity_buyer"]]

    # sample each layer independently so neither overwhelms the map
    if sample:
        ent = ent.sample(min(sample, len(ent)), random_state=seed)
        ind = ind.sample(min(sample, len(ind)), random_state=seed)

    m = folium.Map(location=CHICAGO, zoom_start=11, tiles="cartodbpositron")

    fg_ind = folium.FeatureGroup(name=f"Individual buyer (n={len(ind):,})")
    for _, r in ind.iterrows():
        folium.CircleMarker([r.loc_latitude, r.loc_longitude], radius=2,
                            color="#1f77b4", fill=True, fill_opacity=0.4, weight=0).add_to(fg_ind)
    fg_ind.add_to(m)

    fg_ent = folium.FeatureGroup(name=f"Entity buyer (n={len(ent):,})")
    for _, r in ent.iterrows():
        folium.CircleMarker([r.loc_latitude, r.loc_longitude], radius=2,
                            color="#d62728", fill=True, fill_opacity=0.5, weight=0).add_to(fg_ent)
    fg_ent.add_to(m)

    folium.LayerControl().add_to(m)
    return m


def entity_heatmap(enriched: pd.DataFrame, entity_only=True) -> folium.Map:
    """Density heatmap — better than dots for showing WHERE entity buying concentrates."""
    d = _valid_coords(enriched)
    if entity_only:
        d = d[d["entity_buyer"]]
    m = folium.Map(location=CHICAGO, zoom_start=11, tiles="cartodbpositron")
    HeatMap(d[["loc_latitude", "loc_longitude"]].values.tolist(),
            radius=8, blur=6).add_to(m)
    return m


def flip_map(enriched: pd.DataFrame) -> folium.Map:
    """Highlight the flips: short-term-owner sales that are ALSO entity-involved —
    the investor-flip population. These are the highest-suspicion transactions."""
    d = _valid_coords(enriched)
    flips = d[d["is_stale"] & d["is_entity"]]
    m = folium.Map(location=CHICAGO, zoom_start=11, tiles="cartodbpositron")
    for _, r in flips.iterrows():
        folium.CircleMarker(
            [r.loc_latitude, r.loc_longitude], radius=4,
            color="#ff7f0e", fill=True, fill_opacity=0.7, weight=1,
            popup=f"${r[K.TARGET_RAW]:,.0f} · {r.get(K.REPORT_GEO, '')} · {r.meta_year}",
        ).add_to(m)
    folium.LayerControl().add_to(m)
    return m