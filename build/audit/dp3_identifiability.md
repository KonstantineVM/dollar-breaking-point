# DP3 Identifiability Audit (audit fact #4 of the DP2 audit)

**Date:** 2026-06-28
**Status:** READ-ONLY AUDIT. This is NOT a DP3 specification. No structural model is
specified, built, or written here. This document assesses whether the planned DP3
four-factor measurement system is *identifiable on the matrix support that DP2 actually
produced*, and whether the fallback "narrow the claim to a US-centric model" is a real
option or an empty one.

**Sources of fact (read, not assumed):**
- `build/model/matrix_spec.json` (structure, `cell_basis_register`, area_set)
- `build/results/dp2_residual.json` (`headline_finding`, `balancing_pass_log`,
  `what_was_actually_balanced`, `gcap_residency_to_nationality`, `cell_census`)

---

## 0. What the four factors are, and what cross-sectional variation each needs

The DP3 model is Farhi-Maggiori multiple-equilibrium + global-games selection, with a
four-factor measurement system:

- **F1 funding stress** — a *level/co-movement* factor: tightness in USD funding
  (deposits/loans/repo, money-market spreads) common across holders.
- **F2 Treasury de-specialization** — erosion of the safe-asset premium / convenience
  yield on US Treasuries; a factor on the *price and quantity of the safe leg itself*.
- **F3 sanctions reallocation** — reallocation of claims **ACROSS counterparties**: who
  exits whose claim and *into whose* claim. A *substitution* factor defined on the
  pattern of bilateral flows between many holder/issuer pairs.
- **F4 dollar run** — self-fulfilling run **ACROSS holders** on the dollar leg:
  contagion in the propensity to exit dollar claims, propagating from holder to holder.

**Identification requirement (order / rank intuition).** A latent factor is identified
when the observable measurement block carries enough *independent* cross-sectional
variation to pin its loadings separately from the other factors' loadings and from
idiosyncratic noise. Concretely:

| Factor | Variation it must be read off | Minimum support |
|---|---|---|
| F1 | Common movement in USD funding cost/quantity across *holders or sectors* | A **marginal cross-section** of USD funding exposures (one index per holder/sector) suffices for the common-level part; no pair structure required. |
| F2 | Movement in the safe-asset (Treasury) leg distinct from F1 | A Treasury **quantity-by-holder column** plus a funding cross-section to separate it from F1. A single-debtor (US) Treasury column *is* the natural support. |
| F3 | **Reallocation across counterparties** — covariation in the (i→j) vs (i→k) split as holder i substitutes issuer j for issuer k | A **multi-debtor bilateral block**: variation in who-holds-*whose* claims across many country pairs. One debtor column gives the level of i's claim on a *single* issuer (US); it contains **no information on the j-vs-k split** because no second issuer is observed bilaterally. |
| F4 | **Contagion across holders** on the dollar leg — covariation in holders' simultaneous exit, where holder a's exit raises holder b's | A **holder × holder (or holder × issuer) bilateral block with multiple issuers**, so that a *common dollar-exit* factor can be separated from (a) F1 funding level and (b) F3 reallocation. With one issuer (US) observed bilaterally, "exit the dollar" and "exit the US claim" are the **same column** and cannot be told apart. |

The decisive line: **F1 and F2 are marginal/level factors that a cross-section can
carry; F3 and F4 are *bilateral substitution/contagion* factors that require
multi-country-pair variation** — variation in the *off-diagonal pattern*, not in
marginals.

---

## 1. What the current support actually provides

From `dp2_residual.json` `headline_finding` and `what_was_actually_balanced`, and
`matrix_spec.json` `cell_basis_register`:

1. **One dense bilateral cross-border column.** `FOREIGN_HOLDINGS_US_TREASURIES` (TIC,
   `mfh_dec2025.json`): 36 publisher-named counterparty-country cells, all on **one
   issuer = US Government (S4)**, instrument I2. This is `S7_ROW(by country) holder ×
   S4_GOVERNMENT(US) issuer`. It is a single **debtor** column (US as the only debtor),
   not an area × area matrix. `headline_finding`: "Genuine area-x-area bilateral support
   exists for ONE column only (foreign holdings of US Treasuries, TIC)."

2. **US-internal sector who-to-whom.** `US_ISSUER_TO_HOLDER` (Fed EFA FWTW,
   `fwtw_2026Q1.json`): 585 nonzero `S1-S7 holder × S1-S7 issuer × I1-I6` cells, but
   **residency basis, WITHIN the US**. This is dense *within one area*; its counterpart
   axis is US sectors, not foreign countries (foreign appears only as the single
   `S7_ROW` column/row).

3. **BIS LBS = area-level MARGINALS, not cells.** `CROSS_BORDER_USD_BANK_POSITIONS`:
   per-counterparty all-reporting-banks USD claims/liabilities, instrument I1, but
   `L_CP_SECTOR=A` (all sectors) only. `headline_finding`: "BIS LBS supplies area-level
   MARGINALS (claims-on / liabilities-to each area vs the global bank system), not
   area-x-area cells." These are row/column control totals (each area vs *the global
   bank aggregate*), **not** holder-area × issuer-area cells.

