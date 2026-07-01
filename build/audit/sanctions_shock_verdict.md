# Sanctions-Shock F3 Test — VERDICT

**SOURCE:** build/audit/sanctions_shock_result.json (β/SE/p/CI/LOQO/bootstrap, all read from the estimator);
build/results/sanctions_shock_verify.json (beta_matches=true, bootstrap_p_recomputed_matches=true,
leave_one_out_recomputed_matches=true — byte-reproducible from panel + treatment CSV, seed 42);
build/data/cm_panel/cm_weight_panel_full.parquet (corrected w = cn_haven_raw/tot_haven_raw, USD, NO FX —
the dependent variable, identical to the GPR-China full-panel pass); build/data/sanctions/sanctions_treatment_panel.csv
+ build/contracts/sanctions_sources.json (grounded sanctions treatment + regulatory control, Part 1).
Estimator, wild_cluster_bootstrap_quarter(), leave_one_quarter_out() reused verbatim from
build/audit/cm_regression_full_recompute.py. Recompute: build/audit/sanctions_shock_recompute.py (no network).

## VERDICT: NO-SANCTIONS-F3 (F3 not loaded) — TERMINAL for the F3-LOADS question, with a terminal INSUFFICIENT-POWER caveat on the NEGATIVE (substitution) sign

The corrected, sanctions-specific shock does **not** produce the negative, significant,
regulatory-control-surviving, leave-one-out-robust coefficient that F3 substitution requires. The sanctions
coefficient is **robustly positive** across all 22 leave-one-quarter-out drops and **bootstrap-insignificant at
G = 22** — exactly the GPR-China structure — so **no sanctions-driven substitution loads on the shock**. This is
**TERMINAL for the F3-LOADS question**: a negative, significant, robust, control-surviving β is decisively
absent, and the with/without-control comparison shows no attenuation pattern that would hide one.

**But the verdict does NOT claim an economically meaningful negative is excluded.** The honest inference
instrument for this design is the **G = 22 wild cluster bootstrap**, whose implied CI on the no-lags with-control
spec is **[−0.056, +0.244]**. Its lower bound −0.056 is ≈ half the corrected mean CN-nationality haven share
(~0.109) — an economically meaningful negative the honest inference does **not** exclude. The sign of any
negative (substitution) channel is therefore **UNRESOLVED**: this is a **terminal INSUFFICIENT-POWER caveat on
the negative sign**, mirroring the GPR-China precedent exactly (that pass landed no-substitution with terminal
insufficient-power on the sign of the negative channel, explicitly declining to claim the negative was
excluded). The narrow lagged cluster-quarter CI [+0.0125, +0.0228] (G = 20, t-based) is **not** used as the
exclusion bound — the same verdict designates that few-cluster t-based SE an over-rejecting artifact, and an SE
that over-rejects for significance is equally too-narrow to serve as an exclusion bound.

## The merge and the estimation set

Sanctions treatment merged onto the full CM panel by fiscal_quarter: **22/22 keys matched, 0 orphans on
either side** (merge_ok_22_of_22 = true). Estimation set: 22 quarters (2019q3–2024q4), 104,306 valid w-cells,
7,806 funds. Headline lagged spec uses 84,854 obs (first two quarters lost to the L1/L2 chain → 20 quarter
clusters for the lagged spec; the no-lags specs and the bootstrap run at the full **G = 22**).

## THE LOAD-BEARING COMPARISON — sanctions β WITH vs WITHOUT the regulatory control

Headline spec: w_{f,t} = α_f + β·sanc_freeze_post + λ·reg_crackdown_post + γ₁w_{t-1} + γ₂w_{t-2}
+ δ·relative_returns + θ·[log VIX, broad dollar, oil] + ε. Within (fund-demeaned) OLS, fund FE, NO time FE.

| Spec | β (sanc_freeze) | classical SE / p | cluster-fund SE / p | cluster-quarter SE / p | 95% CI (cluster-quarter) | n_obs | n_funds | G_q |
|------|-----------------|------------------|---------------------|------------------------|--------------------------|-------|---------|-----|
| **WITHOUT** reg control | **+0.018507** | 0.00479 / 0.0001 | 0.00746 / 0.0132 | 0.00339 / 0.0000 | [+0.01141, +0.02560] | 84,854 | 6,307 | 20 |
| **WITH** reg_crackdown | **+0.017661** | 0.00477 / 0.0002 | 0.00769 / 0.0216 | 0.00248 / 0.0000 | [+0.01248, +0.02284] | 84,854 | 6,307 | 20 |

**The sanctions coefficient is POSITIVE and does NOT attenuate when the regulatory control enters**
(+0.0185 → +0.0177, a 4.6% change, well inside the SE). The λ on reg_crackdown_post is **−0.0076**
(cluster-quarter p = 0.016): the mild *negative* delisting-channel loading sits on the regulatory control, not
on the sanctions treatment. So the with/without comparison does not show the "apparent reallocation loaded on
the delisting channel" pattern that a null-via-attenuation would produce — because there is no negative
sanctions loading to reallocate in the first place. The sanctions variation loads **positive**, the opposite of
the F3-substitution sign, in both columns.

