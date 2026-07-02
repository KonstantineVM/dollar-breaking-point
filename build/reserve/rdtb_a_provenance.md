# RDT-B Part A — provenance (SOURCE lines)

All fetches 2026-07-02 (UTC), via the pre-configured HTTPS proxy; raw files retained in
`build/reserve/rdtb_evidence/`; fetch log: `build/reserve/rdtb_evidence/_RDTB_fetch_log.txt`.
On-disk reads are read-only inspections of files committed by earlier agents (paths + their own fetch dates given).

## 1. SLT schema read (on-disk, read-only)

- SOURCE: `build/data/treasury_tic/current/slt_tables/slt_table1.txt` (publisher: https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table1.txt, on-disk copy 2026-06-29). By-country long-term securities; columns = instrument x {Holdings, Net U.S. Sales, Valuation Change}; **no holder-sector column**.
- SOURCE: `build/reserve/rdt_evidence/tic/slt_table3.txt` (publisher: https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table3.txt, on-disk copy 2026-07-01). By-country Treasuries monthly; header `country, country_code, date, for_treas_pos, for_treas_net, for_lt_treas_pos, ...`; **no holder-sector column**.
- SOURCE: `build/data/treasury_tic/current/slt1d.txt` (TIC Table 1D snapshot, on-disk copy 2026-06-29). By-country, instrument split only.
- SOURCE: `build/data/treasury_tic/current/slt2d.txt` (TIC Table 2D snapshot, on-disk copy 2026-06-29). **Aggregate** all-countries rows `Foreign official` / `Private` per instrument, monthly — the SLT official split exists ONLY at this aggregate level. Full history is published as `slt2d_history.csv` (link verified on the live securities(b) page, 2026-07-02).
- SOURCE: `build/data/treasury_tic/current/slt_tables/slt_table5.txt` and `build/reserve/rdt_evidence/tic/slt_table5.txt` (publisher: https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.txt). MFH-format by-country totals 2025-04..2026-04 plus aggregate rows `Of Which: Foreign Official` / `... Treasury Bills` / `... T-Bonds & Notes`.
- SOURCE: `build/reserve/rdt_evidence/tic/mfhhis01.csv` (publisher: https://treasury.gov/resource-center/data-chart-center/tic/Documents/mfhhis01.csv, on-disk copy 2026-07-01). Monthly grids 2000–2025, each with an aggregate `For. Official` row (26 rows counted). **Part-B baseline: available on disk, monthly, 2012–2026-04 fully covered together with slt_table5.**

FINDING (either-way rule): no SLT table, on disk or in the live TIC document list, carries a foreign-official vs private split **by country**.

## 2. TIC SHL annual reports (fetched)

- SOURCE: https://home.treasury.gov/data/treasury-international-capital-tic-system/us-liabilities-to-foreigners-from-holdings-of-us-securities (fetched 2026-07-02) → `tic_shl_reports_page.html`. Lists annual reports 2002–2025.
- SOURCE: https://www.treasury.gov/resource-center/data-chart-center/tic/Documents/shl2025r.pdf (fetched 2026-07-02) → `shl2025r.pdf`, text extraction `shl2025r_extracted.txt`. Official holder-sector data: Exhibit 5 (AFE/EME x official/private), Exhibit 7 (LT securities, all-countries official/private, 2008–2025), Exhibit 8 (ST). **No by-country official values anywhere in the 137-page report** (zero lines containing a country name and "official" with data). Confidentiality: form instructions §I.C — results "made available to the general public at an aggregated level so that neither the U.S. persons or organizations providing information, nor individual or organizational ownership of U.S. securities can be identified."
- SOURCE: https://www.treasury.gov/resource-center/data-chart-center/tic/Documents/shla2018r.pdf (fetched 2026-07-02) → `shla2018r.pdf`. Same pattern (Exhibits 9/10 aggregate official); zero country+official data lines. Cross-vintage confirmation.
- SOURCE: appendix table zips (all fetched 2026-07-02, same Documents/ base URL): `shl2015r-appx.zip`, `shla2016r-appx.zip`, `shla2017r-appx.zip`, `shla2018r_appx.zip`, `shl2019r_appx.zip`, `shla2020r_appx.zip`, `shla2021r_appx.zip`, `shla2022r_appx.zip`, `shla2023r_appx.zip`, `shl2024r_appx.zip`, `shl_appendix_2025.zip`. Tables A1–A12 are by-country x instrument; **no holder-sector dimension in any vintage**. Used for: total US securities (A1) and total/LT Treasuries (A7/A1) for China, Belgium, Luxembourg, June 2015–2025 — all TOTAL_RESIDENT.
- SOURCE: https://www.treasury.gov/resource-center/data-chart-center/tic/Documents/shlhistdat.txt (fetched 2026-07-02) → `shlhistdat.txt`. By-country totals only; footnote confirms official holdings folded into totals, not shown by country.

FINDING: TIC SHL by-country OFFICIAL holdings = **NOT-AVAILABLE** (confidentiality suppression; aggregate holder-sector only). Recorded per the pre-registration; the total-resident by-country values are retained and flagged OVERSTATES_OFFICIAL / lower_bound_eligible=false.

## 3. TIC official-institution lines by country

Tried: MFH (`mfh.txt`, `mfhhis01.csv`, `slt_table5.txt`), SLT tables 1–6 and 1D/2D/3D, `shlhistdat.txt`, and the live securities(b) document list (https://home.treasury.gov/data/treasury-international-capital-tic-system-home-page/tic-forms-instructions/securities-b-portfolio-holdings-of-us-and-foreign-securities, fetched 2026-07-02 → `tic_secb_live.html`). FINDING: **NOT-AVAILABLE** — official lines exist only as all-countries aggregates.

## 4. BIS LBS (fetched)

- SOURCE: https://stats.bis.org/api/v2/structure/dataflow/BIS?format=sdmx-json (fetched 2026-07-02) → `bis_dataflows.json`; flow `WS_LBS_D_PUB` v1.0 ("Locational banking") confirmed current.
- SOURCE: https://stats.bis.org/api/v2/structure/dataflow/BIS/WS_LBS_D_PUB/1.0?references=all (fetched 2026-07-02) → `bis_lbs_dsd.json`. Counterparty-sector dimension `L_CP_SECTOR` → codelist `CL_L_SECTOR`, quoted in full in the manifest; contains `M = Banks, central banks` and `O = Official sector`.
- SOURCE: https://stats.bis.org/api/v2/data/dataflow/BIS/WS_LBS_D_PUB/1.0/Q.S.L.A.USD.A.5J.A.5A.{A,B,G,N,M,O}.CN.N?format=csv&startPeriod=2014-01-01 (fetched 2026-07-02) → `bis_lbs_L_USD_CN_{A,B,G,N,M,O}.csv`. A/B/G/N return data 2014-Q1..2025-Q4; **M and O return `No results for query` (SDMX error code 100)** — raw error responses retained.
- SOURCE: https://stats.bis.org/api/v2/availability/dataflow/BIS/WS_LBS_D_PUB/1.0/Q.S.L.A.USD.A.5J.A.5A.*.CN.N?mode=available (fetched 2026-07-02) → `bis_lbs_avail_sector_CN.json`. Published sectors for the China key: `A,B,C,F,G,H,I,K,N,P,U,X` — no M, no O.
- SOURCE: https://stats.bis.org/api/v2/data/dataflow/BIS/WS_LBS_D_PUB/1.0/Q.S.L.G.USD.A.5J.A.5A.A.CN.N?format=csv&startPeriod=2014-01-01 (fetched 2026-07-02) → `bis_lbs_L_loansdep_USD_CN_A.csv` (loans & deposits, all sectors).

FINDING: **no official/central-bank counterparty split** for USD liabilities to China in public LBS. The total-resident series (A; 638.8 $bn at 2025-Q4, all instruments) is recorded UPPER-side only, holder_sector=TOTAL_RESIDENT, lower_bound_eligible=false — it is NOT presented as official-attributable. General-government (G) exists but excludes the central bank and is negligible (~0.04 $bn in 2014-Q1); documented in the manifest, excluded from the CSV.

## 5. Bias-direction rule compliance

Every CSV row carries `bias_direction` and `lower_bound_eligible`. Zero rows are lower-bound-eligible: no China-attributable OFFICIAL component grounds in any inspected source. Aggregate OFFICIAL rows (country=ALL) are marked UNDERSTATES_OFFICIAL but lower_bound_eligible=false (not China-attributable). All total-resident rows are OVERSTATES_OFFICIAL / false. This satisfies "a total-resident component inside the lower bound is a build failure" by construction.