4. **COFER = world reserve-currency MARGINAL.** 9 currency cells, "World/group aggregate
   only; no bilateral creditor-by-debtor detail" (`cell_basis_register`). A marginal on
   the *currency* axis, with no holder or pair resolution.

5. **The rest of the would-be bilateral structure is absent.** Global portfolio
   bilateral (CPIS) = HOLE (0 observations returned); China outward-by-country (SAFE) =
   HOLE; non-US/non-EA advanced FWTW (OECD) = UNVERIFIED-by-absence (publisher has no
   counterpart dataflow for JP/GB/CA/CH/KR); China bilateral (NBS/PBoC) =
   UNVERIFIED-by-absence (marginals only). ECB QSA who-to-whom exists but is euro-area
   *internal* sector marginals in XDC, not merged USD pair cells.

6. **The RAS could not manufacture the missing pairs.** `balancing_pass_log`:
   `converged: false` after 200 passes; row residual stalls at L2 ~ 3.96e6 USD mn
   (~$3.96tn) while column residual ~0. `interpretation`: "rows whose only real support
   points into the US column cannot simultaneously match their BIS USD-claim row
   marginals. Non-convergence is structural sparsity, not a numerical failure." The only
   thing that balanced was the single TIC US-Treasury column closed to its own published
   grand total. **No off-diagonal bilateral mass was recovered.**

7. **The one reallocation magnitude that was attempted is a HOLE.** GCAP
   residency→nationality (`gcap_residency_to_nationality`): the offshore dollar pool is
   real and measured ($2.07tn BIS Cayman+HK; $1.94tn TIC hubs), but the China-attributed
   **share** is a HOLE — "BIS LBS carries L_PARENT_CTY for the REPORTING bank only, NOT
   the counterparty issuer's nationality." The data needed to attribute *who the claim is
   really on* — the exact thing F3/F4 read off — is absent.

---

## 2. Per-factor verdict on a US-centric narrowing

The narrowed model under test: **one debtor = US; holders = the TIC foreign-counterparty
column; internal structure = the 585 Fed US sector × sector cells; funding level = BIS
per-area USD marginals; reserve-currency mix = COFER marginal.** Verdicts:

### F1 funding stress — **IDENTIFIED (bounded).**
F1 is a common-level funding factor. The BIS per-area USD claim/liability **marginals**
(I1 deposits/loans) plus the Fed US-internal S2 depository cells give a genuine
cross-section of USD funding exposure across areas and US sectors. A common funding-stress
factor can be read off this cross-section without any pair structure. The
creditor/debtor BIS asymmetry (7.19%, $711bn, `bis_marginal_asymmetry`) bounds the noise
floor but does not break identification of a *level* factor. Verdict: identifiable for a
bounded US-funding-stress question.

### F2 Treasury de-specialization — **IDENTIFIED (bounded), with a price caveat.**
F2 lives on the safe (Treasury) leg. The TIC single-debtor column is exactly a
quantity-by-holder cross-section on the US Treasury, and the Fed S4-government issuer
cells give the domestic holder split. The *quantity* side of de-specialization (who is
holding more/less of the US safe leg, and the domestic-vs-foreign split) is supported.
Caveat: the *convenience-yield/price* side of de-specialization is a yield observable not
in this matrix at all (the matrix is a stock/position matrix), so F2 is identified only on
its quantity manifestation, and only as a US-Treasury-specific (not cross-safe-asset)
factor. Within that bound: identifiable.

### F3 sanctions reallocation (across counterparties) — **NOT IDENTIFIED.**
F3 is *defined* on the i→j vs i→k substitution pattern — reallocation across
counterparties. The support contains exactly **one** cross-border issuer observed
bilaterally (US). There is **no second debtor column** anywhere: CPIS is a HOLE, SAFE is
a HOLE, OECD/China bilateral are UNVERIFIED-by-absence, and BIS gives marginals not
pairs. With a single issuer column, the "reallocate away from issuer j *into* issuer k"
direction is **unobserved by construction** — the off-diagonal that F3 loads on does not
exist in the matrix and the RAS proved it cannot be recovered ($3.96tn unplaced row
mass). This is not "smaller scope"; the reallocation axis is *absent*, so F3's loadings
are not pinned by any variation. Verdict: NOT IDENTIFIED — and a US-centric narrowing
does not rescue it, because F3 is inter-counterparty by definition and the US-centric cut
keeps only one counterparty axis.

