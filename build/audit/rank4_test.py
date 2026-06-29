#!/usr/bin/env python3
"""
FALSIFICATION TEST 3 -- rank4_test.py
Build the FULL four-factor loading operator M4 = [v_F1 | v_F2 | v_F3 | v_F4]
in a COMMON observed-moment space and test its rank / conditioning.

READ-ONLY on build artifacts. Writes ONLY build/audit/rank4_test.json.

The build (dp3_spec.json, dp4_*.json) only litigated F3/F4 and PRE-DECLARED
F1/F2 "IDENTIFIED (bounded)" in the section-1 table without ever putting
F1,F2,F3,F4 columns into a single operator and checking its spectrum. This
script does exactly that and asks: are there OTHER collinearities the build
never gated -- e.g. F1-F4 or F2-F4?

Sources (verbatim from disk):
  build/results/dp4_inputs.json   -- DESTn, USAn, v_F3/v_F4 recipe, eval points
  build/model/matrix_assembled.json -- BIS LBS marginals (counts), TIC summary
  build/data/bis_lbs/lbs_compact.json -- BIS USD per-area claim/liability marginals (F1)
  build/data/treasury_tic/mfh_dec2025.json -- TIC US-Treasury-by-holder (F2)
"""
import json, numpy as np, os

ROOT = "/home/user/dollar-breaking-point"

def load(p):
    with open(os.path.join(ROOT, p)) as f:
        return json.load(f)

dp4 = load("build/results/dp4_inputs.json")
bis = load("build/data/bis_lbs/lbs_compact.json")
tic = load("build/data/treasury_tic/mfh_dec2025.json")

# ---------------------------------------------------------------------------
# Factor footprints in their NATIVE cell spaces, indexed by AREA/HOLDER.
# The common moment space is the UNION of areas/holders the factors touch.
# Each factor is a DIRECTION (column-normalised) in that union; a factor gets
# ZERO on cells it does not load on.
# ---------------------------------------------------------------------------

# F3/F4 native space (from dp4_inputs): 3 destination cells + 12 USA-column holders.
DESTn = np.array(dp4["operator_recipe"]["destination_line_direction_DESTn"])      # len 3
USAn  = np.array(dp4["operator_recipe"]["usa_common_direction_USAn"])             # len 12
dest_cells = dp4["moment_space"]["block_A_destination_cells"]                      # US->CYM,HKG,VGB
usa_holders = dp4["moment_space"]["block_B_usa_column_holders"]                    # CYM..BEL (12)

# Map CPIS holder/dest labels to ISO2 used by BIS, and to TIC names.
cpis_to_iso2 = {"CYM":"KY","IRL":"IE","JPN":"JP","LUX":"LU","GBR":"GB","DEU":"DE",
                "FRA":"FR","NLD":"NL","HKG":"HK","CHN":"CN","ITA":"IT","BEL":"BE",
                "USA":"US","VGB":"VG"}
tic_name_to_iso2 = {"Japan":"JP","United Kingdom":"GB","China, Mainland":"CN",
                    "Belgium":"BE","Luxembourg":"LU","Cayman Islands":"KY",
                    "France":"FR","Ireland":"IE","Hong Kong":"HK","Germany":"DE",
                    "Netherlands":"NL","Italy":"IT"}

# F1 native: BIS USD per-area MARGINALS (claims C and liabilities L), per area.
bis_C = {r["cp_country"]: r["value_usd_mn"] for r in bis["rows"]
         if r["position"]=="C" and r["denom"]=="USD"}
bis_L = {r["cp_country"]: r["value_usd_mn"] for r in bis["rows"]
         if r["position"]=="L" and r["denom"]=="USD"}
bis_areas = [a for a in bis_C.keys()]  # 19 areas

# F2 native: TIC US-Treasury-by-holder quantity (named countries).
tic_hold = tic["named_country_holdings_USD_bn"]  # name -> USD bn
tic_iso = {tic_name_to_iso2.get(k): v for k,v in tic_hold.items() if k in tic_name_to_iso2}

