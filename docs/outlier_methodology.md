# Side Quest 2 — Project Plan: Interpretability in Public-Policy Data Science

*A living plan. This is a side quest, parked until the primary hedonic regression (Post 1.1) is done. It uses the same CCAO sales data and geography machinery, but asks a self-contained methodological question. Save in repo; return later.*

---

## Framing: comparing detectors, not adjudicating truth

This is a **statistics-only** study. We compare how different outlier-detection *methods* score and rank the same sales — we do **not** try to decide whether a flagged sale is "really" non-market. CCAO's published flags are the **target we're trying to reproduce**, not a flawed proxy for ground truth (so benchmarking against them is the metric, not circularity).

The deliberate contrast:

| | CCAO's method | This study's challengers |
|---|---|---|
| Low $/sqft flag | N-SD from group mean on log $/sqft | Percentile within neighborhood |
| Anomaly flag | Isolation forest (multivariate, black-box per sale) | Mahalanobis distance; ratio-percentile |
| Legibility | Reproducible + open-sourced, but per-sale inscrutable | Formula a non-specialist can read |

**So-what:** these methods aren't academic — their output *excludes sales from the assessments that set tax bills*. A method that decides who's taxed how should be as simple as accuracy allows. The question is how much accuracy the complexity actually buys.

---

## Guiding question

**"Do transparent, simple outlier methods recover what CCAO's complex ones flag — and if not, what does the complexity catch that a formula can't?"**

Honest-either-way discipline: the article is good whichever way the numbers fall — "simple recovers 90%+" is a legibility win; "the forest catches structure formulas miss" is an honest limit. Decide the agreement bar *before* seeing results so it stays an audit, not a story fit to the data.

---

## The two experiments (kept separate — different claim strengths)

### Experiment 1 — Low $/sqft: N-SD-on-log vs. percentile
- **Risk:** low. Both are univariate on the same variable; logging + SD is close to a percentile by construction.
- **Expected finding:** near-identical ranking (high Spearman) → "an elaborate way to compute a percentile," **plus** the interesting divergence in *thin neighborhoods* where SD is unstable and the percentile is more robust.
- **Metric:** Spearman rank correlation between the two continuous scores (threshold-free — both are scores we control, so no cutoff needed). Set-overlap at matched cutoffs as secondary.

### Experiment 2 — Anomaly: Mahalanobis + ratio-percentile vs. CCAO's forest flag
- **Risk:** high. This is the thesis. Multivariate structure may or may not be reducible to a transparent formula.
- **The binary-target snag:** CCAO published a *flag* (0/1), not the forest's continuous *score*. So score-vs-score rank correlation is off the table; we benchmark against their flag.
- **Method B (chosen):** sweep our method's threshold across its whole range and trace how well our ranking recovers their flag — an ROC/PR-style curve, **AUC** as the headline (threshold-free on our side, neutralizing the arbitrary-cutoff problem).
- **Method C (sanity check):** flag the same *number* of worst-scoring sales CCAO flagged; report set-overlap on equal-sized sets.
- **The ladder:** run **both** challengers (ratio-percentile = cheap partial-multivariate; Mahalanobis = honest multivariate, elliptical assumption) and read the *gap*:
  - ratio ≈ Maha ≈ forest → complexity buys nothing; simplest wins.
  - ratio < Maha ≈ forest → joint structure matters, but a transparent formula captures it (**best case for the thesis**).
  - ratio ≈ Maha < forest → forest catches non-elliptical structure; complexity is doing real work (**honest limit**).

---

## Method — the steps

| Step | What we do |
|---|---|
| **0 — Feature parity (dependency)** | Pull CCAO's anomaly feature list from `model-sales-val` config. Both challengers in Exp. 2 must see the **same features** or we're comparing feature sets, not methods. |
| **1 — Geography** | Reuse the neighborhood boundaries from the primary project (spatial join sales → named neighborhoods) as the grouping unit for the per-neighborhood stats. |
| **2 — Neighborhood sample** | Pick a handful of contrasting neighborhoods: one thick (Lincoln Park), one thin, one mid — so small-sample instability of SD/Mahalanobis actually surfaces. |
| **3 — Experiment 1** | Compute N-SD-on-log $/sqft and percentile per neighborhood; Spearman + divergence cases. |
| **4 — Experiment 2** | Compute Mahalanobis distance and ratio-percentile (same features as forest); AUC vs. CCAO flag (B) + equal-size overlap (C); read the ladder. |
| **5 — Divergence gallery** | Pull the specific sales where methods disagree — addresses, buyer/seller names, streets. The qualitative payoff. |

---

## Candidate insights

- **"Logging + SD is a percentile in a lab coat"** — Exp. 1 rank correlation, with the thin-neighborhood exception where the fancy method is *less* stable.
- **The AUC headline** — one number for "how well a formula recovers the forest's flags."
- **The ladder result** — where on the three rungs accuracy actually jumps (the crux).
- **The divergence gallery** — the actual sales only one method catches; names/streets make it concrete.
- **The stakes-asymmetry point** — a missed non-market sale can bias a *whole neighborhood's* assessed values; so *where* disagreements cluster matters, not just how many.
- **Interpretability vs. auditability** — the forest is open-sourced and reproducible but inscrutable per sale; is per-sale legibility a *requirement* when the output sets taxes? (Argue both sides.)

---

## Scope notes & open questions

- **Statistics-only** — comparing detectors, not validating non-market truth. No hand-labeling.
- **Target is CCAO's published flag** — reproducing it is the goal; agreement is the metric, not circular.
- **OPEN — feature parity:** need CCAO's exact anomaly feature list before Exp. 2 is fair. *(blocking dependency)*
- **OPEN — Mahalanobis fragility:** covariance is unstable in thin groups / correlated features; compute pooled with neighborhood controls or only on thick neighborhoods.
- **Reuses:** neighborhood geography + geopandas machinery from the primary project — do that first.
- **Parked:** side quest #2, after the web tool (#1). Primary focus remains the hedonic regression.