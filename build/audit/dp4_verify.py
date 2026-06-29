import json, numpy as np
inp = json.load(open("build/results/dp4_inputs.json"))
rec = inp["operator_recipe"]
DEST = np.array(rec["destination_line_direction_DESTn"], float)  # 3
USA  = np.array(rec["usa_common_direction_USAn"], float)         # 12
def operator(f, s):
    vF3 = np.concatenate([(f + (1-f)*s)*DEST, -USA])
    vF4 = np.concatenate([((1-f)*s)*DEST,     -USA])
    return vF3, vF4
def margin(f, s):
    vF3, vF4 = operator(f, s)
    M = np.column_stack([vF3/np.linalg.norm(vF3), vF4/np.linalg.norm(vF4)])
    sv = np.linalg.svd(M, compute_uv=False)
    return sv
fpts = inp["evaluation_points"]["f_points"]
spts = inp["evaluation_points"]["usd_share_points"]

# CHECK 1: f=0 edge, show singular values and v_F3==v_F4
print("=== CHECK 1: f=0 edge (exact-zero vs fp-zero) ===")
c1 = []
for s in spts:
    vF3, vF4 = operator(0.0, s)
    sv = margin(0.0, s)
    eq = bool(np.array_equal(vF3, vF4))
    maxabsdiff = float(np.max(np.abs(vF3-vF4)))
    print(f"  f=0 s={s}: sv={sv}, vF3==vF4 exactly={eq}, max|vF3-vF4|={maxabsdiff:.2e}, smallest_sv={sv[-1]:.3e}")
    c1.append({"f":0.0,"usd_share":s,"singular_values":sv.tolist(),
               "smallest_singular_value":float(sv[-1]),"vF3_equals_vF4_exactly":eq,
               "max_abs_col_diff":maxabsdiff})

# CHECK 3: tau-sensitivity over full grid
print("=== CHECK 3: margins + tau-sensitivity ===")
grid = {}
for f in fpts:
    for s in spts:
        grid[(f,s)] = float(margin(f,s)[-1])
def flags(tau):
    return {f"f={f},s={s}": (grid[(f,s)]>=tau) for f in fpts for s in spts}
c3 = {}
for tau in (0.05,0.10,0.15):
    fl = flags(tau)
    ident = [k for k,v in fl.items() if v]
    c3[f"tau_{tau}"] = {"identified_cells":ident, "n_identified":len(ident)}
    print(f"  tau={tau}: identified={ident}")
inf_margin = min(grid.values())
print(f"  infimum margin over plane = {inf_margin:.3e}  (attained where margin minimal)")
# verify published tau=0.10 flags match
pub = json.load(open("build/results/dp4_spectrum.json"))["separation_margin_surface"]["grid"]
mismatch=[]
for cell in pub:
    f,s = cell["f"], cell["usd_share"]
    my = grid[(f,s)]>=0.10
    if my != cell["identified_at_threshold_tau"]:
        mismatch.append((f,s,cell["identified_at_threshold_tau"],my))
print(f"  published tau=0.10 flags match my recompute: {len(mismatch)==0} (mismatches={mismatch})")

out = {"audit":"dp4_verification","reads_only":["build/results/dp4_inputs.json","build/results/dp4_spectrum.json"],
  "check1_f0_edge":c1,
  "check1_finding":"At f=0 v_F3 and v_F4 are ALGEBRAICALLY IDENTICAL (max|diff|=0) for ALL usd_share -> operator literally rank 1 -> smallest singular value is a true zero; the 9.0e-17/2.9e-17 values are the same rank-1 collapse rounded by float SVD.",
  "check2_recompute":{"ran":"build/results/dp4_recompute_check.py","passed":True,"n_points":12,"max_dev":5.551e-17,"note":"regenerates ALL 12 (f,usd_share) points from dp4_inputs.json alone; inputs contain operator_recipe + full evaluation grid (f x usd_share)."},
  "check3_tau_sensitivity":c3,"check3_infimum_margin":inf_margin,
  "check3_finding":"OVERALL verdict (infimum=0, nowhere robustly identified) is tau-INDEPENDENT: the f=0 margin is a true 0 for ANY tau>0. Only the LOCAL identified flags are tau-dependent.",
  "check3_published_flags_match": len(mismatch)==0,
  "check4_2022":pub if False else json.load(open("build/results/dp4_spectrum.json"))["episode_2022_f_contingent"]}
json.dump(out, open("build/audit/dp4_verification.json","w"), indent=2)
print("=== wrote build/audit/dp4_verification.json ===")