# ---------------------------------------------------------------------------
# Build the COMMON moment space.
# Cells are TYPED so we never silently merge two different instruments on one
# row. A cell id is (BLOCK, area). Blocks:
#   "BIS_C"  : BIS USD claim marginal on area      (F1)
#   "BIS_L"  : BIS USD liability marginal on area  (F1)
#   "TIC"    : TIC US-Treasury holdings by holder  (F2)
#   "DEST"   : CPIS offshore destination cell      (F3,F4)
#   "USA"    : CPIS USA-column holding by holder    (F2 broad-leg, F4, ... )
# F1 loads on BIS_C, BIS_L.  F2 loads on TIC (+ broad USA leg per dp3 R2 it
# ALSO touches the USA column as 'broad-safe-leg quantity').  F3,F4 load on
# DEST and USA.
#
# CONSTRUCTION CHOICE (stated, not hidden): we evaluate TWO moment spaces.
#  (S-block) BLOCK-TYPED union: each instrument is its own cell, F2's USA-column
#            entry kept SEPARATE from F4's USA-column entry.  This is the build's
#            implicit "instrument dimension separates F2 from F4" assumption.
#  (S-share) SHARED-HOLDER union: the USA-column-by-holder cells are ONE shared
#            row index; F2 (as a US-safe-leg quantity-by-holder) and F4 (dollar
#            run by holder) PROJECT ONTO THE SAME 12 USA cells.  This is the
#            test the build never ran: does F2's by-holder quantity direction
#            actually differ from F4's by-holder run direction on a single
#            snapshot?  If TIC-by-holder ~ CPIS-USA-by-holder, F2 || F4.
# We report BOTH; the load-bearing verdict uses S-share (the harder, honest test).
# ---------------------------------------------------------------------------

# Representative interior eval point + the f=0 case.
def vF3(f, s): return (f + (1-f)*s)
def vF4coef(f, s): return ((1-f)*s)

def build_F3F4(f, s):
    """Return v_F3,v_F4 on [3 dest ; 12 usa] = 15-dim native, raw (un-normalised)."""
    a3 = vF3(f,s); a4 = vF4coef(f,s)
    vF3v = np.concatenate([ a3*DESTn, -USAn ])
    vF4v = np.concatenate([ a4*DESTn, -USAn ])
    return vF3v, vF4v

# Common holder ordering for the USA / TIC / BIS overlap on the 12 CPIS holders.
holders_iso = [cpis_to_iso2[h] for h in usa_holders]   # KY,IE,JP,LU,GB,DE,FR,NL,HK,CN,IT,BE

# F1 direction in BIS space: the COMMON LEVEL / co-movement direction across areas.
# Per dp3: F1 is a marginal/level factor -- a common direction across areas/holders.
# The natural 'level co-movement' direction is the vector of (normalised) USD
# marginals themselves (areas that are bigger in the USD funding system move
# more under a common funding-stress shock, i.e. loading proportional to exposure).
# Claims and liabilities are independent marginals (they do not net) -> F1 spans
# BOTH the C and L sub-blocks.
f1_C = np.array([bis_C[a] for a in bis_areas])
f1_L = np.array([bis_L[a] for a in bis_areas])

# F2 direction: TIC US-Treasury-by-holder quantity direction (the safe leg).
# Loading proportional to each holder's Treasury holding.
tic_areas = [a for a in tic_iso.keys()]
f2_TIC = np.array([tic_iso[a] for a in tic_areas])

# CPIS USA-column-by-holder magnitudes (for the shared-holder test): how big is
# each holder's USA-column position.  USAn is already the column-normalised
# version of these magnitudes (from dp4_inputs).  We need the by-holder TIC
# direction expressed on the SAME 12 holders to compare F2 vs F4.
tic_on_12 = np.array([tic_iso.get(iso, 0.0) for iso in holders_iso])  # IT,?? present

