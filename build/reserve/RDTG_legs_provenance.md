# RDT-G Part 2 — RECEIVING-LEGS provenance

Grounded 2026-07-02 (UTC). Governing pre-registration: `build/reserve/RDTG_prediction.md`
(commit 7ad70d2), **read first**. Bars were committed before this pass (8dee169); this task
only GROUNDS and FETCHES the nine legs plus the M1 citation — every test, power check and
verdict belongs to the later assembly. Machine-readable contract:
`build/reserve/RDTG_legs_manifest.json`. All retained fetches:
`build/reserve/rdtg_evidence/leg_*` (58 files). Proxy discipline held throughout: retries
with backoff, alternate OFFICIAL channels only, TLS never disabled, failure evidence retained.

Windows per the pre-registration: baseline calendar 2015→2021, verdict calendar 2022→2025,
nearest published boundary per leg, stated per leg below. Local-currency rule: nominal/local
preferred; deviations (market value, %, USD) stated per leg.

---

## China-attributed candidates (reported separately per the pre-registration)

### (a) Japan — b.o.p. vis-à-vis China, portfolio investment liabilities — **GROUNDED-PRIMARY**
- SOURCE: BoJ/MoF BOP-related statistics. The BoJ statistics page lists, verbatim:
  "Portfolio Investment Liabilities, Country Breakdown: transactions broken down by economy
  of transactor (for 45 economies)" (monthly) and quarterly "Regional BOP: Major components
  of the BOP broken down by economy of the counterparty."
  https://www.boj.or.jp/en/statistics/br/bop_06/index.htm, checked 2026-07-02.
- Raw series retained (BoJ Time-Series Data Search flat files, checked 2026-07-02):
  - `leg_a_boj_regbp_q_en.zip` — quarterly regional BOP; rows `BPBP6QFLCN2`
    ("Financial account/Portfolio investment/P.R. China/Net(Liabilities)"), `BPBP6QFLCN21`
    (equity), `BPBP6QFLCN22` (debt securities); unit "100 million Yen"; observed span
    **2014Q1→2025Q4**.
  - `leg_a_boj_bp_m_en.zip` — monthly BOP; rows `BPPI6E1N9CN` etc. ("Portfolio Investment
    Liabilities/Total/P.R. China/Net" plus equity/long-term/short-term splits and gross
    acquisition/disposition); observed span **2014-01→2026-04**.
- Local currency: yes (JPY, nominal transaction values; "Transactions in principle are
  valued at their transaction price" — BoJ BPM6 explanation, retained).
- **Compiler's own custody caveat, verbatim** (BoJ FAQ on BOP-related statistics, Q10,
  retained `leg_a_boj_faqbpsm6.html`):
  > "Transactions under portfolio investment liabilities (i.e., transactions in securities
  > issued by Japanese residents) are classified according to the economy of the transactor.
  > Specifically, when a nonresident investor trades Japanese securities via a foreign
  > securities firm, the economy of the firm -- not of the investor -- is regarded as the
  > economy of the transactor. In addition, when Japanese securities are redeemed via a
  > foreign custodian, the economy of the custodian is reflected in the data."
