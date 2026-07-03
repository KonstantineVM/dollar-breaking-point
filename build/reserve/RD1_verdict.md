# RD1 — Surface 1 (disclosed currency composition): FREEZE EVENT-STUDY VERDICT

SOURCE: LMW `Data.xls` sheet DATA (`build/reserve/rd0_evidence/lmw_Data.xls`, pandas engine `xlrd`)
crossed with the UN GA ES-11/1 roll-call (`build/reserve/rd0_evidence/un_digitallibrary_es11_1_votelines.txt`).
All coefficients read from the numpy estimator in `build/reserve/RD1_recompute.py`; persisted to
`build/reserve/RD1_result.json`; verifier `build/reserve/RD1_verify.json` (all checks true, byte-reproducible).
Coefficients are NOT hardcoded.

STATUS: OUTPUT — NOT ESTABLISHED for downstream use until the RD1 verifier scenario has run and its
artifact exists on disk. `build/reserve/RD1_verify.json` is that artifact (`all_pass = true`).

## VERDICT (pre-registered decision rule, applied mechanically and sign-agnostically): INSUFFICIENT-POWER

The freeze DiD on the disclosing non-aligned-vs-aligned panel is **underpowered** and cannot distinguish a
dollar reallocation from a null. The primary-window (2010–2023) two-way-FE DiD coefficient on
`Treated × Post` is **β = +0.28 pp** (SE 4.34, p = 0.949, 95% CI **[−8.23, +8.78] pp**). That CI simultaneously
contains 0 and a ±5 pp differential USD-share move (the economically meaningful benchmark), with only **9
treated disclosers** and **2 post-freeze years (2022, 2023)**. The design cannot tell "no differential move"
from "a large USD reallocation." Per the pre-registered rule, that is INSUFFICIENT-POWER — not S1-NULL (the CI
is far too wide to assert a null) and not S1-REALLOCATION (β is ~0, wrong sign, insignificant).

A second, independent reason a causal reading would be unsafe even with more power: the **parallel-trend
pre-trend is fragile and window-dependent** — joint lead test p = 0.088 in the primary window (not violated at
5%, but marginal) and p < 1e-16 in the full sample (clearly violated). The control pre-trend is not clean.

**A third and more fundamental limit is construct validity, not power.** The treated group is 9 small
non-aligned disclosers (Bangladesh, Mongolia, Mozambique, Namibia, South Africa, Sri Lanka, Tanzania, Uganda,
Zimbabwe) — the clean sanctions-exposed reserve holders are ABSENT (Russia excluded for lack of 2022 data;
China absent from S1 entirely). This treated set is therefore a **weak proxy** for the sanctions-exposed
thesis: even a fully-powered, clean-pre-trend S1 freeze DiD on these 9 economies would bear only **weakly** on
whether *sanctions-exposed* reserve managers reallocated out of the dollar. The binding limitation on S1's
ability to test the thesis is construct validity as much as power — INSUFFICIENT-POWER here does not mean "the
thesis was tested and the data were too thin," but "the group that S1 can test is not the group the thesis is
about." (This was flagged in the pre-registration; it is restated here so the verdict is self-contained.)

## The three components, kept separate (never conflated)

### (i) Freeze DiD on the disclosing non-aligned-vs-aligned panel — the actual test
- Estimator: `USD_share_{c,t} = α_c + λ_t + β·(Treated_c × Post_t)`, Post = 1[year ≥ 2022], country + year FE,
  SE clustered by country (numpy; statsmodels not installed).
- Treated (No/Abstain voters with 2022 data, n = 9): Bangladesh, Mongolia, Mozambique, Namibia, South Africa,
  Sri Lanka, Tanzania, Uganda, Zimbabwe.
- Control (Yes voters with 2022 data, n = 38): Afghanistan, Australia, Bosnia, Brazil, Brunei, Bulgaria, Canada,
  Chile, Colombia, DR Congo, Denmark, Finland, Germany, Ghana, Iceland, Israel, Kenya, Macedonia, Malawi,
  Moldova, Nepal, New Zealand, Norway, Papua New Guinea, Paraguay, Peru, Poland, Romania, Serbia, Slovenia,
  Sweden, Switzerland, Turkey, Ukraine, United Kingdom, United States, Uruguay, Zambia.
- **β (primary 2010–2023) = +0.278 pp, SE 4.340, p = 0.949, CI [−8.23, +8.78].**
- **β (full sample 1996–2023) = +0.718 pp, SE 4.152, p = 0.863.** Same sign, same insignificance.
- Event-study (leads/lags rel. 2021 base): every lead and lag with CI is in `RD1_result.json`. No individual
  lead or lag is significant at 5% in the primary window; the largest lead is 2014 (−14.2 pp, p = 0.059).
- **Pre-trend joint test:** primary-window Wald = 17.74, df = 11, p = 0.088 (leads jointly insignificant at 5%,
  but marginal); full-sample Wald = 118.86, df = 17, p < 1e-16 (violated). Pre-trend NOT clean.
- **Power:** 9 treated, 38 control, 2 post-freeze years, CI width ≈ 17 pp vs a 5 pp meaningful move.

### (ii) Russia OBSERVED pre-freeze diversification — labelled, NOT the freeze response
Russia's disclosed series (data-integrity check, reproduced exactly): **USD 47.0% (2007) → 13.89% (2021);
CNY 0% (2007) → 21.78% (2021)**; EUR 42.4% → 43.18%; Other 0 → 13.25%. This is a clean sanctions-exposed unit
diversifying out of USD into CNY across 2007–2021 — a **post-2014-Crimea-sanctions response that PRE-DATES the
Feb-2022 freeze**. It is an observation about 2014–2021, NOT the freeze DiD response, and is **not counted as
one**. Russia is EXCLUDED from the DiD: it has no 2022 LMW row (CBR stopped disclosing post-freeze), so its
post-freeze S1 currency composition is UNOBSERVED. A synthetic-control freeze estimate for Russia is
**impossible** — the post-treatment outcome is missing.

### (iii) China INFERRED residual — NOT observed on S1
China is **absent from the LMW panel (0 rows)**. China's USD share on S1 is a residual inference, never an
observation, and does not enter the DiD. It is reported here only to state that it is not evidence of a freeze
response.

## Assignment discipline (not gerrymandered)
Treated/control membership is assigned **mechanically from the ES-11/1 vote × LMW-2022 availability**, not
chosen by any coefficient. Explicitly excluded, with reasons: Russia (No vote, no 2022 data); China (absent);
Kazakhstan / Angola / South Sudan (Abstain but no 2022 data); Azerbaijan (Non-voting — neither Yes nor
No/Abstain); Euro Area and Hong Kong (not UN members, cast no ES-11/1 vote — a mechanical exclusion, not a hand
pick). Full per-country vote→group mapping is in `RD1_result.json`.

## Comparison to the pre-registered RD1 prediction: HELD
The pre-registration's primary prediction was **INSUFFICIENT-POWER or S1-NOT-IDENTIFIED (or S1-NULL); NOT a
clean S1-REALLOCATION.** The realized verdict is **INSUFFICIENT-POWER** → prediction **HELD**. The one
falsifiable commitment (β negative, significant, flat pre-trend, window-robust → REFUTED → S1-REALLOCATION) is
**not** triggered: β is positive, insignificant, the CI is ~17 pp wide, and the pre-trend is window-dependent.

## Scope
No date, no bare probability, no hazard claim. This characterises the S1 disclosed-currency-composition test
around the Feb-2022 freeze; it is not a DP-side breaking-point object. RD2–RD6 not run.
