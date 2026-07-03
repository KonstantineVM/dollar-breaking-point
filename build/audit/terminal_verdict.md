# TERMINAL VERDICT — Dollar Breaking-Point Build (separability axis)

**Date:** 2026-06-29 · **Stage:** Part 3, terminal call of the TERMINAL separability experiment.
**Scope:** Writes EXACTLY this one file (`build/audit/terminal_verdict.md`). Modifies no other file.
DP6 NOT started. No date emitted. No bare probability emitted. The breaking point is rendered as the
three objects required by the operational definition (frontier / distance-to-frontier / hazard-with-binding-mode),
always together.

---

## ENDPOINT: **UNIDENTIFIABLE FROM AVAILABLE DATA**

This is the project's **other-form success** — a precise, grounded impossibility result on the separability
axis — not its primary-form success (REAL F3/F4 separability) and not a fabricated identification. The endpoint
is read off the artifacts, not chosen by momentum. The symmetric alternative (IDENTIFIED) was held open and
checked against the three REAL-separability criteria; it fails two of the three, so it is not the endpoint the
data support.

---

## Mapping check — does Part 2 support REAL separability? (verified, not rubber-stamped)

REAL (empirical) F3/F4 separability requires **ALL THREE** of: (i) a negative within-holder substitution sign,
(ii) footprint separation, (iii) a temporal lead/lag. Part 2's recomputed numbers, checked against the criteria:

- **(i) Within-holder substitution sign — FAILS.**
  SUBJECT-DRIVER: the principled flow transform (month-over-month log-change, demeaned) of within-holder
  US-leg-vs-offshore-haven co-movement is **+0.362 pooled** (all three havens individually positive:
  CYM +0.606, HKG +0.285, VGB +0.408); simple-change robustness **+0.553**. F3 substitution requires a
  **negative** sign (US claims down while offshore-China-conduit exposure up). The sign is positive — the
  WRONG sign — matching Test B's semiannual +0.4664.
  BOUNDARIES: holds on the two flow-appropriate transforms (log-change, simple change); only LEVELS flip
  negative for HKG/VGB while CYM levels stay +0.844 and the pooled level corr is +0.809 — levels are not the
  substitution-appropriate transform.
  FALSIFIER: a negative pooled flow-transform sign would have flipped this to support substitution; it does
  not appear at monthly frequency.
  SOURCE: `build/audit/sep_definitive_test.json` → a_substitution_sign (recomputed_logchange_pooled 0.362091,
  robustness_change_pooled 0.552738, sign_is_substitution_F3 false).