### F4 dollar run (across holders) — **NOT IDENTIFIED / ill-posed against F1.**
F4 is a *contagion-across-holders* factor on the dollar leg. Two problems, both fatal on
this support:
  (a) **No multi-issuer bilateral block** → "exit the dollar" and "exit the US claim"
      collapse to the *same* TIC column. A common dollar-exit factor cannot be separated
      from a US-Treasury-specific quantity move (F2) or a funding-level move (F1), because
      all three project onto the one column the matrix actually carries.
  (b) **The holder-contagion structure (holder a's exit raising holder b's) requires
      holder × holder covariation that the matrix does not contain**: holders appear only
      as 36 marginal entries in one column, with no cross-holder claim structure to carry
      contagion. COFER, which would speak to currency-substitution at the world level, is
      a single marginal with no holder resolution.
Verdict: NOT IDENTIFIED — and *crucially not* because "the run hasn't happened" (that
would be the planting failure this project forbids), but because the **observable block
that would distinguish a dollar-run factor from F1/F2 is structurally absent**. The
non-identification here is a property of the support, and it is the kind that could in
principle be *cured* by adding multi-issuer bilateral data (CPIS, SAFE, OECD
counterpart) — it is data-absence, not a definitional foregone conclusion.

### F3 vs F4 separability (the crux from CLAUDE.md) — **NOT TESTABLE on this support.**
The DP3 mandate requires F3/F4 separation to be a *testable* overidentifying restriction.
On this support there is **no over-identification to test it with**: both factors require
the multi-country-pair off-diagonal that the matrix lacks, so the separating restriction
cannot even be evaluated, let alone rejected. A model run on this support would have to
*assume* the F3/F4 split rather than test it — which is precisely the planting failure
the build exists to refuse. This is an audit finding, not a DP3 specification.

---

## 3. Bottom line: is "narrow the claim" a real option or an empty one?

**It is real for F1/F2 and empty for the breaking-point object itself.**

- A genuinely bounded, *identified* model exists on this support: **a US-centric
  stock model of funding stress (F1) and US-Treasury de-specialization on the quantity
  side (F2)**, built from the TIC single-debtor column + 585 Fed US-internal cells + BIS
  per-area USD marginals + COFER currency marginal. That model is identified and answers
  a real (if smaller) question: *how concentrated and how stressed is the US safe/funding
  leg, and who holds it.*

- But that bounded model is **not the breaking-point model.** Per CLAUDE.md the
  breaking-point object is the locus where a *self-fulfilling reserve-run equilibrium*
  becomes feasible — which is carried by **F4 (the dollar's own run across holders)** and
  attributed against **F3 (sanctions reallocation across counterparties)**. Both of those
  are exactly the factors that are NOT IDENTIFIED on this support, because both are
  inter-counterparty / inter-holder bilateral factors and the support has **one debtor
  column and zero multi-pair structure**. The global cross-country bilateral structure is
  therefore **constitutive**, not decorative: it is the only place the F3 and F4 loadings
  could be read off, and the RAS non-convergence ($3.96tn unplaced) is direct evidence
  that it cannot be synthesized from marginals.

- Therefore "narrow the claim to a US-centric model" **does not narrow the
  breaking-point claim — it changes the subject.** It yields an identified funding/
  safe-asset concentration model (F1/F2) while silently dropping the run and reallocation
  factors (F3/F4) that *are* the breaking point. Presenting the US-centric F1/F2 model as
  a bounded version of the breaking-point question would be a **substitution** (a proxy
  presented as the target). The honest narrowing is to state the F1/F2 model as its own,
  differently-scoped deliverable and to record F3/F4 — and hence the breaking-point
  hazard — as **NOT IDENTIFIED on the current support**, curable only by acquiring
  multi-country-pair bilateral data (CPIS / SAFE / OECD counterpart / a counterparty-
  nationality basis), all currently HOLE or UNVERIFIED-by-absence.

---

## Summary table

| Factor | Variation required | Present in support? | US-centric verdict |
|---|---|---|---|
| F1 funding stress | Funding cross-section (marginal) | Yes — BIS per-area USD marginals + Fed S2 cells | **IDENTIFIED (bounded)** |
| F2 Treasury de-specialization | Safe-leg quantity-by-holder | Yes — TIC US column + Fed S4 cells (quantity only) | **IDENTIFIED (bounded; quantity-only)** |
| F3 sanctions reallocation | Multi-debtor i→j vs i→k off-diagonal | No — one debtor (US); CPIS/SAFE/OECD HOLE/absent | **NOT IDENTIFIED** |
| F4 dollar run | Multi-issuer holder×holder contagion | No — single column; holders are marginals only | **NOT IDENTIFIED (ill-posed vs F1/F2)** |
| F3/F4 separation | Over-identifying multi-pair restriction | No over-identification on this support | **NOT TESTABLE** |

**Constitutive?** Yes — global cross-country bilateral structure is constitutive for F3
and F4 (the breaking-point factors); the RAS non-convergence is the proof it cannot be
recovered from marginals. **Narrowing?** Real for an F1/F2 US safe/funding-concentration
model; empty (a subject-change, not a scope-reduction) for the breaking-point claim,
which depends on the F3/F4 structure that is absent.
