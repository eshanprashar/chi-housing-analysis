"""OLS / WLS fitting and the grouped (partial-F) block comparison."""

import pandas as pd
import statsmodels.api as sm


def fit_ols(df: pd.DataFrame, target: str, predictors: list[str]):
    """Fit OLS with an intercept; returns a fitted statsmodels result."""
    X = sm.add_constant(df[predictors])
    y = df[target]
    return sm.OLS(y, X, missing="drop").fit()


def partial_f_test(restricted, full):
    """Nested-model comparison: does the added block help as a group?

    TODO (Step 3): statsmodels.stats.anova.anova_lm, or compute F from RSS.
    """
    ...
