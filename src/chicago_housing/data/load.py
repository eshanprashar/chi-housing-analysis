"""Load the raw CCAO parquet."""

import pandas as pd

from chicago_housing.config import TRAINING_PARQUET


def load_training_data(columns: list[str] | None = None) -> pd.DataFrame:
    """Read training_data.parquet from data/raw/.

    Pass `columns` to read only what you need (the file is ~100 cols wide).
    """
    return pd.read_parquet(TRAINING_PARQUET, columns=columns)
