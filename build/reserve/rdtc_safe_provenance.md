# RDT-C Part 1 — SAFE totals leg: provenance

All fetches issued by this agent on **2026-07-02** via the pre-configured proxy; raw files retained in
`build/reserve/rdtc_evidence/` (byte sizes and HTTP statuses in `_RDTC_fetch_log.txt`). The task's
search-summary figure (~+$230bn 2022→2025) was **not trusted**; every number below is from these fetches.

## SOURCE lines

- SOURCE: SAFE (State Administration of Foreign Exchange), "Official Reserve Assets" — English channel
  index https://www.safe.gov.cn/en/ForexReserves/index.html (HTTP 200, fetched 2026-07-02), listing the
  yearly data pages used.
- SOURCE: SAFE yearly English pages (all HTTP 200, fetched 2026-07-02):
  - 2021: https://www.safe.gov.cn/en/2021/0203/1798.html → xlsx `/en/file/file/20220128/b62ccc0d28dc401ba16712f592ecd2a0.xlsx` → `safe_ora_2021_MYFETCH.xlsx`
  - 2022: https://www.safe.gov.cn/en/2021/0203/2113.html → xlsx `/en/file/file/20230131/99ae51feb9114aad94ef12715ab95cda.xlsx` → `safe_ora_2022_MYFETCH.xlsx`
  - 2023: https://www.safe.gov.cn/en/2021/0203/2174.html → xlsx `/en/file/file/20240124/612f20d0024b41ec9d8ece9250b922cf.xlsx` → `safe_ora_2023_MYFETCH.xlsx`
  - 2024: https://www.safe.gov.cn/en/2021/0203/2280.html → xlsx `/en/file/file/20250107/cccae56ba9204e43821b62c8441bbea8.xlsx` → `safe_ora_2024_MYFETCH.xlsx`
  - 2025: https://www.safe.gov.cn/en/2021/0203/2386.html → xlsx `/en/file/file/20260207/532af9a5edf040fb95117264b66a748c.xlsx` → `safe_ora_2025_MYFETCH.xlsx`
  - 2026: https://www.safe.gov.cn/en/2021/0203/2045.html → xlsx `/en/file/file/20260607/2990f3246e4746ffb39dbc70d1b390f8.xlsx` → `safe_ora_2026_MYFETCH.xlsx`
- SOURCE: SAFE Chinese-language data pages (same publisher; fill the two English-file seam months;
  both HTTP 200, fetched 2026-07-02):
  - 官方储备资产（2024）https://www.safe.gov.cn/safe/2022/0207/23934.html — inline table with **2024.12
    populated** (FX 32023.57 亿USD, total 34555.58, gold 1913.37 / 7329万盎司) → `safe_cn_ora_2024.html`
  - 官方储备资产（2026）https://www.safe.gov.cn/safe/2026/0206/27116.html — inline table populated through
    **2026.05** (FX 34422.38 亿USD, total 38505.86, gold 3407.52 / 7496万盎司) → `safe_cn_27116.html`
- SOURCE (read-only cross-checks, on disk, not re-fetched):
  - `build/reserve/rd2_evidence/safe_ora_2021..2026.xls*` — un-attributed per RD2 provenance §5; used as
    a **soft** cross-check only.
  - `build/reserve/rdt_k2_gold.csv` — WGC/IFS Q4 gold tonnage (CHN rows).
  - `build/reserve/rd2_evidence/wb_pinksheet_MYFETCH.xlsx` — World Bank Pink Sheet monthly gold price
    (coverage ends 2025-12).

## Units and structure (read from the release, not assumed)

- Values in **亿美元 = 100 million USD** (and a parallel 亿SDR column, not used); converted to USD bn by /10.
- Gold volume row in **万盎司 = 10,000 troy oz**; converted to million oz by /100.
- Rows: 1. 外汇储备/Foreign currency reserves (the **ex-gold FX line** the closure test uses);
  2. IMF reserve position; 3. SDRs; 4. Gold (value + volume); 5. Other reserve assets; 合计/Total.

## Frictions found (publisher-side, verified this run)

1. **The English 2024 file ends at 2024.11** — the 2024.12 column is empty in the publisher's own
   current file (so the RDT-B empty-2024.12 finding stands and is a property of the publisher's English
   file, not of the earlier on-disk copy). Filled from the Chinese 2024 page (same publisher);
   the CSV has **no gap**.
2. **The English 2026 file (dated 2026-06-07) ends at 2026.04**, one month behind the Chinese page,
   which carries 2026.05. Latest month in the CSV is therefore **2026-05**, sourced from the Chinese page.
3. Sheet2/Sheet3 of the 2025/2026 English xlsx are empty; the SDR line breaks upward in 2021-08
   (IMF general SDR allocation) — outside the CSV window start, noted for completeness.

## Cross-check results

- English-xlsx vs Chinese-HTML overlaps (2024.01–11, 2026.01–04; all 7 fields): **zero diffs**.
- My fetch vs on-disk `safe_ora_*` files (all overlapping months 2021-01..2026-04): **zero diffs**;
  the on-disk set lacks 2024-12 and 2026-05, both supplied here.
- SAFE Dec gold volume → tonnes vs `rdt_k2_gold.csv` (WGC/IFS): max diff **0.02 t** (rounding), 2021–2025.
- SAFE-implied gold price (value/volume) vs WB Pink Sheet: within **0.9%** (2021-12), **0.3%** (2022-03),
  **0.02%** (2025-12).

## Valuation caveats (carried into the closure)

- **Gold leg, quantified (2021-12 → 2026-05):** total reserves rose **+423.7 bn**; gold value rose
  **+227.6 bn**, of which **+171.6 bn is price valuation** on the initial 62.64 Moz (price $1,806 →
  $4,546/oz, SAFE-implied) and **+56.0 bn is purchased volume** (62.64 → 74.96 Moz) at the end price.
  I.e. **~40.5% of the total-reserves rise is gold-price valuation** — the reason the closure test uses
  the ex-gold FX line.
- **Inside the FX line, bounded but not decomposable:** SAFE publishes no monthly currency/instrument
  composition, so non-USD-currency and bond-price valuation cannot be split out. Direction: the 2022
  rates selloff + USD strength **cut** the FX line with zero selling (observed −197.7 bn, 2021-12 →
  2022-10 trough); the 2023–2025 rally **partially reversed** it, flattering rises measured from 2022
  starting points.

## Closure numbers (FX-reserves ex-gold line, USD bn; verdict rule NOT applied here)

| window | start | end | Δ | direction |
|---|---|---|---|---|
| verdict axis (RDT-B recent-3y) 2023-05 → 2026-04 | 3176.508 | 3410.547 | **+234.039** | ROSE |
| freeze era 2022-03 → 2026-05 (latest) | 3187.994 | 3442.238 | **+254.244** | ROSE |
| calendar, end-2021 → end-2025 | 3250.166 | 3357.869 | **+107.703** | ROSE |
| calendar, end-2022 → end-2025 | 3127.691 | 3357.869 | **+230.178** | ROSE |

(The end-2022→end-2025 row reproduces, now grounded, the untrusted ~+$230bn search figure. Both readings
of "calendar 2022→2025" are reported; neither is privileged.)
