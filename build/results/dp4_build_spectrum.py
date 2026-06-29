#!/usr/bin/env python3
# DP4 builder: construct the F3/F4 identification operator implied by dp3_spec.json's
# R_sep, compute its singular spectrum across the (f, offshore-USD-share) plane, and persist
#   - build/results/dp4_inputs.json   (operator recipe + matrix quantities + eval points)
#   - build/results/dp4_spectrum.json (the singular spectrum / separation-margin SURFACE)
#
# HARD CONSTRAINTS (inherited from DP3, NOT re-opened/softened/overturned):
#   - DP3 conclusion form (b): F3/F4 separation NOT ESTABLISHED. FAILS at f=0 (admissible
#     endpoint); at best CONDITIONALLY identified toward f=0.60, pending the offshore-USD
#     share (second hole). NOWHERE robustly identified across the full plane.
#   - TWO holes are load-bearing: f in [0.0,0.60] and offshore-USD share s_usd in [0,1].
#   - NO point hazard. Hazard is a BOUND/CONDITIONAL SURFACE over (f, s_usd).
#   - 2022 episode is f-CONTINGENT (loads as F4 at f=0), NOT an F3 identification.
#   - Single snapshot: temporal-variation quantities are UNESTIMABLE-FROM-ONE-SNAPSHOT.
#
# The operator is NOT fit. Its columns are the F3 and F4 loading-FOOTPRINTS in the
# observed-moment space (offshore-pool destination cells + USA issuer column), exactly
# as R_sep + its falsifier define them. Its near-singularity IS the DP3 degeneracy,
# computed as numbers.

import json
import numpy as np

ROOT = "/home/user/dollar-breaking-point"
MX   = json.load(open(f"{ROOT}/build/model/matrix_assembled.json"))

# ------------------------------------------------------------------ matrix quantities
# Offshore-pool destination cells (US row), USD mn, from matrix_assembled.json.
US_CYM = 2798130.0
US_HKG =  107448.0
US_VGB =   51419.0
US_CHN =  255341.0   # direct China residency cell (already counted; NOT part of the pool)
POOL   = US_CYM + US_HKG + US_VGB          # 2,956,997 -- the offshore-FC pool R_sep keys on

# USA issuer COLUMN across the 12 holders (the F4 common dollar-leg block), USD mn.
USA_COLUMN = {
    "CYM": 4513338.3, "IRL": 2583036.4, "JPN": 2342597.3, "LUX": 2199787.3,
    "GBR": 1824619.1, "DEU":  878233.5, "FRA":  876069.0, "NLD":  750520.7,
    "HKG":  419578.3, "CHN":  330700.3, "ITA":  238397.0, "BEL":  119098.6,
}
USA_COLUMN_HOLDERS = list(USA_COLUMN.keys())
USA_COLUMN_VALUES  = np.array([USA_COLUMN[h] for h in USA_COLUMN_HOLDERS], dtype=float)

BIS_FLOOR = 711157.7   # carried forward; does NOT enter the operator.

# ------------------------------------------------------------------ moment space
# Observed-moment space in which F3 and F4 footprints live (R_sep, step2):
#   block A: the 3 offshore-pool DESTINATION cells (CYM,HKG,VGB) of the US row -- the
#            within-row reallocation destination R_sep keys on.
#   block B: the 12 USA-column cells across holders -- the F4 common dollar-leg block.
# dimension = 3 + 12 = 15.
DEST_CELLS  = ["US->CYM", "US->HKG", "US->VGB"]
DEST_VALUES = np.array([US_CYM, US_HKG, US_VGB], dtype=float)
DESTn       = DEST_VALUES / np.linalg.norm(DEST_VALUES)     # destination-line direction
USAn        = USA_COLUMN_VALUES / np.linalg.norm(USA_COLUMN_VALUES)  # common USA direction
n_dest = len(DEST_CELLS)
n_usa  = len(USA_COLUMN_HOLDERS)
m = n_dest + n_usa  # = 15

