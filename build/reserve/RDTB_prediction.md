# RDT-B — Tighten the object: PRE-REGISTERED DESIGN + PREDICTION

**Timestamp: 2026-07-02 (committed BEFORE any RDT-B build — the SLT schema read, the SHL/LBS grounding,
the bound assembly, and the k3 cross-holder distribution do not yet exist).**

Pre-registration, committed first. Symmetric throughout: **the bound may come back degenerate; China may
sit inside a universal pack — both are valid, reported outcomes.** Every verdict rule below is mechanical
and fixed before any component or distribution is seen. Read-only on the RDT/RD1/RD2 artifacts (one
explicitly-tasked exception: the Part-C amendment of `RDT_breaking_point_object.md`, mechanics below).
DP2–DP6 untouched. No date, no bare probability, anywhere.

## Part A — the k1 counterpart bound (China's USD share, bounded from observed components)

**Concept discipline (fixed here).** The RDT k1 coordinate and its 13.89pp frontier are shares of
**disclosed FX (ex-gold) reserves** (the LMW concept). The bound is therefore computed on the **ex-gold
denominator** for the verdict; the incl-gold variant is also reported (labelled) since the upper side uses
the gold share. Denominator source: China total reserves and reserves-ex-gold from the committed
`rdt_k2_gold.csv` (WB, 2015–2025), cross-checked against the on-disk SAFE ORA files
(`rd2_evidence/safe_ora_*.xls*`, 2020–2025 year-ends); discrepancies reported, not smoothed.

**The bias-direction rule (load-bearing).** Every component carries a stated bias direction relative to
the OFFICIAL quantity:
- A component observed as **official-attributable** (foreign-OFFICIAL holder sector) may enter the LOWER
  bound. It UNDERSTATES total official USD assets (omitted components), which is the safe direction for a
  lower bound.
- A component observed only as **TOTAL-RESIDENT** (official + private mixed) OVERSTATES the official
  quantity and may **NOT** enter the lower bound; it may only inform the upper side.
- A total-resident component inside the lower bound is a build failure (the gate BLOCKs it).

**Components (grounding targets — existence is a finding from the files, not an assumption):**
1. **Official US securities held by China** — (i) READ the on-disk SLT tables
   (`build/data/treasury_tic/current/slt_table*.txt` and `build/reserve/rdt_evidence/tic/slt_table*.txt`):
   does the schema carry a foreign-OFFICIAL vs private split by country? Use it if present. (ii) Fetch the
   TIC annual SHL (foreign portfolio holdings of US securities) by-country OFFICIAL holdings and the TIC
   official-institution lines; confirm coverage 2015–2025. What exists is recorded; what does not is
   NOT-AVAILABLE.
2. **Official dollar deposits** — BIS LBS USD-denominated liabilities of reporting banks to China
   counterparties: verify from the LBS DSD whether a counterparty-sector split isolating the OFFICIAL /
   central-bank sector exists. If only total-resident: the deposits component is EXCLUDED from the lower
   bound (upper side only) per the rule above.
3. **Custody band carried through, never collapsed**: every US-securities component is computed both as
   China-alone (lower custody variant) and China+Belgium+Luxembourg (upper custody variant); the k1 band
   reports both.

**Band logic (fixed).** Per year 2015–2025:
- LOWER bound on official USD-asset share L(y) = Σ(official-attributable USD components) / FX-ex-gold
  reserves. Most-conservative construction L_cons = China-alone custody, official-attributable components
  only.
- UPPER bound U(y): incl-gold basis = 1 − constant-price gold value share (from the committed RDT
  coordinates) − any other OBSERVED non-dollar component; ex-gold basis = 1 − (observed non-USD FX
  components)/FX-ex-gold. **Stated plainly: unobserved non-USD assets make the upper side weak** (it will
  sit near 1 unless non-USD components are observed).

**Verdict rule (mechanical, fixed).**
- **NON-DEGENERATE** iff L_cons(latest available year) ≥ 13.89pp + 5pp (i.e., ≥ 18.89pp) — the lower bound
  sits materially above the frontier, so the k1 distance is bounded away from "at the frontier" and the
  composite becomes computable as a bounded interval.
- **STILL-DEGENERATE** otherwise (including: the official split is not published; the components do not
  ground). The k1 cell then stays UNDETERMINED and the SAFE-vintage judgment returns to the human gate.
- If NON-DEGENERATE, the k1 distance uses the RDT metric with **origin = the SAFE-disclosed 2014 point
  (58pp, an observed one-off disclosure)** and current value = the measured band [L, U]:
  d ∈ ([L,U] − 13.89)/(58 − 13.89). The 5pp margin is a pre-registered judgment, disclosed as such.

**Falsifiable expectation (A):** IF the official-by-country split grounds, NON-DEGENERATE with L_cons
landing somewhere in the ~20–45pp range is expected; if the split is not published, STILL-DEGENERATE.
**REFUTE:** a grounded L_cons below 18.89pp → STILL-DEGENERATE is reported as the finding. Either verdict
is valid; the bound reports what the components say.

## Part B — the k3 differential test (universal-vs-differential on the live signal)

**The RD2 discipline applied to the live coordinate:** China's k3-active selling (−93 $bn/yr recent-3y) is
the object's one live signal; a rolloff that is universal across the official-holder universe is real but
NOT sanctions-specific, and saying so plainly demotes the signal.

