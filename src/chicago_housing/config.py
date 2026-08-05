"""Project configuration: paths, scope filters, target, and block -> column mapping.

SINGLE SOURCE OF TRUTH for the analytic sample and the feature blocks. Column
names verified against the parquet schema (Step 0a). A few still carry notes.
"""

from pathlib import Path

# --- paths ---
ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

TRAINING_PARQUET = DATA_RAW / "training_data.parquet"

# --- scope filters (carve the analytic sample BEFORE any modeling) ---
# The public parquet is COUNTYWIDE, all property types, ~9 years. We restrict to
# a clean Chicago / single-family / 2022-24 cross-section. These filters also
# explain most of the missingness (community area / ward only populate in-city).
CITY = "CHICAGO"                    # loc_property_city
MODELING_GROUP = "SF"              # meta_modeling_group (single-family)
YEARS = ["2022", "2023", "2024", "2025"]  # meta_year (str) — excludes COVID (2020-21) + pre-2022

CITY_COL = "loc_property_city"
MODELING_GROUP_COL = "meta_modeling_group"
SALE_DATE_COLS = ["meta_sale_date", "meta_year"]

# card <-> PIN cleanliness (drop multi-card / prorated so the unit is clean)
SINGLE_CARD_ONLY = True
MULTICARD_COL = "ind_pin_is_multicard"
PRORATED_COL = "ind_pin_is_prorated"

# --- sale validity: DROP non-arm's-length, RETAIN price-extreme -------------
# sv_is_outlier bundles two different things: (1) non-market transfers (family,
# non-person, flips) which are a different data-generating process -> exclude;
# (2) genuine but price-extreme sales -> KEEP for inference and let residual
# diagnostics handle influence. We therefore key off the REASON columns, not the
# blunt flag. NON_ARMS_LENGTH_REASONS is PROVISIONAL — calibrate against the
# value_counts printed in notebooks/01_eda.ipynb.
SV_REASON_COLS = ["sv_outlier_reason1", "sv_outlier_reason2", "sv_outlier_reason3"]
NON_ARMS_LENGTH_REASONS = [
    "Non-person sale",
    "Family sale",
    "Transfer of ownership",
    "Flip",
    "Quitclaim",
    "Non-arm",
]
SV_ALWAYS_DROP   = {"PTAX-203 Exclusion", "Family Sale"}          # non-market by statute/relationship
SV_ENTITY        = {"Non-person sale"}                            # necessary, NOT sufficient
SV_NOMINAL_PRICE = {"Low price", "Low price per square foot",     # the price itself looks non-market
                    "Raw price threshold"}

SV_STALE = {"Short-term owner", "Home flip"}   # feature-staleness / rapid re-trade — mixed

# everything else — Statistical Anomaly, High price, High $/sqft — is a genuine
# price-extreme tail we KEEP (diagnostics handle influence). Short-term owner /
# Home flip are feature-staleness issues, also keep-and-diagnose.
PRICE_FLOOR = 10_000     # CCAO-consistent absolute backstop; below Riverdale's real market
# Source: https://github.com/ccao-data/model-sales-val/blob/main/src/model.py
ENTITY_KEYWORDS = (
    r"llc| ll$| l$|l l c|estate|training|construction|building|masonry|"
    r"apartments|plumbing|service|professional|roofing|advanced|office|"
    r"\blaw\b|\bloan\b|legal|production|woodwork|concepts|corp|company|"
    r" united|\binc\b|county|entertainment|community|heating|cooling"
    r"|partners|equity|indsutries|series|revitalization|collection|"
    r"agency|renovation|consulting|flippers|estates|\bthe \b|dept|"
    r"funding|opportunity|improvements|servicing|equities|\bsale\b|"
    r"judicial| in$|bank|\btrust\b|holding|investment|housing"
    r"|properties|limited|realty|development|capital|management"
    r"|developers|construction|rentals|group|investments|invest|"
    r"residences|enterprise|enterprises|ventures|remodeling|"
    r"specialists|homes|business|venture|restoration|renovations"
    r"|maintenance|ltd|real estate|builders|buyers|property|financial"
    r"|associates|consultants|international|acquisitions|credit|design"
    r"|homeownership|solutions|\bhome\b|diversified|assets|family|\bland\b"
    r"|revocable|services|rehabbing|\bliving\b|county of cook|fannie mae"
    r"|veteran|mortgage|savings|lp$|federal natl|hospital|southport|mtg"
    r"|propert|rehab|neighborhood|advantage|chicago|cook c|\bbk\b|\bhud\b"
    r"|department|united states|\busa\b|hsbc|midwest|residential|american"
    r"|tcf|advantage|real e|advantage|fifth third|baptist church"
    r"|apostolic church|lutheran church|catholic church|\bfed\b|nationstar"
    r"|advantage|commercial|health|condominium|nationa|association|homeowner"
    r"|christ church|christian church|baptist church|community church"
    r"|church of c|\bdelaw\b|lawyer|delawar"
)
# CCAO's short-term-owner threshold, copied VERBATIM (SHORT_TERM_OWNER_THRESHOLD).
# WHY WE REWROTE THIS: the parquet's `sv` reason columns only expose the *result*
# ("Short-term owner"), not the logic. We recompute it ourselves — days between
# consecutive sales of the SAME parcel, flagged if < 365 — because (a) it matches
# the County's exact rule, (b) it makes the flip analysis rest on a derivable fact
# rather than trusting a pre-baked flag, and (c) it reuses the same-parcel
# machinery we already need for the price-gap infographic. A sale is short-term if
# the parcel changed hands again within a year.
SHORT_TERM_OWNER_DAYS = 365

