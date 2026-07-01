# RD2 — Surface 2 (gold): PRE-REGISTERED PREDICTION

**Timestamp: 2026-07-01 (committed BEFORE the RD2 gold panel is built and BEFORE any estimation — the WGC/IFS/
national gold sources are to be fetched in Part 1; the panel and the DiD do not yet exist).**

Pre-registration, committed first. The prediction below **may be REFUTED**, and any endpoint is a valid
finding. The treated set is fixed here by the grounded UN criterion; the dependent variable is fixed here as
physical **tonnes**; a value/share result is disallowed as the headline.

## Why this surface, and the two confounds that decide it

The mechanism's primary escape hatch: the IMF's own finding is that sanctions shifted reserves **into gold**,
which COFER excludes by construction — so part of any reallocation **leaves the currency data (S1) and lands
here**. Unlike S1 (blind to Russia post-2021 and China always), **China AND Russia both publish gold tonnage**,
so on this surface the treated units are **directly observed**. But a post-2022 gold rise is meaningful for the
sanctions thesis ONLY if it survives two confound strips:

- **CONFOUND 1 — UNIVERSAL TREND.** Central banks bought gold at record pace in 2022–2023 broadly (WGC). "Treated
  bought gold" is NOT the test; the test is the **treated-vs-control DIFFERENTIAL** — did sanctions-exposed
  holders buy *differentially more* than US-aligned holders, net of the common trend.
- **CONFOUND 2 — TONNAGE NOT VALUATION.** The gold price ran up ~2022–2025; USD value and gold's reserve *share*
  rise mechanically from price with **zero buying**. The dependent variable is **physical tonnes of net
  purchases**, never USD value or share. Any share/value series must be decomposed into tonnage (active) vs
  price-on-existing-stock (valuation); a share rise that is entirely price is a **NULL** for accumulation.

## Treated/control (grounded on ES-11/1; a conflict surfaced, not silently resolved)

Headline treated/control is fixed **mechanically by the UN GA ES-11/1 roll-call** (RD0 taxonomy, grounded):
**TREATED = No/Abstain voters** (Russia = No; China, India, South Africa, Kazakhstan, … = Abstain), **CONTROL =
Yes voters** (US-aligned disclosers), restricted to countries with gold-tonnage data.

**Conflict surfaced (per the honor-instructions rule):** the task names **Turkey** as a treated "non-aligned
buyer," but **Turkey voted YES** on ES-11/1 — so by the grounded criterion Turkey is a **control**, not treated.
Including a large gold buyer as treated against its own vote would be **gerrymandering toward a differential**.
Therefore: the **headline** treated set is the ES-11/1 No/Abstain group (Turkey excluded from treated). A
**labelled robustness variant** may add a broader "large non-Western buyer" set (Turkey, and other large EM
buyers) to test sensitivity — but that variant is **explicitly not the headline** and its looser classification
is disclosed. The verdict rests on the grounded (vote-based) headline; if the differential appears ONLY under
the looser Turkey-included set, that is reported as gerrymander-sensitive, not as the finding.

## The design (fixed here)

**Dependent variable:** per-country per-quarter **net gold purchases in TONNES** (from WGC country demand and/or
IFS official-gold-reserve tonnage first-differences), 2019–2025 (spanning the Feb-2022 = 2022q1 freeze).

**Estimator (Part 3a):** two-way FE DiD / event study on gold TONNAGE:
tonnes_{c,t} = α_c + λ_t + β·(Treated_c × Post_t) + ε, Post_t = 1 for t ≥ 2022q1. α_c country FE, λ_t quarter
FE (absorb the universal trend — Confound 1). **β = the differential post-freeze tonnage change, treated minus
control.** Gold reallocation = **POSITIVE β** (treated accumulate differentially more tonnes after the freeze).
SE clustered appropriately; report the 95% CI. Event-study leads/lags relative to 2021q4 base; the **pre-trend
test** = leads jointly ≈ 0 (parallel pre-trend). Report every lead/lag with CIs. **No LOQO** (invalid for an
event study — the pre-trend leads are the robustness check).

