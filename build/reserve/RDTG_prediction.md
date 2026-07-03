# RDT-G — The receiving side + the I.B line: PRE-REGISTERED DESIGN

**Timestamp: 2026-07-02 (committed BEFORE any RDT-G build — the magnitude bars, the I.B parse, the
receiving-leg grounding, and every verdict do not yet exist).**

Pre-registration, committed first. Symmetric: **DESTINATION-CONSISTENT, DESTINATION-ABSENT, UNPOWERED,
INDETERMINATE, and any I.B axis (SURGE / FLAT / DECLINE / SUPPRESSED) are all promotable.** The fork stands
at ΔnonUS-true ∈ [48.484, 494.977] (RDT-F, route-robust). Two untried discriminators: China's own SDDS
Section I.B ("other foreign currency assets"), never parsed; and the destination countries' own books, never
swept. **Neither can RESOLVE the fork — both masking mechanisms below cap what each leg can claim, and their
consequences are pre-committed here.** Each can move weight honestly. Read-only on prior artifacts except
the tasked insert-only object amendment. No date, no probability, no currency guess (the k1 wall), no
attribution beyond what a leg's own construction carries.

## Windows (fixed) and the mass being tested

- **Baseline window:** calendar 2015→2021. **Verdict window:** calendar 2022→2025 (a leg published to an
  earlier/later boundary uses its nearest published boundary, stated per leg). These are RDT-G's windows —
  deliberately the freeze-era cut, distinct from the RDT-B..F monthly verdict axis; both facts stated.
- **The mass:** the task's bar range **[141, 495] $bn** traces to committed fields:
  upper = 494.977 (`RDTD_result.json identity.china_alone.delta_non_us_busd`); lower = 494.977 − 354.028 =
  **140.949**, where 354.028 is RDT-E's positive-months cross-flow proxy
  (`RDTE_result.json cross_flow_sensitivity_detail.positive_months_proxy_variant.total_busd`) — i.e. the
  interval lower endpoint under RDT-E's most conservative disclosed cross-flow sensitivity. **The fork's own
  lower endpoint (48.484, RDT-F) is smaller; bars at 141 are therefore GENEROUS to the null** — a leg that
  fails to see 141 would see 48.5 even less. Direction stated; the object's fork interval is unchanged by
  this choice. All three constants are READ from the committed artifacts by the recompute, never hardcoded.

## The magnitude bars (computed BEFORE any discriminator series is read — git order)

What [140.949, 494.977] $bn arriving over the verdict window implies **per candidate market**, under TWO
allocation schemes, in **local currency** (the tonnage-not-value lesson — no USD-valuation artifacts):
- **Scheme 1 — market-size-proportional:** allocate the mass across the candidate sovereign markets
  {JGB (JP), Bund (DE), OAT (FR), gilt (UK), AGS (AU), GoC bonds (CA)} in proportion to outstanding stock
  (general/central government debt securities outstanding, local currency, latest pre-verdict-window
  publication or nearest, stated).
- **Scheme 2 — COFER-currency-share-proportional:** allocate by the COFER non-USD currency shares (EUR, JPY,
  GBP, AUD, CAD, CHF, other), **CNY excluded and shares renormalized** (China's own currency is not a
  reserve asset for itself), each currency's mass mapped to its candidate sovereign market (EUR split
  DE/FR by relative outstanding; CHF carried as a stated no-candidate-leg remainder).
- Bars are stated per market as: local-currency amount (converted at a single grounded FX set, source
  retained), % of outstanding, and % of nonresident holdings where the denominator leg publishes one.
- **Sequencing rule (the git-order gate check):** the DENOMINATORS (market outstandings, COFER shares, FX
  set) are the bars' inputs and precede them; the bars are computed and **committed before the I.B parse
  and before any receiving-leg series is read or fetched.** No bar is revised after a discriminator series
  is seen.
- **Stated limitation (direction pre-committed):** the candidate set is not the universe of non-US
  destinations (corporates, equities, deposits, non-candidate sovereigns absorb too), so per-market bars
  OVERSTATE what any one market should show — which again makes a null WEAKER, never stronger.

## Part 1 — the I.B axes (mechanical)

Parse **Section I.B ("other foreign currency assets")** from all on-disk SAFE SDDS templates
(2015-06→latest, the RDT-D corpus): securities / deposits / loans / other, monthly. Verdict on
ΔI.B_total over the verdict window (2022-01→latest published, stated):
- **SURGE** iff ΔI.B_total ≥ 0.05 × 494.977 (= 24.749, a disclosed judgment threshold: a twentieth of the
  upper mass); **DECLINE** iff ≤ −24.749 (equally a finding); **FLAT** iff strictly between;
- **SUPPRESSED** iff the I.B line or its components are unpublished/aggregated/blank in the real templates —
  a finding about DISCLOSURE, never interpolated, and it does not default to any other axis.
- Sub-lines reported wherever published. I.B movement is a within-China's-own-books discriminator
  (re-parking into non-reserve FX assets would surface here); it attributes nothing beyond China's own
  reporting perimeter.

