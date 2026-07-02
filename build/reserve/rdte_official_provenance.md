# RDT-E Part 1(iv)-(v) — Provenance for the official-series legs and the methodology determination

Built 2026-07-02. All raw inputs retained on disk; nothing asserted from memory. Disk-first policy:
the verdict-axis coverage (2023-05..2026-04) was verified from the already-retained RDT/RDT-B/RDT-D
evidence before any new fetch; only the FRBNY leg, the MFH methodology note, and a freshness check
were fetched (log: `build/reserve/rdte_evidence/_RDTE_fetch_log.txt`).

## TIC aggregate foreign-official UST series (`tic_official_ust_busd`)

- SOURCE: https://treasury.gov/resource-center/data-chart-center/tic/Documents/mfhhis01.csv —
  TIC Major Foreign Holders history, memo line "For. Official" per year block; fetched 2026-07-01
  (RDT stage, `build/reserve/rdt_evidence/tic/_RDT_fetch_log.txt`); file (READ-ONLY here):
  `build/reserve/rdt_evidence/tic/mfhhis01.csv`. Used for 2013-01..2025-12.
- SOURCE: https://treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.txt —
  SLT Table 5 "Major Foreign Holders of Treasury Securities", row "Of Which: Foreign Official";
  fetched 2026-07-01 (RDT stage); file: `build/reserve/rdt_evidence/tic/slt_table5.txt`. Used for
  2026-01..2026-04.
- SOURCE (freshness check): https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.txt
  — refetched 2026-07-02 → `build/reserve/rdte_evidence/slt_table5_live.txt`; byte-identical to the
  on-disk copy (`diff -q`), confirming the on-disk vintage is current (data through 2026-04).
- Cross-check: the 9 overlapping months (2025-04..2025-12) between mfhhis01.csv and slt_table5.txt
  agree exactly (max abs diff 0.0 $bn) — computed in
  `build/reserve/rdte_evidence/_RDTE_build_official.py`.
- Series semantics per publisher (footnotes retained in both files): bills/certificates at face
  value plus bonds & notes at market value; collected primarily from U.S.-based custodians;
  publication lag ~6 weeks.

## FRBNY H.4.1 foreign-official custody series (`frbny_custody_ust_busd`)

- SOURCE (data, FRED mirror): https://fred.stlouisfed.org/graph/fredgraph.csv?id=WMTSECL1 —
  fetched 2026-07-02 → `build/reserve/rdte_evidence/fred_wmtsecl1.csv`. Series WMTSECL1
  "Memorandum Items: Custody Holdings: Marketable U.S. Treasury Securities: Wednesday Level",
  weekly (as of Wednesday), millions of USD, NSA, release "H.4.1 Factors Affecting Reserve
  Balances", source Board of Governors — metadata verified on the FRED series page, fetched
  2026-07-02 → `build/reserve/rdte_evidence/fred_wmtsecl1_page.html`.
- SOURCE (primary verification): https://www.federalreserve.gov/releases/h41/current/h41.htm —
  H.4.1 release of 2026-06-25, fetched 2026-07-02 → `build/reserve/rdte_evidence/frb_h41_current.htm`.
  Table 1A Memorandum Items: "Securities held in custody for foreign official and international
  accounts" → "Marketable U.S. Treasury securities", Wednesday 2026-06-24 = 2,636,947 $mn —
  IDENTICAL to the FRED latest observation (2636947). Tier stated: history taken from the FRED
  mirror; label and latest value verified against the FRB primary.
- Monthly conversion: last weekly (Wednesday) observation within each calendar month; observation
  date carried per row in `frbny_obs_date`; millions → billions ($bn, 3 dp).
- Comparability caveats vs the TIC leg (publisher-stated, TIC FAQ #10a, quoted in
  `rdte_methodology_determination.md`): face value vs TIC's valuation hybrid; Wednesday vs
  month-end; FRBNY-custodied-only vs all U.S. reporters; includes international accounts.

## Methodology determination inputs (Part v)

- SOURCE: `build/reserve/rdtb_evidence/shl2025r_extracted.txt` — text extraction of the SHL 2025
  report (https://www.treasury.gov/resource-center/data-chart-center/tic/Documents/shl2025r.pdf,
  fetched 2026-07-02T02:59:34Z, RDT-B stage log).
- SOURCE: `build/reserve/rdtd_evidence/tic_faq2.html` — TIC FAQ part 2
  (https://home.treasury.gov/data/treasury-international-capital-tic-system-home-page/frequently-asked-questions-regarding-the/ticfaq2,
  HTTP 200, fetched 2026-07-02, RDT-D stage log). Carries FAQ #7 (custodial bias) and FAQ #10a
  (TIC vs FRBNY custody).
- SOURCE: https://www.treasury.gov/resource-center/data-chart-center/tic/Pages/method-mfh.aspx —
  "Estimating Holdings of Treasury Securities" (MFH methodology note), fetched 2026-07-02 →
  `build/reserve/rdte_evidence/method_mfh_legacy.html`. (A guessed home.treasury.gov path returned
  404 first; recorded in the fetch log.)
- Determination (ESTABLISHED) with verbatim quotes: `build/reserve/rdte_methodology_determination.md`.

## Reproduction

- Builder script (deterministic, no hardcoded numbers):
  `build/reserve/rdte_evidence/_RDTE_build_official.py` → writes
  `build/reserve/rdte_official_series.csv` and prints the summary JSON used in
  `rdte_official_manifest.json`.
