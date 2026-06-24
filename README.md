# chicago-housing

Hedonic **inference** on Chicago home sale prices — practicing ISL Chapter 3
(regression, F-tests, VIF, heteroskedasticity, residual analysis) on the Cook
County Assessor `training_data.parquet`, written up as a Substack series.

Guiding question: *what are you really paying for when you buy a home in
Chicago — the house, or where it sits?* See `docs/project-brief.md`.

## Setup

```bash
poetry install                 # core: data + inference + geospatial
poetry install --with ml       # add tree models + SHAP (prediction post only)

# register the kernel so notebooks can import the package
poetry run python -m ipykernel install --user --name chicago-housing
poetry run jupyter lab
```

Then drop the CCAO `training_data.parquet` into `data/raw/`.

## Layout

| Path | Purpose |
|---|---|
| `src/chicago_housing/` | importable package — loading, feature blocks, models, diagnostics |
| `notebooks/` | the narrative layer (one notebook per post) |
| `data/` | `raw -> interim -> processed` (gitignored) |
| `outputs/` | figures + tables for Substack (gitignored) |
| `docs/project-brief.md` | the living plan |
| `tests/` | guardrails (e.g. feature blocks don't overlap) |
