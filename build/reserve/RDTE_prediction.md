# RDT-E — The migration bound (the perimeter fork): PRE-REGISTERED DESIGN

**Timestamp: 2026-07-02 (committed BEFORE any RDT-E build — the SLT class/mirror analysis, the
official-series fetches, the methodology verification, and the bound do not yet exist).**

Pre-registration, committed first. Symmetric: **MIGRATION-DOMINANT (the exit reading demotes to custody
housekeeping), MIGRATION-MINOR (the non-US reading survives; currency still k1-walled), and
UNINFORMATIVE-BOUND (the fork stays open) are all promotable landings.** Beneficial ownership inside the
custody centers is confidential — the fork cannot be RESOLVED; this stage BOUNDS it. Read-only on prior
artifacts except the tasked insert-only object amendment. No date, no probability, no currency guess.

## The unknown, and the identity it enters

Migration M = the share of China's −446.493 $bn US-LT-securities active decline (RDT-C/D, verdict axis)
that is custody relocation to Euroclear/Clearstream (off the China line, onto BE/LU — still US paper,
beneficially unchanged) rather than true departure from US paper. Then
**ΔnonUS-true = 494.977 − M**, with the pool caveat and the k1 wall riding the interval everywhere.

## The three caps and their mechanical combination (fixed here)

**Windows fixed:** the RDT-B verdict axis (2023-05..2026-04) is the verdict window; the full window
(2013-01→latest) is context. **Classes fixed:** the SLT schema (Treasury LT / agency LT / corporate LT /
equity LT), as carried by the on-disk by-country by-class tables (positions from 2020-01; the pre-2020
record is total-UST only via MFH — what each cap can see is stated per window).

- **Cap A — class-matched accretion cap.** Migration in class c requires both a China decline in c and a
  BE/LU accretion in c over the window: `capA = Σ_c min( max(−ΔChina_active_c, 0),
  max(ΔBELU_active_c, 0) )`, active basis. The accretion in classes China does not hold (or did not sell)
  caps out mechanically. Blind spot: within-window netting (China sells c while others also feed BE/LU's
  c-line — capA counts gross room, not China's share of it); direction: capA can only OVERSTATE M's
  ceiling, which is the safe direction for a cap.
- **Cap B — synchronized-mirror timing cap.** Per class, the matched mirror mass
  `Σ_months min( China monthly decline, BE/LU monthly rise )`, computed contemporaneously AND with the
  BE/LU rise allowed to lag/lead by up to 3 months (both reported; **the ±3-month version is the cap**,
  the contemporaneous version is context). **Blind spot, stated up front: STAGGERED migration — sell on
  the China line and repurchase via Euroclear more than 3 months later, or drip-fed — evades this cap
  entirely.** A small capB therefore does NOT prove small migration on its own; it grounds the minimum
  only jointly with the other caps' blind spots stated.
- **Cap C — official-classification cap (conditional).** Grounds ONLY IF both: (a) the retained/fetched
  TIC methodology documents establish that Euroclear/Clearstream-custodied official money classifies as
  PRIVATE in TIC (the passage QUOTED verbatim; if the documents are indeterminate, say so — capC does not
  ground and the bound rests on A/B); and (b) the aggregate foreign-official series actually DECLINED
  over the window (if official aggregates rose, capC is uninformative and does not ground). If both hold:
  `capC = the decline magnitude` of the aggregate foreign-official UST series (TIC) and of the FRBNY
  H.4.1 foreign-official custody series, each reported separately; the cap value = the LARGER decline
  (conservative-high). Blind spot: other countries' official net purchases mask a China-migration drain
  (capC is a soft cap valid under the stated assumption that net other-official flows were not strongly
  positive; the observed other-official context is reported next to it).

**Combination (mechanical):** `M_hi = min over the caps that GROUND` (a cap that does not ground is
excluded, never zero-filled); each cap is reported separately, with its value and blind spot, BEFORE the
minimum. `M_lo = 0` unless a floor is established by either (i) a publisher-documented
reclassification/custody event tying a mass to migration, or (ii) the mechanical synchronized-floor rule:
month+class-matched mirror pairs with |China decline − BE/LU rise| ≤ 10% of the pair mass in the SAME
month and class — and even then the floor is labelled CONSISTENT-WITH-migration, not established
beneficial-ownership fact, and the headline M_lo stays 0 with the candidate floor as a labelled
sensitivity. Then **ΔnonUS-true ∈ [494.977 − M_hi, 494.977 − M_lo]**.

## Mechanical verdict (fixed here; thresholds are disclosed judgments)

- **MIGRATION-DOMINANT** iff M_lo ≥ 0.5 × 446.493 (migration at least half the US-securities decline,
  ESTABLISHED by a floor — not merely permitted by a wide ceiling). The exit reading demotes to custody
  housekeeping.
- **MIGRATION-MINOR** iff M_hi ≤ 0.25 × 446.493 (≈ 111.6 $bn — migration cannot exceed a quarter):
  ΔnonUS-true ≥ ~383 $bn and the non-US reading survives; the currency stays k1-walled.
- **UNINFORMATIVE-BOUND** otherwise: the fork stays open; the interval is the deliverable, stated plainly.
- The verdict is computed on the verdict axis; the full window is context. If NO cap grounds, the verdict
  is UNINFORMATIVE-BOUND with M_hi = NOT-CONSTRUCTIBLE (the interval collapses to the uninformative
  [494.977 − 446.493, 494.977] only if even capA fails — capA always grounds if the SLT data exist, so
  this branch is not expected; stated for completeness).

## The mid-2010s Belgium surge (the migration template — checked, never imported)

If the on-disk series carry the mid-2010s Belgium surge, characterize its class/timing signature as the
migration TEMPLATE (what synchronized custody relocation looks like in these data) and compare the
current episode's signature to it. If the on-disk record cannot see it (the by-class tables begin
2020-01; the pre-2020 record is total-UST via MFH), characterize what IS visible and do NOT import the
episode from memory or literature.

