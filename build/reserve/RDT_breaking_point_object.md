# RDT — The frontier / distance / hazard object (reserve-side exit trajectory)

**STATUS: OUTPUT — NOT ESTABLISHED until the verifier artifact exists** (`build/reserve/RDT_verify.json`, all_pass=true).

SOURCE: every number below is computed by `build/reserve/RDT_recompute.py` from two inputs — `build/reserve/RDT_coordinates.parquet` (primary; includes the `_AGG_COFER`/`_LMW_PCTL`/`_PREF`/`_SAFE_ANCHOR` input rows) and `build/reserve/rd0_evidence/lmw_Data.xls` sheet DATA (secondary-trajectory scan only) — plus `wb_pinksheet_MYFETCH.xlsx` solely as the P_ref equality cross-check. No network. Design pre-registered in `build/reserve/RDT_prediction.md`.

**No date. No probability. No composite is sold as "the" number.** Every distance and velocity is conditional on the Russia-calibrated frontier (N=1 completed anticipatory exit; see secondary-trajectory scan) and on each cell's observability flag; kinematic descriptor, not a forecast; no date, no probability.

## 1. The frontier (Russia's calibrated terminal state)

| coord | definition | terminal x_F | frontier REGION (2019-2021 range) | onset found (primary rule, origin end-2013) | onset (alt variant, origin end-2017) |
|---|---|---|---|---|---|
| k1 | USD share of disclosed FX reserves (pp) | 13.890 | [13.890, 30.430] | 2018 | 2018 |
| k2 | constant-price gold share (%) = tonnes*P_ref/(tonnes*P_ref+reserves_ex_gold) | 21.827 | [21.114, 22.839] | 2014 | 2019 |
| k3 | UST / total reserves (%), TIC December snapshot over WB year-end total | 0.618 | [0.618, 1.797] | 2016 | 2018 |
| k4 | CNY share of disclosed reserves (pp) | 21.780 | [15.280, 21.780] | 2017 | 2018 |

Realized move-onset ordering (earliest first): **k2 -> k3 -> k4 -> k1** (k2 2014, k3 2016, k4 2017, k1 2018). Verdict vs the pre-registered expected pattern: **DIFFERENT** — the qualitative sequence gold->UST->currency HELD; the mechanical k3 onset year is 2016 (expected 2018): the RATIO coordinate UST/total crossed the 10% threshold before the 2018 raw-dollar dump because Russia's total reserves contracted 2014-2016 while raw UST holdings were roughly flat — the raw $ collapse (102.5 -> 13.2 busd) is a 2018 event, quoted in the raw series.

Onset sensitivity: under the alternative origin (end-2017) the mechanical onsets are k1 2018; k2 2019; k3 2018; k4 2018 — 3 of 4 coordinates cross the threshold in 2018 itself, so the alternative origin does not resolve an ordering at annual resolution. Russia's full-path d-velocity (origin-2014 scaling, path-fractions/yr): k1 0.142857; k2 0.121392; k3 0.142857; k4 0.142857. Phase velocities show the regime shifts: k1 0.115519 (2014-18) vs 0.179308 (2018-21); k2 0.378415 (2014-18) vs -0.221306 (2018-21); k3 0.224615 (2014-18) vs 0.033846 (2018-21); k4 0.199036 (2014-18) vs 0.067952 (2018-21).

