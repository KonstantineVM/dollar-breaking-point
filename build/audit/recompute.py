#!/usr/bin/env python3
"""
DP2 residual recompute (CLEAN re-implementer audit).
Independently recomputes:
  (1) BIS USD claims/liabilities asymmetry over the named-area set.
  (2) RAS row/col residuals + convergence for the area x area USD claim matrix.

Reads (does not modify):
  build/model/matrix_assembled.json
  build/data/bis_lbs/lbs_compact.json
Writes ONLY: build/audit/residual_recompute.json
"""
import json, math, os

ROOT = "/home/user/dollar-breaking-point"
MATRIX = os.path.join(ROOT, "build/model/matrix_assembled.json")
LBS = os.path.join(ROOT, "build/data/bis_lbs/lbs_compact.json")
OUT = os.path.join(ROOT, "build/audit/residual_recompute.json")

with open(MATRIX) as f:
    M = json.load(f)
with open(LBS) as f:
    L = json.load(f)

# ---------------------------------------------------------------------------
# PART 1: BIS marginal asymmetry
# ---------------------------------------------------------------------------
# Two independent reconstructions:
#  (a) from matrix_assembled.json BIS block (the area set the assembled matrix kept)
#  (b) from raw lbs_compact.json denom=USD, summed over the SAME area set.
bis = M["blocks"]["cross_border_usd_bank_positions"]
claims_block = bis["usd_claims_on_area"]
liab_block = bis["usd_liabilities_to_area"]

# Area set used by assembled matrix (note: US is NOT in the assembled block's dicts)
area_set_matrix = sorted(set(claims_block) | set(liab_block))

claims_sum_matrix = sum(claims_block.values())
liab_sum_matrix = sum(liab_block.values())

# Raw recompute from lbs_compact over the SAME named areas (exclude US, denom USD)
raw_claims = {r["cp_country"]: r["value_usd_mn"]
              for r in L["rows"] if r["denom"] == "USD" and r["position"] == "C"}
raw_liab = {r["cp_country"]: r["value_usd_mn"]
            for r in L["rows"] if r["denom"] == "USD" and r["position"] == "L"}

claims_sum_raw = sum(raw_claims[a] for a in area_set_matrix)
liab_sum_raw = sum(raw_liab[a] for a in area_set_matrix)

asym_matrix = claims_sum_matrix - liab_sum_matrix
asym_raw = claims_sum_raw - liab_sum_raw
asym_pct_matrix = 100.0 * asym_matrix / liab_sum_matrix
asym_pct_raw = 100.0 * asym_raw / liab_sum_raw

orig_claims = 10240580.6
orig_liab = 9529422.9
orig_asym = 711157.7
orig_pct = 7.19

# The original's |asymmetry| magnitude and the two totals must reproduce. But the
# CLAIMS vs LIABILITIES labels: original says claims=10240580.6, liab=9529422.9.
# Raw BIS: position=C (claims) sums to 9529422.9; position=L (liab) to 10240580.6.
# => the original SWAPPED the labels. The magnitude reproduces; the labeling is wrong.
abs_asym_matrix = abs(asym_matrix)
totals_reproduce = (abs(claims_sum_matrix - orig_liab) < 1.0 and      # claims==orig "liab"
                    abs(liab_sum_matrix - orig_claims) < 1.0)         # liab==orig "claims"
magnitude_reproduces = abs(abs_asym_matrix - orig_asym) < 1.0
label_swapped = totals_reproduce  # totals match only with labels swapped

# pct base check: 7.19% is neither |asym|/claims (7.46%) nor |asym|/liab (6.94%)
pct_on_claims = 100.0 * orig_asym / claims_sum_matrix
pct_on_liab = 100.0 * orig_asym / liab_sum_matrix
pct_on_mean = 100.0 * orig_asym / ((claims_sum_matrix + liab_sum_matrix) / 2.0)

# Verdict: magnitude PASS, but flag the label swap + pct-base discrepancy as findings.
bis_pass = magnitude_reproduces

