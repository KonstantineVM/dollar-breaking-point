# Full-Panel Power Rebuild, Part 1 — Tagged Haven Panel (maximum temporal extent)

SOURCE: Real SEC Form N-PORT structured data sets, one ZIP per dissemination quarter,
`https://www.sec.gov/files/dera/data/form-n-port-data-sets/{YYYYqQ}_nport.zip`, downloaded
with a descriptive User-Agent `dollar-breaking-point research milevsky@hotmail.com` and a
`From:` header, bounded per download, streamed and DELETED between quarters. Dissemination
quarter is ONE AHEAD of the fiscal quarter (only last-month-of-fiscal-quarter N-PORT reports
are ever public — SEC dissemination rule), so fiscal `2019q3 <- zip 2019q4 ... 2024q4 <- zip
2025q1`. Parse reused VERBATIM from `build/data/nport/build_us_china_panel.py`
(`build_quarter`); haven filtering + column finalize reused via
`build/data/nport/build_fullpanel_haven.py`. Tagging reused VERBATIM from
`build/data/nport/panel_crosswalk_tagged_recompute.py` (R1–R4 rule logic + the SAME
crosswalk source files under `build/data/crosswalk/`), applied by
`build/data/nport/tag_fullpanel.py`.

Artifact: `build/data/nport/panel_crosswalk_tagged_full.parquet`.

## What was reused, NOT re-derived

- **Per-quarter N-PORT parse** — `build_us_china_panel.build_quarter` called unchanged: reads
  the ZIP's structured TSV tables (`FUND_REPORTED_HOLDING`, `IDENTIFIERS`, `SUBMISSION`,
  `FUND_REPORTED_INFO`, `REGISTRANT`), joins fund identity (`cik | series_id`) and
  `fiscal_quarter`, residence (`INVESTMENT_COUNTRY` → ISO2 → ISO3 echo, `is_haven_resident`
  for KY/HK/VG), `currency_value`, issuer keys (`cusip`/`cusip6`/`isin`/`issuer_lei`/
  `issuer_name`). Only the quarter COUNT changed vs the prior 8-quarter panel.
- **R1–R4 CN-nationality tagging** — the rule IDENTIFIER SETS (R1 SEC-HFCAA resolved
  CUSIP6/ISIN/LEI; R2 XBRL VIE OpCo jurisdiction=CN; R3 F-6/20-F jurisdiction=CN; R4
  GLEIF-QCC CN-segment, restricted) are constructed EXACTLY as in the recompute, from the
  SAME source files (`hfcaa/hfcaa_conclusive.json`, `hfcaa/company_tickers.json`,
  `edgar/edgar_jurisdiction_provenance.json`, `qcc/lei-qcc-20250901T000000.csv`), and R1's
  HFCAA-name→identifier resolution is done against the SAME 8-quarter resolution panel
  (`us_china_nationality_panel.parquet`) the recompute used. The rules are issuer-keyed
  (cusip6/isin/lei), not quarter-specific, so the frozen sets tag every added quarter by the
  same issuer keys. **Verified byte-identical**: re-running the rule construction and tagging
  the resolution panel's 663,325 haven rows reproduces the prior `panel_crosswalk_tagged.parquet`
  with **0 row mismatches** and CN rows 64,057 = 64,057.

Rule-set sizes (frozen, identical to the prior leak-fixed pass): R1 {isin 301, cusip6 180,
lei 108}; R2 {isin 29, cusip6 8, lei 3}; R3 {isin 22, cusip6 5, lei 2}; R4 {QCC-CN LEIs 155};
HFCAA CIIs matched to panel = 148. GCAP note: N-PORT geographic basis is RESIDENCE
(issuer country of organization); the R1–R4 tagging is the residency→nationality (haven→China)
reattribution — its effect is the `parent_nationality=CN` cell reported per quarter below.

## Quarters IN (all 22 — full target span achieved)

Fiscal span **2019q3 → 2024q4, contiguous, 22 of 22 target quarters. None dropped.**
Every quarter traces to a real downloaded ZIP (existing 8 from the prior run's identical
parse; new 14 downloaded this run and deleted after parse).

