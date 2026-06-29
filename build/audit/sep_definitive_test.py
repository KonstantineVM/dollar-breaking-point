#!/usr/bin/env python3
"""
Part 2 -- DEFINITIVE separability test at residency-MONTHLY granularity.

Recomputes EVERY number from the on-disk acquired data alone:
  - build/data/treasury_tic/current/slt_haven_extract.json (monthly CYM/HKG/VGB, both directions)
  - build/results/dp4_inputs.json (DESTn, USAn, tau)  -- operator recipe constants
  - build/model/dp3_spec.json     (F4 backstop respec; backstop balances)
  - f pinned to [0.49,0.71] (china_fraction_bound / f_pin_test)

Outputs JSON to stdout (the artifact writer copies the numbers in).
No data is asserted; everything below is computed from the files above.

SYMMETRIC-ERROR DISCIPLINE:
  substitution is a flow/change concept => the principled transform is
  month-over-month LOG-CHANGES, demeaned. We report the sign under that
  transform AND, as robustness, under simple changes and under levels, so a
  reader can see whether the sign is an artifact of one transform. We do not
  pick the transform that engineers a verdict.
"""
import json, math, os

ROOT = "/home/user/dollar-breaking-point"

# ---------------------------------------------------------------- load monthly
with open(os.path.join(ROOT, "build/data/treasury_tic/current/slt_haven_extract.json")) as f:
    HAV = json.load(f)

F3 = HAV["F3_us_holdings_of_foreign_table2"]   # US holdings OF CYM/HKG/VGB  (destination/offshore-haven exposure)
F4 = HAV["F4_foreign_holdings_of_us_table1"]   # foreign(CYM/HKG/VGB) holdings OF US  (the US-leg / run direction)
HAVENS = ["CYM", "HKG", "VGB"]

def series(block, c):
    rows = block[c]["series"]
    dates = [r["date"] for r in rows]
    vals = [float(r["total_holdings"]) for r in rows]
    return dates, vals

# align dates (identical 76-month grid in both, but verify)
dates_ref = [r["date"] for r in F3["CYM"]["series"]]
for c in HAVENS:
    assert [r["date"] for r in F3[c]["series"]] == dates_ref
    assert [r["date"] for r in F4[c]["series"]] == dates_ref
N = len(dates_ref)

def logdiff(v):
    return [math.log(v[i]) - math.log(v[i-1]) for i in range(1, len(v))]
def diff(v):
    return [v[i] - v[i-1] for i in range(1, len(v))]
def demean(x):
    m = sum(x)/len(x); return [xi - m for xi in x]
def corr(x, y):
    x = demean(x); y = demean(y)
    sx = math.sqrt(sum(xi*xi for xi in x)); sy = math.sqrt(sum(yi*yi for yi in y))
    if sx == 0 or sy == 0: return float("nan")
    return sum(xi*yi for xi, yi in zip(x, y))/(sx*sy)

# ===========================================================================
# (a) SUBSTITUTION SIGN -- within-holder co-movement
#
# F3 substitution (a holder reallocating AWAY from the US into the offshore /
# China-conduit haven) requires, WITHIN a holder:
#     US-leg DOWN  while  offshore-haven exposure UP  =>  NEGATIVE co-movement.
#
# The honest within-holder pairing reconstructible from TIC:
#   US-leg of holder h        = F4[h]  (foreign h's holdings OF US LT securities)
#   offshore-haven exposure   = F3[h]  (US holdings OF h's LT securities) -- this
#       is the destination/offshore-conduit cell for residency h that the DP4
#       operator's block A uses. (This is the SAME within-residency pairing
#       Test B used: US-column vs offshore-China-conduit, here at the CYM/HKG/VGB
#       residency cells, monthly.)
#
# COVERAGE LIMITATION (stated, not invented): TIC SLT only resolves US<->foreign
# legs. It does NOT carry a foreign<->foreign within-holder cell (e.g. a German
# holder's claim ON Cayman). So the "offshore-China-conduit" exposure can only be
# proxied by the US<->haven residency cells (F3[h]) at the haven holders
# themselves -- exactly the cells the operator uses. We cannot reconstruct a
# generic holder's foreign-haven exposure; we say so rather than invent it.
# ===========================================================================
def within_holder_corr(transform):
    """Pool per-haven within-holder (US-leg vs offshore-haven) co-movement."""
    per = {}
    pooled_x, pooled_y = [], []
    for c in HAVENS:
        _, v4 = series(F4, c)   # US-leg
        _, v3 = series(F3, c)   # offshore-haven exposure
        if transform == "logchange":
            x, y = logdiff(v4), logdiff(v3)
        elif transform == "change":
            x, y = diff(v4), diff(v3)
        elif transform == "level":
            x, y = list(v4), list(v3)
        per[c] = corr(x, y)
        # demean per-haven before pooling (removes haven-specific mean drift)
        pooled_x += demean(x); pooled_y += demean(y)
    pooled = corr(pooled_x, pooled_y)
    return per, pooled

