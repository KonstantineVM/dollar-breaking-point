# RD2 Surface 2 (gold) — Part 1 provenance: the TONNAGE panel

**Fetched 2026-07-01, outbound HTTPS via the agent proxy. This is a data contract, not a
result. No tonnage value is asserted from memory: every figure below was read from a file
I fetched this run, whose HTTP status and a load-bearing cell are retained under
`build/reserve/rd2_evidence/`. The IMF confidential COFER aggregate is NOT used.**

Design read first: `build/reserve/RD2_prediction.md` (DV = physical tonnes; Turkey voted
YES on ES-11/1 = CONTROL, not treated). Taxonomy source: `build/reserve/RD0_sources.json`.

---

## 1. World Gold Council — PRIMARY tonnage DV — CONFIRMED

- **Publisher / dataset:** World Gold Council (Goldhub), *Central Banks Dashboard v2*
  (node 16034; suppliers listed on the page = `cbks,fsl,imf,wb,WGC`). WGC republishes IMF
  International Financial Statistics official gold holdings with WGC adjustments.
- **Landing page checked:** https://www.gold.org/goldhub/data/gold-reserves-by-country — HTTP 200.
- **Ungated data API used (load-bearing):**
  `GET https://fsapi.gold.org/api/cbd/v11/charts/getPage?page=date_range&periodicity=QTD_FULL&startDate=2019-01-01&endDate=2025-12-31`
  → **HTTP 200**, application/json, 1,105,202 bytes → `rd2_evidence/cbd_quarterly_2019_2025.json`.
  (The dashboard page embeds `apps.gold.org/cbd-app/latest/fs/index.js`, whose query builder
  exposes `page=date_range`, `periodicity` ∈ {`QTD_FULL`=quarterly, `LAST_YEAR_END`=annual},
  `startDate/endDate`, `countries=`. Supporting captures: `cbd_getPage.json`, `cbd_getFilters.json`.)
- **Structure (read from the file):** `chartData.linechart.QTD_FULL.<metric>.data =
  [{name: ISO3, data: [[unix_ms, value], …]}]`. Metrics present: `gold_reserves` (US$ Millions),
  **`gold_reserves_tns` (TONNES)**, `fx_reserves`, `total_reserves`, `holdings_pct` (gold % of
  total reserves), plus `*_pct_chng` variants.
- **Units:** metric **tonnes** for the DV (confirmed from the metric label `unitName:"tonnes"`).
  Conversion used elsewhere: **1 tonne = 32,150.746 fine troy oz**.
- **Coverage:** **123 ISO3 holders**, **28 quarters Q1-2019 … Q4-2025** (metadata
  `minDateAvailable 2000-12-31`, `maxDateAvailable 2026-03-31`). Quarterly.
- **Publication lag:** IFS-inherited ~2 months (page: "data two months in arrears"; late reporters carried forward).
- **Load-bearing cells retained** (`gold_reserves_tns`, tonnes):
  - CHN 2021Q4=1948.31, 2022Q1=1948.31, 2022Q2=1948.31, 2023Q4=2235.39, 2024Q4=2279.56, 2025Q4=2306.30
  - RUS 2021Q4=2301.64, 2022Q1=2304.75, 2022Q2=2323.41, 2023Q4=2332.74, 2024Q4=2332.74, 2025Q4=2326.52
  - USA 2025Q4=8133.46; DEU 2025Q4=3350.25.
- **Friction — WGC .xlsx are login-gated (recorded, NOT used):**
  `GET https://www.gold.org/download/file/8052/Quarterly_gold_and_FX_Reserves_Q1_2026.xlsx`
  → **HTTP 403** (Drupal "Access denied" HTML; `og:title="Access denied"`; free-account login
  required). Same 403 for file 7739 (World Official Gold Holdings) and 12491 (methodology PDF).
  **This is the friction that stalled the prior run's file route; the ungated `fsapi.gold.org`
  JSON API is the robust substitute and carries the same IFS-sourced tonnage.**
- **Confidence: HIGH** — full quarterly tonnage panel, both treated units and the control set
  present, fetched ungated with retained evidence.

## 2. National direct observations of the treated units

### China — SAFE "Official Reserve Assets" — CONFIRMED (gold VOLUME)
- **Page:** https://www.safe.gov.cn/en/2021/0203/2045.html ("Official Reserve Assets (2026)") — HTTP 200.
- **File fetched:** `.../file/file/20260607/2990f3246e4746ffb39dbc70d1b390f8.xlsx` → **HTTP 200**
  → `rd2_evidence/safe_ora_2026.xlsx`.
- **Gold row units: 万盎司 = 10,000 fine troy oz.** Cells:
  2026.01=7419 (74.19M oz), 2026.02=7422, 2026.03=7438, **2026.04=7464万盎司 = 74.64M fine troy oz**.
  74.64M oz ÷ 32,150.746 = **2321.6 tonnes** — consistent with the WGC CHN trajectory.
