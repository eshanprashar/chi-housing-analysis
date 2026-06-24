"""Residual diagnostics: VIF, heteroskedasticity, residual plots, Moran's I."""

import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor


def vif_table(df: pd.DataFrame, predictors: list[str]) -> pd.DataFrame:
    """VIF per predictor — flags multicollinearity (the parsimony check)."""
    X = sm.add_constant(df[predictors]).dropna()
    rows = [
        (col, variance_inflation_factor(X.values, i))
        for i, col in enumerate(X.columns)
        if col != "const"
    ]
    return (
        pd.DataFrame(rows, columns=["feature", "vif"])
        .sort_values("vif", ascending=False)
        .reset_index(drop=True)
    )


def morans_i_on_residuals(resid, coords):
    """Spatial autocorrelation of residuals (esda.Moran). TODO: Step 5."""
    ...
