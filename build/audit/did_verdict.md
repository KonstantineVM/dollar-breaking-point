# DiD / Event-Study F3 Test (reserve-freeze) — VERDICT (Part 2)

SOURCE: `build/audit/did_feasibility.json` (quarter list + all candidate pre-trends, untrimmed
and trimmed) + `build/results/did_pretrend_verify.json` (independent fast recompute; all
interaction coefficients reproduced to ≤1e-6, branch reproduced, and the 5%-trimmed per-quarter
group-mean table below persisted + self-reproduced to 1e-6) +
`build/data/nport/did_control_panels.parquet` (the per-fund-quarter active-flow-rate panel for
treated + C1 + C2 + C3, all 22 quarters) + the treated-group reconciliation vs
`build/data/nport/active_flow_panel.parquet` (streamed CN-haven rate reproduces the committed
treated rate to max abs rate diff 2.2e-16). Pre-registered design and decision rule:
`build/audit/did_prediction.md`. All numbers below are MEASURED and verifier-reproduced; none
hardcoded.

---

## VERDICT: NOT-IDENTIFIED

No candidate control — **C1** (non-CN haven, CYM/HKG/VGB residence, parent≠CN), **C2** (non-haven
EM equity), or **C3** (developed-market non-US equity) — has an **outlier-robust flat pre-trend**
against the treated group (CN-nationality haven active flow) over the pre-period 2019q4–2021q4.
The parallel-trends assumption that identifies the difference-in-differences / event study is not
satisfiable on this quantity as normalized. **Therefore no DiD β and no event-study coefficients
are estimated or reported** — reporting a β from a design whose pre-trend is not flat would be
presenting a confounded number as a causal effect. NOT-IDENTIFIED is a first-class, pre-registered
outcome (`did_prediction.md`, decision rule), not a failure to compute.

---

## The pre-trend evidence (all candidate controls; untrimmed AND trimmed)

Test: stack treated (treated=1) and control (treated=0) fund-quarter active-flow rates over the 9
pre-quarters 2019q4–2021q4; regress `rate ~ trend + treated + trend:treated` with fund fixed
effects and cluster-by-fund SE. PARALLEL ⇔ the `trend:treated` interaction is ≈0 and insignificant
(p>0.10). Because `active_flow_rate = active flow / lagged group total` has extreme tails when the
lagged denominator is tiny (a fund that held ≈nothing of the group last quarter), the test is run
untrimmed (pre-registered) and with the stacked-rate tails trimmed at 1% and 5% (robustness).

| control | variant | interaction coef | SE (cluster-fund) | p | parallel (p>0.10) |
|---|---|---|---|---|---|
| **C1** non-CN haven | untrimmed | −22.393 | 27.285 | 0.4118 | true |
| | trim 1% | −0.004264 | 0.001262 | 0.000733 | **false** |
| | trim 5% | −0.004842 | 0.000706 | 7.7e-12 | **false** |
| **C2** EM equity | untrimmed | +13.122 | 7.850 | 0.0947 | false |
| | trim 1% | −0.005000 | 0.001470 | 0.000674 | **false** |
| | trim 5% | −0.006173 | 0.000788 | 5.5e-15 | **false** |
| **C3** DM equity | untrimmed | +125.810 | 246.297 | 0.6095 | true |
| | trim 1% | −0.006678 | 0.001129 | 3.5e-09 | **false** |
| | trim 5% | −0.007565 | 0.000651 | 6.0e-31 | **false** |

**parallel_robust (untrimmed AND 1%-trim both parallel): C1 = false, C2 = false, C3 = false.**

### The outlier artifact, stated explicitly (this is the load-bearing point)

Untrimmed, C1 (p=0.41) and C3 (p=0.61) read "parallel" — but this is **not** measured flatness. It is
**SE-inflation** from a handful of extreme-tail `active_flow_rate` values (tiny-lagged-denominator
fund-quarters, rates reaching 1e6–2e7). Those outliers blow the cluster-robust SE up to 27 (C1) and
246 (C3), so the interaction cannot be distinguished from zero and everything spuriously looks
parallel. Remove just the 1% tails and the picture sharpens: the interaction is now **precisely
estimated** (SE ≈ 0.001) and **strongly non-zero** for every candidate — C1 p=0.0007, C2 p=0.0007,
C3 p=3.5e-9 — i.e. **every candidate control has a demonstrably NON-parallel pre-trend.** The
untrimmed "parallel" for C1/C3 is an artifact; the trimmed test is the true reading. Trimming does
not cherry-pick toward a conclusion: **C1 and C3 flip from (spurious) parallel to non-parallel**
under trimming, while **C2 — already non-parallel untrimmed (p=0.0947 < 0.10) — stays
non-parallel**. So after removing the outliers **no candidate is robustly parallel**, and the
pre-registered selection rule (choose a control with a genuinely flat pre-trend; if none,
NOT-IDENTIFIED) returns NOT-IDENTIFIED. (`did_pretrend_verify.json` records
`outlier_flipped_to_nonparallel_when_trimmed` = [C1, C3] — only C1/C3 flip; C2 was non-parallel
throughout.)

### Per-quarter pre-period group-mean active-flow rate (so the divergence is visible)