## Part 2/3 — receiving-leg rules (mechanical; per leg, fixed here)

Legs: China-attributed candidates (a) Japan b.o.p. vis-à-vis China portfolio liabilities (BoJ/MoF);
(b) euro-area b.o.p. by counterpart, China line (ECB/Eurostat); (c) UK Pink Book China portfolio
liabilities (ONS); (d) Canada by-country international securities transactions (StatCan). Aggregate
candidates: (e) Bund nonresident/official structure (Finanzagentur/Bundesbank); (f) JGB foreign share
(BoJ flow of funds); (g) gilt overseas holdings (DMO/ONS); (h) OAT nonresident share (AFT); (i) AGS
nonresident share (AOFM/ABS). For each: existence, frequency, instrument split, and the compiler's OWN
custody caveat quoted — or **NOT-AVAILABLE, honest per leg**. Official-sector split used where published;
else the aggregate with the dilution caveat stated.

Per grounded leg, in local currency: `excess = (verdict-window change) − (baseline mean annual change ×
verdict-window years)`; `Bar_low(leg)` = the leg's Scheme-1 allocation of 140.949 (Scheme-2 alongside).
- **Power test:** the leg is POWERED iff Bar_low(leg) ≥ σ_baseline(leg), the standard deviation of its
  baseline-window annual changes. Unpowered legs are reported but never counted in the verdict.
- **Leg verdicts:** leg-CONSISTENT iff excess ≥ 0.5 × Bar_low(leg); leg-ABSENT iff excess < 0.5 ×
  Bar_low(leg) and the leg is powered. China-attributed legs are the same test on the China line and are
  REPORTED SEPARATELY from aggregate legs; a rising China line is attribution-grade for that leg's
  compiler perimeter only — never construction-grade for the fork interval.
- **Sweep verdict (over powered grounded legs):** **DESTINATION-CONSISTENT** iff ≥ half are leg-CONSISTENT,
  or any China-attributed leg is; **DESTINATION-ABSENT** iff ≥ three-quarters are leg-ABSENT and no
  China-attributed leg is leg-CONSISTENT — **and the verdict sentence itself carries the masking caveat**
  (a null is weak evidence, not disposal); **UNPOWERED** iff fewer than 3 powered grounded legs;
  **INDETERMINATE** (weight unmoved) otherwise. Every leg is reported whatever it shows.

## Both masking mechanisms (stated now; consequences pre-committed)

- **M1 — external managers / custodians:** reserve managers buy through external asset managers, BIS
  facilities, and custodians, so destination compilers attribute holdings to the manager/custodian
  location. The external-manager practice is GROUNDED with a citation (publisher/BIS/compiler text,
  retained) or marked UNDOCUMENTED — never asserted from memory. **Consequence: a null on any leg (and on
  the sweep) is WEAK evidence, not disposal.**
- **M2 — counterpart-attribution in b.o.p.:** transactions routed via financial centers attribute to the
  center (UK/BE/LU), not to China. **Consequence: a surge is CONSISTENCY, not attribution; the absence of
  a China line is not the absence of China.**

## Part 4 — the amendment (consequence rules fixed here)

Insert-only RDTG-AMEND blocks: the I.B verdict; the receiving-side verdict with its pre-stated power
limits riding it; the fork interval ANNOTATED — weight toward true-departure (CONSISTENT), toward
re-parking (ABSENT, masking-capped), or unmoved (UNPOWERED/INDETERMINATE). **The interval's ENDPOINTS
change only if a leg carries construction-grade attribution, which none above is expected to — expected
amendment: annotation only.** Deterministic `RDTG_recompute.py` (strip reproduces the post-RDT-F object
byte-for-byte against its sha, read from `RDTF_verify.json`); prior recomputes untouched;
`RDTG_verify.json` with byte-reproduction and all_pass; every branch template assertion-guarded, unfired
branches fail loud. Numbers computed, never hardcoded.

## The flipped guard (verbatim; BOTH directions are violations)

**DRAMATIZE:** reading any nonresident uptick as China, or declaring consistency on one leg while ignoring
absent legs. **ZERO:** demanding by-name attribution the masking forbids, and calling grounded aggregate
surges unpowered.

## Falsifiable expectation (symmetric)

> Primary: **UNPOWERED or INDETERMINATE on the sweep** (aggregate legs are coarse against bars diluted
> across six markets; masking caps the rest) **and FLAT-or-SUPPRESSED on I.B** (the line is historically
> small for China). I do not favor these: **REFUTED toward DESTINATION-CONSISTENT** if grounded surges land
> at bar scale (especially any China-attributed line rising); **REFUTED toward DESTINATION-ABSENT** if
> powered legs sit flat across the sweep; **REFUTED toward I.B SURGE** at ≥ 24.749. Any landing, any
> combination, is promotable; every leg is reported whichever way it falls.

## Scope

Writes ONLY `build/reserve/RDTG_*` and `build/reserve/rdtg_evidence/*`, plus the tasked amendment.
DP2–DP6 and all prior artifacts otherwise untouched. No date, no probability, no currency guess. What
follows RDT-G, if anything, is decided at the gate.