# --- target ---
TARGET_RAW = "meta_sale_price"
TARGET = "log_sale_price"   # we model log(price)

# sale-year fixed effect — absorbs 2022-2025 rate-driven price-LEVEL shifts while
SALE_YEAR = "meta_year"

# --- feature blocks (final pruned set) ---
BLOCK_A_STRUCTURE = [
    "char_bldg_sf",     # building size — the core feature / simple-regression starter
    "char_land_sf",     # lot size — distinct from building
    "char_yrblt",       # age — non-linearity candidate
    "char_beds",        # bedrooms — the "what's a bedroom worth" headline
    "char_fbath",       # full baths
    "char_gar1_size",   # garage
    "char_air",         # central air (well-balanced)
    "char_porch",       # porch
    "char_bsmt",        # basement
]

BLOCK_B_LOCATION = [
    "dist_to_loop_ft",                       # ENGINEERED (features/spatial.py) — CBD/monocentric
    "prox_lake_michigan_dist_ft",            # lakefront premium
    "prox_nearest_cta_stop_dist_ft",         # transit access
    "prox_nearest_park_dist_ft",             # parks
    "prox_nearest_grocery_store_dist_ft",    # food access
    "prox_avg_school_rating_in_half_mile",   # school quality — filled; null IFF no rated school 
    "loc_access_cmap_walk_total_score",      # walkability
    "prox_nearest_major_road_dist_ft",       # dis-amenity (traffic/noise)
    "prox_num_foreclosure_per_1000_pin_past_5_years",  # distress — assoc, not causal
    "no_rated_school_nearby",                # ENGINEERED (features/derive.py) — absorbs the null rows
]

DEMOGRAPHICS = [
    "acs5_median_income_household_past_year",   # income — NOTE top-coded at 250,001
    "acs5_percent_education_bachelor",          # kept WITH income on purpose -> VIF demo
    "acs5_percent_household_owner_occupied",    # tenure — distinct construct
]

BLOCKS = {
    "A_structure": BLOCK_A_STRUCTURE,
    "B_location": BLOCK_B_LOCATION,
    "demographics": DEMOGRAPHICS,
}

# categorical predictors (numerically encoded in raw data — treat as categorical)
CATEGORICAL = ["char_gar1_size", "char_air", "char_porch", "char_bsmt"]

# --- school-rating handling (EDA: rating is null IFF zero RATED schools nearby) ---
SCHOOL_RATING = "prox_avg_school_rating_in_half_mile"            # raw (in Block B; filled)
SCHOOL_RATED_COUNT = "prox_num_school_with_rating_in_half_mile"  # derivation input (not a predictor)
NO_RATED_SCHOOL_FLAG = "no_rated_school_nearby"                  # engineered flag (in Block B)

# columns PRODUCED by features/ (engineered — not read from the parquet)
ENGINEERED = ["dist_to_loop_ft", NO_RATED_SCHOOL_FLAG]
# raw columns needed ONLY to derive engineered features (read, but not predictors)
DERIVE_INPUTS = [SCHOOL_RATED_COUNT]

# buyer/seller names — needed by clean.drop_non_market (holding-vehicle name rule)
SELLER_NAME = "meta_sale_seller_name"
BUYER_NAME = "meta_sale_buyer_name"

# --- leakage: proxies OF the outcome; never on the RHS of a market hedonic ---
LEAKAGE_EXCLUDE = [
    # CCAO's own assessment outputs (current + prior years)
    "meta_board_bldg", "meta_board_land", "meta_board_tot",
    "meta_mailed_bldg", "meta_mailed_land", "meta_mailed_tot",
    "meta_certified_bldg", "meta_certified_land", "meta_certified_tot",
    "meta_1yr_pri_board_bldg", "meta_1yr_pri_board_land", "meta_1yr_pri_board_tot",
    "meta_2yr_pri_board_bldg", "meta_2yr_pri_board_land", "meta_2yr_pri_board_tot",
    # other outcome-proxies
    "acs5_median_household_owner_occupied_value",  # Census home-value estimate
    "other_ihs_avg_year_index",                    # neighborhood home-price index
    "other_tax_bill_amount_total",                 # depends on assessed value (rate is ok)
]

# --- keys / geo (not predictors) ---
KEYS = ["meta_pin", "meta_nbhd_code", "loc_census_tract_geoid"]
GEO_COORDS = ["loc_latitude", "loc_longitude", "loc_x_3435", "loc_y_3435"]
REPORT_GEO = "loc_chicago_community_area_name"  # reader-facing geography
ADDRESS = "loc_property_address"

# convenience: every column the analytic pipeline needs to read
def analysis_columns() -> list[str]:
    cols = (
        [TARGET_RAW, CITY_COL, MODELING_GROUP_COL, MULTICARD_COL, PRORATED_COL,
         SELLER_NAME, BUYER_NAME]
        + SALE_DATE_COLS 
        + SV_REASON_COLS
        + BLOCK_A_STRUCTURE
        + [c for c in BLOCK_B_LOCATION if c not in ENGINEERED]
        + DERIVE_INPUTS
        + DEMOGRAPHICS
        + KEYS + GEO_COORDS + [REPORT_GEO]
    )
    seen, out = set(), []
    for c in cols:
        if c not in seen:
            seen.add(c); out.append(c)
    return out