- **(ii) Footprint separation — PRESENT only as average-drift divergence, NOT period-by-period substitution.**
  SUBJECT-DRIVER: the mean-direction footprint cosine fell to **−0.047** (vs Test B's 0.9386), but the
  per-month cosine stays **+0.329** and the within-holder co-movement stays **+0.362**.
  BOUNDARIES: the drop is divergence of the two directions' AVERAGE growth rates, consistent with two
  positively-co-moving directions; it is not a negative-sign substitution signal.
  FALSIFIER: separation accompanied by a negative substitution sign or a substitution lead/lag would count;
  neither accompanies it.
  SOURCE: `build/audit/sep_definitive_test.json` → b_footprint_separation (cosine_meandirection −0.047026,
  cosine_monthly_mean 0.328619); honest_scope.footprint_cosine_nuance.

- **(iii) Temporal lead/lag — FAILS.**
  SUBJECT-DRIVER: the F4-vs-F3 cross-correlation peaks at **k=0 (contemporaneous), POSITIVE** (+0.608 full
  sample, +0.445 in the 2021-07..2023-06 window around the 2022 episode); no negative correlation appears at
  any lead or lag k.
  BOUNDARIES: profile computed over k=−6..+6 months on aggregate haven series, both full sample and 2022 window.
  FALSIFIER: a strong negative correlation at any nonzero k would be a substitution reallocation signature; the
  monthly resolution reveals none, confirming Test B's "2022 simultaneous, no lead/lag."
  SOURCE: `build/audit/sep_definitive_test.json` → b_footprint_separation.lead_lag (full_sample_peak k=0
  value 0.607988, episode_2022_peak k=0 value 0.444814).

**Conclusion of the check:** Two of the three required criteria (the load-bearing sign, and the temporal
lead/lag) FAIL; the third is only average-drift divergence. REAL separability is NOT supported. The mapping
to GEOMETRIC-ONLY-CONFIRMED → UNIDENTIFIABLE-FROM-AVAILABLE-DATA holds.
SOURCE: `build/audit/sep_definitive_test.json` → verdict "GEOMETRIC-ONLY-CONFIRMED", verdict_basis.

---

## The precise locus of the impossibility — geometry OPEN, no flow LOADS it

SUBJECT-DRIVER: once f is pinned to [0.49,0.71], the structurally-complete operator (DP4 base operator plus the
F4-official-sector backstop respec) is **geometrically non-degenerate**: base min margin **0.220969**,
backstop-stress min margin **0.224911**, both ≥ τ=0.10; the backstop (an F4-only orthogonal official cell,
b_stress_scaled 0.068339) can only INCREASE the F3/F4 angle, so it does not collapse the boundary. The
F3-exclusive direction (v_F3 − v_F4 = [f·DESTn ; 0]) therefore **exists on paper**.
BOUNDARIES: this is a property of the pinned rectangle [0.49,0.71]×[s∈0,1]; it reproduces
geo_vs_emp_test.json's min_pinned_margin 0.220969 exactly.
FALSIFIER: a min margin below τ=0.10 on the pinned rectangle would make the boundary geometrically degenerate;
it does not — margin ≥0.221.
SOURCE: `build/audit/sep_definitive_test.json` → operator_with_backstop (base_min_margin_pinned_rectangle
0.220969, backstop_stress_min_margin 0.224911, margin_anchor); `build/model/dp3_spec.json` →
F4_dollar_run.official_sector_respec; `build/results/dp4_inputs.json`; `build/model/china_fraction_bound.json`
(interval_for_sweep [0.0,0.60]; pinned working interval [0.49,0.71]).

SUBJECT-DRIVER: **no obtainable flow loads that direction in the substitution sense.** The geometric openness
(margin > τ) is precisely **NOT** identification — that gap between "the boundary exists" and "the data move
along it" is the result. Non-identification here is an **empirical property of the data not loading F3**, not a
construction artifact: the operator is non-degenerate by 0.221, so the factor was not defined to make
non-identification automatic.
FALSIFIER: a dataset moving along [f·DESTn ; 0] with a negative substitution sign and a temporal lead/lag would
close it; none of the obtainable datasets does (enumerated below).
SOURCE: `build/audit/sep_definitive_test.json` → verdict_basis, honest_scope.

---

## Every dataset tried, and why each fails to load F3

1. **Semiannual CPIS residency panel (Test B).**
   SUBJECT-DRIVER: within-holder US-vs-offshore co-movement **+0.4664** (wrong sign), footprint cosine 0.9386
   (near-collinear), 2022 episode simultaneous across 11/12 holders (no lead/lag).
   FALSIFIER: a negative within-holder corr would load F3; it is positive.
   SOURCE: `build/audit/geo_vs_emp_test.json` → panel_substitution_sign
   (within_holder...corr 0.4664, sign_is_substitution_F3 false), verdict "GEOMETRIC_ONLY".

2. **Monthly TIC SLT residency — the higher-resolution acquisition (Part 1 / Part 2).**
   SUBJECT-DRIVER: within-holder sign **+0.362** (log-change; +0.553 simple change) — still the wrong sign;
   lead/lag **contemporaneous and positive** (k=0: +0.608 full, +0.445 in 2022) — no substitution signature.
   BOUNDARIES: TIC SLT resolves only US↔foreign residency legs; it carries no foreign↔foreign within-holder
   cell, so a nationality cell cannot be reconstructed from it — the China-NATIONALITY reallocation is invisible
   to residency-only coverage.
   FALSIFIER: the higher frequency would have revealed a hidden negative sign or a negative lead/lag; it reveals
   neither — it confirms Test B at higher frequency rather than overturning it.
   SOURCE: `build/audit/sep_definitive_test.json` → a_substitution_sign, b_footprint_separation,
   coverage_limitation_stated_not_invented; `build/audit/sep_data_acquired.json` → part_a_monthly_tic_slt
   (determination "OBTAINED", basis_caveat_CRITICAL: residency-based, does NOT resolve nationality f).

3. **GCAP nationality-basis restatement (Part 1, re-confirming Test A).**
   SUBJECT-DRIVER: every GCAP nationality-restatement file (Restated Bilateral External Portfolios, 398,332
   rows; China-in-Tax-Havens) terminates at **data-year 2020** — **NONE_AT_GRANULARITY post-2020**, read
   directly from the publisher files on 2026-06-29.
   BOUNDARIES: the restatement cell (US holdings of CYM/HKG/VGB reattributed to CHN nationality) exists only
   through 2020; it cannot test a 2022 or 2025 nationality reallocation.
   FALSIFIER: a post-2020 row at this granularity would let f be tested across a sanctions episode; no such row
   exists in any file fetched.
   SOURCE: `build/audit/sep_data_acquired.json` → part_b_post2020_gcap_nationality_restatement
   (determination "NONE_AT_GRANULARITY", latest_data_year_by_series RBEP 2020); `build/audit/vintage_test.json`
   → post2020_signal.NONE_AT_GRANULARITY TRUE.

---

## What data — that does not currently exist — would close it

SUBJECT-DRIVER: closing the F3/F4 separation requires a **post-2020, counterpart-resolved, NATIONALITY-basis
(not residency) restatement at f-granularity** — i.e., US holdings of CYM/HKG/VGB reattributed to CHN
nationality — at **monthly / sub-annual frequency**, spanning a sanctions episode, so the substitution sign and
the lead/lag can be tested on the nationality reallocation the residency data cannot see.
BOUNDARIES: it is the **nationality × counterpart × sub-annual conjunction** that is missing. Each ingredient
partially exists — TIC SLT supplies counterpart×monthly but only at residency basis; GCAP supplies
nationality×counterpart but only annually and only through 2020 — but the conjunction of all three does not
exist in any publisher file fetched.
FALSIFIER: release of such a dataset (e.g., a post-2020 GCAP restatement vintage at monthly/sub-annual
nationality granularity) would make this verdict revisable; until then the conjunction is absent.
SOURCE: `build/audit/sep_data_acquired.json` (residency-only monthly TIC; nationality frozen at 2020);
`build/audit/vintage_test.json` (no post-2020 f-granularity restatement); `build/audit/sep_definitive_test.json`
→ honest_scope.what_residency_monthly_CANNOT_settle.

---

## THE THREE OBJECTS (reported together)

1. **Frontier — fundamentals-gated manifold.**
   SUBJECT-DRIVER: the multiple-equilibrium boundary EXISTS as a geometric object on the pinned rectangle
   [0.49,0.71]: the structurally-complete operator (backstop in F4, f pinned) is non-degenerate with min margin
   ≥0.221 (base) / 0.225 (backstop-stress) > τ=0.10. The F3-exclusive direction [f·DESTn ; 0] spans a distinct
   axis by construction.
   BOUNDARIES: geometric existence only; the backstop does not collapse it (margin ≥ base).
   FALSIFIER: margin < τ on the pinned rectangle would erase the frontier; it does not.
   SOURCE: `build/audit/sep_definitive_test.json` → operator_with_backstop; `build/model/dp3_spec.json`
   (F4 official_sector_respec); `build/results/dp4_inputs.json`.

2. **Distance-to-frontier — signed scalar.**
   SUBJECT-DRIVER: a signed distance exists as a GEOMETRIC object — the pinned-f level sits **0.282 above** the
   break-identification threshold f*=0.249 (matrix-comparable 2020 f=0.532; conservative pinned floor 2019
   f=0.489 sits 0.240 above), and the operator margin sits 0.121 above τ at the worst corner (0.221 − 0.10).
   BOUNDARIES: this distance is measured in the geometry of the pinned rectangle; it is a separation distance,
   not a probability and not a date.
   FALSIFIER: f falling to f*=0.249 would zero the distance; in 14 years of GCAP history f never fell over any
   5-year window (worst 5-year move +0.068, an increase).
   SOURCE: `build/audit/vintage_test.json` → break_even_f_star 0.24944,
   distance_2020_FH_above_f_star 0.2823; `build/audit/sep_definitive_test.json` → operator margins.

3. **Hazard — with binding-mode attribution.**
   SUBJECT-DRIVER: the hazard's **binding-mode attribution is NOT IDENTIFIED FROM AVAILABLE DATA.** Whether a
   given fall in the USA-column is an **F3 sanctions-driven nationality reallocation** or an **F4 dollar run**
   cannot be distinguished by any obtainable flow: within-holder substitution sign is positive (wrong sign) and
   lead/lag is contemporaneous-positive at every obtainable resolution. This is the precise locus of the
   impossibility — the frontier and a signed distance exist geometrically, but the F3-vs-F4 binding-mode of a
   USA-column move is unidentifiable from data.
   BOUNDARIES: this is a data-loading property, not a geometric degeneracy — the operator is non-degenerate
   (margin ≥0.221), so this is not a construction artifact. No hazard scalar, no band, no date is emitted; doing
   so would fabricate identification the data refuse.
   FALSIFIER: a nationality×counterpart×sub-annual dataset showing a negative substitution sign and a temporal
   lead/lag over a sanctions episode would identify the binding mode; no such dataset exists.
   SOURCE: `build/audit/sep_definitive_test.json` → verdict_basis, honest_scope;
   `build/audit/geo_vs_emp_test.json` → verdict "GEOMETRIC_ONLY".

---

## Relation to the prior status and the project's intended outcome

SUBJECT-DRIVER: this terminally resolves the prior **OPEN-PENDING-DATA** status on the **separability axis**.
The official-sector axis was already structurally fixed by the F4 backstop respecification (operator
non-degenerate with the backstop, margin 0.225 ≥ base 0.221). The remaining f / empirical-separability axis is
what this settles: the higher-resolution data the prior verdict was pending on (monthly TIC SLT) was obtained,
recomputed, and does NOT load F3 — and the nationality-basis data that could is frozen at 2020.
BOUNDARIES: this settles the separability axis; it is revisable only by the named not-yet-existing dataset.
FALSIFIER: arrival of that dataset, or a recomputed negative flow-transform sign with a temporal lead/lag, would
reopen it.
SOURCE: `build/audit/consolidated_verdict.md` (prior OPEN-PENDING-DATA);
`build/audit/sep_definitive_test.json` (separability axis); `build/model/dp3_spec.json`
(official-sector axis fixed by backstop).

This is the project's intended **symmetric outcome** exercised in its impossibility form: a refusal to fabricate
identification, landing on a precise, grounded, named impossibility result. "Hazard not identified /
binding-mode unidentifiable from available data" is stated plainly because that is what the artifacts show.

---

## Integrity self-check

- **No date emitted; no bare probability emitted.** The breaking point is rendered as the three objects.
- **No planting.** The UNIDENTIFIABLE endpoint follows from the recomputed wrong-sign (+0.362) and the
  no-lead/lag (k=0 positive) — data-driven — NOT from a factor defined so non-identification is automatic; the
  operator is geometrically non-degenerate (margin ≥0.221), so non-identification is empirical.
- **No substitution.** The geometric openness (margin > τ) is reported as precisely NOT identification; the gap
  between geometric existence and empirical loading IS the result, not glossed as a band or point.
- **No scope reduction.** All three objects are reported together; the unresolved object (hazard binding-mode)
  is stated as unidentified, not dropped.
- SOURCE for every claim above = the read-only artifacts named inline.
