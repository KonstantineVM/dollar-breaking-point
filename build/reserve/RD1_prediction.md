# RD1 — Surface 1 (disclosed currency composition): PRE-REGISTERED PREDICTION

**Timestamp: 2026-07-01 (committed BEFORE the RD1 panel is assembled and BEFORE the freeze event-study is
run — the LMW dataset is grounded/fetched (RD0), but the panel and the estimation do not yet exist).**

Pre-registration, committed first. The prediction below **may be REFUTED**, and any endpoint is a valid
finding. The treated set is fixed here by the grounded UN criterion (not chosen by any coefficient); the China
residual is never presented as an observation; Russia's pre-freeze diversification is not relabeled as the
freeze response.

## What S1 can and cannot see (a-priori, from RD0 grounding — stated before estimation)

S1 = the Laser–Mihailov–Weidner (LMW) disclosed currency-composition panel (`build/reserve/rd0_evidence/
lmw_Data.xls`, sheet DATA: country/year/USD/EUR/JPY/CAD/CNY/GBP/AUD/Other; 64 economies, 1996–2023; 50 have
2022). Two load-bearing observability facts, grounded in RD0:
1. **Russia — the clean treated (frozen) unit — discloses only through 2021.** Its post-freeze currency
   composition is **UNOBSERVED on S1** (CBR stopped publishing after Feb-2022). Russia's dramatic **pre-freeze**
   diversification (USD 47%→13.9%, CNY 0→21.8% across 2007–2021) is observed, but it **pre-dates the freeze**
   (post-2014-Crimea-sanctions response) and is **not** the freeze response.
2. **China is absent from the LMW panel** (0 rows). China's USD share on S1 is a **residual inference**, not an
   observation, and is reported as such — never as evidence of a freeze response.

Consequently the **freeze event-study/DiD on S1** cannot use Russia's post-2022 response or observe China
directly. It rests on the broader **non-US-aligned discloser set with 2022 data vs the US-aligned disclosers**
— an indirect, weaker test — with **annual** disclosure and **few treated disclosing units**. This is
intrinsically low-power.

## The design (fixed here)

**Data-integrity check (must pass before estimation):** replicate Russia's disclosed series from the DATA
sheet — USD 47.0% (2007) → 13.89% (2021) and CNY 0 → 21.78% (2021). If this does not reproduce, the panel is
mis-read and estimation halts.

**Treated/control (grounded on UN GA ES-11/1 roll-call, RD0 taxonomy):**
- TREATED (freeze DiD) = **non-US-aligned disclosers**: LMW countries that voted **No or Abstain** on ES-11/1
  AND have post-2022 LMW data. (Russia excluded — no 2022 data; China excluded — not in panel. So the treated
  group is the *other* non-aligned disclosers, e.g. abstainers among the 50 with 2022 data — a weak proxy for
  "sanctions-exposed," stated honestly.)
- CONTROL = **US-aligned disclosers**: LMW countries that voted **Yes** and are not sanctions-exposed, with
  post-2022 data.
- The exact treated/control membership is assigned mechanically from the ES-11/1 vote (RD0 taxonomy) crossed
  with LMW 2022 availability — reported in full in RD1_result.json, not hand-picked.

**Estimator:** two-way fixed-effects DiD / event study on the **disclosed USD share**:
USD_share_{c,t} = α_c + λ_t + β·(Treated_c × Post_t) + ε, Post_t = 1 for year ≥ 2022 (the freeze). α_c country
FE, λ_t year FE. **β = the differential post-freeze USD-share change, treated vs control.** S1 dollar
reallocation = **NEGATIVE β** (non-aligned reserve managers cut USD share after the freeze, relative to
aligned). SE clustered by country; report the 95% CI.

