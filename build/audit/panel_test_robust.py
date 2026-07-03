#!/usr/bin/env python3
"""
Robustness layer for FALSIFICATION TEST 2. Two confounds to rule out before the verdict:

(R1) The CYM->USA series has a discontinuity at 2023-S2 (1.72T -> 3.86T, +124%), a
     likely reclassification/coverage break, NOT a portfolio flow. It could inflate
     contemporaneous co-movement. Re-run with CYM dropped from the holder set.

(R2) The dominant signal is a COMMON growth/valuation trend across all holders (every
     US-column series dips at 2022-S1 and trends up). If that common factor is what
     makes F3 and F4 footprints collinear, then DEMEANING each period's holder diffs
     by the cross-holder mean (removing the common factor) is the real test of whether
     an IDIOSYNCRATIC lead/lag (F4 contagion) or idiosyncratic substitution (F3) signal
     survives. If after removing the common factor the within-holder US-vs-destination
     correlation turns NEGATIVE for a coherent set of holders AND a clean lead/lag order
     appears, that would be evidence FOR separation. If not, the panel cannot separate.

This reuses raw pulls; READ-ONLY on artifacts; prints only (merged into panel_test.json
by panel_test_finalize.py).
"""
import re, glob, os, math
from itertools import combinations

PANEL_DIR = "/home/user/dollar-breaking-point/build/data/imf_cpis/panel"
PERIODS = ["2020-S1","2020-S2","2021-S1","2021-S2","2022-S1","2022-S2",
           "2023-S1","2023-S2","2024-S1","2024-S2","2025-S1"]

def parse(path):
    txt = open(path).read()
    return {tp: float(ov) for tp, ov in
            re.findall(r'TIME_PERIOD="([^"]*)"\s+OBS_VALUE="([^"]*)"', txt)}

dest, uscol = {}, {}
for f in sorted(glob.glob(os.path.join(PANEL_DIR, "*.xml"))):
    base = os.path.basename(f)[:-4]
    if base.startswith("_"): continue
    s = parse(f)
    if base.startswith("dest_USA_to_"): dest[base.replace("dest_USA_to_","")] = s
    elif base.startswith("uscol_") and base.endswith("_to_USA"):
        uscol[base[len("uscol_"):-len("_to_USA")]] = s

def diffs(s):
    v = [s.get(p) for p in PERIODS]
    return [(v[i]-v[i-1]) if (v[i] is not None and v[i-1] is not None) else None
            for i in range(1,len(v))]

def pcorr(x,y):
    pr=[(a,b) for a,b in zip(x,y) if a is not None and b is not None]
    n=len(pr)
    if n<3: return None,n
    mx=sum(a for a,_ in pr)/n; my=sum(b for _,b in pr)/n
    sx=math.sqrt(sum((a-mx)**2 for a,_ in pr)); sy=math.sqrt(sum((b-my)**2 for _,b in pr))
    if sx==0 or sy==0: return None,n
    return sum((a-mx)*(b-my) for a,b in pr)/(sx*sy), n

def offdiff():
    out=[]
    for i in range(1,len(PERIODS)):
        s=0.0
        for k in ["CYM","HKG","VGB"]:
            s += dest[k][PERIODS[i]]-dest[k][PERIODS[i-1]]
        out.append(s)
    return out
OFF = offdiff()

# ---- R1: drop CYM holder (reclassification break) ----
H_noCYM = [h for h in sorted(uscol) if h != "CYM"]
usd = {h: diffs(uscol[h]) for h in sorted(uscol)}
f3_noCYM = {h: pcorr(usd[h], OFF)[0] for h in H_noCYM}
m = [v for v in f3_noCYM.values() if v is not None]
print("R1 (CYM holder dropped) mean within-holder US-vs-offshore corr:", sum(m)/len(m))
print("R1 count NEGATIVE (F3 substitution sign):", sum(1 for v in m if v < 0), "of", len(m))

# ---- R2: remove common factor (demean each transition by cross-holder mean) ----
H = sorted(uscol)
# common factor per transition = mean of holder diffs (exclude CYM break to avoid contamination)
Hc = [h for h in H if h != "CYM"]
common = []
for t in range(10):
    vals = [usd[h][t] for h in Hc if usd[h][t] is not None]
    common.append(sum(vals)/len(vals) if vals else None)
usd_resid = {h: [ (usd[h][t]-common[t]) if (usd[h][t] is not None and common[t] is not None) else None
                  for t in range(10)] for h in H}
# also remove common factor from the offshore destination diffs? No -- F3 asks whether a
# holder's IDIOSYNCRATIC US move co-moves with the offshore-China pool. Keep OFF as-is.
f3_resid = {h: pcorr(usd_resid[h], OFF)[0] for h in Hc}
mr = [v for v in f3_resid.values() if v is not None]
print("\nR2 (common factor removed) mean idiosyncratic US-vs-offshore corr:", sum(mr)/len(mr))
print("R2 count NEGATIVE (F3 substitution sign):", sum(1 for v in mr if v < 0), "of", len(mr))
for h in Hc:
    print(f"   {h}: resid corr = {f3_resid[h]}")

# R2 lead/lag on residuals: any consistent cross-holder ordering (F4 contagion)?
def lead(a,b):  # a leads b: corr(a(t-1), b(t))
    return pcorr(a[:-1], b[1:])[0]
ll=[]
for a,b in combinations(Hc,2):
    rab=lead(usd_resid[a],usd_resid[b]); rba=lead(usd_resid[b],usd_resid[a])
    if rab is not None and rba is not None:
        ll.append(abs(rab-rba))
print("\nR2 residual lead/lag mean pairwise asymmetry:", sum(ll)/len(ll) if ll else None,
      "(n pairs=",len(ll),", each from <=9 obs)")

# footprint cosine on residuals
f4_foot={}
ct=[]
for a,b in combinations(Hc,2):
    r=pcorr(usd_resid[a],usd_resid[b])[0]
    if r is not None: ct.append((a,b,r))
for h in Hc:
    rs=[r for a,b,r in ct if a==h or b==h]
    f4_foot[h]=sum(rs)/len(rs) if rs else None
keys=[h for h in Hc if f4_foot[h] is not None and f3_resid[h] is not None]
av=[f4_foot[k] for k in keys]; bv=[f3_resid[k] for k in keys]
na=math.sqrt(sum(x*x for x in av)); nb=math.sqrt(sum(x*x for x in bv))
cos=sum(x*y for x,y in zip(av,bv))/(na*nb) if na and nb else None
print("R2 residual footprint cosine F4 vs F3:", cos)
