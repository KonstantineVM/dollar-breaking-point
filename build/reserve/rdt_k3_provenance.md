# RDT k3 provenance — UST positions and net Treasury transactions (US Treasury TIC)

All fetches 2026-07-01 UTC through the configured proxy; raw files retained in
`build/reserve/rdt_evidence/tic/`; append-only log `build/reserve/rdt_evidence/tic/_RDT_fetch_log.txt`.
Build script (offline, rerunnable from the raw files): `build/reserve/rdt_evidence/tic/_RDT_k3_build.py`.
Nothing below is asserted from memory; every claim was read from the fetched publisher files/pages named.

## How the file URLs were grounded (navigation trail, not guessed filenames)

1. SOURCE: https://home.treasury.gov/data/treasury-international-capital-tic-system (fetched 2026-07-01) — TIC landing page → `tic_landing.html`.
2. SOURCE: https://home.treasury.gov/data/treasury-international-capital-tic-system/tic-forms-instructions/securities-b-portfolio-holdings-of-us-and-foreign-securities (fetched 2026-07-01) — Securities (B) page → `tic_secb_page.html`. This page carries the live links and every methodology notice quoted below. Verified anchor texts:
   - "Major Foreign Holders of U.S. Treasury Securities (MFH table)" → slt_table5.html/.txt ("Monthly, in file called Table 5")
   - "Recent and historical data for more countries holding Treasury securities" → slt_table3.html/.txt ("Monthly in file called Table 3")
   - "MFH-history tables" → mfhhis01.html/.txt/.csv ("History back to March 2000")
   - "the 2011 through 2019 data" / "More Countries holding Treasury securities since September 2011" → slt3d_globl.csv
   - "Treasury holdings for twelve oil exporting countries, December 1974 to March 2016" → oilexp_hist_to2016mar.csv
3. SOURCE: https://home.treasury.gov/data/treasury-international-capital-tic-system-home-page/tic-forms-instructions/securities-a-us-transactions-with-foreign-residents-in-long-term-securities (fetched 2026-07-01) — Securities (A) page → `tic_seca_page.html`. Verified anchors: "Global (includes a set for each country)" → s1_globl.tic/.txt; "Transactions with four oil exporting countries, January 2003 to December 2014" → oilexp_sdata_hist_2003-2014.csv.

## Raw data files (all retained)

| file | URL (SOURCE) | fetched | role |
|---|---|---|---|
| slt_table5.txt / .html | https://treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.txt | 2026-07-01 | current MFH table (Table 5); top-20 named holders + All Other; months 2025-04..2026-04; billions USD; used for cross-check only |
| mfhhis01.csv / .txt | https://treasury.gov/resource-center/data-chart-center/tic/Documents/mfhhis01.csv | 2026-07-01 | MFH history tables, yearly blocks, monthly 2000-03..2025-12, billions USD; PRIMARY positions source |
| slt_table3.txt | https://treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table3.txt | 2026-07-01 | all-countries long file 2020-01..2026-04, millions USD: total/LT/ST holdings, Net U.S. Sales, Valuation Change; positions 2026-01..04 and transactions from 2023-02 |
| slt3d_globl.csv | https://treasury.gov/resource-center/data-chart-center/tic/Documents/slt3d_globl.csv | 2026-07-01 | frozen all-countries holdings 2011-09..2023-01, millions USD; fills Russia 2019, Turkey 2018-2019 |
| s1_globl.txt | https://treasury.gov/resource-center/data-chart-center/tic/Documents/s1_globl.txt | 2026-07-01 | Form S gross transactions by country, monthly to 2023-01; net LT Treasury purchases = col[1] − col[7]; PRIMARY transactions source pre-break |
| oilexp_sdata_hist_2003-2014.csv | https://treasury.gov/resource-center/data-chart-center/tic/Documents/oilexp_sdata_hist_2003-2014.csv | 2026-07-01 | one-time Form S transactions for Bahrain/Kuwait/Saudi Arabia/UAE (Saudi rows 2008-01..2014-12); Saudi transactions 2013-2014 |
| oilexp_hist_to2016mar.csv | https://treasury.gov/resource-center/data-chart-center/tic/Documents/oilexp_hist_to2016mar.csv | 2026-07-01 | one-time holdings table, 12 oil exporters incl. named Saudi Arabia column, 1974-12..2016-03, billions; retained as context (NOT merged) |
| mfh.txt | https://treasury.gov/resource-center/data-chart-center/tic/Documents/mfh.txt | 2026-07-01 | frozen pre-redesign MFH snapshot (dated March 15, 2023; data 2022-01..2023-01); retained as context and cross-check |

## Built outputs

- `build/reserve/rdt_k3_ust.csv` — country, date (YYYY-MM), ust_busd, source_file. 2,135 rows,
  8 countries, no monthly gaps 2013-01 onward. Merge precedence mfhhis01.csv > slt_table3.txt >
  slt3d_globl.csv (mfhhis01 carries the latest MFH revision). Table-3/slt3d values are millions
  converted /1000.
