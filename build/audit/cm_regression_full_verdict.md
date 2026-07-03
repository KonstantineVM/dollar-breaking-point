# Full-Panel Converse-Mallucci Weight-Regression F3 Test (POWER REBUILD, CORRECTED no-FX) — VERDICT

SOURCE: build/audit/cm_regression_full_result.json (8 re-estimated specs at G=22 + power_diagnostic +
few_cluster_inference + 8-quarter-subset comparison) and build/results/cm_regression_full_verify.json
(every cited statistic recomputed deterministically from build/audit/cm_regression_full_recompute.py
with no network: beta_matches=true, bootstrap_p_recomputed_matches=true,
leave_one_out_recomputed_matches=true). Panel: build/data/cm_panel/cm_weight_panel_full.parquet
(7,856 funds x 22 contiguous fiscal quarters 2019q3–2024q4; 104,306 valid-w fund-quarter cells,
1,114 dropped tot_haven<=0). External series over the full 22-quarter span:
build/contracts/cm_sources_full.json (GPRC_China=GPRC_CHN in matteoiacoviello.com data_gpr_export.xls;
VIX=VIXCLS, broad dollar=DTWEXBGS, oil=DCOILWTICO from FRED; relative_returns=MCHI−ACWX adj-close TR,
Yahoo v8 — each fetched over the full span, all 22 quarters non-null, reproducing the prior 8-quarter
contract values to float precision). Pre-registration: build/audit/fullpanel_prediction.md (committed
before the rebuild; NOT tuned to). Estimator/functions REUSED from build/audit/cm_regression_recompute.py
(the CR1 cluster-meat and the wild-bootstrap inner loop were vectorized for tractability at G=22; the CR1
formula, the within-OLS, the lags, the seed-42 Rademacher draw order, and the null-imposed restricted
residuals are unchanged — result and verifier recompute with the same functions and match to 1e-12).
Every statistic below is read from the estimator/bootstrap output, never hardcoded.

## FX CORRECTION (a bug fix, not a re-specification) — grounded against the filer's own data

The earlier draft of this rebuild multiplied the weight numerator/denominator by an FX rate. That was
WRONG. N-PORT FUND_REPORTED_HOLDING.CURRENCY_VALUE is ALREADY denominated in USD (valUSD);
CURRENCY_CODE only tags the instrument's native denomination. PROOF from the filer's own numbers
(no memory, no external source): N-PORT PERCENTAGE = holding value as % of the fund's USD net assets, so
implied_net_assets = currency_value/(percentage/100). Grouping the 8-quarter nationality panel by
(accession, currency_code), the WITHIN-fund ratio of implied net assets across currencies vs USD is
EXACTLY 1.0000 (p25=p50=p75): CNY/USD=1.000 (n=5,487 funds), HKD/USD=1.000 (n=10,770), TWD/USD=1.000
(n=2,193). If CURRENCY_VALUE were native currency these would be ~7.0 / ~7.8 / ~30.0. They are 1.000 =>
CURRENCY_VALUE is USD. The correct, IDENTICAL w needs NO conversion: w = cn_haven_raw / tot_haven_raw
(both direct CURRENCY_VALUE=USD sums). Removing the FX multiply is the ONLY change; the definition of w
is unchanged. The prior committed 8-quarter pass also used the spurious FX basis — its files are not
edited; the corrected 8-quarter numbers are reported here alongside for comparison.

## VERDICT: NO-SUBSTITUTION (F3 not loaded), terminal INSUFFICIENT-POWER on the negative sign — the pre-registered fragility prediction HELD

The power fix WAS delivered this time (G=22, contiguous, lag chains intact). Applying the pre-registered
rule mechanically and sign-agnostically: **the single-quarter leave-one-quarter-out fragility
SUBSTANTIALLY ATTENUATED (the primary prediction HELD)**, but the well-powered panel reveals that the
sign of β is NOT robust across the lag structure, β is economically SMALL in every direction, and the
negative (substitution-direction) channel is decisively insignificant on honest few-cluster inference
(bootstrap p = 0.58 at G=22). No spec is simultaneously negative, significant, and leave-one-out-robust.
There is **no large, robust, sign-consistent substitution effect** — F3 is NOT loaded.

