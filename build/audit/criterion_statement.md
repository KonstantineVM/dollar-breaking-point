# CRITERION STATEMENT — REAL (empirical) F3/F4 separability bar, stated for human audit

**Date:** 2026-06-29 · **Stage:** Test 3, read-only ratification support for the terminal separability verdict.
**Scope:** Writes EXACTLY this one file (`build/audit/criterion_statement.md`). Modifies no other file. READ-ONLY on all
prior artifacts. DP6 NOT started. This file STATES the criterion that was already applied; it does NOT change, re-run,
or re-adjudicate it. No date emitted. No bare probability emitted. The build is NOT declared complete — that is the
human's call at the ★ gate.

**Purpose:** Make the REAL-separability criterion explicit and auditable so the human ratifies a STATED bar, not an
implicit one. Whether this is the right economic bar is the judgment routed to the ★ human gate.

---

## 1. The REAL-separability BAR as it was applied (conjunctive — ALL THREE required)

SUBJECT-DRIVER: REAL (empirical) F3/F4 separability — distinguishing an F3 sanctions-driven nationality reallocation
from an F4 dollar run in the data — was required to satisfy **ALL THREE** of the following conditions jointly:

- **(i) NEGATIVE within-holder substitution sign.** The within-holder US-leg-vs-offshore-haven co-movement must be
  NEGATIVE: the US leg falls WHILE offshore-haven (China-conduit) exposure rises. A positive sign is common growth,
  not substitution.
- **(ii) FOOTPRINT SEPARATION.** The F3-vs-F4 footprint cosine must fall well below Test B's 0.9386 (near-collinear),
  i.e. the two directions must not be near-collinear.
- **(iii) TEMPORAL LEAD/LAG.** A lead/lag must distinguish reallocation from a common run: a NEGATIVE cross-correlation
  at some nonzero lead/lag k (substitution reallocation signature), as opposed to a contemporaneous (k=0) POSITIVE
  peak (common-run / contagion signature).

