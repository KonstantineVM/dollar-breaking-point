# RDT-G Phase 0b — DENOMINATORS provenance

Grounded 2026-07-02 (UTC). Governing pre-registration: `build/reserve/RDTG_prediction.md`
(commit 7ad70d2), read first. This phase supplies ONLY the magnitude-bar denominators:
(1) candidate-market outstandings in local currency, (2) COFER end-2021 raw currency
shares, (3) a single-source end-2021 FX set. Per the pre-registered sequencing rule,
no discriminator series (SAFE SDDS template contents; destination-country holdings /
b.o.p.-by-counterpart / nonresident-share series) was read, fetched, or opened.
Machine-readable contract: `build/reserve/RDTG_denominators.json`. All retained
fetches: `build/reserve/rdtg_evidence/denom_*`.

---

## 1. Market outstandings (local currency, end-2021 stock or nearest, stated)

### JGB (Japan, JPY) — GROUNDED-PRIMARY
- **Figure:** General Bonds (普通国債) outstanding, end-December 2021 = **9,681,121
  hundred million yen** (¥968,112.1 bn ≈ ¥968.1 trillion).
- SOURCE: MoF Japan, "Central Government Debt (End of June 2021 - present)",
  https://www.mof.go.jp/english/policy/jgbs/reference/gbb/suii.xls (landing:
  .../gbb/index.htm), fetched 2026-07-02. Retained:
  `denom_jp_mof_cgd_timeseries_suii.xls`.
- Quoted cell: sheet `suii`, row "普　通　国　債\n General Bonds", column
  "R3.12末\n2021 December" = 9681121; unit cell "（単位：億円）（Unit: 100 million yen）".
- Friction: the original quarterly release page `e202112.html` returns **404**
  (retained: `denom_jp_mof_cgd_202112_404.html`) — the MoF site was restructured and
  older quarters are served through the current time-series file (last saved
  2026-04-21). Context row: total 内国債 Government Bonds (incl. FILP etc.)
  end-Dec-2021 = 10,886,083 億円. No holder breakdown exists in this file.
- Confidence: **HIGH** (publisher-primary, exact labeled cell + unit).

### Bund (Germany, EUR) — GROUNDED-PRIMARY
- **Figure:** Outstanding volume of Federal securities at 2021-12-31 =
  **EUR 1,589,900,000,000** (€1,589.9 bn), *including own holdings*; the same sheet's
  "Own holdings" line at 2021-12-31 = **−EUR 162,662,257,456** (free float ≈ €1,427.2 bn).
- SOURCE: Deutsche Finanzagentur, debt-statistics report workbook,
  https://www.deutsche-finanzagentur.de/fileadmin/user_upload/Institutionelle-investoren/berichtswesen/schuldenbericht_en.xlsx
  (landing: /en/federal-funding/debt-statistics/outstanding-volumes), fetched
  2026-07-02. Retained: `denom_de_finanzagentur_schuldenbericht_en.xlsx`,
  `denom_de_finanzagentur_outstanding_volumes.html`.