- Windows: baseline 2015Q1→2021Q4 exact; verdict 2022Q1→2025Q4 exact.
- Friction: MoF's own English "Regional BOP (historical data)" page (ebparea.htm, retained)
  publishes only current-account detail plus a financial-account NET by area (6a-20.csv,
  retained) — the liabilities country detail lives on the BoJ stat-search channel, which the
  MoF portfolio page itself points to ("Other data is available on BOJ Time-Series Data
  Search", retained `leg_a_mof_ebppi_index.html`).

### (b) Euro area — b.o.p./i.i.p. by counterpart, China, portfolio liabilities — **GROUNDED-PRIMARY** (position only; flows structurally absent)
- SOURCE: ECB Data Portal dataset BP6, checked 2026-07-02. A serieskeysonly wildcard over
  all euro-area series with COUNTERPART_AREA=CN, ACCOUNTING_ENTRY=L, FUNCTIONAL_CAT=P
  returns **exactly one series** (probe retained `leg_b_ecb_bp6_cn_liab_serieskeys_probe.xml`):
  `BP6.Q.N.I8.CN.S1.S1.LE.L.FA.P.F._Z.EUR._T.M.N` — "Euro area 19 (fixed composition) ...
  vis-a-vis China ... Closing balance sheet/Positions/Stocks ... Portfolio Investment ...
  Market value". Raw series retained (`leg_b_ecb_bp6_ea19_cn_pi_liab_position.csv`):
  quarterly, EUR millions, **2008Q1→2022Q3**, every observation flagged **E (estimated)**.
- Eurostat cross-check (BOP_EU6_Q, probes retained): partner CN_X_HK portfolio LIAB at
  euro-area level returns **0 observations** in every variant (LIAB/NET/NI/NO) while the
  same item's ASSETS side returns 130 observations and other-investment has both sides —
  the China-attributed portfolio-liabilities FLOW cell is absent **by construction**.
- Local currency: EUR, but **market value**, not nominal (stated per the local-currency rule).
- **Compiler's own caveat, verbatim** (ECB b.o.p./i.i.p. quality report, June 2024,
  footnote 8, retained `leg_b_ecb_bopips202406_quality_report.pdf`):
  > "Portfolio investment liabilities within the euro area (broken down by resident sector)
  > are estimated residually by deducting the euro area holdings of residents from the total
  > securities issued by euro area residents. This method is used to circumvent the
  > difficulty in identifying the residency of end holders of securities issued by euro
  > area residents."
- Windows: baseline 2014Q4→2021Q4 exact; verdict **truncated to 2021Q4→2022Q3** (nearest
  published boundary 2022Q3 — the series stops there in the current portal; observed end,
  stated). No instrument split, no flows, EA19 fixed composition.

### (c) UK — Pink Book geographic detail, China portfolio liabilities — **GROUNDED-PRIMARY**
- SOURCE: ONS Pink Book dataset 10 "Geographical breakdown of the UK international
  investment position", https://www.ons.gov.uk/economy/nationalaccounts/balanceofpayments/datasets/10geographicalbreakdownoftheukinternationalinvestmentpositionthepinkbook2016,
  checked 2026-07-02. Table **10.1** carries the row "China" × column "Portfolio investment
  liabilities" (GBP billion, balance-sheet positions) — but each edition publishes **one
  reference year** (table 10.1 lags one year; PB2025 title: "...valued at end of year
  [note1] 2023").
- Raw series retained: **all ten editions PB2016→PB2025**
  (`leg_c_ons_pinkbook2016..2025_chapter10.*`), giving the stitchable annual span
  **end-2014→end-2023**. Parse check performed (values read, not analyzed): end-2015 8.9,
  end-2016 11.2, end-2017 12.3, end-2018 12.1, end-2019 13.6, end-2020 16, end-2021 18.6,
  end-2022 25.5, end-2023 27.2 (GBP bn); the end-2014 cell in PB2016 may be "-" (nil/<£1m
  symbol) — the assembly parses it. Mixed-vintage friction stated (each year from a
  different edition; latest year provisional per ONS notes, retained in-workbook).
- Local currency: yes (GBP), market-value positions. No debt/equity split on the country
  row; table 10.3 total-liabilities China (CDID HFNE, 1999→2024) retained in the same
  workbooks as context.
- **Compiler's own attribution statement, verbatim** (Pink Book 2014, Part 3, retained
  `leg_c_ons_pinkbook2014_part3_geographical.html`):
  > "Portfolio investment liabilities are derived from the Co-ordinated Portfolio
  > Investment Survey (CPIS) returns of other countries reporting assets held in the UK..."
  No ONS sentence using the word "custody" was found in the retained text — the CPIS-mirror
  construction is the compiler's stated basis and imports the counterpart compilers'
  custody bias. Stated, not smoothed.
