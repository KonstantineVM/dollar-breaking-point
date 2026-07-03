#!/usr/bin/env python3
"""
FALSIFICATION TEST 2 -- execute resolution path (a).
Build the temporal lead/lag discriminator from the 11-period CPIS/PIP panel and
test whether the time dimension breaks the f=0 rank-1 degeneracy that drives the
DP5 'F3/F4 not identified' verdict.

READ-ONLY on build artifacts. Writes only build/audit/panel_test.json.
Raw pulls already saved under build/data/imf_cpis/panel/*.xml.

Method (stated in full):
 The DP4 operator is rank-1 at f=0 because, on ONE snapshot, the 12 USA-column
 cells load on a single shared F3=F4 direction: a holder's US-claim level cannot
 be ordered in time against (F4) other holders' US-claim moves or against (F3)
 that holder's own offshore-China destination move. A panel supplies that order.

 F4 (dollar-run / contagion) footprint: cross-holder LEAD/LAG co-movement in the
   reductions of the USA-column (holder a's US drop LEADS holder b's US drop).
   Operationalized as the lead-1 cross-correlation between holders' US-column
   first-differences: corr( d_a(t-1), d_b(t) ). A contagion structure shows a
   systematic asymmetry (some holders consistently lead) AND positive
   contemporaneous co-movement of US-claim reductions across holders.

 F3 (sanctions substitution) footprint: WITHIN-holder negative correlation between
   a holder's OWN US-column change and the offshore-China DESTINATION change
   (US->CYM/HKG/VGB/CHN). Substitution = a holder pulls out of US claims while the
   offshore-China destination pool rises at the same time. Operationalized as
   corr( d(US-column move), d(destination move) ) within the panel; F3 predicts a
   negative within-period correlation for the substituting holders.

 SEPARATION TEST at f=0: the two footprints are DISTINGUISHABLE without pinning f
   iff (i) the F4 cross-holder lead/lag structure is statistically present and
   ordered (not symmetric noise) AND (ii) the F3 within-holder US-vs-destination
   sign is identifiable, AND (iii) these two load on DIFFERENT temporal directions
   so that the USA-column block is no longer a single shared direction. If either
   footprint is absent/indistinct in the panel, or the destination cells are too
   smooth to carry an F3 signal, the time dimension does NOT break the degeneracy.
"""
import re, glob, os, json, math
from itertools import combinations

PANEL_DIR = "/home/user/dollar-breaking-point/build/data/imf_cpis/panel"
OUT = "/home/user/dollar-breaking-point/build/audit/panel_test.json"

PERIODS = ["2020-S1","2020-S2","2021-S1","2021-S2","2022-S1","2022-S2",
           "2023-S1","2023-S2","2024-S1","2024-S2","2025-S1"]

def parse(path):
    txt = open(path).read()
    d = {}
    for tp, ov in re.findall(r'TIME_PERIOD="([^"]*)"\s+OBS_VALUE="([^"]*)"', txt):
        d[tp] = float(ov)
    return d

# load
dest = {}   # destination cells USA->X
uscol = {}  # holder->USA
for f in sorted(glob.glob(os.path.join(PANEL_DIR, "*.xml"))):
    base = os.path.basename(f)[:-4]
    if base.startswith("_"): continue
    series = parse(f)
    if base.startswith("dest_USA_to_"):
        dest[base.replace("dest_USA_to_","")] = series
    elif base.startswith("uscol_") and base.endswith("_to_USA"):
        h = base[len("uscol_"):-len("_to_USA")]
        uscol[h] = series

def vec(series):
    return [series.get(p, None) for p in PERIODS]

def diffs(series):
    v = vec(series)
    out = []
    for i in range(1, len(v)):
        if v[i] is None or v[i-1] is None:
            out.append(None)
        else:
            out.append(v[i]-v[i-1])
    return out  # length 10, aligned to transitions PERIODS[i-1]->PERIODS[i]

def pcorr(x, y):
    pairs = [(a,b) for a,b in zip(x,y) if a is not None and b is not None]
    n = len(pairs)
    if n < 3: return None, n
    mx = sum(a for a,_ in pairs)/n
    my = sum(b for _,b in pairs)/n
    sx = math.sqrt(sum((a-mx)**2 for a,_ in pairs))
    sy = math.sqrt(sum((b-my)**2 for _,b in pairs))
    if sx == 0 or sy == 0: return None, n
    cov = sum((a-mx)*(b-my) for a,b in pairs)
    return cov/(sx*sy), n

def lead_lag_xcorr(da, db):
    """corr(da(t-1), db(t)): does a LEAD b? Use diff series (len 10)."""
    x = da[:-1]   # t-1
    y = db[1:]    # t
    return pcorr(x, y)

