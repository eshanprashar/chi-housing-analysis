"""The fixed domain model for the Chicago housing analysis.

constants.py holds everything that describes the PROBLEM and is stable across
machines/environments: the exact column identifiers, the analytic scope, the
sale-validity policy, the target, feature blocks, leakage exclusions, categorical
encodings, and the wrangling fixes (dtype corrections, redundant-column drops).
If it's a fact or a decision about the DATA or the MODEL, it lives here.

config.py holds only runtime/infrastructure: filesystem paths (and, later, env /
compute / tracking settings) — the things that change per machine or deployment.

Nothing here imports project code — constants is the base of the dependency graph.
Column names were verified against the parquet schema (Step 0a).
"""

from __future__ import annotations

from dataclasses import dataclass

# ===========================================================================
# Column identifiers — the exact strings as they appear in the parquet schema
# ===========================================================================
# scope / filtering
CITY_COL = "loc_property_city"
MODELING_GROUP_COL = "meta_modeling_group"
SALE_YEAR = "meta_year"                        # sale-year column (also the FE key)
SALE_DATE_COLS = ["meta_sale_date", "meta_year"]

# card <-> PIN cleanliness flags
MULTICARD_COL = "ind_pin_is_multicard"
PRORATED_COL = "ind_pin_is_prorated"

# sale-validity reason columns (three parallel flag columns per sale)
SV_REASON_COLS = ["sv_outlier_reason1", "sv_outlier_reason2", "sv_outlier_reason3"]

# target (raw) + buyer/seller names
TARGET_RAW = "meta_sale_price"
SELLER_NAME = "meta_sale_seller_name"
BUYER_NAME = "meta_sale_buyer_name"

# school-rating columns
SCHOOL_RATING = "prox_avg_school_rating_in_half_mile"            # raw rating (filled)
SCHOOL_RATED_COUNT = "prox_num_school_with_rating_in_half_mile"  # derivation input
NO_RATED_SCHOOL_FLAG = "no_rated_school_nearby"                  # engineered flag

# garage (char_gar1_size is recoded to labels; the label "0 cars" == no garage)
GAR1_SIZE = "char_gar1_size"
GAR1_EXISTS_FLAG = "char_gar1_exists"          # engineered flag (features/derive.py)
GAR1_NO_GARAGE_LABEL = "0 cars"                # recoded char_gar1_size value meaning "no garage"

# keys / geography (not predictors)
KEYS = ["meta_pin", "meta_nbhd_code", "loc_census_tract_geoid"]
GEO_COORDS = ["loc_latitude", "loc_longitude", "loc_x_3435", "loc_y_3435"]
REPORT_GEO = "loc_chicago_community_area_name"   # reader-facing geography
ADDRESS = "loc_property_address"

# ---------------------------------------------------------------------------
# Reader-facing "sides" — the 1830 Chicago-River three-part division
# (chicagostudies.uchicago.edu/sides): North, West, South. Reconciled to the 77
# community areas via the city's OFFICIAL lists — the West Side's nine areas and
# the South Side's forty-two (which explicitly includes the "Far Southeast Side",
# East Side among them). Central areas the official lists leave unstated are
# placed by geography: Near West is already official West; Near North -> North;
# Near South -> South.
#
# EAST SIDE FOOTNOTE: the community area literally named "East Side" is east of
# the CALUMET river (not the Chicago), and the city files it under the South Side
# (Far Southeast). It is NOT a fourth cardinal "side" — we fold it into South and
# footnote the quirk wherever the geography is the point.
REGION_COL = "region"
REGION_ORDER = ["North", "West", "South"]
EAST_SIDE_AREA = "EAST SIDE"   # colloquially its own 'side'; officially South (Far SE)

