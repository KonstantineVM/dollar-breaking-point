# RDT-F valuation-basis quotes (Part 2 grounding — quotes only; no reconciliation computed here)

Date grounded: 2026-07-02. Every basis statement below is quoted verbatim from the series' own publisher documentation retained on disk; nothing is asserted from memory. Machine companion for the center set: `build/reserve/RDTF_centers_manifest.json`.

## 1. FRBNY custody memo line (H.4.1) — basis: FACE VALUE (publisher-stated)

**Series:** Federal Reserve statistical release H.4.1, Table 1A "Memorandum Items", memo item "Securities held in custody for foreign official and international accounts", sub-line "Marketable U.S. Treasury securities" (carries superscript footnote 1). This is the series behind FRED WMTSECL1 used in RDT-E (`build/reserve/rdte_evidence/fred_wmtsecl1.csv`).

**Verbatim footnote 1 (the valuation-basis statement), from the release itself:**

> "Includes securities and U.S. Treasury STRIPS at face value, and inflation compensation on TIPS. Does not include securities pledged as collateral to foreign official and international account holders against reverse repurchase agreements with the Federal Reserve presented in tables 1, 5, and 6."

- Source path (fetched and retained this stage): `build/reserve/rdtf_evidence/frb_h41_current_20260702.htm` (raw bytes; footnote text at the Table 1A footnote block) with reading-aid extraction `build/reserve/rdtf_evidence/frb_h41_table1A_memo_extract.txt`. Also present, verbatim-identical, in the RDT-E retained copy `build/reserve/rdte_evidence/frb_h41_current.htm` (line 3281; memo row with footnote marker at lines 3081, 3054).
- Document identity: Board of Governors of the Federal Reserve System, statistical release H.4.1 "Factors Affecting Reserve Balances", release dated June 25, 2026 (week ended June 24, 2026), fetched 2026-07-02 from https://www.federalreserve.gov/releases/h41/current/h41.htm .

**Treasury's own concurring statement (TIC FAQ 10a),** verbatim: "Differences in valuation: The custody holdings at FRBNY are reported at face value." — `build/reserve/rdtd_evidence/tic_faq2.html` (FAQ 10a, "How do the TIC data on Major Foreign Holders of U.S. Treasury Securities compare with FRBNY custody holdings?"); reading aid `build/reserve/rdtf_evidence/tic_faq2_extracted.txt` line ~418.

**Basis-change history stated by the publisher text (FAQ 10b),** verbatim: "As of November 15, 2012, table 1A of the H.4.1 began reporting FRBNY custody holdings on a current face-value basis, which is much closer to the market value reported on the TIC SLT and SHL." (Through the November 8, 2012 release the holdings "were listed at original face value".) Same source paths. The RDT-F verdict axis (2023-05..2026-04) lies entirely in the current-face-value regime.

## 2. TIC MFH / SLT holdings — basis: ESTIMATED (MARKET) VALUE for long-term Treasuries; bills at FACE VALUE (publisher-stated)

**Verbatim, TIC FAQ 10a (`build/reserve/rdtd_evidence/tic_faq2.html`; reading aid `rdtf_evidence/tic_faq2_extracted.txt` line ~418):**

> "Differences in valuation: The custody holdings at FRBNY are reported at face value. TIC MFH data are reported at estimated value. As described in the companion note on the revised methodology for the MFH table effective February 29, 2012, the TIC MFH data for the most recent month for Treasury bonds and notes are estimated by taking the market value as of the most recent TIC SLT report, and then projecting forward one month using monthly transactions data, also at market value. Treasury bills and certificates are included at face value. These differences in valuation can also make slight differences both in holdings and in changes in holdings as reported in the two sources."

**Verbatim, the companion MFH methodology note itself (`build/reserve/rdte_evidence/method_mfh_legacy.html`, "Valuation of securities" paragraph; reading aid `rdtf_evidence/method_mfh_legacy_extracted.txt` line 343):**

> "Valuation of securities. Although holdings estimates in the Major Foreign Holders tables are still a hybrid of market and face values, the potential distortions caused by differences in market and face values are much reduced in the current methodology. Foreign holdings of long-term Treasury securities are collected at market value in the annual surveys and on the SLT. Transactions in long-term securities on the TIC S are also reported at market value. Foreign holdings of short-term Treasury bills are reported on the TIC form BL-2 at face value, but the differences between market and face values for short-term Treasury securities tends to be limited."

- Document identity: U.S. Treasury, "New Methodology for Estimating Major Foreign Holders of Treasury Securities" (effective with the February 29, 2012 release), http://www.treasury.gov/resource-center/data-chart-center/tic/Pages/method-mfh.aspx , fetched 2026-07-02T14:36:45Z. (The modern URL https://home.treasury.gov/.../methodology-for-estimating-holdings-of-treasury-securities returned HTTP 404 on 2026-07-02 per `rdte_evidence/_RDTE_fetch_log.txt` line 1 — the method-mfh.aspx page is the copy that resolves.)
- The current expanded-SLT form title itself carries the fair-value basis in its name, verbatim from the MFH/SLT Table 5 notes (`build/reserve/rdte_evidence/slt_table5_live.txt` lines 39-42, fetched 2026-07-02 from https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.txt): "Estimated foreign holdings of U.S. Treasury marketable and non-marketable bills, bonds, and notes reported under the Treasury International Capital (TIC) reporting system are based on monthly data on holdings of Treasury bonds and notes as reported on TIC Form SLT, \"Aggregate Holdings, Purchases and Sales, and Fair Value Changes of Long-Term Securities by U.S. and Foreign Residents\" and on TIC Form BL2, \"Report of Customers' U.S. Dollar Liabilities to Foreign Residents.\"