- Windows: baseline end-2015→end-2021; verdict end-2021→**end-2023** (nearest published
  boundary; PB2025's 10.1 lags one year).

### (d) Canada — by-country international securities transactions, China — **NOT-AVAILABLE**
- The distinction, stated: **absence by construction, not a fetch failure.** StatCan's
  international-securities geographic tables exist and were fetched, but their finest
  geography is {United States, United Kingdom, Other EU, Japan, Other OECD, All other
  countries} — **no China line** (cube metadata retained for flows 36-10-0030 and positions
  36-10-0486; the tasked example 36-10-0473 has a China line but is DIRECT investment, not
  securities — its metadata retained as evidence of the check).
- SOURCE: StatCan WDS getCubeMetadata (productIds 36100030, 36100486, 36100473) and
  full-table CSV https://www150.statcan.gc.ca/n1/tbl/csv/36100030-eng.zip, checked
  2026-07-02; retained `leg_d_statcan_36100030_its_by_geography.zip` (monthly, 1988-01→
  2026-04, CAD, net flows/sales/purchases by instrument × 6 regions — China sits inside the
  "All other countries" residual only).
- **Compiler's own collection-basis statement, verbatim** (IMDB 1535, retained
  `leg_d_statcan_imdb1535_methodology.html`):
  > "In general, it is much more practical to collect these data from the intermediaries
  > who act as brokers or agents for those trading securities, rather than trying to collect
  > the data from the transactors themselves who are ultimately buying or selling the
  > securities."
  No sentence using "custodian" found in the retained text; stated.
- Windows: both windows fully covered by the aggregate table; the China line is
  NOT-AVAILABLE for both.

## Aggregate candidates

### (e) Bund — nonresident/official investor structure — **GROUNDED-PRIMARY**
- SOURCE: Deutsche Finanzagentur, "Investor Structure",
  https://www.deutsche-finanzagentur.de/en/federal-funding/government-as-issuer/investor-structure,
  checked 2026-07-02, retained `leg_e_finanzagentur_investor_structure.html`. The page IS
  the data: "Share of German Government Securities held by their total Volume by Investor
  Group" at 2020-12-31, 2021-12-31, 2022-12-31, 2023-12-31, 2024-12-31, 2025-06-30 —
  including the OFFICIAL third-country line "Central banks and government sector — third
  countries" (17% at 2021-12-31 → 14% at 2025-06-30 as published) and
  "Other investors — third countries".
- Units: % shares of total volume (not local-currency amounts; the same publisher's
  outstanding-volumes workbook, grounded at the denominators pass, is the EUR denominator).
- **Compiler's own caveat, verbatim** (same page):
  > "German Government securities are bearer bonds that are traded daily and a change of
  > ownership is therefore possible at any time. It is not recorded which person or
  > institution the current owner is. However, the investor structure of the Federal
  > government can be estimated from various sources of information."
  Plus the page's model note: "2024 revised model with retrospective new estimates;
  Differences up to 100% are possible due to rounding" — a methodology-revision friction.
- Corroborating custody-channel statement (Bundesbank Monthly Report July 2018, retained
  `leg_e_bundesbank_mr2018-07_holder_structure.pdf`):
  > "It seems most investors from non-euro area countries also trade German government
  > securities via their own branches or authorised financial institutions within the euro
  > area and accordingly hold the securities in safe custody at resident reporting
  > custodians."
- Windows: **baseline support is 2020-12-31→2021-12-31 only** (earlier baseline years are
  not on the current page; one annual change — power decided by the assembly); verdict
  2021-12-31→2025-06-30 (nearest published boundary 2025-06-30).

### (f) JGB — foreign-holdings share (BoJ flow of funds) — **GROUNDED-PRIMARY**
- SOURCE: BoJ Flow of Funds (2008 SNA), stat-search flat file fof2_en.zip, checked
  2026-07-02, retained `leg_f_boj_fof2_en.zip` (quarterly + fiscal-year CSVs). Rows:
  `FOF_FFAS500A311` (Overseas holdings of central government securities and FILP bonds,
  stock), `FOF_FFAS500A310` (T-bills), flow/reconciliation variants, and the
  from-whom-to-whom row `FOF_FFALC08G500` (Holder: Overseas × Issuer: Central government
  and Fiscal Loan Fund). Observed span **1997Q4→2026Q1**.