def footprints(f, s_usd):
    """
    F3 and F4 loading-footprints implied by R_sep + its FALSIFIER, in moment space
    [destination block (3) ; USA block (12)], per unit factor amplitude.

    R_sep economic content (verbatim drivers from dp3_spec.json):
      - F4 (dollar run) is a COMMON cut of the USA/dollar leg across holders: USA block = -USAn.
        Its FALSIFIER: insofar as the destination cells are themselves offshore-USD (dollar)
        claims, F4 ALSO moves them. The offshore-USD content of the destination is the part of
        the (1-f) remainder that is USD: magnitude (1-f)*s_usd along the destination line.
      - F3 (sanctions reallocation) is a within-row substitution: the SAME observed common USA
        fall is its dollar source (USA block = -USAn, the row's dollar leg), and it lands the
        mass in the destination cells. The part of that destination that is China-by-nationality
        AND non-USD -- magnitude f along the destination line -- is F3-EXCLUSIVE (F4 does NOT move
        non-USD China claims). The REMAINDER of what F3 reallocates lands in offshore-USD
        destinations that are F4-shared (magnitude (1-f)*s_usd) -- the SAME shared mass F4 moves.

    => SHARED destination component (F3 and F4 both move it): (1-f)*s_usd * DESTn
       F3-EXCLUSIVE destination component (only F3):           f * DESTn
       SHARED USA component (single realized common fall):     -USAn  (identical for both)

      v_F3 = [ (f + (1-f)*s_usd) * DESTn ; -USAn ]   (exclusive China rise + shared offshore-USD)
      v_F4 = [ (    (1-f)*s_usd) * DESTn ; -USAn ]   (shared offshore-USD only)

    THE DEGENERACY (DP3 form (b), now numerical):
      The ONLY thing separating v_F3 from v_F4 is the F3-EXCLUSIVE term f*DESTn.
      * At f=0 it VANISHES -> v_F3 == v_F4 for ALL s_usd -> the operator is RANK 1 ->
        smallest singular value (separation margin) = 0 -> F3 and F4 OBSERVATIONALLY EQUIVALENT.
        This is the admissible-endpoint failure DP3 argued.
      * As s_usd rises the SHARED term (1-f)*s_usd grows and dominates BOTH footprints,
        shrinking the angle between them -> margin falls -> the offshore-USD CONFOUND.
      * The USA block is the SAME realized common fall for both (single snapshot: no lead/lag
        discriminator -- dp3_spec step2), so it is shared and does NOT separate the factors.
    """
    a3 = (f + (1.0 - f) * s_usd) * DESTn      # F3 destination block
    a4 = ((1.0 - f) * s_usd) * DESTn          # F4 destination block
    b  = -USAn                                # shared common USA fall (identical for both)
    v_F3 = np.concatenate([a3, b])
    v_F4 = np.concatenate([a4, b])
    return v_F3, v_F4

def spectrum_at(f, s_usd):
    v_F3, v_F4 = footprints(f, s_usd)
    M = np.column_stack([v_F3, v_F4])
    norms = np.linalg.norm(M, axis=0)
    norms_safe = np.where(norms > 0, norms, 1.0)
    Mn = M / norms_safe                       # column-normalised: margin is a geometric angle
    U, S, Vt = np.linalg.svd(Mn, full_matrices=False)
    s1, s2 = float(S[0]), float(S[1])
    cos_angle = (abs(v_F3 @ v_F4) / (np.linalg.norm(v_F3) * np.linalg.norm(v_F4)))
    return {
        "f": f, "usd_share": s_usd,
        "singular_values": [s1, s2],
        "smallest_singular_value_separation_margin": s2,
        "largest_singular_value": s1,
        "spectral_gap": s1 - s2,
        "footprint_collinearity_cos": float(cos_angle),
        "collapsing_right_singular_vector_F3_F4": Vt[1, :].tolist(),
        "column_norms_usd_dimensionless": norms.tolist(),
    }

# ------------------------------------------------------------------ evaluation grid
F_POINTS = [0.00, 0.0864, 0.20, 0.60]      # SAME equation-justified points as dp3_sensitivity.json
S_POINTS = [0.0, 0.5, 1.0]                 # second hole swept: 0=non-USD, 0.5=HOLE midpoint, 1.0=fully offshore-USD
TAU = 0.10                                 # stated separation-margin threshold (geometric; 0=collapsed, 1=orthogonal)

surface = []
for f in F_POINTS:
    for s in S_POINTS:
        row = spectrum_at(f, s)
        row["identified_at_threshold_tau"] = bool(row["smallest_singular_value_separation_margin"] >= TAU)
        surface.append(row)