## Honest few-cluster inference (the decision-controlling test)

Wild cluster bootstrap by quarter (Rademacher, null imposed, seed 42, 2000 reps, **G = 22**) on the headline
WITH-control spec (no-lags design, the same convention as the GPR pass): β = +0.093985, t = 1.304,
**bootstrap p = 0.2655**, implied CI **[−0.056, +0.244]**. The tiny cluster-quarter p on the lagged spec is a
few-cluster over-rejecting artifact; under the honest bootstrap the coefficient is **insignificant**, and its
interval is wide enough to include an economically meaningful negative (−0.056 ≈ half the ~0.109 mean CN haven
share). So the honest instrument rules out a significant *positive-or-negative* sanctions effect **and** — the
load-bearing point for the label — does **not** exclude a meaningful negative. This same artifact-vs-honest
distinction governs every exclusion claim below: the narrow lagged CI is not an exclusion bound.

## Robustness panel (all genuinely re-estimated; none selected for sign)

| # | Spec | β | cluster-quarter p | 95% CI (cluster-quarter) | note |
|---|------|---|-------------------|--------------------------|------|
| 1 | freeze, no control | +0.018507 | 0.0000 | [+0.0114, +0.0256] | positive |
| 2 | freeze + reg_crackdown (headline) | +0.017661 | 0.0000 | [+0.0125, +0.0228] | positive; no attenuation |
| 3 | freeze + reg_hfcaa (bounded window) | +0.017777 | 0.0000 | [+0.0125, +0.0230] | positive; stable |
| 4 | eo2023 (2nd sanctions event) + freeze + reg | −0.003557 | 0.1544 | [−0.0086, +0.0015] | negative but INSIGNIFICANT |
| 5 | sanc_intensity (SURVIVORSHIP-BIASED/SPARSE) + reg | −0.000082 | 0.5149 | [−0.0003, +0.0002] | ≈0; flagged robustness only |
| 6 | narrow event window (2022q1–q2 vs pre) + reg | +0.042015 | 0.0000 | [+0.0361, +0.0480] | positive, larger |
| 7 | freeze + reg, NO weight lags (G=22) | +0.093985 | 0.2065 | [−0.0559, +0.2439] | positive, insignificant |
| 7b | freeze, NO lags, NO control (G=22) | +0.107298 | 0.2687 | [−0.0891, +0.3037] | positive, insignificant |

The only negative coefficients (r4 Dec-2023 secondary-sanctions EO; r5 survivorship-biased intensity) are both
**insignificant** and are the two specs the pre-registration and Part-1 contract flagged as the distinct-timing
lever (r4) and the sparse/biased regressor (r5). No spec produces a significant negative. The headline freeze
step is **positive across every window definition**, including the tight 2-quarter event window (r6, +0.042).

## Leave-one-quarter-out (LOAD-BEARING; computed, persisted, verifier-reproduced)

All 22 β's persisted for both the WITH-control and WITHOUT-control headline specs.
- **WITH control:** every drop stays positive, range +0.0038 (drop 2021q3) to +0.0226 (drop 2022q3); never
  crosses zero. Full β = +0.0177.
- **WITHOUT control:** every drop positive, range +0.0076 (drop 2021q3) to +0.0236 (drop 2022q3); never crosses
  zero. Full β = +0.0185.

The result is robustly positive and never sign-flips; it is not driven by any single quarter. (leave_one_out_
recomputed_matches = true.)

## Collinearity diagnostic — can the panel separate the channels?

- Across-22-quarter correlation sanc_freeze_post vs reg_crackdown_post = **0.8281** (the r=0.828 Part-1 flagged).
- VIF of sanc_freeze in the WITH-control within design (after fund FE + macro block + weight lags +
  reg_crackdown) = **6.37**; sqrt(VIF) = 2.52. Without the regulatory control VIF = 6.28. Adding reg_crackdown
  changes the sanctions cluster-quarter SE by a factor of **0.73** (it slightly *tightens* it, because
  reg_crackdown absorbs residual variance while barely touching the sanctions variation).

The r=0.828 collinearity is real. It is not what drives the F3-LOADS answer — the point estimate is robustly
**positive** in every spec, not a marginal negative that the collinearity blurs. But the collinearity (VIF≈6.4,
sqrt≈2.5) **does** widen the honest interval: the narrow WITH-control cluster-quarter CI [+0.0125, +0.0228] is a
G=20 t-based interval from an SE the honest-inference section calls an **over-rejecting artifact**, so it is
**not** a valid exclusion bound. The honest G=22 wild cluster bootstrap CI is **[−0.056, +0.244]** — it does
**not** exclude an economically meaningful negative (lower bound −0.056 ≈ half the ~0.109 mean CN haven share).
So on the honest instrument the panel **cannot** exclude a meaningful negative; the F3-LOADS *positive-loading*
answer is clean, but the *negative sign* is INSUFFICIENT-POWER.

