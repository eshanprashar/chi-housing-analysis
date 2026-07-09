# Standard Errors, the √N Law, and Heteroskedasticity — Learning Notes

*From the Step-1 detour. Written to be re-derivable, not just re-remembered. The
transferable reflex is at the bottom — read that first if skimming.*

---

## 1. Goal

Understand what a **standard error (SE)** actually is — and how confidence
intervals are built from it — not as a formula to memorize but as the **standard
deviation of an estimate's sampling distribution**. The bootstrap makes that
abstract object *visible*.

## 2. Method — the bootstrap

- Draw **B** resamples, each of **N paired rows** (a sale = sqft **and** price
  together), sampled **with replacement** from the data.
- For each resample, **refit the regression and record the slope β̂₁** — *not* a
  mean. The point is that a regression coefficient has a sampling distribution
  exactly like a sample mean does (the bridge from the dice intuition).
- Result: a distribution of **B slopes**. Its SD *is* the SE, empirically.

## 3. Result — the CENTER (two separate guarantees)

- The slope distribution is **centered on β̂₁** because the estimator is
  **unbiased** (aimed true). This is *not* CLT.
- The distribution is **bell-shaped** because of the **CLT** (the slope is a big
  weighted sum of errors, so it goes normal regardless of the errors' own shape).
- **Keep these in separate drawers: unbiasedness → correct center; CLT → normal shape.**
- Subtlety: the bootstrap centers on β̂₁ (our sample estimate), not the true β₁ —
  it re-draws from *our* data, so it reveals the *spread* around our estimate.

## 4. Result — the SPREAD (where the assumptions bite)

- Bootstrap SD ≈ **8.0e-6** vs classical formula SE ≈ **5.4e-6** — the bootstrap
  was ~1.5× larger.
- **Non-independence and heteroskedasticity do NOT move the center or bias the
  estimate.** (Confirmed: bootstrap mean 7.856e-4 landed on the estimate 7.853e-4.)
  They make the **classical SE wrong — too small** — because correlated /
  unequal-variance observations carry less independent information than their
  count suggests. Center = fine; **width = miscalibrated.**
- This is exactly why robust / clustered SEs exist (Step 5 → 1.2): same estimate,
  repaired uncertainty.

## 5. The √N law, made visible (the k/√n experiment)

Claim: **SE shrinks in proportion to 1/√n.** Shown, not asserted:

- `sigma = sqrt(res1.scale)` → σ̂ (RSE, typical size of one error).
- `k = sigma / sqrt(x.var())` → a constant bundling everything in the SE formula
  *except* sample size. Because `Σ(xᵢ−x̄)² ≈ n·Var(x)`,
  `SE(n) ≈ σ/√(n·Var(x)) = [σ/√Var(x)] · 1/√n = k/√n`. So `k` = "the SE at n=1".
- Sweep n ∈ {500…16000}; at each, draw 200 subsamples **without replacement**,
  refit, take the **SD of the 200 slopes** = empirical SE at that n.
- Empirical SE fell along the **k/√n** curve → quadruple the data, halve the SE.
- Empirical points sat slightly **above** the line, converging at large n — the
  same heteroskedasticity/leverage story (the classical curve is a touch optimistic).

## 6. Chasing the gap → heteroskedasticity

- **Definition (precise):** the **variance (spread) of the residuals is not
  constant across the predictor / fitted values.** Not "residuals have a
  non-uniform shape."
- It need not be a widening fan. **Ours was a U** — residual SD high at both the
  smallest and largest homes, lowest for the modal ~1,100–1,250 sqft house
  (SD swing ~0.55 → 0.70, ≈1.25×).
- Diagnosed two ways:
  - **residuals vs fitted** — look for the band changing width (the visual).
  - **residual-SD-by-sqft-decile table** — the *quantified* version (put a number
    on the funnel).
  - (Breusch-Pagan test parked — will recur in the multiple-regression step.)

## 7. Deeper find — residuals as a second data-validity pass

- **Residual units:** the model is on log price, so a residual is a **log-ratio**:
  `resid = log(actual / predicted)`. Read it as **actual = e^resid × predicted**.
  resid −1 ≈ sold at 37% of predicted; −5 ≈ 0.67% of predicted.
- The U wasn't "the market is noisier at the tails." Extreme residuals traced to
  **two distinct causes**:
  - **Low end = contamination.** Non-market sales that slipped the `sv` filter —
    $22k–$40k entity transfers, concentrated in low-value South Side community
    areas (Greater Grand Crossing, Roseland, Englewood…).
  - **High end = misspecification.** Linear-in-raw-sqft predicts absurd prices for
    9,000+ sqft homes ($25M–$236M) — a straight line has no ceiling. This is the
    concrete argument for the **log-log transform (Step 4)**.
- **Group-relative flag limitation (worth remembering):** CCAO's `Low price`
  flags are defined *relative to the neighborhood group*, so a nominal $22k sale
  in an already-cheap area doesn't trip them — our corroboration rule then has
  nothing to corroborate the entity flag with, and it survives. Group-relative
  price flags **miss non-market sales in low-value neighborhoods.** Carry these
  forward as Step-5 influence candidates (Cook's distance); do NOT reactively
  hand-delete (researcher-DOF trap).

## 8. The transferable reflex (the real takeaway)

**When an empirical/robust estimate disagrees with a formula that assumes clean
conditions, the assumptions are what's wrong — go look at the residuals.** The
bootstrap–formula gap was the *signal* that sent us to the residuals, which
revealed variance structure, contamination, and misspecification all at once.
Residual analysis is not just an assumptions check — it doubles as a second pass
at **data validity** and a test of **functional form**. And the honest fix for
the high-end misspecification is the **log-log transform**, not deleting houses.

---

## 9. Bias, unbiasedness, and omitted-variable bias (OVB)

### The proof that OLS is unbiased (one line)

The estimated slope decomposes as **truth + a noise term**:

`β̂₁ = β₁ + Σᵢ wᵢ εᵢ`,  where the weights `wᵢ = (xᵢ − x̄) / Σⱼ (xⱼ − x̄)²` are fixed
numbers determined by the x's.

Take the expected value (average over re-draws); β₁ is constant so it passes through:

`E[β̂₁] = β₁ + Σᵢ wᵢ E[εᵢ]`.

If `E[εᵢ] = 0` — the noise has mean zero — every term vanishes and `E[β̂₁] = β₁`. **Unbiased.**

That's the whole proof. Unbiasedness is **not** a deep property of least squares;
it's a direct consequence of **one assumption: the errors average to zero and
don't correlate with x.** Assume clean noise → get true aim. Almost circular, in
a satisfying way.

### The load-bearing part: ε uncorrelated with x

The mean-zero half is cheap (the intercept absorbs any constant offset). The
condition that actually breaks is that **the noise must not co-move with the
predictor.** When it does, `Σ wᵢ εᵢ` no longer averages to zero → β̂₁ is **biased**
(aimed off-target, not merely noisy).

### OVB is the usual cause

ε holds everything x doesn't capture. If an omitted variable **z** affects price
**and** correlates with x, then z lives inside ε and drags it into correlation
with x. β̂₁ then absorbs part of z's effect and mis-attributes it to x.

Rule of thumb: `bias ≈ (effect of z on y) × (association of z with x)`. Both
nonzero → bias.

### Two tiers — the practical distinction (observed vs unobserved)

- **Observed confounder → SOLVABLE.** If you can *measure* z, include it; the bias
  disappears because z leaves ε and enters the model. **Example: location.** Size
  correlates with location, location drives price → the single-variable size slope
  is biased. Fix: add Block B (Step 3). *Watching the size coefficient move when
  location enters IS this bias being corrected in real time* — and the size of the
  shift is a measurable statement of how much "size" was really location.

- **Unobserved confounder → HARD / UNSOLVABLE.** If z can't be measured, you can't
  include it and the bias stays. **Example: interior condition / quality /
  renovation — the exact CCAO blind spot (they can't enter buildings).** A
  renovated and a gut-job house with identical sqft/beds/location get the same
  prediction; whatever links condition to your predictors biases the coefficients,
  and no amount of adding *observed* features fixes it.

**Why "there's almost always OVB":** because there are almost always *unobserved*
confounders. No feature set is complete. So the honest stance is never "I removed
the bias" — it's **"I removed the bias from the confounders I could observe, and
here's what's plausibly left."**

### What you can still do about unobserved bias (can't remove → reason about it)

- **Sign it.** Often you can argue the *direction*: if condition correlates
  positively with both size and price, the size coefficient is biased *up*, so the
  estimate is an *upper bound*. Direction alone is worth a lot.
- **Proxy it.** Find an observed stand-in (year built / a renovation flag partly
  proxy condition).
- **Heavier machinery** — neighborhood fixed effects (absorb anything constant
  within an area), instruments, bounding arguments. Mostly beyond this project,
  but worth naming.

### The clean contrast to keep next to the SE one

| Problem | Estimate (aim) | SE (width) |
|---|---|---|
| Heteroskedasticity / non-independence | **unbiased** (fine) | **wrong** (too small) |
| Confounding / OVB | **biased** (off) | can look perfectly fine |

**Different drawers.** Step 1's size-only slope is suffering the *second* one: it
carries location on its back, so it is a **biased** estimate of size's effect.
Correcting that — by adding observed confounders block by block — is the whole
point of Steps 2–3. What can't be corrected (condition/quality) is the residual
honesty caveat the post has to state.