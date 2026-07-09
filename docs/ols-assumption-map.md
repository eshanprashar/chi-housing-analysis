# The Assumption Map — What Each OLS Assumption Breaks

*Reference for three jobs: (1) reading a regression honestly, (2) writing the
post — address each assumption in turn, (3) interview prep.*

**Organizing principle:** don't memorize assumptions as a flat list. Know
**which output each one corrupts**, and **whether the summary table shows a
symptom.** That last part is the whole point — some violations are visible in
standard diagnostics; the most dangerous one is invisible.

The three tiers, ordered by how hard they are to catch:

1. **Tier 1 — SE assumptions:** break the *uncertainty* (SE, t, p, CI). The
   estimate is still aimed right. **Detectable.**
2. **Tier 2 — Distributional assumption:** breaks the *reference curve* for t and
   p. **Rescued by large N.**
3. **Tier 3 — Structural assumptions:** break the *estimate itself*. **No symptom
   in the table.** The dangerous tier.

---

## Tier 1 — Assumptions that break the STANDARD ERROR

When these fail, the coefficient is still **unbiased** (aimed right), but the
reported SE is wrong — almost always **too small**. The cascade:

- SE too small → t too big → p too small → CI too narrow → **you over-claim significance.**

### 1. Homoskedasticity — errors have constant variance
1. **Assumes:** residual spread is the same across all values of x / fitted values.
2. **Breaks when:** variance changes with x (a funnel — or the U-shape we found).
3. **Effect:** the formula factors out a single σ that doesn't exist → SE wrong (usually too small).
4. **Symptom (VISIBLE):** residuals-vs-fitted changes width; residual-SD-by-bin table moves; bootstrap SD ≠ classical SE; Breusch-Pagan rejects.
5. **Fix:** robust (HC) standard errors — same estimate, honest SE.
6. **In our data:** yes — the U-shaped residual spread.

### 2. Independence — errors are uncorrelated with each other
1. **Assumes:** each observation carries fresh, independent information.
2. **Breaks when:** observations share unobserved shocks (nearby houses → spatial; repeated dates → temporal).
3. **Effect:** correlated obs repeat information → **effective N < actual N** → SE understated (SE shrinks like 1/√information).
4. **Symptom (visible with effort):** Moran's I on residuals (spatial); Durbin-Watson (temporal); clusters in a residual map.
5. **Fix:** clustered SEs, or a spatial error/lag model.
6. **In our data:** yes — spatial autocorrelation (motivates Steps 5–6 / Post 1.2).

**Link out of Tier 1:** both failures share one signature — the classical SE is
**too small**, so robust/clustered SEs come out *larger*. The tell is always **"a
resampling or robust estimate disagrees with the formula."** If they disagree, an
SE assumption is broken.

---

## Tier 2 — The assumption that breaks the REFERENCE CURVE

### 3. Normality of errors
1. **Assumes:** errors are normally distributed — so t and p can be read off a normal/t curve.
2. **Breaks when:** errors are skewed or fat-tailed.
3. **Effect:** the reference bell used to compute p is the wrong shape → p mis-calibrated.
4. **The rescue (why this is Tier 2, not Tier 1):** CLT. β̂ is a big weighted sum of errors, so **the coefficient goes normal even when the errors don't** — at large N. t/p stay valid.
5. **Symptom:** Q-Q plot of residuals bends; Jarque-Bera / Omnibus reject (they will, at our N).
6. **Matters when:** small samples. Nearly free at large N.
7. **In our data:** violated (skewed residuals, Omnibus rejects) but **harmless** — N≈30k, CLT covers it.

**Link out of Tier 2:** Tiers 1 and 2 both concern *inference/uncertainty*, and
both are at least partly **visible** in the table or standard diagnostics. Tier 3
is categorically different — it corrupts the estimate itself, and it hides.

---

## Tier 3 — Assumptions that break the ESTIMATE (and leave no symptom)

When these fail, the SE, t, and p can all be **perfectly valid** — and you are
precisely, confidently estimating the **wrong number.** There is no red flag in
the summary table. This is why a tiny p-value never means "correct."