HOLDERS = sorted(uscol.keys())

# raw panel for the report
raw = {
    "destination_cells_USA_to_X": {k: {p: dest[k].get(p) for p in PERIODS} for k in sorted(dest)},
    "us_column_holder_to_USA":    {k: {p: uscol[k].get(p) for p in PERIODS} for k in HOLDERS},
}

# ---- F4: cross-holder lead/lag in US-column first-differences ----
usd = {h: diffs(uscol[h]) for h in HOLDERS}

leadlag = []   # corr(a leads b)
contemp = []   # contemporaneous corr of US-column diffs across holder pairs
for a, b in combinations(HOLDERS, 2):
    r_ab, n_ab = lead_lag_xcorr(usd[a], usd[b])   # a leads b
    r_ba, n_ba = lead_lag_xcorr(usd[b], usd[a])   # b leads a
    r_c, n_c   = pcorr(usd[a], usd[b])            # contemporaneous
    if r_ab is not None: leadlag.append((a, b, r_ab))
    if r_ba is not None: leadlag.append((b, a, r_ba))
    if r_c  is not None: contemp.append((a, b, r_c))

# Asymmetry of the lead/lag structure: for an ORDERED contagion structure we'd
# expect, for many pairs, |corr(a->b) - corr(b->a)| large and a consistent
# direction. Symmetric noise => mean lead/lag ~ mean lag/lead, low asymmetry.
def mean(xs): return sum(xs)/len(xs) if xs else None
ll_vals = [r for *_ , r in leadlag]
ct_vals = [r for *_ , r in contemp]

# Pair asymmetry magnitude
asym = []
seen = {}
for a, b, r in leadlag:
    seen[(a,b)] = r
for a, b in combinations(HOLDERS, 2):
    if (a,b) in seen and (b,a) in seen:
        asym.append(abs(seen[(a,b)] - seen[(b,a)]))

# ---- F3: within-holder US-column vs offshore-China destination ----
# Each holder's own US-column change vs the change in the offshore-China
# destination pool. The destination pool is USA-as-holder -> offshore/China.
# F3 substitution prediction: a holder reducing US claims co-occurs with a RISE
# in the offshore-China destination => negative within-holder correlation.
# Offshore-China destination = sum of US->CYM, US->HKG, US->VGB, US->CHN
# (the pool the f=0 degeneracy lives on).
def pooled_dest_diff():
    keys = [k for k in ["CYM","HKG","VGB","CHN"] if k in dest]
    out = []
    for i in range(1, len(PERIODS)):
        s = 0.0; ok = True
        for k in keys:
            a = dest[k].get(PERIODS[i]); b = dest[k].get(PERIODS[i-1])
            if a is None or b is None: ok = False; break
            s += (a-b)
        out.append(s if ok else None)
    return out, keys

destdiff, dest_keys = pooled_dest_diff()
# offshore-only (the CYM/HKG/VGB pool, where the masked-China nationality sits)
def offshore_only_diff():
    keys = [k for k in ["CYM","HKG","VGB"] if k in dest]
    out = []
    for i in range(1, len(PERIODS)):
        s = 0.0; ok = True
        for k in keys:
            a = dest[k].get(PERIODS[i]); b = dest[k].get(PERIODS[i-1])
            if a is None or b is None: ok = False; break
            s += (a-b)
        out.append(s if ok else None)
    return out, keys
offdiff, off_keys = offshore_only_diff()

f3_within = {}
for h in HOLDERS:
    r_pool, n1 = pcorr(usd[h], destdiff)      # vs CYM+HKG+VGB+CHN
    r_off,  n2 = pcorr(usd[h], offdiff)       # vs CYM+HKG+VGB only
    f3_within[h] = {"corr_us_vs_dest_pool": r_pool, "n_pool": n1,
                    "corr_us_vs_offshore": r_off, "n_off": n2}

f3_pool_vals = [v["corr_us_vs_dest_pool"] for v in f3_within.values() if v["corr_us_vs_dest_pool"] is not None]
f3_off_vals  = [v["corr_us_vs_offshore"]  for v in f3_within.values() if v["corr_us_vs_offshore"]  is not None]

# ---- separation diagnostics ----
# F4 present & ordered?  contemp co-movement positive on average AND lead/lag
# asymmetry materially > 0 with a consistent sign.
# F3 present?            within-holder US-vs-destination correlation systematically
# negative (substitution) and distinguishable from the F4 contemporaneous pattern.

# Build the two candidate "temporal footprint" vectors over holders and check
# whether they are DISTINCT directions (the crux: at f=0 they were collinear).
# F4 footprint per holder = mean contemporaneous co-move of that holder with others.
f4_foot = {}
for h in HOLDERS:
    rs = []
    for a, b, r in contemp:
        if a == h: rs.append(r)
        if b == h: rs.append(r)
    f4_foot[h] = mean(rs)