- Quoted cells: sheet `rpgOutstanding` (header: "Outstanding Volume & Own Holdings of
  Federal Securities"), rows "Outstanding volume" / "Own holdings", column 2021-12-31.
  Cross-check within the same workbook: sheet `rpgDebt` "Federal securities" (debt-level
  basis) 2021-12-31 = 1,428,234,179,933 — consistent with outstanding minus own holdings.
- Friction: continuously regenerated workbook (report stamp 2026-06-03); own holdings
  are ~10% of outstanding — the bars step must state which basis it divides by. No
  investor-structure (nonresident) sheet exists in this workbook.
- Confidence: **HIGH**.

### OAT (France, EUR) — GROUNDED-ALTERNATE-OFFICIAL (AFT primary unreachable)
- **Figure:** Negotiable central government debt outstanding, total, end-December 2021
  = **EUR 2,145,121 million** (€2,145.121 bn).
- SOURCE: INSEE BDM SDMX, series IDBANK **001739081**, TITLE_EN "Negotiable central
  government debt outstanding amount - Total", UNIT_MEASURE=EUROS, UNIT_MULT=6;
  https://www.bdm.insee.fr/series/sdmx/data/SERIES_BDM/001739081?startPeriod=2021-10&endPeriod=2022-01
  fetched 2026-07-02. Retained: `denom_fr_insee_bdm_001739081.xml`. Quoted:
  `TIME_PERIOD="2021-12" OBS_VALUE="2145121"` (adjacent: 2021-11 = 2,151,245;
  2022-01 = 2,166,809).
- **Publisher friction (stated, not smoothed):** the tasked primary publisher
  aft.gouv.fr is behind a Cloudflare JS challenge from this egress: the January-2022
  monthly bulletin PDF and the bulletins index both return "Just a moment..." challenge
  pages (retained: `denom_fr_aft_bulletin_jan2022_cloudflare_challenge.html`,
  `denom_fr_aft_bulletins_index_cloudflare_challenge.html`); WebFetch returns 403 on
  aft.gouv.fr paths; budget.gouv.fr returns 403 (Incapsula). INSEE's catalogue lists
  this series under the grouping "Dette négociable de l'État Agence France Trésor"
  (visible in the INSEE catalogue listing), but the insee.fr series page is a JS app
  and the attribution line did not render server-side — recorded **UNVERIFIED-on-page**
  (page shells retained: `denom_fr_insee_serie_001739081.html`,
  `denom_fr_insee_series_group_102765717.html`).
- Consequence: under a strict publisher=AFT reading the gate may treat OAT as
  NOT-GROUNDED; the figure itself is grounded against an official-statistics endpoint.
- Confidence: **MEDIUM** (official figure, non-tasked publisher, attribution line not
  server-rendered).

### gilt (UK, GBP) — GROUNDED-PRIMARY
- **Figure:** "GILTS IN ISSUE ON 31 DECEMBER 2021 — Total Amount Outstanding
  (including inflation uplift for index-linked gilts) = **£2,113.64 billion nominal**."
- SOURCE: UK DMO report D1A generated with parameter COBDate=31/12/2021:
  https://www.dmo.gov.uk/umbraco/surface/PDFReport/GetDataExport?reportCode=D1A&parameters=%26COBDate%3D31%2F12%2F2021
  (landing: /data/gilt-market/gilts-in-issue/), fetched 2026-07-02. Retained:
  `denom_uk_dmo_D1A_gilts_in_issue_20211231.pdf` (grounding document, 6 pages),
  `denom_uk_dmo_D1A_gilts_in_issue_20211231.csv`, `denom_uk_dmo_gilts_in_issue_index.html`.
- Friction: the CSV export of the same report returns **only the conventional-gilt
  section** (58 bonds, no totals, no index-linked block) — the PDF export carries the
  full report and the quoted total. Report is generated on demand ("Data Date:
  02-Jul-2026") from the DMO's current database for the 31-Dec-2021 close.
- Sequencing note: the gilts-in-issue landing page contains a navigation **link** to
  "Government Holdings" pages; the link was not followed and no holdings content is on
  any retained page.
- Confidence: **HIGH**.

### AGS (Australia, AUD) — **NOT-GROUNDED** (permitted result; failure stated)
- No figure recorded. aofm.gov.au is unreachable from this egress, 2026-07-02:
  - WebFetch: **HTTP 503** on /data-hub (twice) and /securities;
  - curl HTTP/2: stream INTERNAL_ERROR; curl HTTP/1.1 (Chrome/Firefox/Safari UAs,
    30–60 s timeouts): **0 bytes, timeout** on www.aofm.gov.au/data-hub and on the
    apex-domain 301 target; robots.txt fetch also failed.
  - Archive fallback: a Wayback snapshot exists (20220106113229 of the AOFM homepage,
    availability API confirmed) but web.archive.org content is **blocked by the
    environment egress policy** (block response retained:
    `denom_au_aofm_wayback_fetch_blocked.txt`) and WebFetch cannot reach web.archive.org.
  - RBA statistical tables carry **no AGS-on-issue outstanding table**; the index lists
    only holdings-classified tables (A3.1/A3.2), which are discriminator-adjacent and
    were **not opened**.
- Nothing was substituted from memory. Per the pre-registration, the AGS market drops
  out of Scheme 1 with the drop stated by the bars step; Scheme 2's AUD-share mass hits
  a market with no grounded denominator and must be carried as a stated remainder or
  re-grounded (e.g. from a network position that can reach aofm.gov.au) before use.
- Confidence: **LOW** (absence of grounding, fully documented).

### GoC bonds (Canada, CAD) — GROUNDED-PRIMARY
- **Figure:** Marketable bonds payable in Canadian currency, end-December 2021 =
  **CAD 1,014,462 million** (C$1,014.462 bn).
- SOURCE: Statistics Canada table 10-10-0002-01 "Central government debt" (CANSIM
  191-0002), full-table CSV https://www150.statcan.gc.ca/n1/tbl/csv/10100002-eng.zip
  (landing: /t1/tbl1/en/tv.action?pid=1010000201), fetched 2026-07-02. Retained:
  `denom_ca_statcan_10100002.zip`. Cube note 1: "Source: Department of Finance Canada."
  (within the tasked publisher set: StatCan/Finance Canada).
- Quoted row: `"2021-12","Canada","2016A000011124","Marketable bonds payable in
  Canadian currency","Dollars","81","millions","6","v86822809","1.8","1014462"`.
- Friction: monthly data unaudited (note 2), retroactive revisions on methodology
  changes (note 3); FX-payable marketable bonds (15,859 CAD mn) excluded by the
  local-currency line's construction. No nonresident split exists in this table.
- Confidence: **HIGH**.

## 2. COFER end-2021 currency shares — GROUNDED-FROM-DISK (checked first, as tasked)

- **On-disk check:** `build/data/imf_cofer/` (marginal + shares XML, fetched
  2026-06-28) and `build/reserve/rdt_k4_cofer.csv` (USD share only) exist; the full
  multi-currency payload is the committed RDT-stage fetch
  **`build/reserve/rdt_evidence/rmb/cofer_data_all_2014on.xml`** (api.imf.org SDMX 2.1,
  dataset IMF.STA:COFER(7.0.1), fetched 2026-07-01; XML header PUBLICATION_DATE
  2026-03-27). Used directly; no new fetch needed. Original provenance:
  `build/reserve/rdt_k4_provenance.md` §5.
- **2021-Q4 shares of allocated reserves (COUNTRY=G001, INDICATOR=AFXRA,
  SHRO_PT, %),** extracted programmatically 2026-07-02:

  | currency | share % |
  |---|---|
  | USD | 59.4025 |
  | EUR | 19.8154 |
  | JPY | 5.5041 |
  | GBP | 4.8805 |
  | AUD | 2.0051 |
  | CAD | 2.4330 |
  | CHF | 0.1622 |
  | CNY | 2.8516 |
  | other (CI_OTHC) | 2.9456 |

  Sum = 100.00. Allocated total 2021-Q4 = USD 12,914.13 bn (NV_USD).
- **Vintage caveat (travels with any use):** post-2025Q3 COFER methodology —
  unallocated eliminated with revisions back to 2000Q1, missing values imputed by IMF
  staff (IMF TNM/2025/14, retained at the RDT stage). These are therefore the current
  IMF vintage of the end-2021 structure, 100%-coverage and partially imputed, not the
  contemporaneous 2022 release.
- Raw shares only are recorded here; the pre-registered non-USD CNY-excluded
  renormalization is computed later by the bars step.
- Confidence: **HIGH**.

## 3. FX conversion set — GROUNDED-PRIMARY (single source)

- **On-disk check first:** no committed end-2021 FX artifact exists in `build/data`
  or `build/contracts` (searched 2026-07-02), so the set was fetched.
- SOURCE: Federal Reserve Board, **H.10 Foreign Exchange Rates**, weekly release,
  Release Date: January 3, 2022, https://www.federalreserve.gov/releases/h10/20220103/,
  fetched 2026-07-02. Retained: `denom_fx_fed_h10_20220103.html`.
- **Rate date: 2021-12-30** — the release's "Dec. 31" column is **ND** (no data) for
  all currencies, so Dec 30, 2021 is the last certified 2021 observation and is the
  end-2021 rate set (stated, not smoothed).
- Rates (publisher's own quotation conventions, one page):
  USD per EUR **1.1318** · USD per GBP **1.3500** · USD per AUD **0.7260** ·
  JPY per USD **115.17** · CAD per USD **1.2777** · CHF per USD **0.9146**.
- Confidence: **HIGH**.

## Sequencing attestation (the git-order gate check)

**No discriminator series was read, fetched, or opened in this task.** Specifically:
no SAFE SDDS template contents (Part 1 corpus untouched); no Japan/euro-area/UK/Canada
b.o.p.-by-counterpart or portfolio-liability series; no Bund investor structure, JGB
foreign-share, gilt overseas-holdings, OAT nonresident-share, or AGS nonresident-share
series (Part 2 legs untouched). Co-presence register — pages retained where
discriminator material was adjacent but **not extracted**:
1. DMO gilts-in-issue index page links to "Government Holdings" — link not followed.
2. RBA tables index (scratchpad probe) listed holdings-table **titles**
   (A3.1/A3.2) — files not opened.
3. AOFM search snippets mentioned "AGS investor base" / "Investor Chart Pack" — never
   opened (site unreachable regardless).
4. None of the retained denominator documents (MoF suii.xls, Finanzagentur workbook,
   INSEE BDM series, DMO D1A report, StatCan 10-10-0002-01, H.10, COFER world XML)
   contains a nonresident-holdings column for any candidate market.
COFER shares are a pre-registered Scheme-2 denominator input, not a discriminator.
`RDTG_prediction.md` was read first as tasked; `rdt_k4_provenance.md` was read only to
locate the committed COFER artifact.

## Files written by this task

- `build/reserve/RDTG_denominators.json`
- `build/reserve/RDTG_denominators_provenance.md` (this file)
- `build/reserve/rdtg_evidence/denom_*` — 16 retained files (fetches + failure
  evidence), listed per market above.