Secondary trajectories (mechanical scan of 64 LMW disclosers): **20 qualifiers** (USD-share decline >=15pp within <=10y, no recovery above start-10pp): Lithuania 1998->2004 (89.7->0.0pp, -89.7pp, final 0.0); United Kingdom 2008->2012 (70.9->6.2pp, -64.7pp, final 17.7); Sri Lanka 2020->2021 (84.6->25.5pp, -59.1pp, final 26.5); Switzerland 1996->2006 (84.0->32.8pp, -51.2pp, final 37.3); South Sudan 2014->2020 (93.7->47.3pp, -46.4pp, final 47.3); Russia 2017->2021 (55.3->13.9pp, -41.4pp, final 13.9); Malawi 2019->2021 (91.7->50.8pp, -40.9pp, final 57.9); Turkey 2014->2019 (83.4->45.0pp, -38.4pp, final 52.0); Macedonia 2016->2021 (38.1->0.0pp, -38.1pp, final 0.0); Namibia 2015->2021 (64.0->28.6pp, -35.4pp, final 36.3); Czech Republic 2005->2015 (47.9->14.8pp, -33.1pp, final 30.6); South Africa 2004->2013 (81.3->50.0pp, -31.3pp, final 67.8); Mongolia 2012->2014 (91.6->60.4pp, -31.2pp, final 75.2); Uganda 2020->2023 (91.7->64.0pp, -27.7pp, final 64.0); Denmark 2015->2017 (35.0->8.7pp, -26.3pp, final 9.8); Slovakia 2002->2008 (31.6->6.5pp, -25.1pp, final 6.5); Iceland 2014->2021 (56.1->33.9pp, -22.2pp, final 36.0); Romania 2008->2016 (32.5->11.8pp, -20.8pp, final 14.9); Peru 2003->2012 (97.0->77.2pp, -19.7pp, final 77.5); Croatia 2001->2006 (33.4->14.5pp, -18.9pp, final 18.6).
  - Turkey move-ordering over its window (adapted rule): k1=2016, k2=2017, k3=2017, k4=no terminal movement over the window (|x_t2-x_t1|=0) — vs Russia's k2->k3->k4->k1; where a qualifier is not one of the six holders its k2/k3 are not in the coordinates file and its ordering is not computed.

N=1 remains the central limitation for the CALIBRATION even though the scan finds other >=15pp USD-share decliners: Russia is the only qualifier with a completed, sanctions-anticipatory exit across all four coordinates ending at the frontier; other qualifiers inform the k1 margin only, and where their k2/k3 exist (the six holders) their move-ordering is compared above.

## 2. Distances and velocities (per coordinate FIRST; composite second)

### Russia — CALIBRANT (position ~ frontier by construction)

| coord | flag | vintage | raw position | d (2014 origin) | d (2018 origin) | v recent-3y (d/yr) | v full-window (d/yr) |
|---|---|---|---|---|---|---|---|
| k1 | OBSERVED | 2021 | 13.890 | 0.000 | 0.000 | 0.179 | 0.143 |
| k2 | OBSERVED | 2024 | 24.646 | -0.594 | 1.156 | 0.248 | 0.159 |
| k3 | OBSERVED | 2024 | 0.007 | -0.028 | -0.278 | 0.009 | 0.103 |
| k4 | OBSERVED | 2021 | 21.780 | -0.000 | -0.000 | 0.068 | 0.143 |

Composite (pre-registered construction): C = -0.155; members k1+k2+k3+k4; S1 median -0.014124; S2 OBSERVED-only -0.155 (k1+k2+k3+k4); S3 min k2 -0.594. Alt-onset (2018) C = 0.219.

### China

| coord | flag | vintage | raw position | d (2014 origin) | d (2018 origin) | v recent-3y (d/yr) | v full-window (d/yr) |
|---|---|---|---|---|---|---|---|
| k1 | INFERRED-BOUNDED | 2025 | [0.000, 100.000] (mid 50.000) pp (envelope; INFERRED-BOUNDED) | UNBOUNDED | UNBOUNDED | not computable on envelope | not computable on envelope |
| k2 | OBSERVED | 2025 | 3.750 | 0.892 | 0.978 | 0.004 | 0.010 |
| k3 | INFERRED-BOUNDED (TIC custody band) | 2025 | [18.233, 42.548] (mid 30.390) (band) | [0.398, 1.340] (mid 0.869) | [0.367, 1.202] (mid 0.785) | [-0.254, 0.359] (mid 0.053) | [-0.058, 0.093] (mid 0.017) |
| k4 | N/A-issuer | — | — | — | — | — | — |

China k1 (INFERRED-BOUNDED everywhere it appears): headline envelope [0.000, 100.000] (mid 50.000) pp — the union with the [0,100]-clipped residual route is effectively [0,100]; raw residual endpoints (unclipped): 2014 [12.78, 152.21], 2025 [-22.83, 153.53] pp. d is UNBOUNDED by interval arithmetic (the origin envelope straddles the frontier), so China's headline composite is degenerate — reported, not smoothed. SAFE-route SENSITIVITY (labelled, NOT the headline): position [33.879, 82.121] (mid 58.000) pp, d(2014 origin) [0.453, 1.547] (mid 1.000), d(2018 origin) [0.340, 2.314] (mid 1.327).