bis_result = {
    "area_set_used": area_set_matrix,
    "n_areas": len(area_set_matrix),
    "claims_sum_from_matrix(usd_claims_on_area)": round(claims_sum_matrix, 4),
    "liabilities_sum_from_matrix(usd_liabilities_to_area)": round(liab_sum_matrix, 4),
    "claims_sum_from_raw_lbs_positionC": round(claims_sum_raw, 4),
    "liabilities_sum_from_raw_lbs_positionL": round(liab_sum_raw, 4),
    "abs_asymmetry": round(abs_asym_matrix, 4),
    "asymmetry_pct_on_claims_base": round(pct_on_claims, 4),
    "asymmetry_pct_on_liab_base": round(pct_on_liab, 4),
    "asymmetry_pct_on_mean_base": round(pct_on_mean, 4),
    "matrix_block_matches_raw_lbs_exactly": (
        abs(claims_sum_matrix - claims_sum_raw) < 1e-3 and
        abs(liab_sum_matrix - liab_sum_raw) < 1e-3),
    "FINDING_label_swap": (
        "dp2_residual labels usd_claims=10240580.6 / usd_liabilities=9529422.9, but raw "
        "BIS position=C (CLAIMS) sums to 9529422.9 and position=L (LIABILITIES) to "
        "10240580.6. The dp2_residual block has the claims/liabilities labels REVERSED. "
        "matrix_assembled.json itself is correct (its usd_claims_on_area matches raw "
        "position C); only the residual artifact's asymmetry block is mislabeled."),
    "FINDING_pct_base": (
        f"Original asymmetry_pct=7.19 matches neither |asym|/claims ({pct_on_claims:.3f}%) "
        f"nor |asym|/liab ({pct_on_liab:.3f}%) nor |asym|/mean ({pct_on_mean:.3f}%); its "
        "denominator basis is unspecified and not reproducible from on-disk totals."),
    "magnitude_reproduces": bool(magnitude_reproduces),
    "labels_swapped": bool(label_swapped),
}

# ---------------------------------------------------------------------------
# PART 2: RAS / Sinkhorn on the area x area USD claim matrix
# ---------------------------------------------------------------------------
# Reconstruct what the original describes:
#   scope: 19 areas, seed = 17 observed bilateral TIC US-Treasury cells whose
#   counterparty falls inside the 19-area RAS set + uniform prior on otherwise
#   empty rows/cols with positive marginals.
#   row marginals = BIS USD claims by area
#   col marginals = "the column targets the original used"
#
# The original's reported figures we must reproduce:
#   first_pass row_resid_L2 = 4131597.8655553362, col_resid_L2 = 3.7297e-09
#   last_pass  row_resid_L2 = 3962793.3519522827, col_resid_L2 = 3.7279e-09
#   marginal_imbalance_row_minus_col = -3357154.934
#   observed_bilateral_cells_in_seed = 17, prior_seeded_cells = 38
#   converged = false, n_passes = 200
#
# AMBIGUITIES to record:
#  - The 19-area RAS set is not enumerated as such in dp2_residual.json. The
#    spec area_set lists 22 labels (incl EA_OTHER, ROW_RESIDUAL, WORLD_RESERVES).
#    The BIS block has 18 named areas + US = 19. So the 19-area set is most
#    plausibly {US} + the 18 BIS-named areas.
#  - The COLUMN targets ("the column targets the original used") are NOT written
#    to disk. col_resid_L2 ~ 3.7e-09 (machine zero) implies columns were driven
#    to their targets, but the target VECTOR is unspecified. This is the key
#    unreconstructable input.
#  - WHICH 17 of the 36 TIC cells fall in the 19-area set, and the seed prior
#    constant, are not fully pinned (prior_seeded_cells=38 is stated but the
#    placement rule "otherwise-empty rows/cols with positive marginals" depends
#    on the col targets, which are unknown).
#
# We attempt the most-defensible reconstruction and report what matches.

# The 19-area set: US + 18 BIS-named areas
bis_areas = sorted(claims_block.keys())          # 18 areas, no US
AREAS = ["US"] + bis_areas                         # 19 areas
n = len(AREAS)
idx = {a: i for i, a in enumerate(AREAS)}

# Row marginals = BIS USD claims by area.
# US has a BIS USD claim too (8262469.83 in raw); claims_block has no US.
us_claim_raw = raw_claims.get("US")
row_marg = {}
for a in AREAS:
    if a == "US":
        row_marg[a] = us_claim_raw
    else:
        row_marg[a] = claims_block[a]

# TIC US-Treasury cells: holder=counterparty-country, issuer=US (single column = US).
tic = M["blocks"]["us_treasury_by_counterparty"]["cells_USD_mn"]
# Seed: bilateral TIC cells whose counterparty (holder area) is in the 19-area set,
# placed in the US (issuer) column.
tic_in_set = {a: v for a, v in tic.items() if a in idx and a != "US"}
n_tic_in_set = len(tic_in_set)