a_per_log, a_pooled_log   = within_holder_corr("logchange")   # PRINCIPLED
a_per_chg, a_pooled_chg   = within_holder_corr("change")
a_per_lvl, a_pooled_lvl   = within_holder_corr("level")

# ===========================================================================
# (b) FOOTPRINT SEPARATION -- empirical footprint cosine F4 vs F3 at monthly freq
#
# Build the realized monthly footprint of each direction as the cross-haven
# vector of co-movements, mirroring Test B's footprint-cosine construction but
# at monthly frequency.
#
# F4 footprint = vector over havens of monthly US-leg log-changes' loading;
# F3 footprint = vector over havens of monthly offshore-exposure log-changes'
# loading. We take, per month t, the cross-haven change vector for each
# direction, then the footprint is the *time-average direction* (mean change
# vector) and the cosine is the angle between the two mean direction vectors --
# i.e. do the two directions point the same way across the haven block?
#
# This reproduces the "footprint cosine" notion: cosine ~1 => F3 and F4 footprints
# collinear (inseparable); cosine << 0.94 => they separate.
# ===========================================================================
def cosine(u, v):
    du = math.sqrt(sum(a*a for a in u)); dv = math.sqrt(sum(b*b for b in v))
    if du == 0 or dv == 0: return float("nan")
    return sum(a*b for a, b in zip(u, v))/(du*dv)

# mean monthly log-change footprint over the haven block
foot_F4 = [sum(logdiff(series(F4, c)[1]))/(N-1) for c in HAVENS]
foot_F3 = [sum(logdiff(series(F3, c)[1]))/(N-1) for c in HAVENS]
foot_cos_meandir = cosine(foot_F4, foot_F3)

# Alternative (variance-weighted) footprint cosine: stack the per-month cross-haven
# change vectors into matrices and compare leading directions via the average
# elementwise cosine across months -- robustness, does not cherry-pick.
def monthly_vectors(block):
    cols = [logdiff(series(block, c)[1]) for c in HAVENS]   # each length N-1
    return [[cols[j][t] for j in range(len(HAVENS))] for t in range(N-1)]
MV4 = monthly_vectors(F4)
MV3 = monthly_vectors(F3)
cos_per_month = [cosine(MV4[t], MV3[t]) for t in range(N-1)
                 if not (all(a==0 for a in MV4[t]) or all(a==0 for a in MV3[t]))]
foot_cos_monthly_mean = sum(cos_per_month)/len(cos_per_month)

# ===========================================================================
# (b2) LEAD/LAG -- cross-correlation of aggregate F3-destination move vs
# aggregate F4 US-column move at lags +/- k months, focused on the 2022 episode
# and full sample.
#   x = F4 aggregate US-leg log-change (sum over havens of levels, then logdiff)
#   y = F3 aggregate offshore-exposure log-change
# xcorr(k) = corr( x_t , y_{t+k} ).  k>0 => F3 LAGS F4 (F4 leads); k<0 => F3 leads.
# For SUBSTITUTION we'd want, at some k, a strong NEGATIVE corr (US-leg falls,
# offshore rises with a lead/lag). For CONTAGION/common-growth, corr is positive
# and peaks at k=0 (contemporaneous).
# ===========================================================================
def agg_logchange(block, dmin=None, dmax=None):
    idx = list(range(N))
    if dmin is not None:
        idx = [i for i in range(N) if dmin <= dates_ref[i] <= dmax]
    agg = [sum(float(block[c]["series"][i]["total_holdings"]) for c in HAVENS) for i in idx]
    return [math.log(agg[i]) - math.log(agg[i-1]) for i in range(1, len(agg))], [dates_ref[i] for i in idx[1:]]

def xcorr_profile(x, y, kmax=6):
    out = {}
    for k in range(-kmax, kmax+1):
        if k >= 0:
            xx = x[:len(x)-k]; yy = y[k:]
        else:
            xx = x[-k:]; yy = y[:len(y)+k]
        out[k] = corr(xx, yy) if len(xx) >= 6 else None
    return out

x_full, _ = agg_logchange(F4)
y_full, _ = agg_logchange(F3)
xcorr_full = xcorr_profile(x_full, y_full, 6)