- Unit verified from the publisher's own release workbook (retained
  `leg_f_boj_sjpre_units.xlsx`): "(100 million yen)". Local currency: yes. The share's
  numerator and denominator (all-sector totals) are both inside the retained file; the
  share itself is computed by the assembly.
- **Compiler's own perimeter statement, verbatim** (Guide to Japan's Flow of Funds
  Accounts, retained `leg_f_boj_exsj01_fof_guide.pdf`):
  > "overseas sector in the FFA is defined as 'non-residents' in the BOP, and the financial
  > surplus or deficit of the 'overseas' sector is made to equal the sum of the 'current
  > account' and 'capital account' in the BOP."
  The FFA Overseas sector therefore inherits the same compiler's custodian-attribution
  caveat quoted verbatim under leg (a).
- Windows: baseline 2015Q1→2021Q4 exact; verdict 2022Q1→2025Q4 exact (published to 2026Q1).

### (g) gilts — overseas holdings — **GROUNDED-PRIMARY**
- SOURCE: ONS time series **HEWD** "BoP: IIP: Liabs: Overseas holdings of BGS: total: CP
  NSA: £m", dataset UKEA,
  https://www.ons.gov.uk/economy/nationalaccounts/balanceofpayments/timeseries/hewd/ukea,
  checked 2026-07-02. Raw series retained (CSV + JSON):
  `leg_g_ons_hewd_ukea_overseas_gilt_holdings.csv/.json` — quarterly **1966Q4→2026Q1**,
  GBP million, current prices (market value), NSA. Local currency: yes.
- Corroboration: DMO Quarterly Review Jan–Mar 2026 (retained
  `leg_g_dmo_quarterly_review_jan_mar_2026.pdf`) republishes the same figures — "Gilt
  holdings (£mn, market values) ... Overseas ... Q4 2025 737,355 ... Source: ONS" — and
  HEWD 2025Q4 = 737,355. Identity confirmed on the publishers' own documents.
- Caveat: the DMO table's own footnote "Source: ONS. These figures can be revised
  retrospectively." No custody-specific caveat found in the retained ONS text for HEWD;
  the ONS CPIS-mirror statement retained under leg (c) is the same compiler's
  liabilities-attribution basis. Stated. No official-sector split; no conventional/IL split.
- Windows: baseline 2015Q1→2021Q4 exact; verdict 2022Q1→2025Q4 exact (published to 2026Q1).

### (h) OAT — nonresident share — **NOT-AVAILABLE** (exists but not fetchable; the distinction stated)
- Tasked primary (AFT, aft.gouv.fr): **Cloudflare JS challenge from this egress** — HTTP 403
  "Just a moment..." on 3 attempts with backoff at
  https://www.aft.gouv.fr/en/oat-holders, 2026-07-02 (evidence retained
  `leg_h_aft_oat_holders_cloudflare_403.html`), matching the denominators-pass precedent.
- Alternate official channel (Banque de France, per the denominators precedent): the exact
  series **EXISTS** — webstat catalogue `DET.Q.FR.1315.F33000.M.Z9.8.F`, publisher title
  "Détention par les non-résidents de la Dette Négociable de l'Etat (en %)" / EN
  "Percentage of negotiable debt issued by the state and held by non-residents", quarterly,
  **1999-12-31→2025-12-31**, unit %, source agency FR2 (Banque de France) — all from the
  publisher's own metadata endpoint (retained
  `leg_h_bdf_webstat_DET_Q_FR_1315_F33000_metadata.json`, incl. last two published values
  56.0, 55.1). **But the observations could not be fetched:** the webstat ODS catalog
  exposes metadata-only shells portal-wide (CSV/JSON exports return zero records — probe
  retained `leg_h_bdf_webstat_DET_csv_export_empty.csv`), and the official data API
  requires registered client credentials (anonymous call → HTTP 401 "Invalid client id or
  secret", retained `leg_h_bdf_api_401_unauthorized.json`). Legacy portal endpoints
  redirect to the new JS app. **A leg that exists but cannot be fetched is NOT-AVAILABLE —
  this is a fetch failure, not absence by construction.**
- Partial compiler-published material retained (perimeter differs — general government, not
  the State-debt share; use decided by the assembly): the BdF Stat Info Q3-2025 release HTML
  embeds the chart series "Non-resident holdings of long-term debt (by resident issuer
  sector)" with the General government line **Q3-2022→Q3-2025** (48.89 → 53.83 %), retained
  `leg_h_bdf_statinfo_securities_issues_2025q3.html`; the "Émission et détention de titres
  français" 2025Q2 PDF carries the "dont État" stock and nonresident net-purchase flows,
  retained `leg_h_bdf_statinfo_emission_detention_2025q2.pdf`.
