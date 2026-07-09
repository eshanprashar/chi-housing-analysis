"""OLS / WLS fitting and the grouped (partial-F) block comparison."""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf


def fit_ols(df: pd.DataFrame, target: str, predictors: list[str]):
    """Fit OLS with an intercept; returns a fitted statsmodels result."""
    X = sm.add_constant(df[predictors])
    y = df[target]
    return sm.OLS(y, X, missing="drop").fit()

def tidy_coefficients(results, alpha: float=0.05) -> pd.DataFrame:
    """One tidy row per term: coef, std, err, t, p and CI bounds
    Reused by every later step (block models, comparisons and post tables)
    """
    ci = results.conf_int(alpha=alpha)
    out = pd.DataFrame(
        {
            "coef": results.params,
            "std_err": results.bse,
            "t": results.tvalues,
            "p_value": results.pvalues,
            "ci_low": ci[0],
            "ci_high": ci[1],
        }
    )
    out.index.name = "term"
    return out.reset_index()

def fit_summary_stats(results) -> pd.Series:
    """Model-level fit numbers: N, R2, adj-R2, RSE(log units), F and its p.
    """
    return pd.Series({
        "n_obs": int(results.nobs),
        "r_squared": results.rsquared,
        "adj_r_squared": results.rsquared_adj,
        "rse": float(np.sqrt(results.scale)), # residual std error, in log units
        "f_stat": results.fvalue,
        "f_pvalue": results.f_pvalue,
    })

def build_formula(target: str, predictors: list[str], categorical=()) -> str:
    """Assemble a Patsy formula, wrapping categoricals in C() for dummy-encoding.

    Continuous predictors pass through as-is; anything in `categorical` becomes
    C(col) so statsmodels creates dummies against a reference level.
    """
    cat = set(categorical)
    terms = [f"C({c})" if c in cat else c for c in predictors]
    return f"{target} ~ " + " + ".join(terms)


def fit_formula(df, formula: str):
    """Fit OLS from a Patsy formula (handles categoricals, interactions via *).

    Rows with NaN in any formula term are dropped (statsmodels default).
    """

    return smf.ols(formula, data=df).fit()


def partial_f_test(restricted, full):
    """Nested-model comparison: does the added block help as a group?

    TODO (Step 3): statsmodels.stats.anova.anova_lm, or compute F from RSS.
    """
    ...