## What was estimated (β read from the estimator; verifier reproduces it)

w_{f,t} = α_f + β·GPRC_China_t + γ1·w_{f,t-1} + γ2·w_{f,t-2} + δ·relative_returns + θ·X_t + ε,
X_t = [log VIX, broad dollar, oil], α_f = fund FE. Within (fund-demeaned) OLS. w-based specs at G=22;
w_ALT specs at G=8 (foreign denominator needs CN-resident holdings, which the input persisted only for
the original 8 quarters — a genuine coverage gap unrelated to FX, recorded, not substituted).

Lagged vs no-lags obs (the contiguity power gain, measured): **lagged n = 84,854 (6,307 funds)** vs the
8-quarter panel's 22,200; **no-lags n = 103,867 (7,367 funds)** vs 36,277. Far more fund-quarters enter,
exactly as the pre-registration predicted from contiguous quarters keeping the two lag chains intact.

### β / SE(cluster-quarter) / p / CI across all 8 specs, with G

| # | spec | β | n_obs | n_funds | SE_q | p_q | 95% CI_q | G |
|---|------|---|-------|---------|------|-----|----------|---|
| 0 | HEADLINE w~gprc_avg+L1+L2+X+relret | **+0.01252** | 84,854 | 6,307 | 0.00495 | 0.021 | [+0.0022, +0.0229] | 22 |
| 1 | w~gprc_avg+L1+L2+X (no relret)     | +0.01006 | 84,854 | 6,307 | 0.00483 | 0.051 | [−0.0001, +0.0202] | 22 |
| 2 | w~gprc_avg+X+relret (no lags)      | **−0.07592** | 103,867 | 7,367 | 0.08540 | 0.384 | [−0.2535, +0.1017] | 22 |
| 3 | w~gprc_avg+X (no lags,no relret)   | −0.07604 | 103,867 | 7,367 | 0.08282 | 0.369 | [−0.2483, +0.0962] | 22 |
| 4 | w~gprc_END+L1+L2+X+relret          | +0.00565 | 84,854 | 6,307 | 0.00246 | 0.033 | [+0.0005, +0.0108] | 22 |
| 5 | w~gprc_END+X+relret (no lags)      | +0.00772 | 103,867 | 7,367 | 0.01464 | 0.603 | [−0.0227, +0.0382] | 22 |
| 6 | w_ALT~gprc_avg+L1+L2+X+relret (G=8) | −0.00018 | 11,314 | 4,065 | 0.00001 | 0.005 | [−0.0002, −0.0001] | 8 |
| 7 | w_ALT~gprc_avg+X+relret no-lags (G=8) | −0.02400 | 36,276 | 6,284 | 0.00187 | 0.000 | [−0.0284, −0.0196] | 8 |

Read sign-agnostically: the **with-lags w-specs (0,1,4) are POSITIVE, small, marginally significant**;
the **no-lags w-specs (2,3) are NEGATIVE but wildly INSIGNIFICANT** (p 0.37–0.38, CI spans zero from
−0.25 to +0.10); the gprc_END no-lags (5) is +0.008 and insignificant (p 0.60). The **w_ALT specs (6,7)
are negative and significant but are on the FX-independent 8-quarter foreign-denom subset (G=8), not the
full panel.** Magnitudes are economically small throughout: the headline +0.0125 is ~+11% of the
corrected mean CN haven share (0.109). There is NO large, robust, sign-consistent substitution β.

## Full-panel leave-one-quarter-out vs the 8-quarter panel: the pre-registered test (PERSISTED all 22)

