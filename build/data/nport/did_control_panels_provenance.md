# DiD F3 Part 0(b) — Control Panels & Pre-Trend Provenance (STREAMING build)

SOURCE: Real SEC Form N-PORT dissemination ZIPs `https://www.sec.gov/files/dera/data/form-n-port-data-sets/{YYYYqQ}_nport.zip`, UA `dollar-breaking-point research milevsky@hotmail.com`, parsed to disk in a prior pass (haven_bal_parts/, did_control_parts/). This build REUSES those on-disk parts; nothing re-downloaded or re-parsed. Fiscal quarter = zip label minus one quarter.

## Memory pattern (the fix)
The prior attempt (`build_did_control_panels.py`) concatenated all 22 quarters of raw non-haven holdings into one DataFrame before decomposing; peak RSS >13GB, killed by the memory guard before writing output. This rewrite (`build_did_control_panels_streaming.py`) streams quarter-by-quarter: each quarter is loaded, collapsed IMMEDIATELY to per-(fund,security) rows (dropping every heavy raw string column), decomposed against the single previously-collapsed quarter, aggregated to per-(fund,quarter) active flow, then the raw frame is freed (`del`+`gc.collect()`). At most TWO collapsed quarters are held at once — the first difference needs only t and t-1. **Measured peak RSS = 0.886 GB** (target < 6GB).

## Groups
- **treated**: CN-nationality haven active flow. COMMITTED `active_flow_panel.parquet` reused verbatim in the output panel; ALSO re-streamed here purely to reconcile the streaming build against it.
- **C1**: non-CN haven (CYM/HKG/VGB residence, parent!=CN). Streamed from `haven_bal_parts/` with R1-R4 tagging VERBATIM (`tag_fullpanel`), focus=parent!=CN, normalization base = total haven (identical denominator to treated).
- **C2**: non-haven EM equity, ASSET_CAT=EC, INVESTMENT_COUNTRY in ['BR', 'ID', 'IN', 'KR', 'MX', 'MY', 'PH', 'PL', 'TH', 'TR', 'TW', 'ZA']. Streamed from `did_control_parts/` (control_group=C2).
- **C3**: developed-market non-US equity, ASSET_CAT=EC, INVESTMENT_COUNTRY in ['AU', 'CA', 'CH', 'DE', 'ES', 'FR', 'GB', 'IT', 'JP', 'NL', 'SE']. Streamed (control_group=C3).

## Decomposition (reused verbatim, streamed)
Constant-price: CONTINUING active=(bal_t-bal_{t-1})*price_{t-1}, passive=dCV-active; NEW active=cv_t; CLOSED active=-cv_{t-1}. Placeholder CUSIP nulled -> ISIN fallback; duplicate lots summed before pricing. Correctness gate active+passive==dCV accumulated streaming per group (below).

## Treated-group reconciliation vs committed active_flow_panel (the sanity gate)
Streaming the CN-haven group with the total-haven denominator reproduces the committed treated rate: matched rows=36547, max_abs_rate_diff=2.220446049250313e-16, max_abs_active_flow_diff=9.5367431640625e-07, reproduces_committed=True. Streamed correctness gate: max_abs=5.960e-08, pass=True. This proves the streaming build is algebraically identical to the committed batch build.

## Pre-trend parallelism (PRE 2019q4-2021q4; rate ~ trend + treated + trend:treated, fund FE, cluster-by-fund SE)

**Outlier caveat (load-bearing):** `active_flow_rate` = active flow / lagged group total has extreme tails when the lagged denominator is tiny. On the UNTRIMMED rate these outliers inflate the cluster-robust SE so much that nothing is significant and every control reads 'parallel' (large p) -- that flatness is an SE-inflation artifact, NOT measured parallelism. The table reports the pre-registered untrimmed test AND a 1%/5%-tail-trim robustness re-run. A control is a valid control only if 'parallel' is ROBUST (holds untrimmed AND at the 1% trim).