- China gold is OBSERVED (not inferred), corroborating the WGC panel's visible 2022+ accumulation
  (flat 1948.31 t through 2022Q2 → 2306.30 t by 2025Q4).

### Russia — Bank of Russia — CONFIRMED page, with OPACITY caveat (value, not tonnes)
- **Page:** https://www.cbr.ru/eng/hd_base/mrrf/mrrf_m/ — HTTP 200.
- Monetary gold is published **in USD millions only** (nested under reserves), monthly, and
  **continues to May-2026**. Retained cell: **gold = 24,282 (US$ millions) as of 2025-06-30**.
- **Russia-opacity note (honest):** the CBR public monthly series is a **USD VALUE** (which rises
  mechanically with the gold price), **not a physical-tonnage** series; a direct CBR tonnage series
  was **NOT located** this run. The tonnage picture comes from WGC/IFS, which shows RUS **flat at
  ~2332.7 t Q4-2022→Q4-2024, then −6 t by Q4-2025** — i.e. accumulation halted and granular
  physical disclosure is reduced post-freeze. Observability is stated, not assumed.

## 3. Gold USD price (for the tonnage-vs-valuation decomposition only) — CONFIRMED

- **World Bank Pink Sheet, monthly gold (USD/troy oz)** — independently fetched by me:
  `GET https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx`
  → **HTTP 200**, 778,415 bytes → `rd2_evidence/wb_pinksheet_MYFETCH.xlsx`, sheet "Monthly Prices",
  "Gold" column. Cells: 2019M01=1291.75, 2021M12=1790.43, 2022M03=1947.83, 2024M12=2648.01,
  2025M12=4309.23. Mapped to quarter-end month (Q1→M03 … Q4→M12) as `gold_usd_price_per_oz_wb`.
- **Corroborant — WGC-implied quarter-end price** = median over countries of
  `gold_reserves(US$M)·1e6 / (gold_reserves_tns · 32,150.746)`, column
  `gold_usd_price_per_oz_wgc_implied`. WB vs WGC-implied agree within ~1–2% every checked quarter
  (2019Q1 $1,301 vs $1,295; 2022Q1 $1,948 vs $1,942; 2025Q4 $4,309 vs $4,368).
- **Friction:** the classic FRED LBMA series **GOLDPMGBD228NLBM / GOLDAMGBD228NLBM is discontinued
  on FRED** — `https://fred.stlouisfed.org/series/GOLDPMGBD228NLBM` → **HTTP 301** to a St. Louis Fed
  notice "ICE Benchmark Administration Ltd (IBA) data to be removed from FRED" (Jan-2022). The WGC
  `fsapi.gold.org/api/goldprice/v13/charts/spotprice` endpoint is live (HTTP 200) but **spot-only**.
  World Bank replaces FRED cleanly, so price is **CONFIRMED, not UNVERIFIED**. (The DiD does not
  depend on price; only the decomposition does.)

## 4. IMF IFS official gold (tonnes) — secondary cross-check — TIME-BOXED, friction recorded

Per the anti-hang instruction, two attempts only:
1. `GET https://api.imf.org/external/sdmx/3.0/structure/dataflow/IMF.STA/IFS/+?format=sdmx-json`
   → **HTTP 204** (endpoint alive, No Content; exact restructured monetary-gold indicator code NOT pinned).
2. `GET https://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/IFS/M.RU.RAFAGOLD_OZT`
   → **HTTP 000** (legacy host unreachable).
- **Result:** the 2025 IFS restructuring friction is confirmed (matches RD0). IMF IFS is **NOT
  load-bearing** here — WGC republishes the same IFS tonnage in accessible form. Recorded and moved on.
- **Confidence for this cross-check: LOW** (endpoint not pinned) — but it is only a corroborant.

## 5. Provenance-integrity note — un-attributed files present in the evidence dir

During this run, files I did **not** fetch appeared in `rd2_evidence/` (timestamps interleaved
with, and one after, my own calls — i.e. a concurrent writer): `imf_il_rgv_volume_Q.xml`
(IMF SDMX `IMF.STA:IL` International-Liquidity flow), `worldbank_pinksheet_monthly.xlsx`,
`safe_ora_2020..2025.*`, `cbr_mrrf_m.html`, and the two 403 `.xlsx` stubs I did create.
**These un-attributed files are deliberately NOT part of the verified evidence chain and are NOT
used in the panel** — I cannot attest to the URL checked or HTTP status for fetches I did not
issue, and I do not upgrade an un-provenanced file into a source. The panel and this contract rest
**only** on files I personally fetched (Sections 1–4, HTTP statuses shown). My independent World
Bank price fetch is the distinctly-named `wb_pinksheet_MYFETCH.xlsx`.

---

## Treated / control assignment (MECHANICAL, from ES-11/1)

