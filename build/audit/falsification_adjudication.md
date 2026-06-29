# Falsification audit — adjudicated verdict (integrity-critic corrected)

**Date:** 2026-06-29 · **Stage:** read-only falsification audit of the DP5 non-identification verdict.
This file is the **corrected synthesis**: the five test artifacts are honest records of what each test
found, but the initial top-line ("3 OVERTURN / 2 CONFIRM") **overstated** the result. The integrity
critic BLOCKED that framing. The corrected adjudication below is what goes to the ★ human gate.

## The headline correction
The accurate top line is **NOT** "three overturns topple the verdict." It is:

> **One grounded, decision-relevant overturn (Test 5); two confirms (Tests 2, 3); two strained /
> out-of-scope overturns that do not survive adversarial scrutiny (Tests 1, 4).**

The DP5 non-identification verdict **REOPENS — but at exactly ONE locus:**
`build/model/china_fraction_bound.json`'s admission of **f = 0 as the lower endpoint** of the
China-nationality interval. It does **NOT** reopen the operator USA-block specification that Tests 1
and 4 attack.

## Per-test, re-adjudicated

| Test | Initial | Adjudicated | Why |
|------|---------|-------------|-----|
| 1 — operator re-spec | OVERTURN | **Does NOT overturn (strained)** | The concentrated `-CONCn` USA block is a *new modeling assumption the structural model never makes*. The shared `-USAn` is the substantive content of R_sep (on a single snapshot F3 and F4 both manifest as the same common USA-column fall; the destination block `f·DESTn` + a lead/lag distinguish them). Test 1's "open" rests **entirely** on the USA-block shape (its own reason field concedes the destination blocks coincide at f=0), is **below τ** for much of the range, and is **contradicted by Test 2's data**: the within-holder US-vs-offshore-destination co-movement is **+0.47 (wrong sign for substitution)** and the footprints are near-collinear (cosine 0.94). A geometric degree of freedom the panel data refute — not a demonstration the data separate F3 from F4. |
| 2 — execute CPIS panel | CONFIRM | **CONFIRM (sound)** | 11 periods actually pulled; 2025-S1 CYM = 2,798,130 matches the matrix. The temporal lead/lag discriminator does not separate (semiannual too coarse — 2022 drops 11/12 holders in one bucket; positive co-movement; "demeaning is circular" reasoning correct). Path (a), when *executed*, does not rescue identification. |
| 3 — full 4-factor rank | CONFIRM | **CONFIRM (sound, honest)** | M4 built and SVD'd: rank 4, cond 15.6 away from f=0; only the (F3,−F4) direction is small. No new F1–F4 collinearity; surfaces the un-quantified F2–F4 \|cos\|=0.672 caveat. The §1 "F1/F2 identified" table survives. |
| 4 — 2022 ground truth | OVERTURN | **Inconclusive on the operator (scope mismatch)** | The 2022 facts are real and grounded (Brookings; McCauley-Chinn-Ito Chow F=0.574, p=0.57; live CPIS: US-securities holdings stable/rising while Russian-securities holdings collapsed 60–97%). **But** 2022 was reallocation *away from Russian securities* — a destination **not in the operator's China-offshore cells** (CYM/HKG/VGB). "The operator reads it as F4" reflects that the episode is *out of scope for that F3 axis*, not that the f=0 symmetrization blinds it to an in-scope F3 event. A real concentrated-reallocation event exists — but it cannot demonstrate mis-specification of the China-conduit axis. |
| 5 — pin f from GCAP | OVERTURN | **OVERTURN — REAL and DECISIVE** | The **holdings-side** GCAP restatement (Investor=USA × haven-residency {CYM,HKG,VGB} × CHN nationality; Restatement Matrices Methodology 1/2 — issuance-side Methodology 3 correctly excluded) pins **f ∈ [0.49, 0.71]** for *this specific pool*, never below ~0.36 across 2007–2020, rising since 2017. **f is bounded well away from 0**, so the f=0 endpoint that makes the DP4 operator rank-1 is **inadmissible on the grounded set** — the "infimum margin = 0" result loses its attaining point. At the DP4 operator's own margins, f≈0.6 gives 0.28–0.38 (above τ=0.10) for all s_usd. |

## The single reopening locus
The build's `china_fraction_bound.json` set the interval to **[0, 0.60]** using an **issuance-side >60%
equity figure** (NBER WP 30865) and admitted **0 as a "direct-only floor."** Test 5 shows the
**holdings-side, pool-matched** fraction for the US-held CYM/HKG/VGB → China-nationality pool is
**[0.49, 0.71]**. If f cannot reach 0 on any observed vintage, the rank-1-at-f=0 degeneracy — which
DP5 §3 calls "the single binding reason" — **does not occur on the admissible set**, and the
non-identification verdict *as written* does not survive.

