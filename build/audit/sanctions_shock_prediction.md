# Sanctions-Shock F3 Test (corrected treatment) — PRE-REGISTERED PREDICTION

**Timestamp: 2026-07-01 (written and committed BEFORE Part 1 grounding and BEFORE Part 2 estimation — before
the sanctions treatment or the regulatory control is built, before the regression is run).**

Pre-registration, committed to the branch *before* estimation. The prediction below **may be REFUTED**, and
any of the three endpoints is the finding. Do not spec-search a sanctions treatment toward a negative; do not
dress an underpowered or confounded null as a clean null; run the regression and report the coefficient
whatever its sign.

## Why this test exists (and why a null is a-priori likely)

The full-panel Converse–Mallucci weight regression returned a **POWERED NULL** on GPR-China: headline β
= **+0.0125** (positive, robust across all 22 leave-one-quarter-out drops), the negative (substitution)
direction bootstrap-insignificant (**p = 0.58 at G = 22**), residual GPRC share of within-fund variation
74.5%. But **GPR-China is a generic geopolitical-risk index, not a sanctions measure.** F3 is specifically a
**sanctions** mechanism: the Feb-2022 Russian FX-reserve freeze read across to China as a reserve/asset-freeze
risk, predicting a shift OUT of China-nationality exposure. This test replaces the generic shock with a
**sanctions-specific treatment** inside the SAME CM weight-regression identification, and adds a control for
the **competing regulatory/delisting channel** (HFCAA identification, the 2021 Didi/tech crackdown, the
Dec-2023 outbound-investment EO) so that a negative loading is attributable to *sanctions* and not to
regulatory delisting risk.

**A-priori expectation (stated before the data, honestly): a clean sanctions-F3 effect will be HARD to
isolate, and a null is genuinely likely.** Two reasons, both structural:
1. **The GPR null is already powered.** GPR-China co-moves with sanctions risk over 2022; the powered GPR null
   is evidence (not proof) that no large within-haven CN-weight substitution occurred on the generic shock.
2. **The regulatory channel is a known competing cause that co-moves with the sanctions timing.** HFCAA
   Commission-Identification and the delisting scare ramp over 2021–2022 — the SAME window as the Feb-2022
   reserve freeze. With fund FE and no time FE (CM's device, required because the sanctions shock is a single
   national series), both the sanctions treatment and the regulatory control are **national time series that
   ramp together in 2022**. Separating them off ≈22 quarters is intrinsically hard; the one lever that can
   distinguish them is **different timing** (the Feb-2022 freeze and the Dec-2023 secondary-sanctions EO are
   distinct from the 2021 crackdown / HFCAA-conclusive timing).

INSUFFICIENT-POWER and NO-SANCTIONS-F3 are **first-class outcomes**, at least as likely a priori as
SANCTIONS-F3-LOADS. I do **not** favor F3-LOADS.

## The sanctions treatment (Part 1 grounds each; defined here before building)

- **Event windows.** (i) **Feb-2022 Russian FX-reserve freeze** — the F3 triggering event (read-across
  asset-freeze risk to China). (ii) **Dec-2023 secondary-sanctions executive order** — expands
  secondary-sanctions exposure of foreign financial institutions. Post-event indicators keyed to
  fiscal_quarter; both event dates grounded against the primary source (US Treasury/OFAC / White House EO
  text), not asserted from memory.
- **Continuous intensity (if constructible).** A quarterly sanctions-intensity series — e.g. OFAC
  China-related designation counts per quarter, or a documented sanctions-risk proxy — fetched and recorded
  from the real OFAC source. If only event dummies are defensibly constructible from free primary data, event
  dummies are used and that limitation is stated; no intensity series is fabricated.
- **The shock of interest** replaces GPRC_China in the CM spec. Sign convention: a **negative** coefficient =
  funds shift weight OUT of China-nationality haven exposure as sanctions risk rises = F3 substitution.

## The regulatory-channel control (load-bearing; Part 1 grounds it)

- **HFCAA Commission-Identified status over time** — already on disk from the crosswalk build
  (hfcaa_conclusive.json + the R1 tagging). The delisting-risk timing (provisional/conclusive identification
  ramp, 2022) enters as a control so a CN-nationality security's delisting risk does not masquerade as
  sanctions reallocation.
- **The 2021 Didi/tech-crackdown date and the Dec-2023 outbound-investment EO date** as additional
  regulatory-timing controls, grounded.
- **This control is not optional.** Without it the test cannot separate F3 (sanctions) from the regulatory
  channel. The estimate is reported **WITH and WITHOUT** the regulatory control so the reader (and the critic)
  can see which channel the within-fund CN-weight variation loads on. If the sanctions coefficient vanishes
  once delisting risk is controlled, that is the finding — the apparent reallocation was regulatory, not F3.

## The exact specification (headline)

w_{f,t} = α_f + β·SANCTIONS_t + λ·REGULATORY_t + γ₁·w_{f,t−1} + γ₂·w_{f,t−2} + δ·relative_returns + θ·X_t + ε_{f,t}