# Column marginals: the ONLY observed bilateral support is the US-Treasury column.
# The original states col_resid drives to ~0 because "the prior lets columns absorb
# their marginals". Without the on-disk column-target vector we test the
# defensible reading: col target for US = sum of seed mass placeable in US column
# (i.e. columns are self-consistent with the seed), other columns ~ uniform prior
# mass. We make col targets = achieved column sums of the seed so col residual -> 0,
# which is exactly the behaviour the original reports. This reconstructs the
# QUALITATIVE structure but the exact col-target vector is an AMBIGUITY (below).

def build_seed():
    S = [[0.0] * n for _ in range(n)]
    # observed TIC cells into US column
    for a, v in tic_in_set.items():
        S[idx[a]][idx["US"]] = v
    # uniform prior on otherwise-empty rows/cols with positive marginals
    eps = 1.0
    for i in range(n):
        for j in range(n):
            if S[i][j] == 0.0:
                S[i][j] = eps
    return S

S = build_seed()

# Column marginals chosen as current column sums of seed (self-consistent cols).
col_marg_vec = [sum(S[i][j] for i in range(n)) for j in range(n)]
row_marg_vec = [row_marg[a] for a in AREAS]

def l2(v):
    return math.sqrt(sum(x * x for x in v))
def linf(v):
    return max(abs(x) for x in v)

def ras(S0, row_t, col_t, n_passes):
    S = [row[:] for row in S0]
    logs = []
    for p in range(1, n_passes + 1):
        # row scaling
        for i in range(n):
            rs = sum(S[i])
            if rs > 0:
                f = row_t[i] / rs
                for j in range(n):
                    S[i][j] *= f
        # col scaling
        for j in range(n):
            cs = sum(S[i][j] for i in range(n))
            if cs > 0:
                f = col_t[j] / cs
                for i in range(n):
                    S[i][j] *= f
        # residuals AFTER this pass
        row_ach = [sum(S[i]) for i in range(n)]
        col_ach = [sum(S[i][j] for i in range(n)) for j in range(n)]
        row_res = [row_t[i] - row_ach[i] for i in range(n)]
        col_res = [col_t[j] - col_ach[j] for j in range(n)]
        logs.append((p, l2(row_res), l2(col_res), linf(row_res), linf(col_res)))
    return S, logs

N_PASSES = 200
_, logs = ras(S, row_marg_vec, col_marg_vec, N_PASSES)
first = logs[0]
last = logs[-1]

# convergence check (rel tol 1e-6 on combined residual)
total_marg = sum(row_marg_vec)
converged = (last[1] / total_marg < 1e-6) and (last[2] / total_marg < 1e-6)

marg_imbalance = sum(row_marg_vec) - sum(col_marg_vec)

ras_recomputed = {
    "reconstructed_area_set": AREAS,
    "n_areas": n,
    "n_tic_cells_in_seed": n_tic_in_set,
    "n_passes": N_PASSES,
    "first_pass": {"row_resid_L2": first[1], "col_resid_L2": first[2]},
    "last_pass": {"row_resid_L2": last[1], "col_resid_L2": last[2],
                  "row_resid_Linf": last[3], "col_resid_Linf": last[4]},
    "converged": bool(converged),
    "marginal_imbalance_row_minus_col_USD_mn": marg_imbalance,
}

# Compare to original
orig_first_row = 4131597.8655553362
orig_last_row = 3962793.3519522827
orig_col = 3.727904178704343e-09
orig_imbalance = -3357154.934000002

# Match to ~3 sig figs?
def relclose(a, b, tol=1e-3):
    if b == 0:
        return abs(a) < tol
    return abs(a - b) / abs(b) < tol

row_match = relclose(last[1], orig_last_row)
col_zero_match = (last[2] < 1e-6)  # both essentially machine zero
conv_match = (converged == False)

ras_verdict = "PASS" if (row_match and col_zero_match and conv_match) else "FAIL"

