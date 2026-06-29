#!/usr/bin/env python3
# RESOLUTION TEST A -- make the 2020->2025 vintage leap DECIDABLE.
#
# STEP 1: full f path 2007..2020 (per year) for the HOLDINGS-side methodologies,
#         using ONLY the two on-disk GCAP CSVs (numerator CHN-share rows + denominator
#         Position_Residency pool weights). Report which years are covered by the
#         denominator file; do NOT fabricate missing-year denominators.
# STEP 2: break-even f* -- rebuild the DP4 15x2 [v_F3|v_F4] operator from dp4_inputs.json,
#         sweep f at the WORST confound corner s_usd=1.0, solve margin(f,1.0)=tau=0.10.
# STEP 3 is grounded separately (web) and merged into the JSON by hand.
#
# READ-ONLY on prior artifacts. Writes ONLY build/audit/vintage_test_compute.json
# (the verdict file vintage_test.json is assembled after grounding step 3).

import json, csv
import numpy as np

ROOT = "/home/user/dollar-breaking-point"

# matrix asset-class code -> RBEP asset-class code (same map as f_pin_recompute_check.py)
MATAC = {2: "BSF", 3: "E", 4: "BC", 5: "BG"}
METH_MAP = {1: "Enhanced Fund Holdings", 2: "Fund Holdings"}  # holdings-side only; 3=Issuance excluded
POOL = ["CYM", "HKG", "VGB"]

def fnum(x):
    try: return float(x)
    except: return 0.0

# ---- load numerator CHN-share rows ----
share = {}
with open(f"{ROOT}/build/data/gcap_usa_haven_to_chn_matrix.csv") as fh:
    for r in csv.DictReader(fh):
        mname = METH_MAP.get(int(r["Methodology"]))
        if mname is None:
            continue
        acc = MATAC.get(int(r["Asset_Class"]))
        if acc is None:
            continue
        share[(mname, int(r["Year"]), r["Destination"], acc)] = float(r["Value"])

# ---- load denominator Position_Residency weights ----
weight = {}
den_years = set()
with open(f"{ROOT}/build/data/gcap_usa_haven_pool_denominators.csv") as fh:
    for r in csv.DictReader(fh):
        weight[(r["Methodology"], int(r["Year"]), r["Issuer"], r["Asset_Class_Code"])] = \
            fnum(r["Position_Residency_usd_mn"])
        if r["Issuer"] in POOL:
            den_years.add(int(r["Year"]))

# ---- STEP 1: full f path per methodology per year ----
def f_for(mname, year):
    denom = 0.0; numer = 0.0; hit = False
    for (m, y, iss, acc), w in weight.items():
        if m == mname and y == year and iss in POOL:
            hit = True
            denom += w
            s = share.get((mname, year, iss, acc), 0.0)
            numer += w * s
    if not hit or denom <= 0:
        return None
    return numer / denom

ALL_YEARS = list(range(2007, 2021))
f_path = {}            # methodology -> {year: f}
for mname in ["Fund Holdings", "Enhanced Fund Holdings"]:
    f_path[mname] = {}
    for y in ALL_YEARS:
        fv = f_for(mname, y)
        if fv is not None:
            f_path[mname][y] = round(fv, 4)

years_covered = sorted(den_years)

def vol_stats(series_by_year):
    ys = sorted(series_by_year)
    vals = [series_by_year[y] for y in ys]
    diffs = [abs(vals[i+1]-vals[i]) for i in range(len(vals)-1)]
    # trend via OLS slope on year index
    x = np.array(ys, dtype=float); yv = np.array(vals, dtype=float)
    slope = float(np.polyfit(x, yv, 1)[0]) if len(x) >= 2 else 0.0
    return {
        "mean_abs_annual_change": round(float(np.mean(diffs)), 4) if diffs else None,
        "max_abs_annual_change": round(float(np.max(diffs)), 4) if diffs else None,
        "min_f": round(min(vals), 4),
        "max_f": round(max(vals), 4),
        "ols_slope_per_year": round(slope, 5),
        "trend": ("rising" if slope > 0.005 else ("falling" if slope < -0.005 else "flat")),
    }

stats = {m: vol_stats(f_path[m]) for m in f_path}

# ---- STEP 2: break-even f* at worst confound s_usd=1.0 ----
INP = json.load(open(f"{ROOT}/build/results/dp4_inputs.json"))
DESTn = np.array(INP["operator_recipe"]["destination_line_direction_DESTn"], dtype=float)
USAn  = np.array(INP["operator_recipe"]["usa_common_direction_USAn"], dtype=float)
TAU   = INP["operator_recipe"]["threshold_tau"]

def footprints(f, s):
    a3 = (f + (1.0 - f) * s) * DESTn
    a4 = ((1.0 - f) * s) * DESTn
    b  = -USAn
    return np.concatenate([a3, b]), np.concatenate([a4, b])

def margin_at(f, s):
    vF3, vF4 = footprints(f, s)
    M = np.column_stack([vF3, vF4])
    nn = np.linalg.norm(M, axis=0)
    nn = np.where(nn > 0, nn, 1.0)
    S = np.linalg.svd(M / nn, compute_uv=False)
    return float(S[1])

# sanity: reproduce published anchors
sanity = {
    "f0.2_s1.0": round(margin_at(0.2, 1.0), 6),   # published 0.078207  (< tau)
    "f0.6_s1.0": round(margin_at(0.6, 1.0), 6),   # published 0.284350
    "f0.49_s1.0": round(margin_at(0.49, 1.0), 6), # ~0.220 (> tau)
}

