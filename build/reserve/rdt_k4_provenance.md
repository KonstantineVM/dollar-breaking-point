# RDT k4 provenance — RMB/alternative-adoption + k1-China bounding inputs

Built 2026-07-01/02 (UTC; fetches straddle midnight — exact timestamps in
`build/reserve/rdt_evidence/rmb/_RDT_fetch_log.txt`, append-only).
Scope per RDT_prediction.md: k4 quantitative sub-coordinate = CNY share of disclosed
reserves (LMW); swap lines and CIPS are FLAGS (context, not composite inputs); COFER
world aggregate enters ONLY as the k1-China residual-route bounding input; SAFE
disclosure anchors the k1-China origin. No estimation was performed in this stage;
all outputs are grounded data rows.

---

## 1. PBoC bilateral local-currency swap lines — GROUNDED, PRIMARY

SOURCE: PBOC, *RMB Internationalization Report (2025)* (English PDF), Part Eight
chronology ("Highlights of RMB Internationalization") and Part Six regional
statements.
URL: https://www.pbc.gov.cn/en/3688241/3688636/3828468/5624529/2025123116494089198/2025123116480428858.pdf
(landing page: https://www.pbc.gov.cn/en/3688241/3688636/3828468/5624529/2025123116494089198/index.html)
Fetched: 2026-07-01. Raw retained: `rdt_evidence/rmb/pbc_rmb_internationalization_report_2025_EN.pdf`
(2,000,840 bytes) + extracted text `pbc_rmb2025_extracted.txt`.
Chronology events were mapped to their year headers programmatically (17 year markers
found in the extracted text); the year assignments below were verified that way, not
recalled.

Verbatim (chronology; spacing artifacts of extraction cleaned):
- **Russia** — 2014: "On October 13, the PBOC and the Central Bank of Russian
  Federation signed a bilateral local currency swap agreement of RMB 150 billion
  yuan/RUB 815 billion." Renewed 2017-11-22 (RMB 150bn/RUB 1,325bn, validity 3 years)
  and 2020-11-23 (RMB 150bn/RUB 1.75 trillion). → year_signed 2014, size 150 bn CNY.
- **Turkey** — 2012: "On February 21, the PBOC and the Central Bank of the Republic
  of Turkey signed a bilateral currency swap agreement of RMB 10 billion/TRY 3
  billion." Renewed 2015-09-26 (RMB 12bn/TRY 5bn), 2019-05-30 (RMB 12bn/TRY 10.9bn);
  amended 2021-06-04 "to expand the swap scale to RMB 35 billion/TRY 46 billion."
  → year_signed 2012, current size 35 bn CNY.
- **Saudi Arabia** — 2023: "On November 20, the PBOC and the Saudi Arabian Monetary
  Authority (SAMA) signed a bilateral local currency swap agreement of RMB 50 billion
  yuan/SAR 26 billion." → year_signed 2023, size 50 bn CNY.
- **Poland** — **NO SWAP LINE** (a value, not a gap). The report's Europe statement:
  the PBOC "has signed bilateral local currency swap agreements with the central banks
  of six countries — the UK, Switzerland, Russia, Hungary, Türkiye, and Iceland — as
  well as with the ECB, with a total size of RMB 1.08 trillion yuan." Poland appears
  in the report only via the 2016 approval to issue RMB-denominated bonds (PBOC
  General Administration Department Letter [2016] No.378).
- **India** — **NO SWAP LINE** (a value, not a gap). Zero mentions of India anywhere
  in the report; absent from every regional swap enumeration (Europe above; Middle
  East: "5 Middle Eastern countries, including Saudi Arabia, the UAE, Qatar, Türkiye,
  and Egypt, with a total amount of RMB 173 billion yuan"; Africa: South Africa,
  Egypt, Nigeria, Mauritius; Latin America: Brazil, Argentina, Chile).

Caveat stated: "no swap line" is grounded as absence from the PBoC's own 2025 report
(coverage through end-2024/mid-2025). It is publisher-primary absence, not a signed
denial.

## 2. CIPS participation — aggregates GROUNDED-PRIMARY; per-country NOT-AVAILABLE

SOURCE (aggregate): CIPS Participants Announcement No. 117,
https://www.cips.com.cn/en/2026-04/09/article_2026040916303626713.html, fetched
2026-07-01. Raw retained: `cips_announcement_117.html` (+ Chinese counterpart).
Verbatim: "As of March 2026, CIPS has 194 Direct Participants and 1597 Indirect
Participants. Among Indirect Participants, 1165 participants are from Asia (including
564 from Chinese Mainland), 266 from Europe, 73 from Africa, 35 from North America,
33 from South America, and 25 from Oceania. CIPS participants are located in 126
countries and regions around the world."

SOURCE (regional, end-2024): PBOC RMB Internationalization Report 2025 (above):
Europe "290 participating banking institutions, including 29 direct participants and
261 indirect participants"; Middle East "68 Middle Eastern institutions ... 12 direct
participants and 56 indirect participants"; ASEAN 22 direct + 128 indirect. System:
"As of the end of June 2025, the CIPS had 176 direct participants and 1,514 indirect
participants, with 64% of participants located overseas."

Per-country counts for Russia, India, Turkey, Saudi Arabia, Poland:
**NOT-AVAILABLE from the publisher.** Tried (all retained + logged): EN announcement
index and No. 117; CN announcement index (14 pages, paginated
`/cips/ywfw/cyzgg/ae9dcb25-N.html`), No. 117, No. 116, No. 110, No. 72 (Dec-2021),
No. 44 (Jul-2019). The currently-published versions carry only system totals and
continental splits; the historical per-country participant tables are stripped from
the re-published (2023 article-ID) pages and no PDF/XLS attachments exist.

## 3. LMW CNY/USD shares — from disk, read-only

SOURCE: `build/reserve/rd0_evidence/lmw_Data.xls`, sheet `DATA`, pandas engine
`xlrd`, read 2026-07-01. (Panel provenance is RD0's; file not modified.)
Columns: country, year, USD, EUR, JPY, CAD, CNY, GBP, AUD, Other (shares, %).
- Russia: 2007–2021 (15 obs). USD 47.00 (2007) → 13.89 (2021); CNY 0 through 2016,
  3.38 (2017), 17.34 (2018), 15.28 (2019), 16.69 (2020), 21.78 (2021). Matches the
  RD1-replicated values cited in RDT_prediction.md.
- Turkey: 2004–2023 (20 obs). CNY = 0.0 in every year; USD 39.33 (2004) … 52.00 (2023).
- Poland: 2004–2022 (19 obs). CNY = 0.0 in every year; USD 50.00 (2004) … 41.00 (2022).
- **India: ABSENT from the panel** (substring scan of the country column, no match).
- **Saudi Arabia: ABSENT from the panel** (no match). China also absent.
Presence/absence reported as found; absence is the expected pattern in the
coordinate-applicability matrix and is now verified, not assumed.

## 4. SAFE anchor (k1-China origin) — GROUNDED, PRIMARY, quoted

SOURCE: SAFE, *Annual Report of the State Administration of Foreign Exchange (2018)*
(国家外汇管理局年报（2018）), published 2019-07-28. Box 4 (专栏4)
"中国外汇储备投资情况概览" (Overview of China's foreign exchange reserve
investment), printed page 35 (PDF page 44 of 159).
URL: https://www.safe.gov.cn/safe/file/file/20190728/108d3e1d09ac4d52b99685e6aaa9c222.pdf
Fetched: 2026-07-02. Raw retained: `safe_annual_report_2018_CN.pdf` (5,489,161 bytes).

Verbatim (Chinese, from the PDF text layer):
> "外汇储备货币结构日益分散，比全球平均水平更为多元。"
> [chart 我国外汇储备货币结构] 1995年: 美元 79% / 非美元 21%；2014年: 美元 58% / 非美元 42%。
> [chart 全球外汇储备货币结构] 1995年: 美元 59% / 非美元 41%；2014年: 美元 65% / 非美元 35%。
> 注："全球外汇储备货币结构根据国际货币基金组织（IMF）公布的官方外汇储备货币构成（COFER）计算…"

Translation: "The currency structure of the FX reserves has become increasingly
diversified, more diversified than the global average." China's FX reserve currency
structure: 1995: USD 79% / non-USD 21%; 2014: USD 58% / non-USD 42%. Global (per IMF
COFER, per the box's own note): 1995: USD 59%; 2014: USD 65%.

Extraction method: PyMuPDF positioned-word extraction (the four pie charts interleave
in the raw text layer). Pairing verified from coordinates: in each chart the USD label
sits on the same side; the global chart's values (59% in 1995, 65% in 2014) match the
independent COFER USD-of-allocated series, fixing the China values as USD 79% (1995)
and USD 58% (2014). **Disclosed points: China USD share 79% (1995), 58% (2014).**
This is the one-off disclosure; no later SAFE annual report figure was claimed or used.

## 5. COFER public world aggregate — GROUNDED, PRIMARY (with methodology break)

SOURCE (data): IMF, COFER dataset via the IMF data portal SDMX 2.1 API,
https://api.imf.org/external/sdmx/2.1/data/IMF.STA,COFER/?startPeriod=2014
(structure: /datastructure/IMF.STA/DSD_COFER; codelist CL_COFER_INDICATOR).
Fetched 2026-07-01. Raw retained: `cofer_data_all_2014on.xml`, `cofer_dsd.xml`,
`codelist_CL_COFER_INDICATOR.xml`.
Series used (World = COUNTRY G001): AFXRA / CI_USD / SHRO_PT / Q (USD share of
allocated, %); AFXRA / CI_T / NV_USD / Q (allocated total; OBS_VALUE in USD,
converted /1e9 to $bn — unit fixed after cross-checking magnitudes; an earlier CSV
vintage mislabeled /1e3 values as bn).
Output: `build/reserve/rdt_k4_cofer.csv`, 49 quarters 2014-Q1 → 2026-Q1.
Endpoints: 2014-Q1 USD 61.32% of $11,852.9bn; **2026-Q1 USD 57.13% of $13,104.9bn**.

METHODOLOGY BREAK (grounded, must travel with any residual-route use):
SOURCE: https://data.imf.org/en/datasets/IMF.STA:COFER (fetched 2026-07-01):
> "Starting in 2025Q3, with revisions back to 2000Q1, the IMF eliminated the
> 'unallocated' portion of the COFER dataset to provide a complete currency
> composition—expressed in both dollars and shares—that accounts for 100 percent of
> the world's foreign exchange reserves. Also starting with 2025Q3, the IMF publishes
> the share of total reserves that have been imputed."
Confirmed in the fetched data: UFXRA (unallocated) = 0 for all quarters; AFXRA = TFXRA;
TFXRA_IMP (share imputed by IMF staff) = 10.65% at 2026-Q1. Technical note retained:
IMF TNM/2025/14, "Improving the Analytical Usefulness of the IMF's COFER Data"
(https://www.imf.org/-/media/files/publications/tnm/2025/english/tnmea2025014.pdf).
Consequence for the pre-registered residual route: W_t is now a 100%-coverage,
partially-imputed share (not a discloser-only share); the k1-China residual bound must
carry this imputation caveat explicitly.

CHINA-INCLUSION GROUNDING:
- GROUNDED: "China" appears as a distinct entry on the IMF's published **List of
  COFER Reporters** (alongside separate "Hong Kong SAR" and "Macao SAR" entries).
  SOURCE: https://data.imf.org/en/Datasets/COFER/List-of-Reporters, fetched
  2026-07-01, raw retained. India and Poland also appear; **Russia, Saudi Arabia and
  Turkey do not appear** on the disclosed list (the IMF states reporter names are
  confidential unless consent is given — non-appearance ≠ non-reporting).
- GROUNDED: RMB separately identified in COFER from the 2016Q4 survey (published
  2017-03-31). SOURCES: IMF PR 17/108 (retained `imf_pr17108.html`); TNM/2025/14:
  "The IMF separately identified the renminbi in its official foreign exchange
  reserves database starting October 1, 2016. The change was reflected in the survey
  for the fourth quarter of 2016 that was published at the end of March 2017."
- **UNVERIFIED**: the widely-repeated claim that China began reporting to COFER
  partially in 2015 and phased in over ~2–3 years was NOT found on any current IMF
  page fetched (dataset page, FAQ, List-of-Reporters, PR 17/108, PR 15/690 search,
  TNM/2025/14, BOPCOM 24-09). Recorded UNVERIFIED; not asserted from memory. The
  residual route needs only current inclusion (grounded above) plus the imputation
  caveat.

Conflict handling (per RDT_prediction.md): the COFER aggregate is used ONLY as the
k1-China bounding input — never as country-level evidence, never as a freeze-response
observation.

## NOT-AVAILABLE / UNVERIFIED register

1. CIPS per-country direct/indirect counts (Russia, India, Turkey, Saudi Arabia,
   Poland): NOT-AVAILABLE from cips.com.cn current site version (tries logged).
2. IMF statement on China's 2015 partial/phased COFER entry: UNVERIFIED on current
   IMF pages (China's present inclusion IS grounded via the reporter list).
3. India / Saudi Arabia in the LMW panel: ABSENT (verified value, not a gap).
4. Poland / India PBoC swap line: NO-SWAP-LINE (grounded publisher-primary absence,
   PBoC 2025 report).

## Files

- `build/reserve/rdt_k4_rmb.csv` — 142 rows, long format.
- `build/reserve/rdt_k4_cofer.csv` — 49 quarters, 2014-Q1 → 2026-Q1.
- `build/reserve/rdt_k4_manifest.json`
- `build/reserve/rdt_evidence/rmb/` — 35 raw files + `_RDT_fetch_log.txt`.
