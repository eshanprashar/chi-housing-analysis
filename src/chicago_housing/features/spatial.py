"""Spatial features: distance-to-Loop, centroids, neighbor weights.

distance-to-Loop is our differentiator (CCAO has no explicit CBD distance).
Loop reference ~ (41.8786, -87.6359).
"""

LOOP_LAT, LOOP_LON = 41.8786, -87.6359


def add_distance_to_loop(df, lat="loc_latitude", lon="loc_longitude"):
    """Add `dist_to_loop_ft` (Haversine -> feet). TODO: implement in Step 0."""
    ...