China k3 (custody BAND, INFERRED-BOUNDED everywhere it appears): ACTIVE-basis (primary) — cumulative net long-term Treasury transactions from 2014 on the TIC band, over WB denominators: H_active(2025) = [130.9, 1161.7] (mid 646.3) $bn, x_active = [3.49, 30.99] (mid 17.24)%, d_active = [0.065, 0.971] (mid 0.518); v_active recent-3y [0.063, 0.140] (mid 0.102) d/yr, full-window [0.029, 0.083] (mid 0.056) d/yr; raw active flow [-101.6, -85.0] (mid -93.3) $bn/yr (recent-3y, = mean net transactions) vs market-value holdings drift -61.2 (China-alone) / 15.8 (China+BEL+LUX) $bn/yr — the valuation confound is why the active basis is primary. Coherent custody-pairing sensitivity: d = 0.563003 (China-alone path) vs 0.946666 (China+BEL+LUX path); both paths approach on recent-3y (0.085113 / 0.032003 d/yr).

Composite (pre-registered construction): C = UNBOUNDED — DEGENERATE — a member d is UNBOUNDED (k1); members k1+k2+k3; S1 median DEGENERATE (unbounded member: k1); S2 OBSERVED-only 0.892 (k2); S3 min DEGENERATE (unbounded member — the minimum is unbounded below). Alt-onset (2018) C = UNBOUNDED — DEGENERATE — a member d is UNBOUNDED (k1).
SAFE-route sensitivity composite (labelled, NOT the headline): C = [0.581, 1.260] (mid 0.920) (2014 origin); [0.562, 1.498] (mid 1.030) (2018 origin).

### India

_composite over k2,k3 only: k1 and k4_cny are NOT-AVAILABLE (absent from the LMW panel) — noted, not imputed_

| coord | flag | vintage | raw position | d (2014 origin) | d (2018 origin) | v recent-3y (d/yr) | v full-window (d/yr) |
|---|---|---|---|---|---|---|---|
| k1 | NOT-AVAILABLE | — | — | — | — | — | — |
| k2 | OBSERVED | 2025 | 8.119 | 1.122 | 1.028 | 0.002 | -0.011 |
| k3 | OBSERVED | 2025 | 26.126 | 1.024 | 0.733 | 0.179 | -0.002 |
| k4 | NOT-AVAILABLE | — | — | — | — | — | — |

Composite (pre-registered construction): C = 1.073; members k2+k3; S1 median 1.073052; S2 OBSERVED-only 1.073 (k2+k3); S3 min k3 1.024. Alt-onset (2018) C = 0.881.

### Turkey

| coord | flag | vintage | raw position | d (2014 origin) | d (2018 origin) | v recent-3y (d/yr) | v full-window (d/yr) |
|---|---|---|---|---|---|---|---|
| k1 | OBSERVED | 2023 | 52.000 | 0.548 | 1.203 | 0.023 | 0.050 |
| k2 | OBSERVED | 2025 | 33.167 | -0.713 | -2.235 | 0.120 | 0.156 |
| k3 | OBSERVED | 2025 | 7.546 | 0.116 | 0.938 | -0.033 | 0.080 |
| k4 | OBSERVED | 2023 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 |

Composite (pre-registered construction): C = 0.238; members k1+k2+k3+k4; S1 median 0.331967; S2 OBSERVED-only 0.238 (k1+k2+k3+k4); S3 min k2 -0.713. Alt-onset (2018) C = 0.226.

### SaudiArabia

_composite over k2,k3 only: k1 and k4_cny are NOT-AVAILABLE (absent from the LMW panel) — noted, not imputed_

| coord | flag | vintage | raw position | d (2014 origin) | d (2018 origin) | v recent-3y (d/yr) | v full-window (d/yr) |
|---|---|---|---|---|---|---|---|
| k1 | NOT-AVAILABLE | — | — | — | — | — | — |
| k2 | OBSERVED | 2025 | 3.907 | 0.927 | 0.985 | -0.000 | 0.007 |
| k3 | OBSERVED | 2025 | 29.594 | 2.312 | 0.873 | -0.121 | -0.119 |
| k4 | NOT-AVAILABLE | — | — | — | — | — | — |

