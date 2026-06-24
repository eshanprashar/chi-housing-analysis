"""Project configuration: paths, target, and the block -> column mapping.

SINGLE SOURCE OF TRUTH for which columns belong to which block. Every model
imports BLOCKS from here, so "house vs location" is defined in one place.

NOTE: the lists below are PROVISIONAL. Step 0a (the data-quality audit) decides
what survives — drop heavy-missingness columns, keep one of any near-duplicate
pair (parsimony). Verify every name against the parquet schema.
"""

from pathlib import Path

# --- paths ---
ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

TRAINING_PARQUET = DATA_RAW / "training_data.parquet"

# --- target ---
TARGET_RAW = "meta_sale_price"   # VERIFY against schema in Step 0a
TARGET = "log_sale_price"        # we model log(price)

# --- feature blocks (PROVISIONAL — set by Step 0a) ---
BLOCK_A_STRUCTURE = [
    "char_bldg_sf",
    "char_beds",
    "char_fbath",
    "char_yrblt",
    "char_rooms",
    "char_land_sf",
]

BLOCK_B_LOCATION = [
    "prox_nearest_cta_stop_dist_ft",
    "prox_nearest_metra_stop_dist_ft",
    "prox_nearest_park_dist_ft",
    "prox_lake_michigan_dist_ft",
    "loc_access_cmap_walk_total_score",
    "prox_avg_school_rating_in_half_mile",
    # dist_to_loop_ft  <- our own feature, built in features/spatial.py
]

DEMOGRAPHICS = [
    "acs5_median_income_household_past_year",
    "acs5_percent_education_bachelor",
    "acs5_percent_household_owner_occupied",
]

GEO_KEYS = ["loc_latitude", "loc_longitude", "loc_census_tract_geoid"]

BLOCKS = {
    "A_structure": BLOCK_A_STRUCTURE,
    "B_location": BLOCK_B_LOCATION,
    "demographics": DEMOGRAPHICS,
}