**Finding, stated plainly:** the publisher's word for the MFH aggregate basis is "estimated value" (a hybrid: long-term Treasuries at market value from SLT/surveys; bills and certificates at face value). The pre-registration's expectation "estimated market value" is confirmed for the long-term component, which dominates the official aggregate (Of Which: Foreign Official T-Bonds & Notes 3,449.2 vs Bills 457.3 $bn at 2026-04 per `slt_table5_live.txt` lines 30-31); the bill component is face value by publisher statement.

## 3. SLT "valuation change" column — what it measures (publisher-stated) and where it lives

**Definition, verbatim, TIC FAQ 2 "(2023 Sept.)" (`build/reserve/rdtd_evidence/tic_faq2.html`; reading aid `rdtf_evidence/tic_faq2_extracted.txt` lines ~350-361):**

> "This information will help users decompose changes in holdings into changes due to transactions and changes due to price movements. Valuation changes include both price change and exchange rate changes for non-dollar denominated securities."

and the residual caveat, verbatim (same FAQ):

> "Will changes in holdings equal net transactions plus valuation changes ? No, holdings changes will not necessarily equal net transactions plus valuation changes. Changes in holdings may differ from net transactions plus valuation changes due to other changes, which are defined as a residual. Other changes can include purchases or sales of U.S. securities by one foreign country from another foreign country, changes in the foreign country where U.S. securities are held, changes in the respondent panel, corporate acquisitions by stock swaps, and any other change in holdings not included in net transactions or valuation changes."

**Publication start, verbatim, live TIC securities(b) page (`build/reserve/rdtb_evidence/tic_secb_live.html`, fetched 2026-07-02; reading aid `rdtf_evidence/tic_secb_live_extracted.txt` line 330):**

> "Data in columns called \"Net U.S. Sales\" and \"Valuation Change\" do have a series break at 2023-02. The series-break marks the beginning of the new transactions and valuation change data collected on the expanded Form SLT. Before the series-break the transactions data were collected on the discontinued Form S. There were no valuation change data before the series-break at 2023-02."

**Where the official-aggregate valuation-change column actually lives on disk (friction against the pre-registration's file naming):**
- The pre-registration references "the on-disk slt2d/official rows". Per the publisher's 03-31-2023 notice on the securities(b) page (reading aid line 373-376, verbatim): "The \"slt_table1.html\" (and \"slt_table1.txt\" ) file covers data on foreign holdings and net U.S. sales of U.S. long-term securities. It replaces several old files: slt1d, slt1d_globl, slt2d, slt2d_history." and "The \"slt_table3.html\" (and \"slt_table3.txt\" ) file covers data on foreign holdings and net U.S. sales of U.S. Treasury securities. It replaces old files: slt3d, slt3d_globl, tressect."
- The on-disk snapshot `build/data/treasury_tic/current/slt2d.txt` is the legacy holdings-only Table 2D (columns 2022-01..2023-01, no valuation column).
- The Treasury-securities official aggregate WITH the "Valuation Change" column is on disk in `build/reserve/rdt_evidence/tic/slt_table3.txt` (fetched 2026-07-01 from https://treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table3.txt): header row names the column "Valuation Change" (machine name `for_lt_treas_valchg`, long-term Treasuries only) and rows "Of Which: Foreign Official" (country code 99990) carry populated values from 2023-02 through 2026-04 (e.g. line 6774: 2026-04 value −8,872 $mn). There is no valuation-change column for short-term bills (which are at face value per section 2).
- **Staleness note, stated plainly:** TIC FAQ 2's sub-answer "Are valuation data from the expanded TIC Form SLT also being published ? Not at present." is contradicted by the newer securities(b)-page notice and by the populated columns in the retained `slt_table3.txt`; the FAQ text is the stale one. An "Article on TIC" dated 04-18-2024 about the valuation-change data is referenced on the securities(b) page (reading aid line 329) but was not fetched; the definition quoted above from FAQ 2 plus the series-break notice are the publisher statements this contract rests on.

## Verification trail

| Claim | Verbatim quote source (on disk) | Publisher URL, fetch date |
|---|---|---|
| H.4.1 memo marketable-UST custody at face value | `rdtf_evidence/frb_h41_current_20260702.htm` (+ `rdte_evidence/frb_h41_current.htm` line 3281) | https://www.federalreserve.gov/releases/h41/current/h41.htm , 2026-07-02 |
| FRBNY custody at face value / MFH at estimated value | `rdtd_evidence/tic_faq2.html` (FAQ 10a) | https://home.treasury.gov/data/treasury-international-capital-tic-system-home-page/frequently-asked-questions-regarding-the/ticfaq2 , 2026-07-02 |
| Long-term Treasuries at market value on SLT/surveys; bills at face value | `rdte_evidence/method_mfh_legacy.html` ("Valuation of securities") | http://www.treasury.gov/resource-center/data-chart-center/tic/Pages/method-mfh.aspx , 2026-07-02 |
| Valuation change = price change + exchange-rate change; residual "other changes" | `rdtd_evidence/tic_faq2.html` (FAQ 2, 2023 Sept.) | same FAQ URL, 2026-07-02 |
| Valuation-change data published from series break 2023-02 | `rdtb_evidence/tic_secb_live.html` (securities(b) page) | https://home.treasury.gov/data/treasury-international-capital-tic-system-home-page/tic-forms-instructions/securities-b-portfolio-holdings-of-us-and-foreign-securities , 2026-07-02 |
| Official-aggregate valchg rows on disk, 2023-02..2026-04 | `rdt_evidence/tic/slt_table3.txt` ("Of Which: Foreign Official", 99990) | https://treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table3.txt , 2026-07-01 |