**Scaling (exact, fixed).** For every TIC MFH country c with transactions data: the annualized active-flow
rate r_c = [Σ monthly net purchases of long-term Treasuries over the window] / H_c(window start) / (window
years), where H_c(window start) = MFH holdings in the month immediately preceding the window.
- **Recent-3y window (the VERDICT axis, fixed ex ante):** the last 36 published months ending at the
  latest published month.
- **Full window (always shown beside it, so the window choice is visible, not selected):** 2013-01 (or the
  country's first coverage month) → latest.
- **Universe rule (mechanical):** countries with H_c(window start) ≥ $10bn (small-denominator guard) and
  ≥ 30 of 36 transaction months non-missing (recent window; proportional rule for the full window).
  Exclusions listed. China enters both as China-alone AND as a labelled synthetic China+Belgium+Luxembourg
  pooled holder (custody band, never collapsed).
- **Distribution statistic:** China's percentile rank in the cross-holder distribution of r_c (selling
  direction = more negative = lower percentile), both custody variants, both windows.
- **ES-11/1 split:** treated = No/Abstain voters in the universe, control = Yes voters (mechanical, from
  the committed RD0 vote file); non-UN/unmapped entities stay in the distribution but out of the split
  (stated). Report group medians/means and a rank-sum statistic with a normal-approximation p as a
  DESCRIPTIVE quantity (small treated N expected; no causal claim).
- **Baseline:** the aggregate foreign-OFFICIAL Treasury-holdings rolloff over the same windows (from the
  TIC official-aggregate lines if on disk or fetched), scaled the same way: r_off.

**Verdict rule (mechanical, fixed; the verdict axis is the recent-3y window):**
- **DIFFERENTIAL** iff ALL of: (i) China (China-alone variant) is in the selling tail, percentile ≤ 10%;
  (ii) China's rate is beyond the official baseline: r_off ≥ 0, or r_CN/r_off > 2 (both negative);
  (iii) the treated group's median r is more negative than control's AND the rank-sum normal-approx
  p < 0.10.
- **UNIVERSAL-ROLLOFF** iff China's percentile > 25% OR (baseline-comparable: both negative and
  r_CN/r_off ∈ [0.5, 2]) AND the treated/control split shows no treated-specific selling under (iii).
- **MIXED** otherwise — stating exactly which axis mixes (percentile / baseline / split), with the numbers.

**Falsifiable expectation (B):** UNIVERSAL-ROLLOFF or MIXED — every prior differential test in this build
(RD2 gold; the fund-side arc) found universal patterns, and the 2022–2025 official rolloff is broad. I do
NOT favor that outcome: **REFUTE = China a clear outlier against the universe AND the baseline AND the
treated/control split → DIFFERENTIAL**, which UPGRADES the object's live signal to sanctions-consistent.
Both directions are findings.

## Part C — the object amendment (mechanics surfaced, not silent)

`RDT_breaking_point_object.md` is currently byte-regenerated by `RDT_recompute.py` (RDT_verify.json).
Amending it would break that byte-identity. Resolution, fixed here: the amendment is performed by a new
deterministic `RDTB_recompute.py` that regenerates the AMENDED object from the committed RDT artifacts +
the new RDT-B artifacts (targeted, labelled edits: the k1 cell replaced by the measured band or explicitly
retained DEGENERATE; the k3 signal annotated DIFFERENTIAL/UNIVERSAL/MIXED with the distribution beside it;
the composite recomputed under the pre-registered RDT metric ONLY if k1 became non-degenerate,
sensitivities alongside; limitations updated; an amendment provenance note added). `RDT_recompute.py` is
NOT modified; `RDT_verify.json`'s object byte-identity claim becomes historical (pre-amendment) and
`RDTB_verify.json` carries the amended object's byte-reproduction. No date, no probability, no composite
sold as "the" number — unchanged.

## The flipped guard (verbatim; BOTH directions are violations)

**DRAMATIZATION vectors — violations:** optimistic components smuggled into the lower bound (any
total-resident or private-inclusive quantity inside L); a window maximizing China's percentile (the
verdict axis is fixed above at recent-3y with the full window always shown).
**ZEROING vectors — violations:** discarding a valid official-split source (if the SLT/SHL/LBS official
split exists, it is used); diluting China's flow in a full-decade window (the full window is context,
never the verdict axis).

## Anti-planting commitments

- Every bound value, percentile, rank statistic, and verdict is computed by the recompute scripts
  (`RDTB_k1_bound` and `RDTB_k3_distribution` recomputes) from committed inputs, byte-reproduced in
  `RDTB_verify.json`; nothing hardcoded.
- The official-split existence (SLT schema, SHL tables, LBS DSD) is a FINDING read from the real files,
  recorded either way; NOT-AVAILABLE is recorded honestly.
- The custody band rides every China number in both parts; no point-collapse.
- Verdict thresholds (5pp margin; 10%/25% percentiles; the 2× baseline ratio; p<0.10 descriptive) are
  fixed here, before any data; they are judgments, disclosed as such, and applied mechanically.

## Scope

Writes ONLY `build/reserve/RDTB_*` and `build/reserve/rdtb_evidence/*`, plus the tasked tracked amendment
of `build/reserve/RDT_breaking_point_object.md` via `RDTB_recompute.py`. DP2–DP6, RD1, RD2, and all other
RDT artifacts untouched. No date, no bare probability. What follows RDT-B, if anything, is decided at the
gate.