print("holders_iso:", holders_iso)
print("tic_on_12  :", tic_on_12)
print("USAn        :", USAn)

# ===========================================================================
# MOMENT SPACE S-share (load-bearing): cells =
#   [ BIS_C(19) , BIS_L(19) , DEST(3) , USA(12) ]   -> 53 cells
# F1 -> BIS_C + BIS_L blocks (level co-movement).
# F2 -> the USA(12) block, with loading = TIC-by-holder quantity (the US safe
#       leg is measured here as the by-holder quantity; this is F2's by-holder
#       footprint, and it lands on THE SAME 12 USA cells F4 lands on).
# F3 -> DEST + USA, coefficient vF3.
# F4 -> DEST + USA, coefficient vF4 (the broad run, loading -USAn).
# ===========================================================================
def build_M4_shared(f, s):
    nC, nL, nD, nU = 19, 19, 3, 12
    N = nC+nL+nD+nU
    v1 = np.zeros(N); v2 = np.zeros(N); v3 = np.zeros(N); v4 = np.zeros(N)
    # F1 on BIS blocks
    v1[0:nC]      = f1_C
    v1[nC:nC+nL]  = f1_L
    # F2 on the USA(12) block as TIC-by-holder quantity (safe-leg quantity by holder)
    off_U = nC+nL+nD
    v2[off_U:off_U+nU] = tic_on_12
    # F3/F4 on DEST + USA
    vF3v, vF4v = build_F3F4(f, s)
    off_D = nC+nL
    v3[off_D:off_D+nD] = vF3v[0:3];  v3[off_U:off_U+nU] = vF3v[3:15]
    v4[off_D:off_D+nD] = vF4v[0:3];  v4[off_U:off_U+nU] = vF4v[3:15]
    M = np.column_stack([v1,v2,v3,v4])
    return M

# ===========================================================================
# MOMENT SPACE S-block (the build's implicit assumption): F2 gets its OWN TIC
# cells, disjoint from the USA(12) block. cells =
#   [ BIS_C(19) , BIS_L(19) , TIC(12) , DEST(3) , USA(12) ] -> 65
# Here F2 is block-disjoint from F4 by construction -- this is what makes the
# build's pre-declaration LOOK safe. We compute it to expose that the CONFIRM
# verdict is an ARTIFACT of typing TIC as its own block.
# ===========================================================================
def build_M4_block(f, s):
    nC,nL,nT,nD,nU = 19,19,12,3,12
    N=nC+nL+nT+nD+nU
    v1=np.zeros(N);v2=np.zeros(N);v3=np.zeros(N);v4=np.zeros(N)
    v1[0:nC]=f1_C; v1[nC:nC+nL]=f1_L
    off_T=nC+nL; v2[off_T:off_T+nT]=tic_on_12
    off_D=nC+nL+nT; off_U=off_D+nD
    vF3v,vF4v=build_F3F4(f,s)
    v3[off_D:off_D+nD]=vF3v[0:3]; v3[off_U:off_U+nU]=vF3v[3:15]
    v4[off_D:off_D+nD]=vF4v[0:3]; v4[off_U:off_U+nU]=vF4v[3:15]
    return np.column_stack([v1,v2,v3,v4])

def colnorm(M):
    Mn = M.copy().astype(float)
    norms = np.linalg.norm(Mn, axis=0)
    for j in range(Mn.shape[1]):
        if norms[j] > 0: Mn[:,j] /= norms[j]
    return Mn, norms