Assigned in `rd2_build_panel.py` from the RD0-grounded UN GA ES-11/1 roll-call
(`rd0_evidence/un_digitallibrary_es11_1_votelines.txt`): **TREATED = No or Abstain;
CONTROL = Yes; Turkey (Y) = CONTROL.** Non-UN / non-voting holders (Taiwan, Hong Kong, Aruba,
Azerbaijan, Turkmenistan, Uzbekistan, Venezuela, …) → `NA_vote`, excluded from the headline split
but retained in the panel. `country_key` = ISO3, matching the RD0/RD1 vote mapping.
Robustness flag `robust_nonwestern_buyer` = **{TUR}** only (the named large non-Western buyer that
voted YES) — a **labelled sensitivity, explicitly not the headline**; kept minimal to avoid
gerrymandering an EM set into treated. Broader-set membership is a Part-3 decision.

- **TREATED n=24** (20 with 2022+ tonnage): ARM, BDI, BGD, BLR, BOL, **CHN**, COG, DZA, ERI, IND,
  IRQ, KAZ, KGZ, LAO, LKA, MNG, MOZ, NIC, PAK, **RUS**, SLV, SYR, TJK, ZAF.
- **CONTROL n=90** (84 with 2022+ tonnage): US-aligned Yes-voters incl. USA, DEU, JPN, GBR, CHE,
  FRA, ITA, and **TUR** (voted Yes).
- **NA_vote n=9** (7 with 2022+): non-UN/non-voting holders (kept, not classified).

## Panel deliverable

**`build/reserve/RD2_gold_panel.parquet`** — long, country × quarter.
- **rows 3,444 = 123 countries × 28 quarters (2019Q1–2025Q4).**
- Columns: `country_key` (ISO3), `un_name`, `quarter`, `date_qend`,
  **`reserve_gold_tonnes`** (level), **`net_gold_purchases_tonnes`** (the DV = within-country
  quarter-over-quarter first difference of the tonnage level), `gold_usd_value_musd`,
  `fx_reserves_musd`, `total_reserves_musd`, `gold_share_pct`, `gold_usd_price_per_oz_wb`,
  `gold_usd_price_per_oz_wgc_implied`, `es11_1_vote`, `treat_label`, `treated` (1/0/NA),
  `post_freeze` (1 for ≥2022Q1), `robust_nonwestern_buyer`.
- Build script (reproducible): `build/reserve/rd2_build_panel.py`.
- **China observed:** flat 1948.31 t through 2022Q2 → 2306.30 t by 2025Q4 (accumulation timed
  after the freeze). **Russia observed:** rose to ~2332.7 t by end-2022 then flat/slightly down
  (plateau; USD-value series continues but tonnage disclosure reduced).

## Scope

Part 1 only: sources grounded and the tonnage panel built. **Did NOT run the DiD or the
decomposition (Parts 2–3).** Did not touch DP2–DP6, the RD1 currency panel, `build/ledger.json`,
`build/approvals/`, or the operator. Nothing committed.

## Reconciliation note (orchestrator, post-build)

The committed panel is a **single-route WGC build**, cross-checked internally against on-disk evidence.
The tonnage DV comes from the WGC Central Banks Dashboard API (`fsapi.gold.org/api/cbd/v11`, which
republishes IMF IFS gold tonnage; 123-country coverage), committed as
`rd2_evidence/cbd_quarterly_2019_2025.json`. The internal cross-check that the committed files DO support:
the panel carries two price columns — `gold_usd_price_per_oz_wb` (World Bank Pink Sheet,
`rd2_evidence/wb_pinksheet_MYFETCH.xlsx`) and `gold_usd_price_per_oz_wgc_implied` (implied from the WGC
value/tonnage cells) — and these agree, corroborating the value/tonnage reconciliation used in the
Confound-2 decomposition.

A second fetch route ran during the build — the IMF IFS SDMX endpoint directly
(`api.imf.org/.../IMF.STA,IL,13.0.1/{ISO3}.RGV_REVS.FTO.Q`, 39-country coverage) — and, in the
concurrent-writer incident below, its 39-country parquet transiently overwrote the WGC parquet. That IMF
route's raw artifact was among the un-attributed concurrent-writer files quarantined and removed; **it is
NOT retained in the committed evidence directory.** Its earlier apparent agreement on the treated-unit
tonnage is therefore recorded here only as build-time context, **not as a verifiable committed cross-check**
— the verdict rests solely on the WGC panel, and no claim in this build depends on the IMF-direct route.

**Headline panel = the WGC-cbd 123-country build** (`rd2_build_panel.py` + the committed evidence), chosen
for its broader control coverage (more Yes-voter controls -> better-powered treated-vs-control DiD). The
concurrent-writer incident (the two fetch agents overwrote each other's parquet mid-run) was resolved by
standardizing on this single reproducible build: `RD2_gold_panel.parquet` regenerates deterministically from
`rd2_build_panel.py` + `rd2_evidence/{cbd_quarterly_2019_2025.json, wb_pinksheet_MYFETCH.xlsx}` and the RD0
ES-11/1 vote file. Valuation caveat carried: national gold *value* uses mixed statutory/market conventions
(e.g. US books at $42.22/oz), so the tonnage-vs-price decomposition anchors to the market-price columns and
to a window where both tonnes and price are observed.
