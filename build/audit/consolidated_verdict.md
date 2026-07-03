# Consolidated verdict — the three open questions resolved

**Date:** 2026-06-29 · **Stage:** read-only resolution of the three questions the falsification
audit left unsettled. **Scope:** writes only to `build/audit/`. Prior artifacts (dp3_spec, dp4_inputs,
dp4_spectrum, dp5_*, china_fraction_bound) are **read-only and NOT modified**. The verdict below is
**NOT merged into the build** and **DP6 is NOT started** — that is the human gate's call.

This file is the top-line synthesis. Each test is a pointer to its on-disk artifact; the integrity
critic ran on all three (GATE = PASS, with one required non-blocking correction now applied).

---

## CONSOLIDATED VERDICT: **OPEN-PENDING-DATA**

Not IDENTIFIED, not NOT-IDENTIFIED. The two extremes are each ruled out by a different test, and what
remains is a separability that is **geometric but not empirical**, plus a **sector gap** — both
closable only by named data the build does not yet hold.

### Why not NOT-IDENTIFIED
The DP5 "NOT IDENTIFIED — HOLDS" verdict rested on **f = 0 being admissible** (the rank-1 degeneracy of
the [v_F3|v_F4] operator occurs only at f=0). **Test A (vintage)** makes the transfer of the grounded
2020 holdings-side pin decidable and lands **SUPPORTED**: f is bounded well away from 0 (matrix-comparable
2020 f = 0.532; conservative pinned floor 2019 = 0.489), the break-identification threshold is
**f\* = 0.249** at the worst confound corner, and in 14 years of GCAP history f has never fallen over any
5-year window (worst 5-yr move = +0.068, an increase). The f=0 attaining point that made the margin
infimum zero is **inadmissible on the grounded set** → the NOT-IDENTIFIED verdict *as written* does not
survive. → `build/audit/vintage_test.json` (+ verifier `vintage_test_compute.json`, script `vintage_test.py`).

### Why not IDENTIFIED
Two independent blocks:

1. **Test B (geometric vs empirical).** With f pinned to [0.49,0.71], the operator's separation margin is
   **≥ 0.221 > τ=0.10** across the whole rectangle — but that is **geometric** separability (the columns
   span distinct directions by construction of R_sep). The **empirical** test fails: the within-holder
   US-destination vs offshore-destination co-movement is **+0.47 — the WRONG SIGN for substitution**
   (F3 reallocation should move them oppositely), and the footprints are near-collinear. Verdict
   **GEOMETRIC_ONLY**: the data do not separate F3 from F4, they merely fail to forbid it.
   → `build/audit/geo_vs_emp_test.json`.

2. **Test C (official-sector / swap-line omission).** The Fed central-bank liquidity-swap line — a
   first-order official-sector dollar-provision channel — is **absent from the matrix entirely**. Fed SWPT
   peaks (2008-12-17 = $583,135mn; 2020-05-27 = $448,946mn) show it is material exactly in the run episodes
   F4 is meant to capture. F4 (dollar run across holders) cannot be cleanly identified while a major
   dollar-backstop leg is missing. This is a **separate DP1+DP3 reopening**, not curable inside the
   F3/F4 operator. → `build/audit/official_sector_test.json` (+ data `build/data/fed_swaps/SWPT_2007_2021.csv`).

---

## Per-test pointers

| Test | Question | Artifact | Result |
|------|----------|----------|--------|
| A | Is the 2020→2025-S1 vintage leap decidable, and does the f-pin transfer? | `build/audit/vintage_test.json` | **SUPPORTED** — f stable/rising, gap-to-f\* (0.28) far outside any historical 5-yr drift; f=0 unreachable. HONEST CAVEAT: 2020-vintage pin, no publisher post-2020 f-granularity restatement (NONE_AT_GRANULARITY); the coarse post-2020 signal points UP. |
| B | Is the separation empirical or only geometric? | `build/audit/geo_vs_emp_test.json` | **GEOMETRIC_ONLY** — pinned margins ≥0.221 geometrically, but within-holder co-movement +0.47 (wrong sign); the panel does not empirically separate F3/F4. |
| C | Does omitting the official-sector swap line bias the result? | `build/audit/official_sector_test.json` | **BLOCKING GAP** — Fed swap line absent from matrix; SWPT peaks $583bn (2008), $449bn (2020); F4 incomplete until wired in (separate DP1+DP3 reopen, watch BIS-LBS double-count). |

Integrity-critic GATE: **PASS** on all three. One required non-blocking correction (the EFH column in
`vintage_test.json` mis-transcribed vs its own verifier) is now **applied** — EFH realigned to
`vintage_test_compute.json` (2008→0.2996, 2011→0.4308, 2012→0.4185, etc.). The correction does not move
any verdict (the matrix-comparable FH basis the verdict rests on was always correct).

---

## Named datasets that would settle it (what OPEN-PENDING-DATA is pending on)

1. **To convert Test B's geometric separability into empirical separability** — a panel that resolves the
   single-snapshot/wrong-sign degeneracy at f-granularity:
   - **Monthly US TIC** holdings (TIC SLT / TIC-S) of **CYM / HKG / VGB** securities, giving a
     higher-frequency destination-column time series to test the substitution sign directly; and/or
   - a **post-2020 GCAP restatement vintage** (Restated Bilateral External Portfolios / Restatement
     Matrices) at **nationality f-granularity** — none exists past data-year 2020 today; its release would
     both close Test A's vintage caveat and supply the temporal discriminator Test B needs.

2. **To close Test C's sector gap** — wire the **Fed H.4.1 / FRED SWPT** central-bank liquidity-swap
   balances into the matrix as an official-sector dollar-provision leg of F4, via a **DP1 contract +
   DP3 F4-backstop respecification**, with explicit care against **BIS LBS double-counting** (swap-funded
   dollars may already appear in cross-border bank claims).

---

## Routed to the ★ human gate (not decided here)

1. **The 2020→2025-S1 vintage transfer.** Decidable and SUPPORTED, but rests on extrapolation from a
   2020-vintage pin (GCAP publishes no 2025 restatement). Whether the 2020 pin legitimately governs the
   2025-S1 matrix cell is an economic-judgment call.
2. **Whether to narrow `china_fraction_bound.json`** to the grounded holdings-side interval [0.49,0.71]
   and re-run DP3→DP5. If taken, the f-axis degeneracy that drove NOT-IDENTIFIED is removed — but Test B
   (empirical) and Test C (sector) still stand, so the re-run would land at OPEN-PENDING-DATA, not
   IDENTIFIED.
3. **Whether Test C blocks before DP6.** The official-sector gap is a structural omission in F4; the human
   decides whether DP6 may proceed with it flagged-and-bounded or must wait on the DP1+DP3 reopening.

---

## Bottom line
The three-question resolution moves the verdict off the NOT-IDENTIFIED endpoint (f=0 is inadmissible on
the grounded set) **without** reaching IDENTIFIED (separability is geometric-only, and a first-order
official-sector leg is missing). The honest status is **OPEN-PENDING-DATA**, pending the two named data
streams above. This is not decided by momentum: each endpoint is excluded by a *different* grounded test,
and the gap is named in datasets that exist or could exist, not waved at. The verdict is **not merged**
and **DP6 is not started** — both await the human gate.
