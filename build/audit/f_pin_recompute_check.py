#!/usr/bin/env python3
# FALSIFICATION TEST 5 -- end-to-end reproducibility closures.
#
# CLOSURE 1: recompute f for the US-held CYM/HKG/VGB pool from ON-DISK files ALONE:
#   numerator shares  : build/data/gcap_usa_haven_to_chn_matrix.csv  (Restatement-Matrices CHN share rows)
#   denominator weights: build/data/gcap_usa_haven_pool_denominators.csv (RBEP Position_Residency $mn)
#   f = sum_cells( Position_Residency * CHN_share ) / sum_cells( Position_Residency ).
#   Confirms f in [0.49, 0.71] across the two HOLDINGS-side methodologies / latest vintages.
#
# CLOSURE 2: rebuild the DP4 15x2 F3/F4 operator from build/results/dp4_inputs.json (same
#   construction as build/results/dp4_recompute_check.py) and evaluate the separation margin
#   at the pinned-interval corner (f=0.49, s_usd=1.0) and across a fine (f,s_usd) grid on
#   f in [0.49,0.71], s_usd in [0,1]. Records where the margin clears tau=0.10.
#
# READ-ONLY on prior artifacts. Writes ONLY build/audit/f_pin_recompute_check.json.

import json, csv
import numpy as np

ROOT = "/home/user/dollar-breaking-point"

# ---------------- CLOSURE 1: f from disk (numerator + denominator) ----------------
# matrix asset-class code (matrices) -> RBEP asset-class code
MATAC = {2: "BSF", 3: "E", 4: "BC", 5: "BG"}   # 1=AllBonds unused; 2=ABS,3=CommonEq,4=CorpBonds,5=GovBonds
METH_MAP = {1: "Enhanced Fund Holdings", 2: "Fund Holdings"}  # holdings-side only; 3=Issuance excluded

# load numerator CHN-share rows
num = []
with open(f"{ROOT}/build/data/gcap_usa_haven_to_chn_matrix.csv") as fh:
    for r in csv.DictReader(fh):
        num.append(r)

# load denominator Position_Residency weights
den = []
with open(f"{ROOT}/build/data/gcap_usa_haven_pool_denominators.csv") as fh:
    for r in csv.DictReader(fh):
        den.append(r)

def fnum(x):
    try: return float(x)
    except: return 0.0

# build CHN-share lookup: (methodology_name, year, dest, rbep_acc) -> share
share = {}
for r in num:
    mname = METH_MAP.get(int(r["Methodology"]))
    if mname is None:
        continue
    acc = MATAC.get(int(r["Asset_Class"]))
    if acc is None:
        continue
    share[(mname, int(r["Year"]), r["Destination"], acc)] = float(r["Value"])

# build denominator weights: (methodology_name, year, issuer, acc) -> position_residency
weight = {}
for r in den:
    weight[(r["Methodology"], int(r["Year"]), r["Issuer"], r["Asset_Class_Code"])] = \
        fnum(r["Position_Residency_usd_mn"])

POOL = ["CYM", "HKG", "VGB"]
f_results = {}
for mname in ["Fund Holdings", "Enhanced Fund Holdings"]:
    for year in [2019, 2020]:
        denom = 0.0
        numer = 0.0
        for (m, y, iss, acc), w in weight.items():
            if m == mname and y == year and iss in POOL:
                denom += w
                s = share.get((mname, year, iss, acc), 0.0)
                numer += w * s
        if denom > 0:
            f_results[f"{mname}|{year}"] = {
                "pool_denominator_usd_mn": round(denom, 0),
                "china_nationality_usd_mn": round(numer, 0),
                "f": round(numer / denom, 4),
            }

f_values = [v["f"] for v in f_results.values()]
f_lo, f_hi = min(f_values), max(f_values)
interval_ok = (abs(round(f_lo, 2) - 0.49) < 0.02) and (abs(round(f_hi, 2) - 0.71) < 0.02)

# ---------------- CLOSURE 2: DP4 corner margin at (f=0.49, s=1.0) ----------------
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
    return float(S[1]), float(S[0])

# sanity: reproduce two published grid values from dp4_spectrum.json convention
chk_f02_s10 = margin_at(0.2, 1.0)[0]   # published 0.07820655552050046
chk_f06_s10 = margin_at(0.6, 1.0)[0]   # published 0.28435008349206115

# the pinned-interval FLOOR corner (worst confound s_usd=1.0)
corner_lo = margin_at(f_lo, 1.0)        # f=0.49, s=1.0
corner_lo_s0 = margin_at(f_lo, 0.0)     # f=0.49, s=0.0 (best confound)
corner_hi = margin_at(f_hi, 1.0)        # f=0.71, s=1.0

