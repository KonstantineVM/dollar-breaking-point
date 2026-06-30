# Full-Panel CM Re-Estimation (Power Rebuild) — PRE-REGISTERED PREDICTION

**Timestamp: 2026-06-30 (committed BEFORE Part 1 — before the full N-PORT panel is built, before GPRC/FRED
are re-merged, before the regression is re-run).**

Pre-registration, committed to the branch *before* the rebuild. The prediction below **may be REFUTED**, and
any of the three endpoints is the finding. This is a **POWER rebuild, NOT a re-specification**: only the
quarter count changes. Do not spec-search; compute the bootstrap and leave-one-quarter-out for real (the
prior pass's integrity-critic BLOCK was an asserted-not-computed leave-one-out — that must not recur).

## What changed and what did NOT

The prior Converse–Mallucci weight regression returned **β negative in all 8 specifications** (the F3
substitution direction) but **INSUFFICIENT-POWER**: fragile because the panel was only **8 non-contiguous
quarters**, and leave-one-quarter-out collapsed β to ~0 when any of five crisis quarters was dropped (and the
no-lags β flipped sign dropping 2024Q4). The binding constraint was identified as **POWER**. N-PORT spans
**2019Q4 → present (~22 public quarters)**, not 8 — the 8 were a tractability subset. This rebuild uses the
**maximum achievable temporal extent** and re-runs the IDENTICAL spec.

**IDENTICAL to `build/audit/cm_regression_prediction.md` (committed 8e2ae9f), quoted verbatim:**

> w_{f,t} = α_f + β·GPRC_China_t + γ₁·w_{f,t−1} + γ₂·w_{f,t−2} + δ·relative_returns + θ·X_t + ε_{f,t},
> X_t = [log VIX, broad dollar index, oil], α_f = fund fixed effects.
> w_{f,t} = (CN-nationality haven value held by fund f at t) / (fund f's total haven value at t).
> Fund FE + X_t replace time FE because GPRC_China is a single national series (CM's device).
> β is the substitution parameter. Negative β = funds shift weight OUT of China-nationality exposure when
> Chinese geopolitical risk rises, net of co-movement = F3 substitution.

Unchanged: estimator (within/fund-demeaned OLS), dependent variable, controls, fund FE, the two weight lags,
relative_returns, the robustness set (alt denominator; quarter-avg vs end-quarter GPRC; with/without lags;
cluster by fund and by quarter; wild cluster bootstrap by quarter, **same seed 42, 2000 reps**), and the
decision rule. **Only the number of quarters changes** (8 → target ~22, 2019Q4–latest available).

## Target span and the load-bearing power quantity

Target: **2019Q4 → latest available N-PORT quarter (~22 quarters)**. If the full 22 is infeasible in one
pass, the maximum contiguous span achievable (a 16–18 quarter panel is still a major power gain); the
provenance will list exactly which quarters are in/out, and report achieved-vs-22. **No silent fall-back to
the 8-quarter panel.**

The power quantities that matter: the **number of quarter clusters G** (was 6–8; target ~18–22) and the
**within-fund GPRC variation surviving the macro controls** (was 23.5%). With contiguous quarters, the two
weight lags no longer drop gap-broken transitions, so far more fund-quarters enter the lagged specs.

## The prediction (falsifiable; sign-agnostic on β)

> **Primary prediction: the leave-one-quarter-out FRAGILITY will SUBSTANTIALLY ATTENUATE.** On the
> 8-quarter panel, dropping any single crisis quarter collapsed β to ~0 because each quarter was ~1/8 of the
> identification and the two lags broke on the gaps. On a ~22-quarter contiguous panel, no single quarter is
> more than ~1/22 of identification, the lag chains stay intact, and G rises to ~18–22 (so the wild cluster
> bootstrap is far better powered). I therefore expect the single-quarter collapse to LARGELY DISAPPEAR.
>
> **I do NOT predict which endpoint β resolves to.** Whether the now-robust β is (i) negative-and-significant
> surviving leave-one-out → **F3-LOADS**, or (ii) ~0 with a tight CI → **NO-SUBSTITUTION**, depends on whether
> the all-8-specs negative was real signal or a small-sample artifact — that is precisely what more data
> adjudicates, and I commit to neither. The negative appearing in all 8 specs of the subset is *some* evidence
> it is not pure noise, but I do not favor F3-LOADS.
>
> **The one falsifiable commitment:** if, on the full ~22-quarter panel, the leave-one-quarter-out STILL
> collapses β to ~0 when single quarters are dropped (fragility persists despite the power fix), the primary
> prediction is REFUTED, and the verdict is **INSUFFICIENT-POWER as the TERMINAL answer** for this
> identification — the power constraint was directly addressed and still cannot resolve it.

## Decision rule (unchanged; applied in Part 4)

- **F3-LOADS** — β negative, significant (incl. the wild-cluster bootstrap below 5%), AND **survives
  leave-one-quarter-out** (no single quarter collapses it). The power constraint is broken; substitution is
  real and identified net of co-movement; state the magnitude.
- **NO-SUBSTITUTION** — β ≈ 0 with a CI tight enough to exclude an economically meaningful negative.
- **INSUFFICIENT-POWER** — β still fragile on the full panel. Because the power fix has been applied, this
  becomes the **TERMINAL** answer; state what (if anything) further could change it, and compare the
  leave-one-out fragility explicitly to the 8-quarter panel (improved / vanished / persisted).

## Anti-planting commitments

- The headline is the prior pre-registered spec on **more data** — NOT a new spec. A β significant only under
  a new spec is **spec-search** and is reported as such, never as the result.
- The wild cluster bootstrap and leave-one-quarter-out are **computed, persisted, and verifier-reproduced** —
  never asserted (the exact prior BLOCK).
- β read from the estimator, never hardcoded. Power reported honestly: an underpowered-persists result is
  INSUFFICIENT-POWER, not NO-SUBSTITUTION; a boundary-significant β is not inflated to F3-LOADS without the
  leave-one-out surviving.
- The crosswalk tagging (R1–R4) is REUSED verbatim from the prior pass, not re-derived, so CN coverage is
  consistent across the added quarters.

## Scope

STOPS after the prediction, full panel, weight panel, regression result, recompute script, and verdict. Does
NOT build a hazard, does NOT touch DP2–DP5, does NOT begin DP6. No date, no bare probability, no hazard claim.