**Event-study form (the validity check):** year dummies relative to **2021 (base)** — leads (pre-2022) and lags
(2022+). The **pre-trend test** = the leads jointly ≈ 0 and insignificant (parallel pre-trend). Report every
lead and lag with CIs so a pre-trend violation is VISIBLE. **No leave-one-quarter-out** (invalid for an event
study — the DiD lesson); the pre-trend leads ARE the robustness check.

**Russia as a separate pre-freeze case study:** report Russia's observed 2007–2021 USD/CNY trajectory as a
labelled *pre-freeze diversification* observation — the clean sanctions-exposed unit diversifying, but before
the 2022 freeze and now unobservable — explicitly NOT counted as the freeze DiD response. If a synthetic
control were attempted, note that Russia's **post-freeze outcome is missing**, so no synthetic-control freeze
estimate is possible either; Russia is a pre-freeze observation, not a freeze estimate.

## Decision rule (applied in the verdict, after the numbers)

- **S1-REALLOCATION** — β NEGATIVE, significant, with a FLAT pre-trend (leads jointly insignificant), robust to
  the window. Non-aligned disclosers cut USD share after the freeze relative to aligned; state magnitude + the
  pre-trend evidence (the flat pre-trend is what makes it causal).
- **S1-NULL** — β ≈ 0 with adequate power and a flat pre-trend. No differential post-freeze USD-share move.
- **S1-NOT-IDENTIFIED** — no valid control pre-trend (leads significant); β not interpretable. Reported
  honestly; a broken-pre-trend β is not sold as causal.
- **INSUFFICIENT-POWER** — CI too wide (annual data, small treated N) to distinguish. State what would resolve.

## The falsifiable prediction (sign-agnostic; power-and-observability-pessimistic)

> **Primary prediction: INSUFFICIENT-POWER or S1-NOT-IDENTIFIED (or S1-NULL).** A-priori: the clean treated
> unit (Russia) is unobserved post-freeze; China is a residual; the freeze DiD rests on a small set of
> non-aligned disclosers that are a weak proxy for sanctions exposure; annual disclosure gives few post-freeze
> points and a small treated N. I therefore expect the S1 freeze DiD to be underpowered or not cleanly
> identified — NOT a clean S1-REALLOCATION. I do NOT favor the null: if the non-aligned disclosers show a
> robust, pre-trend-valid post-2022 USD-share drop relative to aligned disclosers, that is **S1-REALLOCATION**
> and the finding.
>
> **The one falsifiable commitment:** if β is negative, significant, with jointly-insignificant leads (flat
> pre-trend) and robust across the window, the primary prediction is REFUTED → S1-REALLOCATION. I do not
> predict β's sign; a null, a positive, or a non-identified design are all admissible.
>
> Separately (NOT the freeze test): Russia's **pre-freeze** USD 47→14 / CNY 0→22 diversification is expected to
> replicate (the data-integrity check). Its replication is an observation about 2014–2021, and by itself does
> **not** establish a 2022-freeze response — conflating the two would be the error this pre-registration guards
> against.

## Anti-planting commitments

- β and the event-study lead/lag coefficients **read from the estimator, never hardcoded.**
- Treated/control membership fixed by the ES-11/1 vote × LMW-2022 availability — **not gerrymandered** to
  produce a USD-share drop; the full membership list is reported.
- The China residual is **never** presented as an observation; Russia's pre-freeze diversification is reported
  as pre-freeze, not as the freeze response.
- The pre-trend leads/lags are **computed, persisted, and verifier-reproduced**; no LOQO. Power reported
  honestly — a wide-CI or broken-pre-trend result is INSUFFICIENT-POWER / NOT-IDENTIFIED, not S1-NULL.

## Scope

STOPS after the prediction, the S1 panel, the freeze event-study result, the recompute script, and the S1
verdict. Does NOT run RD2–RD6 (each is a separate human-gated stage). Does NOT build a hazard, does NOT touch
DP2–DP6. No date, no bare probability, no hazard claim. Reserve-side reallocation is characterised, not a
DP-side breaking-point object.
