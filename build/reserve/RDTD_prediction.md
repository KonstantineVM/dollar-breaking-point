# RDT-D — The identity, its fragility, and China's SDDS instrument split: PRE-REGISTERED DESIGN

**Timestamp: 2026-07-02 (committed BEFORE any RDT-D build — the fragility computation, the pool-definition
grounding, the SDDS template ingestion, and every verdict do not yet exist).**

Pre-registration, committed first. Symmetric: **a deposits answer, a non-US-securities answer, a
suppressed answer, and a 446.5-unreliable answer are all promotable.** No date, no probability, and **no
currency guess — the k1 wall (RDT-B/C) stands**: nothing below identifies the currency of any non-US
asset. Read-only on prior artifacts except the tasked insert-only object amendment. DP2–DP6 untouched.

## The identity (Part 0 core; every term traces to a committed number)

Over the RDT-B/C **verdict axis** (2023-05..2026-04; the SDDS leg uses the same axis truncated to the
latest published template month, stated):

`ΔNonUS ≡ ΔTotal(ex-gold) − ΔH_us_LT = ΔTotal(ex-gold) + 446.5 − V_us`

- **ΔTotal(ex-gold)** = the change in SAFE's ex-gold FX-reserves line = **+234.039 $bn** (committed
  `rdtc_safe_totals.csv`).
- **+446.5** = China-alone total US LT securities ACTIVE outflow over the axis = −(X + A) =
  −(−284.774 − 161.719) = **446.493 $bn** (committed `RDTC_class_flows.json` / `RDTC_result.json`); the
  CN+BE+LU variant (326.323) is carried in parallel — the custody band rides the identity.
- **V_us** = the valuation residual on China's US LT holdings over the axis = ΔH_us_LT − (−446.493),
  with ΔH_us_LT read from the committed `RDTC_class_panel.parquet`. V_us as defined ABSORBS the SLT
  identity gap; Part 1 sizes that gap separately against the stated-valuation column.
- **Meaning discipline:** ΔNonUS is the change in SAFE ex-gold reserves NOT accounted for by US **LT
  securities** — it still includes US T-bills, USD deposits anywhere, and USD assets in non-US custody.
  **ΔNonUS ≠ "non-dollar."** The tasked headline identity is LT-only; the **short-term US leg** enters
  as a labelled ADJUSTMENT term where the on-disk SLT table carries a China short-term position column
  (Δposition, with the caveat that bills sit near par so the position change is mostly flow) — reported
  beside the headline, never silently added or dropped.
- **Pool caveat (Part 2, a BOUND on the identity):** the TIC "China (mainland)" attribution and the SAFE
  reserve pool are different perimeters (non-reserve official entities such as CIC; state banks; custody
  geography). Part 2 determines from PUBLIC definitions whether one perimeter contains the other; if not
  publicly decomposable, the mismatch is stated as a bound on the identity — **no split is fabricated.**

## Part 1 — the fragility of the 446.5 (mechanical rule)

Per class and per custody variant over the verdict axis, compute
`G = ΔH − V_stated − active` (the reconciliation gap), where V_stated is the SLT stated valuation-change
column (published from 2023-02 — the whole axis lies on it). Report G per class, its sign, and the total.
**Threshold (fixed here): if |G_total| > 0.25 × |active_total| for the China-alone variant (i.e.,
> ~111.6 $bn), the 446.5 is flagged 446.5-UNRELIABLE** — the identity's flow leg is then carried as the
band [active − |G|, active + |G|] everywhere downstream, and the verdict says so. Otherwise
RELIABLE-WITHIN-GAP (with G still reported). The known MECHANISM for such gaps — transactions are
attributed to the transacting counterparty's country (UK/intermediary financial centers), holdings
surveys to the beneficial owner — is stated from the TIC publisher's own documentation (grounded to the
retained files, not asserted).

## Part 3 — the SDDS instrument split (mechanical verdict axes)

