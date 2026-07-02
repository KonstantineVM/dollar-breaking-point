# RDT_coordinates.parquet — Provenance (RDT Part 1(d), coordinates assembly)

Assembled 2026-07-02 from disk only (no network), per the pre-registered design in
`build/reserve/RDT_prediction.md`. This file stores **coordinates and inputs only** — no
distance, velocity, ordering, or composite is computed here. Any number derived from these
rows is an estimation OUTPUT and is **NOT ESTABLISHED** until `RDT_recompute.py` runs and
`RDT_verify.json` exists.

Schema (LONG format, 793 rows): `holder, coordinate, year, value, value_lower, value_upper,
observability ∈ {OBSERVED, INFERRED-BOUNDED, NOT-AVAILABLE}, vintage, source`.
Holders: Russia, China, India, Turkey, SaudiArabia, Poland + pseudo-holders `_AGG_COFER`,
`_LMW_PCTL`, `_PREF`, `_SAFE_ANCHOR`. NOT-AVAILABLE rows carry NaN values (a recorded gap,
never a substituted number). Every row's `source` field carries its own full provenance;
this document summarizes and adds the construction notes.

## SOURCE lines (carried from the grounding provenances; all read-only from disk)

- SOURCE: `build/reserve/rdt_k2_gold.csv` (+ `rdt_k2_manifest.json`, `rdt_k2_provenance.md`) —
  gold tonnes: WGC Central Banks Dashboard v11 API (republishes IMF IFS official gold
  holdings), quarterly, Q4 = year-end, fetched 2026-07-01, HTTP 200, raw retained
  `rdt_evidence/gold_history/cbd_quarterly_2000_2026.json`; denominators: World Bank API
  FI.RES.TOTL.CD / FI.RES.XGLD.CD, fetched 2026-07-01, raw retained
  `rdt_evidence/gold_history/wb_FI_RES_TOTL_CD.json` / `wb_FI_RES_XGLD_CD.json`.
- SOURCE: `build/reserve/rdt_k3_ust.csv`, `rdt_k3_transactions.csv` (+ manifest/provenance) —
  U.S. Treasury TIC system, fetched 2026-07-01; positions merge precedence mfhhis01.csv >
  slt_table3.txt > slt3d_globl.csv; transactions from s1_globl.txt (Form S, pre-2023-02;
  Saudi 2013–2014 from oilexp_sdata_hist_2003-2014.csv) and slt_table3.txt (expanded Form
  SLT, from 2023-02); raw files retained in `rdt_evidence/tic/`; URLs and the navigation
  trail in `rdt_k3_provenance.md`.
- SOURCE: `build/reserve/rdt_k4_rmb.csv`, `rdt_k4_cofer.csv` (+ manifest/provenance) —
  PBOC RMB Internationalization Report 2025 (EN PDF, pbc.gov.cn, fetched 2026-07-01; swap
  lines); CIPS Participants Announcement No. 117 (cips.com.cn, fetched 2026-07-01; world
  aggregate only); SAFE Annual Report 2018, Box 4, printed p.35 / PDF p.44
  (safe.gov.cn, fetched 2026-07-02; China USD share 79% in 1995, 58% in 2014); IMF COFER
  via api.imf.org SDMX 2.1, dataset IMF.STA/COFER, World (G001), AFXRA, fetched 2026-07-01;
  raw files retained in `rdt_evidence/rmb/`.
- SOURCE: `build/reserve/rd0_evidence/lmw_Data.xls`, sheet DATA, pandas engine xlrd —
  LMW disclosed-reserves currency-composition panel (RD0-vetted secondary-academic source);
  64 countries, years 1996–2023 (25 of 1,077 USD cells missing, dropped from percentiles).
- SOURCE: `build/reserve/rd2_evidence/wb_pinksheet_MYFETCH.xlsx`, sheet "Monthly Prices",
  Gold ($/troy oz) column — WB Pink Sheet, committed RD2 evidence file (RD2 provenance).
- SOURCE (checked for rule-2 backfill and reconciliation echo only, READ-ONLY):
  `build/reserve/RD2_gold_panel.parquet`.

## Per-coordinate construction notes