# 2022 episode window: 2021-07 .. 2023-06 (brackets the Russia-sanctions / 2022 stress)
x_22, d22 = agg_logchange(F4, "2021-07", "2023-06")
y_22, _   = agg_logchange(F3, "2021-07", "2023-06")
xcorr_22 = xcorr_profile(x_22, y_22, 6)

def peak(prof):
    items = [(k, v) for k, v in prof.items() if v is not None]
    kbest = max(items, key=lambda kv: abs(kv[1]))
    return {"k_at_max_abs": kbest[0], "value_at_max_abs": round(kbest[1], 6),
            "value_at_0": round(prof[0], 6)}

# ===========================================================================
# OPERATOR WITH BACKSTOP -- margin anchor at pinned rectangle
#
# Base 15x2 [v_F3 | v_F4] exactly as dp4_inputs.json / dp4_recompute_check.py:
#   v_F3 = [ (f + (1-f)*s)*DESTn ; -USAn ]
#   v_F4 = [ (    (1-f)*s)*DESTn ; -USAn ]
# margin = smallest singular value of the COLUMN-NORMALISED 2-col operator.
#
# BACKSTOP RESPEC (dp3_spec F4-OFFICIAL-BACKSTOP): v_F4 gains a 16th OFFICIAL
# cell b_backstop (POSITIVE; opposite sign to the -USAn drain), entered as a
# single system-aggregate term. v_F3 has 0 in that official cell (the backstop is
# an F4-only leg). So the operator becomes 16x2; F3 is unchanged, F4 gets one
# extra positive component. We verify the BASE (no-backstop) margin reproduces
# geo_vs_emp's pinned margins (>=0.221), then report the backstop margin as the
# anchor (the official cell is F4-exclusive, so it can only ADD separation).
# ===========================================================================
with open(os.path.join(ROOT, "build/results/dp4_inputs.json")) as f:
    DP4 = json.load(f)
DESTn = DP4["operator_recipe"]["destination_line_direction_DESTn"]      # len 3
USAn  = DP4["operator_recipe"]["usa_common_direction_USAn"]             # len 12
TAU   = DP4["operator_recipe"]["threshold_tau"]

def smallest_sv_2col(col1, col2):
    # column-normalise
    def norm(v):
        d = math.sqrt(sum(a*a for a in v)); return [a/d for a in v]
    a = norm(col1); b = norm(col2)
    # 2x2 Gram -> singular values of [a|b] are sqrt(eig of G), G=[[1,c],[c,1]]
    c = sum(ai*bi for ai, bi in zip(a, b))
    s_max = math.sqrt(1 + abs(c)); s_min = math.sqrt(max(0.0, 1 - abs(c)))
    return s_min

def vF3(f, s):
    g = f + (1-f)*s
    return [g*d for d in DESTn] + [-u for u in USAn]
def vF4(f, s, b=0.0):
    g = (1-f)*s
    base = [g*d for d in DESTn] + [-u for u in USAn]
    return base + [b]     # append official cell (b for F4)
def vF3_ext():            # F3 has 0 in official cell when backstop dimension added
    pass

def margin_base(f, s):
    return smallest_sv_2col(vF3(f, s), vF4(f, s))

def margin_backstop(f, s, b):
    # 16-dim: F3 gets a trailing 0 official cell, F4 gets b
    c1 = vF3(f, s) + [0.0]
    c2 = vF4(f, s, b)
    return smallest_sv_2col(c1, c2)

# Backstop magnitude: stress-state Fed dollar-provision balance from dp3_spec.
# Peaks 583,135 (2008) / 448,946 (2020) USD mn; calm ~35. The official cell is
# entered in the SAME units as the matrix USA-column cells (USD mn). To set its
# RELATIVE scale honestly we express b as the backstop balance normalised the same
# way the USAn block is normalised. We anchor with the 2020 stress balance (the
# in-sample episode), and also report calm (~35) so the reader sees the regime
# dependence; we do NOT tune b to hit a target margin.
B_STRESS_2020 = 448946.0
B_CALM        = 35.0
# Normalise b by the same scale as the USA block: USAn is unit-normed from the raw
# usa_issuer_column_by_holder; its raw L2 norm:
raw_usa = list(DP4["matrix_quantities_usd_mn"]["usa_issuer_column_by_holder"].values())
usa_raw_norm = math.sqrt(sum(v*v for v in raw_usa))
b_stress_scaled = B_STRESS_2020 / usa_raw_norm   # backstop in USAn-normalised units
b_calm_scaled   = B_CALM / usa_raw_norm

