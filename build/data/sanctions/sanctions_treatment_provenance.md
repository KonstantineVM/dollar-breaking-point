# Sanctions treatment + regulatory control — provenance & fiscal-quarter mapping

Part 1 of the sanctions-shock F3 test (build/audit/sanctions_shock_prediction.md).
Grounding only; the regression is Part 2. Every date/count is grounded to a primary
publisher in `build/contracts/sanctions_sources.json` with raw evidence under
`build/data/sanctions/evidence/`. Fetched 2026-07-01.

Panel: `sanctions_treatment_panel.csv`, 22 rows keyed by `fiscal_quarter`
(2019q3..2024q4), merges onto `build/data/nport/panel_crosswalk_tagged_full.parquet`
(key confirmed present with exactly these 22 values).

## Event -> fiscal_quarter mapping

| Event | Calendar date (grounded) | Primary source | fiscal_quarter | Column |
|-------|--------------------------|----------------|----------------|--------|
| Russian central-bank FX-reserve freeze (OFAC Directive 4, E.O. 14024) | **2022-02-28** (allied commitment 2022-02-26) | Treasury press release jy0612 (datetime 2022-02-28T12:30:00Z) | **2022q1** | `sanc_freeze_post` = 1 from 2022q1 on |
| E.O. 14114 secondary-sanctions EO (amends E.O. 14024) | **2023-12-22** (signed; pub. 2023-12-26) | Federal Register 2023-28662, EO 14114, 88 FR 89271 | **2023q4** | `sanc_eo2023_post` = 1 from 2023q4 on |
| NS-CMIC (CMIC-EO13959) additions | 2021-08-02 (n=59); 2022-02-08 (n=1); 2022-02-14 (n=8) | OFAC Consolidated list cons_prim.csv, per-entry "Effective Date (CMIC)" | 2021q3 (59), 2022q1 (9) | `sanc_intensity` (count) |
| HFCAA CII determinations begin | first conclusive cohort **2022-03-30** (= 2022-03-08 provisional five) | On-disk SEC-sourced list `hfcaa_conclusive.json` | **2022q1** | `reg_hfcaa_post` window start |
| PCAOB access determination (vacates 2021 determinations; pauses delistings) | **2022-12-15** | PCAOB news release + SEC HFCAA page | **2022q4** | `reg_hfcaa_post` window end |
| Didi / China tech-regulatory crackdown onset | IPO 2021-06-30; CAC review July 2021; delisting Form 25 2022-06-02 | SEC EDGAR DiDi Global submissions (CIK 1764757) | **2021q3** | `reg_crackdown_post` = 1 from 2021q3 on |
| Outbound-investment EO (E.O. 14105) — CORRECTION: Aug 2023, not Dec 2023 | **2023-08-09** (signed; pub. 2023-08-11) | Federal Register 2023-17449, EO 14105, 88 FR 54867 | 2023q3 | (context only; not a headline column) |

Notes on the N-PORT convention: the one-quarter N-PORT dissemination-vs-fiscal offset
matters only for the panel's own quarter keying (already handled upstream in
`panel_crosswalk_tagged_full.parquet`). Each **calendar event above is mapped to the
fiscal quarter it falls in**, as instructed.

## Column definitions (as built)

- `sanc_freeze_post` — 1 from 2022q1 onward (RCB reserve-freeze quarter on). The F3 triggering step.
- `sanc_eo2023_post` — 1 from 2023q4 onward (EO 14114 quarter on). The distinct-timing lever.
- `sanc_intensity` — NS-CMIC additions per quarter: 2021q3=59, 2022q1=9, else 0.
  **SURVIVORSHIP-BIASED** (current-snapshot list; removed entities absent) and **SPARSE**
  (non-zero in only 2 quarters). Retained as a documented robustness regressor; the
  pre-registered **primary** sanctions treatment is the event dummies, not this series.
- `reg_hfcaa_post` — 1 for the delisting-risk window **2022q1..2022q4 inclusive** (CII
  determinations begin 2022q1 through the PCAOB-access-restored quarter 2022q4), per the
  pre-registration. A bounded window, not an open step.
- `reg_crackdown_post` — 1 from 2021q3 onward (Didi/tech-crackdown onset).

## Sanctions-vs-regulatory step correlations (22 quarters) — load-bearing

Measured on the built panel:

| pair | Pearson r |
|------|-----------|
| sanc_freeze_post vs reg_crackdown_post | **0.8281** |
| ANY sanctions step vs ANY regulatory step | **0.8281** |
| sanc_freeze_post vs sanc_eo2023_post | 0.4951 |
| sanc_freeze_post vs reg_hfcaa_post | 0.4303 |
| sanc_eo2023_post vs reg_crackdown_post | 0.4100 |
| reg_hfcaa_post vs reg_crackdown_post | 0.3563 |
| sanc_intensity vs reg_crackdown_post | 0.1893 |
| sanc_intensity vs reg_hfcaa_post | -0.0321 |
| sanc_eo2023_post vs reg_hfcaa_post | **-0.2557** |

**Interpretation.** The headline sanctions step (`sanc_freeze_post`, 2022q1 on) is
strongly collinear (r=0.828) with the crackdown step (`reg_crackdown_post`, 2021q3 on) —
exactly the co-movement the pre-registration flags as making the sanctions/regulatory
separation intrinsically hard over 22 quarters. Two levers break the collinearity, both
identified in the pre-registration: (a) `reg_hfcaa_post` is a **bounded** 2022q1–2022q4
window, so it is only weakly correlated with the persistent freeze step (0.43) and
**negatively** correlated with the later EO-2023 step (-0.26); (b) `sanc_eo2023_post`
(2023q4 on) has timing distinct from the 2021–2022 regulatory ramp. These timing
differences are the only way to distinguish the channels, and are what the with/without-
control comparison in Part 2 will exploit.
