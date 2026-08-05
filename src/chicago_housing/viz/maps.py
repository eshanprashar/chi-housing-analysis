"""Folium maps for the sales EDA. Take an enriched frame (df + flags + lat/lon),
render to an interactive map. Sampled for performance — 30K points chokes folium.
"""

from __future__ import annotations
import folium
from folium.plugins import FastMarkerCluster, HeatMap
import pandas as pd
from chicago_housing import config as C

CHICAGO = [41.8781, -87.6298]


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
            popup=f"${r[C.TARGET_RAW]:,.0f} · {r.get(C.REPORT_GEO, '')} · {r.meta_year}",
        ).add_to(m)
    folium.LayerControl().add_to(m)
    return m