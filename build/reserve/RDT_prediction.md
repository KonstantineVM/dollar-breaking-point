# RDT — Exit-trajectory model: PRE-REGISTERED DESIGN + PREDICTION

**Timestamp: 2026-07-01 (committed BEFORE any RDT data build — the TIC / gold-history / RMB-adoption
sources are fetched in Part 1 AFTER this commit; the coordinates file, the Russia calibration, and every
distance/velocity/composite do not yet exist).**

Pre-registration, committed first. The expectation below **may be REFUTED**, and any endpoint is a valid
finding — "China has barely moved" and "China is far along" are equally valid outputs; the object reports
whatever the coordinates say. The gate endpoints OBJECT-BUILT and NOT-BUILDABLE-per-coordinate are both
valid; a coordinate whose data cannot be grounded is reported as such and the object is built on the
remainder.

## What this stage is (the reframe, without scope reduction)

RDT supersedes the event-study framing of RD3–RD6 **without reducing its scope**: every remaining surface
enters as a coordinate of a state vector — S1 → k1 (currency composition), S2 → k2 (gold), S3 → k3 (UST),
S4 → k4 (RMB/alternative adoption), S5 (decomposition inputs) → the valuation-split and constant-price
machinery INSIDE k2/k3, RD6 (synthesis) → the composite and the object. The question changes from "did X
respond to the freeze" (exhausted: RD1 = INSUFFICIENT-POWER, RD2 = GOLD-NULL) to the charter's object:
**where is each reserve manager on the dollar-exit path, and how fast is it moving.**

Empirical basis, on disk: exit — where it has been observed — was **anticipatory and gradual**. Russia,
the one sanctioned holder we observe, executed its exit 2014–2021, BEFORE the freeze (USD 47.0% (2007) →
13.89% (2021); CNY 0 → 21.78%; replicated. SOURCE: `build/reserve/RD1_result.json`, from
`build/reserve/rd0_evidence/lmw_Data.xls` sheet DATA). Russia therefore calibrates the path; every other
holder is measured by position and velocity along it. Stated honestly: the RD1/RD2 nulls are NOT evidence
FOR the trajectory model — they exhausted the event framing; the trajectory framing is measured on its own
coordinates.

Deliverable: the **frontier / distance / hazard** object. **NEVER a date. NEVER a bare probability.**

## The state space (fixed here) — with the coordinate-applicability matrix

| coord | definition (distance coordinate in bold) | Russia | China | India | Turkey | Saudi Arabia | Poland |
|---|---|---|---|---|---|---|---|
| k1 | **USD share of disclosed FX reserves (pp)** — LMW annual panel, read-only from disk | OBSERVED (→2021) | **INFERRED-BOUNDED** (rule below; never a point) | expected NOT-AVAILABLE (verify vs panel) | OBSERVED | expected NOT-AVAILABLE (verify vs panel) | OBSERVED |
| k2 | official gold TONNES (extended history ≥2010, merged with the RD2 panel); **distance coordinate = constant-price gold share** (rule below); raw tonnes always alongside | OBSERVED | OBSERVED | OBSERVED | OBSERVED | OBSERVED | OBSERVED |
| k3 | UST position, TIC Major-Foreign-Holders monthly (annual snapshot = December); **distance coordinate = UST / total reserves (%)**; raw $B always alongside | OBSERVED | OBSERVED as custody **BAND** (rule below; never a point) | OBSERVED | OBSERVED | OBSERVED (named line from 2016; earlier grouped — verify from source) | OBSERVED |
| k4 | alternative-adoption: **CNY share of disclosed reserves (pp, LMW)** as the quantitative sub-coordinate; PBoC swap-line (year signed, size) and CIPS participation as FLAGS (context, not composite inputs) | OBSERVED | **N/A — China is the alternative's issuer** (applicability, not a data hole) | flags only (verify) | OBSERVED | flags only (verify) | OBSERVED |