**China + Russia observed case studies (Part 3b):** from national monthly tonnage (PBoC troy-oz official gold;
CBR gold), is the accumulation **timed to the freeze** (2022q1+, not just "post-2020"), and how large in tonnes?
Russia's post-freeze gold reporting may be opaque — observability stated honestly, not assumed.

**Decomposition (Part 3c):** for the treated units, split any gold-share/value rise into **tonnage-change
(active)** vs **price-change-on-existing-stock (valuation)** and report both — the Confound-2 check.

## Decision rule (applied in Part 4)

- **GOLD-REALLOCATION-PRESENT** — treated-vs-control tonnage differential β POSITIVE, significant, FLAT
  pre-trend, TIMED to the freeze (the lags load 2022q1+, not before), AND the treated accumulation is TONNAGE
  not valuation. Sanctions-exposed central banks differentially accumulated gold post-freeze — the escape-hatch
  surface loads. State magnitude in tonnes + the China/Russia observed pieces.
- **GOLD-NULL** — no treated-vs-control differential (universal surge), OR the rise is price not tonnage, OR the
  differential is not timed to the freeze. Gold shows no sanctions-specific reallocation once trend and
  valuation are stripped. State which (universal / price / mistimed).
- **NOT-IDENTIFIED** — no valid control pre-trend (leads significant); β not interpretable (a broken-pre-trend
  β is not sold as causal).
- **INSUFFICIENT-POWER** — CI too wide (few treated units / few post quarters) to distinguish.

## The falsifiable prediction (sign-agnostic; confound-pessimistic)

> **Primary prediction: GOLD-NULL or INSUFFICIENT-POWER — the post-2022 gold surge is most likely UNIVERSAL
> (broad central-bank buying) and partly PRICE-DRIVEN, either of which is a null for the sanctions thesis once
> stripped.** But — crucially, and unlike S1 — the treated units (China, Russia) ARE directly observed here, so
> this surface CAN test the thesis rather than a weak proxy. I do NOT favor the null: if treated buy
> *differentially more* tonnes with a flat pre-trend timed to 2022q1, that is **GOLD-REALLOCATION-PRESENT** and
> the finding. I do not predict β's sign.
>
> **The one falsifiable commitment:** if the treated-vs-control tonnage differential is positive, significant,
> pre-trend-valid, freeze-timed, AND survives the tonnage-not-valuation decomposition, the primary prediction is
> REFUTED → GOLD-REALLOCATION-PRESENT. A universal surge, a price-driven (not tonnage) rise, a mistimed
> differential, or a broken pre-trend each REFUTE nothing — they are the expected null.

## Anti-planting commitments

- Dependent variable is **physical tonnes**, never USD value or share; a value/share-based headline is
  **disallowed** and would be a Confound-2 failure. Any share series is decomposed tonnage-vs-price.
- Treated/control fixed by the ES-11/1 vote; **Turkey (Yes) is not in the headline treated set**; the broader
  buyer set is a labelled robustness only. The full membership is reported; the set is not gerrymandered toward
  a differential.
- β and the event-study lead/lag coefficients **read from the estimator, never hardcoded**; the pre-trend +
  leads/lags are computed, persisted, and verifier-reproduced; no LOQO.
- Timing is checked against the freeze specifically (2022q1+), not "post-2020"; a mistimed surge is not the
  freeze response.
- Sources public/national/primary (WGC, IMF IFS, PBoC/CBR, LBMA/FRED); the IMF confidential COFER aggregate is
  not used. A NOT-AVAILABLE source is recorded, not substituted.

## Scope

STOPS after the prediction, the gold panel, the DiD/decomposition result, the recompute script, and the
verdict. Does NOT run RD3–RD6 (each separately human-gated). Does NOT touch DP2–DP6 or the RD1 currency panel.
No date, no bare probability, no hazard claim.