- **Compiler's own custody statement, verbatim** (BdF Stat Info Q3-2025, retained):
  > "Issuance data is based on issuers' reporting, while holding statistics is calculated
  > using custodian account statements."
  (FR, retained PDF: "...celles relatives aux détenteurs par les déclarations des teneurs
  de compte conservateurs.")
- Windows: the publisher's series covers both windows (1999Q4→2025Q4) but is unfetchable
  from this egress; retained partials cover Q3-2022→Q3-2025 on a different perimeter. Stated.

### (i) AGS — nonresident share — **GROUNDED-ALTERNATE-OFFICIAL**
- Tasked primary (AOFM): unreachable again 2026-07-02 — HTTP/2 stream INTERNAL_ERROR ×3
  with backoff, then HTTP/1.1 50-second timeout with 0 bytes (log retained
  `leg_i_aofm_retry_failure_log.txt`), consistent with the denominators-pass 503s.
- Alternate OFFICIAL channel per task: **ABS 5302.0 IIP via the ABS SDMX API** — stated as
  GROUNDED-ALTERNATE. Raw series retained
  (`leg_i_abs_iip_653B_gg_foreign_liab_debtsec.csv`): dataflow ABS:IIP(1.0.0), DATA_ITEM
  **653B "Foreign Liabilities, Portfolio investment, Debt securities"** × SECTOR **3000999
  "General Government Total"**, all seven measures (positions begin/end, transactions,
  price/FX/other adjustments, income), quarterly, **2013Q1→2026Q1**, AUD millions. Local
  currency: yes; positions on the IIP market-value convention (ABS methodology retained).
- Perimeter friction, stated: general government = AGS **plus** state/territory issuers
  (semis) — broader than AGS-only; and the AGS outstanding denominator is NOT-GROUNDED
  (AOFM blocked, denominators pass), so the share construction is the assembly's decision;
  the retained series is a local-currency amount leg.
- RBA channel probed and rejected as the leg: statistical table A3.1 "Holdings of
  Australian Government Securities and Semis" is holdings under RBA operations, not a
  nonresident split (file retained `leg_i_rba_a03hist_rba_own_holdings_notleg.xlsx`,
  marked not-the-leg).
- **Compiler's own custody/nominee statement, verbatim** (ABS BoP & IIP methodology,
  Dec 2025, retained `leg_i_abs_bop_iip_methodology_dec2025.html`):
  > "The security-by-security collection is a quarterly survey of nominees (Form 85L), in
  > respect of their holdings on behalf of non-residents, of securities issued in Australia
  > (shares, debt securities and all types of derivatives)."
- Windows: baseline 2015Q1→2021Q4 exact; verdict 2022Q1→2025Q4 exact (published to 2026Q1).

---

## M1 — the external-manager/custodian practice — **GROUNDED** (retained documents, quoted verbatim)

Practice (reserve managers use external managers and custodians) — IMF, *Revised Guidelines
for Foreign Exchange Reserve Management* (Executive Board, 2013-02-12),
https://www.imf.org/external/np/pp/eng/2013/020113.pdf, fetched 2026-07-02, retained
`leg_m1_imf_revised_guidelines_fx_reserve_management_2013.pdf`:
> "External managers may have skills that the reserve management entity lacks, or they may
> provide a level of safety to foreign operations that the entity is unable to achieve."
> "Appointment of external managers can also have implications for the reserve manager's
> choice of a custodian for its foreign securities."