Fetch and parse the monthly SAFE/IMF **SDDS Reserves Data Template** .xls files, 2015-06 → latest, from
the publisher (safe.gov.cn/en/ForexReserves). Extract **Section I.A**: securities; total currency and
deposits with (i) other national central banks/BIS/IMF, (ii) banks headquartered in the reporting
country, (iii) banks headquartered outside; other reserve assets. **The line detail is verified from the
real files; a suppressed or aggregated line is a FINDING** (OTHER-OR-SUPPRESSED axis), never interpolated.

Ledger over the verdict axis (truncated to the latest template month, stated): Δsec_SDDS, Δdep_CB/BIS,
Δdep_commercial (in+outside), Δother. **The netting rule (fixed): the SDDS securities line INCLUDES US
securities. The non-US-securities discriminator is `Δsec_SDDS − ΔH_us_LT` (TIC), carried with the custody
band and the pool caveat — reading raw Δsec_SDDS as non-US purchases is the named dramatization vector.**

**Verdict (mechanical, on the identity's ΔNonUS midpoint, China-alone headline):**
- **DEPOSITS-SURGE** iff Δdeposits_total ≥ 0.5 × ΔNonUS (and ΔNonUS > 0);
- **NON-US-SECURITIES** iff (Δsec_SDDS − ΔH_us_LT) ≥ 0.5 × ΔNonUS;
- both ≥ 0.5 → **MIXED-COMPOSITION** (both stated);
- required lines suppressed/aggregated so the axes cannot be computed, or neither reaches 0.5 →
  **OTHER-OR-SUPPRESSED** (stating which: suppression vs sub-threshold residual/other).
- If Part 1 flags 446.5-UNRELIABLE, the verdict is computed on the identity BAND and reported as a band;
  if the band straddles a threshold, the verdict is the band-honest OTHER-OR-SUPPRESSED with the straddle
  stated.

## The flipped guard (verbatim; BOTH directions are violations)

**DRAMATIZE:** reading the SDDS securities line as non-US purchases without netting the TIC US leg;
treating a suppressed line as positive evidence of concealment-and-exit (suppression is a finding about
DISCLOSURE, not about destination); pushing past the pool caveat to a currency claim.
**ZERO:** dismissing the identity wholesale via the pool caveat without computing the stated bound;
averaging a deposits surge away in the full 2015-06→ window (the verdict axis is the RDT-B/C axis; the
long window is context for the series' behavior, pre-registered as such).

## Falsifiable expectation (symmetric)

> Primary: **OTHER-OR-SUPPRESSED or MIXED-COMPOSITION** — China's SDDS reporting is expected coarse at
> the line level, and the ΔNonUS mass (order +680 $bn mid, before the band) is large relative to plausible
> single-instrument moves. I do not favor it: **REFUTED toward DEPOSITS-SURGE** if the deposits lines
> absorb ≥ half; **REFUTED toward NON-US-SECURITIES** if the netted securities move absorbs ≥ half; and
> **446.5-UNRELIABLE** overrides into the band-honest reporting if Part 1's threshold trips. Every
> landing is promotable.

## Part 4 — amendment mechanics (the established precedent)

Insert-only RDTD-AMEND blocks via a deterministic `RDTD_recompute.py` (strip-and-reinsert reproduces the
post-RDT-C object byte-for-byte against its sha); `RDT_recompute.py`, `RDTB_recompute.py`,
`RDTC_recompute.py` untouched; `RDTD_verify.json` carries byte-reproduction for the result, the SDDS
series, and the amended object; branch-specific template prose is assertion-guarded from the start (the
RDT-C GATE lesson). Numbers computed, never hardcoded.

## Scope

Writes ONLY `build/reserve/RDTD_*` and `build/reserve/rdtd_evidence/*`, plus the tasked amendment.
No date, no probability, no currency guess. What follows RDT-D, if anything, is decided at the gate.
