# context.md

*Living notes — the nuances and judgment calls that matter but don't fit in code comments. Append as the project develops. Each section records "what we know and why it changes a decision," not just facts.*

---

## 1. Data

### Where provenance is documented (canonical references)

When you need the authoritative source or definition for any single column, check these in order:

- **Per-column descriptions:** `docs/data-dict.csv` in [`ccao-data/model-res-avm`](https://github.com/ccao-data/model-res-avm).
- **Lineage / SQL definitions / column origins:** the [`ccao-data/data-architecture`](https://github.com/ccao-data/data-architecture) and [`ccao-data/documentation`](https://github.com/ccao-data/documentation) repos (ETL/ELT, lineage graphs, SQL defs), plus the Athena data-catalog views that feed the training and assessment datasets.
- **Name/value crosswalk:** the [`ccao-data/ccao`](https://github.com/ccao-data/ccao) package — `vars_dict` powers the human-readable rename (`vars_rename()`) and recode (`vars_recode()`) of numerically-encoded fields.
- **Raw sales (independent of the model):** [Cook County data portal — Assessor Parcel Sales](https://datacatalog.cookcountyil.gov/Property-Taxation/Assessor-Parcel-Sales/wvhk-k5uv) ([Data.gov mirror](https://catalog.data.gov/dataset/assessor-parcel-sales)). Sales 1999–present; **note** that as of Oct 2023 the portal file is no longer pre-filtered by deed type / price / recency, so non-arm's-length transfers are included unless re-filtered.

### The key insight: not all prefixes are "sources"

Of the CCAO-internal prefixes, only some are genuine data *sources*; the rest are **derived** by the office from those sources. Provenance type *is* the trustworthiness signal.

| Prefix | Provenance type | Trust | Use in our model |
|---|---|---|---|
| `char_` | First-party administrative (system of record) | High for recorded attrs; blind to interior | Block A core — structural fields |
| `meta_` (keys) | System of record | High (identifiers) | Joins / grouping |
| `meta_` (sale) | Recorded deed transfers (county recorder) | Authoritative but raw → needs `sv_` filter | Target (`meta_sale_price`) |
| `meta_` (assessment values) | CCAO assessment *outputs* | N/A — downstream of value | **Exclude (leakage)** |
| `ind_` | CCAO-derived flags | = underlying data + derivation logic | Cleaning levers / controls only |
| `ccao_` | First-party administrative/derived | Reliable for administrative status | Optional controls |
| `acs5_` | Census (external) | Survey-based; MOE; tract-smoothed | Block B / demographics |
| `prox_`, `loc_` | CCAO spatial joins/computations | Softer — depends on join quality | Block B (scrutinize) |
| `other_` | Third-party indices (distress, IHS, etc.) | Vendor black-box | Block B (scrutinize) |

### Per-prefix nuances

**`char_` — first-party administrative (system of record).** Straight from the Assessor's property-characteristics database, extracted from the CCAO system-of-record into their warehouse. Highest provenance authority — the County's official record. **Catch:** the office can't enter buildings to observe characteristics, so `char_` is authoritative for *exterior/recorded* attributes (sqft, year built, beds, baths) but blind to interior condition and quality, and is updated infrequently (often only on permit or sale → can be stale). *Trust the structural fields; treat quality/condition fields as known-incomplete.* (This is the "what the County can't see" material.)

**`meta_` — mixed; split it into three.**
- *Keys* (`meta_pin`, `meta_class`, `meta_nbhd_code`, township) — system of record, fully trustworthy as identifiers.
- *The sale* (`meta_sale_price`, `meta_sale_date`, `meta_sale_document_num`) — recorded deed transfers from the county recorder. Authoritative as transactions, but raw — which is why the `sv_` flags exist to mark non-arm's-length sales.
- *Assessment values* (`meta_*_board/mailed/certified`, `meta_*_pri_board_*`) — the office's own assessment outputs, **not** market data. For a market hedonic these are **leakage** — exclude as predictors. (They'd be the *target* for an assessment-regressivity analysis.)

**`ind_` — CCAO-derived flags, not a source.** `ind_pin_is_multicard`, `ind_bldg_gte_95_percentile`, etc. are booleans computed off the system-of-record data. Trustworthiness = underlying data + CCAO's derivation logic. Fine as cleaning levers or controls; not independent facts.

**`ccao_` — first-party administrative/derived.** `ccao_is_active_exe_homeowner` (homeowner exemption), `ccao_is_corner_lot` — exemption records plus derived geometry. Reliable for what they are (administrative status), CCAO-internal.

### Provenance hierarchy (for pruning)

1. **Trustworthy first-party:** `char_` structural fields + `meta_` keys/sale — with the `char_` exterior-blindness asterisk.
2. **Derived (trust = their logic):** `ind_`, `ccao_` — controls, not facts.
3. **Exclude:** `meta_` assessment values — downstream outputs, leakage for a market model.
4. **Softer / external (scrutinize at Block B):** `acs5_` (Census survey, MOE, smoothed), `prox_`/`loc_` (join-quality dependent), `other_` (vendor indices).

### Other standing data notes

- **Sale-validation:** examine `sv_is_outlier` and check which non-arm's length sales need to be dropped before modeling. More details in Section 3.
- **Scope:** this parquet is `model-res-avm` = single/multi-family (class 200) only — **condos excluded** (separate `model-condo-avm`).
- **Selection bias:** rows are *sold* properties, not the full housing stock; claims about "all homes" carry this caveat.
- **Unit:** card/PIN-level sales, not tract aggregates. Aggregate residuals/predictions up to community areas for reader-facing maps.

---

## 2. EDA

### 2.0 Column triage (201 columns)
Triage by **prefix/role** before auditing: `char_`/`acs5_`/`loc_`/`prox_` = predictor candidates; `meta_` = keys/target/leakage; `sv_` = the cleaning lever; `time_`/`ind_`/`year` = not predictors. Cuts the audit surface from 201 to ~80.

### 2.1 Audit method — missingness AND degeneracy
A column can be 0% missing and still useless. Profile three things: `pct_missing`, `pct_modal` (share in the single most common value → degeneracy), `n_unique`.
- Dropped for **no variance**: `char_cnst_qlty` (98.8% one value), `char_recent_renovation` (99.8% False) — *the "what the County can't see" material: construction quality and renovation, the very things that separate neighbours, are recorded as near-constant.*
- **"0.000 missing" ≠ zero.** `char_bldg_sf` showed 0.000 at 3 decimals but had **2 NaNs** — invisible in the audit, fatal to bare-numpy ops (poisoned a bootstrap). Rounded audit tables hide small-N nulls.

### 2.2 Categorical code meanings (via `ccao.vars_recode`)
| Column | Codes | Note |
|---|---|---|
| `char_air` | 1 = Central A/C, **2 = No Central A/C** | 61% of sample has *no* central air |
| `char_bsmt` | 1 Full, 2 Slab, 3 Partial, 4 Crawl | |
| `char_porch` | 0 None, 1 Frame enclosed, 2 Masonry enclosed | |
| `char_gar1_size` | 1=1car … 5=3car, **7 = 0 cars**, 8=4car | **out of order** → must be `C()` categorical, never ordinal |

`C()` uses the **lowest code as reference**: air ref = Central A/C (so the dummy is the *penalty for lacking* A/C); garage ref = 1-car (so `[T.7]` = "no garage vs 1-car").

**Thin cells (do not over-interpret):** garage 3.5-car n=11, 4-car n=27, 3-car n=305; porch Masonry n=344. → bin to `none/1/2/3+` in `derive.py` as a Step-4 refinement.

### 2.3 Distributions
- **Raw price: heavy right skew → log.** Log price is roughly symmetric (this is why Y is logged).
- `char_yrblt` is **bimodal** — the 1920s and 1950s building booms. The story is bimodality, not skew.
- `dist_to_loop_ft` is roughly **symmetric** — a useful counterexample: it may still want a log because its *effect* curves (see §4 transform reasoning).
- `char_bldg_sf`, `char_land_sf`, `prox_nearest_cta_stop_dist_ft`: right-skewed with long tails.

### 2.4 Outlier / residual analysis (from the Step-1 detour)
- **Residual units:** Y is log price → a residual is a **log-ratio**: `actual = e^resid × predicted`. resid −1 ≈ sold at 37% of predicted.
- **Variance is U-shaped, not a fan** — residual SD ≈0.695 (smallest homes) → 0.555 (middle) → 0.676 (largest). Heteroskedasticity need not widen monotonically.
- Extreme residuals decomposed into **two different pathologies**:
  1. **Low end = contamination** — non-market sales that slipped the filter ($22k–$40k entity transfers, concentrated in Greater Grand Crossing, Roseland, Englewood, West Pullman).
  2. **High end = misspecification** — linear-in-raw-sqft predicted **$25M–$236M** houses. A straight line has no ceiling. → the concrete case for log-log.
- **Known filter gap:** CCAO's `Low price` flags are **group-relative**, so a nominal $22k sale in an already-cheap neighbourhood doesn't trip them, and our corroboration rule then has nothing to corroborate the entity flag with. **Group-relative price flags miss non-market sales in low-value areas.** Carry forward as Step-5 influence candidates; do not hand-delete.
- **Reflex to keep:** extreme residuals are a free non-market-sale detector — residual analysis doubles as a second pass at data validity *and* a functional-form test.
---

## 3. Training sample creation

### Scope filters (applied first — they explain most missingness)
Countywide, all-types, ~9-year parquet → **Chicago / single-family / 2022–24 / single-card, non-prorated**.
- `loc_property_city == "CHICAGO"`, `meta_modeling_group == "SF"`, `meta_year ∈ {2022, 2023, 2024}`.
- **Why exclude 2020–21:** COVID shifted the price *surface itself* (space premium, home-office value, urban-condo swings), so pooling those years violates the single-coefficient-set assumption. 2022–24 is a more coefficient-stable regime and sits inside one ACS 2020–2024 5-year vintage (clean sale-vs-predictor alignment).
- **Residual level drift within 2022–24** (rates ~doubled) is absorbed by a **sale-year fixed effect** (`meta_year` as categorical), not by dropping years.

### Sale validity — the asymmetric rule (this supersedes the section-2 note)
**We do NOT drop on `sv_is_outlier` directly.** That flag bundles two different things, and we treat them oppositely:
- **Non-market transfers → drop** (a different data-generating process): statutory (`PTAX-203 Exclusion`), `Family Sale`, and *corroborated* entity/holding transfers.
    - **PTAX-203** is the Illinois Real Estate Transfer Declaration filed on every deed. It has a checkbox section for transfers that are exempt from transfer tax because they aren't ordinary sales — transfers between related entities, deeds correcting a title, transfers to/from a trust for no consideration, foreclosure/deed-in-lieu, court-ordered transfers, etc.
    - Family Sale — a transfer between related parties (parent→child, between spouses). The price is set by the relationship, not the market: often below market as a gift-in-disguise, sometimes a nominal figure
- **Price-extreme but genuine sales → keep** (`Statistical Anomaly`, `High/Low price`, `High/Low $/sqft`) and let residual diagnostics (Cook's distance, studentized residuals) handle influence. `Short-term owner` / `Home flip` are *feature-staleness* issues, not validity — also keep-and-diagnose.

**The corroboration principle (the crux):** an entity/trust buyer is *not* evidence of a non-market price on its own.
- *Low end:* `Non-person sale` **and** a nominal-price signal (`Low price` / `Low $/sqft` / `Raw price threshold`, or `< $10k` floor) → drop. Cheap entity transfers are almost always non-market (portfolio shuffles, REO, nominal-consideration deeds).
- *High end:* `Non-person sale` + only `Statistical Anomaly` → **keep**. An expensive trust/LLC purchase is usually a real buyer using a vehicle for privacy (the Astor Street pattern); "anomaly" here means *rare/expensive*, not *fake*.
- **Holding-vehicle names** (`LAND TRUST`, `TITLE` in buyer/seller) are dropped **only when price-corroborated too** — same rule, so a $15k land-trust transfer goes but an $8M one stays.

*One-line defense:* "Sold to an LLC/trust" is a question, not a verdict — entity transfers are treated as non-market only when the **price itself** corroborates it.

### Result
- 33,106 (scoped) → **30,693** sales after validity filtering (~7% removed).
- Breakdown: statutory 1,747 · entity+nominal 670 · name+nominal ~77 · ($10k floor caught 0 — CCAO's low-price flags already cover it).
- **Config:** `SV_ALWAYS_DROP`, `SV_ENTITY`, `SV_NOMINAL_PRICE`, `NONMARKET_NAME_TOKENS`, `PRICE_FLOOR`; logic in `clean.drop_non_market(use_name_rule=True)`.

### Knowingly retained (handle at diagnostics, not cleaning)
- Genuine estate/nominal transfers at *high* prices with no low-price flag (few; surface as high-leverage points).
- All price-extreme arm's-length sales (the real tail — the whole point of inference-not-prediction).

### Resolved: school rating missingness
- Mechanism verified: `prox_avg_school_rating_in_half_mile` is null **IFF** `prox_num_school_with_rating_in_half_mile == 0` (exact identity, no exceptions).
- It is **not** "no school nearby" — most null rows *have* schools, just none with a public rating (parish/private-school Chicago: Beverly, Norwood Park, Mount Greenwood, Edison Park).
- **Handling:** derive `no_rated_school_nearby` from the *rated-school count* (a positive fact), fill the raw rating with the median; the flag absorbs the difference, so the fill value is immaterial. **No rows dropped → geography preserved.**
- Caveat: the flag conflates private/parochial prevalence, charters, and new schools — association, not a clean causal object.

### Sample sizes through the pipeline
33,106 scoped → **30,693** after validity → 30,604 (Block A fit) → **30,381** (complete-case across all blocks; used for all nested F-tests).

## 4. Model details (Steps 1–3 findings)

### The headline decomposition (nested R², same complete-case rows, N=30,381)
| Model | Predictors | R² |
|---|---|---|
| A | structure only | **48.1%** |
| A+B | + location/access | **68.2%** (+20.1) |
| A+B+D | + demographics | **72.4%** (+4.2) |

- **The sentence:** "The house explains 48% of price. Where it sits explains another 24 — half again as much as the house."
- **Location does ~5× the work of demographics** (+20.1 vs +4.2). *Physical* geography prices in far more than *who the neighbours are* — the reverse of common intuition.
- Partial-F (`anova_lm`): B → F≈2,210; D → F≈1,542, both p=0. Jointly significant — but that's the big-N expectation; the **R² lift is the story**.

### Coefficient shifts = OVB correction, quantified (A → full)
| Feature | A | full | change |
|---|---|---|---|
| `char_bldg_sf` | 0.000567 | 0.000286 | **−50%** (size premium halved) |
| `char_fbath` | 0.148 | 0.064 | **−57%** |
| `char_beds` | −0.032 | +0.024 | **sign FLIP** |
| `char_land_sf` | −1.6e-5 | +4.7e-5 | **sign FLIP** |

- **Pattern:** strong "size-ish" premiums *attenuated ~half*; marginal ones *flipped sign*. Same cause — location was confounded with all four.
- **Best teaching example:** `char_beds` is negative without location, positive with it → *a coefficient means nothing without its ceteris-paribus clause.*
- Half the apparent "size premium" was really "big houses sit in nicer/closer areas."

### VIF — honest result (milder than predicted)
- Income (4.5) and education (4.1) are the **highest** VIFs — collinearity real and detected as designed — but **below the 5/10 alarm thresholds**.
- Keep as a **detection** demo; no PCA/drop needed. "Checked for the expected multicollinearity, found it, it was mild enough to leave" is the honest story.
- Why mild: Chicago has educated-lower-income (young professionals/students) and higher-income-lower-degree (trades/legacy owners) areas, so the two don't move in lockstep.

### Transform reasoning (Step 4) — "log for CURVATURE, not for skew"
- Logging a **predictor** is about whether its *effect on price is curved/multiplicative*, NOT whether its histogram is skewed (`dist_to_loop` is symmetric yet may still want a log).
- **Log candidates:** `char_bldg_sf` (primary — caused the $236M extrapolation), `char_land_sf`, the distances, income (conventional).
- **Leave linear:** `char_beds`/`char_fbath` (discrete counts), `char_yrblt` (a year; the story is bimodality).

#### Result:
Logged the curved-effect predictors (`char_bldg_sf`, `char_land_sf`, income); distances left linear.

| Metric | Linear | Log-log |
|---|---|---|
| R² | 0.724 | **0.734** |
| Max predicted price | $24.9M (absurd) | **$6.2M** (plausible) |
| Residual SD by sqft decile | 0.695 → 0.555 → 0.676 (**U**) | 0.519 → 0.366 (**flat, −30% level**) |

- **Size elasticity = 0.465** — a 1% larger house sells ~0.47% more. **Sub-1 ⇒ diminishing returns to size**, which the linear form structurally could not express. (Was 0.521 without location — same OVB attenuation.)
- **Fit improved.** A straight line was fitting a curved relationship badly; letting it bend gained ~1 point rather than costing.
- **Key intuition: misspecification masquerades as heteroskedasticity.** A linear fit to a curved truth produces systematic over/under-prediction by region, which reads as non-constant variance. Fixing the curve removed most of it — it was bias varying across x, not variance.
  - → **Assumption-map amendment:** a Tier 3 fix (functional form) partially resolved a Tier 1 symptom. Check functional form *before* reaching for robust SEs, or you paper over a wrong model shape while leaving biased coefficients.
- **Residual heteroskedasticity remains** (~0.52 vs 0.37, small vs large homes) — consistent with low-end *contamination* (the $22k entity transfers), which no transform fixes. Robust SEs handle the remainder.

---

## 5. Validation strategy

Governed by `docs/assumption-map.md` — which OLS assumption breaks which output, and whether it shows a symptom.

**Status:**
- **Tier 3 exogeneity (observed confounders)** — ADDRESSED in Step 3 (added location + demographics; watched the bias correct).
- **Tier 3 functional form** — addressed in Step 4 (log-log).
- **Tier 1 heteroskedasticity** — DETECTED (U-shaped residual SD; bootstrap SD ≈8.0e-6 vs classical SE 5.4e-6, ~1.5×). Fix = robust SEs. *Article 2.*
- **Tier 1 independence (spatial)** — expected, not yet tested. Moran's I on residuals. *Article 2.*
- **Tier 2 normality** — violated (Omnibus/JB reject) but **harmless** at N≈30k (CLT).
- **Tier 3 unobserved confounder (condition/quality)** — UNCORRECTABLE. The standing honesty caveat: *"I removed the bias from the confounders I could observe; here's what's plausibly left."*