REGION_MEMBERS = {
    "North": [   # North Side + Northwest Side + Near North (24)
        "ROGERS PARK", "EDISON PARK", "WEST RIDGE", "FOREST GLEN", "NORTH PARK",
        "EDGEWATER", "NORWOOD PARK", "JEFFERSON PARK", "LINCOLN SQUARE", "UPTOWN",
        "ALBANY PARK", "OHARE", "PORTAGE PARK", "IRVING PARK", "NORTH CENTER",
        "DUNNING", "LAKE VIEW", "AVONDALE", "MONTCLARE", "BELMONT CRAGIN",
        "HERMOSA", "LINCOLN PARK", "LOGAN SQUARE", "NEAR NORTH SIDE",
    ],
    "West": [    # the city's official West Side (9)
        "WEST TOWN", "NEAR WEST SIDE", "LOWER WEST SIDE", "HUMBOLDT PARK",
        "EAST GARFIELD PARK", "WEST GARFIELD PARK", "NORTH LAWNDALE",
        "SOUTH LAWNDALE", "AUSTIN",
    ],
    "South": [   # South + Southwest + Far Southwest + Far Southeast + Near South (43)
        "ARMOUR SQUARE", "BRIDGEPORT", "DOUGLAS", "ENGLEWOOD", "FULLER PARK",
        "GRAND BOULEVARD", "GREATER GRAND CROSSING", "HYDE PARK", "KENWOOD",
        "OAKLAND", "SOUTH SHORE", "WASHINGTON PARK", "WOODLAWN",
        "ARCHER HEIGHTS", "BRIGHTON PARK", "CHICAGO LAWN", "CLEARING", "GAGE PARK",
        "GARFIELD RIDGE", "MCKINLEY PARK", "NEW CITY", "WEST ELSDON",
        "WEST ENGLEWOOD", "WEST LAWN",
        "ASHBURN", "AUBURN GRESHAM", "BEVERLY", "MORGAN PARK", "MOUNT GREENWOOD",
        "WASHINGTON HEIGHTS",
        "AVALON PARK", "BURNSIDE", "CALUMET HEIGHTS", "CHATHAM", "EAST SIDE",
        "HEGEWISCH", "PULLMAN", "RIVERDALE", "ROSELAND", "SOUTH CHICAGO",
        "SOUTH DEERING", "WEST PULLMAN",
        "NEAR SOUTH SIDE",
    ],
}
# community-area name -> region (flattened for a fast .map())
REGION_MAP = {area: region for region, areas in REGION_MEMBERS.items() for area in areas}

# ---------------------------------------------------------------------------
# CONDO variant of the sides. Condos (unlike single-family) are a DOWNTOWN
# market, so the four official "Central" community areas — the Loop plus Near
# North / South / West — form their own region instead of folding into N/S/W.
# This DELIBERATELY diverges from the SF map (where Near-* went to N/S/W and the
# Loop had no sales): here Central is the high-rise core. All 77 areas covered.
CENTRAL_AREAS = ["LOOP", "NEAR NORTH SIDE", "NEAR SOUTH SIDE", "NEAR WEST SIDE"]
CONDO_REGION_MEMBERS = {
    "Central": CENTRAL_AREAS,
    "North": [a for a in REGION_MEMBERS["North"] if a not in CENTRAL_AREAS],
    "West":  [a for a in REGION_MEMBERS["West"] if a not in CENTRAL_AREAS],
    "South": [a for a in REGION_MEMBERS["South"] if a not in CENTRAL_AREAS],
}

# ===========================================================================
# Analytic scope — which rows constitute the sample (carved BEFORE modeling)
# ===========================================================================
# The public parquet is COUNTYWIDE, all property types, ~9 years. We restrict to
# a clean Chicago / single-family / 2022-25 cross-section. These filters also
# explain most of the missingness (community area / ward only populate in-city).
CITY = "CHICAGO"                    # value in CITY_COL
MODELING_GROUP = "SF"              # value in MODELING_GROUP_COL (single-family)
YEARS = ["2022", "2023", "2024", "2025"]  # values in SALE_YEAR — excludes COVID (2020-21) + pre-2022

# card <-> PIN cleanliness (drop multi-card / prorated so the unit is clean)
SINGLE_CARD_ONLY = True

# ===========================================================================
# Property-type registry — one config object per market the 01_02 sales analysis
# runs on. Bundles everything that differs between single-family, multi-family and
# condo: the raw file, the modeling-group value, scope rules, the column rename,
# and the region scheme. The generic wrangling/maps functions read a PropertyType
# instead of hard-coding SF, so every 01_02 notebook is identical but for `P=K.*`.
#
# Notes captured in the flags:
#   single_card_scope — SF & MF drop multi-card + prorated; condos have no
#     multi-card concept and are ALWAYS prorated, so they skip both filters.
#   price_only — condo unit sqft/beds/baths are ~70% null, so condo analysis is
#     price-based (no $/sqft); SF & MF have full characteristics.
#   region scheme — SF & MF use the 3-side N/W/S map (they're neighborhood
#     residential; the Loop is ~empty for them); condos add a downtown Central.
# (parquet_key resolves to a file in config.py — constants stays path-free.)
@dataclass(frozen=True)
class PropertyType:
    key: str                 # 'sf' | 'mf' | 'condo' — also the notebook subfolder
    label: str               # human label ('single-family', ...)
    parquet_key: str         # load_training_data source: 'sf' or 'condo'
    city: str                # value in CITY_COL
    modeling_group: str      # value in MODELING_GROUP_COL
    years: tuple             # values in SALE_YEAR
    single_card_scope: bool  # drop multi-card + prorated rows?
    price_only: bool         # skip $/sqft (sparse characteristics)?
    column_rename: dict       # raw -> canonical char names ({} when already canonical)
    region_members: dict      # region -> [community areas]
    region_order: tuple

    @property
    def region_map(self) -> dict:
        """community-area name -> region (flattened for a fast .map())."""
        return {a: r for r, areas in self.region_members.items() for a in areas}