Composite (pre-registered construction): C = 1.619; members k2+k3; S1 median 1.619391; S2 OBSERVED-only 1.619 (k2+k3); S3 min k2 0.927. Alt-onset (2018) C = 0.929.

### Poland

| coord | flag | vintage | raw position | d (2014 origin) | d (2018 origin) | v recent-3y (d/yr) | v full-window (d/yr) |
|---|---|---|---|---|---|---|---|
| k1 | OBSERVED | 2022 | 41.000 | 1.226 | 0.900 | 0.151 | -0.028 |
| k2 | OBSERVED | 2025 | 14.063 | 0.485 | 0.498 | 0.127 | 0.047 |
| k3 | OBSERVED | 2025 | 22.259 | 0.803 | 0.651 | 0.004 | 0.018 |
| k4 | OBSERVED | 2022 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 |

Composite (pre-registered construction): C = 0.878; members k1+k2+k3+k4; S1 median 0.901384; S2 OBSERVED-only 0.878 (k1+k2+k3+k4); S3 min k2 0.485. Alt-onset (2018) C = 0.762.

Pre-registered expectation, evaluated mechanically: (i) Russia ordering **DIFFERENT**; (ii) China headline C midpoint = DEGENERATE (unbounded interval) -> branch: UNDETERMINED (midpoint degenerate); SAFE-route sensitivity C midpoint (labelled) = 0.920228 -> >=0.60: early path — expectation (ii) consistent; (iii) comparator composite midpoints: India 1.073052, Turkey 0.237853, SaudiArabia 1.619391, Poland 0.878452.

## 3. The hazard — conditional kinematics only

For every holder-coordinate with d > 0 and v > 0, tau = d/v — each tau strictly "if current velocity persists; velocities regime-shift (Russia's own did in 2014 and 2018); kinematic descriptor, not a forecast". If v <= 0: not approaching at current velocity, no tau.

| holder | coord | d (2014 origin) | v recent-3y | tau recent-3y (yr) | v full | tau full (yr) |
|---|---|---|---|---|---|---|
| Russia | k1 | 0.000 | 0.179 | at or beyond the frontier (d <= 0); no tau | 0.143 | at or beyond the frontier (d <= 0); no tau |
| Russia | k2 | -0.594 | 0.248 | at or beyond the frontier (d <= 0); no tau | 0.159 | at or beyond the frontier (d <= 0); no tau |
| Russia | k3 | -0.028 | 0.009 | at or beyond the frontier (d <= 0); no tau | 0.103 | at or beyond the frontier (d <= 0); no tau |
| Russia | k4 | -0.000 | 0.068 | at or beyond the frontier (d <= 0); no tau | 0.143 | at or beyond the frontier (d <= 0); no tau |
| China | k1 | UNBOUNDED (envelope) | — | not computable (unbounded interval input) | — | — |
| China | k2 | 0.892 | 0.004 | 234.3 | 0.010 | 90.6 |
| China | k3 | [0.398, 1.340] (mid 0.869) | [-0.254, 0.359] (mid 0.053) | velocity sign indeterminate within the interval (v spans 0); tau unbounded above; no point tau | [-0.058, 0.093] (mid 0.017) | velocity sign indeterminate within the interval (v spans 0); tau unbounded above; no point tau |
| India | k2 | 1.122 | 0.002 | 490.7 | -0.011 | not approaching at current velocity (v <= 0); no tau |
| India | k3 | 1.024 | 0.179 | 5.7 | -0.002 | not approaching at current velocity (v <= 0); no tau |
| Turkey | k1 | 0.548 | 0.023 | 23.6 | 0.050 | 10.9 |
| Turkey | k2 | -0.713 | 0.120 | at or beyond the frontier (d <= 0); no tau | 0.156 | at or beyond the frontier (d <= 0); no tau |
| Turkey | k3 | 0.116 | -0.033 | not approaching at current velocity (v <= 0); no tau | 0.080 | 1.4 |
| Turkey | k4 | 1.000 | 0.000 | not approaching at current velocity (v <= 0); no tau | 0.000 | not approaching at current velocity (v <= 0); no tau |
| SaudiArabia | k2 | 0.927 | -0.000 | not approaching at current velocity (v <= 0); no tau | 0.007 | 139.1 |
| SaudiArabia | k3 | 2.312 | -0.121 | not approaching at current velocity (v <= 0); no tau | -0.119 | not approaching at current velocity (v <= 0); no tau |
| Poland | k1 | 1.226 | 0.151 | 8.1 | -0.028 | not approaching at current velocity (v <= 0); no tau |
| Poland | k2 | 0.485 | 0.127 | 3.8 | 0.047 | 10.4 |
| Poland | k3 | 0.803 | 0.004 | 179.5 | 0.018 | 44.8 |
| Poland | k4 | 1.000 | 0.000 | not approaching at current velocity (v <= 0); no tau | 0.000 | not approaching at current velocity (v <= 0); no tau |

