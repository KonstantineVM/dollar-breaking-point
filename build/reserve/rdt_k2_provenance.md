# RDT k2 — Provenance (official gold tonnes, extended history + reserve denominators)

Built 2026-07-01 by the k2 grounding agent. Every value in `rdt_k2_gold.csv` is read from a
raw file fetched this run and retained under `build/reserve/rdt_evidence/gold_history/`.
Nothing is asserted from memory. Fetch log: `rdt_evidence/gold_history/_RDT_fetch_log.txt`.

## SOURCE lines

- SOURCE: WGC Central Banks Dashboard API (republishes IMF IFS official gold holdings, tonnes) —
  `https://fsapi.gold.org/api/cbd/v11/charts/getPage?page=date_range&periodicity=QTD_FULL&startDate=2000-01-01&endDate=2026-12-31`
  — fetched 2026-07-01, HTTP 200, 3,859,095 bytes → `rdt_evidence/gold_history/cbd_quarterly_2000_2026.json`.
  Structure identical to the RD2 fetch (`chartData.linechart.QTD_FULL.gold_reserves_tns.data`
  = `[{name: ISO3, data: [[ts_ms, tonnes], ...]}]`); 123 holders; quarterly 2000Q4–2026Q1.
  The API accepted the extended (pre-2019) window directly — the PRIMARY route succeeded, so the
  IMF IFS fallback and the (login-gated, per RD2 log) WGC historical .xlsx were NOT needed.
- SOURCE: World Bank API, indicator FI.RES.TOTL.CD (total reserves incl. gold, current US$) —
  `https://api.worldbank.org/v2/country/RUS;CHN;IND;TUR;SAU;POL/indicator/FI.RES.TOTL.CD?format=json&date=2010:2026&per_page=300`
  — fetched 2026-07-01, HTTP 200, 22,615 bytes → `rdt_evidence/gold_history/wb_FI_RES_TOTL_CD.json`.
- SOURCE: World Bank API, indicator FI.RES.XGLD.CD (total reserves minus gold, current US$) —
  `https://api.worldbank.org/v2/country/RUS;CHN;IND;TUR;SAU;POL/indicator/FI.RES.XGLD.CD?format=json&date=2010:2026&per_page=300`
  — fetched 2026-07-01, HTTP 200, 22,231 bytes → `rdt_evidence/gold_history/wb_FI_RES_XGLD_CD.json`.
- SOURCE (reconciliation input, READ-ONLY): `build/reserve/RD2_gold_panel.parquet`, column
  `reserve_gold_tonnes` (committed RD2 artifact, 2019Q1–2025Q4).

## Construction

`rdt_k2_gold.csv` — columns: country, year, gold_tonnes (year-end = Q4 value of the quarterly
WGC/IFS series), total_reserves_usd_bn, reserves_ex_gold_usd_bn (World Bank values / 1e9),
source. Countries: RUS, CHN, IND, TUR, SAU, POL + USA (tonnage stability anchor); years
2010–2025; 112 rows. USA carries no denominators (outside the six-holder denominator scope).

## Integrity anchor (mandatory) — PASS

Russia's 2014–2020 accumulation is visible in the built series, quoted from `rdt_k2_gold.csv`:
**end-2013 = 1,035.21 t → end-2014 = 1,208.19 t → end-2020 = 2,298.53 t** (end-2021 = 2,301.64 t).
Order ~1,000 t → ~2,300 t: satisfied.

USA stability anchor: 8,133.46 t at end-2010 and at end-2025 (flat throughout), consistent with
the expected ~8,133.5 t.

## RD2 overlap reconciliation (2019+)

All 28 overlapping quarters (2019Q1–2025Q4) compared per country against the committed RD2 panel:
max |tonnes diff| = **0.0 t for all seven countries** (RUS, CHN, IND, TUR, SAU, POL, USA). Exact
match — same publisher API, fetched the same day; no revisions observed in the overlap window.
The RD2 panel was not modified.

## Observed source features (reported as published; not adjusted, not explained from memory)

- TUR: flat at ~116.1 t 2010–2016, then rising from 2017 to 614.30 t (2025), as published.
- CHN: 1,054.09 t (2010–2014) stepping to 1,762.31 t (2015) — the 2015 disclosure step is in the
  source data as published; latest 2,306.30 t (end-2025).
- SAU: essentially flat, 322.90 → 323.07 t across 2010–2025.
- RUS: post-2021 plateau — 2,332.74 t for 2022–2024, 2,326.52 t for 2025 (consistent with the
  RD2 opacity caveat on Russian disclosure after the freeze).

## NOT-AVAILABLE (recorded honestly)

- RUS World Bank denominators for 2025: FI.RES.TOTL.CD / FI.RES.XGLD.CD end at 2024 for RUS in
  the fetched JSON (no 2025 observation returned). Not substituted.
- USA denominators: not fetched (out of scope by task definition).

## Note for the recompute stage

These grounded values are inputs; any distance/velocity/composite derived from them is an
estimation OUTPUT and is NOT ESTABLISHED until `RDT_recompute.py` runs and `RDT_verify.json`
exists (per RDT_prediction.md anti-planting commitments). China's FI.RES.TOTL.CD series here
(2010–2025; 2025 = 3,748.7 $bn) also feeds the pre-registered k1-China residual as R_C,t.