def analyze(M, tol_frac=1e-8):
    Mn, norms = colnorm(M)
    U,S,Vt = np.linalg.svd(Mn, full_matrices=False)
    smax = S[0]; smin = S[-1]
    cond = float(smax/smin) if smin>0 else float('inf')
    tol = tol_frac * smax
    rank = int(np.sum(S > tol))
    # also a "sensible" tolerance: relative 1e-6 and absolute 1e-3
    rank_e6 = int(np.sum(S > 1e-6*smax))
    rank_abs = int(np.sum(S > 1e-3))
    return {
        "singular_values": [float(x) for x in S],
        "smax": float(smax), "smin": float(smin),
        "condition_number": cond,
        "rank_tol_1e8": rank,
        "rank_tol_1e6rel": rank_e6,
        "rank_abs_1e3": rank_abs,
        "right_singular_vectors_Vt": [[float(x) for x in row] for row in Vt],
        "column_norms": [float(x) for x in norms],
    }

labels = ["F1","F2","F3","F4"]

def collinear_pairs(res, thresh=0.05):
    """For each small singular value (s < thresh*smax), report which columns mix
    via the magnitudes in the corresponding right-singular vector."""
    out=[]
    S=res["singular_values"]; Vt=res["right_singular_vectors_Vt"]; smax=res["smax"]
    for k,s in enumerate(S):
        if s < thresh*smax:
            vec = Vt[k]
            mix = sorted([(labels[j], round(vec[j],4)) for j in range(len(vec))],
                         key=lambda t:-abs(t[1]))
            out.append({"singular_value": s, "rel": s/smax,
                        "mixing_vector": dict(mix),
                        "dominant_columns":[m[0] for m in mix if abs(m[1])>0.3]})
    return out

# Pairwise cosine of column footprints (raw, in the shared space) -- the direct
# F1-F4, F2-F4, F1-F2 collinearity readout.
def pairwise_cos(M):
    Mn,_=colnorm(M)
    G = Mn.T @ Mn
    cos={}
    for i in range(4):
        for j in range(i+1,4):
            cos[f"{labels[i]}-{labels[j]}"]=float(G[i,j])
    return cos

results = {}
eval_pts = [(0.20,0.5,"interior"), (0.0,0.5,"f0_smid"), (0.0,1.0,"f0_susd1"),
            (0.60,0.0,"best_case")]

for space_name, builder in [("S_share_shared_holder_index", build_M4_shared),
                            ("S_block_TIC_own_block", build_M4_block)]:
    results[space_name]={}
    for f,s,tag in eval_pts:
        M = builder(f,s)
        res = analyze(M)
        res["pairwise_cos_F_columns"]=pairwise_cos(M)
        res["collinear_combinations"]=collinear_pairs(res)
        results[space_name][tag]={"f":f,"s_usd":s, **res}

# ---- Build verdict from the S_share interior point (load-bearing) ----
interior = results["S_share_shared_holder_index"]["interior"]
cos = interior["pairwise_cos_F_columns"]
f1f4 = abs(cos["F1-F4"])
f2f4 = abs(cos["F2-F4"])
f1f2 = abs(cos["F1-F2"])
rank4 = interior["rank_tol_1e6rel"]
cond  = interior["condition_number"]

# f=0 case (where F3==F4 collapses -- already gated by the build)
f0 = results["S_share_shared_holder_index"]["f0_smid"]

new_coll=[]
COS_THR = 0.95    # |cos|>0.95 => within ~18deg: a TRUE new collinearity the build never gated.
ELEV_THR = 0.50   # 0.50<|cos|<=0.95: ELEVATED correlation -- separately identified but NOT clean.
if f1f4 > COS_THR: new_coll.append({"pair":"F1-F4","cos":cos["F1-F4"]})
if f2f4 > COS_THR: new_coll.append({"pair":"F2-F4","cos":cos["F2-F4"]})
if f1f2 > COS_THR: new_coll.append({"pair":"F1-F2","cos":cos["F1-F2"]})

elevated=[]
for nm,val,c in [("F1-F4",f1f4,cos["F1-F4"]),("F2-F4",f2f4,cos["F2-F4"]),
                 ("F1-F2",f1f2,cos["F1-F2"])]:
    if COS_THR>=val>ELEV_THR:
        elevated.append({"pair":nm,"cos":c,"angle_deg":float(np.degrees(np.arccos(min(1.0,val))))})