## Power diagnostic

- sanc_freeze_post cross-quarter SD (22q) = 0.5096.
- Within-fund SD of sanc_freeze surviving fund FE = residual share **0.399** of within-fund variation after FE
  + macro controls (NO reg), **0.396** after also adding reg_crackdown. Nearly 40% of the treatment's
  within-fund variation survives the controls and the regulatory control — the treatment is **not** absorbed;
  there is genuine identifying variation.
- G = 22 quarter clusters. The lagged WITH-control cluster-quarter CI half-width is 1.96·0.00248 ≈ 0.0049, but
  that G=20 t-based interval is the over-rejecting artifact and is **not** the exclusion bound (see below).

There is genuine identifying variation and enough of it to reject an F3-substitution *loading* (the point
estimate is robustly positive, not a blurred marginal negative). But **power is NOT adequate to exclude an
economically meaningful negative.** The honest instrument — the G=22 wild cluster bootstrap — gives an implied
CI of **[−0.056, +0.244]**, and −0.056 is ≈ half the corrected mean CN haven share (~0.109). The tight lagged
[+0.012, +0.023] interval is **not** used as the exclusion bound, because the honest-inference section flags its
SE as over-rejecting; an SE too narrow for correct significance is equally too narrow for exclusion. Honest
read: **NO-SANCTIONS-F3 on the positive-loading finding, with terminal INSUFFICIENT-POWER on the negative
sign** — the meaningful negative is not excluded.

## Which channel does the within-fund CN-weight variation load on?

Neither channel produces sanctions-style substitution (a negative weight move). The sanctions treatment loads
**positive** (opposite of F3) and is bootstrap-insignificant; the regulatory control carries a mild significant
**negative** (λ = −0.0076), i.e. what small delisting-driven CN-weight reduction exists sits on the regulatory
control — but that regulatory negative is small and is not a sanctions effect. There is no sanctions-specific
outflow to attribute to F3.

## Comparison to the GPR-China full-panel result

GPR-China full-panel pass: headline β = **+0.0125** (positive), robust across all 22 LOQO drops, negative
(substitution) direction bootstrap-insignificant (p = 0.58 at G = 22). Sanctions pass: headline β = **+0.0177**
WITH control / **+0.0185** WITHOUT control (positive), robust across all 22 LOQO drops, bootstrap p = 0.27 at
G = 22. **The two passes are structurally parallel: both robust-positive across all 22 LOQO drops, both
bootstrap-insignificant at G = 22, both leaving the negative (substitution) sign UNRESOLVED.** The GPR pass
landed no-substitution with a terminal insufficient-power caveat on the sign of the negative channel and did
**not** claim the negative was excluded; this sanctions pass reaches the identical structure and makes the
identical, not a stronger, claim. Replacing the generic geopolitical-risk shock with the grounded sanctions
treatment (and adding the regulatory control) does not change the conclusion: no within-haven CN-weight
substitution *loads* on the shock, and the negative sign is not resolved from this data either way. The
GPR result holds under the correct sanctions shock.

## Comparison to the Part-0 pre-registered prediction: **HELD**

The pre-registration's primary prediction was **NO-SANCTIONS-F3 or INSUFFICIENT-POWER** — that the corrected
sanctions shock would not yield a negative, significant, regulatory-control-surviving, leave-one-out-robust
coefficient. **The prediction is HELD.** The relabeled verdict — NO-SANCTIONS-F3 on the positive-loading
finding, **with a terminal INSUFFICIENT-POWER caveat on the negative sign** — falls squarely inside the
pre-registered "NO-SANCTIONS-F3 or INSUFFICIENT-POWER" disjunction; it is, in fact, both endpoints at once (F3
not loaded on the sign that was estimable; the negative sign left under-powered). The one falsifiable commitment
(a negative, bootstrap-significant, window-robust, control-surviving, LOQO-robust β → SANCTIONS-F3-LOADS,
REFUTED) is **not** triggered: the coefficient is positive, bootstrap-insignificant, and does not attenuate
under the regulatory control. The prediction did not have to hold — a negative significant β was a live outcome
and was tested for; it did not appear.

## Magnitude statement

The sanctions treatment moves the within-fund CN-nationality haven weight by **+0.0177 (WITH regulatory
control) / +0.0185 (WITHOUT)** per unit of the freeze-post step — a *positive* move of ~1.8 percentage points,
opposite in sign to F3 substitution, and statistically indistinguishable from zero on the wild cluster
bootstrap (p = 0.27, G = 22). **No sanctions-driven substitution out of China-nationality haven exposure is
identified (F3 not loaded).** The honest G=22 bootstrap CI [−0.056, +0.244] does not exclude an economically
meaningful negative, so the *sign* of any negative substitution channel remains unresolved — a terminal
INSUFFICIENT-POWER caveat, not a claim that the negative is ruled out.