# F3 footprint per holder = within-holder US-vs-offshore correlation
f3_foot = {h: f3_within[h]["corr_us_vs_offshore"] for h in HOLDERS}

# cosine between the two footprint vectors across holders
common = [h for h in HOLDERS if f4_foot[h] is not None and f3_foot[h] is not None]
def cosvec(d1, d2, keys):
    a = [d1[k] for k in keys]; b = [d2[k] for k in keys]
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(x*x for x in b))
    if na == 0 or nb == 0: return None
    return sum(x*y for x,y in zip(a,b))/(na*nb)
foot_cos = cosvec(f4_foot, f3_foot, common) if len(common) >= 3 else None

report = {
  "test": "FALSIFICATION TEST 2 -- execute DP5 resolution path (a): temporal lead/lag discriminator on the CPIS/PIP panel.",
  "generated": "2026-06-29",
  "checked_on": "2026-06-29",
  "grounding": {
    "api": "IMF SDMX 2.1 api.imf.org dataflow IMF.STA,PIP,5.0.0",
    "key_form_verified_fresh_2026-06-29": "COUNTRY.A.P_TOTINV_P_USD.S1.S1.COUNTERPART.S (holder.A.indicator.S1.S1.issuer.S)",
    "probe": "USA.A.P_TOTINV_P_USD.S1.S1.CYM.S?startPeriod=2020&endPeriod=2025 returned 11 semiannual periods; 2025-S1 = 2,798,130,000,000 matches dp2_residual us_to_cym.",
    "raw_pulls_dir": "build/data/imf_cpis/panel/*.xml"
  },
  "periods": PERIODS,
  "panel_periods_pulled": len(PERIODS),
  "cells_pulled": {
    "destination_USA_to": sorted(dest.keys()),
    "us_column_holders_to_USA": HOLDERS,
    "n_series": len(dest) + len(uscol)
  },
  "raw_panel": raw,
  "method": "See module docstring. F4 = cross-holder lead/lag + contemporaneous co-movement of US-column first-differences; F3 = within-holder US-column vs offshore-China destination first-difference correlation. Separation at f=0 holds iff both footprints are present, statistically distinguishable, and load on different temporal directions (footprint cosine away from +/-1).",
  "F4_cross_holder_lead_lag": {
    "n_holder_pairs": len(list(combinations(HOLDERS,2))),
    "mean_leadlag_xcorr_corr(a_leads_b)": mean(ll_vals),
    "mean_contemporaneous_US_diff_corr": mean(ct_vals),
    "mean_pairwise_leadlag_asymmetry_abs": mean(asym),
    "note": "10 first-difference transitions per holder; lead/lag uses 9 overlapping pairs. With n<=9 per pair, individual correlations are very low power."
  },
  "F3_within_holder_us_vs_destination": {
    "destination_pool_keys": dest_keys,
    "offshore_pool_keys": off_keys,
    "per_holder": f3_within,
    "mean_corr_us_vs_dest_pool": mean(f3_pool_vals),
    "mean_corr_us_vs_offshore": mean(f3_off_vals)
  },
  "separation_diagnostic": {
    "f4_footprint_per_holder_contemp": f4_foot,
    "f3_footprint_per_holder_within": f3_foot,
    "footprint_cosine_F4_vs_F3_across_holders": foot_cos,
    "holders_in_common": common
  }
}

# verdict logic computed in a second pass below (printed), then injected.
with open(OUT, "w") as fh:
    json.dump(report, fh, indent=2)

print("=== KEY STATS ===")
print("periods pulled:", len(PERIODS))
print("series pulled:", len(dest)+len(uscol))
print("F4 mean lead/lag xcorr:", report["F4_cross_holder_lead_lag"]["mean_leadlag_xcorr_corr(a_leads_b)"])
print("F4 mean contemp US-diff corr:", report["F4_cross_holder_lead_lag"]["mean_contemporaneous_US_diff_corr"])
print("F4 mean pairwise lead/lag asymmetry:", report["F4_cross_holder_lead_lag"]["mean_pairwise_leadlag_asymmetry_abs"])
print("F3 mean corr US vs dest pool:", report["F3_within_holder_us_vs_destination"]["mean_corr_us_vs_dest_pool"])
print("F3 mean corr US vs offshore :", report["F3_within_holder_us_vs_destination"]["mean_corr_us_vs_offshore"])
print("footprint cosine F4 vs F3   :", foot_cos)
print("\nF3 per-holder US-vs-offshore corr:")
for h in HOLDERS:
    print(f"  {h}: {f3_foot[h]}")