Actual observability is recorded per cell in `RDT_coordinates.parquet` (flag ∈ {OBSERVED,
INFERRED-BOUNDED, NOT-AVAILABLE}); the matrix above is the expected pattern and is verified, not assumed.

**k2 constant-price rule (S5 machinery; RD2 Confound-2 discipline).** The distance coordinate is
`tonnes·P_ref / (tonnes·P_ref + reserves_ex_gold_USD)` with **P_ref = the 2021 annual mean of the WB Pink
Sheet monthly gold price**, computed in the recompute from the committed
`build/reserve/rd2_evidence/wb_pinksheet_MYFETCH.xlsx` — never hardcoded, and **never the market-price
share** (a market-price share moves with zero buying; that was RD2's Confound 2). Raw tonnes are reported
alongside every use.

**k3 rules (S5 machinery; the custody and valuation confounds).**
- China is a custody **BAND**: lower bound = the China (mainland) line alone; upper bound = China +
  Belgium + Luxembourg (Euroclear/Clearstream custody masking). The band is stated; a point is never
  picked. The band is intentionally wide (Belgium/Luxembourg custody also serves non-China clients) and
  is labelled as such.
- **Valuation split**: TIC net transactions in Treasuries (active, manager decision) are decomposed
  against holdings changes (market value); the 2022–2023 rates selloff cut market value with zero selling
  — the FALSE-POSITIVE-exit confound. If a clean transactions-by-country series cannot be grounded, the
  active-vs-valuation split is **BOUNDED** per year and the bounding is disclosed. k3 velocity for China
  is computed on the **active basis primary**, raw alongside.

**k1-China rule (INFERRED-BOUNDED; never a point).** Two routes, both reported:
- **Residual route (per this stage's instruction)**: China's USD share s_C(t) is bounded from
  `s_C = (W_t·A_t − s_NC·(A_t − R_C,t)) / R_C,t`, where W_t = the PUBLIC IMF COFER world allocated USD
  share, A_t = world allocated total ($), R_C,t = China total reserves ($, WB/SAFE), and s_NC (the
  non-China rest-of-world USD share) ranges over the **10th–90th percentile of the LMW discloser USD-share
  distribution** at the nearest LMW year. Both endpoints reported. *Conflict surfaced, not silently
  resolved*: RD0 scoped the reserve-side program to bypass the IMF aggregate as evidence; this stage
  explicitly instructs a residual-based bound for k1-China. Resolution recorded here: the COFER **public
  world aggregate** enters ONLY as the bounding input for this one INFERRED-BOUNDED cell — never as
  country-level evidence and never as a freeze-response observation. China's inclusion in COFER "allocated"
  is grounded against the IMF's own coverage notes, not assumed; if it cannot be grounded the residual
  carries that caveat explicitly.
- **SAFE-anchor route (corroboration + path origin)**: SAFE's own published one-off disclosure of China's
  reserve currency composition (reported to exist in a SAFE annual report; the agent must locate and quote
  the actual disclosure — it is NOT asserted from memory here). The disclosed point anchors China's k1
  **origin**; a current-value corridor is formed as anchor ± the 10th–90th percentile of |Δ USD share|
  over the elapsed horizon across LMW disclosers.
- Final k1-China interval = the **envelope (union)** of the two routes where both ground (conservative);
  the single grounded route otherwise; **NOT-AVAILABLE** if neither grounds. The interval propagates to
  every distance and composite by interval arithmetic; it is never collapsed to a point or to its
  most-null endpoint.

## Calibration design (fixed here)

- **Russia path.** Onset PRIMARY = 2014 (Crimea sanctions regime); ALTERNATIVE = 2018 (April-2018
  sanctions; the UST-dump year). Origins = Russia's end-2013 / end-2017 values. **Both reported
  everywhere.**
- **Frontier (terminal state) per coordinate** = Russia's last pre-freeze observation (k1, k4: 2021;
  k3: Dec-2021; k2: the mean of the 2020–2021 plateau), with the 2019–2021 range reported as the frontier
  REGION. Post-freeze Russia is outside the anticipatory regime (the freeze truncates the path); every
  terminal value is verified from the built series, not assumed.
- **Move-onset (ordering) rule, mechanical**: onset(k) = the first year t > 2013 with
  |x_t − x_2013| ≥ 0.10·|x_F − x_2013|, with sign(x_t − x_2013) = sign(x_F − x_2013), sustained (the
  condition holds for all t′ ≥ t). The expected pattern — gold moving from 2014, the UST dump in 2018,
  the currency share completing by 2021 — is **verified from the data, not assumed**.
- **Secondary trajectories scan, mechanical**: every LMW discloser with a USD-share decline ≥ 15pp
  between two observations ≤ 10 years apart whose final panel value does not recover above
  (start − 10pp). All qualifiers reported; their move-ordering compared to Russia's where their k2/k3
  exist. **If none qualifies, N=1 is stated as the model's central limitation in the object itself, not a
  footnote.**

## The distance metric (fixed here; per-coordinate PRIMARY, composite second)

- **Per-coordinate path-fraction remaining** (the primary output):
  `d_k(h,t) = (x_k(h,t) − x_F,k) / (x_k(h,2014) − x_F,k)`
  — d = 1: at one's own 2014 position (no movement); d = 0: at the frontier; d < 0: beyond it; d > 1:
  moved AWAY from the frontier. The alternative-onset (2018) variant replaces the origin year. Interval
  inputs (China k1, k3 band) propagate by interval arithmetic. **RAW coordinate values (pp, tonnes, $B,
  %) are always reported before and beside any path-fraction.**
- **Degeneracy guard**: if |x_O(h) − x_F| < 0.20·|x_O(Russia) − x_F| for a coordinate, the path-fraction
  is NOT-MEANINGFUL for that holder-coordinate (the holder's origin is already near the frontier);
  raw-space distance is reported instead. Stated wherever it fires.
- **Velocity**: v_k = −Δd_k/Δt (path-fractions per year; positive = toward the frontier), on TWO windows:
  **recent-3y** (the last 3 years of that coordinate's observations) and **full-window** (2014 → latest).
  **Both are always reported**; k3-China velocity on the active (transactions) basis primary.
- **THE composite (one, pre-registered)**: C(h) = the **unweighted mean of d_k** over the coordinates
  applicable AND available (OBSERVED or INFERRED-BOUNDED) for holder h; intervals propagate.
  **Sensitivities (computed, never asserted)**: S1 = the median of d_k; S2 = the OBSERVED-only mean
  (INFERRED-BOUNDED cells excluded — a labelled sensitivity, never the headline); S3 = min_k d_k (the
  nearest-to-frontier coordinate). Per-coordinate distances are reported FIRST; **no composite is sold as
  "the" number.**
- **Asynchronous vintages**: each coordinate is measured at its own latest observation; the vintage year
  is stated per cell.

## Hazard form (fixed here)

Conditional kinematics ONLY. Per holder-coordinate: (d, v_recent-3y, v_full, and τ_k = d_k / v_k **IF**
v_k > 0), every τ labelled "**if current velocity persists**" and carrying the regime-shift caveat:
**velocities regime-shift — Russia's own velocity changed discontinuously in 2014 and again in 2018 — so
τ is a kinematic descriptor, not a forecast.** If v_k ≤ 0: "not approaching at current velocity," and no
τ is computed. **Explicitly: no date, no probability** — a τ is a conditional duration under a frozen
velocity, presented only with its conditionality attached, never converted to a calendar date.

## Binding-mode boundary (stated, not modeled)

This stage measures the **ANTICIPATORY-REALLOCATION regime** — gradual, decision-driven movement (the
F3-flavoured channel). A self-fulfilling **RUN** (the old F4) is a discontinuity OUTSIDE these kinematics:
it is a **stated, unmeasured boundary**; nothing in the object bounds, prices, or times it. Two
non-conflations, fixed here: (1) the RDT frontier is an **empirical anchor** — the terminal state of the
one completed exit observed — NOT the DP-arc's theoretical multiple-equilibrium frontier; the DP-arc
terminal verdict (UNIDENTIFIABLE-FROM-AVAILABLE-DATA) stands untouched. (2) Kinematics are **not
attribution**: RD2 established that the post-2022 gold move is not sanctions-differential; the object
measures where holders ARE and how fast they MOVE, not why.

## The flipped symmetric guard (verbatim; BOTH directions are violations)

**DRAMATIZATION vectors — violations:** a metric or normalization choice that places China close to the
frontier; a custody-UNADJUSTED China UST series read as selling; a market-value holdings drop read as
selling (the valuation confound); a flattering velocity window (reporting only whichever of recent-3y /
full-window shows the faster approach).

**ZEROING vectors — violations:** silently dropping the inferred k1 from China's composite; diluting a
recent acceleration inside a full-window average (reporting only the full window); collapsing a bounded
interval to its most-null endpoint.

Commitments: both velocity windows always reported; both interval endpoints always carried; every
exclusion labelled (S2 is a labelled sensitivity, not the headline); per-coordinate before composite.

## The falsifiable expectation (stated; the object reports what it measures)

> **(i) Russia ordering:** the move ordering replicates gold-from-2014 / UST-dump-2018 /
> currency-share-completing-by-2021 under the mechanical onset rule. REFUTED if the built series show a
> different ordering — the calibration then uses the ordering found.
> **(ii) China position:** China sits EARLY-TO-MID path — the pre-registered composite C (mean d,
> interval midpoint) **≥ 0.60** (no more than ~40% of the Russia path traversed), with its movement
> concentrated in k2 (post-2022Q4 tonnage) and a slow k3 active decline. **REFUTED if the C midpoint
> < 0.40** — "China is far along" is then the finding, reported with equal confidence. Between 0.40 and
> 0.60: neither confirmed nor refuted; reported as measured.
> **(iii) Comparators:** dispersion expected (positions spread along the path); no specific ordering
> predicted. No velocity signs are predicted for any holder.

## Anti-planting commitments

- Every distance, velocity, ordering, and composite is **read from the recompute**
  (`build/reserve/RDT_recompute.py`, regenerating everything from `RDT_coordinates.parquet` — including
  the aggregate input rows stored there — with no network), never hardcoded; the verifier
  `RDT_verify.json` byte-reproduces.
- **Integrity anchors (a failed anchor is a broken build, not a finding):** the coordinate build must
  replicate (a) Russia's 2018 UST collapse — order ~$100B → ~$15B within months — with the actual monthly
  values quoted from the fetched TIC data, and (b) Russia's 2014–2020 gold accumulation, quoted from the
  fetched history. Either failing BLOCKS the object.
- Sources fetched, not asserted; NOT-AVAILABLE recorded honestly; an observability flag on every cell;
  the RD2 gold panel overlap (2019+) reconciled and the reconciliation reported.
- China k1 and k3 enter every downstream number as intervals/bands, never points.
- Coefficient-free stage: there is no estimator whose sign can be tuned; the corresponding discipline here
  is that **metric, windows, onsets, guards, composite, and sensitivities are all fixed in this document
  before any coordinate exists.**

## Scope

Writes ONLY `build/reserve/RDT_*` and `build/reserve/rdt_evidence/*`. DP2–DP6, RD1, and RD2 artifacts are
read-only inputs. No date, no bare probability, no run model, no composite sold as "the" number. RD3–RD6's
surfaces are absorbed as coordinates (scope preserved), and nothing beyond RDT is presumed — what follows,
if anything, is decided at the gate.
