"""Load the raw CCAO parquet."""

from typing import Literal

import pandas as pd
from chicago_housing.config import CONDO_TRAINING_PARQUET, SF_TRAINING_PARQUET

_TRAINING_PARQUETS = {
    "sf": SF_TRAINING_PARQUET,
    "condo": CONDO_TRAINING_PARQUET,
}

def load_training_data(
    property_type: Literal["sf", "condo"],
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Read the training parquet for `property_type` from data/raw/.

    Pass `property_type="sf"` for single-family or `"condo"` for condos.
    Pass `columns` to read only what you need (the file is ~100 cols wide).
    """
    try:
        parquet = _TRAINING_PARQUETS[property_type]
    except KeyError:
        raise ValueError(
            f"property_type must be 'sf' or 'condo', got {property_type!r}") from None
    return pd.read_parquet(parquet, columns=columns)