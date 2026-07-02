# RDT-D Part 3 — SDDS Reserves Data Template ingestion: provenance

All fetches issued by this agent on **2026-07-02** via the pre-configured proxy. Every raw file is
retained in `build/reserve/rdtd_evidence/` (HTTP statuses and byte sizes per fetch in
`_RDTD_fetch_log.txt`). Nothing below is asserted from memory or from secondary sources; the data
month of every template file is read from the **As-at header inside the file**, never from the link
label.

## SOURCE lines — channel and index pages (all HTTP 200, fetched 2026-07-02)

- SOURCE: SAFE English forex-reserves channel index —
  https://www.safe.gov.cn/en/ForexReserves/index.html → `safe_en_forexreserves_index.html`.
  Lists the yearly "Data Template on International Reserves and Foreign Currency Liquidity" pages
  (2018–2026) and the 2015.06–2017.12 sub-channel.
- SOURCE: SAFE yearly Data Template pages (each carrying direct monthly .xls links):
  - 2026: https://www.safe.gov.cn/en/2021/0203/1799.html → `sdds_page_2026.html` (5 links, 01–05)
  - 2025: https://www.safe.gov.cn/en/2021/0203/2397.html → `sdds_page_2025.html` (12 links)
  - 2024: https://www.safe.gov.cn/en/2021/0203/2288.html → `sdds_page_2024.html` (12 links + 1 stray
    duplicate of the 2023-01 file URL, deduplicated by URL)
  - 2023: https://www.safe.gov.cn/en/2021/0203/2180.html → `sdds_page_2023.html` (12 links)
  - 2022: https://www.safe.gov.cn/en/2021/0203/2053.html → `sdds_page_2022.html` (12 links)
  - 2021: https://www.safe.gov.cn/en/2021/0203/1935.html → `sdds_page_2021.html` (12 links)
  - 2020: https://www.safe.gov.cn/en/2020/0228/1743.html → `sdds_page_2020.html` (13 links — the
    extra is a second, corrected 2020-10 vintage; see frictions)
  - 2019: https://www.safe.gov.cn/en/2018/0517/1494.html → `sdds_page_2019.html` (12 links)
  - 2018: https://www.safe.gov.cn/en/2018/0517/1432.html → `sdds_page_2018.html` (12 links)
- SOURCE: SAFE 2015.06–2017.12 sub-channel (31 monthly article pages, each with one .xls link):
  https://www.safe.gov.cn/en/DataTemplateonInternational/index.html and
  .../index_2.html → `sdds_channel_2015_2017_index.html`, `sdds_channel_2015_2017_index_2.html`;
  the 31 article pages retained as `artpage_en_*.html` (URLs itemized in `_RDTD_fetch_log.txt`).

## SOURCE lines — the 133 template data files

- 133 file URLs (102 direct year-page links + 31 article-page links) under
  `https://www.safe.gov.cn/en/file/file/...` — every URL, HTTP status, and byte size is itemized in
  `_RDTD_fetch_log.txt`; files retained as `raw_NNN_<hash>.xls(x)`. All HTTP 200. One transient
  failure (the 2023-12 file, HTTP 000 timeout) succeeded on immediate retry (logged).
- 133 files → **132 unique data months, 2015-06..2026-05, no gaps**. The one month with two files is
  **2020-10** (publisher republication; both vintages retained, later one used — see manifest).
  `sample_202605.xls` is an early manual fetch of the same URL as `raw_004_*` (identical values).

## Structure (read from the files, not assumed)

- Sheet 表一(Section I): Section I.A "Official reserve assets" with lines (1) FX reserves,
  (1)(a) securities + of-which issuer-HQ sub-line, (1)(b) currency-and-deposits with (i) other
  national central banks/BIS/IMF, (ii) banks HQ in reporting country + of-which located-abroad,
  (iii) banks HQ outside + of-which located-in-reporting-country, (2) IMF reserve position,
  (3) SDRs, (4) gold + volume, (5) other reserve assets with derivatives/loans/other sub-lines;
  Section I.B other foreign currency assets. Values in 亿美元 (100 million USD); an 亿SDR column
  appears from 2016-04 (publisher note inside the files).
- Parsed to `build/reserve/rdtd_sdds_series.csv` (USD bn = 亿/10). Line-population map, blank/zero
  spans, publisher frictions, and reconciliation stats: `build/reserve/rdtd_sdds_manifest.json`.

## Reconciliation (same publisher, committed artifacts read-only)

- vs `build/reserve/rdtc_safe_totals.csv` (54 overlap months, 2021-12..2026-05): max |diff| =
  **0.000 bn** on total official reserve assets, IMF position, SDRs, gold, other reserve assets.
- Template internal identities: securities + deposits vs the FX-reserves line max |diff|
  **0.001 bn**; deposit components vs deposits total **0.001 bn**; component sum vs line A
  **0.002 bn** (publisher rounding).