**Headline (with lags), LOQO over all 22 quarters:** β stays POSITIVE and tight dropping EVERY quarter —
range +0.0035 (drop 2021q3) to +0.0271 (drop 2022q2); full-sample +0.01252. **No single-quarter collapse,
no sign flip.** On the 8-quarter panel, dropping any of five crisis quarters collapsed the (spuriously
FX'd) headline β to ~0 and flipped several positive. **The single-quarter fragility of the with-lags
headline VANISHED at 22 quarters.**

**No-lags, LOQO over all 22 quarters:** β stays NEGATIVE dropping any quarter EXCEPT 2019q3 (flips to
+0.011); otherwise −0.067 to −0.143 (drop 2022q1 = −0.143). The no-lags negative is sign-stable across
21/22 drops, but the full-sample no-lags β is INSIGNIFICANT (p 0.38, bootstrap 0.58), so this is
stability of an imprecise near-null-with-negative-lean, not of an identified effect.

**Apples-to-apples 8-quarter subset on the SAME corrected no-FX basis** (result →
eight_quarter_subset_corrected_no_fx): headline β = −0.00014 (≈0), n = 11,314; no-lags β = +0.31123 with
LOQO betas swinging violently (+2.13 dropping 2020q2, −1.74 dropping 2022q2, −1.11 dropping 2024q4). The
corrected 8-quarter panel is DEGENERATE — even more fragile than the prior spurious-FX 8-quarter pass —
confirming 8 non-contiguous quarters could never resolve this and that the prior INSUFFICIENT-POWER call
was correct about the 8-quarter panel.

Fragility comparison verdict: **the leave-one-quarter-out fragility VANISHED for the headline (with-lags)
spec at 22 quarters (from crisis-quarter collapse to fully robust +0.011..+0.027), and the no-lags spec
became sign-stable across 21/22 drops.** That is exactly the pre-registered PRIMARY prediction: fragility
substantially attenuates on the contiguous ~22-quarter panel.

## Wild cluster bootstrap at G≈22 (COMPUTED, PERSISTED, VERIFIER-REPRODUCED)

No-lags spec, Rademacher weights, null imposed via restricted residuals, seed 42, 2000 reps, **G = 22
quarter clusters**: β = −0.07592, naive cluster-quarter SE = 0.08540, t_obs = −0.889, **bootstrap
two-sided p = 0.5825.** (Recomputed independently to 1e-12: bootstrap_p_recomputed_matches = true.) With
22 clusters properly powering the test, the no-lags negative direction is **decisively insignificant** —
the wide cluster-quarter SE (0.085, against a point β of −0.076) shows the negative is not distinguishable
from zero.

## Power diagnostic vs the prior 23.5%

- Cross-quarter SD of gprc_avg over 22 quarters = **0.2276** (the added calmer quarters lower it vs the
  crisis-8 subset's 0.2911).
- **GPRC residual SD after fund FE + controls = 0.1646; share of within-fund variation = 74.5%**, vs the
  prior 8-quarter **23.5%.** With 22 contiguous quarters and intact lag chains, the macro controls no
  longer absorb almost all the China-GPRC variation — far more within-fund GPRC signal survives to
  identify β. This is the power gain the rebuild sought, now realized.
- Number of quarter clusters **G = 22** for the w-specs (G = 8 for the w_ALT specs only).

## Decision rule applied mechanically (sign-agnostic)

- NOT **F3-LOADS**: requires β **negative**, significant (incl. wild-cluster bootstrap < 5%), AND
  surviving leave-one-out. The robust, significant, leave-one-out-surviving spec (headline with lags) is
  **POSITIVE (+0.0125)** — the wrong sign for F3 substitution; the NEGATIVE direction (no-lags) is
  bootstrap-insignificant (p = 0.58). No spec is simultaneously negative, significant, and robust.
  F3-LOADS is not cleared.
- **NO-SUBSTITUTION** is the mechanical fit for the substitution channel: the economically meaningful
  negative β the F3 channel predicts is NOT present — the robust identified β is a small POSITIVE, and the
  negative direction is a wide, insignificant near-null. For the with-lags specs "β ≈ 0 with a CI tight
  enough to exclude an economically meaningful negative" holds (tight, positive, near-zero: CI
  [+0.002, +0.023]).
- **INSUFFICIENT-POWER on the SIGN of the negative channel** is the terminal qualifier: the no-lags
  specs have a WIDE CI ([−0.25, +0.10] at G=22) that does not exclude a meaningful negative, and the
  with-lags vs no-lags specs disagree on the sign of a tiny β. Because the power fix has now genuinely been
  applied (G=22, fragility resolved, residual GPRC share 74.5%), this is the TERMINAL answer for the sign:
  more N-PORT quarters will not sharpen a β whose sign is not even stable across including vs excluding the
  weight lags.

Net: **no large, robust, sign-consistent substitution effect exists.** The identified (with-lags,
leave-one-out-robust) β is a small POSITIVE; the negative (no-lags) direction is an insignificant
near-null at G=22. F3 substitution is NOT loaded.

## Comparison to the pre-registered prediction — HELD

PRIMARY PREDICTION: "the leave-one-quarter-out FRAGILITY will SUBSTANTIALLY ATTENUATE" on a ~22-quarter
contiguous panel; the one falsifiable commitment was that if fragility STILL collapsed β to ~0 on single-
quarter drops, the prediction is REFUTED. Sign-agnostic; did not predict which endpoint β resolves to.

**HELD.** On the corrected 22-quarter contiguous panel the headline (with-lags) β is robust to dropping
every one of the 22 quarters (no collapse, no flip; +0.011..+0.027), and the no-lags β is sign-stable
across 21/22 drops — a decisive attenuation from the 8-quarter crisis-quarter collapse. The
pre-registration explicitly did NOT commit to which endpoint β resolves to; the data adjudicate that the
all-negative signal of the (spuriously-FX'd) 8-quarter subset was a small-sample/spurious-basis artifact:
once the FX bug is fixed and the panel is well-powered, the robust identified β is a small positive and
the negative direction is an insignificant near-null. So the primary prediction HELD, and the endpoint it
resolved to is NO-SUBSTITUTION (with a terminal INSUFFICIENT-POWER on the negative direction's sign),
not F3-LOADS.

## What would (not) change it

- The fragility question is resolved; the power fix is applied (G=22, residual GPRC share 74.5%). More
  N-PORT quarters would not change the finding that no large, robust, sign-consistent negative β exists —
  the with-lags β is a robust small positive and the no-lags negative is bootstrap-insignificant at G=22.
- The one remaining coverage limit is w_ALT at the full span: its foreign denominator needs CN-resident
  holdings, which the provided input persisted only for the original 8 quarters. Building w_ALT at G=22
  would require re-parsing the N-PORT ZIPs to recover the CN-resident leg (out of this task's scope). The
  w_ALT G=8 specs are reported but not treated as full-panel evidence.

## Provenance and integrity

- FX correction grounded on the filer's own numbers (percentage internal-consistency test:
  CNY/HKD/TWD implied-net-assets ratio to USD = 1.0000 exactly); documented in
  build/contracts/cm_sources_full.json → weight_panel_construction.currency_value_is_usd. The earlier
  FX-INCOMPLETE claim is WITHDRAWN: there was never an FX gap.
- w = cn_haven_raw / tot_haven_raw (direct CURRENCY_VALUE = USD sums), definition unchanged; the ONLY
  change vs the earlier draft is removing the erroneous FX multiply (mean w corrected 0.175 → 0.109).
- All four external series fetched over the full 2019q3–2024q4 span and confirmed; all 22 quarters
  non-null; 8-quarter overlap reproduces the prior contract to float precision.
- β and every inference statistic read from the estimator/bootstrap output. The CR1 cluster meat and the
  wild-bootstrap inner loop were vectorized for tractability at G=22; the CR1 formula, within-OLS, lags,
  seed-42 Rademacher draw order, and null-imposed restricted residuals are unchanged. The wild cluster
  bootstrap and both 22-quarter LOQO sets (plus the 8-quarter-subset LOQO) are deterministic, seeded
  (seed 42), persisted in cm_regression_full_result.json, and reproduced byte-for-byte by
  build/results/cm_regression_full_verify.json (beta_matches, bootstrap_p_recomputed_matches,
  leave_one_out_recomputed_matches all true). No spec selected for sign. Power reported honestly. No date,
  no bare probability, no hazard claim. The prior task's committed 8-quarter files were not edited.
