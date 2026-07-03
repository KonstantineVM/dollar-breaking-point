#!/usr/bin/env python3
"""
TEST 1 -- TRANSFORM ROBUSTNESS (read-only ratification).

Recompute the WITHIN-HOLDER co-movement sign between:
   US-leg          = F4[h] (foreign holder h's holdings OF US LT securities, Table 1)
   offshore-exposure = F3[h] (US holdings OF h's LT securities, Table 2)
for h in {CYM,HKG,VGB}, pooled and per-haven, under FIVE defensible flow transforms:

  (a) demeaned month-over-month LOG-CHANGE  -- the verdict's transform.
      Must reproduce pooled +0.362091; per-haven CYM +0.606213 / HKG +0.285294 / VGB +0.407876.
  (b) simple month-over-month CHANGE (level difference) -- confirm pooled +0.552738.
  (c) QUARTER-over-QUARTER log-change (resample to quarter-end, then log-change) -- slower cadence.
  (d) YoY 12-month log-change -- deseasonalize.
  (e) growth relative to each holder's OWN trailing 12-month mean (scale-free reallocation share).

Every number is computed from slt_haven_extract.json ALONE.
The pooling convention exactly reproduces the verdict script:
  per-haven series transformed, then DEMEANED per-haven before pooling.
"""
import json, math, os

ROOT = "/home/user/dollar-breaking-point"
with open(os.path.join(ROOT, "build/data/treasury_tic/current/slt_haven_extract.json")) as f:
    HAV = json.load(f)

F3 = HAV["F3_us_holdings_of_foreign_table2"]   # US holdings OF h  (offshore-exposure)
F4 = HAV["F4_foreign_holdings_of_us_table1"]   # h's holdings OF US (US-leg)
HAVENS = ["CYM", "HKG", "VGB"]

dates_ref = [r["date"] for r in F3["CYM"]["series"]]
for c in HAVENS:
    assert [r["date"] for r in F3[c]["series"]] == dates_ref
    assert [r["date"] for r in F4[c]["series"]] == dates_ref
N = len(dates_ref)

def vals(block, c):
    return [float(r["total_holdings"]) for r in block[c]["series"]]

def demean(x):
    if not x: return x
    m = sum(x)/len(x); return [xi - m for xi in x]

def corr(x, y):
    x = demean(x); y = demean(y)
    sx = math.sqrt(sum(xi*xi for xi in x)); sy = math.sqrt(sum(yi*yi for yi in y))
    if sx == 0 or sy == 0: return float("nan")
    return sum(xi*yi for xi, yi in zip(x, y))/(sx*sy)

# ---- transforms -----------------------------------------------------------
def logdiff(v, lag=1):
    return [math.log(v[i]) - math.log(v[i-lag]) for i in range(lag, len(v))]

def diff(v, lag=1):
    return [v[i] - v[i-lag] for i in range(lag, len(v))]

def to_quarterly(v, dates):
    """Resample to quarter-end levels (take the value at the last month of each quarter)."""
    q = {}
    order = []
    for d, x in zip(dates, v):
        yr, mo = d.split("-")
        qtr = (int(mo) - 1)//3 + 1
        key = (int(yr), qtr)
        if key not in q:
            order.append(key)
        q[key] = x   # last month in quarter wins (quarter-end level)
    return [q[k] for k in order], order

def trailing_mean_ratio(v, window=12):
    """growth relative to own trailing `window`-month mean: v_t / mean(v[t-window..t-1]) - 1.
    Starts at index `window` so the trailing mean is fully populated."""
    out = []
    for i in range(window, len(v)):
        tm = sum(v[i-window:i]) / window
        out.append(v[i]/tm - 1.0 if tm != 0 else float("nan"))
    return out

# ---- generic within-holder pooled+per-haven correlation -------------------
def within_holder(transform_fn):
    per = {}
    px, py = [], []
    n_used = {}
    for c in HAVENS:
        x = transform_fn(vals(F4, c))
        y = transform_fn(vals(F3, c))
        L = min(len(x), len(y))
        x, y = x[:L], y[:L]
        per[c] = corr(x, y)
        n_used[c] = L
        px += demean(x); py += demean(y)   # demean per-haven before pooling (verdict convention)
    pooled = corr(px, py)
    return per, pooled, n_used

