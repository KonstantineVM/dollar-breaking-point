# RD2 — Surface 2 (gold): VERDICT

**SOURCE:** `build/reserve/RD2_gold_panel.parquet` (3,444 rows = 123 countries x 28 quarters, 2019Q1–2025Q4;
DV = `net_gold_purchases_tonnes`, physical within-country q/q first difference). Coefficients read from the
numpy estimator in `build/reserve/RD2_recompute.py`; persisted in `build/reserve/RD2_result.json`; byte-reproduced
by `build/reserve/RD2_verify.json` (`all_pass: true`). Treated/control from the panel's ES-11/1-vote-based
`treated` flag. NOT hardcoded.

## VERDICT: GOLD-NULL

**The post-2022 gold surge is UNIVERSAL and the treated units' gold-value rise is mostly PRICE, not tonnage.
Once the common trend (quarter FE) and valuation are stripped, sanctions-exposed central banks did NOT accumulate
gold tonnage differentially more than US-aligned holders.** The DiD design is valid (flat pre-trend), and the null
is well-identified (not a power failure): the differential is a precise zero, and the treated buying that did occur
lags the freeze rather than tracking it. Reported sign-agnostically; the estimator was free to return a positive
differential and did not.

## The numbers that decide it (all from the estimator)

- **Treated = 24 (ES-11/1 No/Abstain), Control = 90 (Yes).** Turkey voted YES → CONTROL in the headline; it is the
  only `robust_nonwestern_buyer`, added to treated only in the labelled robustness variant (treated = 25 there).

- **DiD Treated × Post (headline, Turkey excluded): β = +0.104 tonnes/quarter, SE = 1.253, p = 0.934,
  95% CI [−2.35, +2.56], n_obs = 2,758.** A precise zero. GOLD-REALLOCATION would be a POSITIVE, significant β; this
  is neither. The CI excludes a ±5 t/qtr differential, so this is an identified NULL, not INSUFFICIENT-POWER.

- **DiD robustness (Turkey included): β = +0.343 t/qtr, p = 0.776.** Still null. The finding is **not**
  gerrymander-sensitive — no positive differential appears under the broader buyer set either.

- **Pre-trend joint Wald = 13.05, df = 10, p = 0.221 → FLAT.** The parallel-trend assumption holds; the design is
  valid, so the null is interpretable (this is NOT the NOT-IDENTIFIED branch). Every event-study lead AND lag is
  individually insignificant (all CIs cross zero); **no lag loads on 2022Q1+** — the differential is not timed to
  the freeze.

- **Confound 1 — universal, not treated-concentrated.** Raw per-quarter means: in the post window BOTH arms buy
  (treated ≈ 1–3 t/country/qtr, control ≈ 0.5–1). Treated also bought more than control in several PRE-freeze
  quarters (2019Q2–Q4, 2021Q3). Country FE absorbs that standing gap; the change-in-gap (β) is ~0. The surge is
  broad central-bank buying, which is exactly Confound 1.

- **Confound 2 — mostly price, not tonnage.** Over 2021Q4→2024Q4 (both tonnes and price observed; 18 of 24 treated
  units have full endpoints, 6 excluded for a missing tonnage endpoint), the treated aggregate gold-VALUE rise
  decomposes to **tonnage-driven 12.4%, price-driven 81.7%, interaction 5.9%.** A gold-share rise that is mostly
  price is a NULL for accumulation.

## China and Russia — observed (the reason this surface can test what S1 could not)

- **China:** PBoC gold **flat at 1,948.3t from 2021Q4 through 2022Q3** — i.e. through the two quarters *after* the
  Feb-2022 freeze — then **+62.2t in 2022Q4**, reaching 2,306.3t by 2025Q4. First material post-freeze purchase
  **LAGS the freeze by 3 quarters**; total accumulation 2022Q3→2025Q4 = **+358.0t**. China did accumulate real
  tonnes, but the timing is inconsistent with a freeze response and it does not produce a treated-vs-control
  differential once the universal trend is removed.

- **Russia:** CBR gold sits on a **plateau ~2,326–2,336t across the entire post-freeze window** (2022Q1–2025Q4);
  net change ≈ **+24.9t** with small ± moves near reporting noise. Stated honestly: CBR disclosure continued at
  reduced granularity; the plateau is what the *reported* tonnage shows, not an inferred accumulation. Russia did
  NOT materially add gold tonnage post-freeze on the reported series.

## Which null (per the pre-registered rule)

GOLD-NULL fires on **all three** of its stated grounds simultaneously: **(1) no treated-vs-control differential
(universal surge)**, **(2) the treated value rise is price not tonnage (81.7% price)**, and **(3) the treated
buying that occurred is mistimed (China lags 3 quarters; no lag loads at 2022Q1+).** Not NOT-IDENTIFIED (pre-trend
flat). Not INSUFFICIENT-POWER (CI excludes a ±5 t/qtr move).

## Comparison to the RD2 prediction and to RD1

- **RD2 prediction: HELD.** The pre-registered primary prediction was GOLD-NULL or INSUFFICIENT-POWER — the surge
  likely universal and partly price-driven. Both confound strips fired as anticipated. The one falsifiable
  commitment (positive, significant, pre-trend-valid, freeze-timed, tonnage-not-valuation differential → REFUTED →
  GOLD-REALLOCATION-PRESENT) is **not met**: the differential is a precise zero, mistimed, and mostly price. The
  prediction is **not refuted**.

- **Versus RD1 (S1, disclosed currency composition): INSUFFICIENT-POWER** there — the treated units (China absent,
  Russia stopped disclosing post-freeze) are unobserved, so S1 *could not test* the thesis. On gold the treated
  units **ARE directly observed** (China and Russia both publish tonnage), so RD2 delivers what S1 could not: an
  **identified answer**. That answer is that the escape-hatch surface does **not** load — the observed treated
  accumulation is universal-trend and price, not a sanctions-specific tonnage reallocation.

The three objects are not produced on this surface: RD2 tests one escape-hatch channel and returns a null on it. No
frontier, distance, or hazard is claimed here, and no reserve-run equilibrium is asserted or dated.