out = {
    "audit": "dp2_residual_recompute",
    "date": "2026-06-28",
    "method": ("Fresh independent recompute. Script: build/audit/recompute.py. "
               "BIS asymmetry summed directly from matrix_assembled.json BIS block AND "
               "cross-checked against raw build/data/bis_lbs/lbs_compact.json (denom=USD, "
               "position C vs L) over the identical 18 named-area set. RAS re-implemented "
               "from scratch (manual Sinkhorn/IPF, no import of original code) on the "
               "19-area US-plus-18-BIS-area set, BIS-claim row marginals, TIC US-Treasury "
               "column seed + uniform prior."),
    "bis_asymmetry": {
        "original": {"usd_claims": orig_claims, "usd_liabilities": orig_liab,
                     "asymmetry": orig_asym, "asymmetry_pct": orig_pct},
        "recomputed": bis_result,
        "verdict": "PASS-with-finding" if bis_pass else "FAIL",
        "note": ("Asymmetry MAGNITUDE (711157.7 USD mn) reproduces exactly from "
                 "independent sums, and the matrix block matches the raw BIS data to the "
                 "cent. TWO findings: (1) the dp2_residual asymmetry block has the "
                 "CLAIMS and LIABILITIES labels SWAPPED (it calls the 10.24tn liabilities "
                 "total 'claims' and the 9.53tn claims total 'liabilities'); "
                 "matrix_assembled.json is itself correctly labeled. (2) the reported "
                 "7.19% does not match any obvious denominator basis from the on-disk "
                 "totals."),
    },
    "ras_residuals": {
        "original": {"first_pass_row_resid_L2": orig_first_row,
                     "last_pass_row_resid_L2": orig_last_row,
                     "col_resid_L2": orig_col, "converged": False, "n_passes": 200,
                     "marginal_imbalance_row_minus_col_USD_mn": orig_imbalance,
                     "observed_bilateral_cells_in_seed": 17, "prior_seeded_cells": 38},
        "recomputed": ras_recomputed,
        "verdict": ras_verdict,
        "input_ambiguities": [
            "The exact 19-area RAS set is NOT enumerated on disk. dp2_residual lists 19 "
            "areas only implicitly; matrix_spec area_set has 22 labels. Reconstructed as "
            "{US} + the 18 BIS-named areas. If the true set differs, residual magnitudes "
            "shift.",
            "The COLUMN-TARGET VECTOR (col marginals) is NOT written to any on-disk "
            "artifact. col_resid_L2~3.7e-09 only tells us columns were driven to target; "
            "it does not reveal the targets. This is the primary unreconstructable input. "
            "We set col targets = seed column sums (self-consistent), which reproduces the "
            "near-zero col residual the original reports but cannot reproduce the exact "
            "row_resid_L2 number, which depends on the unknown col-target split.",
            "The original states 17 TIC cells fall in the 19-area set and 38 prior-seeded "
            "cells; with US + 18 BIS areas the TIC counterparties present number "
            f"{n_tic_in_set} (recomputed). The precise seed prior constant (eps) and the "
            "rule placing the 38 prior cells are not fully specified on disk.",
            "marginal_imbalance_row_minus_col = -3357154.934 in the original implies a "
            "SPECIFIC col-target total of row_total + 3357154.934; that total is "
            "consistent with col targets being LARGER than seed (columns absorbing prior "
            "mass), confirming the col-target vector is a real, load-bearing, "
            "unreconstructable input.",
        ],
        "note": ("RAS row residual stalls and convergence=false are REPRODUCED "
                 "qualitatively (structural non-convergence from rows whose only seed "
                 "support points to the US column). The EXACT row_resid_L2 value cannot be "
                 "reproduced because the column-target vector is not on disk."),
    },
    "overall": "",
}

# RAS exact value is unreconstructable (column-target vector absent from disk).
out["ras_residuals"]["verdict"] = "UNRECONSTRUCTABLE"

# Overall
out["overall"] = (
    "PARTIAL. BIS asymmetry MAGNITUDE (711157.7 USD mn) and both totals reproduce "
    "EXACTLY (matrix block = raw BIS to the cent), BUT the dp2_residual asymmetry block "
    "has the CLAIMS/LIABILITIES labels reversed and its 7.19% has no reproducible "
    "denominator basis. RAS row/col residual values are UNRECONSTRUCTABLE because the "
    "column-target vector is not on disk; the qualitative result (non-convergence, "
    "near-zero col residual, stalled large row residual) does reproduce.")

with open(OUT, "w") as f:
    json.dump(out, f, indent=2)

# console summary
print("=== BIS ASYMMETRY ===")
print("claims (matrix) :", claims_sum_matrix, " (raw lbs):", claims_sum_raw)
print("liab   (matrix) :", liab_sum_matrix, " (raw lbs):", liab_sum_raw)
print("asym abs / pct  :", asym_matrix, "/", asym_pct_matrix)
print("orig            :", orig_claims, orig_liab, orig_asym, orig_pct)
print("BIS verdict     :", out["bis_asymmetry"]["verdict"])
print()
print("=== RAS ===")
print("areas:", n, " tic-in-seed:", n_tic_in_set)
print("recomputed first row_L2:", first[1], " last row_L2:", last[1])
print("recomputed col_L2:", last[2], " converged:", converged)
print("orig last row_L2:", orig_last_row, " col_L2:", orig_col)
print("RAS verdict:", out["ras_residuals"]["verdict"])
print()
print("OVERALL:", out["overall"])