# (a) demeaned MoM log-change
a_per, a_pooled, a_n = within_holder(lambda v: logdiff(v, 1))
# (b) simple MoM change
b_per, b_pooled, b_n = within_holder(lambda v: diff(v, 1))
# (c) QoQ log-change on quarterly-resampled levels
def qoq(v):
    qv, _ = to_quarterly(v, dates_ref)
    return logdiff(qv, 1)
c_per, c_pooled, c_n = within_holder(qoq)
# (d) YoY (12-month) log-change
d_per, d_pooled, d_n = within_holder(lambda v: logdiff(v, 12))
# (e) growth vs own trailing 12-month mean
e_per, e_pooled, e_n = within_holder(lambda v: trailing_mean_ratio(v, 12))

def r6(x): return round(x, 6)

def sgn(x):
    if x != x: return "nan"
    return "POSITIVE" if x > 0 else ("NEGATIVE" if x < 0 else "ZERO")

panels = {
  "a_demeaned_MoM_logchange": {"justification": "the verdict's principled transform; substitution is a flow/change concept",
        "pooled": r6(a_pooled), "pooled_sign": sgn(a_pooled),
        "per_haven": {c: r6(a_per[c]) for c in HAVENS},
        "per_haven_sign": {c: sgn(a_per[c]) for c in HAVENS},
        "n_per_haven": a_n,
        "anchor_target": {"pooled": 0.362091, "CYM": 0.606213, "HKG": 0.285294, "VGB": 0.407876}},
  "b_simple_MoM_change": {"justification": "level difference; symmetric robustness against log distortion",
        "pooled": r6(b_pooled), "pooled_sign": sgn(b_pooled),
        "per_haven": {c: r6(b_per[c]) for c in HAVENS},
        "per_haven_sign": {c: sgn(b_per[c]) for c in HAVENS},
        "n_per_haven": b_n,
        "anchor_target": {"pooled": 0.552738}},
  "c_QoQ_logchange": {"justification": "slower cadence -- substitution may operate quarterly not monthly; resample to quarter-end level then log-change",
        "pooled": r6(c_pooled), "pooled_sign": sgn(c_pooled),
        "per_haven": {c: r6(c_per[c]) for c in HAVENS},
        "per_haven_sign": {c: sgn(c_per[c]) for c in HAVENS},
        "n_per_haven": c_n},
  "d_YoY_logchange": {"justification": "12-month log-change removes residual seasonality",
        "pooled": r6(d_pooled), "pooled_sign": sgn(d_pooled),
        "per_haven": {c: r6(d_per[c]) for c in HAVENS},
        "per_haven_sign": {c: sgn(d_per[c]) for c in HAVENS},
        "n_per_haven": d_n},
  "e_growth_vs_own_trailing12m_mean": {"justification": "scale-free reallocation share vs each holder's own trailing 12-month mean (window=12 chosen to match TIC annual cycle and YoY panel)",
        "pooled": r6(e_pooled), "pooled_sign": sgn(e_pooled),
        "per_haven": {c: r6(e_per[c]) for c in HAVENS},
        "per_haven_sign": {c: sgn(e_per[c]) for c in HAVENS},
        "n_per_haven": e_n,
        "trailing_window_months": 12},
}

pooled_signs = [a_pooled, b_pooled, c_pooled, d_pooled, e_pooled]
all_positive = all(s > 0 for s in pooled_signs)
any_negative = any(s < 0 for s in pooled_signs)

out = {
  "test": "TEST 1 -- transform robustness of the within-holder US-leg(F4) vs offshore-exposure(F3) co-movement sign",
  "panels": panels,
  "five_pooled_signs": {
     "a_logchange": r6(a_pooled), "b_change": r6(b_pooled),
     "c_QoQ": r6(c_pooled), "d_YoY": r6(d_pooled), "e_trailing_mean": r6(e_pooled)},
  "all_five_pooled_positive": all_positive,
  "any_pooled_negative": any_negative,
}
print(json.dumps(out, indent=2))
