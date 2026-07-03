# Active-Flow F3 Test — VERDICT (Part 3)

SOURCE: build/audit/active_flow_result.json (estimation output) + build/results/active_flow_verify.json
(verifier: beta_matches=true, bootstrap_p_recomputed_matches=true, leave_one_out_recomputed_matches=true,
byte-reproducible, seed 42) + build/data/nport/active_flow_panel.parquet (the active-flow DV: constant-price
decomposition, valuation removed by construction) + build/audit/active_flow_feasibility.json (branch A,
reconstruction exact to 5.96e-08 USD) + build/data/sanctions/sanctions_treatment_panel.csv (grounded
sanctions treatment + regulatory controls). Coefficients read from the estimator at design position 0, never
hardcoded. Prediction served (committed BEFORE this estimate): build/audit/active_flow_prediction.md.

SIGN CONVENTION (fixed in Part 1, not tuned here): NEGATIVE sanctions β = funds ACTIVELY SOLD CN-nationality
haven securities as sanctions risk rose = F3 substitution. F3 = a robustly negative, significant β.

## VERDICT: INSUFFICIENT-POWER (leaning toward NO-F3, but the honest instrument does not exclude a meaningful negative)

SUBJECT-DRIVER: Under the pre-registered decision rule applied sign-agnostically, the active-flow sanctions β
is not a robust significant negative (fails F3-LOADS-ON-ACTIVE-FLOW), but the honest few-cluster instrument's
confidence interval is too wide, and the sign is not stable across the with/without-control and DV1/DV2/DV3
normalization axes, to reach the stronger NO-F3-ON-ACTIVE-FLOW endpoint. The result does not distinguish "no
active reallocation" from "a modest sell the test cannot resolve." BOUNDARIES: fund-FE within-OLS, no time FE,
2019q3-2024q4, G=22 quarters (G=21 on the honest no-lags bootstrap design); CN-nationality haven active net
flow as DV. FALSIFIER: a larger active-flow panel (more funds/quarters) or a lower-variance normalization that
tightens the honest wild-bootstrap CI on the WITH-control DV1 spec to exclude either 0 or an economically
meaningful negative would move this to NO-F3-ON-ACTIVE-FLOW or (if it excludes 0 on the negative side)
F3-LOADS-ON-ACTIVE-FLOW.

### Why not F3-LOADS-ON-ACTIVE-FLOW
The rule requires the active-flow β to be NEGATIVE, significant INCLUDING the wild-cluster bootstrap, robust
across event-window AND normalization definitions, surviving the regulatory control AND leave-one-quarter-out.
- Honest instrument (G=21 wild cluster bootstrap by quarter, Rademacher, null imposed, seed 42, 2000 reps) on
  the headline DV1 WITH-control spec: β=−0.012354, t=−1.408, **bootstrap p = 0.1595** — not significant at 5%.
- Cluster-quarter p on the lagged headline DV1 WITH-control spec: **0.3307**; 95% CI [−0.02857, +0.01015]
  spans zero. Cluster-fund p=0.18. Not significant on any honest SE.
- Not robust across normalization: DV1 WITHOUT-control β=−0.0017 (p=0.93), DV2 WITHOUT +0.0019 (p=0.91),
  DV3 WITHOUT −0.0020 (p=0.87) — the sign flips across DV1/DV2/DV3 in the without-control specs. The negative
  sign appears only WITH the regulatory control (DV1 −0.0092, DV2 −0.0049, DV3 −0.0079), and is insignificant
  in all three. A sign that is present only after adding a control that is r=0.828 collinear with the treatment
  is exactly the fragility the pre-registration flagged; it does not satisfy "robust across normalization."
- LOQO (DV1 WITH control): the negative β is not stable — dropping 2021q2 pushes β to −0.0383, dropping 2022q1
  or 2022q2 flips it POSITIVE (+0.0025, +0.0038). A sign that flips on single-quarter deletion is not a
  survived-LOQO negative.

