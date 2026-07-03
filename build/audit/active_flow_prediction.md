# Active-Flow F3 Test — PRE-REGISTERED PREDICTION

**Timestamp: 2026-07-01 (committed BEFORE Part 2 estimation — the active-flow panel exists and is
reconstruction-verified (Part 1), but the active-flow regression has NOT been run. This predicts the
REGRESSION RESULT, which does not yet exist.)**

Pre-registration, committed before estimation. The prediction below **may be REFUTED**, and any of the three
endpoints (plus the already-resolved feasibility branch) is a valid finding. Do not spec-search toward a
negative on active flow; do not dress an underpowered or outlier-driven result as a clean result; run the
regression and report the coefficient whatever its sign.

## What this test does and why

Every prior F3 test used portfolio **weight** as the dependent variable and returned a null (GPR +0.0125;
sanctions +0.0177). But a weight = **manager decision + valuation**. Chinese ADRs fell ~50%+ over 2021–2023,
so a weight can move (or stay flat) from **price**, not from the manager selling. F3 is a claim about **active
reallocation** (a manager decision). This test decomposes holdings into **active flow** (constant-price
reallocation = decision) vs **passive** (valuation), and re-runs the sanctions test on **active flow**, so the
valuation component is removed *by construction* rather than controlled.

Feasibility (Part 0, already resolved from real data): **branch A** — N-PORT `BALANCE`/`UNIT` are populated on
99.97% of haven-CN value; the constant-price decomposition `active = (shares_t − shares_{t−1})·price_{t−1}` is
built directly and reconstructs Δvalue to floating precision (max abs 5.96e-08 USD).

## The specification

Same design as the weight-based sanctions test (`build/audit/sanctions_shock_result.json`), with the
**dependent variable replaced by active net flow into CN-nationality haven securities** (normalized to a rate):

active_flow_rate_{f,t} = α_f + β·SANCTIONS_t + λ·REGULATORY_t + (lagged active-flow terms) + δ·relative_returns
+ θ·[log VIX, broad dollar, oil] + ε_{f,t}

- SANCTIONS_t = the grounded sanctions treatment (Feb-2022 freeze `sanc_freeze_post`; Dec-2023 EO 14114 as the
  second event). REGULATORY_t = the delisting/HFCAA control. α_f = fund FE; no time FE (CM's device).
- **F3 substitution on active flow = funds actively SELL CN-nationality securities as sanctions risk rises =
  NEGATIVE β**, net of valuation (removed by construction, not controlled).
- The load-bearing comparison, as in the weight test: β **WITH vs WITHOUT** the regulatory control.

## Normalization / outlier discipline (stated before the estimate; anti-artifact)

The active-flow rate normalized by *lagged* total haven value explodes for funds newly entering the haven
space (near-zero denominator: |rate|>5 in 96 fund-quarters, tied to a lagged base ~74× below typical). This is
a mechanical artifact, not signal. The estimate MUST be reported across a disclosed, defensible outlier
treatment — winsorization at symmetric percentiles AND/OR an average-base normalization (÷ mean of t−1 and t
haven value, which is well-behaved: sd 0.30 vs 874) AND/OR a lagged-base floor — and the sanctions coefficient
reported **across** these so the finding is not an artifact of the outlier handling. The treatment is fixed for
being outlier-robust, **not** tuned toward a null or a negative; report with and without.

## Decision rule (applied in Part 3, after the numbers)

- **F3-LOADS-ON-ACTIVE-FLOW** — active-flow sanctions β NEGATIVE, significant (incl. wild-cluster bootstrap by
  quarter), robust across event-window and normalization definitions, SURVIVES the regulatory control AND
  leave-one-quarter-out. F3 was real and **valuation-masked** — every prior weight test missed it because it
  measured decision+price. This REOPENS identification; state magnitude and what reopens.
- **NO-F3-ON-ACTIVE-FLOW** — active-flow β ≈ 0 / positive with adequate power (a CI tight enough to exclude an
  economically meaningful negative on the honest inference instrument). Managers did **not** actively
  reallocate; the weight null was NOT a valuation artifact; F3 is absent on the manager-decision quantity.
  TERMINAL, and stronger than the weight null because it rules out the valuation-masking explanation.
- **INSUFFICIENT-POWER** — CI too wide (on the honest instrument) to distinguish; state what would resolve it.

## The falsifiable prediction (sign-agnostic; null-plausible, not null-favored)

> **Primary prediction: NO-F3-ON-ACTIVE-FLOW or INSUFFICIENT-POWER.** A-priori (before the estimate): the
> weight tests were powered nulls, and the most likely reason the weight showed no substitution is that the
> managers did not actively sell — in which case active flow is *also* null. Moving from weight to active flow
> plausibly does NOT reveal a hidden negative. I do NOT, however, favor the null: the valuation-masking
> hypothesis is real and testable (Chinese ADRs did fall ~50%+, so a genuine sell could have been hidden in the
> weight by the offsetting price drop), and if it is true the active-flow β turns negative where the weight β
> was positive. That is precisely what the decomposition adjudicates.
>
> **The one falsifiable commitment:** if the active-flow sanctions β is negative, bootstrap-significant,
> robust across event-window AND normalization definitions, survives the regulatory control, and survives
> leave-one-quarter-out — i.e. the weight→active-flow move flips the sign from the weight's +0.0177 to a
> robust negative — the primary prediction is REFUTED and the verdict is **F3-LOADS-ON-ACTIVE-FLOW** (F3 was
> valuation-masked). I do not predict the sign; a positive or a null active-flow β is equally admissible.

## Anti-planting commitments

- β and every inference statistic **read from the estimator/bootstrap output, never hardcoded.**
- The active-flow DV is the constant-price decomposition **kept exactly as the task defined active flow**; the
  reconstruction gate (active+passive = Δvalue, error ~0) already guards against a manufactured split.
- The outlier/normalization treatment is disclosed and reported across variants; it is not selected for sign.
- The wild cluster bootstrap and leave-one-quarter-out are **computed, persisted, and verifier-reproduced** —
  never asserted (the standing lesson).
- The KEY diagnostic — whether weight→active-flow changed the sign/significance — is reported plainly, so a
  null is shown to be a genuine no-reallocation result and not a decomposition that did nothing (Part 1 already
  shows 2,678 fund-quarters where active flow and weight change have opposite sign — the decomposition does
  move).

## Scope

STOPS after the prediction, the feasibility artifact, the active-flow panel, the regression result, the
recompute script, and the verdict. Does NOT re-tag the operator, does NOT build a hazard, does NOT touch
DP2–DP5, does NOT begin DP6. No date, no bare probability, no hazard claim.