# fine scan over the pinned interval x full s_usd hole
grid = []
fs = [round(f_lo + i*(f_hi-f_lo)/8, 4) for i in range(9)]
ss = [0.0, 0.25, 0.5, 0.75, 1.0]
min_margin_over_interval = (1e9, None)
for fv in fs:
    for sv in ss:
        m2, m1 = margin_at(fv, sv)
        grid.append({"f": fv, "s_usd": sv, "margin": round(m2, 6),
                     "clears_tau_0.10": bool(m2 >= TAU)})
        if m2 < min_margin_over_interval[0]:
            min_margin_over_interval = (m2, (fv, sv))

# where does the FLOOR f=0.49 cross tau as s_usd rises?
floor_scan = []
for sv in [0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0]:
    m2 = margin_at(f_lo, sv)[0]
    floor_scan.append({"f": f_lo, "s_usd": sv, "margin": round(m2, 6),
                       "clears_tau_0.10": bool(m2 >= TAU)})

# s_usd threshold below which the FLOOR f=0.49 clears tau (linear bisection)
def floor_margin(s): return margin_at(f_lo, s)[0]
lo, hi = 0.0, 1.0
if floor_margin(0.0) >= TAU and floor_margin(1.0) < TAU:
    for _ in range(60):
        mid = 0.5*(lo+hi)
        if floor_margin(mid) >= TAU: lo = mid
        else: hi = mid
    s_star_floor = round(0.5*(lo+hi), 4)
else:
    s_star_floor = None

result = {
    "verifier": "f_pin_recompute_check",
    "generated": "2026-06-29",
    "reads_only": [
        "build/data/gcap_usa_haven_to_chn_matrix.csv (numerator CHN-share rows)",
        "build/data/gcap_usa_haven_pool_denominators.csv (denominator Position_Residency weights)",
        "build/results/dp4_inputs.json (operator recipe for the corner SVD)",
    ],
    "closure_1_f_recompute_from_disk": {
        "method": "f = sum(Position_Residency * CHN_share) / sum(Position_Residency) over USA x {CYM,HKG,VGB} x asset-class, from the two on-disk CSV files ALONE.",
        "f_by_methodology_year": f_results,
        "f_interval_recomputed": [round(f_lo, 4), round(f_hi, 4)],
        "matches_pinned_interval_0.49_0.71": bool(interval_ok),
    },
    "closure_2_corner_margin": {
        "operator": "DP4 15x2 [v_F3|v_F4] rebuilt from dp4_inputs.json; smallest singular value of column-normalised operator; tau=0.10.",
        "sanity_reproduces_published_grid": {
            "f0.2_s1.0_recomputed": round(chk_f02_s10, 6),
            "f0.2_s1.0_published": 0.078207,
            "f0.6_s1.0_recomputed": round(chk_f06_s10, 6),
            "f0.6_s1.0_published": 0.284350,
        },
        "pinned_floor_corner_f0.49_s1.0": {
            "margin": round(corner_lo[0], 6),
            "clears_tau_0.10": bool(corner_lo[0] >= TAU),
        },
        "pinned_floor_f0.49_s0.0_best_confound": {
            "margin": round(corner_lo_s0[0], 6),
            "clears_tau_0.10": bool(corner_lo_s0[0] >= TAU),
        },
        "pinned_ceiling_f0.71_s1.0": {
            "margin": round(corner_hi[0], 6),
            "clears_tau_0.10": bool(corner_hi[0] >= TAU),
        },
        "min_margin_over_pinned_interval_x_full_s_usd": {
            "margin": round(min_margin_over_interval[0], 6),
            "at_f_s": min_margin_over_interval[1],
        },
        "floor_f0.49_s_usd_scan": floor_scan,
        "s_usd_threshold_below_which_floor_clears_tau": s_star_floor,
        "grid": grid,
    },
}
json.dump(result, open(f"{ROOT}/build/audit/f_pin_recompute_check.json", "w"), indent=1)

print("CLOSURE 1 -- f from disk:")
for k, v in f_results.items():
    print(f"  {k:30s} f={v['f']:.4f}  (denom {v['pool_denominator_usd_mn']:,.0f} mn)")
print(f"  interval {f_lo:.4f}..{f_hi:.4f}  matches [0.49,0.71]: {interval_ok}")
print("CLOSURE 2 -- DP4 corner margins:")
print(f"  sanity f0.2,s1.0 = {chk_f02_s10:.6f} (pub 0.078207); f0.6,s1.0 = {chk_f06_s10:.6f} (pub 0.284350)")
print(f"  CORNER f=0.49,s=1.0 margin = {corner_lo[0]:.6f}  clears tau: {corner_lo[0]>=TAU}")
print(f"  f=0.49,s=0.0 margin        = {corner_lo_s0[0]:.6f}  clears tau: {corner_lo_s0[0]>=TAU}")
print(f"  f=0.71,s=1.0 margin        = {corner_hi[0]:.6f}  clears tau: {corner_hi[0]>=TAU}")
print(f"  min over interval x s_usd  = {min_margin_over_interval[0]:.6f} at {min_margin_over_interval[1]}")
print(f"  floor f=0.49 clears tau for s_usd <= {s_star_floor}")