| fiscal | zip | zip bytes | holdings in qtr | haven rows | CN-tagged rows | ident. cov % | source |
|--------|-----|-----------|-----------------|-----------|----------------|--------------|--------|
| 2019q3 | 2019q4 | 240,007,320 | 2,939,568 | 62,821 | 5,600 | 99.3283 | prior-run (identical parse) |
| 2019q4 | 2020q1 | 340,462,382 | 4,355,921 | 77,391 | 7,146 | 99.3707 | prior-run (identical parse) |
| 2020q1 | 2020q2 | 332,888,140 | 4,058,607 | 78,480 | 7,563 | 99.2444 | prior-run (identical parse) |
| 2020q2 | 2020q3 | 371,068,711 | 4,631,801 | 82,351 | 8,474 | 99.2423 | prior-run (identical parse) |
| 2020q3 | 2020q4 | 359,205,250 | 4,408,043 | 84,547 | 9,208 | 99.2087 | prior-run (identical parse) |
| 2020q4 | 2021q1 | 342,516,796 | 4,263,146 | 81,343 | 8,486 | 99.0546 | this-run download |
| 2021q1 | 2021q2 | 358,497,137 | 4,348,390 | 91,366 | 9,939 | 99.1660 | this-run download |
| 2021q2 | 2021q3 | 380,417,219 | 4,609,095 | 95,039 | 9,545 | 99.0930 | this-run download |
| 2021q3 | 2021q4 | 374,616,598 | 4,500,945 | 99,627 | 9,410 | 99.1207 | this-run download |
| 2021q4 | 2022q1 | 482,447,144 | 6,331,478 | 93,835 | 8,395 | 99.1847 | this-run download |
| 2022q1 | 2022q2 | 432,741,571 | 5,384,188 | 100,204 | 9,948 | 99.1497 | prior-run (identical parse) |
| 2022q2 | 2022q3 | 724,385,184 | 10,002,036 | 93,445 | 8,863 | 99.2199 | prior-run (identical parse) |
| 2022q3 | 2022q4 | 422,189,888 | 5,226,300 | 90,555 | 8,739 | 99.2016 | this-run download |
| 2022q4 | 2023q1 | 480,447,687 | 6,255,353 | 88,853 | 8,283 | 99.1030 | this-run download |
| 2023q1 | 2023q2 | 427,953,767 | 5,399,060 | 93,740 | 9,583 | 99.3589 | this-run download |
| 2023q2 | 2023q3 | 457,209,257 | 5,971,675 | 88,815 | 8,471 | 99.3830 | this-run download |
| 2023q3 | 2023q4 | 420,320,703 | 5,201,934 | 86,288 | 8,180 | 99.2525 | this-run download |
| 2023q4 | 2024q1 | 446,989,787 | 6,104,221 | 81,021 | 6,967 | 99.3212 | this-run download |
| 2024q1 | 2024q2 | 506,739,574 | 6,673,064 | 89,643 | 8,800 | 99.2481 | this-run download |
| 2024q2 | 2024q3 | 478,076,657 | 6,107,336 | 85,397 | 7,630 | 99.1510 | this-run download |
| 2024q3 | 2024q4 | 406,008,057 | 5,080,041 | 82,695 | 7,261 | 99.1535 | this-run download |
| 2024q4 | 2025q1 | 462,120,659 | 5,948,809 | 84,086 | 7,255 | 99.1188 | prior-run (identical parse) |

**Totals:** haven rows = **1,911,542**; CN-tagged rows = **183,746**; distinct (cik,series)
funds = **7,856**; distinct cik = **1,451**; fund-quarter (fiscal_quarter × cik × series_id)
universe = **105,420**; cik-quarter universe = **24,140**.

## Quarters OUT

**None.** The full 22-quarter target span (2019q3–2024q4) is IN. No quarter was skipped and
there is no fall-back to the prior 8-quarter subset. (Public N-PORT begins with the 2019q4
dissemination ZIP → fiscal 2019q3; there is no earlier public fiscal quarter to include.)

## Identifier-coverage check (replicated on the NEW quarters, MEASURED per quarter)

Definition (same as prior): share of haven rows carrying a usable ISIN (12 chars) OR usable
CUSIP (9 chars). Threshold: >95%. **Every one of the 22 quarters passes.** Range across all
quarters: **99.0546% (2020q4) to 99.3830% (2023q2)**; minimum = 99.0546% > 95%. These are
measured on the rows actually built, not asserted. The 14 new quarters specifically: min
99.0546% (2020q4), all > 99%.

## Overlap-consistency result (vs prior `panel_crosswalk_tagged.parquet`)

The 8 overlapping fiscal quarters (2019q3, 2019q4, 2020q1, 2020q2, 2020q3, 2022q1, 2022q2,
2024q4) in the full panel were compared against the prior tagged panel:

- Full-panel overlap rows = **663,325** = prior rows **663,325**.
- `rules_fired` multiset **identical** (every rule-combination bucket matches exactly).
- Shared issuer keys (cusip, isin, lei) = 32,340; **mismatched rule decisions = 0**.
- CN-tagged rows in overlap = **64,057** = prior CN rows **64,057**.

The tagging on the overlapping quarters reproduces the prior panel exactly — the R1–R4 rules
were applied consistently, not re-derived.

## Schema

`fiscal_quarter, cik, series_id, cusip, isin, cusip6, issuer_name, issuer_lei,
residence_iso3, parent_nationality, rules_fired, currency_value`. This is the prior tagged-panel
schema PLUS `fiscal_quarter` and the fund-identity columns `cik, series_id` (holder identity
carried through this time, because Part 2's fund × quarter weight panel needs it).

## Caveats (carried, not smoothed)

- Geographic basis is RESIDENCE; `parent_nationality=CN` is the constructed reattribution from
  R1–R4 and is retained ALONGSIDE `residence_iso3` (auditable per row). Rows with no resolvable
  identifier tying to a source row are left `UNDETERMINED-NON-CN-OR-UNREACHED` — no name-guessing.
- Holder universe is U.S.-registered-fund filers only (N-PORT scope); not the global holder matrix.
- R4 reach is capped by LEI presence; the QCC restriction to CN-segment is the load-bearing guard
  against spurious CLO/Cayman tagging (documented in the recompute provenance, reused verbatim here).
- `currency_value` USD denomination is the N-PORT standard but was not confirmed from primary
  form-instruction text in the Part-0 pass; `currency_code` is retained per source row.

## Generators

- `build/data/nport/build_fullpanel_haven.py` — orchestrates the 14 missing quarters, reusing
  `build_us_china_panel.build_quarter`; filters early to haven; deletes each ZIP after parse.
- `build/data/nport/tag_fullpanel.py` — reuses the R1–R4 rule construction from the recompute,
  freezes the identifier sets against the resolution panel, tags all 22 quarters, carries
  fiscal_quarter + cik + series_id.
- Per-quarter build/tag summaries: `build/data/nport/haven_parts/_meta_2021q1.json`,
  `build/data/nport/haven_parts/_tag_summary.json`.