This propagates forward: **china_fraction_bound.json → DP3 (the f=0 admissibility in R_sep's sweep) →
DP4 (the f=0 rank-1 endpoint) → DP5 (infimum margin = 0).** The reopening is at the *bound*, not the
operator.

## What does NOT reopen
- **The operator USA-block symmetrization** (Tests 1, 4): the shared `-USAn` is faithful structural
  content of R_sep, not an artifact. Do **not** reopen `dp3_spec.json` / `dp4_inputs.json` on Test 1's
  basis — it is a strained re-specification contradicted by Test 2's substitution-sign evidence.
- **The 4-factor identification of F1/F2** (Test 3): survives.
- **Path (a) as a temporal rescue** (Test 2): the panel, when executed, does not separate F3/F4 —
  DP5's "resolvable via path (a)" claim is itself qualified (the semiannual residency basis bites).

## Open items / routed to the ★ human gate
1. **The 2020 → 2025-S1 vintage leap (the central judgment).** GCAP publishes no 2025-aligned
   restatement. f∈[0.49,0.71] is a 2020-vintage pin; that no observed vintage 2007–2020 goes near 0 is
   strong but **does not certify** f could not have fallen toward 0 by 2025-S1. Whether the 2020 pin
   legitimately governs the 2025-S1 matrix cell is an economic-judgment call for the human.
2. **Test 5 reproducibility — CLOSED, and the result strengthened.** The GCAP denominator pool weights
   (Position_Residency, 318 rows) are now persisted to `build/data/gcap_usa_haven_pool_denominators.csv`;
   `build/audit/f_pin_recompute_check.py` recomputes **f = [0.4889, 0.7084]** end-to-end from the
   numerator + denominator CSVs *alone* (FH2019 0.489, FH2020 0.532, EFH2019 0.702, EFH2020 0.708) —
   matching [0.49,0.71]. The (f=0.49, s_usd=1.0) corner was recomputed from `dp4_inputs.json` (the
   operator reproduces the published grid values exactly): margin = **0.220 ≥ τ=0.10**, and the
   **minimum over the entire pinned rectangle** f∈[0.49,0.71]×s_usd∈[0,1] is **also 0.220**. So on the
   grounded pool, **F3/F4 identification HOLDS for ALL s_usd** — the s_usd hole, while still not pinned,
   **no longer threatens identification** once f is grounded. This *strengthens* the OVERTURN: it is not
   merely that f=0 is inadmissible, but that across the whole grounded admissible set the separation
   margin is bounded away from τ.
3. **The f=0 admissibility decision itself** — whether to narrow `china_fraction_bound.json` to the
   grounded holdings-side interval and re-run DP3→DP5 — is the human's call. If taken, the build
   reopens at the *bound*, and the downstream identification result may flip to **identified** (the
   margin is above τ across the bulk of [0.49,0.71]).

## Bottom line
The falsification audit did its job: it found a **real** defect the build's earlier gates never tested
for — the non-identification rested on an **f=0 endpoint that the wrong (issuance-side) figure
admitted, and that the grounded holdings-side data exclude.** The verdict **reopens at the
china-fraction lower bound**, on the strength of Test 5 alone. The other two overturns (Tests 1, 4) are
**not** load-bearing — flagging them as overturns was the framing error the integrity critic correctly
blocked. This corrected adjudication, not the raw "3 OVERTURN" tally, is the honest result.

**The reopening, sharpened by the closed Test 5 gaps:** on the grounded holdings-side pool the
China-nationality fraction is **f ∈ [0.49, 0.71]** (recomputable end-to-end from disk), and across the
whole admissible rectangle the DP4 operator's own separation margin is **≥ 0.220 > τ** — so if the
human gate accepts the 2020-vintage GCAP pin as governing the 2025-S1 cell, the breaking-point
mechanism (F3/F4) **flips from NOT IDENTIFIED to IDENTIFIED** on this pool, and the build must re-run
DP3→DP5 with `china_fraction_bound.json` narrowed to the grounded interval. The one judgment that
remains the human's: whether the 2020 pin legitimately governs 2025-S1 (GCAP has no 2025 vintage). The
build's machinery did exactly what it should — it refused to fabricate identification, and when an
adversarial audit grounded the missing number, it surfaced the flip honestly rather than defending the
prior verdict.