SF = PropertyType(
    key="sf", label="single-family", parquet_key="sf", city=CITY,
    modeling_group="SF", years=tuple(YEARS), single_card_scope=True,
    price_only=False, column_rename={},
    region_members=REGION_MEMBERS, region_order=tuple(REGION_ORDER))

MF = PropertyType(   # same parquet as SF, just a different modeling group
    key="mf", label="multi-family", parquet_key="sf", city=CITY,
    modeling_group="MF", years=tuple(YEARS), single_card_scope=True,
    price_only=False, column_rename={},
    region_members=REGION_MEMBERS, region_order=tuple(REGION_ORDER))

CONDO = PropertyType(
    key="condo", label="condo", parquet_key="condo", city=CITY,
    modeling_group="CONDO", years=tuple(YEARS), single_card_scope=False,
    price_only=True,
    column_rename={"char_unit_sf": "char_bldg_sf",   # the UNIT's living area
                   "char_bedrooms": "char_beds",
                   "char_full_baths": "char_fbath"},
    region_members=CONDO_REGION_MEMBERS, region_order=("Central", "North", "West", "South"))

PROPERTY_TYPES = {p.key: p for p in (SF, MF, CONDO)}

# ===========================================================================
# Sale validity: DROP non-arm's-length, RETAIN price-extreme
# ===========================================================================
# sv_is_outlier bundles two different things: (1) non-market transfers (family,
# non-person, flips) which are a different data-generating process -> exclude;
# (2) genuine but price-extreme sales -> KEEP for inference and let residual
# diagnostics handle influence. We therefore key off the REASON columns, not the
# blunt flag. NON_ARMS_LENGTH_REASONS is PROVISIONAL — calibrate against the
# value_counts printed in notebooks/01_02_data_exploration.ipynb.
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

# CCAO's short-term-owner threshold, copied VERBATIM (SHORT_TERM_OWNER_THRESHOLD).
# WHY WE REWROTE THIS: the parquet's `sv` reason columns only expose the *result*
# ("Short-term owner"), not the logic. We recompute it ourselves — days between
# consecutive sales of the SAME parcel, flagged if < 365 — because (a) it matches
# the County's exact rule, (b) it makes the flip analysis rest on a derivable fact
# rather than trusting a pre-baked flag, and (c) it reuses the same-parcel
# machinery we already need for the price-gap infographic. A sale is short-term if
# the parcel changed hands again within a year.
SHORT_TERM_OWNER_DAYS = 365

# ===========================================================================
# Target
# ===========================================================================
# TARGET_RAW (the raw price column) is above; TARGET is the modeled transform.
TARGET = "log_sale_price"   # we model log(price)

# ===========================================================================
# Feature blocks (final pruned set)
# ===========================================================================
BLOCK_A_STRUCTURE = [
    "char_air",         # central air (well-balanced)
    "char_attic_fnsh",  # attic finish
    "char_attic_type",  # attic type
    "char_beds",        # bedrooms
    "char_bldg_sf",     # building size — the core feature / simple-regression starter
    "char_bsmt",        # basement
    "char_bsmt_fin",    # basement finish
    "char_fbath",       # full baths
    "char_gar1_att",    # Indicator for garage attached
    "char_gar1_size",   # garage
    "char_heat",        # heat type
    "char_land_sf",     # lot size — distinct from building
    "char_porch",       # porch
    "char_roof_cnst",   # roof material / construction
    "char_yrblt",       # age — non-linearity candidate
    #"char_bldg_is_mixed_use"
]

BLOCK_B_LOCATION = [
    "dist_to_loop_ft",                       # ENGINEERED (features/derive.py) — CBD/monocentric
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
    "acs5_median_age_total",
    "acs5_median_household_renter_occupied_gross_rent",
    "acs5_median_income_household_past_year",   # income — NOTE top-coded at 250,001
    "acs5_percent_education_bachelor",          # kept WITH income on purpose -> VIF demo
    "acs5_percent_household_owner_occupied",    # tenure — distinct construct
    "acs5_percent_income_below_poverty_level"
]