- w_{f,t} = (CN-nationality haven value held by fund f at t) / (fund f's total haven value at t) — **identical**
  to the full-panel CM dependent variable (currency_value is USD; no FX conversion; the standing correction).
- SANCTIONS_t = the sanctions treatment (event dummies and/or intensity); β is the parameter of interest.
- REGULATORY_t = the delisting/regulatory-risk control (the confound).
- X_t = [log VIX, broad dollar index, oil]; α_f = fund fixed effects (no time FE — CM's device for a single
  national shock). Estimator: within (fund-demeaned) OLS. Panel: the full 22-quarter crosswalk-tagged panel
  (2019q3–2024q4), same as the full-panel CM pass.
- **The load-bearing comparison: β WITH vs WITHOUT REGULATORY_t.**

## Decision rule (applied in Part 3, after the numbers)

- **SANCTIONS-F3-LOADS** — β NEGATIVE, significant (incl. wild-cluster bootstrap by quarter < 5%), robust
  across the robustness panel, AND **survives inclusion of the regulatory control** (β stays negative and
  significant with REGULATORY_t in) AND survives leave-one-quarter-out. Substitution is real, sanctions-driven,
  and distinct from the regulatory/delisting channel — F3 identified. State the magnitude (Δweight per unit
  sanctions treatment). This REFUTES the null-likely primary prediction, and that refutation is the finding.
- **NO-SANCTIONS-F3** — β ≈ 0, OR β vanishes/attenuates to insignificance once the regulatory control enters,
  with adequate power (a CI tight enough to exclude an economically meaningful sanctions-specific negative).
  The mechanism is not present distinct from regulatory/delisting effects; the powered GPR null holds under the
  correct (sanctions) shock too. **TERMINAL** for the sanctions-F3 lever.
- **INSUFFICIENT-POWER** — CI too wide to distinguish SANCTIONS-F3-LOADS from NO-SANCTIONS-F3 (few events, thin
  cross-section, sanctions/regulatory collinearity). State exactly what would resolve it.

## The falsifiable prediction (sign-agnostic on β; confound-and-power-pessimistic)

> **Primary prediction: NO-SANCTIONS-F3 or INSUFFICIENT-POWER.** The corrected (sanctions-specific) shock will
> NOT produce a negative, significant, regulatory-control-surviving, leave-one-out-robust coefficient. Either
> the sanctions coefficient is ≈0 / bootstrap-insignificant (the powered GPR null holds under the correct
> shock), or whatever negative appears WITHOUT the regulatory control **attenuates to insignificance once the
> regulatory control enters** (the apparent reallocation loads on the delisting channel, not sanctions), or the
> sanctions/regulatory collinearity leaves the CI too wide to tell (INSUFFICIENT-POWER).
>
> **The one falsifiable commitment:** if the sanctions coefficient is negative, significant on honest
> few-cluster inference, robust across event-window definitions, AND **remains negative and significant with the
> regulatory control included** and survives leave-one-quarter-out, the primary prediction is REFUTED and the
> verdict is **SANCTIONS-F3-LOADS** — F3 substitution is identified as a distinct sanctions mechanism.
>
> I do NOT predict the sign of β WITHOUT the control; a spurious negative from the 2022 regulatory ramp is
> plausible there, which is exactly why the with/without-control comparison is the load-bearing test, not the
> raw sign.

## Anti-planting commitments

- β and every inference statistic **read from the estimator/bootstrap output, never hardcoded.**
- The sanctions treatment and the regulatory control are **grounded in real primary sources** (OFAC/Treasury,
  White House EO text, the on-disk HFCAA list); a source that cannot be fetched is recorded, not assumed.
- The regulatory control is **genuinely included** — a real sanctions effect must not be erased by absorbing it
  into a collinear control, so the WITH-vs-WITHOUT comparison is reported in full and the collinearity between
  SANCTIONS_t and REGULATORY_t is measured and reported, so the critic can see which channel the variation
  loads on.
- **No spec-search across event windows.** The headline event definition is fixed here; alternative window
  widths and intensity-vs-dummy are robustness, not cherry-picks. No treatment definition is selected for its
  sign.
- The wild cluster bootstrap and leave-one-quarter-out are **computed, persisted, and verifier-reproduced** —
  never asserted (the standing lesson from the prior BLOCK on this line of work).
- Power reported honestly: an underpowered or collinearity-limited wide-CI result is INSUFFICIENT-POWER, not
  NO-SANCTIONS-F3; a null that only appears once a collinear control absorbs the effect is reported as the
  with/without divergence it is, not as a clean sanctions null.

## Scope

STOPS after the prediction, the sanctions treatment + regulatory control (with sources contract), the
regression result, the recompute script, and the verdict. Does NOT re-tag the operator, does NOT build a
hazard, does NOT touch DP2–DP5, does NOT begin DP6. No date, no bare probability, no hazard claim.
