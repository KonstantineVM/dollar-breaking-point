# Converse–Mallucci Weight-Regression F3 Test — PRE-REGISTERED PREDICTION

**Timestamp: 2026-06-30 (written and committed BEFORE Part 1 — before the weight panel is built, before GPRC_China and the FRED controls are fetched, before the regression is run).**

This is a pre-registration, committed to the branch *before* estimation. The prediction below **may be
REFUTED by the result**, and any of the three endpoints is the finding. Do not spec-search toward a negative
β; do not dress an underpowered null as a clean null; run the regression and report β whatever its sign.

## Why this test exists

Every prior F3 test computed a within-holder **correlation**, which structurally cannot separate substitution
from co-movement — which is why aggregate, marginal-reconstruction, and per-security-tagged data all returned
~+0.5. Converse & Mallucci (NBER 32638) separate them with a portfolio-**weight regression** on a
country-specific risk shock, with fund fixed effects and a macro state vector absorbing the common component.
The substitution parameter is the coefficient β on China's geopolitical-risk index.

## The exact specification (headline)

w_{f,t} = α_f + β·GPRC_China_t + γ₁·w_{f,t−1} + γ₂·w_{f,t−2} + δ·relative_returns + θ·X_t + ε_{f,t}

- w_{f,t} = (CN-nationality haven value held by fund f at t) / (fund f's total haven value at t)
- X_t = [log VIX, broad dollar index, oil]
- α_f = fund fixed effects
- **Fund FE + X_t replace time FE** because GPRC_China is a single national series; absorbing the common
  component with the macro state vector (not time dummies) is CM's exact device — without it, time FE would
  collinearly absorb GPRC itself.
- β is the substitution parameter. Negative β = funds shift weight OUT of China-nationality exposure when
  Chinese geopolitical risk rises, net of co-movement = F3 substitution.

## Sign prediction with reasoning (sign-agnostic on β; power-pessimistic)

**Primary prediction: INSUFFICIENT-POWER** — β will be statistically insignificant with a 95% CI too wide to
exclude an economically meaningful negative. Reasoning (a-priori, before seeing the data): the tagged panel
spans only **8 fiscal quarters** (2019q3, 2019q4, 2020q1–q3, 2022q1, 2022q2, 2024q4), and they are
**non-contiguous** (gaps 2020q3→2022q1 and 2022q2→2024q4). With **fund FE absorbing all cross-sectional
variation**, β is identified purely off **within-fund time variation in a single national GPRC series** — i.e.
off ≈8 time points (fewer once the two weight lags w_{t−1}, w_{t−2}, which need three consecutive quarters,
drop the gap-broken transitions to ≈5). Four time-varying regressors plus two lags against ≈8 national time
points, with GPRC, VIX, dollar, and oil all co-moving over those same crisis quarters, will inflate β's SE
through near-collinearity. The estimator is the right one; the panel is thin.

**I do NOT predict a negative β.** The point estimate may land either side of zero; predicting its sign would
be spec-searching toward a result. The honest a-priori is about *power*, not sign.

## Decision rule (applied in Part 3, after the numbers)

- **F3-LOADS** — β NEGATIVE, significant, and robust across the robustness panel (alt denominator,
  quarter-avg vs end-quarter GPRC, with/without lags, fund- and quarter-clustered SE). Substitution is real
  and identified net of co-movement — the discriminant the correlation could not isolate. State the magnitude
  (Δweight per 1-SD GPRC_China rise). This would REFUTE the power-pessimistic primary prediction, and that
  refutation is the finding.
- **NO-SUBSTITUTION** — β ≈ 0 with a CI **tight enough to exclude an economically meaningful negative**.
  Substitution genuinely absent, established with an estimator that *can* detect it.
- **INSUFFICIENT-POWER** — CI **too wide to distinguish** F3-LOADS from NO-SUBSTITUTION. The method is right
  but the panel (≈8 non-contiguous quarters, CN coverage 0.34) cannot resolve it. State exactly what would
  (more quarters / higher coverage).

## A-priori power note (binding, anti-planting)

A null result here is, a priori, **at least as likely to be low-power as true-null**. INSUFFICIENT-POWER is a
**first-class outcome** and MUST NOT be relabeled NO-SUBSTITUTION. NO-SUBSTITUTION may be returned *only* if
the 95% CI is tight enough to exclude an economically meaningful negative β; otherwise the verdict is
INSUFFICIENT-POWER. The power (effective within-fund time d.o.f., the CI width relative to a meaningful effect
size) is to be reported explicitly and drive the adjudication.

## Anti-planting commitments

- β is read from the estimation output, **never hardcoded**. The pre-registered spec above is the headline;
  the alternatives are robustness, not cherry-picks. No spec is selected for its sign.
- Power is reported honestly; an underpowered wide-CI null is INSUFFICIENT-POWER, not NO-SUBSTITUTION.
- If GPRC_China or the FRED controls are unfetchable, that is recorded INCOMPLETE — no assumed series is
  substituted.

## Scope

STOPS after the prediction, panel, regression result, recompute script, and verdict. Does NOT re-tag the
operator, does NOT build a hazard, does NOT touch DP2–DP5, does NOT begin DP6. No date, no bare probability,
no hazard claim.