**k1_usd_share_pct.** Russia (2007–2021), Turkey (2004–2023), Poland (2004–2022): the LMW
USD column, all disclosed years, OBSERVED, point values. India, SaudiArabia: single
NOT-AVAILABLE marker rows, source `absent-from-LMW-panel` (absence verified by scan, not
assumed). China: **INFERRED-BOUNDED only — never a point** — residual route, years
2014–2025 (each year where COFER Q4 and China's WB total reserves both exist; 2026
excluded because WB China reserves end at 2025):
`s_C = (W·A − s_NC·(A − R_C)) / R_C`, W = COFER world allocated USD share (%), A = COFER
allocated total ($bn), R_C = China WB total reserves ($bn — same units as A; unit check in
each row), s_NC ranging over the LMW discloser USD-share p10–p90 of that year (target years
2024–2025 use the latest LMW year, 2023, stated in source). `value` = midpoint-of-interval,
labelled as such — a label, not a point estimate. **The residual is weak and this is
reported, not hidden:** in all 12 years a raw endpoint falls outside [0,100] (e.g. 2025:
raw [−22.83, 153.53]); stored bounds are clipped to [0,100] and every raw endpoint is
preserved in the row source and in `rdt_assembly_manifest.json`
(`k1_china_residual_route_by_year`). China is ~28–34% of the world allocated total, so s_C
is hypersensitive to s_NC; the LMW discloser spread (p90 ≈ 88–95%) maps to an interval
wider than [0,100]. Implied non-China USD mass is positive at both endpoints in every year
(recorded per row).

**k1_usd_share_pct_safe_route (China only; kept DISTINCT — the estimation stage takes the
envelope of the two routes, per the pre-registration).** Corridor per year 2014–2026:
anchor 58 (SAFE-disclosed 2014 USD share) ± p90 of |cumulative ΔUSD share over the elapsed
horizon 2014→t| across the 54 LMW disclosers with a 2014 observation. Construction choice,
disclosed: the prediction's "anchor ± the 10th–90th percentile of |Δ USD share|" is
implemented as the conservative envelope ±p90, with p10 recorded per year in each row's
source and in the manifest. Disclosers whose panel ends before the target year contribute
their Δ over 2014→own panel end (horizon truncated; count per year in source); for target
years beyond 2023 the drift input is fully truncated at the panel end (LMW ends 2023) and
the corridor freezes at [33.88, 82.12]. `value` = 58, the corridor centre (anchor).

**k2_gold_tonnes / k2_reserves_ex_gold_usd_bn / k2_total_reserves_usd_bn.** Annual year-end
2010–2025 from `rdt_k2_gold.csv`, OBSERVED, six holders (USA anchor rows not carried — it
is not a holder). Rule-2 backfill check performed: `RD2_gold_panel.parquet` was checked for
2025 values the csv lacks — RUS 2025Q4 denominators are NaN in RD2 too, so **nothing was
backfilled** and Russia's 2025 WB denominators are NOT-AVAILABLE rows (WB series ends 2024
for RUS; recorded, not substituted). Raw tonnes are stored; the constant-price gold share
(tonnes·P_ref rule) is computed downstream from these rows plus the `_PREF` row — never
here, never at market price (RD2 Confound-2 discipline).

