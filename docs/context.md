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

*(to be filled)*

### 2.1 Distributions
- target (`sale_price` → log), key predictors, skew/transform decisions —

### 2.2 Outlier analysis
- `sv_is_outlier` reasons, price/sqft sanity bounds, influential-point notes —

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

### Open
- **School rating (~25% missing):** impute vs. complete-case — decide deliberately; missingness is likely spatially patterned, so `dropna()` re-introduces geographic bias. *(unresolved)*

## 4. Model details

*(to be filled)*
- specification(s), feature blocks used, transforms, weighting (WLS), interactions —

---

## 5. Validation strategy

*(to be filled)*
- diagnostics run, robust/cluster SEs, spatial-residual handling, how findings were stress-tested —