deg   = spectrum_at(0.00, 0.5)   # degenerate endpoint
worst = spectrum_at(0.60, 1.0)   # most favourable f, maximal confound
best  = spectrum_at(0.60, 0.0)   # most favourable f, no confound

# ------------------------------------------------------------------ persist inputs (reproducibility)
inputs = {
    "dp": "DP4",
    "artifact": "dp4_inputs.json",
    "purpose": "Persisted operator recipe + matrix quantities (verbatim from matrix_assembled.json) + evaluation points so dp4_spectrum.json regenerates from disk ALONE via dp4_recompute_check.py.",
    "generated": "2026-06-29",
    "reads": ["build/model/matrix_assembled.json (cell values, reproduced verbatim below)"],
    "matrix_quantities_usd_mn": {
        "offshore_pool_destination_cells": {"US->CYM": US_CYM, "US->HKG": US_HKG, "US->VGB": US_VGB},
        "offshore_pool_total_POOL": POOL,
        "direct_us_to_china_cell_not_in_pool": US_CHN,
        "usa_issuer_column_by_holder": USA_COLUMN,
        "bis_marginal_floor_carried_forward": BIS_FLOOR,
    },
    "moment_space": {
        "block_A_destination_cells": DEST_CELLS,
        "block_B_usa_column_holders": USA_COLUMN_HOLDERS,
        "dimension": m,
    },
    "operator_recipe": {
        "shape": "15 x 2  (columns = [v_F3 | v_F4])",
        "destination_line_direction_DESTn": DESTn.tolist(),
        "usa_common_direction_USAn": USAn.tolist(),
        "v_F3": "[ (f + (1-f)*s_usd)*DESTn ; -USAn ]  -- F3-exclusive China-non-USD rise (f) + shared offshore-USD (1-f)*s_usd, shared common USA fall.",
        "v_F4": "[ (    (1-f)*s_usd)*DESTn ; -USAn ]  -- shared offshore-USD destination (the FALSIFIER: F4 also moves offshore-USD claims) + shared common USA fall.",
        "separating_component": "f*DESTn (F3-exclusive). Vanishes at f=0 -> v_F3==v_F4 -> rank-1 -> margin 0 for ALL s_usd.",
        "confound": "shared term (1-f)*s_usd*DESTn grows with s_usd, dominates both footprints, shrinks the angle -> margin falls.",
        "single_snapshot_shared_USA": "the USA block -USAn is the SAME realized common fall for both factors; one matrix has no lead/lag discriminator, so it does NOT separate them.",
        "margin_definition": "smallest singular value of the COLUMN-NORMALISED operator (geometric; 0=footprints collapsed/observationally equivalent, 1=orthogonal/cleanly separated).",
        "threshold_tau": TAU,
        "threshold_basis": "stated, not tuned: for a column-normalised 15x2 map the smallest singular value lies in [0,1]; tau=0.10 marks a footprint angle of ~arccos(sqrt(1-tau^2)) where the two footprints are within ~8 degrees of collinear -- below it the factors are treated as observationally inseparable. The verdict (form (b)) does NOT depend on tau: the margin is EXACTLY 0 at f=0 for all s_usd regardless of tau.",
    },
    "evaluation_points": {
        "f_points": F_POINTS,
        "f_points_justification": "SAME equation-justified points as dp3_sensitivity.json (endpoints 0.0, 0.60 + landmarks 0.0864 offshore-increment=direct-cell, 0.20 NBER corporate-bond China-nationality share).",
        "usd_share_points": S_POINTS,
        "usd_share_justification": "the offshore-USD (ABS) share of the (1-f) remainder is a HOLE; swept as a PARAMETER at 0.0 (remainder fully non-USD; F4 has no destination reach), 0.5 (HOLE midpoint -- NOT an estimate), 1.0 (remainder fully offshore-USD = confound maximal; F4 reaches all destinations). No point value invented.",
    },
    "carried_forward_not_resolved": [
        "HOLE: China-nationality fraction f in [0.0, 0.60] (china_fraction_bound.json).",
        "HOLE: offshore-USD (ABS) share of the non-China remainder s_usd in [0,1] (second hole; UNVERIFIED).",
        "$711,157.7mn BIS banking-marginal floor (does not enter operator; carried as F1 noise floor).",
        "UNESTIMABLE-FROM-ONE-SNAPSHOT: contagion-vs-substitution (lead/lag) discriminator; no second matrix on disk.",
    ],
}
json.dump(inputs, open(f"{ROOT}/build/results/dp4_inputs.json", "w"), indent=1)

