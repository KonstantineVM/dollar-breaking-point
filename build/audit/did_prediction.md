# Diff-in-Diff / Event-Study F3 Test (reserve-freeze) — PRE-REGISTERED PREDICTION

**Timestamp: 2026-07-01 (committed BEFORE Part 0 builds or tests any control group, and BEFORE the DiD is
estimated — before any control's pre-trend is known, before the DiD β exists).**

Pre-registration, committed first. The prediction below **may be REFUTED**, and any of the four endpoints is a
valid finding. The control is selected by a **pre-trend rule fixed here** (flat pre-trend), NOT by the DiD
coefficient it produces; all candidate controls' pre-trends are reported so the selection is auditable.

## Why this estimator, and why it is not a new shock

Every prior F3 test used a **continuous-shock panel regression** with leave-one-quarter-out robustness. For a
**discrete sanctions event** (the Feb-2022 = 2022q1 Russian reserve freeze, read across to China), LOQO is the
WRONG robustness check: dropping the event quarters removes the identifying variation, so a genuine event
effect is made to look "fragile." This runs the **correct estimator** — a difference-in-differences / event
study around 2022q1 on the valuation-stripped **active flow** already built (`active_flow_panel.parquet`), with
a **pre-trend test**. Same event, same data; the right estimator for the structure F3 actually has.

Feasibility already scoped from disk (not assumed): 10 pre-freeze quarters (2019q3–2021q4) and 12 post
(2022q1–2024q4) — ample for a pre-trend test.

## The design (fixed here)

Treated group = US-fund holdings of **CN-nationality haven** securities (the crosswalk-tagged CN group).
Candidate controls, each tested for a **parallel pre-trend** over 2019q4–2021q4:
- **C1** = non-CN haven securities (same CYM/HKG/VGB residence, non-Chinese parent — mostly Cayman
  CLO/structured credit). A-priori likely rates-driven and NON-parallel — tested, not assumed.
- **C2** = non-haven **EM equity** (e.g. KR/TW/IN/BR and similar EM-resident equity) — the same EM-equity risk
  class, the cleaner parallel-trend candidate.
- **C3** = developed-market non-US equity — a broad foreign-equity control (if constructible).

**Control-selection rule (fixed, anti-cherry-pick):** the control is the candidate with a genuinely FLAT
pre-trend (the trend×group interaction over the pre-period ~0 and insignificant, and the event-study leads
jointly insignificant). ALL candidates' pre-trends are reported, not just the chosen one. If NO candidate
parallels the treated group, DiD is **NOT-IDENTIFIED** and that is the finding — no β is reported from a broken
design.

Estimator (only if a valid control exists):
active_flow_{f,g,t} = α_f + λ_t + β·(Treated_g × Post_t) + ε, Post_t = 1 for t ≥ 2022q1; fund FE α_f, quarter
FE λ_t. **β = DiD; F3 substitution = NEGATIVE β** (funds actively sell CN-nationality securities post-freeze,
relative to control). Also the **event-study** form: quarter-relative-to-freeze dummies (leads + lags), base
t = 2021q4; the leads test the pre-trend (should be ~0), the lags show the dynamic effect. SE clustered by fund
and by quarter. **No leave-one-quarter-out** — it is invalid for an event study (it removes the identifying
event quarters); the pre-trend test and the event-study leads ARE the robustness checks.

## Decision rule (applied in Part 2, after the numbers)

- **DiD-LOADS** — β NEGATIVE, significant, WITH a FLAT pre-trend (leads jointly insignificant). F3 is real:
  funds actively reallocated out of CN-nationality securities after the freeze, relative to a parallel control,
  net of valuation. The estimator matched to the event; REOPENS identification. State magnitude + the pre-trend.
- **DiD-NULL** — β ≈ 0 with adequate power AND a flat pre-trend. No differential post-freeze reallocation; F3
  absent under the correct event estimator on the valuation-stripped quantity. TERMINAL, the strongest null yet.
- **NOT-IDENTIFIED** — no candidate control has a flat pre-trend (leads significant); β is not interpretable.
  Reported honestly; a broken-pre-trend β is NOT reported as causal.
- **INSUFFICIENT-POWER** — valid design but CI too wide to distinguish; state what would resolve it.

## The falsifiable prediction (sign-agnostic; outcome not favored)

> **Primary prediction: DiD-NULL or NOT-IDENTIFIED.** A-priori (before any control is built): the prior
> weight and active-flow tests were powered/insignificant, and the cleanest active-flow read leaned NO-F3, so I
> expect either no differential post-freeze active reallocation (DiD-NULL) or that no candidate control has a
> flat enough pre-trend to identify the DiD (NOT-IDENTIFIED) — CN ADRs, EM equity, and Cayman credit all had
> idiosyncratic 2020–2021 dynamics. I do NOT favor the null: the DiD is the estimator best matched to a discrete
> event, and LOQO genuinely was the wrong robustness check for it — so if a real event effect was masked by the
> continuous-shock/LOQO framing, THIS design is the one that can surface it. If it does, that is the finding.
>
> **The one falsifiable commitment:** if, against a control with a demonstrably FLAT pre-trend, the DiD β is
> NEGATIVE and significant with jointly-insignificant leads, the primary prediction is REFUTED and the verdict
> is **DiD-LOADS** — F3 identified by the correct event estimator. I do not predict the sign of β; a null, a
> positive, or a non-identified design are all admissible.

## Anti-planting commitments

- β and the pre-trend/event-study coefficients **read from the estimator, never hardcoded.**
- The control is chosen by the **pre-trend rule above**, not by the DiD β; ALL candidate controls' pre-trends
  are reported, so a cherry-picked control cannot hide.
- A β from a design whose pre-trend is NOT flat is reported as **NOT-IDENTIFIED**, never as a causal effect.
- Active flow is the already-built, reconstruction-gated valuation-stripped quantity; control groups use the
  identical constant-price decomposition.
- No leave-one-quarter-out (invalid here); the pre-trend leads are the robustness check. Power reported honestly.

## Scope

STOPS after the prediction, the feasibility artifact (quarter list + all candidate pre-trends), the DiD +
event-study result, the recompute script, and the verdict. Does NOT re-tag the operator, does NOT build a
hazard, does NOT touch DP2–DP5, does NOT begin DP6. No date, no bare probability, no hazard claim.
