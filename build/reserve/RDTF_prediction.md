# RDT-F — Route-robust migration ceiling + custody-basis reconciliation: PRE-REGISTERED DESIGN

**Timestamp: 2026-07-02 (committed BEFORE any RDT-F build — the center-set grounding, the global ceiling,
the basis reconciliation, and every verdict do not yet exist).**

Pre-registration, committed first. Symmetric: **MINOR-ROBUST, FORK-REOPENED, TENSION-REAL,
TENSION-ARTIFACT, PARTIAL, and any combination are promotable.** This stage closes RDT-E's two live items:
(1) migration via custody jurisdictions OTHER than BE/LU was unbounded; (2) the aggregate tension (FRBNY
custody −232.2 vs TIC official +116.8 over the verdict axis) is unresolved as real-vs-basis-artifact. It
also resolves the routed net-vs-gross judgment BY CONSTRUCTION: **the branch verdict is rendered on the
OVERSTATING-SAFE (gross) ceiling; window-net is carried as the tighter, disputed sensitivity.** Read-only
on prior artifacts except the tasked insert-only object amendment. No date, no probability, no currency
guess (the k1 wall stands).

## The custody-center set (DERIVED, not chosen)

**Derivation rule (mechanical):** a jurisdiction enters the custody-center set IF AND ONLY IF a retained
or fetched PUBLISHER document (TIC attribution/methodology documentation, the SHL/SHCA custodial-bias
passages, or equivalent publisher text) names it as a **custodial / ICSD / attribution-bias center** — the
grounding line QUOTED verbatim per center. Known candidate lines already on disk: the SHL custodial-bias
passage naming **Belgium, Luxembourg, Switzerland, and the United Kingdom** (retained in
`rdtb_evidence/shl2025r_extracted.txt`, quoted in RDT-D). The grounding pass re-reads the retained
documents (and may fetch additional TIC/SHCA methodology pages) and quotes the line for EVERY center that
enters; a center with no quoted line does NOT enter. **The DP-era offshore-hub tagging (CYM/HKG/VGB) is a
BENEFICIAL-OWNER/issuer-haven taxonomy, not a custody taxonomy — per the zero-guard, beneficial-owner
jurisdictions do NOT enter the custody set unless a publisher line independently names them as custodial
attribution-bias centers.** No center enters or exits by choice; the set is whatever the quoted lines
support, and the quotes are the audit trail.

## The two ceiling constructions (fixed here; per center, per class)

Over the RDT-B/C/D/E **verdict axis** (2023-05..2026-04; full window as context), on the ACTIVE
(transactions) basis, per custody-center country line c and SLT class k:
- **GROSS (the VERDICT basis; overstating-safe by construction):**
  `M_center(c) = Σ_k min( ChinaGrossDecline_k , CenterGrossInflow_k )`, where
  ChinaGrossDecline_k = Σ_months max(−ΔChina_active_{k,m}, 0) and
  CenterGrossInflow_k = Σ_months max(+ΔC_active_{k,m}, 0). The min() with China's gross decline
  mechanically zeroes accretion in classes China never sold in any month (the zero-guard, honored by
  construction, never by hand).
- **WINDOW-NET (the tighter, DISPUTED sensitivity — RDT-E's construction, carried alongside, never the
  verdict):** the RDT-E formula per center, `Σ_k min(max(−ΔChina_net_k,0), max(ΔC_net_k,0))`.
- **Global:** `M_hi_global = min( Σ_grounded-centers M_center(gross) , 446.493 )` — the ceiling cannot
  exceed the net decline it explains; if the sum reaches the cap, the ceiling is VACUOUS and the branch is
  FORK-REOPENED regardless. The net-version global sum is reported alongside. BE/LU's RDT-E figures are
  NESTED inside the table for comparison. **Leave-one-center-out is mandatory:** the global gross ceiling
  recomputed dropping each grounded center in turn, reported as a table in the result AND the object body.

## Branch thresholds (CARRIED, not re-tuned)