### Why not the stronger NO-F3-ON-ACTIVE-FLOW
That endpoint requires the honest CI to be tight enough to EXCLUDE an economically meaningful negative. It is
not. On the honest instrument the WITH-control DV1 point estimate is −0.0092 to −0.0124 and the cluster-quarter
95% CI reaches −0.0286 (≈0.11 of the DV1 sd of 0.266) — an economically non-trivial active sell is inside the
interval. The bootstrap p=0.16 fails to reject the null, but a p that fails to reject is not a CI that excludes
the alternative. So NO-F3 (which would be the strong, terminal "managers did not reallocate, weight null was
not a valuation artifact" claim) is NOT supported: the test cannot rule out a modest hidden sell. Calling this
NO-F3 would overstate power. The primary pre-registered prediction named NO-F3-ON-ACTIVE-FLOW *or*
INSUFFICIENT-POWER; the honest reading is the latter.

## THE KEY COMPARISON: does moving from weight to active flow change the sanctions coefficient?

YES — the sign flips, but the significance does not appear. Read plainly:
- Weight DV (build/audit/sanctions_shock_result.json): sanctions β = **+0.017661** WITH control / +0.018507
  WITHOUT, POSITIVE, cluster-quarter p<0.001 but honest wild-bootstrap p=0.27 (a powered null on
  *substitution*; the positive weight move is not a substitution signal on the honest instrument).
- Active-flow DV (valuation removed by construction): DV1 β = **−0.009211** WITH control / −0.001698 WITHOUT;
  DV2 −0.004894 / +0.001898; DV3 −0.007896 / −0.002012. Honest wild-bootstrap p = **0.1595** (G=21).

So decomposing weight into active flow + valuation **removed the positive weight coefficient** (+0.0177) and
left a small, insignificant, sign-unstable coefficient centered near zero (WITHOUT control) to modestly
negative (WITH control). The decomposition genuinely moved the estimate — the +0.0177 weight coefficient does
NOT survive the decomposition (it moves to an insignificant, sign-unstable estimate centered near zero),
consistent with — but NOT established as — a substantial valuation artifact, since neither the weight
coefficient (+0.0177, bootstrap p=0.27) nor the active-flow coefficient (−0.0092, bootstrap p=0.16) is
significant on the honest instrument; Part 1's 2,678 opposite-sign fund-quarters confirm the decomposition is
not inert. But the move did NOT reveal a robust hidden negative: the
active-flow coefficient is not bootstrap-significant, not normalization-robust, and not LOQO-stable. The
decomposition **flipped the point sign (with control) and widened/dissolved the result**, rather than
preserving the positive weight finding or establishing a clean negative.

## Comparison to the Part-0 pre-registered prediction: HELD

The pre-registration's primary prediction was **NO-F3-ON-ACTIVE-FLOW or INSUFFICIENT-POWER**, with the single
falsifiable commitment that a robust, bootstrap-significant, normalization-robust, control-surviving,
LOQO-surviving negative would REFUTE it and force F3-LOADS-ON-ACTIVE-FLOW. That falsifiable condition is NOT
met (bootstrap p=0.16; sign flips across DV1/DV2/DV3 without-control and on LOQO deletions of 2022q1/q2). The
verdict lands on INSUFFICIENT-POWER, which is one of the two named primary outcomes. **Prediction HELD.** The
valuation-masking hypothesis is not confirmed: the active-flow coefficient turned modestly negative only under
the collinear regulatory control and never significantly, so the weight null is not shown to have hidden a real
sell — but neither is it proven clean, because the honest CI does not exclude a modest negative.

## Diagnostics (all read from the estimator)

- Collinearity: corr(sanc_freeze, reg_crackdown) across 22 quarters = 0.8281 (Part-1 r=0.828 carried); VIF of
  the treatment in the DV1 WITH-control within design after FE = 5.481 (sqrt≈2.34 SE inflation). The negative
  β appears only once this collinear control is added — a reason to distrust the WITH-control sign.
- Power: the treatment's within-fund variation surviving FE + controls is ~43% of its within-fund sd
  (residual_share NO_reg=0.4317, WITH_reg=0.4271); DV standard deviations DV1=0.266, DV2=0.300, DV3=0.196. At
  G=22/21 quarter clusters the honest instrument has limited power to resolve a coefficient of order 0.01
  against a DV sd of ~0.2-0.3.
- Merge (verified): treatment→panel 22/22 quarters matched, 0 orphans either side; macro/relative_returns
  matched on 34,315 of 36,547 fund-quarter rows (2,232 orphan, 104 active-flow holders not in the CM panel);
  those orphan rows drop from any spec requiring relative_returns (the headline spec does). DV1 estimation uses
  32,546 non-null DV cells before the relative_returns/lag requirements, 24,360 obs / 2,275 funds in the fitted
  headline spec.

No date. No bare probability. No hazard claim. No deferral. The three F3-decision endpoints were all admissible
on entry; the estimator selected INSUFFICIENT-POWER by the pre-registered rule.