| control | variant | coef | SE | p | parallel | gate pass | n_fq |
|---|---|---|---|---|---|---|---|
| C1 | untrimmed | -22.39 | 27.29 | 0.4118 | True | True | 90557 |
| C1 | trim_1pct | -0.004264 | 0.001262 | 0.0007327 | False |  |  |
| C1 | trim_5pct | -0.004842 | 0.0007064 | 7.681e-12 | False |  |  |
| C1 | **parallel_robust** | | | | **False** | | |
| C2 | untrimmed | 13.12 | 7.85 | 0.09467 | False | True | 46102 |
| C2 | trim_1pct | -0.005 | 0.00147 | 0.0006739 | False |  |  |
| C2 | trim_5pct | -0.006173 | 0.0007876 | 5.521e-15 | False |  |  |
| C2 | **parallel_robust** | | | | **False** | | |
| C3 | untrimmed | 125.8 | 246.3 | 0.6095 | True | True | 112202 |
| C3 | trim_1pct | -0.006678 | 0.001129 | 3.478e-09 | False |  |  |
| C3 | trim_5pct | -0.007565 | 0.0006515 | 5.958e-31 | False |  |  |
| C3 | **parallel_robust** | | | | **False** | | |

## Branch decision
{
  "decision": "NOT-IDENTIFIED",
  "note": "No candidate control has an OUTLIER-ROBUST flat pre-trend. Untrimmed, ['C1', 'C3'] read 'parallel', but this is an SE-inflation artifact of extreme-tail active_flow_rate values (tiny lagged denominators): trimming the 1% rate tails flips EVERY candidate to strongly NON-parallel (interaction p <= 0.001). The DiD is NOT identified on this quantity as normalized; a bare untrimmed 'parallel' verdict would be reporting an artifact as a result.",
  "parallel_untrimmed": [
    "C1",
    "C3"
  ],
  "outlier_flipped_to_nonparallel_when_trimmed": [
    "C1",
    "C3"
  ]
}

## Per-quarter row counts (fund-quarters with non-null rate)

**treated**: 2019q3=0, 2019q4=1430, 2020q1=1713, 2020q2=1852, 2020q3=1908, 2020q4=1846, 2021q1=1839, 2021q2=1826, 2021q3=1774, 2021q4=1627, 2022q1=1566, 2022q2=1574, 2022q3=1482, 2022q4=1444, 2023q1=1425, 2023q2=1460, 2023q3=1368, 2023q4=1271, 2024q1=1242, 2024q2=1302, 2024q3=1321, 2024q4=1276

**C1**: 2019q3=0, 2019q4=3557, 2020q1=4264, 2020q2=4219, 2020q3=4322, 2020q4=4169, 2021q1=4205, 2021q2=4418, 2021q3=4502, 2021q4=4397, 2022q1=4428, 2022q2=4459, 2022q3=4480, 2022q4=4373, 2023q1=4393, 2023q2=4459, 2023q3=4390, 2023q4=4229, 2024q1=4218, 2024q2=4386, 2024q3=4388, 2024q4=4301

**C2**: 2019q3=0, 2019q4=1699, 2020q1=1995, 2020q2=2093, 2020q3=2146, 2020q4=2072, 2021q1=2088, 2021q2=2190, 2021q3=2236, 2021q4=2197, 2022q1=2206, 2022q2=2230, 2022q3=2246, 2022q4=2212, 2023q1=2222, 2023q2=2250, 2023q3=2262, 2023q4=2190, 2024q1=2257, 2024q2=2441, 2024q3=2454, 2024q4=2416

**C3**: 2019q3=0, 2019q4=4292, 2020q1=5040, 2020q2=5291, 2020q3=5386, 2020q4=5186, 2021q1=5104, 2021q2=5283, 2021q3=5473, 2021q4=5410, 2022q1=5433, 2022q2=5548, 2022q3=5609, 2022q4=5510, 2023q1=5508, 2023q2=5587, 2023q3=5502, 2023q4=5312, 2024q1=5355, 2024q2=5502, 2024q3=5513, 2024q4=5358