The thresholds are **read programmatically from the committed `build/reserve/RDTE_prediction.md`** and
byte-matched at the gate: MINOR at ceiling ≤ 0.25 × 446.493 (= 111.623); DOMINANT at an established floor
≥ 0.5 × 446.493 (not expected to arise here — no floor machinery changes). Branch mapping for this stage,
on the GROSS global ceiling: **MINOR-ROBUST** iff M_hi_global ≤ 111.623 (RDT-E's MINOR survives
route-robustly on the overstating-safe basis); **FORK-REOPENED** otherwise (the route-robust ceiling does
not sustain MINOR; the interval is the deliverable, and RDT-E's BE/LU MINOR is re-labelled route-specific).
Either way: **ΔnonUS-true ∈ [494.977 − M_hi_global, 494.977]**, pool caveat and k1 wall riding.

## The basis reconciliation (Part 2 design, fixed here)

- **Each series' valuation basis QUOTED from its own documentation** (retained): the H.4.1 memo line's
  basis (expected: face/par value — quote the footnote/technical note from the FRB's own documentation,
  fetched and retained) and the TIC MFH/SLT basis (expected: estimated market value — quote the TIC
  documentation). No basis is asserted from memory.
- **The price-adjustment method (named):** convert BOTH legs to a QUANTITY-like basis and compare changes
  over the verdict axis: the FRBNY leg's par change (already quantity-like) vs the TIC official
  aggregate's **transactions-basis change** = Δholdings − cumulative stated valuation change (the official
  aggregate's valchg column from the on-disk slt2d/official rows, published from 2023-02 — the axis lies
  on it). The **basis-adjusted divergence** = |FRBNY_par_change − TIC_official_txbasis_change|.
- **Verdict (mechanical; disclosed judgment thresholds):** **TENSION-ARTIFACT** iff the basis-adjusted
  divergence ≤ 50 $bn (the raw ~349 divergence collapses under the stated adjustment);
  **TENSION-REAL** iff ≥ 150 $bn (a quantified residual of official custody leaving the Fed,
  unattributed); **PARTIAL** between, with the residual stated. If REAL (or PARTIAL with a material
  residual): **state plainly that official custody leaving the Fed at scale is structurally live
  in-window and therefore bears on Part 1's interpretation — do not smooth it.** The perimeter facts ride
  the verdict: FRBNY custody ⊂ TIC official (officials can custody outside the Fed), so a real residual
  is custody RELOCATION away from the Fed, exactly the migration channel Part 1 bounds.

## The flipped guard (verbatim; BOTH directions are violations)

**DRAMATIZE / keep-the-exit-alive:** shrinking the center set (a grounded center omitted) or rendering the
verdict on the net construction — the verdict basis is gross, fixed here.
**ZERO / kill-it:** counting accretion in classes China did not shed (the min() construction forbids it
mechanically), or admitting beneficial-owner jurisdictions into the custody set (the derivation rule
forbids it).

## Falsifiable expectation (symmetric)

> Primary: **FORK-REOPENED on the route-robust gross ceiling** — the UK and Switzerland lines are large
> and a 36-month gross-inflow sum class-matched against China's Treasury-heavy decline plausibly exceeds
> 111.6 $bn on the overstating-safe basis — **and TENSION-REAL or PARTIAL** on the basis check (the raw
> 349 divergence seems too large to be pure price). I do not favor these: **REFUTED toward MINOR-ROBUST**
> if the grounded-set gross ceiling lands ≤ 111.623 (RDT-E's MINOR then survives its strongest
> route-robust test); **REFUTED toward TENSION-ARTIFACT** if the stated adjustment collapses the
> divergence. Any landing, in any combination, is promotable; the interval and the residual are the
> deliverables whichever way they fall.

## Amendment mechanics (the established precedent)

Insert-only RDTF-AMEND blocks via a deterministic `RDTF_recompute.py` (strip reproduces the post-RDT-E
object byte-for-byte against its sha); prior recomputes untouched; `RDTF_verify.json` carries
byte-reproduction for the ceiling table, the reconciliation, and the amended object; every branch template
assertion-guarded (all branches implemented, unfired ones guarded). The amendment: the route-robust
interval SUPERSEDING the BE/LU-only bound; the branch label re-rendered on the gross basis (RDT-E's MINOR
made robust or demoted, whichever the number says); the basis verdict; the leave-one-center-out table in
the body. Numbers computed, never hardcoded.

## Scope

Writes ONLY `build/reserve/RDTF_*` and `build/reserve/rdtf_evidence/*`, plus the tasked amendment.
DP2–DP6 and all prior artifacts otherwise untouched. No date, no probability, no currency guess. What
follows RDT-F, if anything, is decided at the gate.