### 4. Exogeneity — errors uncorrelated with x (no omitted confounders)
1. **Assumes:** everything left in the error term is unrelated to your predictors.
2. **Breaks when:** an omitted variable affects y AND correlates with x (a confounder).
3. **Effect:** β̂ is **biased** — it absorbs the confounder's effect and mis-attributes it to x.
4. **Two sub-cases (the solvable / unsolvable split):**
   - Observed confounder → include it → bias removed (e.g., location, Step 3).
   - Unobserved confounder → can't include → bias remains (e.g., condition — the CCAO blind spot).
5. **Symptom:** **NONE in the table.** Only domain reasoning, sign checks, or coefficients *shifting when you add controls* reveal it.
6. **Fix:** add observed confounders; for unobserved — sign the bias, proxy it, fixed effects, instruments; otherwise disclose.
7. **In our data:** pervasive — the whole Block A → Block B story; condition unobservable.

### 5. Correct functional form — the relationship is actually linear (as specified)
1. **Assumes:** the model's shape matches reality (here, linear in the predictors as entered).
2. **Breaks when:** the true relationship curves (raw sqft vs price → absurd extrapolation).
3. **Effect:** the estimated "linear effect" is a biased summary of a nonlinear truth.
4. **Symptom:** curved residual-vs-fitted pattern; implausible predictions (the $236M house).
5. **Fix:** transform (log-log, Step 4), polynomials, splines.
6. **In our data:** yes at the tails — motivates the log-log transform.

**Link out of Tier 3:** this is why "read the coefficients, not the p-values" is
only *half* the discipline. The other half: **a coefficient can be precise,
significant, and wrong.** The table certifies precision, never correctness.

---

## The map, at a glance

| # | Assumption | What it breaks | Symptom in table? | Effect | Fix | In our data |
|---|---|---|---|---|---|---|
| 1 | Homoskedasticity | SE (uncertainty) | Yes — resid plot, BP | SE too small → over-claim | robust SE | Yes (U-shape) |
| 2 | Independence | SE (uncertainty) | Partly — Moran's I | SE too small → over-claim | clustered / spatial SE | Yes (spatial) |
| 3 | Normality | t/p reference curve | Yes — Q-Q, JB | mis-calibrated p | CLT / more N | Violated but harmless |
| 4 | Exogeneity | the estimate (bias) | **No** | wrong number | controls / FE / IV | Pervasive |
| 5 | Functional form | the estimate (bias) | Partly — resid curve | wrong number | transform | Yes (tails) |

The further down the table, the **more dangerous and less visible.** Tier 1
shouts, Tier 2 is rescued, Tier 3 (especially #4) is silent.

---

## How to use this when writing the post

Address them in order of "does the reader even know to worry?" — visible first,
invisible last, so the piece builds toward the real caveat.

1. **State the estimates and CIs** — the findings.
2. **Tier 1 (honest-uncertainty caveat):** heteroskedasticity + spatial
   correlation make classical SEs optimistic; show robust/clustered SEs; report
   which findings survive.
3. **Tier 2 (one sentence):** residuals are non-normal, but N makes t/p safe —
   shows you checked.
4. **Tier 3 (the climax — the real limits):**
   - *Exogeneity:* "I controlled for the confounders I can see (location); here's
     what I can't (condition) and the direction it likely biases things."
   - *Functional form:* the log-log fix and why raw-linear was wrong.
5. **Close on the honest line:** a precise, significant coefficient can still be
   the wrong number — significance certifies *not-zero*, never *correct*.

---

## Interview-ready compression

- **"Which OLS output does each assumption break?"**
  SE assumptions (homoskedasticity, independence) break the **SE**; normality
  breaks the **t/p reference curve** (CLT rescues at large N); exogeneity and
  functional form break the **estimate itself**.
- **"Which is most dangerous?"**
  Exogeneity — it biases the estimate and leaves **no symptom** in the table.
- **"How do you detect each?"**
  resid-vs-fitted + Breusch-Pagan (homoskedasticity); Moran's I / Durbin-Watson
  (independence); Q-Q / Jarque-Bera (normality); domain reasoning + coefficient
  shifts (exogeneity); residual curvature (functional form).
- **"One-line takeaway?"**
  The summary table certifies **precision, never correctness.**