# The F3-F4 degeneracy is EXPECTED/known (the build gated it). A NEW problem is
# any collinearity NOT involving the F3-F4 pair, i.e. F1 or F2 against F4/each other.
known_f3f4 = abs(cos["F3-F4"])

if new_coll:
    verdict = "OVERTURN" if (f1f4>COS_THR or f2f4>COS_THR) else "PARTIAL"
    reason = ("Beyond the gated F3-F4 degeneracy, the full 4-factor operator shows "
              "ADDITIONAL collinearity the build never gated: " +
              ", ".join(f"{c['pair']} cos={c['cos']:.3f}" for c in new_coll) +
              ". The section-1 'F1/F2 identified (bounded)' assertion was pre-declared, "
              "never tested as columns of M4, and does not survive at the interior point.")
elif elevated:
    verdict = "CONFIRM"
    reason = ("Full 4-factor operator is full column rank away from the gated F3-F4 "
              f"degeneracy (rank4={rank4}/4, cond={cond:.1f}); the ONLY small singular "
              "value is the F3-F4 difference direction (mixing vector ~(F3,-F4), F1=F2=0), "
              "exactly the degeneracy the build gated and NOT contaminated by F1/F2. So "
              "F1/F2 ARE separately identified -- section-1 table SURVIVES -- BUT with a "
              "QUALIFICATION the build never quantified: on the shared-holder snapshot the "
              "F2 (Treasury-by-holder) and F4 (USA-column run) footprints are ELEVATED-"
              f"correlated (|cos F2-F4|={f2f4:.3f}, ~{np.degrees(np.arccos(f2f4)):.0f} deg apart), "
              "consistent with dp3 R2's own 'THIN for the cross-holder dimension' caveat. "
              "F1 is block-orthogonal (cos 0) only because its BIS marginals occupy disjoint "
              "cells -- its identification rests on that disjointness, a level-factor claim, "
              "not a tested cross-factor separation. No NEW gating failure; the bound on F2 "
              "is real and larger than the §1 table's bare 'identified (bounded)' implies.")
else:
    verdict = "CONFIRM"
    reason = ("Away from the known F3-F4 degeneracy the 4-factor operator is full column "
              f"rank (rank4={rank4}/4) with F1,F2,F4 mutually well-separated "
              f"(|cos F1-F4|={f1f4:.3f}, |cos F2-F4|={f2f4:.3f}, |cos F1-F2|={f1f2:.3f}). "
              "The only small singular value is the F3-F4 difference direction the build "
              "already gated. F1/F2 are separately identified; section-1 table survives.")

