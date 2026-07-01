# RD0 — Reserve-Side Dollar-Breaking-Point Program: scope + five-surface plan

**Orchestrator scoping document.** Grounded source availability, endpoints, and the treated/control
classification are in `build/reserve/RD0_sources.json` (fetch-confirmed, evidence in
`build/reserve/rd0_evidence/`). This file is the PLAN; it does not assert any present-day fact that
`RD0_sources.json` has not fetch-confirmed. No IMF confidential aggregate (COFER) is used as evidence. This
program does NOT touch the prior DP2–DP6 chain.

## The pivot and the mechanism

The prior arc (DP0–DP5 + five fund-side F3 tests) measured **US funds holding Chinese securities** — the
wrong actor/asset for the dollar-breaking-point thesis. The breaking point lives in **reserve managers'**
behaviour, measurable from **public national/primary** sources that bypass the confidential IMF aggregate. The
mechanism has **five observable surfaces**; the deliverable (at RD6) is whether they **corroborate** around the
Feb-2022 Russian reserve freeze in the sanctions-exposed holders — with **contradiction across surfaces itself
a finding**, and a "mechanism not coherently present" as valid as a coherent signal.

## The five surfaces (grounded availability from RD0_sources.json)

| S | surface | observed quantity | public source (grounded) | status |
|---|---------|-------------------|--------------------------|--------|
| S1 | Currency composition | per-country per-year currency shares (USD/EUR/RMB/gold/other) | Laser–Mihailov–Weidner (LMW) 64-economy dataset, BOFIT DSpace, 1996–2023 | **CONFIRMED** |
| S2 | Gold | central-bank gold demand / tonnage by country, quarterly | World Gold Council (login-gated) + IMF IFS (ungated) + PBoC/CBR national | **CONFIRMED** (IFS is the ungated corroborant) |
| S3 | Treasury holdings | foreign-official UST holdings by country, monthly + gross transactions | US Treasury TIC (MFH history + s1_globl transactions); reuses `build/contracts/treasury_tic.json` | **CONFIRMED** |
| S4 | RMB internationalization | RMB payment share, CIPS, PBoC swap lines, CNH, invoicing | SWIFT RMB tracker + PBoC swap list (public); CIPS/CNH/invoicing partial | **CONFIRMED (partial)** |
| S5 | Decomposition inputs | FX rates (valuation strip) + total-reserve levels (accumulation strip) | FRED FX (confirmed); IMF IFS reserve levels (indicator code UNVERIFIED) | **CONFIRMED (FX)** |

Do not proceed to build a surface whose data RD0 could not locate. Any UNVERIFIED source (CIPS monthly-2022,
CNH/HKMA deposits, RMB invoicing, exact IFS reserve-level code) must be fetch-confirmed at the start of its own
stage before that surface is estimated, or that component is recorded NOT-AVAILABLE.

## Treated/control taxonomy (grounded on a public criterion, not stipulated)

**Primary criterion:** the recorded roll-call of **UN General Assembly Resolution ES-11/1** ("Aggression against
Ukraine", 2 March 2022) — Yes 141 / No 5 / Abstentions 35 — fetched verbatim from the UN Digital Library
(RD0_sources.json → taxonomy). Corroborated by Russia-sanctions-coalition membership (OFAC jy0612, 2022-02-28).

- **TREATED — sanctioned / frozen:** **Russia** (voted **No**; its ~$300bn reserves were frozen Feb-2022 — the
  clean observed treated unit).
- **TREATED — sanctions-exposed / non-US-aligned "active diversifier" set:** **China** (**Abstain**) and the
  other abstainers/no-voters that are reserve-holding economies (India, South Africa, Kazakhstan, … — the
  low-US-alignment set).
- **CONTROL — US-aligned disclosers:** advanced-economy reserve managers that voted **Yes** and are not
  sanctions-exposed (US, UK, Euro Area, Japan, Canada, Australia, Korea, Switzerland, …).

## Per-surface observability of China (load-bearing — a residual is NOT an observation)

- **S1 currency composition — INFER.** China does **not** disclose currency composition and is **absent from
  the LMW panel** (0 rows, confirmed). China's USD share on S1 is a **residual inference**, never presented as
  an observation.
- **S2 gold — OBSERVE** (PBoC/SAFE monthly official gold; WGC).
- **S3 Treasury holdings — OBSERVE** (China in the TIC MFH panel monthly; custodial-attribution caveat).
- **S4 RMB — OBSERVE** (China is the issuer; SWIFT/CIPS/PBoC swaps public).
- **S5 — OBSERVE** for FX/reserve levels.

## The load-bearing constraint that shapes RD1 (S1)

The clean treated unit, **Russia, discloses currency composition only through 2021** — the CBR stopped
publishing after the freeze, so **Russia's post-freeze S1 currency composition is UNOBSERVED**. Consequences,
carried into the RD1 pre-registration:
1. Russia's dramatic **pre-freeze** diversification (USD 47%→13.9%, CNY 0→21.8% across 2007–2021, confirmed in
   the data) is an observed **case study of a sanctions-exposed manager diversifying — but it PRE-DATES the
   Feb-2022 freeze** (it is the post-2014-Crimea-sanctions response), and it is NOT the freeze response.
2. The **freeze event-study/DiD on S1** therefore cannot use Russia's post-2022 response; it rests on the
   broader **non-US-aligned discloser set with 2022 data vs the US-aligned disclosers** — an indirect, weaker
   test — with China entering only as a residual inference. Low power (annual disclosure, few treated
   disclosers) means **INSUFFICIENT-POWER / NOT-IDENTIFIED are first-class outcomes**, exactly as in the fund
   stage.

## Program stages (this pass runs RD0 + RD1, then HARD STOP for the human gate)

- **RD0** — scope + dataset grounding (this file + `RD0_sources.json`). ✔ grounded; awaiting gate.
- **RD1** — Surface 1: disclosed currency composition (pre-register → panel → freeze event-study with
  pre-trend → verdict). Runs this pass.
- **RD2–RD6** — gold (S2), Treasury (S3), RMB (S4), decomposition (S5), and the **cross-surface synthesis** (do
  the surfaces corroborate / contradict around the freeze). **Each is a separate human-gated stage; NOT run in
  this pass.** The synthesis (RD6) is not collapsed into a single regression.

## Integrity commitments for the program

- Every source public/national/primary and fetch-confirmed; UNVERIFIED components re-confirmed at their stage
  or recorded NOT-AVAILABLE. The IMF aggregate COFER is never used as evidence.
- Symmetric throughout: a coherent breaking-point signal, a "mechanism not coherently present," and
  cross-surface contradiction are equally reportable; no surface is built to force a conclusion.
- The China residual (S1) is never presented as an observation; the treated set is fixed by the grounded UN
  criterion, not gerrymandered.
- No date, no bare probability, no hazard claim is produced by this reserve-side program (it characterises
  reserve-manager reallocation, not the DP-side breaking-point objects). DP2–DP6 untouched.
