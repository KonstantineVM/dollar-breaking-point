# DP5 — Final Verdict: the Dollar Breaking-Point as a Precisely-Bounded Non-Identification

**Build:** dollar-breaking-point · **Stage:** DP5 (identification gate) · **Date:** 2026-06-29
**Synthesizes:** `build/results/dp5_episode_sort.json` (Part 1), `build/results/dp5_idtest.json` (Part 2), `build/results/dp5_resolution_path.json` (Part 3)
**Verdict on F3/F4 separation:** **NOT ESTABLISHED — HOLDS.** This is the terminal statement of the build. It is a non-identification, bounded exactly, with a grounded path to resolution. It is **not** a hazard number and **not** a date.

---

## In plain terms

The build asked whether the data can tell apart two ways the dollar's reserve role could break:

- **F3 — sanctions-reallocation:** specific holders exit US/dollar claims and move the money into a specific destination (the China-conduit columns), keeping their portfolio roughly the same size.
- **F4 — dollar-run:** holders cut their dollar leg *together*, contagiously, and the money leaves the dollar system — a self-fulfilling run.

Both mechanisms move the **same observable cells** (a fall in the USA column). On the single matrix we have, they are **observationally the same thing**. The gate's job was to test whether the data separates them. It does not — and we can say exactly why, and exactly what would fix it.

---

## 1. What IS identified

- **F1 — USD funding stress:** identified as a level/marginal factor (BIS USD per-area claims/liabilities, Fed S2 cells), **bounded** by a `$711,157.7 mn` BIS claims-vs-liabilities asymmetry floor that limits precision but not identification.
- **F2 — US-Treasury de-specialization:** identified as a Treasury-specific **quantity** factor (TIC Treasury-by-counterparty + Fed S4-government cells). **Quantity-side only** — the convenience-yield / safe-asset **price leg (κ) is a HOLE**, not in this stock matrix.
- **F4's common-run footprint as a direction:** the common, signed fall across the 12-holder USA issuer column **exists as an observable direction** (CYM→USA `$4.51tn`, IRL→USA `$2.58tn`, JPN→USA `$2.34tn`, … BEL→USA `$0.12tn`). F4 is *not* defined as "the event that hasn't happened" — it has a concrete footprint episodes can load on.
- **The offshore pool, measured:** US→CYM `$2,798,130 mn`, US→HKG `$107,448 mn`, US→VGB `$51,419 mn` (pool `$2,956,997 mn`), dwarfing the direct US→CHN cell (`$255,341 mn`) ~11×. The *mass* is observed; its *nationality and currency* are not.

## 2. What is NOT identified

- **The F3/F4 SEPARATION** — sanctions-reallocation vs dollar-run — is **not identified**. This is the load-bearing failure.
- **The breaking-point HAZARD as a point** — refused; it would require inventing the two holes.
- **The China-by-nationality magnitude** — a bounded HOLE, `f ∈ [0, 0.60]`, never a point.

Per the three required objects (CLAUDE.md):

| Object | Status |
|---|---|
| **frontier** (multiple-equilibrium manifold) | **NOT located.** The global-games threshold θ\* needs F4's cross-holder complementarity loading, which needs the F3/F4 separation; and θ (issuer fundamental) is out-of-matrix. Specified in form, not located. |
| **distance-to-frontier** | **NOT a scalar.** Reported only as the conditional separation-margin **surface** over (f, offshore-USD share), whose **infimum is 0**. |
| **hazard** (with binding-mode attribution) | **NOT IDENTIFIED.** The attribution (F3 vs F4) is undecidable at the admissible endpoint and nowhere robustly identified across the admissible plane. |

## 3. The single binding reason

The identification operator **M = [v_F3 | v_F4]** (15-dim: 3 offshore destination cells + 12 USA-column cells) **collapses to rank-1 at f = 0**, an *admissible* endpoint of the China-nationality interval. There, the only F3-exclusive component (`f·DESTn`) vanishes, so:

> **v_F3 == v_F4 exactly — `max|v_F3 − v_F4| = 0`, a TRUE, τ-independent zero — for ALL offshore-USD shares.** (Re-confirmed from `dp4_inputs.json` this run.)

Three facts compound it:

1. **Algebraic rank-1 collapse** at f = 0 (true zero, not a small number, not τ-dependent).
2. **Two open HOLES:** `f ∈ [0, 0.60]` (China-by-nationality fraction) and `s_usd ∈ [0, 1]` (offshore-USD/ABS share of the remainder).
3. **A single 2025-S1 snapshot:** one matrix, so the contagion-vs-substitution lead/lag discriminator that would split the shared USA-column direction is UNESTIMABLE-FROM-ONE-SNAPSHOT.

**Episode evidence (Part 1, by footprint, no pre-assignment):** No stress episode decidably isolates the F3-exclusive direction on disk. In particular the **2022 Russia reserve-immobilization / sanctions episode is UNDECIDABLE / F4-at-endpoint, NOT F3** — at the admissible f = 0 its offshore-destination + USA-column footprint lies on the shared F3=F4 (= F4 common-run) direction. 2008 GFC and 2020 COVID dash-for-cash load on the same shared common-run direction (undecidable for the separation); 2011–2013 debt-ceiling is F2-flavoured (thin F2/F4 split) and silent on the F3/F4 degeneracy. Pre-assigning 2022 to F3 was the specific planting failure this gate forbids; it is not committed.

## 4. The hazard as a bounded conditional surface — never a point

The hazard is reported **only** as a conditional surface over (f, s_usd), carrying its own explicit unidentified region:

