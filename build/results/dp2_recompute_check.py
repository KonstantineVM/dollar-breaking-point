#!/usr/bin/env python3
# Independent verifier: regenerate DP2 residuals from build/model/ras_inputs.json ALONE.
import json, math, sys
M=json.load(open("/home/user/dollar-breaking-point/build/model/ras_inputs.json"))
ok=True

# --- CPIS consistency pass ---
p=M["passes"]["cpis_portfolio_consistency_pass"]
ROWS=p["row_labels"]; COLS=p["col_labels"]
ri={a:i for i,a in enumerate(ROWS)}; ci={a:j for j,a in enumerate(COLS)}
n_r,n_c=len(ROWS),len(COLS)
A=[[0.0]*n_c for _ in range(n_r)]
for r,c,v in p["seed_matrix_sparse_rcv"]:
    A[ri[r]][ci[c]]=v
rt=p["row_targets"]; ct=p["col_targets"]
log=[]
for it in range(1,p["n_passes"]+1):
    for i in range(n_r):
        s=sum(A[i]); f=rt[i]/s if s>0 else 1.0
        for j in range(n_c): A[i][j]*=f
    for j in range(n_c):
        s=sum(A[i][j] for i in range(n_r)); f=ct[j]/s if s>0 else 1.0
        for i in range(n_r): A[i][j]*=f
    rr=[abs(sum(A[i])-rt[i]) for i in range(n_r)]
    cr=[abs(sum(A[i][j] for i in range(n_r))-ct[j]) for j in range(n_c)]
    rL2=math.sqrt(sum(x*x for x in rr)); cL2=math.sqrt(sum(x*x for x in cr))
    log.append((rL2,cL2))
    if rL2<p["tolerance"] and cL2<p["tolerance"]: break
recomputed_final=log[-1]
persisted_final=(p["per_pass_residual_norms"][-1]["row_resid_L2"],p["per_pass_residual_norms"][-1]["col_resid_L2"])
match_cpis = abs(recomputed_final[0]-persisted_final[0])<1e-6 and len(log)==len(p["per_pass_residual_norms"])
print("CPIS pass: recomputed passes=%d final_row_L2=%.6g | persisted passes=%d final_row_L2=%.6g | MATCH=%s"
      %(len(log),recomputed_final[0],len(p["per_pass_residual_norms"]),persisted_final[0],match_cpis))

# --- BIS floor ---
b=M["passes"]["bis_banking_marginal_reconciliation"]
sumC=sum(b["claims_position_C_usd_mn"]); sumL=sum(b["liabilities_position_L_usd_mn"])
floor=sumL-sumC
match_bis = abs(floor-b["floor_pre_ras_usd_mn"])<1e-3 \
        and abs(sumC-b["sum_claims_usd_mn"])<1e-3 and abs(sumL-b["sum_liabilities_usd_mn"])<1e-3
print("BIS floor: recomputed claims=%.1f liab=%.1f floor=%.1f | persisted floor=%.1f | MATCH=%s"
      %(sumC,sumL,floor,b["floor_pre_ras_usd_mn"],match_bis))

ok = match_cpis and match_bis
result={"verifier":"dp2_recompute_check","passed":ok,
        "cpis_consistency_pass_reproduced":match_cpis,
        "bis_floor_reproduced":match_bis,
        "recomputed_cpis_final_row_L2":recomputed_final[0],
        "recomputed_bis_floor_usd_mn":round(floor,3)}
json.dump(result,open("/home/user/dollar-breaking-point/build/results/dp2_recompute_check.json","w"),indent=1)
print("VERIFIER PASSED" if ok else "VERIFIER FAILED"); sys.exit(0 if ok else 1)
