# Post 1.1 / 1.2 — Project Brief: The Chicago Hedonic

*A living brief. This is the plan for the first regression post(s), built on the CCAO `training_data.parquet`. It maps each analysis step to a section of ISL Chapter 3 so the project doubles as structured practice.*

---

## Framing: inference, not prediction

The goal is to **explain and attribute** variation in home prices — to read coefficients and make defensible claims — not to minimize prediction error. This is the deliberate contrast with the Cook County Assessor (CCAO):

| | CCAO model | This project |
|---|---|---|
| Goal | Prediction (assess every property) | Inference (explain price) |
| Model | LightGBM (trees) | OLS / WLS regression |
| Features | ~100, redundancy is fine | ~12–16, curated & non-redundant |
| What's read | Predicted value, SHAP | Coefficients, p-values, CIs |
| Multicollinearity | Mostly harmless | Poison — wrecks coefficients |

Parsimony (few, non-redundant predictors) is the discipline that keeps the coefficients interpretable. That trade — a little R² for explainability — *is* the inference-vs-prediction choice, and it's a recurring Substack beat.

---

## 1. Guiding question

**"In Chicago, what are you really paying for when you buy a home — A (the house itself) or B (where it sits)?"**

The A-vs-B split is kept **generic on purpose**. Data quality (esp. structure-feature missingness) may reshape what "A" and "B" end up being; we let the data settle the labels rather than committing up front.

### Sub-questions (housing analogues of ISL Ch. 3's seven questions)

1. Do these features relate to price at all? → overall **F-test** *(3.2.2)*
2. How much of price do they explain? → **R², RSE** *(3.1.3 / 3.2.2)*
3. Which features matter — and is it real or just huge N? → **t-tests / p-values** + big-N caveat *(3.1.2 / 3.3.3)*
4. How big is each effect (what's a bedroom worth, in %)? → **coefficients + confidence intervals**, log-Y *(3.1.2 / 3.3)*
5. Does B matter beyond A? → **grouped (partial-F) comparison** *(3.2.2)*
6. Are relationships linear; do features amplify each other? → **non-linearity & interactions** *(3.3.2)*
7. Do the model's assumptions hold? → **residual diagnostics** *(3.3.3)*

---

## 2. Research method — the steps (mapped to ISL §3)

**Outcome:** `log(sale price)` — stabilizes variance and lets coefficients read as percentages.

| Step | What we do | ISL |
|---|---|---|
| **0a — Data quality audit** | Missingness per candidate feature; sanity checks (0-bed homes, $1 sales, impossible year-built). May itself decide the A/B split and yields its own Substack beat. | — |
| **0 — Setup** | Curate a small, non-redundant feature set; group into block A (house) and block B (location). | 3.1 / 3.3.1 |
| **1 — One feature first** | Simple regression on a single variable (e.g. sqft): read slope, SE, t/p, CI, R² and *feel* what each number means. | 3.1 |
| **2 — Block A only** | Multiple regression on house features: overall F, individual effects, variance explained. | 3.2 |
| **3 — Add block B** | Add location features; test whether they collectively improve the model beyond A. **The money question.** | 3.2.2 |
| **4 — Shape & synergy** | Is sqft–price linear or curved? Does a bedroom pay off more in richer areas (interaction)? | 3.3.2 |
| **5 — Diagnose** | Residual battery: heteroskedasticity (does price get noisier as it rises?), outliers/influential sales, and the geospatial twist — **spatial autocorrelation** of residuals (Moran's I). | 3.3.3 |
| **6 — Robustness (→ 1.2)** | If spatial correlation is real (it will be), OLS p-values are overstated. Fix the standard errors (cluster by neighborhood / spatial model); see which findings survive. | 3.3.3 (correlated errors) |

### Post split
- **Post 1.1** = Steps 0a–5. The clean OLS story, ending on the **detection** cliffhanger: *"the errors aren't random — look where the model fails."*
- **Post 1.2** = Step 6 (the spatial **fix**) + OLS-vs-KNN and the essay on distance *(ISL 3.5)*.
- **Post 2** = the temporal cousin (time-series): correlated errors in time.

---

## 3. The crime teaser (scoped narrowly)

Crime is included as **one right-hand-side predictor**, asking a single inference question: *does crime's effect on price survive once income and location are controlled, or does it collapse into them?* (CCAO dropped crime precisely because it's collinear with income/neighborhood — so this is a grounded VIF demonstration.)

**Hard caveat to state explicitly:** price ↔ crime causation is ambiguous (crime may depress prices; cheaper areas may attract crime; disinvestment may drive both). The hedonic shows **association, not causation**. The teaser must not imply otherwise — and that limitation is the bridge to the future standalone crime post, where crime becomes the *outcome* (spatial spread, time trend, cross-city comparison).

---

## 4. Candidate Substack insights

*(Real numbers TBD — these are the shapes of findings to aim for.)*

- **Headline decomposition:** "The house explains X% of price; location lifts it to Y% — so most of what's left is about *where*, not *what*."
- **Price tags on features:** what a bedroom / 100 sqft / a year of age is worth in %, with honest uncertainty — and which flip or vanish once location is controlled.
- **The big-N honesty moment:** with hundreds of thousands of sales, everything is "significant," so significance is meaningless and effect size is the real story.
- **Multicollinearity made visible:** income vs. education fighting over credit; what happens to coefficients when you keep one vs. both.
- **The map that makes the point:** plot *where* the model is wrong (residuals). Errors cluster (rich pockets, sharp edges like CCAO's Hyde Park price-cliff) — the visual argument for "location beyond features" and for why plain OLS understates uncertainty.
- **The CCAO contrast:** 100 features + trees for prediction vs. ~14 + regression for explanation — same data, opposite goals.
- **"What the County doesn't reliably know about your house":** the data-quality audit as content — condition unrecorded for >98% of properties, sparse characteristics, the exterior-only blind spot.
- **A "what-if" policy note (stretch):** if interior/image data were shared by third parties (which owners already permit for listings), would property-tax accuracy improve enough to outweigh the privacy cost? A speculative companion piece, clearly flagged as opinion.

---

## 5. Scope notes & open questions

- **A/B labels are provisional** — to be settled by the Step 0a audit.
- **Spatial fix is deferred to 1.2** — 1.1 detects, 1.2 corrects.
- **Condos excluded** — the `model-res-avm` parquet covers single/multi-family only; condos are a separate CCAO model. Either scope to SF/MF or add condo data later.
- **Selection bias** — sold homes ≠ the full housing stock; claims about "all homes" carry this caveat.
- **Unit of analysis** — individual sales (PIN/card-level), not tract aggregates; aggregate residuals/predictions up to community areas for reader-facing maps.

---

## Tooling

Python + Poetry. `statsmodels` (not just sklearn) is required for the inference half — it provides the p-values, CIs, F-tests, and summary tables ISL teaches. Repo: `src/` package (shared loading, feature blocks, diagnostics) + `notebooks/` (the narrative layer / the posts themselves).