- `build/reserve/rdt_k3_transactions.csv` — country, period (YYYY-MM), net_purchases_busd,
  source_file. 1,280 rows: 8 countries × 160 months (2013-01..2026-04), no gaps. Long-term
  Treasury bonds & notes only (bills are not in the transactions data). Positive = net foreign
  purchases. `source_file` marks the publisher's 2023-02 basis break row-by-row
  (s1_globl.txt / oilexp_sdata = Form S; slt_table3.txt = expanded Form SLT).

## Integrity anchor — Russia 2018 (read from `rdt_k3_ust.csv`, source mfhhis01.csv)

2018-01: 96.9 · 2018-02: 93.8 · **2018-03: 96.1 · 2018-04: 48.7 · 2018-05: 14.9** · 2018-06: 14.9 · 2018-12: 13.2 (USD billions)

REPLICATED: ~$96B → ~$15B between March and May 2018. Corroborated in the independent
slt3d_globl.csv vintage: 96.050 / 48.724 / 14.905. Same-months Form S net long-term Treasury
transactions (rdt_k3_transactions.csv): 2018-04 −20.472, 2018-05 −14.155 — the transactions leg
accounts for only part of the holdings drop; the data attribute the remainder to short-term bills
and non-transaction effects.
SOURCE: mfhhis01.csv, slt3d_globl.csv, s1_globl.txt (URLs above, fetched 2026-07-01).

## Publisher methodology facts used (each read from the fetched Securities (B)/(A) pages, 2026-07-01)

1. Table 3 "Holdings" columns go back to 2020-01 with **no break at 2023-02**; holdings 2011-2019 are in slt3d_globl.csv. SOURCE: tic_secb_page.html.
2. Table 3 "Net U.S. Sales" and "Valuation Change" **break at 2023-02**: before it, transactions came from the discontinued Form S; after, from the expanded Form SLT. "There were no valuation change data before the series-break at 2023-02." Verified in the data: those columns are n.a. for all pre-2023-02 rows. SOURCE: tic_secb_page.html; slt_table3.txt.
3. MFH-history file shows the MFH tables back to March 2000. SOURCE: tic_secb_page.html; verified in mfhhis01.csv (26 yearly blocks, 2000→2025).
4. Notice (5-16-2016): MFH aggregates discontinued — "Asian Oil Exporters (… Saudi Arabia …)" etc.; covered countries shown separately thereafter; one-time historical tables published. Verified in the data: Saudi named line in mfhhis01.csv starts 2012-01; named Saudi column 1974-12..2016-03 in oilexp_hist_to2016mar.csv. SOURCE: tic_secb_page.html; both files.
5. Notice (8-15-2013): from that release the MFH table is based on Form SLT holdings for all months. SOURCE: tic_secb_page.html.
6. Custody caveat printed on Table 5 itself: data come from U.S.-based custodians; overseas-custody holdings may not be attributed to actual owners (TIC FAQ #7). SOURCE: slt_table5.txt notes block.
7. Latest published month 2026-04 in both slt_table5.txt and slt_table3.txt (fetched 2026-07-01). SOURCE: those files.

## Cross-checks performed (values read from built csv vs fetched publisher tables)

- 2026-04 vs slt_table5.txt: China 651.072 vs 651.1; Belgium 459.890 vs 459.9; Luxembourg 431.128 vs 431.1; India 181.008 vs 181.0; Saudi Arabia 140.120 vs 140.1 — all match (Table 5 is rounded to 0.1).
- 2023-01 vs frozen mfh.txt: Belgium 331.1, Poland 40.9, India 232.0 match exactly; China 859.3 vs 859.4 (0.1 revision between the frozen snapshot and the revised MFH history — mfhhis01 kept).
- mfhhis01 vs slt3d_globl over 871 overlapping cells: mean abs diff 0.03 busd; only two cells differ by >1 busd (Belgium 2022-11: 334.4 vs 332.864; Belgium 2022-12: 351.2 vs 354.325 — frozen vintage vs later revision; mfhhis01 kept).
- mfhhis01 vs slt_table3 over 360 overlapping cells: max abs diff 0.05 busd.
- China, Mainland 2016 annual net purchases (sum of built monthly Form S rows): −155.2 busd.

## NOT-AVAILABLE (recorded honestly)

- **Poland total holdings 2026-01..2026-04**: not published anywhere inspected — Table 3/slt3d Poland total and short-term columns are n.a. from 2015-01 onward (only long-term published there); Poland is not in Table 5's top-20; mfhhis01 ends 2025-12. Poland's positions series therefore ends 2025-12. Long-term-only Poland values for 2026 months exist in the retained slt_table3.txt (`for_lt_treas_pos`, e.g. 2026-04: 56,221 M) and were not mixed into the total series.
- **By-country valuation change before 2023-02**: publisher states none exist. The pre-2023 active-vs-valuation split must be bounded (transactions vs holdings change), exactly the BOUNDED case the pre-registration provides for. From 2023-02 the split is direct: slt_table3.txt carries monthly by-country Net U.S. Sales and Valuation Change for long-term Treasuries (retained raw; not in the fixed-schema csv).
- **Saudi Arabia named-line data before 2011-09/2012-01** in the merged holdings panel: kept out of `rdt_k3_ust.csv` (the 1974-12..2016-03 one-time table is retained separately as oilexp_hist_to2016mar.csv; merging a one-time table into the MFH panel was not needed for the ≥2013 requirement).