Raw (untrimmed) per-quarter means are themselves outlier-contaminated and swing into the hundreds/
thousands from single fund-quarters (retained in `did_feasibility.json`), which is why the untrimmed
interaction is uninformative. The **5%-trimmed** per-quarter group means (below) show the genuine,
non-artifact structure: the control groups sit systematically **above** treated across the pre-period,
and the gap moves with the quarter — a non-parallel pre-trend, consistent with the trimmed interaction
tests. Trim definition (deterministic): for each (group, quarter) cell, `scipy.stats.trim_mean(rate,
0.05)` — symmetric 5% two-sided trim of that cell's own rate observations, then mean of the remainder.

| quarter | treated | C1 | C2 | C3 |
|---|---|---|---|---|
| 2019q4 | 0.0192 | 0.0374 | 0.0117 | 0.0184 |
| 2020q1 | −0.0013 | 0.0032 | −0.0338 | −0.0236 |
| 2020q2 | 0.0387 | 0.0595 | 0.0680 | 0.0520 |
| 2020q3 | 0.0307 | 0.0602 | 0.0515 | 0.0220 |
| 2020q4 | 0.0291 | 0.0529 | 0.0757 | 0.0302 |
| 2021q1 | 0.0436 | 0.0917 | 0.0775 | 0.0712 |
| 2021q2 | 0.0088 | 0.0472 | 0.0437 | 0.0473 |
| 2021q3 | −0.0049 | 0.0476 | 0.0110 | 0.0342 |
| 2021q4 | −0.0065 | 0.0134 | 0.0418 | 0.0167 |

(SOURCE for the trimmed table above: `build/results/did_pretrend_verify.json` →
`per_quarter_group_means_trim5pct.means` — these exact values are computed and persisted by the
verifier from `did_control_panels.parquet` alone and reproduce to 1e-6 on re-run
(`self_reproduce_match_1e-6` = true; `self_reproduce_max_abs_diff` = 0.0). The verifier also
reproduces every interaction coefficient, `all_coef_match_1e-6` = true. Untrimmed per-quarter means
retained separately in `did_feasibility.json` → `candidate_controls[*].pretrend.
per_quarter_group_means`.)

**Conclusion of the pre-trend stage:** the parallel-trends validity check could NOT be validly passed
by any control. A valid parallel control does not exist among the EM-equity, DM-equity, and non-CN-
haven candidates on this active-flow normalization.

---

## Comparison to the active-flow continuous-shock panel result

`build/audit/active_flow_verdict.md` (Part 3 of the prior active-flow test) reached
**INSUFFICIENT-POWER, leaning NO-F3**: the sanctions β on valuation-stripped active flow was
**−0.009211 WITH the regulatory control** (−0.001698 without), the negative sign appearing only with
the control, and **insignificant on the honest wild-cluster bootstrap (p≈0.16)** — an insignificant
near-null the instrument lacked the power to move to a terminal NO-F3.

**Did switching to the DiD / event-study estimator change the answer? No.** The event study is, in
principle, the estimator better matched to a discrete sanctions event than a continuous-shock panel
with leave-one-quarter-out (LOQO removes the identifying event quarters and makes a real event look
fragile — the reason the DiD was worth running). But the event estimator's identifying assumption is
a **parallel control**, and that assumption **fails on the available data**: once the rate outliers
are removed, all three candidate controls have strongly non-parallel pre-trends. So the DiD does
**not** deliver a cleaner identification here and **cannot rescue** an event effect that the
continuous-shock test left as an insignificant near-null. The two estimators do not disagree: the
continuous-shock test said "cannot resolve" (INSUFFICIENT-POWER); the event estimator says "cannot
identify" (NOT-IDENTIFIED). Neither surfaces a robust negative active-flow response to the freeze;
switching estimators did not convert the near-null into an effect.

Honest note on robustness: **no leave-one-quarter-out was run here — correctly**, because LOQO is
invalid for an event study (it deletes the identifying event quarters). The pre-trend test WAS the
design's validity check, and it failed. That failure is the robustness finding, not a gap in it.

---

## Comparison to the Part-0 pre-registered prediction

`did_prediction.md` committed, before any control was built or any pre-trend known, a primary
prediction of **DiD-NULL or NOT-IDENTIFIED**, with the single falsifiable commitment that a NEGATIVE,
significant β against a demonstrably flat-pre-trend control would REFUTE it (verdict DiD-LOADS).

**Prediction HELD.** NOT-IDENTIFIED is one of the two named primary outcomes, and it is reached on
measured grounds: every candidate control's pre-trend was built, tested (untrimmed and trimmed),
verifier-reproduced, and reported; none is robustly parallel; and no β is reported from the broken
design. The falsifiable commitment is not triggered — there is no control with a demonstrably flat
pre-trend against which a negative significant β could stand, so DiD-LOADS does not obtain. The
anti-planting commitments hold: the control was selected by the fixed pre-trend rule (not by any β),
all candidates' pre-trends are on the record, and the outlier artifact that would otherwise have
smuggled C1/C3 in as "parallel" is exposed rather than relied upon.

---

## Scope / what was NOT done

No DiD or event-study regression was estimated — there is no valid design to estimate one on. DP2–DP6,
the ledger, `build/approvals/`, the operator tagging, and prior committed files were not touched. No
date, no bare probability, no hazard claim.