# ------------------------------------------------------------------ persist spectrum
spectrum = {
    "dp": "DP4",
    "artifact": "dp4_spectrum.json",
    "title": "Singular spectrum and F3/F4 separation-margin SURFACE over the (f, offshore-USD-share) plane -- the DP3 degeneracy made numerical. NO point hazard.",
    "status": "OUTPUT -- NOT ESTABLISHED. Estimation run; not established until the DP5 verifier scenario runs and its verifier artifact exists on disk. Inherits DP3 form (b): F3/F4 separation NOT ESTABLISHED -- fails at f=0, at best conditionally identified toward f=0.60. NOT re-opened/softened/overturned.",
    "generated": "2026-06-29",
    "reads": ["build/results/dp4_inputs.json (operator recipe + matrix quantities + eval points)"],
    "regenerates_from": "build/results/dp4_inputs.json via build/results/dp4_recompute_check.py",

    "what_the_operator_is": "The 15x2 linear map M=[v_F3|v_F4] whose columns are the F3 and F4 loading-footprints in the observed-moment space (3 offshore-pool destination cells + 12 USA-column cells), implied by R_sep + its falsifier. Its near-singularity IS the F3/F4 degeneracy DP3 argued analytically. Not a fit; a footprint operator.",

    "singular_spectrum_full": {
        "note": "operator is 15x2 -> two singular values per (f,s_usd). The COLLAPSING direction is the right-singular vector of the SMALLER singular value: the (F3,F4) combination that is unresolved.",
        "degenerate_endpoint_f0_smid": deg,
        "worst_confound_f060_usdshare1": worst,
        "best_case_f060_usdshare0": best,
        "which_direction_collapses": "At f=0 the smallest-singular-value right vector is ~(1,-1)/sqrt(2): the F3-MINUS-F4 difference is unresolved -- i.e. the operator cannot tell a sanctions-reallocation from a dollar-run on the offshore cells. As f rises the collapsing combination tilts but the F3-F4 difference remains the poorly-resolved direction whenever s_usd is high.",
    },

    "separation_margin_surface": {
        "axes": {"f": F_POINTS, "usd_share": S_POINTS},
        "margin_definition": "smallest singular value of the column-normalised operator; 0 = F3/F4 footprints COLLAPSE (observationally equivalent), 1 = orthogonal (cleanly separated).",
        "threshold_tau": TAU,
        "grid": surface,
        "how_the_margin_moves": "MONOTONE INCREASING in f (more China-non-USD destination = more separating support) and MONOTONE DECREASING in s_usd (more offshore-USD remainder = stronger confound). The margin is EXACTLY 0 along the entire f=0 edge for all s_usd, and stays below tau in a band of small f / high s_usd.",
    },

    "numerical_confirmations_of_dp3": {
        "margin_zero_along_f0_edge": "At f=0 the F3-exclusive destination term f*DESTn is ZERO, so v_F3==v_F4 and the operator is rank 1: separation margin = 0.0 for s_usd=0.0, 0.5 AND 1.0. The f=0 failure is not a knife-edge in s_usd -- it holds for the whole edge. This is DP3's admissible-endpoint degeneracy, shown as numbers.",
        "margin_falls_with_usd_share_even_at_f060": f"At f=0.60 the margin falls from {best['smallest_singular_value_separation_margin']:.4f} (s_usd=0.0) to {worst['smallest_singular_value_separation_margin']:.4f} (s_usd=1.0): the offshore-USD confound bites even at the MOST FAVOURABLE admissible f. The separation is NOT clean even there -- exactly DP3's 'conditionally identified, pending the second hole'.",
        "margin_clears_tau_only_when": "the margin clears tau ONLY for f away from 0 with s_usd not too high. That region is NOT pinned on disk: f is a HOLE in [0,0.60] AND s_usd is a HOLE in [0,1]. So identification is NOWHERE established across the full admissible plane.",
    },

    "hazard_as_bound_not_point": {
        "STATEMENT": "NO point hazard is output. A point breaking-point hazard requires data NOT on disk -- the China-nationality fraction f AND the offshore-USD share s_usd. Both are HOLES. The hazard is reported ONLY as a CONDITIONAL SURFACE over (f, s_usd), carrying the regions where F3/F4 IS vs IS NOT identified.",
        "identified_region": "f sufficiently large AND s_usd sufficiently low: separation margin >= tau; the binding-mode attribution (sanctions-reallocation F3 vs dollar-run F4) is DECIDABLE there.",
        "NOT_identified_region": "(i) the entire f=0 edge for ALL s_usd: margin=0, F3=F4, attribution UNDECIDABLE; (ii) small f with high s_usd: margin<tau, the confound dominates, attribution UNDECIDABLE.",
        "bound_over_the_plane": "Over the full admissible plane (f in [0,0.60], s_usd in [0,1]) the separation margin's INFIMUM is 0 (attained along f=0). The margin is NOT bounded away from 0, so the binding-mode is NOWHERE robustly identified across the whole plane. The hazard is a BOUND/SURFACE with an explicit unidentified region, never a scalar.",
        "single_hazard_number_would_be": "a STAGE FAILURE -- it would require inventing f and s_usd. Refused.",
    },

    "episode_2022_f_contingent": {
        "STATEMENT": "The 2022 Russia reserve-immobilization / sanctions episode's signature in the operator is F3-OR-F4 CONTINGENT ON f. It is NOT reported as an F3 identification.",
        "at_f0": "At f=0 the operator is rank 1: the 2022 offshore footprint loads on the SHARED F3=F4 direction, which is observationally the F4 common-run direction. The episode is observationally F4 at the admissible endpoint, NOT F3.",
        "toward_f060": "As f rises the F3-exclusive destination term becomes nonzero and the episode COULD load on F3 -- but only conditional on s_usd low (else the confound re-aligns the footprints). So even the F3 reading is conditional on BOTH holes.",
        "planting_guard": "Reviving the 2022-sanctions->F3 assignment as established is the specific planting failure forbidden here. NOT committed: the episode is f-contingent, and at the admissible endpoint f=0 it is F4.",
    },

    "single_snapshot_honesty": {
        "UNESTIMABLE-FROM-ONE-SNAPSHOT": "The contagion-vs-substitution discriminator (does a holder's USA drop LEAD others' = F4 contagion, or co-occur with that holder's own destination rise = F3 substitution?) needs temporal variation. There is ONE matrix on disk. This quantity is UNESTIMABLE-FROM-ONE-SNAPSHOT and is NOT proxied. It is why the USA block is a SHARED direction in the operator (it does not separate the factors on one realization).",
    },

    "carried_forward_not_resolved": [
        "HOLE: f in [0.0, 0.60].",
        "HOLE: offshore-USD share s_usd in [0,1] (second hole).",
        "$711,157.7mn BIS banking-marginal floor.",
        "UNESTIMABLE-FROM-ONE-SNAPSHOT: contagion-vs-substitution lead/lag discriminator.",
    ],

    "verifier_required": "DP5 episode-sort gate + hazard overid test (identification-gate-agent), verifier artifact build/results/dp5_idtest.json. Until that artifact exists on disk, every result here is an OUTPUT, NOT ESTABLISHED.",
}
json.dump(spectrum, open(f"{ROOT}/build/results/dp4_spectrum.json", "w"), indent=1)

# ------------------------------------------------------------------ console summary
print("=== DP4 SINGULAR SPECTRUM / SEPARATION-MARGIN SURFACE ===")
print(f"moment dim = {m}  (3 destination cells + 12 USA-column cells);  threshold tau = {TAU}\n")
print(f"{'f':>7} {'usd_share':>9} {'s1':>8} {'s2(margin)':>11} {'gap':>8} {'collin_cos':>10} {'identified':>10}")
for row in surface:
    print(f"{row['f']:>7.4f} {row['usd_share']:>9.2f} {row['singular_values'][0]:>8.4f} "
          f"{row['smallest_singular_value_separation_margin']:>11.5f} {row['spectral_gap']:>8.4f} "
          f"{row['footprint_collinearity_cos']:>10.5f} {str(row['identified_at_threshold_tau']):>10}")
print("\nf=0 collapsing right-singular vector (F3,F4):", [round(x,4) for x in deg["collapsing_right_singular_vector_F3_F4"]])
print("wrote build/results/dp4_inputs.json and build/results/dp4_spectrum.json")