BOUNDARIES: this is the bar on the empirical-separability axis; it is conjunctive (the AND of i, ii, iii), applied to
the residency-monthly TIC SLT haven cells the DP4 operator's block A uses. It is the bar applied in Part 2 and read
off in Part 3 — not a new bar.
FALSIFIER: if the bar had been stated as disjunctive (any one of i/ii/iii sufficing), condition (ii) being MET would
have flipped the verdict to separable; it was not stated disjunctively, and the verdict turns on the conjunction.
SOURCE: `build/audit/sep_definitive_test.json` (verdict_basis: "REAL SEPARABILITY would require ALL of: negative
within-holder sign + footprint separation + temporal lead/lag"); `build/audit/terminal_verdict.md` (Mapping check:
"requires ALL THREE of: (i) a negative within-holder substitution sign, (ii) footprint separation, (iii) a temporal
lead/lag").

---

## 2. Which condition the data MET and which FAILED (traced to sep_definitive_test.json)

- **(i) within-holder substitution sign → FAILED.**
  SUBJECT-DRIVER: the principled flow transform (month-over-month log-change, demeaned) gives a POSITIVE pooled sign
  +0.362 (per-haven: CYM +0.606, HKG +0.285, VGB +0.408); simple-change robustness +0.553. The bar requires a
  NEGATIVE sign; the observed sign is positive — the WRONG sign for F3 substitution, matching Test B's +0.4664.
  BOUNDARIES: holds on the two flow-appropriate transforms (log-change, simple change); only LEVELS flip negative for
  HKG/VGB while CYM levels stay +0.844 and the pooled level corr is +0.809 — and levels are not the substitution-
  appropriate transform.
  FALSIFIER: a negative pooled flow-transform sign would have met this condition; it does not appear at monthly
  frequency.
  SOURCE: `build/audit/sep_definitive_test.json` → a_substitution_sign (recomputed_logchange_pooled 0.362091,
  robustness_change_pooled 0.552738, sign_is_substitution_F3 false).

- **(ii) footprint separation → MET.**
  SUBJECT-DRIVER: the mean-direction footprint cosine fell to −0.047 (vs Test B's 0.9386) — well below 0.94, so the
  numeric threshold of condition (ii) is satisfied.
  BOUNDARIES: this is divergence of the two directions' AVERAGE drift directions; the per-month cosine stays POSITIVE
  at +0.329 and the within-holder co-movement stays POSITIVE at +0.362. Average-drift divergence is consistent with
  two positively-co-moving directions of different mean growth rates; meeting (ii) numerically does NOT establish
  period-by-period substitution.
  FALSIFIER: a footprint cosine staying near 0.94 would have failed (ii); it fell to −0.047, so (ii) is met as stated.
  SOURCE: `build/audit/sep_definitive_test.json` → b_footprint_separation (recomputed_footprint_cosine_meandirection
  −0.047026, recomputed_footprint_cosine_monthly_mean 0.328619); honest_scope.footprint_cosine_nuance.

- **(iii) temporal lead/lag → FAILED.**
  SUBJECT-DRIVER: the F4-vs-F3 cross-correlation peaks at k=0 (CONTEMPORANEOUS) with POSITIVE sign (+0.608 full
  sample, +0.445 in the 2021-07..2023-06 window around the 2022 episode); no negative correlation appears at any
  nonzero lead or lag k. This is the common-run signature, not the substitution-reallocation signature the bar
  requires.
  BOUNDARIES: profile computed over k=−6..+6 months on aggregate haven series, both full sample and 2022 window.
  FALSIFIER: a strong negative correlation at any nonzero k would have met (iii); the monthly resolution reveals none.
  SOURCE: `build/audit/sep_definitive_test.json` → b_footprint_separation.lead_lag (full_sample_peak k=0 value
  0.607988, episode_2022_peak k=0 value 0.444814).

**Met/failed mapping:** (i) FAILED · (ii) MET · (iii) FAILED. Two of three required conditions fail; the one that is
met is met only as average-drift divergence.

---

## 3. The SIGN (condition i) is the LOAD-BEARING condition

SUBJECT-DRIVER: the verdict turns on requiring condition (i) — the NEGATIVE within-holder substitution sign — as
load-bearing, NOT on the footprint cosine alone. The footprint-cosine drop (condition ii MET, cosine −0.047) does NOT
by itself establish separability: average-drift-direction divergence, with the per-month cosine still +0.329 and the
within-holder co-movement still +0.362, is consistent with two positively-co-moving directions that have different
mean growth rates. Without a negative substitution sign (i) AND a substitution lead/lag (iii), average-drift
divergence is not period-by-period substitution. The conjunctive bar — with the SIGN as the decisive FAILED condition
— is what yields GEOMETRIC-ONLY / UNIDENTIFIABLE-FROM-AVAILABLE-DATA rather than REAL separability.
BOUNDARIES: this is a statement about which condition is decisive under the bar as applied; the sign and the lead/lag
both fail, and either failing alone defeats a conjunctive bar, but the sign is the discriminator the criterion treats
as load-bearing (footprint divergence absent a sign change is explicitly held insufficient).
FALSIFIER: if the bar were read so that condition (ii) alone (footprint-cosine drop) established separability, the
verdict would flip to separable; the criterion as applied does not read it that way, and a negative substitution sign
does not appear on either flow transform.
SOURCE: `build/audit/sep_definitive_test.json` → honest_scope.footprint_cosine_nuance ("Separation of average drift
directions WITHOUT a negative substitution sign or a substitution lead/lag does not constitute REAL (empirical)
separability in the F3 sense"); verdict_basis; `build/audit/terminal_verdict.md` ("Two of the three required criteria
(the load-bearing sign, and the temporal lead/lag) FAIL; the third is only average-drift divergence").

---

## 4. Geometric non-degeneracy is NOT identification

SUBJECT-DRIVER: the structurally-complete operator (DP4 base plus the F4-official backstop respec, f pinned
[0.49,0.71]) is geometrically non-degenerate — base min margin 0.220969, backstop-stress min margin 0.224911, both
≥ τ=0.10 — so the F3-exclusive direction [f·DESTn ; 0] exists on paper. Geometric non-degeneracy (operator margin > τ)
is precisely NOT identification: it states the boundary exists, not that the data move along it in the substitution
sense. Substituting the geometric openness for identification is exactly the error this statement guards against; the
margin > τ result is reported as NOT identification.
BOUNDARIES: property of the pinned rectangle [0.49,0.71]; the backstop is an F4-only orthogonal cell that can only
increase the F3/F4 angle, so it does not collapse the boundary. This is a separate axis from the empirical-loading
bar of sections 1–3.
FALSIFIER: a min margin below τ=0.10 would make the boundary geometrically degenerate; it does not (margin ≥0.221).
Conversely, the non-degenerate margin does not supply a substitution sign or a lead/lag — those are sections 2(i) and
2(iii), which fail.
SOURCE: `build/audit/sep_definitive_test.json` → operator_with_backstop (base_min_margin_pinned_rectangle 0.220969,
backstop_stress_min_margin 0.224911, margin_anchor); `build/audit/geo_vs_emp_test.json` (min_pinned_margin 0.220969,
verdict "GEOMETRIC_ONLY").

---

## 5. This is a STATEMENT of the existing criterion, not a change to it

SUBJECT-DRIVER: this file states, for human audit, the criterion that was already applied in Part 2
(`sep_definitive_test.json`) and read off in Part 3 (`terminal_verdict.md`). It does not change the bar, does not
re-run any computation, and does not re-adjudicate the verdict. The criterion was cleared in its earlier form at the
DP5 gate.
BOUNDARIES: whether the conjunctive bar with the sign as load-bearing is the RIGHT economic bar is a judgment routed
to the ★ human gate, not settled here. The build is not declared complete here.
FALSIFIER: any text in this file that altered a threshold, a transform choice, or a met/failed mapping would make it a
change rather than a statement; none does — every number and condition is quoted from the named source artifacts.
SOURCE: `build/audit/sep_definitive_test.json` (the criterion as applied); `build/audit/terminal_verdict.md` (the
criterion as read into the terminal call); DP5 gate clearance of the earlier form of the criterion.