## The flipped guard (verbatim; BOTH directions are violations)

**DRAMATIZE:** selecting windows/classes to shrink M_hi and keep the exit reading alive — the windows and
classes are fixed above, before any data; every grounded cap enters the minimum.
**ZERO:** attributing the whole BE/LU accretion to China to kill it — capA counts class-matched ROOM, and
the bound never asserts the accretion IS China's; the pool determination's custody-masking direction is
carried, not resolved.

## Falsifiable expectation (symmetric)

> Primary: **UNINFORMATIVE-BOUND** — the BE/LU accretion is large (the RDT-D perimeter contrast), so capA
> is expected loose; capB may bite but its staggered blind spot limits what a small value can claim; capC
> is conditional on a methodology finding not yet made. I do not favor it: **REFUTED toward
> MIGRATION-MINOR** if the grounded minimum lands ≤ 111.6 $bn; **REFUTED toward MIGRATION-DOMINANT** if a
> documented floor reaches 223.2 $bn. Any landing is promotable; the interval is reported whichever way it
> falls.

## Amendment mechanics (the established precedent)

Insert-only RDTE-AMEND blocks via a deterministic `RDTE_recompute.py` (strip reproduces the post-RDT-D
object byte-for-byte against its sha); prior recomputes untouched; `RDTE_verify.json` carries
byte-reproduction for the ingredients, the result, and the amended object; branch-specific template prose
assertion-guarded from the start. Numbers computed, never hardcoded.

## Scope

Writes ONLY `build/reserve/RDTE_*` and `build/reserve/rdte_evidence/*`, plus the tasked amendment.
DP2–DP6 and all prior artifacts otherwise untouched. No date, no probability, no currency guess. What
follows RDT-E, if anything, is decided at the gate.
