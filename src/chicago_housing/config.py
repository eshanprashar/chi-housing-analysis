"""Runtime / infrastructure configuration.

ONLY things that change per machine or environment live here: filesystem paths
today, and (as the project grows) compute/env/tracking settings — e.g. ENV,
NUM_WORKERS, USE_GPU, an MLflow URI, an S3 bucket.

The fixed DOMAIN model — column names, analytic scope, sale-validity policy,
target, feature blocks, leakage exclusions, wrangling fixes — lives in
constants.py. If a value is a fact or decision about the DATA or the MODEL,
it belongs there, not here.
"""

from pathlib import Path

# --- paths ---
ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

SF_TRAINING_PARQUET = DATA_RAW / "sf_training_data.parquet"
CONDO_TRAINING_PARQUET = DATA_RAW / "condo_training_data.parquet"
COMMUNITY_AREAS_GEOJSON = DATA_RAW / "chicago_community_areas_boundaries.geojson"  # city portal (77 areas)