- **Separation margin = smallest singular value** of the column-normalised operator (0 = footprints collapsed / observationally equivalent; 1 = orthogonal / cleanly separated). Threshold τ = 0.10, stated not tuned.
- **Monotone:** increasing in f (more China-non-USD destination = more separating support), decreasing in s_usd (more offshore-USD remainder = stronger confound).
- **Explicit unidentified region:** **the entire f = 0 edge for ALL s_usd** (margin = 0), **plus** small-f / high-USD-share (margin < τ).
- **The bound over the whole admissible plane:**

> **Infimum of the separation margin over (f ∈ [0, 0.60], s_usd ∈ [0, 1]) = 0**, attained along the entire f = 0 edge. The margin is **not bounded away from zero**, so the binding-mode is nowhere robustly identified.

A single hazard scalar would require inventing f and s_usd. **Refused.**

## 5. The grounded resolution path (ranked a > b > c > d)

All sources below were **fetched from their publishers on 2026-06-29** and quoted, or recorded as `NONE_AT_GRANULARITY`. No path is executed here; no hole is pinned; this is a roadmap, not a result.

- **(a) A second time period — a CPIS semiannual panel. GROUNDED-HIGH. The key finding.**
  IMF CPIS/PIP (dataflow `IMF.STA:PIP(5.0.0)`) returns **11 semiannual periods** for the exact load-bearing offshore cell US-holder → Cayman, **2020-S1 … 2025-S1** (2025-S1 = `2,798,130 mn`, matching the matrix), spanning the 2022 episode.
  Fetched: `https://api.imf.org/external/sdmx/2.1/data/IMF.STA,PIP,5.0.0/USA.A.P_TOTINV_P_USD.S1.S1.CYM.S?startPeriod=2020`.
  **This breaks the rank-1 degeneracy directly** — a temporal lead/lag makes v_F3 ≠ v_F4 *even at f = 0*, **without pinning either hole**. The discriminating data demonstrably **exists and is retrievable**. (Caveat: semiannual resolution; residency basis.)

- **(b) Currency split of the destination columns — PARTIAL.** BIS International Debt Securities (`WS_DEBT_SEC2_PUB`) carries a currency-of-denomination dimension and a real Cayman-resident USD-vs-total observation — but for **debt only**; CPIS has **no currency dimension**, and the equity/fund/ABS portion is uncovered. Breaks the degeneracy via exclusion where it applies.

- **(c) Counterparty-issuer nationality basis (pins f) — MEDIUM.** A reusable residence→nationality restatement dataset **exists and is downloadable** (Global Capital Allocation Project, `globalcapitalallocation.com/data`: "Restated Bilateral External Portfolios", "Restatement Matrices", "China in Tax Havens" replication, "Time Series for Chinese Firms' Presence in Tax Havens"). **BIS verified UNABLE** to supply the joint Cayman-residence × China-nationality cell (live query `Q.KY.CN…` → SDMX error code 100; residence and nationality published only as alternative marginals collapsed to the `3P` aggregate). Exact counterpart granularity / 2025 vintage of the GCAP matrices for this precise pool is **unverified in-page**.

- **(d) Offshore-USD / ABS share of the remainder (pins s_usd) — NONE_AT_GRANULARITY for ABS.** The USD-currency share is groundable for Cayman **debt** (BIS), but the **ABS share** — the specific confound from NBER WP 30865 fn. 3 ("U.S. banks are substantial issuers of ABS via Cayman domiciled SPVs") — is **published nowhere at this granularity**: the BIS `CL_ISSUE_TYPE` codelist has **no ABS flag** {A, C, E, G}, and NBER gives no share figure.

**Overall:** **unidentified-NOW but RESOLVABLE on the primary axis** — path (a), a CPIS time-series panel, is fully grounded and would break the rank-1 degeneracy — **with a residual unidentifiable-from-available-data component** (the ABS share, and an aligned counterpart-resolved 2025 China-nationality fraction). The "F3/F4 NOT ESTABLISHED" verdict is therefore not a permanent unidentifiability on the breaking-point mechanism; it is unidentified on *this* matrix, with the discriminating data shown to exist.

## 6. The honest end of the build

This is a **precisely-bounded non-identification** with an **exact, grounded path to resolution** — not a fabricated hazard, not a date. The build:

- located the **single binding reason** (algebraic rank-1 collapse at the admissible endpoint f = 0, true τ-independent zero);
- bounded the **hazard as a conditional surface** with **infimum = 0** and an explicit unidentified region (the whole f = 0 edge; small-f / high-USD-share);
- held the **planting guard** (2022 reported by footprint as F4-at-endpoint / undecidable, never pre-assigned to F3);
- and produced a **grounded resolution path** (a > b > c > d) showing the degeneracy is resolvable in principle by a CPIS panel that demonstrably exists, with a bounded residual that current published data cannot resolve.

"Hazard not identified" is the **established final result**, reported with its evidence — exactly as the build was designed to do rather than smooth over.

---

### Carried forward, NOT resolved
- **HOLE-1:** China-by-nationality fraction `f ∈ [0, 0.60]` — load-bearing; at f = 0 the operator is rank-1.
- **HOLE-2:** offshore-USD / ABS share `s_usd ∈ [0, 1]` of the (1−f) remainder — ABS component `NONE_AT_GRANULARITY`.
- **`$711,157.7 mn`** BIS banking-marginal floor (F1 noise floor; does not enter the F3/F4 operator).
- **Single-snapshot limit:** one 2025-S1 matrix on disk; the contagion-vs-substitution lead/lag discriminator is UNESTIMABLE-FROM-ONE-SNAPSHOT (resolvable via path (a), not executed here).

*No value was supplied for either hole. No point hazard was computed. The HOLDS verdict is not overturned. No date is output. The DP4 surface and its f = 0 rank-1 degeneracy stand unaltered.*
