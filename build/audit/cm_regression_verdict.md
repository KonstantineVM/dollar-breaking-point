# Converse-Mallucci Weight-Regression F3 Test — VERDICT

SOURCE: build/audit/cm_regression_result.json (8 re-estimated specs + power_diagnostic +
few_cluster_inference) and build/results/cm_regression_verify.json (every cited statistic recomputed
deterministically from build/audit/cm_regression_recompute.py with no network: beta_matches=true,
bootstrap_p_recomputed_matches=true, leave_one_out_recomputed_matches=true). Panel:
build/data/cm_panel/cm_weight_panel.parquet (7,412 funds x 8 fiscal quarters, 37,403 fund-quarter obs).
External series: build/contracts/cm_sources.json (GPRC_China=GPRC_CHN, VIX=VIXCLS, broad dollar=DTWEXBGS,
oil=DCOILWTICO, relative_returns=MCHI-ACWX adj-close TR — each fetched and confirmed from the real
publisher file). Pre-registration: build/audit/cm_regression_prediction.md (committed before estimation;
NOT tuned to). Every statistic below is read from the estimator/bootstrap output, never hardcoded.

## VERDICT: INSUFFICIENT-POWER (with a negative directional lean)

The CM weight-regression estimator is the right discriminant (it separates substitution from
co-movement, which a within-holder correlation structurally cannot). The point estimate on GPRC_China is
**negative in all eight specifications**, but under honest inference for a single national series the
result is **too fragile to distinguish F3-LOADS from a near-null**: the wild cluster bootstrap p sits on
the 5% boundary, and leave-one-quarter-out shows the negative sign is not robust to dropping a single
quarter. Per the pre-registered rule, a fragile/boundary result whose CI does not exclude a near-null is
**INSUFFICIENT-POWER, not NO-SUBSTITUTION**, and the F3-LOADS bar ("negative, significant, AND robust")
is not cleared.

## What was estimated (beta read from the estimator; verifier reproduces it identically)

w_{f,t} = alpha_f + beta·GPRC_China_t + gamma1·w_{f,t-1} + gamma2·w_{f,t-2} + delta·relative_returns
          + theta·X_t + eps,  X_t = [log VIX, broad dollar, oil],  alpha_f = fund FE.