China k3 ACTIVE-basis kinematics (primary construction for China's k3 velocity): tau recent-3y: {"lower": 0.462172, "upper": 15.438977, "midpoint_label_only": 5.094741}; tau full-window: {"lower": 0.785978, "upper": 33.97638, "midpoint_label_only": 9.319223} — each "if current velocity persists; velocities regime-shift (Russia's own did in 2014 and 2018); kinematic descriptor, not a forecast".

**Regime-shift statement:** velocities regime-shift — Russia's own velocity changed discontinuously in 2014 and again in 2018 (phase velocities in section 1) — so every tau above is a kinematic descriptor under a frozen velocity, never a forecast and never a date.

**Boundary statement:** this measures the ANTICIPATORY-REALLOCATION regime only; a self-fulfilling RUN — the old F4, named as such — is a discontinuity OUTSIDE these kinematics: stated, unmeasured, unpriced, untimed; nothing here bounds, prices, or times it.

## 4. Limitations (in the object, not a footnote)

1. **Path calibration rests on Russia (N=1 completed exit).** The scan found 20 USD-share-decline qualifiers, but none is a completed all-coordinate anticipatory exit; Turkey's ordering over its own decline window differs from Russia's (currency first, gold/UST later), so the Russia ordering is not a universal law.
2. **China k1 is INFERRED-BOUNDED, never a point.** The residual route is nearly uninformative: raw endpoints [12.78, 152.21] pp (2014) and [-22.83, 153.53] pp (2025), clipped to [0,100]; the headline envelope is effectively [0,100] and every downstream headline number carries that width (hence the degenerate headline composite).
3. **China k3 custody band width**: at the latest published month (2026-04) the band is [651.1, 1542.1] $bn UST — **891.0 $bn wide** (China-alone vs China+Belgium+Luxembourg; Euroclear/Clearstream custody also serves non-China clients, so the band is intentionally wide).
4. **k4 is coarse**: CIPS per-country participation NOT-AVAILABLE (publisher does not publish it); LMW CNY shares are grounded zeros for Turkey/Poland and NOT-AVAILABLE for India/Saudi Arabia; swap lines are context flags only (India 0, Turkey 35, Saudi 50, Russia 150 bn CNY), never composite inputs.
5. **COFER 2025Q3 methodology break** (unallocated eliminated; IMF-staff imputation back to 2000Q1, TNM/2025/14) rides every residual-route input; **LMW thins in 2023** (n=31 disclosers vs ~49-56 earlier), so the 2023 percentiles behind the 2024-2026 residual and SAFE corridors rest on a thinner cross-section that freezes after 2023.
6. **The valuation split is a residual construction**: by-country valuation change exists only from 2023-02 (basis break marked in the 2023 rows); pre-2023 the split is bounded, and the residual absorbs coverage/custody reclassification, not only price — the 2022-2023 rates selloff cut market values with zero selling (the false-positive-exit confound), which is why China's k3 velocity is computed on the active basis.
7. Russia k2 denominators end 2024 and Poland k3 2026 is unpublished; each coordinate is measured at its own latest vintage, stated per cell.

STATUS: OUTPUT — NOT ESTABLISHED until the verifier artifact exists.
