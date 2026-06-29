#!/usr/bin/env python3
# DP4 VERIFIER: regenerate the singular spectrum / separation-margin surface from
# build/results/dp4_inputs.json ALONE (the persisted operator recipe + matrix quantities
# + evaluation points), then compare to build/results/dp4_spectrum.json.
#
# This reads ONLY dp4_inputs.json and dp4_spectrum.json -- NOT dp4_build_spectrum.py and
# NOT any intermediate state. It rebuilds the operator from the persisted recipe,
# recomputes the SVD at every (f, s_usd) point, and confirms:
#   (1) the regenerated margin surface matches dp4_spectrum.json (max abs deviation),
#   (2) the margin -> 0 at the f=0 edge (the F3/F4 degeneracy) reproduces.
# A spectrum not regenerable from persisted inputs is NOT established.

import json
import numpy as np

ROOT = "/home/user/dollar-breaking-point"
INP  = json.load(open(f"{ROOT}/build/results/dp4_inputs.json"))
SPEC = json.load(open(f"{ROOT}/build/results/dp4_spectrum.json"))

# --- rebuild operator pieces from the PERSISTED recipe (dp4_inputs.json only) ---
DESTn = np.array(INP["operator_recipe"]["destination_line_direction_DESTn"], dtype=float)
USAn  = np.array(INP["operator_recipe"]["usa_common_direction_USAn"], dtype=float)
TAU   = INP["operator_recipe"]["threshold_tau"]
F_POINTS = INP["evaluation_points"]["f_points"]
S_POINTS = INP["evaluation_points"]["usd_share_points"]

# Sanity: rebuild DESTn / USAn independently from the persisted matrix quantities and confirm
# they match the persisted directions (so the recipe is consistent with the raw cell values).
mq = INP["matrix_quantities_usd_mn"]
dest_vals = np.array([mq["offshore_pool_destination_cells"]["US->CYM"],
                      mq["offshore_pool_destination_cells"]["US->HKG"],
                      mq["offshore_pool_destination_cells"]["US->VGB"]], dtype=float)
usa_vals  = np.array(list(mq["usa_issuer_column_by_holder"].values()), dtype=float)
DESTn_chk = dest_vals / np.linalg.norm(dest_vals)
USAn_chk  = usa_vals  / np.linalg.norm(usa_vals)
dir_dev = max(float(np.max(np.abs(DESTn - DESTn_chk))), float(np.max(np.abs(USAn - USAn_chk))))

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

# --- recompute surface and compare to persisted dp4_spectrum.json grid ---
persisted_grid = {(round(r["f"], 6), round(r["usd_share"], 6)):
                  r["smallest_singular_value_separation_margin"]
                  for r in SPEC["separation_margin_surface"]["grid"]}

max_margin_dev = 0.0
recomputed = []
for f in F_POINTS:
    for s in S_POINTS:
        m2, m1 = margin_at(f, s)
        key = (round(f, 6), round(s, 6))
        dev = abs(m2 - persisted_grid[key])
        max_margin_dev = max(max_margin_dev, dev)
        recomputed.append({"f": f, "usd_share": s,
                           "recomputed_margin": m2,
                           "persisted_margin": persisted_grid[key],
                           "abs_dev": dev})

# --- degeneracy check: margin == 0 along the f=0 edge for ALL s_usd ---
f0_margins = [margin_at(0.0, s)[0] for s in S_POINTS]
degeneracy_reproduces = all(abs(x) < 1e-9 for x in f0_margins)

TOL = 1e-9
match = (max_margin_dev < TOL) and (dir_dev < 1e-9) and degeneracy_reproduces
passed = bool(match)

result = {
    "verifier": "dp4_recompute_check",
    "reads_only": ["build/results/dp4_inputs.json", "build/results/dp4_spectrum.json"],
    "passed": passed,
    "max_abs_margin_deviation_recomputed_vs_persisted": max_margin_dev,
    "direction_vectors_consistent_with_raw_cells_max_dev": dir_dev,
    "f0_edge_margins_recomputed": f0_margins,
    "degeneracy_margin_zero_at_f0_reproduces": degeneracy_reproduces,
    "tolerance": TOL,
    "n_points_checked": len(recomputed),
    "per_point": recomputed,
    "note": "Regenerated the 15x2 F3/F4 identification operator from dp4_inputs.json ALONE, recomputed the SVD at every (f,s_usd) point, and matched the persisted dp4_spectrum.json margin surface. The margin is exactly 0 along the f=0 edge for ALL s_usd (the F3/F4 degeneracy, DP3 form (b)). Still an OUTPUT -- NOT ESTABLISHED until the DP5 verifier artifact exists.",
}
json.dump(result, open(f"{ROOT}/build/results/dp4_recompute_check.json", "w"), indent=1)

print("DP4 recompute check")
print(f"  max abs margin deviation (recomputed vs persisted) = {max_margin_dev:.3e}")
print(f"  direction vectors vs raw cells max dev             = {dir_dev:.3e}")
print(f"  f=0 edge margins (s=0,0.5,1.0)                      = {[f'{x:.2e}' for x in f0_margins]}")
print(f"  degeneracy (margin->0 at f=0) reproduces           = {degeneracy_reproduces}")
print("VERIFIER PASSED" if passed else "VERIFIER FAILED")