Fund FE + X_t replace time FE because GPRC_China is a SINGLE national series; time dummies would be
collinear with GPRC and absorb it, leaving beta unidentified (CM's exact device). Estimator: within
(fund-demeaned) OLS. Verifier: headline beta recomputed identically (beta_matches=true).

### Headline: w ~ gprc_avg + L1 + L2 + X + relative_returns  (cm_regression_result.json specs[0])
- beta = **-0.03826**  (n = 22,200 fund-quarter obs, 4,522 funds, within dof = 17,671)
- SE classical:         0.04198, p = **0.362**, 95% CI [-0.1205, +0.0440]  — INSIGNIFICANT
- SE clustered-fund:    0.01568, p = 0.015,   95% CI [-0.0690, -0.0075]
- SE clustered-quarter: 0.01257, p = 0.029,   95% CI [-0.0706, -0.0059]  (only G = 6 clusters here)
- Magnitude: -0.0111 weight per 1-SD GPRC_China rise = **-6.3% of the mean CN haven share (0.175)**.

### Robustness panel (all genuinely re-estimated; cm_regression_result.json specs[1..7])
| spec | beta | n_obs | n_funds | p (cluster-quarter) |
|------|------|-------|---------|---------------------|
| HEADLINE w, gprc_avg, +lags, +relret      | -0.03826 | 22,200 | 4,522 | 0.029 |
| w, gprc_avg, +lags, NO relret             | -0.05590 | 22,200 | 4,522 | 0.005 |
| w, gprc_avg, NO lags, +relret             | -0.03540 | 36,277 | 6,286 | 0.001 |
| w, gprc_avg, NO lags, NO relret           | -0.03379 | 36,277 | 6,286 | 0.000 |
| w, gprc_END, +lags, +relret               | -0.13815 | 22,200 | 4,522 | 0.029 |
| w, gprc_END, NO lags, +relret             | -0.01478 | 36,277 | 6,286 | 0.025 |
| w_ALT (foreign denom), gprc_avg,+lags,+rr | -0.04528 | 22,195 | 4,522 | 0.006 |
| w_ALT, gprc_avg, NO lags, +relret         | -0.03963 | 36,261 | 6,283 | 0.002 |

Sign is **uniformly negative**. Adding the two weight lags (which require three consecutive panel
quarters) drops the gap-broken transitions: the lagged specs fall from ~36,300 to ~22,200 obs.

## Few-cluster inference and leverage (COMPUTED; cm_regression_result.json -> few_cluster_inference)

These are the load-bearing numbers, now computed in build/audit/cm_regression_recompute.py as
deterministic, seeded code and reproduced by the verifier (bootstrap_p_recomputed_matches=true,
leave_one_out_recomputed_matches=true). They are no longer asserted.

1. **Wild cluster bootstrap by quarter** (no-lags spec, G = 8 quarter clusters, Rademacher weights,
   null imposed via restricted residuals, **2000 reps, seed 42**):
   beta = -0.03540, naive cluster-quarter SE = 0.00699, t_obs = -5.061,
   **bootstrap two-sided p = 0.0480.**
   The naive cluster-quarter SE alone reports p ≈ 0.001, but with only 8 clusters CR1 over-rejects;
   the wild-cluster-t correction puts the honest p right on the 5% boundary. (The independently
   recomputed bootstrap p in the verifier equals 0.0480 to 1e-12 — deterministic under the seed.)

2. **Leave-one-quarter-out, HEADLINE spec (with lags):** full beta = -0.03826.
   drop 2019q3 -0.04633 · drop 2019q4 -0.04620 · drop 2020q1 **+0.00009** · drop 2020q2 **+0.00001** ·
   drop 2020q3 **+0.00005** · drop 2022q1 **-0.00002** · drop 2022q2 **+0.00671** · drop 2024q4 -0.03971.
   Dropping ANY of the five crisis-window quarters (2020q1/q2/q3, 2022q1, 2022q2) collapses beta to ~0
   and several flip slightly positive. This is because two weight lags need three consecutive panel
   quarters; removing one quarter breaks most lag chains (n falls 22,200 -> ~9k-15k) and the within-fund
   GPRC identification with it. That is a thin-panel signature, NOT robustness.

3. **Leave-one-quarter-out, NO-LAGS spec** (retains all remaining quarters; cleaner read):
   drop 2019q3 -0.03390 · drop 2019q4 -0.03476 · drop 2020q1 -0.05432 · drop 2020q2 -0.01169 ·
   drop 2020q3 -0.03116 · drop 2022q1 -0.03116 · drop 2022q2 -0.03851 · drop 2024q4 **+0.07286**.
   Even the more stable no-lags beta stays negative dropping any single quarter EXCEPT **2024q4, where
   it FLIPS SIGN to +0.073.** The negative depends on the single 2024q4 observation.

CORRECTION TO PRIOR DRAFT: the prior verdict asserted "dropping 2022q2 collapses beta -0.038 -> -0.008"
from an un-persisted ad-hoc run. The COMPUTED, verifier-reproduced headline value is **drop-2022q2 =
+0.00671** (collapse to ~0, slightly positive) — even more fragile than asserted. The recomputed numbers
are used here.

4. **Power diagnostic** (cm_regression_result.json -> power_diagnostic): cross-quarter SD of gprc_avg =
   0.291; after fund FE + controls the **residual GPRC SD identifying beta = 0.066 — only 23.5% of the
   within-fund variation survives** the macro state vector (oil corr +0.65, relative_returns -0.40 with
   GPRC across the 8 quarters absorb most of it). The 95% CI half-width on the 1-SD-GPRC effect
   (clustered-quarter) is 0.0072 against a point effect of -0.0111 — the band reaches near zero.

## Why INSUFFICIENT-POWER, not F3-LOADS, and not NO-SUBSTITUTION

- NOT **F3-LOADS**: F3-LOADS requires negative, significant, AND robust. The honest few-cluster
  inference (wild-bootstrap p = 0.0480) is on the 5% boundary, not decisively significant; and the
  beta is NOT robust — it collapses to ~0 (headline) or flips sign at drop-2024q4 (no-lags) under
  leave-one-quarter-out. The "robust" condition fails.
- NOT **NO-SUBSTITUTION**: the point estimate is negative and the CI does not exclude an economically
  meaningful negative; the pre-registration's binding anti-planting rule forbids relabeling a fragile,
  boundary, wide-uncertainty result as a clean null.
- Therefore **INSUFFICIENT-POWER**: the method is right; with ~8 non-contiguous national GPRC time
  points (≈5 effective lagged transitions, 6-8 clusters), the panel cannot resolve F3-LOADS from a
  near-null. The negative directional lean is reported, not promoted to a finding.

## Comparison to the pre-registered prediction

PRIMARY PREDICTION: **INSUFFICIENT-POWER** — "beta will be statistically insignificant with a 95% CI too
wide to exclude an economically meaningful negative … the estimator is the right one; the panel is thin."
Sign-agnostic; did NOT predict a negative beta.

**HELD.** The verdict matches the pre-registered primary prediction. New information beyond the
prediction: the point estimate landed negative in every spec (a directional lean toward F3 substitution),
and naive clustered SEs would have called it significant — but the COMPUTED wild-cluster bootstrap
(p = 0.048) and leave-one-quarter-out (collapse to ~0 / sign flip at one quarter) show the thin panel
cannot carry an F3-LOADS claim. The a-priori power-pessimism was correct; the sign lean does not, by
itself, refute it into F3-LOADS.

## What would resolve it (stated exactly, per the rule)

- **More quarters with within-fund continuity.** Binding constraint: ~8 non-contiguous national GPRC
  time points collapsing to ~5 effective lagged transitions and 6-8 clusters; one quarter (2024q4 in
  no-lags) can flip the sign. A contiguous run of N-PORT quarters (filling 2020q4-2021q4 and
  2022q3-2024q3) would raise the cluster count, stabilize the lag chains, and break the
  single-quarter dependence.
- **Higher CN coverage.** The tag reaches CN-nationality at ~0.34 of haven value; raising coverage
  tightens w_{f,t} and the residual GPRC variation identifying beta.

Until then the result is recorded INSUFFICIENT-POWER: the method is right, the sign leans negative,
the panel cannot resolve F3-LOADS from a near-null.

## Provenance and integrity

- Every series fetched and confirmed from the real publisher file (see cm_sources.json): GPRC_China =
  column GPRC_CHN in matteoiacoviello.com data_gpr_export.xls; VIX/dollar/oil from FRED fredgraph CSV
  (headers confirmed); relative_returns = MCHI adj-close TR minus ACWX adj-close TR (Yahoo v8), a
  documented free PROXY run WITH and WITHOUT.
- Fund-id (holder = cik|series_id) and fiscal_quarter re-attached to the tagged haven rows by the
  documented positional alignment and VERIFIED byte-identical (currency_value max abs diff 0.0;
  issuer_name/cusip/isin identical row-for-row) before use.
- beta and every inference statistic read from the estimator/bootstrap output; the wild cluster
  bootstrap and both leave-one-quarter-out sets are deterministic, seeded (seed 42), persisted in
  cm_regression_result.json, and reproduced by build/results/cm_regression_verify.json
  (bootstrap_p_recomputed_matches=true, leave_one_out_recomputed_matches=true). No spec selected for
  sign. Power reported honestly. No date, no bare probability, no hazard claim. No INCOMPLETE series.