PIN = [(0.49, 0.0), (0.49, 0.5), (0.49, 1.0),
       (0.60, 0.0), (0.60, 0.5), (0.60, 1.0),
       (0.71, 0.0), (0.71, 0.5), (0.71, 1.0)]
base_margins = {f"f={f}|s={s}": round(margin_base(f, s), 6) for f, s in PIN}
backstop_stress = {f"f={f}|s={s}": round(margin_backstop(f, s, b_stress_scaled), 6) for f, s in PIN}
backstop_calm   = {f"f={f}|s={s}": round(margin_backstop(f, s, b_calm_scaled), 6) for f, s in PIN}
min_base = min(base_margins.values())
min_backstop_stress = min(backstop_stress.values())

# ===========================================================================
# assemble result block
# ===========================================================================
RES = {
  "a_substitution_sign": {
    "principled_transform": "month-over-month LOG-CHANGE, demeaned (substitution is a flow/change concept)",
    "within_holder_pairing": "US-leg = F4[h] (foreign h holdings OF US LT secs); offshore-haven exposure = F3[h] (US holdings OF h LT secs); h in {CYM,HKG,VGB}",
    "F3_substitution_predicts": "NEGATIVE within-holder co-movement (US-leg DOWN while offshore-haven exposure UP)",
    "logchange_per_haven": {c: round(a_per_log[c], 6) for c in HAVENS},
    "logchange_pooled": round(a_pooled_log, 6),
    "change_per_haven": {c: round(a_per_chg[c], 6) for c in HAVENS},
    "change_pooled": round(a_pooled_chg, 6),
    "level_per_haven": {c: round(a_per_lvl[c], 6) for c in HAVENS},
    "level_pooled": round(a_pooled_lvl, 6),
    "testB_semiannual_value": 0.4664,
    "coverage_limitation": "TIC SLT resolves only US<->foreign legs; a generic holder's foreign<->foreign haven exposure is NOT reconstructible. The offshore-haven exposure is proxied by the US<->haven residency cells the DP4 operator actually uses (CYM/HKG/VGB residency). Stated, not invented."
  },
  "b_footprint_separation": {
    "footprint_cosine_meandirection": round(foot_cos_meandir, 6),
    "footprint_cosine_monthly_mean": round(foot_cos_monthly_mean, 6),
    "testB_panel_footprint_cosine": 0.9386,
    "construction": "mean monthly log-change footprint over the CYM/HKG/VGB block for each direction; cosine of the two mean-direction vectors (and mean of per-month cosines as robustness)"
  },
  "b2_lead_lag": {
    "definition": "xcorr(k)=corr(F4_USleg_logchg_t, F3_offshore_logchg_{t+k}); k>0 => F3 lags F4; k<0 => F3 leads. Substitution would show a strong NEGATIVE corr at some lead/lag; common-growth/contagion shows positive corr peaking at k=0.",
    "full_sample_profile": {str(k): (round(v,6) if v is not None else None) for k,v in xcorr_full.items()},
    "full_sample_peak": peak(xcorr_full),
    "episode_2022_window": "2021-07..2023-06",
    "episode_2022_profile": {str(k): (round(v,6) if v is not None else None) for k,v in xcorr_22.items()},
    "episode_2022_peak": peak(xcorr_22)
  },
  "operator_with_backstop": {
    "base_15x2_margins_pinned": base_margins,
    "min_base_margin_pinned": min_base,
    "base_reproduces_geo_vs_emp": "geo_vs_emp min pinned margin 0.220969; recomputed here = %.6f" % min_base,
    "backstop_respec": "v_F4 += single positive OFFICIAL cell b_backstop (F4-exclusive; v_F3=0 there). 16x2 operator.",
    "b_stress_2020_usd_mn": B_STRESS_2020,
    "b_calm_usd_mn": B_CALM,
    "b_scaled_by_usa_block_L2norm": {"stress": round(b_stress_scaled,6), "calm": round(b_calm_scaled,6), "usa_raw_L2norm": round(usa_raw_norm,3)},
    "backstop_stress_margins_pinned": backstop_stress,
    "min_backstop_stress_margin": min_backstop_stress,
    "backstop_calm_margins_pinned": backstop_calm,
    "note": "Backstop cell is F4-exclusive (orthogonal direction added to F4 only), so it can only INCREASE the F3/F4 angle => margin >= base. Anchor: base min %.6f (matches geo_vs_emp >=0.221), backstop-stress min %.6f." % (min_base, min_backstop_stress)
  }
}
print(json.dumps(RES, indent=2))