Attribution consequence (destination compilers attribute to the intermediary/custodian
location) — U.S. Treasury/Federal Reserve, *Foreign Portfolio Holdings of U.S. Securities
as of June 28, 2024*,
https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/shl2024r.pdf,
fetched 2026-07-02, retained `leg_m1_ustreasury_tic_shl2024r_custodial_bias.pdf`:
> "...if a foreign custodian holds securities on behalf of a third country, the TIC system
> records the holder country as the custodian's residence, not the country of residence of
> the custodian's customer."
> "This 'custodial bias' tends to overstate the amounts of holdings by residents of
> countries with major custodial activities such as Belgium, Luxembourg, Switzerland, and
> the United Kingdom."
> "As such, some holdings attributed to private intermediaries, especially in major
> custodial centers, may reflect holdings of foreign official institutions."

Compiler-side corroboration is quoted verbatim inside legs (a) BoJ, (b) ECB, (e)
Finanzagentur/Bundesbank, (h) Banque de France, (i) ABS above. Consequence per the
pre-registration: **a null on any leg (and on the sweep) is WEAK evidence, not disposal.**

---

## Fetch log (chronological, all 2026-07-02 UTC)

1. mof.go.jp ebparea.htm / ebppi.htm / faq_its + 6a-20.csv — 200, retained (leg a).
2. boj.or.jp bop_06 index, exbpsm6, faqbpsm6 — 200, retained (leg a).
3. stat-search.boj.or.jp dload_en.html + regbp_q_en.zip + bp_m_en.zip + fof2_en.zip — 200, retained (legs a, f).
4. ECB data-api BP6 serieskeys wildcard + series CSV — 200, retained (leg b).
5. Eurostat bop_eu6_q constraint + LIAB probe (0 obs) + ASS probe (130 obs) — 200, retained (leg b).
6. ecb.europa.eu bopips202406 quality report PDF — 200, retained (leg b).
7. ons.gov.uk dataset-10 page + PB2016–PB2025 chapter-10 workbooks + 2014 Part 3 page — 200 ×13, retained (leg c).
8. statcan WDS metadata ×3 + 36100030 zip + IMDB 1535 — 200, retained (leg d).
9. deutsche-finanzagentur.de investor-structure — 200, retained; bundesbank.de MR 2018-07 PDF — 200, retained (leg e).
10. boj.or.jp sj index + sjpre.xlsx + exsj01.pdf — 200, retained (leg f).
11. ons.gov.uk HEWD/UKEA JSON + CSV — 200, retained; dmo.gov.uk quarterly-review list + jan-mar-2026.pdf — 200, retained (leg g).
12. aft.gouv.fr /en/oat-holders — **403 Cloudflare ×3 (backoff 5/10/15s)**, evidence retained (leg h).
13. webstat.banque-france.fr ODS catalog search + DET metadata + empty exports + records probes; api.webstat.banque-france.fr — **401**; banque-france.fr Stat Info HTML + PDF — 200, retained (leg h).
14. aofm.gov.au — **HTTP/2 INTERNAL_ERROR ×3 (backoff 8/16/24s), HTTP/1.1 timeout 50s** — log retained (leg i).
15. rba.gov.au tables index + a03hist.xlsx — 200, probed, marked not-the-leg, retained (leg i).
16. data.api.abs.gov.au IIP structure + 653B×3000999 data — 200, retained; abs.gov.au methodology Dec-2025 — 200, retained (leg i).
17. imf.org 020113.pdf — 200, retained; ticdata.treasury.gov shl2024r.pdf — 200, retained (M1).

No approval markers touched; writes confined to `build/reserve/rdtg_evidence/leg_*`,
`build/reserve/RDTG_legs_manifest.json`, `build/reserve/RDTG_legs_provenance.md`.