# margin(f,1.0) is monotone increasing in f over [0.2,0.49] (0.078 -> 0.220);
# solve margin(f,1.0)=tau by bisection on s_usd=1.0 corner.
def g(f): return margin_at(f, 1.0) - TAU
lo, hi = 0.0, 0.49
assert g(lo) < 0 and g(hi) > 0, (g(lo), g(hi))
for _ in range(100):
    mid = 0.5*(lo+hi)
    if g(mid) < 0: lo = mid
    else: hi = mid
f_star = 0.5*(lo+hi)

# also report f* across full s_usd hole (the worst corner is s=1.0; confirm it is the binding one)
# find, over s in [0,1], the f* that maxes (i.e. the hardest s_usd). Sweep s, solve f* each.
fstar_by_s = {}
for sv in [0.0, 0.25, 0.5, 0.75, 1.0]:
    def gs(f): return margin_at(f, sv) - TAU
    if gs(0.0) >= 0:
        fstar_by_s[sv] = 0.0   # clears tau even at f=0
        continue
    a, b = 0.0, 1.0
    if gs(b) < 0:
        fstar_by_s[sv] = None   # never clears on [0,1]
        continue
    for _ in range(100):
        m = 0.5*(a+b)
        if gs(m) < 0: a = m
        else: b = m
    fstar_by_s[sv] = round(0.5*(a+b), 5)

# worst-corner f* is the maximum over s of fstar_by_s (the f you need to clear the HARDEST s_usd)
fstar_worst = max(v for v in fstar_by_s.values() if v is not None)

# ---- distance of 2020 f from f* ----
# primary basis: Fund Holdings (matrix-comparable, ABS-inclusive, the conservative low floor)
f_2020_FH  = f_path["Fund Holdings"].get(2020)
f_2020_EFH = f_path["Enhanced Fund Holdings"].get(2020)
# the pinned FLOOR used by f_pin_test is FH 2019 = 0.489; report distance of the 2020 floor and the pinned floor
f_2019_FH  = f_path["Fund Holdings"].get(2019)

dist_2020_FH  = round(f_2020_FH  - f_star, 4)
dist_2019_FH  = round(f_2019_FH  - f_star, 4)
dist_2020_EFH = round(f_2020_EFH - f_star, 4)

out = {
    "verifier": "vintage_test_compute",
    "generated": "2026-06-29",
    "reads_only": [
        "build/data/gcap_usa_haven_to_chn_matrix.csv",
        "build/data/gcap_usa_haven_pool_denominators.csv",
        "build/results/dp4_inputs.json",
    ],
    "step1_f_path": {
        "f_path_Fund_Holdings_matrix_comparable": f_path["Fund Holdings"],
        "f_path_Enhanced_Fund_Holdings": f_path["Enhanced Fund Holdings"],
        "years_covered_by_denominator_file": years_covered,
        "denominator_covers_all_2007_2020": years_covered == ALL_YEARS,
        "volatility_Fund_Holdings": stats["Fund Holdings"],
        "volatility_Enhanced_Fund_Holdings": stats["Enhanced Fund Holdings"],
    },
    "step2_break_even": {
        "tau": TAU,
        "worst_confound_corner": "s_usd=1.0",
        "sanity_published_anchors": sanity,
        "f_star_at_s_usd_1.0": round(f_star, 5),
        "f_star_by_s_usd": fstar_by_s,
        "f_star_worst_over_s_usd_hole": round(fstar_worst, 5),
        "note": "f_star is the f at which the column-normalised [v_F3|v_F4] separation margin falls to tau=0.10. The worst confound (largest f_star required) is at s_usd=1.0.",
    },
    "step3_distance": {
        "primary_basis": "Fund Holdings (ABS-inclusive, matrix-comparable, conservative low floor)",
        "f_2020_Fund_Holdings": f_2020_FH,
        "f_2019_Fund_Holdings_pinned_floor": f_2019_FH,
        "f_2020_Enhanced_Fund_Holdings": f_2020_EFH,
        "distance_2020_FH_from_f_star": dist_2020_FH,
        "distance_2019_FH_pinned_floor_from_f_star": dist_2019_FH,
        "distance_2020_EFH_from_f_star": dist_2020_EFH,
    },
}
json.dump(out, open(f"{ROOT}/build/audit/vintage_test_compute.json", "w"), indent=1)

print("=== STEP 1: f path (Fund Holdings, matrix-comparable) ===")
for y in sorted(f_path["Fund Holdings"]):
    print(f"  {y}: {f_path['Fund Holdings'][y]:.4f}")
print(f"  years covered by denominator file: {years_covered}")
print(f"  FH volatility: {stats['Fund Holdings']}")
print(f"  EFH volatility: {stats['Enhanced Fund Holdings']}")
print("=== STEP 2: break-even f* ===")
print(f"  sanity: {sanity}")
print(f"  f* at s_usd=1.0 = {f_star:.5f}")
print(f"  f* by s_usd     = {fstar_by_s}")
print(f"  f* worst over hole = {fstar_worst:.5f}")
print("=== STEP 3: distances ===")
print(f"  f_2020 FH = {f_2020_FH}  -> distance to f* = {dist_2020_FH}")
print(f"  f_2019 FH (pinned floor) = {f_2019_FH} -> distance = {dist_2019_FH}")
print(f"  f_2020 EFH = {f_2020_EFH} -> distance = {dist_2020_EFH}")