BLOCKS = {
    "A_structure": BLOCK_A_STRUCTURE,
    "B_location": BLOCK_B_LOCATION,
    "demographics": DEMOGRAPHICS,
}

# --- school-rating handling (EDA: rating is null IFF zero RATED schools nearby) ---
# columns PRODUCED by features/ (engineered — not read from the parquet)
ENGINEERED = ["dist_to_loop_ft", NO_RATED_SCHOOL_FLAG]
# raw columns needed ONLY to derive engineered features (read, but not predictors)
DERIVE_INPUTS = [SCHOOL_RATED_COUNT]

# categorical predictors (numerically encoded in the raw data — treat as categorical)
CATEGORICAL = ["char_gar1_size", "char_air", "char_porch", "char_bsmt"]

# ===========================================================================
# Leakage: proxies OF the outcome; never on the RHS of a market hedonic
# ===========================================================================
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

# ===========================================================================
# Wrangling maps — POPULATED FROM PROFILING (clean.profile_columns)
# ===========================================================================
# The workflow (see notebooks/01_01_data_prep.ipynb):
#   1. profile_columns(df, cols)                        -> read the dtype/missingness audit
#   2. note float cols that are really integers here    -> CHANGE_DTYPE_FROM_FLOAT_TO_INT
#      note redundant cols here                          -> DROP_REDUNDANT_COLS_WRANGLING
#   3. profile_columns(df, cols, convert_dtypes=True, drop_columns=True) -> re-audit post-fix
#
# These are data-EVIDENCED fixes (this column is an int stored as float; this
# column is a duplicate), justified by the profile output — no infrastructure
# concern, hence here and not in config.

# Float columns that are integer-valued in truth (counts, years, room tallies).
# clean.convert_float_to_int() coerces each to pandas nullable "Int64" (keeps NaN).
# NOTE: confirm/trim against the profile output before trusting.
CHANGE_DTYPE_FROM_FLOAT_TO_INT: list[str] = [
    "acs5_median_household_renter_occupied_gross_rent",
    "acs5_median_income_household_past_year",
    "char_beds",     # bedroom count
    "char_bldg_sf",
    "char_fbath",    # full-bath count
    "char_land_sf",
    "char_yrblt",    # year built
    "loc_access_cmap_walk_total_score",	
    ""
]

# Columns to drop during wrangling because they are redundant / superseded.
# clean.drop_redundant_columns() removes any of these that are present.
# NOTE: start empty; add columns as profiling reveals duplicates. Examples of the
# kind of thing that lands here (uncomment/edit after confirming):
DROP_REDUNDANT_COLS_WRANGLING: list[str] = [
    "char_attic_fnsh", #33K values are None
    "char_porch", #~32K values are None
    "char_attic_type", #~24K full; ~11K partial
    "char_bsmt_fin", #~28K unfinished; ~13K formal rec room
    "char_roof_cnst", #~90% values are Shingle + Asphalt 
    # "loc_x_3435", "loc_y_3435",  # projected coords duplicate lat/long for our use
    # SCHOOL_RATED_COUNT,          # only needed to derive the flag; drop after derive
]

# ===========================================================================
# Sanity bounds for outlier / data-error checks (clean.sanity_checks)
# ===========================================================================
# Plausible (lo, hi) ranges for Chicago single-family; None = no bound that side.
# Rows outside a bound are DATA-ERROR candidates — REPORTED, not dropped — and are
# distinct from genuine price-extreme tails, which we keep and diagnose later.
SANITY_BOUNDS: dict[str, tuple] = {
    "char_bldg_sf":    (50, 20_000),   # building sqft
    "char_land_sf":    (50, 30_000),   # lot sqft
    "char_beds":       (1, 12),        # 0 beds suspect; >12 implausible for SF
    "char_fbath":      (1, 10),
    "char_yrblt":      (1850, 2025),   # plausible construction years
    "meta_sale_price": (PRICE_FLOOR, None),  # floor already enforced upstream
}

# Price-ratio sanity bands — clean.add_price_ratios flags values outside these.
PRICE_PER_BLDG_SQFT_BOUNDS = (20, 3_000)         # $ per building sqft
PRICE_PER_LAND_SQFT_BOUNDS = (20, 3_000)
PRICE_PER_BED_BOUNDS = (5_000, 2_000_000)   # $ per bedroom

# ===========================================================================
# CCAO legal-entity keyword regex — a mechanical lookup lifted from CCAO's
# model-sales-val repo. Consumed by clean._is_legal_entity to flag non-person
# buyers/sellers. Not a decision: it's the County's published keyword list.
# ===========================================================================
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