**k3_ust_busd.** Annual snapshot = December value from `rdt_k3_ust.csv`; 2026 = latest
published month 2026-04, vintage `2026-04`. Per-row `source_file` (mfhhis01.csv /
slt_table3.txt / slt3d_globl.csv) carried in source — Russia's named MFH line ends 2018-12
and later values come from the SLT tables, visible there. China: **custody BAND,
INFERRED-BOUNDED, never a point** — value_lower = China (mainland) alone, value_upper =
China + Belgium + Luxembourg (December values summed; Euroclear/Clearstream custody
masking, publisher's own Table-5 custody caveat), value = midpoint-of-band (label). The
band is intentionally wide — Belgium/Luxembourg custody also serves non-China clients —
and every row says so. Poland 2026: NOT-AVAILABLE (total UST not published 2026-01..04:
Table-3 total/short-term n.a. for Poland from 2015-01, not in Table-5 top-20, MFH history
ends 2025-12; long-term-only values exist in retained slt_table3.txt and were NOT mixed
in). SaudiArabia 2010: NOT-AVAILABLE (named line begins 2011-09; earlier grouped in the
discontinued Oil Exporters aggregate).

**k3_net_tx_busd.** Annual sums of monthly net purchases (long-term Treasury bonds & notes
only; bills excluded — publisher's data boundary) from `rdt_k3_transactions.csv`,
2013–2025 full years + 2026 partial (2026-01..04, marked in source and vintage). China:
band as above (China alone vs China+Belgium+Luxembourg; whichever is smaller is
value_lower, the China-alone endpoint labelled per row; lower ≤ upper verified for all
rows). **2023 rows carry the publisher-documented 2023-02 basis break** (Form S →
expanded Form SLT), marked in source; the csv's source_file column marks it row-by-row.
By-country valuation change exists only from 2023-02 (publisher states none exist before);
the pre-2023 active-vs-valuation split will be BOUNDED downstream — the series is stored
here, the split is not computed.

**k4_cny_share_pct.** LMW CNY column: Russia (2007–2021; 0 through 2016, then 3.38 →
21.78), Turkey (2004–2023) and Poland (2004–2022) are 0.0 in every year — **grounded,
OBSERVED zeros** (disclosed composition contains no CNY), not gaps. China: NOT-AVAILABLE,
source `N/A-issuer` (applicability — China is the alternative's issuer — not a data hole).
India, SaudiArabia: NOT-AVAILABLE (absent from LMW panel).

**k4_swap_line_bn_cny (flag, context — not a composite input).** Russia 150 (signed
2014-10-13; renewals 2017-11-22 and 2020-11-23 at 150 in source); Turkey 35 (signed
2012-02-21 at 10; renewed 2015 and 2019 at 12; amended 2021-06-04 to 35 — chronology in
source); SaudiArabia 50 (signed 2023-11-20); India 0 OBSERVED and Poland 0 OBSERVED —
**grounded zeros** (publisher-primary absence from the PBoC 2025 report's complete
regional enumerations; coverage through end-2024; absence, not a signed denial). China:
NOT-AVAILABLE, `N/A-issuer`.

**k4_cips_participants (flag).** NOT-AVAILABLE for all five non-China holders: the
publisher does not publish per-country counts (cips.com.cn announcements No.44/72/110/
116/117 checked EN+CN; participant tables stripped). World aggregate carried in source as
context only: 194 direct / 1,597 indirect participants, March 2026. China: `N/A-issuer`
(operator).

**Pseudo-holders (so the recompute regenerates everything from this one file).**
- `_AGG_COFER`: `usd_share_pct_allocated` and `allocated_total_usd_bn`, Q4 values
  2014–2025 + 2026-Q1 (vintage `2026-Q1`). **COFER methodology-break caveat carried in
  every row's source**: since the 2025Q3 release (revisions back to 2000Q1) the IMF
  eliminated the unallocated portion; missing values imputed by IMF staff (TNM/2025/14);
  imputed share 10.65% at 2026-Q1. Per the pre-registration's conflict resolution, COFER
  enters ONLY as the k1-China bounding input — never as country-level evidence, never as a
  freeze-response observation.
- `_LMW_PCTL`: `usd_share_p10/p25/p50/p75/p90` per year 1996–2023 across ALL LMW
  disclosers with non-missing USD share (not just the six holders); per-year n in source
  (49–56 in 2010–2022, **31 in 2023** — the thinner final cross-section is flagged in the
  manifest issues).
- `_PREF`: `gold_usd_per_oz_2021mean` = **1799.6291666666664 $/oz** (mean of the 12
  monthly 2021 values of the Pink Sheet Gold column, computed this build from the
  committed xlsx — never hardcoded downstream).
- `_SAFE_ANCHOR`: China USD share 79 (1995) and 58 (2014), OBSERVED — SAFE Annual Report
  2018, Box 4, printed p.35/PDF p.44; one-off disclosure; pairing verified by
  positioned-text extraction against the COFER-consistent global values in the same box
  (`rdt_k4_provenance.md` sec. 4).

## REALIZED applicability matrix (holder × coordinate × observability, from the parquet)

| holder | k1_usd_share_pct | k1_safe_route | k2 (3 coords) | k3_ust_busd | k3_net_tx_busd | k4_cny_share_pct | k4_swap | k4_cips |
|---|---|---|---|---|---|---|---|---|
| Russia | OBS 2007–2021 (15) | — | OBS 2010–2025; denominators OBS →2024, **N-A 2025** | OBS 2010–2026 (17) | OBS 2013–2026 (14) | OBS 2007–2021 (15) | OBS 150 (2014) | N-A |
| China | **I-B 2014–2025 (12, residual)** | **I-B 2014–2026 (13)** | OBS 2010–2025 | **I-B 2010–2026 (17, custody band)** | **I-B 2013–2026 (14, band)** | N-A (issuer) | N-A (issuer) | N-A (issuer) |
| India | N-A (absent from LMW) | — | OBS 2010–2025 | OBS 2010–2026 (17) | OBS 2013–2026 (14) | N-A (absent from LMW) | OBS 0 (grounded zero) | N-A |
| Turkey | OBS 2004–2023 (20) | — | OBS 2010–2025 | OBS 2010–2026 (17) | OBS 2013–2026 (14) | OBS 2004–2023 (20, all 0.0) | OBS 35 (2012→2021) | N-A |
| SaudiArabia | N-A (absent from LMW) | — | OBS 2010–2025 | OBS 2011–2026 (16); **N-A 2010** | OBS 2013–2026 (14) | N-A (absent from LMW) | OBS 50 (2023) | N-A |
| Poland | OBS 2004–2022 (19) | — | OBS 2010–2025 | OBS 2010–2025 (16); **N-A 2026** | OBS 2013–2026 (14) | OBS 2004–2022 (19, all 0.0) | OBS 0 (grounded zero) | N-A |

Pseudo-holders: `_AGG_COFER` OBS 2014–2026 (2×13); `_LMW_PCTL` OBS 1996–2023 (5×28);
`_PREF` OBS (1); `_SAFE_ANCHOR` OBS 1995+2014 (2).
Totals: 721 OBSERVED, 56 INFERRED-BOUNDED, 16 NOT-AVAILABLE = 793 rows.
This realizes the expected pattern in RDT_prediction.md's coordinate-applicability matrix;
the two "expected NOT-AVAILABLE (verify vs panel)" cells (India, Saudi Arabia k1) were
verified absent, and China's k1/k3 are intervals/bands everywhere, never points.

## Caveats, stated where they bind

1. **COFER 2025Q3 methodology break** (unallocated eliminated, imputation back to 2000Q1,
   TNM/2025/14, imputed share 10.65% at 2026-Q1): carried in every `_AGG_COFER` row and
   every k1-China residual row; it makes W a 100%-coverage, partially-imputed share.
   China's presence on the IMF List of COFER Reporters is grounded (fetched 2026-07-01);
   the historical phase-in timing is UNVERIFIED and is not asserted.
2. **TIC custody band** (China): publisher's own Table-5 caveat; the band is intentionally
   wide and never collapsed to a point; midpoints are labels only.
3. **2023-02 transactions basis break** (Form S → expanded Form SLT): marked in every 2023
   annual row and row-by-row in the underlying csv; by-country valuation change exists only
   from 2023-02, so the pre-2023 active-vs-valuation split must be BOUNDED downstream.
4. **k1-China residual weakness**: all 12 years clip at [0,100]; raw endpoints preserved.
   The residual route, as pre-registered, is close to uninformative on its own; the
   SAFE-anchor route provides the tighter corridor, and the estimation stage takes the
   envelope. Neither route is merged here.
5. **Anchor echoes (both REPLICATED — see `rdt_assembly_manifest.json`)**: Russia k3
   Dec-2017 102.5 → Dec-2018 13.2 $bn (monthly, quoted from the csv: 2018-03 96.1 →
   2018-04 48.7 → 2018-05 14.9); Russia k2 end-2013 1035.21 t → end-2020 2298.53 t; RD2
   overlap reconciliation: max |tonnes diff| = 0.0 for all 7 countries over 28 quarters.
6. **Read-only discipline**: mtimes of all 48 guarded input files recorded before and
   after the build — none modified.