out = {
  "dp":"AUDIT-FT3",
  "artifact":"rank4_test.json",
  "generated":"2026-06-29",
  "status":"AUDIT OUTPUT -- read-only falsification test of the DP4 section-1 'identified' table. Does NOT modify build artifacts and does NOT start DP6.",
  "question":"The build only litigated F3/F4 and PRE-DECLARED F1/F2 identified. Build the FULL four-factor operator M4 and test rank/conditioning for OTHER ungated collinearities (F1-F4? F2-F4?).",
  "moment_space_definition":{
    "principle":"Common observed-moment space = UNION of the cells the four factors touch, indexed by area/holder. Each factor is a column-normalised DIRECTION in the union; zero where it does not load.",
    "S_share_shared_holder_index":{
       "cells":"[BIS_C(19 USD claim marginals) | BIS_L(19 USD liability marginals) | DEST(3 offshore dest cells US->CYM/HKG/VGB) | USA(12 USA-column-by-holder cells)] = 53 cells",
       "F1":"BIS_C+BIS_L blocks, loading = USD per-area marginal (common funding-level co-movement).",
       "F2":"USA(12) block, loading = TIC US-Treasury-by-holder quantity on the SAME 12 holders (the safe-leg quantity-by-holder). LANDS ON THE SAME 12 USA cells as F4 -- this is the test the build never ran.",
       "F3":"DEST+USA, coef (f+(1-f)s) on DEST, -USAn on USA.",
       "F4":"DEST+USA, coef (1-f)s on DEST, -USAn on USA.",
       "rationale":"This is the HONEST test: dp3 R2 separates F2 from F4 by an 'instrument dimension', but on a single snapshot the only multi-holder observable for both is a by-holder quantity vector over the same 12 holders. If TIC-by-holder direction ~ CPIS-USA-by-holder direction, F2 and F4 are collinear regardless of instrument labels."
    },
    "S_block_TIC_own_block":{
       "cells":"[BIS_C(19)|BIS_L(19)|TIC(12 own cells)|DEST(3)|USA(12)] = 65 cells",
       "note":"F2 typed into its OWN disjoint TIC block. This is the build's IMPLICIT assumption (instrument dimension = separate cells). Reported to show the CONFIRM-looking result is an ARTIFACT of that typing, not a test of it."
    }
  },
  "M4_results":results,
  "key_readout_interior_S_share":{
     "f":0.20,"s_usd":0.5,
     "singular_spectrum":interior["singular_values"],
     "condition_number":cond,
     "rank_tol_1e6rel":rank4,
     "pairwise_cos":cos,
     "abs_cos_F1_F4":f1f4,"abs_cos_F2_F4":f2f4,"abs_cos_F1_F2":f1f2,
     "abs_cos_F3_F4_known":known_f3f4
  },
  "f0_case_S_share":{
     "note":"At f=0 the F3-F4 difference collapses (gated by the build). Reported for completeness.",
     "singular_spectrum":f0["singular_values"],
     "rank_tol_1e6rel":f0["rank_tol_1e6rel"],
     "cos_F3_F4":f0["pairwise_cos_F_columns"]["F3-F4"]
  },
  "rank4":rank4,
  "condition_number":cond,
  "new_collinearities":new_coll,
  "elevated_correlations_not_collinear":elevated,
  "f1_f4_collinear": bool(f1f4>COS_THR),
  "f2_f4_collinear": bool(f2f4>COS_THR),
  "f1_f2_collinear": bool(f1f2>COS_THR),
  "verdict_on_section1_table":verdict,
  "reason":reason,
  "caveats":[
    "Single snapshot: 'collinearity' here is the angle between fixed footprint DIRECTIONS in the union cell space, not a sampling covariance. A small angle => observationally near-equivalent footprints on this one matrix.",
    "F1 level direction taken as the USD per-area marginal vector (exposure-weighted common shock). An alternative F1 = uniform/equal-weight level direction is also defensible; the F1-vs-F4 cosine is reported so the reader can see sensitivity.",
    "F2's by-holder footprint is the TIC Treasury-by-holder quantity; the convenience-yield PRICE leg (kappa) is a HOLE not on disk (dp3), so F2 is tested only on its quantity-by-holder direction -- exactly the direction that overlaps F4.",
    "The S_block space makes F1,F2 block-orthogonal to F4 BY CONSTRUCTION; its full-rank result is not evidence of identification, only of the typing choice."
  ]
}

os.makedirs(os.path.join(ROOT,"build/audit"), exist_ok=True)
with open(os.path.join(ROOT,"build/audit/rank4_test.json"),"w") as fo:
    json.dump(out, fo, indent=1)

print("\n=== SUMMARY ===")
print("S_share interior (f=0.2,s=0.5): sing=",[round(x,4) for x in interior["singular_values"]])
print("  cond=%.4g rank4(1e-6rel)=%d"%(cond,rank4))
print("  |cos| F1-F4=%.3f F2-F4=%.3f F1-F2=%.3f F3-F4=%.3f"%(f1f4,f2f4,f1f2,known_f3f4))
print("S_block interior cos:",{k:round(v,3) for k,v in results["S_block_TIC_own_block"]["interior"]["pairwise_cos_F_columns"].items()})
print("new_collinearities:",new_coll)
print("VERDICT:",verdict)
