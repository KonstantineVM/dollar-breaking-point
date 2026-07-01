# Active-Flow Panel — Provenance (ACTIVE-FLOW F3 TEST, Part 1)
SOURCE: Real SEC Form N-PORT dissemination ZIPs, `https://www.sec.gov/files/dera/data/form-n-port-data-sets/{YYYYqQ}_nport.zip`, UA `dollar-breaking-point research milevsky@hotmail.com`, streamed and DELETED per quarter. Fiscal = zip minus one quarter (SEC dissemination rule).
## Branch
**A — constant-price decomposition, direct.** Part-0 feasibility (`build/audit/active_flow_feasibility.json`) measured BALANCE populated and positive for 99.97% of haven-CN currency_value across the tested quarters (fiscal 2022q1 crisis quarter + 2021q3); implied price = currency_value/balance finite and positive on the same share. No valuation-strip (branch B) dependency was needed.
## Method
Per fund (`cik|series_id`) per security (`cusip`, `isin` fallback) across CONSECUTIVE fiscal quarters, over the fund's CN-NATIONALITY haven holdings:
- `price_t = currency_value_t / balance_t` (require `balance>0`).
- CONTINUING: **`active = (bal_t - bal_{t-1})·price_{t-1}`** — the manager DECISION valued at the beginning-of-period (constant) price, exactly per spec. **`passive = Δcurrency_value − active`** — the pure valuation term `bal_{t-1}·(price_t − price_{t-1})` PLUS the quantity×price cross term `(bal_t − bal_{t-1})·(price_t − price_{t-1})`. The spec's two-term split leaves that cross term unassigned; folding it into `passive` (a) keeps `active` the pure constant-price flow the spec defines, and (b) makes `active + passive` reconstruct `Δcurrency_value` EXACTLY (no residual). This choice is the load-bearing correctness fix — the naive two-term form does NOT reconstruct Δcurrency_value (it drops the cross term, giving errors up to ~$2.5B on large quantity+price moves).
- NEW (not held t-1): `active = currency_value_t`, `passive = 0`.
- CLOSED (held t-1, absent t): `active = -currency_value_{t-1}`, `passive = 0`.
By construction `active + passive = Δcurrency_value` for every continuing/new/closed row (verified below to floating precision).
- SECURITY KEY: placeholder CUSIP sentinels (`000000000`, `N/A`, all-zeros, wrong length) are NULLED before keying — they are not a security identity and would spuriously pool distinct instruments into one blended-price bucket; such rows fall back to ISIN, else drop (value share reported).
Duplicate (fund, security, quarter) lots summed on currency_value and balance before pricing, so `price` is the lot-weighted average price.
NORMALIZE: `active_flow_rate = cn_active_flow / tot_haven_lag`, the fund's lagged total-haven currency_value (consecutive-quarter lag only). Raw `cn_active_flow` and `cn_passive` retained for audit.
## Tagging reused VERBATIM
R1-R4 imported from `tag_fullpanel.py` (`build_rule_sets`, `tag_rows`) — same frozen identifier sets, same crosswalk source files, R1 resolved against the same 8-quarter resolution panel. Frozen set sizes: {"hf_isin": 301, "hf_cusip6": 180, "hf_lei": 108, "r2_isin": 29, "r2_cusip6": 8, "r2_lei": 3, "r3_isin": 22, "r3_cusip6": 5, "r3_lei": 2, "qcc_cn_leis": 155}.
Haven row set + CN row set + CN currency_value reproduce the committed `panel_crosswalk_tagged_full.parquet` per fiscal quarter: **all_match = True** (only balance/unit added).
## Correctness gate (reconstruction error)
- rows checked: 203110
- max abs error: 5.960464e-08 USD
- value-weighted mean abs error: 5.172728e-11 USD
- max relative error: 6.829e-14
- **gate pass: True** — active+passive reconstructs Δcurrency_value to floating precision.
## Non-decomposable / dropped (value shares)
- dropped, no security key: 266514227.01 USD
- continuing but non-decomposable (balance ≤0/na one side), treated as active-fallback = ΔCV: 1093482706.25 USD (0.0548% of CN value)
- closed-position events synthesized: 25592
## Caveats (recorded honestly)
- SPLITS / ADR-ratio changes shift `balance` at constant economic value and are therefore booked as ACTIVE flow — a contamination source; not corrected here.
- Mixed UNIT types (NS number-of-shares vs PA principal-amount) coexist; the decomposition is in USD (value) terms so aggregation is valid, but `price` for PA rows is price-per-unit-principal, not per-share — interpret the per-security price accordingly.
- Non-decomposable rows (null/≤0 balance) fall back to active=ΔCV, passive=0; their value share is reported above and is small.
## Per-quarter active-flow row counts
| fiscal | n_fund_quarters | Σ cn_active_flow | Σ cn_passive |
|--------|-----------------|------------------|--------------|
| 2019q3 | 1409 | 6.491e+10 | 0.000e+00 |
| 2019q4 | 1765 | 2.735e+10 | 9.630e+09 |
| 2020q1 | 1868 | -8.749e+09 | -1.572e+09 |
| 2020q2 | 2028 | -2.587e+09 | 9.006e+09 |
| 2020q3 | 1998 | 1.094e+10 | 1.148e+10 |
| 2020q4 | 2019 | -1.549e+10 | -5.910e+09 |
| 2021q1 | 2010 | 5.023e+10 | -1.923e+10 |
| 2021q2 | 1947 | -2.646e+09 | -1.967e+10 |
| 2021q3 | 1860 | 1.505e+10 | -1.743e+10 |
| 2021q4 | 1754 | -2.904e+10 | -1.115e+10 |
| 2022q1 | 1676 | 5.823e+10 | -1.054e+10 |
| 2022q2 | 1651 | -2.149e+10 | -4.133e+09 |
| 2022q3 | 1539 | 7.856e+08 | -1.775e+10 |
| 2022q4 | 1549 | -4.241e+09 | 1.739e+10 |
| 2023q1 | 1528 | 1.207e+10 | -4.154e+09 |
| 2023q2 | 1541 | -4.402e+09 | 9.980e+08 |
| 2023q3 | 1451 | -2.275e+09 | -5.751e+09 |
| 2023q4 | 1409 | -2.963e+10 | -1.880e+09 |
| 2024q1 | 1370 | 4.882e+10 | -4.489e+08 |
| 2024q2 | 1377 | -2.011e+10 | 8.874e+08 |
| 2024q3 | 1391 | -2.156e+08 | 1.102e+10 |
| 2024q4 | 1407 | -3.048e+09 | -1.205e+09 |
## Active flow vs pure weight change (did the decomposition do something?)
gap = active_rate − ΔCV_rate = −passive_rate. ΔCV_rate is the weight-change-scale quantity a naive F3 regression would use.
- corr(active_rate, ΔCV_rate), all fund-quarters = 0.99996; excluding the trivial first quarter (2019q3 all-NEW, where active≡ΔCV by construction) = 0.99996. High because dominated by many small-move quarters; the separation is in the tail.
- mean |gap| = 0.0995, p95 |gap| = 0.2211.
- **2678 fund-quarters have ACTIVE flow and weight-change of OPPOSITE sign** (with |ΔCV_rate|>0.05): the manager was buying while the position's value fell (valuation loss exceeded the purchase), or vice versa. A weight-change regression misreads these as the opposite manager decision — this is exactly the conflation the active-flow quantity removes, and the concrete evidence the decomposition is not a relabeling of weight change.
- passive materially moves the value change (|gap|>0.02) in 45.0% of continuing fund-quarters.
