#!/usr/bin/env python3
"""RDT Parts 2-4 — recompute: Russia-trajectory calibration, holder measurement, object.

Regenerates EVERY distance, velocity, ordering, composite, sensitivity and kinematic
deterministically from the committed inputs alone (no network):

  INPUT 1 (primary): build/reserve/RDT_coordinates.parquet
      — all coordinates + pseudo-holder input rows (_AGG_COFER/_LMW_PCTL/_PREF/_SAFE_ANCHOR)
  INPUT 2 (Part-2 secondary-trajectory scan ONLY): build/reserve/rd0_evidence/lmw_Data.xls
      sheet DATA (engine xlrd) — the full LMW discloser panel is not in the parquet
  CROSS-CHECK-ONLY input (no computation uses it beyond the equality check):
      build/reserve/rd2_evidence/wb_pinksheet_MYFETCH.xlsx — re-derives P_ref and
      requires it to MATCH the _PREF row (a mismatch is a broken build and halts).

Outputs (the only files written):
  build/reserve/RDT_calibration.json
  build/reserve/RDT_result.json
  build/reserve/RDT_breaking_point_object.md   (generated here so every number is computed)
  build/reserve/RDT_verify.json                (match flags; all_pass)

Design is pre-registered in build/reserve/RDT_prediction.md (read-only): metric, windows,
onsets, guards, composite, sensitivities are FIXED there. No date. No probability.
Every output is an OUTPUT — NOT ESTABLISHED until RDT_verify.json exists with all_pass.
"""

import hashlib
import json
import math
import os
import re

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PARQ = os.path.join(HERE, "RDT_coordinates.parquet")
LMW_XLS = os.path.join(HERE, "rd0_evidence", "lmw_Data.xls")
PINK = os.path.join(HERE, "rd2_evidence", "wb_pinksheet_MYFETCH.xlsx")

OUT_CAL = os.path.join(HERE, "RDT_calibration.json")
OUT_RES = os.path.join(HERE, "RDT_result.json")
OUT_OBJ = os.path.join(HERE, "RDT_breaking_point_object.md")
OUT_VER = os.path.join(HERE, "RDT_verify.json")

OZT_PER_TONNE = 1e6 / 31.1034768  # exact troy oz per metric tonne (31.1034768 g/ozt)

STAMP = ("OUTPUT — NOT ESTABLISHED until the verifier artifact "
         "build/reserve/RDT_verify.json exists with all_pass=true")

TAU_CAVEAT = ("if current velocity persists; velocities regime-shift (Russia's own did "
              "in 2014 and 2018); kinematic descriptor, not a forecast")

DV_CAVEAT = ("conditional on the Russia-calibrated frontier (N=1 completed anticipatory "
             "exit; see secondary-trajectory scan) and on each cell's observability flag; "
             "kinematic descriptor, not a forecast; no date, no probability")

HOLDERS = ["Russia", "China", "India", "Turkey", "SaudiArabia", "Poland"]
PRIMARY_ONSET, ALT_ONSET = 2014, 2018


def r6(x):
    if x is None:
        return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return float(round(float(x), 6))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ interval helpers
# An interval is a (lo, hi) tuple of floats, lo <= hi. Points are (v, v).

def ival(lo, hi):
    lo, hi = float(lo), float(hi)
    return (min(lo, hi), max(lo, hi))


def imid(a):
    return 0.5 * (a[0] + a[1])


def iadd(a, b):
    return (a[0] + b[0], a[1] + b[1])


def isub(a, b):
    return (a[0] - b[1], a[1] - b[0])


def iscale(a, s):
    return ival(a[0] * s, a[1] * s)


def idiv(a, b):
    """Interval division a/b. Returns None if b spans zero (UNBOUNDED)."""
    if b[0] <= 0.0 <= b[1]:
        return None
    cands = [a[0] / b[0], a[0] / b[1], a[1] / b[0], a[1] / b[1]]
    return (min(cands), max(cands))


def ifmt(a, nd=3):
    if a is None:
        return "UNBOUNDED"
    if abs(a[0] - a[1]) < 5e-7:
        return f"{a[0]:.{nd}f}"
    return f"[{a[0]:.{nd}f}, {a[1]:.{nd}f}]"


def ijson(a):
    if a is None:
        return {"lower": None, "upper": None, "midpoint": None,
                "flag": "UNBOUNDED-BY-INTERVAL-ARITHMETIC"}
    return {"lower": r6(a[0]), "upper": r6(a[1]), "midpoint": r6(imid(a))}


# ------------------------------------------------------------------ load inputs
DF = pd.read_parquet(PARQ)


def rows(holder, coord):
    sub = DF[(DF.holder == holder) & (DF.coordinate == coord)].sort_values("year")
    out = {}
    for _, r in sub.iterrows():
        if r.observability == "NOT-AVAILABLE" or pd.isna(r.value):
            continue
        out[int(r.year)] = {"iv": ival(r.value_lower, r.value_upper),
                            "obs": str(r.observability), "vintage": str(r.vintage),
                            "source": str(r.source)}
    return out


def point_series(holder, coord):
    return {y: imid(d["iv"]) for y, d in rows(holder, coord).items()}


# P_ref: from the _PREF row; cross-check re-derivation from the committed Pink Sheet xlsx.
P_REF_PARQ = point_series("_PREF", "gold_usd_per_oz_2021mean")[2021]


def rederive_pref():
    wb = pd.ExcelFile(PINK).parse("Monthly Prices", header=None)
    gcol = next(j for i in range(12) for j, c in enumerate(wb.iloc[i].tolist())
                if str(c) == "Gold")
    vals = []
    for i in range(len(wb)):
        lab = str(wb.iloc[i, 0])
        if re.fullmatch(r"2021M\d{2}", lab):
            vals.append(float(wb.iloc[i, gcol]))
    assert len(vals) == 12, f"expected 12 monthly 2021 gold prices, got {len(vals)}"
    return sum(vals) / 12.0


P_REF_XLSX = rederive_pref()
P_REF_MATCH = abs(P_REF_PARQ - P_REF_XLSX) < 1e-9
if not P_REF_MATCH:
    raise SystemExit(f"P_ref MISMATCH parquet={P_REF_PARQ} xlsx={P_REF_XLSX} — broken build; halt.")
P_REF = P_REF_PARQ


def gold_usd_bn(tonnes):
    return tonnes * OZT_PER_TONNE * P_REF / 1e9


def k2_share_series(holder):
    """Constant-price gold share (%) per year: tonnes*P_ref/(tonnes*P_ref+reserves_ex_gold)."""
    t = point_series(holder, "k2_gold_tonnes")
    x = point_series(holder, "k2_reserves_ex_gold_usd_bn")
    out = {}
    for y in sorted(set(t) & set(x)):
        gv = gold_usd_bn(t[y])
        out[y] = 100.0 * gv / (gv + x[y])
    return out


def k3_ratio_series(holder):
    """UST/total reserves (%) per year, as intervals (China band propagates)."""
    u = rows(holder, "k3_ust_busd")
    tot = point_series(holder, "k2_total_reserves_usd_bn")
    out = {}
    for y in sorted(set(u) & set(tot)):
        out[y] = iscale(u[y]["iv"], 100.0 / tot[y])
    return out


# China k1: the two routes and the pre-registered envelope (union).
def china_k1_routes():
    res = rows("China", "k1_usd_share_pct")
    safe = rows("China", "k1_usd_share_pct_safe_route")
    env = {}
    for y in sorted(set(res) | set(safe)):
        if y in res and y in safe:
            a, b = res[y]["iv"], safe[y]["iv"]
            env[y] = {"iv": (min(a[0], b[0]), max(a[1], b[1])), "routes": "both"}
        elif y in res:
            env[y] = {"iv": res[y]["iv"], "routes": "residual-only"}
        else:
            env[y] = {"iv": safe[y]["iv"], "routes": "safe-only"}
    raw_endpoints = {}
    for y, d in res.items():
        m = re.search(r"RAW endpoints \[(-?[\d.]+), (-?[\d.]+)\]", d["source"])
        if m:
            raw_endpoints[y] = [float(m.group(1)), float(m.group(2))]
    return res, safe, env, raw_endpoints


CH_RES, CH_SAFE, CH_ENV, CH_RAW = china_k1_routes()


# ------------------------------------------------------------------ coordinate accessors
def coord_series(holder, k):
    """Distance-coordinate series as {year: interval}, plus a vintage note."""
    if k == "k1":
        if holder == "China":
            # headline = envelope; handled separately where route matters
            return {y: d["iv"] for y, d in CH_ENV.items()}
        return {y: d["iv"] for y, d in rows(holder, "k1_usd_share_pct").items()}
    if k == "k2":
        return {y: (v, v) for y, v in k2_share_series(holder).items()}
    if k == "k3":
        return k3_ratio_series(holder)
    if k == "k4":
        return {y: d["iv"] for y, d in rows(holder, "k4_cny_share_pct").items()}
    raise KeyError(k)


K_LABEL = {
    "k1": "USD share of disclosed FX reserves (pp)",
    "k2": "constant-price gold share (%%) = tonnes*P_ref/(tonnes*P_ref+reserves_ex_gold)",
    "k3": "UST / total reserves (%%), TIC December snapshot over WB year-end total",
    "k4": "CNY share of disclosed reserves (pp)",
}

# ------------------------------------------------------------------ PART 2: frontier
RUS = {k: coord_series("Russia", k) for k in ["k1", "k2", "k3", "k4"]}
RUS_PT = {k: {y: imid(v) for y, v in s.items()} for k, s in RUS.items()}

FRONTIER = {
    "k1": RUS_PT["k1"][2021],
    "k2": 0.5 * (RUS_PT["k2"][2020] + RUS_PT["k2"][2021]),
    "k3": RUS_PT["k3"][2021],
    "k4": RUS_PT["k4"][2021],
}
FRONTIER_DEF = {
    "k1": "Russia LMW USD share, last pre-freeze observation (2021)",
    "k2": "mean of Russia's 2020-2021 constant-price gold-share plateau",
    "k3": "Russia UST/total reserves at the Dec-2021 snapshot",
    "k4": "Russia LMW CNY share, last pre-freeze observation (2021)",
}
FRONTIER_REGION = {k: [r6(min(RUS_PT[k][y] for y in (2019, 2020, 2021))),
                       r6(max(RUS_PT[k][y] for y in (2019, 2020, 2021)))]
                   for k in ["k1", "k2", "k3", "k4"]}


# ------------------------------------------------------------------ PART 2: onset rule
def onset_year(series_pt, origin_year, terminal_value, last_path_year):
    """First t > origin_year with |x_t - x_O| >= 0.10*|x_F - x_O|, sign-matching,
    sustained for all observed t' in [t, last_path_year]. Returns (year|None, detail)."""
    x0 = series_pt[origin_year]
    gap = terminal_value - x0
    thresh = 0.10 * abs(gap)
    sgn = 1.0 if gap > 0 else -1.0
    years = [y for y in sorted(series_pt) if origin_year < y <= last_path_year]

    def ok(y):
        d = series_pt[y] - x0
        return abs(d) >= thresh and (d * sgn) > 0

    detail = {y: {"x": r6(series_pt[y]), "delta_vs_origin": r6(series_pt[y] - x0),
                  "meets_10pct_threshold_and_sign": bool(ok(y))} for y in years}
    for i, y in enumerate(years):
        if all(ok(y2) for y2 in years[i:]):
            return y, {"threshold_abs": r6(thresh), "sign_required": ("+" if sgn > 0 else "-"),
                       "per_year": detail}
    return None, {"threshold_abs": r6(thresh), "sign_required": ("+" if sgn > 0 else "-"),
                  "per_year": detail}


ONSETS = {}
ONSET_DETAIL = {}
for k in ["k1", "k2", "k3", "k4"]:
    y, det = onset_year(RUS_PT[k], 2013, FRONTIER[k], 2021)
    ONSETS[k] = y
    ONSET_DETAIL[k] = det
    # full-series sustainment check (beyond the pre-freeze path), recorded
    y_full, _ = onset_year(RUS_PT[k], 2013, FRONTIER[k], max(RUS_PT[k]))
    ONSET_DETAIL[k]["onset_sustained_over_full_available_series"] = y_full

# alternative-origin (end-2017) variant of the ordering rule, labelled as such
ONSETS_ALT = {}
for k in ["k1", "k2", "k3", "k4"]:
    y, _ = onset_year(RUS_PT[k], 2017, FRONTIER[k], 2021)
    ONSETS_ALT[k] = y

realized_order = sorted(["k1", "k2", "k3", "k4"], key=lambda k: (ONSETS[k] is None, ONSETS[k] or 9999, k))
EXPECTED = {"k2_onset": 2014, "k3_onset": 2018, "k1_completes_by": 2021}
ordering_components = {
    "gold_k2_moves_from_2014": bool(ONSETS["k2"] == 2014),
    "ust_k3_onset_2018": bool(ONSETS["k3"] == 2018),
    "k3_onset_found": ONSETS["k3"],
    "currency_k1_completes_by_2021": bool(abs(RUS_PT["k1"][2021] - FRONTIER["k1"]) < 1e-12),
    "k1_completion_note": ("by construction: the k1 frontier IS Russia's 2021 value, so "
                           "'completes by 2021' is tautologically true; the informative part "
                           "is the k1 onset year found = " + str(ONSETS["k1"])),
    "sequence_gold_before_ust_before_currency": bool(
        ONSETS["k2"] < ONSETS["k3"] < ONSETS["k1"]),
}
ORDERING_VERDICT = ("HELD" if (ordering_components["gold_k2_moves_from_2014"]
                               and ordering_components["ust_k3_onset_2018"]
                               and ordering_components["currency_k1_completes_by_2021"])
                    else "DIFFERENT")


# ------------------------------------------------------------------ distances d_k
def d_interval(x_t, x_origin, xF):
    """Path-fraction d = (x_t - x_F)/(x_O - x_F), interval arithmetic."""
    return idiv(isub(x_t, (xF, xF)), isub(x_origin, (xF, xF)))


def latest_year(series, cap=None):
    ys = [y for y in series if cap is None or y <= cap]
    return max(ys) if ys else None


def nearest_at_or_before(series, target):
    ys = [y for y in series if y <= target]
    return max(ys) if ys else None


def guard_check(x_origin, k, onset):
    """Degeneracy guard: |x_O(h)-x_F| < 0.20*|x_O(Russia)-x_F| -> NOT-MEANINGFUL.
    For interval origins: fires 'UNVERIFIABLE' if the interval admits values below the
    threshold (never silently cleared)."""
    xF = FRONTIER[k]
    rus_origin = RUS_PT[k].get(onset)
    thresh = 0.20 * abs(rus_origin - xF)
    lo, hi = x_origin
    dist_lo = 0.0 if lo <= xF <= hi else min(abs(lo - xF), abs(hi - xF))
    dist_hi = max(abs(lo - xF), abs(hi - xF))
    if dist_hi < thresh:
        return "FIRES", thresh
    if dist_lo < thresh:
        if abs(lo - hi) < 5e-7:
            return "FIRES", thresh
        return "UNVERIFIABLE-INTERVAL-ORIGIN", thresh
    return "CLEARS", thresh


# ------------------------------------------------------------------ Russia calibration block
def russia_calibration():
    per_k = {}
    for k in ["k1", "k2", "k3", "k4"]:
        s = RUS_PT[k]
        xF = FRONTIER[k]
        d14 = {y: (s[y] - xF) / (s[2014] - xF) for y in sorted(s)}
        d18 = {y: (s[y] - xF) / (s[2018] - xF) for y in sorted(s)} if abs(s.get(2018, xF) - xF) > 1e-12 else None
        last_pre = 2021 if k != "k3" else 2021
        lat = latest_year(s)
        raw_series = {str(y): r6(s[y]) for y in sorted(s)}
        # velocities in d-space (origin-2014 scaling): full path 2014->2021, phases
        def v(dser, y1, y2):
            if dser is None or y1 not in dser or y2 not in dser:
                return None
            return -(dser[y2] - dser[y1]) / (y2 - y1)
        per_k[k] = {
            "definition": K_LABEL[k],
            "raw_series": raw_series,
            "origin_end2013": r6(s[2013]),
            "origin_end2017": r6(s[2017]),
            "metric_origin_x2014": r6(s[2014]),
            "metric_origin_x2018": r6(s[2018]),
            "frontier_terminal": r6(xF),
            "frontier_definition": FRONTIER_DEF[k],
            "frontier_region_2019_2021": FRONTIER_REGION[k],
            "d_series_origin2014": {str(y): r6(d14[y]) for y in sorted(d14)},
            "onset_primary_rule_origin2013": ONSETS[k],
            "onset_alternative_variant_origin2017": ONSETS_ALT[k],
            "onset_detail": ONSET_DETAIL[k],
            "velocity_path_fraction_per_yr": {
                "full_path_2014_2021": r6(v(d14, 2014, 2021)),
                "phase_2014_2018": r6(v(d14, 2014, 2018)),
                "phase_2018_2021": r6(v(d14, 2018, 2021)),
                "alt_origin2018_2018_2021": r6(v(d18, 2018, 2021)) if d18 else None,
                "note": "positive = toward the frontier; d-space, origin-2014 scaling",
            },
            "velocity_raw_units_per_yr": {
                "full_path_2014_2021": r6((s[2021] - s[2014]) / 7.0),
                "phase_2014_2018": r6((s[2018] - s[2014]) / 4.0),
                "phase_2018_2021": r6((s[2021] - s[2018]) / 3.0),
            },
            "post_freeze_observations_note": (
                "observations after 2021 are post-freeze and OUTSIDE the anticipatory path "
                f"(latest available: {lat})"),
            "conditionality": DV_CAVEAT,
        }
        _ = last_pre
    # raw blocks beside derived values
    per_k["k2"]["raw_inputs"] = {
        "gold_tonnes": {str(y): r6(v) for y, v in point_series("Russia", "k2_gold_tonnes").items()},
        "reserves_ex_gold_usd_bn": {str(y): r6(v) for y, v in
                                    point_series("Russia", "k2_reserves_ex_gold_usd_bn").items()},
        "P_ref_usd_per_ozt": r6(P_REF), "ozt_per_tonne": r6(OZT_PER_TONNE),
        "denominator_note": "Russia WB denominators end 2024; 2025 share not computable (NOT-AVAILABLE, recorded)",
    }
    per_k["k3"]["raw_inputs"] = {
        "ust_busd_dec": {str(y): r6(v) for y, v in point_series("Russia", "k3_ust_busd").items()},
        "total_reserves_usd_bn": {str(y): r6(v) for y, v in
                                  point_series("Russia", "k2_total_reserves_usd_bn").items()},
    }
    return per_k


# ------------------------------------------------------------------ PART 2: secondary scan
def secondary_scan():
    lmw = pd.read_excel(LMW_XLS, sheet_name="DATA", engine="xlrd")
    qualifiers = []
    all_countries = sorted(lmw.country.unique())
    for c in all_countries:
        sub = lmw[(lmw.country == c)].dropna(subset=["USD"]).sort_values("year")
        ys = sub.year.astype(int).tolist()
        xs = sub.USD.astype(float).tolist()
        if len(ys) < 2:
            continue
        final_val = xs[-1]
        best = None
        for i in range(len(ys)):
            for j in range(i + 1, len(ys)):
                if ys[j] - ys[i] > 10:
                    continue
                decline = xs[i] - xs[j]
                if decline >= 15.0 and final_val <= xs[i] - 10.0:
                    if best is None or decline > best["decline_pp"]:
                        best = {"window": [ys[i], ys[j]], "start_usd_pp": r6(xs[i]),
                                "end_usd_pp": r6(xs[j]), "decline_pp": r6(decline),
                                "final_panel_year": ys[-1], "final_usd_pp": r6(final_val)}
        if best:
            best["country"] = c
            qualifiers.append(best)
    qualifiers.sort(key=lambda q: -q["decline_pp"])

    # ordering comparison for qualifiers among the six parquet holders
    name_map = {"Russia": "Russia", "China": "China", "India": "India", "Turkey": "Turkey",
                "Saudi Arabia": "SaudiArabia", "Poland": "Poland"}
    for q in qualifiers:
        h = name_map.get(q["country"])
        if h is None:
            q["ordering_comparison"] = ("k2/k3 for this discloser are not in the coordinates "
                                        "file (only the six holders were assembled); ordering "
                                        "not computed — NOT fetched, per the input basis")
            continue
        t1, t2 = q["window"]
        onsets_q = {}
        for k in ["k1", "k2", "k3", "k4"]:
            try:
                s = {y: imid(v) for y, v in coord_series(h, k).items()}
            except Exception:
                s = {}
            if t1 not in s or t2 not in s:
                onsets_q[k] = "series does not cover the window"
                continue
            if abs(s[t2] - s[t1]) < 1e-9:
                onsets_q[k] = "no terminal movement over the window (|x_t2-x_t1|=0)"
                continue
            oy, _ = onset_year(s, t1, s[t2], t2)
            onsets_q[k] = oy
        q["adapted_onset_rule"] = ("origin=window start year, terminal=window end value, same "
                                   "10%-threshold + sign + sustained-through-window rule")
        q["onsets_over_window"] = onsets_q
        q["russia_realized_ordering"] = {k: ONSETS[k] for k in ["k1", "k2", "k3", "k4"]}
    return {
        "rule": ("every LMW discloser with a USD-share decline >= 15pp between two observations "
                 "<= 10 years apart whose final panel value does not recover above (start - 10pp); "
                 "reported window = the maximum-decline qualifying pair"),
        "n_disclosers_scanned": len(all_countries),
        "n_qualifiers": len(qualifiers),
        "qualifiers": qualifiers,
        "n1_statement": ("N=1 remains the central limitation for the CALIBRATION even though the "
                         "scan finds other >=15pp USD-share decliners: Russia is the only qualifier "
                         "with a completed, sanctions-anticipatory exit across all four coordinates "
                         "ending at the frontier; other qualifiers inform the k1 margin only, and "
                         "where their k2/k3 exist (the six holders) their move-ordering is compared "
                         "above" if len(qualifiers) > 1 else
                         "N=1: no other discloser qualifies; this is the model's central limitation"),
    }


# ------------------------------------------------------------------ PART 3 helpers
def k1_headline_china():
    """Headline China k1 = envelope at the latest year where BOTH routes ground (2025 -> [0,100]).
    The 2026 envelope is safe-route-only (residual lacks a 2026 WB denominator); using it as the
    headline would silently swap the SAFE route in — forbidden. Reported separately."""
    both_years = [y for y, d in CH_ENV.items() if d["routes"] == "both"]
    y_head = max(both_years)
    y_single = max(CH_ENV)
    return y_head, CH_ENV[y_head]["iv"], y_single, CH_ENV[y_single]["iv"], CH_ENV[y_single]["routes"]


def holder_coordinate_block(h, k):
    """Full per-coordinate measurement for one holder."""
    xF = FRONTIER[k]
    if h == "China" and k == "k1":
        return china_k1_block()
    if h == "China" and k == "k4":
        return {"status": "N/A-issuer",
                "note": "China is the alternative's issuer — applicability, not a data hole; "
                        "excluded from China's composite (not an available coordinate)"}
    try:
        s = coord_series(h, k)
    except Exception:
        s = {}
    if not s:
        return {"status": "NOT-AVAILABLE",
                "note": f"{k} not available for {h} (see coordinates provenance); "
                        "excluded from the composite"}
    lat = latest_year(s)
    x_t = s[lat]
    out = {"observability": ("INFERRED-BOUNDED (TIC custody band)" if (h == "China" and k == "k3")
                             else "OBSERVED"),
           "definition": K_LABEL[k],
           "vintage_latest": lat,
           "position_raw": ijson(x_t),
           "frontier": r6(xF),
           "conditionality": DV_CAVEAT}
    if k == "k2":
        t = point_series(h, "k2_gold_tonnes")
        xg = point_series(h, "k2_reserves_ex_gold_usd_bn")
        out["raw_beside"] = {"gold_tonnes_latest": r6(t[lat]),
                             "reserves_ex_gold_usd_bn_latest": r6(xg[lat]),
                             "gold_constant_price_usd_bn_latest": r6(gold_usd_bn(t[lat]))}
    if k == "k3":
        u = rows(h, "k3_ust_busd")
        latest_u = max(u)
        out["raw_beside"] = {"ust_busd_latest_published": ijson(u[latest_u]["iv"]),
                             "ust_vintage": u[latest_u]["vintage"],
                             "ratio_denominator_year": lat,
                             "total_reserves_usd_bn": r6(point_series(h, "k2_total_reserves_usd_bn")[lat]),
                             "note": "ratio uses the latest year with BOTH numerator and WB denominator"}
    if k == "k1" or k == "k4":
        out["raw_beside"] = {"share_pp_latest": ijson(x_t)}

    for onset, tag in [(PRIMARY_ONSET, "primary_onset_2014"), (ALT_ONSET, "alt_onset_2018")]:
        if onset not in s:
            out[tag] = {"status": f"origin year {onset} not observed for this coordinate"}
            continue
        x_o = s[onset]
        gstat, gthr = guard_check(x_o, k, onset)
        blk = {"origin_x": ijson(x_o),
               "degeneracy_guard": {"status": gstat, "threshold_pp": r6(gthr),
                                    "rule": "|x_O(h)-x_F| < 0.20*|x_O(Russia)-x_F| -> path-fraction NOT-MEANINGFUL"}}
        if gstat == "FIRES":
            blk["d"] = {"status": "NOT-MEANINGFUL (guard fires)",
                        "raw_space_distance": ijson(isub(x_t, (xF, xF))),
                        "raw_space_units": "coordinate units (pp / % points)"}
        else:
            dser = {y: d_interval(s[y], x_o, xF) for y in sorted(s)}
            d_lat = dser[lat]
            blk["d"] = ijson(d_lat)
            blk["d"]["raw_space_distance_to_frontier"] = ijson(isub(x_t, (xF, xF)))
            # velocities: recent-3y and full-window, both, in d-space and raw units
            y3 = nearest_at_or_before(s, lat - 3)
            vel = {}
            if y3 is not None and y3 != lat and dser.get(y3) is not None and d_lat is not None:
                vel["recent_3y"] = {
                    "window": [y3, lat],
                    "v_path_fraction_per_yr": ijson(iscale(isub(dser[y3], d_lat), 1.0 / (lat - y3))),
                    "v_raw_units_per_yr": ijson(iscale(isub(x_t, s[y3]), 1.0 / (lat - y3))),
                }
            if onset in dser and onset != lat and dser[onset] is not None and d_lat is not None:
                vel["full_window"] = {
                    "window": [onset, lat],
                    "v_path_fraction_per_yr": ijson(iscale(isub(dser[onset], d_lat), 1.0 / (lat - onset))),
                    "v_raw_units_per_yr": ijson(iscale(isub(x_t, x_o), 1.0 / (lat - onset))),
                }
            blk["velocities"] = vel if vel else {"status": "insufficient observations"}
            blk["tau_if_velocity_persists"] = {
                w: tau_block(d_lat, ((vel[w]["v_path_fraction_per_yr"]["lower"],
                                      vel[w]["v_path_fraction_per_yr"]["upper"])
                                     if vel[w]["v_path_fraction_per_yr"]["lower"] is not None else None))
                for w in vel}
        out[tag] = blk
    return out


def tau_block(d, v):
    """tau = d/v IF v>0, intervals -> tau intervals; carries the literal caveat."""
    base = {"caveat": TAU_CAVEAT}
    if d is None or v is None:
        base["status"] = "not computable (unbounded interval input)"
        return base
    if d[1] <= 0:
        base["status"] = "at or beyond the frontier (d <= 0); no tau"
        return base
    if v[1] <= 0:
        base["status"] = "not approaching at current velocity (v <= 0); no tau"
        return base
    if v[0] <= 0:
        base["status"] = ("velocity sign indeterminate within the interval (v spans 0); "
                          "tau unbounded above; no point tau")
        base["tau_years_lower_bound_at_v_upper"] = r6(max(d[0], 0.0) / v[1])
        return base
    lo = max(d[0], 0.0) / v[1]
    hi = d[1] / v[0]
    base["tau_years"] = {"lower": r6(lo), "upper": r6(hi),
                         "midpoint_label_only": r6(imid(d) / imid(v))}
    if d[0] < 0:
        base["note"] = "d interval straddles the frontier; lower tau clipped at 0"
    return base


def china_k1_block():
    """China k1: pre-registered ENVELOPE headline (mechanical) + SAFE-route sensitivity."""
    xF = FRONTIER["k1"]
    y_head, env_head, y_single, env_single, single_routes = k1_headline_china()
    env_origin = CH_ENV[2014]["iv"]
    out = {
        "observability": "INFERRED-BOUNDED (never a point)",
        "definition": K_LABEL["k1"],
        "vintage_latest_both_routes": y_head,
        "headline_envelope_union_of_routes": {
            "value_pp": ijson(env_head),
            "note": ("pre-registered envelope = union(residual route, SAFE-anchor route); the "
                     "residual route is clipped to [0,100] in every year, so the union is "
                     "effectively [0,100] — reported honestly as the headline interval"),
            "residual_raw_endpoints_echo_pp": {
                "origin_2014": CH_RAW.get(2014), "latest_2025": CH_RAW.get(2025),
                "note": "raw (unclipped) residual endpoints, echoed from the row sources/manifest"},
        },
        "envelope_at_2026_single_route": {
            "value_pp": ijson(env_single), "routes": single_routes, "year": y_single,
            "note": ("at 2026 only the SAFE route grounds (WB China reserves end 2025); the "
                     "single-route envelope is NOT used as the headline — that would silently "
                     "swap the SAFE route in")},
        "frontier": r6(xF),
        "conditionality": DV_CAVEAT,
    }
    for onset, tag in [(PRIMARY_ONSET, "primary_onset_2014"), (ALT_ONSET, "alt_onset_2018")]:
        x_o = CH_ENV[onset]["iv"]
        gstat, gthr = guard_check(x_o, "k1", onset)
        d = d_interval(env_head, x_o, xF)
        out[tag] = {
            "origin_x_envelope": ijson(x_o),
            "degeneracy_guard": {"status": gstat, "threshold_pp": r6(gthr),
                                 "rule": "|x_O(h)-x_F| < 0.20*|x_O(Russia)-x_F|"},
            "d_headline": (ijson(d) if d is not None else
                           {"lower": None, "upper": None, "midpoint": None,
                            "flag": "UNBOUNDED-BY-INTERVAL-ARITHMETIC",
                            "reason": ("the origin-envelope minus frontier interval spans zero "
                                       "(a direct consequence of the residual route's near-"
                                       "uninformativeness), so the path-fraction is unbounded; "
                                       "reported as such, never collapsed")}),
            "raw_space_distance_to_frontier_pp": ijson(isub(env_head, (xF, xF))),
            "raw_space_note": ("with the [0,100] envelope the raw-space distance is itself nearly "
                               "uninformative; stated, not smoothed"),
            "velocities": {"status": ("not computable on the headline envelope (unbounded/near-"
                                      "uninformative d); see SAFE-route sensitivity")},
            "tau_if_velocity_persists": tau_block(d, None),
        }
    # SAFE-route-only sensitivity (labelled; NOT the headline)
    safe = {y: d["iv"] for y, d in CH_SAFE.items()}
    lat_s = max(safe)
    sens = {"label": "SENSITIVITY — SAFE-anchor route only (NOT the headline)",
            "vintage_latest": lat_s, "position_pp": ijson(safe[lat_s])}
    for onset, tag in [(PRIMARY_ONSET, "primary_onset_2014"), (ALT_ONSET, "alt_onset_2018")]:
        x_o = safe[onset]
        gstat, gthr = guard_check(x_o, "k1", onset)
        dser = {y: d_interval(safe[y], x_o, xF) for y in sorted(safe)}
        d_lat = dser[lat_s]
        y3 = nearest_at_or_before(safe, lat_s - 3)
        vel = {}
        if y3 and dser.get(y3) is not None and d_lat is not None:
            vel["recent_3y"] = {"window": [y3, lat_s],
                                "v_path_fraction_per_yr": ijson(iscale(isub(dser[y3], d_lat), 1.0 / (lat_s - y3)))}
        if onset in dser and dser[onset] is not None and d_lat is not None:
            vel["full_window"] = {"window": [onset, lat_s],
                                  "v_path_fraction_per_yr": ijson(iscale(isub(dser[onset], d_lat), 1.0 / (lat_s - onset)))}
        sens[tag] = {"origin_x": ijson(x_o),
                     "degeneracy_guard": {"status": gstat, "threshold_pp": r6(gthr)},
                     "d": ijson(d_lat) if d_lat is not None else {"flag": "UNBOUNDED"},
                     "corridor_freeze_note": ("the SAFE corridor freezes at [33.879, 82.121] from "
                                              "2024 (LMW drift input ends 2023), so recent-3y "
                                              "velocity is 0 by construction there"),
                     "velocities": vel,
                     "tau_if_velocity_persists": {w: tau_block(
                         d_lat, ((vel[w]["v_path_fraction_per_yr"]["lower"],
                                  vel[w]["v_path_fraction_per_yr"]["upper"])
                                 if vel[w]["v_path_fraction_per_yr"]["lower"] is not None else None))
                         for w in vel}}
    out["safe_route_sensitivity"] = sens
    return out


# ------------------------------------------------------------------ China k3 extras
def china_k3_extras():
    """Coherent custody-pairing d/v, band-midpoint v, and the ACTIVE-basis construction."""
    xF = FRONTIER["k3"]
    u = rows("China", "k3_ust_busd")
    tot = point_series("China", "k2_total_reserves_usd_bn")
    years = sorted(set(u) & set(tot))
    lat = max(years)
    x_lo = {y: 100.0 * u[y]["iv"][0] / tot[y] for y in years}   # China-alone path
    x_hi = {y: 100.0 * u[y]["iv"][1] / tot[y] for y in years}   # China+BEL+LUX path
    out = {}
    for onset, tag in [(PRIMARY_ONSET, "primary_onset_2014"), (ALT_ONSET, "alt_onset_2018")]:
        d_lo = {y: (x_lo[y] - xF) / (x_lo[onset] - xF) for y in years}
        d_hi = {y: (x_hi[y] - xF) / (x_hi[onset] - xF) for y in years}
        y3 = nearest_at_or_before({y: 0 for y in years}, lat - 3)
        blk = {
            "label": ("construction sensitivity — coherent custody pairing: the custody state "
                      "(China-alone vs China+Belgium+Luxembourg) is held fixed across years "
                      "instead of treated as independent intervals; both paths reported"),
            "d_china_alone_path": r6(d_lo[lat]), "d_china_plus_bel_lux_path": r6(d_hi[lat]),
            "v_recent_3y_path_fraction_per_yr": {
                "window": [y3, lat],
                "china_alone": r6(-(d_lo[lat] - d_lo[y3]) / (lat - y3)),
                "china_plus_bel_lux": r6(-(d_hi[lat] - d_hi[y3]) / (lat - y3))},
            "v_full_window_path_fraction_per_yr": {
                "window": [onset, lat],
                "china_alone": r6(-(d_lo[lat] - d_lo[onset]) / (lat - onset)),
                "china_plus_bel_lux": r6(-(d_hi[lat] - d_hi[onset]) / (lat - onset))},
            "band_midpoint_v_recent_3y": r6(-((imid((d_lo[lat], d_hi[lat])) if d_lo[lat] <= d_hi[lat] else imid((d_hi[lat], d_lo[lat])))
                                              - (imid((d_lo[y3], d_hi[y3])) if d_lo[y3] <= d_hi[y3] else imid((d_hi[y3], d_lo[y3])))) / (lat - y3)),
            "tau_recent_3y_years": {
                "china_alone": (r6(d_lo[lat] / (-(d_lo[lat] - d_lo[y3]) / (lat - y3)))
                                if -(d_lo[lat] - d_lo[y3]) > 0 and d_lo[lat] > 0 else None),
                "china_plus_bel_lux": (r6(d_hi[lat] / (-(d_hi[lat] - d_hi[y3]) / (lat - y3)))
                                       if -(d_hi[lat] - d_hi[y3]) > 0 and d_hi[lat] > 0 else None),
                "caveat": TAU_CAVEAT},
        }
        out[tag] = blk

    # ACTIVE basis: cumulative net-tx from the origin year, same WB denominators.
    tx = rows("China", "k3_net_tx_busd")
    active = {}
    for onset, tag in [(PRIMARY_ONSET, "primary_onset_2014"), (ALT_ONSET, "alt_onset_2018")]:
        H0 = u[onset]["iv"]
        h_act = {onset: H0}
        cum = (0.0, 0.0)
        for y in range(onset + 1, lat + 1):
            if y in tx:
                cum = iadd(cum, tx[y]["iv"])
            h_act[y] = iadd(H0, cum)
        x_act = {y: iscale(h_act[y], 100.0 / tot[y]) for y in h_act if y in tot}
        x_o = x_act[onset]
        d_act = {y: d_interval(x_act[y], x_o, xF) for y in x_act}
        d_lat = d_act[lat]
        y3 = lat - 3
        # correlated velocity: Delta x = H_act(t1)*(1/T(t2)-1/T(t1)) + S/T(t2), S = sum tx(t1+1..t2)
        def v_correlated(y1, y2):
            S = (0.0, 0.0)
            for y in range(y1 + 1, y2 + 1):
                if y in tx:
                    S = iadd(S, tx[y]["iv"])
            dx = iadd(iscale(h_act[y1], 100.0 * (1.0 / tot[y2] - 1.0 / tot[y1])),
                      iscale(S, 100.0 / tot[y2]))
            dd = idiv(dx, isub(x_o, (xF, xF)))  # Delta d over the window
            return iscale(dd, -1.0 / (y2 - y1)) if dd is not None else None
        v3 = v_correlated(y3, lat)
        vf = v_correlated(onset, lat)

        # raw active flow: H_act(t2)-H_act(t1) = interval sum of tx(t1+1..t2) EXACTLY
        # (the shared H(origin)+prior-tx terms cancel algebraically; no naive band subtraction)
        def raw_flow(y1, y2):
            S = (0.0, 0.0)
            for y in range(y1 + 1, y2 + 1):
                if y in tx:
                    S = iadd(S, tx[y]["iv"])
            return iscale(S, 1.0 / (y2 - y1))
        active[tag] = {
            "construction": ("ACTIVE basis (PRIMARY per the pre-registration for China k3 "
                             "velocity): H_active(t) = H(origin, TIC band) + cumulative net "
                             "long-term Treasury transactions (band) from the origin year; "
                             "share coordinate x_active = H_active / WB total reserves (same "
                             "denominators as the headline ratio); bills are excluded "
                             "(publisher boundary) and pre-2023-02 transactions are on the "
                             "Form-S basis (2023-02 basis break marked)"),
            "H_active_latest_busd": ijson(h_act[lat]),
            "x_active_latest_pct": ijson(x_act[lat]),
            "d_active_latest": ijson(d_lat) if d_lat is not None else {"flag": "UNBOUNDED"},
            "v_active_recent_3y_path_fraction_per_yr": (ijson(v3) if v3 is not None else {"flag": "UNBOUNDED"}),
            "v_active_full_window_path_fraction_per_yr": (ijson(vf) if vf is not None else {"flag": "UNBOUNDED"}),
            "velocity_windows": {"recent_3y": [y3, lat], "full_window": [onset, lat]},
            "v_active_raw_busd_per_yr": {
                "recent_3y": ijson(raw_flow(y3, lat)),
                "full_window": ijson(raw_flow(onset, lat)),
                "note": ("= interval mean of net transactions over the window (the cumulative "
                         "band's shared origin terms cancel exactly; no naive band subtraction)")},
            "raw_holdings_market_value_v_busd_per_yr_alongside": {
                "recent_3y": {"china_alone": r6((u[lat]["iv"][0] - u[y3]["iv"][0]) / (lat - y3)),
                              "china_plus_bel_lux": r6((u[lat]["iv"][1] - u[y3]["iv"][1]) / (lat - y3))},
                "full_window": {"china_alone": r6((u[lat]["iv"][0] - u[onset]["iv"][0]) / (lat - onset)),
                                "china_plus_bel_lux": r6((u[lat]["iv"][1] - u[onset]["iv"][1]) / (lat - onset))},
                "note": "coherent custody pairing (custody state held fixed across years), labelled"},
            "tau_active_if_velocity_persists": {
                "recent_3y": tau_block(d_lat, v3), "full_window": tau_block(d_lat, vf)},
            "where_the_caveats_bind": (
                "the 2023-02 Form S -> expanded Form SLT basis break sits INSIDE every "
                "cumulative-transactions sum that crosses 2023; the valuation term in the "
                "split is a RESIDUAL (holdings change minus transactions) and therefore also "
                "absorbs coverage/custody reclassification, not only price"),
        }
    return out, active


def valuation_split():
    """Per holder-year: Delta holdings = net_tx (active) + valuation_residual."""
    out = {}
    for h in HOLDERS:
        u = rows(h, "k3_ust_busd")
        tx = rows(h, "k3_net_tx_busd")
        tab = {}
        for y in sorted(tx):
            if y not in u or (y - 1) not in u:
                continue
            dH = isub(u[y]["iv"], u[y - 1]["iv"])
            val = isub(dH, tx[y]["iv"])
            row = {"delta_holdings_busd": ijson(dH), "net_tx_busd": ijson(tx[y]["iv"]),
                   "valuation_residual_busd": ijson(val)}
            if h == "China":
                # coherent custody pairing: custody state held fixed within the year; the
                # China-alone vs China+BEL+LUX tx endpoints are parsed from the row source
                # (which endpoint is China-alone flips year to year), holdings lower=alone.
                ma = re.search(r"China\(mainland\) alone = (-?[\d.]+) busd", tx[y]["source"])
                mc = re.search(r"China\+Belgium\+Luxembourg = (-?[\d.]+) busd", tx[y]["source"])
                if ma and mc:
                    txa, txc = float(ma.group(1)), float(mc.group(1))
                    dha = u[y]["iv"][0] - u[y - 1]["iv"][0]
                    dhc = u[y]["iv"][1] - u[y - 1]["iv"][1]
                    row["coherent_custody_pairing"] = {
                        "china_alone": {"delta_holdings_busd": r6(dha), "net_tx_busd": r6(txa),
                                        "valuation_residual_busd": r6(dha - txa)},
                        "china_plus_bel_lux": {"delta_holdings_busd": r6(dhc), "net_tx_busd": r6(txc),
                                               "valuation_residual_busd": r6(dhc - txc)},
                        "label": ("custody state held fixed within the year (labelled "
                                  "construction; the independent-interval version above is "
                                  "the conservative mechanical bound)")}
            if y == 2023:
                row["basis_break"] = ("2023-02 Form S -> expanded Form SLT transactions basis "
                                      "break binds in this row (publisher-documented)")
            if str(tx[y]["vintage"]).startswith("2026"):
                row["partial_year"] = "2026 covers Jan-Apr only (both terms partial)"
            tab[str(y)] = row
        out[h] = {"table": tab,
                  "note": ("valuation_residual = Delta holdings (market value) - net transactions "
                           "(long-term bonds & notes only); it is a RESIDUAL: it absorbs price/"
                           "valuation AND coverage, custody-reclassification and bills, so it is "
                           "an upper bound on pure valuation effects; China rows are custody-band "
                           "intervals (independent-interval arithmetic, conservative)")}
    return out


# ------------------------------------------------------------------ composites
COMPOSITE_COORDS = {"Russia": ["k1", "k2", "k3", "k4"], "China": ["k1", "k2", "k3"],
                    "India": ["k2", "k3"], "Turkey": ["k1", "k2", "k3", "k4"],
                    "SaudiArabia": ["k2", "k3"], "Poland": ["k1", "k2", "k3", "k4"]}


def composite(h, per_coord, tag):
    ks = COMPOSITE_COORDS[h]
    ds = {}
    for k in ks:
        blk = per_coord[k].get(tag, {})
        d = blk.get("d_headline") if (h == "China" and k == "k1") else blk.get("d")
        if d is None or "status" in (d if isinstance(d, dict) else {}):
            ds[k] = None
        elif isinstance(d, dict) and d.get("lower") is None:
            ds[k] = None  # unbounded
        else:
            ds[k] = (d["lower"], d["upper"])
    n = len(ks)
    unbounded = [k for k in ks if ds[k] is None]
    res = {"members": ks,
           "label": ("pre-registered construction: C(h) = unweighted mean of d_k over "
                     "applicable AND available coordinates; interval arithmetic; "
                     "per-coordinate distances come FIRST and no composite is 'the' number"),
           "asynchronous_vintages_note": "each coordinate measured at its own latest vintage"}
    if unbounded:
        res["C"] = {"lower": None, "upper": None, "midpoint": None,
                    "flag": "DEGENERATE — a member d is UNBOUNDED (" + ",".join(unbounded) + ")",
                    "reason": ("the headline China k1 envelope makes d_k1 unbounded by interval "
                               "arithmetic; the composite interval is therefore unbounded and its "
                               "midpoint degenerate — reported as such, never collapsed")}
    else:
        lo = sum(ds[k][0] for k in ks) / n
        hi = sum(ds[k][1] for k in ks) / n
        res["C"] = ijson((lo, hi))
    mids = {k: (imid(ds[k]) if ds[k] is not None else None) for k in ks}
    defined = sorted([k for k in ks if mids[k] is not None])
    if unbounded:
        res["S1_median"] = {"flag": "DEGENERATE (unbounded member: " + ",".join(unbounded) + ")"}
        res["S3_min"] = {"flag": "DEGENERATE (unbounded member — the minimum is unbounded below)"}
    elif defined:
        med = sorted(mids[k] for k in defined)
        m = med[len(med) // 2] if len(med) % 2 == 1 else 0.5 * (med[len(med) // 2 - 1] + med[len(med) // 2])
        res["S1_median"] = {"value_of_midpoints": r6(m),
                            "note": "median taken over coordinate d midpoints (labels for intervals)"}
        kmin = min(defined, key=lambda k: mids[k])
        res["S3_min"] = {"coordinate": kmin, "d": ijson(ds[kmin]),
                         "note": "nearest-to-frontier coordinate"}
    # S2: OBSERVED-only mean (labelled sensitivity, never the headline)
    obs_ks = [k for k in ks if not (h == "China" and k in ("k1", "k3"))]
    if obs_ks and all(ds[k] is not None for k in obs_ks):
        lo = sum(ds[k][0] for k in obs_ks) / len(obs_ks)
        hi = sum(ds[k][1] for k in obs_ks) / len(obs_ks)
        res["S2_observed_only_mean"] = {"members": obs_ks, "value": ijson((lo, hi)),
                                        "label": ("LABELLED SENSITIVITY (never the headline): "
                                                  "INFERRED-BOUNDED cells excluded"
                                                  + ("; for China this is k2 ALONE" if h == "China" else ""))}
    return res


def china_safe_sensitivity_composite(per_coord, tag):
    """China composite with k1 = SAFE-route-only d (labelled sensitivity, NOT the headline)."""
    sens = per_coord["k1"]["safe_route_sensitivity"][tag]["d"]
    if sens.get("lower") is None:
        return {"flag": "SAFE-route d unbounded"}
    ds = [(sens["lower"], sens["upper"])]
    for k in ["k2", "k3"]:
        d = per_coord[k][tag]["d"]
        ds.append((d["lower"], d["upper"]))
    lo = sum(d[0] for d in ds) / 3.0
    hi = sum(d[1] for d in ds) / 3.0
    mids = sorted(imid(d) for d in ds)
    return {"label": ("LABELLED SENSITIVITY — China composite with k1 = SAFE-anchor route only; "
                      "NOT the headline (the headline keeps the pre-registered envelope and is "
                      "degenerate)"),
            "members": ["k1(SAFE-route)", "k2", "k3"],
            "C": ijson((lo, hi)),
            "S1_median_of_midpoints": r6(mids[1]),
            "S3_min_of_midpoints": r6(mids[0])}


# ------------------------------------------------------------------ build everything
def compute():
    rus_cal = russia_calibration()
    scan = secondary_scan()

    calibration = {
        "_stamp": STAMP,
        "SOURCE": ("computed by build/reserve/RDT_recompute.py from "
                   "build/reserve/RDT_coordinates.parquet (primary input; includes the "
                   "_AGG_COFER/_LMW_PCTL/_PREF/_SAFE_ANCHOR pseudo-holder input rows) and "
                   "build/reserve/rd0_evidence/lmw_Data.xls sheet DATA (secondary-trajectory "
                   "scan ONLY); build/reserve/rd2_evidence/wb_pinksheet_MYFETCH.xlsx used "
                   "ONLY to cross-check P_ref; design fixed in build/reserve/RDT_prediction.md"),
        "no_date_no_probability": ("this artifact contains NO breaking-point date and NO "
                                   "probability; taus are conditional durations, not forecasts"),
        "p_ref_usd_per_ozt": {
            "from_parquet_PREF_row": r6(P_REF_PARQ),
            "rederived_from_wb_pinksheet_xlsx": r6(P_REF_XLSX),
            "match": bool(P_REF_MATCH),
            "ozt_per_tonne_constant": r6(OZT_PER_TONNE),
            "constant_note": ("exact troy-ounce conversion 1e6/31.1034768; the prediction's "
                              "tonnes*P_ref formula is dimensional shorthand — the conversion "
                              "constant is disclosed here and used everywhere")},
        "onsets": {"primary": PRIMARY_ONSET, "primary_origin": "end-2013 values",
                   "alternative": ALT_ONSET, "alternative_origin": "end-2017 values"},
        "frontier": {k: {"terminal": r6(FRONTIER[k]), "definition": FRONTIER_DEF[k],
                         "region_2019_2021": FRONTIER_REGION[k]} for k in ["k1", "k2", "k3", "k4"]},
        "russia_trajectory": rus_cal,
        "move_onset_ordering": {
            "rule": ("onset(k) = first year t>2013 with |x_t - x_2013| >= 0.10*|x_F - x_2013|, "
                     "sign-matching, sustained for all observed t' in [t, 2021] (the pre-freeze "
                     "path; full-series sustainment also checked and recorded per coordinate)"),
            "realized_onsets": {k: ONSETS[k] for k in ["k1", "k2", "k3", "k4"]},
            "realized_order_earliest_first": realized_order,
            "alternative_origin2017_variant_onsets": {k: ONSETS_ALT[k] for k in ["k1", "k2", "k3", "k4"]},
            "expected_pattern": EXPECTED,
            "components": ordering_components,
            "verdict_vs_expected": ORDERING_VERDICT,
            "verdict_note": (
                "the qualitative sequence gold->UST->currency "
                + ("HELD" if ordering_components["sequence_gold_before_ust_before_currency"] else "DID NOT HOLD")
                + f"; the mechanical k3 onset year is {ONSETS['k3']} (expected 2018): the RATIO "
                  "coordinate UST/total crossed the 10% threshold before the 2018 raw-dollar dump "
                  "because Russia's total reserves contracted 2014-2016 while raw UST holdings "
                  "were roughly flat — the raw $ collapse (102.5 -> 13.2 busd) is a 2018 event, "
                  "quoted in the raw series"),
        },
        "secondary_trajectory_scan": scan,
        "construction_judgments": [
            "onset/ordering rule origin = end-2013 value (per the calibration design); the "
            "path-fraction denominator = x(h, 2014) and x(h, 2018) (per the pre-registered "
            "metric formula); both are reported and neither is swapped for the other",
            "onset sustainment is evaluated on the pre-freeze path (through 2021); a full-series "
            "sustainment check is recorded per coordinate and does not change any onset",
            "k2 frontier region uses the 2019-2021 range of the constant-price share; Russia's "
            "post-2021 observations are post-freeze and excluded from the calibrated path",
            "secondary-scan qualifier window = the maximum-decline qualifying pair; the adapted "
            "onset rule for qualifiers uses origin = window start, terminal = window end value",
        ],
        "conditionality": DV_CAVEAT,
    }
    return calibration


def compute_result():
    per_holder = {}
    for h in HOLDERS:
        per_coord = {k: holder_coordinate_block(h, k) for k in ["k1", "k2", "k3", "k4"]}
        if h == "China":
            coherent, active = china_k3_extras()
            per_coord["k3"]["coherent_custody_pairing_sensitivity"] = coherent
            per_coord["k3"]["active_basis_PRIMARY_velocity"] = active
        comp = {"primary_onset_2014": composite(h, per_coord, "primary_onset_2014"),
                "alt_onset_2018": composite(h, per_coord, "alt_onset_2018")}
        if h == "China":
            comp["safe_route_sensitivity_composite"] = {
                t: china_safe_sensitivity_composite(per_coord, t)
                for t in ["primary_onset_2014", "alt_onset_2018"]}
        entry = {"per_coordinate_FIRST": per_coord, "composite_SECOND": comp}
        if h == "Russia":
            entry["role"] = ("CALIBRANT — Russia defines the path and the frontier; its position "
                             "is ~ the frontier BY CONSTRUCTION (d~0 at the 2021 terminal); its "
                             "post-2021 k2/k3 drift is post-freeze, outside the anticipatory "
                             "regime, and is NOT read as further exit")
        if h in ("India", "SaudiArabia"):
            entry["coverage_note"] = ("composite over k2,k3 only: k1 and k4_cny are "
                                      "NOT-AVAILABLE (absent from the LMW panel) — noted, "
                                      "not imputed")
        per_holder[h] = entry

    # expectation evaluation (mechanical)
    ch = per_holder["China"]["composite_SECOND"]
    headline_C = ch["primary_onset_2014"]["C"]
    safe_C = ch["safe_route_sensitivity_composite"]["primary_onset_2014"]["C"]

    def branch(mid):
        if mid is None:
            return "UNDETERMINED (midpoint degenerate)"
        if mid >= 0.60:
            return ">=0.60: early path — expectation (ii) consistent"
        if mid < 0.40:
            return "<0.40: far along — expectation (ii) REFUTED branch"
        return "0.40-0.60: neither confirmed nor refuted; reported as measured"

    expectation = {
        "i_russia_ordering": {"verdict": ORDERING_VERDICT,
                              "realized_onsets": {k: ONSETS[k] for k in ["k1", "k2", "k3", "k4"]},
                              "note": "see calibration.move_onset_ordering for the mechanical detail"},
        "ii_china_position": {
            "headline_C_midpoint": headline_C.get("midpoint"),
            "headline_branch": branch(headline_C.get("midpoint")),
            "headline_degeneracy_reason": headline_C.get("flag"),
            "SAFE_route_sensitivity_C_midpoint_labelled": safe_C.get("midpoint"),
            "SAFE_route_sensitivity_branch_labelled": branch(safe_C.get("midpoint")),
            "labelling": ("the SAFE-route branch is a LABELLED SENSITIVITY, reported because the "
                          "headline midpoint is degenerate from the [0,100] k1 envelope; it is "
                          "NOT swapped in as the headline"),
        },
        "iii_comparators_dispersion": {
            h: per_holder[h]["composite_SECOND"]["primary_onset_2014"]["C"].get("midpoint")
            for h in ["India", "Turkey", "SaudiArabia", "Poland"]},
    }

    result = {
        "_stamp": STAMP,
        "SOURCE": ("computed by build/reserve/RDT_recompute.py; INPUT BASIS (disclosed): "
                   "(1) build/reserve/RDT_coordinates.parquet — primary, includes the "
                   "_AGG_COFER/_LMW_PCTL/_PREF/_SAFE_ANCHOR pseudo-holder input rows; "
                   "(2) build/reserve/rd0_evidence/lmw_Data.xls sheet DATA (engine xlrd) — "
                   "used ONLY for the Part-2 secondary-trajectory scan (the full discloser "
                   "panel is not in the parquet); plus wb_pinksheet_MYFETCH.xlsx as a "
                   "P_ref cross-check ONLY (equality asserted, no other use); no network"),
        "no_date_no_probability": ("this artifact contains NO breaking-point date and NO "
                                   "probability; every tau is a conditional duration under a "
                                   "frozen velocity and carries its caveat"),
        "metric": {"d": "d_k(h,t) = (x_k(h,t) - x_F,k)/(x_k(h,origin) - x_F,k); origin years 2014 (primary) and 2018 (alternative)",
                   "v": "-Delta d / Delta t, path-fractions per year, positive = toward the frontier; recent-3y AND full-window, both always reported",
                   "tau": "d/v IF v>0, with the literal caveat on every tau",
                   "guard": "degeneracy guard per the pre-registration; raw-space distance when it fires",
                   "composite": "unweighted mean of d_k (pre-registered), with S1 median / S2 OBSERVED-only / S3 min computed"},
        "frontier_echo": {k: {"terminal": r6(FRONTIER[k]), "region_2019_2021": FRONTIER_REGION[k]}
                          for k in ["k1", "k2", "k3", "k4"]},
        "holders": per_holder,
        "k3_valuation_split": valuation_split(),
        "expectation_evaluation_mechanical": expectation,
        "binding_mode_boundary": (
            "this measures the ANTICIPATORY-REALLOCATION regime only; a self-fulfilling RUN — "
            "the old F4, named as such — is a discontinuity OUTSIDE these kinematics: stated, "
            "unmeasured, unpriced, untimed; nothing here bounds, prices, or times it"),
        "conditionality": DV_CAVEAT,
    }
    return result


# ------------------------------------------------------------------ the object (md)
def fmt_ij(d, nd=3):
    if d is None or d.get("lower") is None:
        return "UNBOUNDED"
    if abs(d["lower"] - d["upper"]) < 5e-7:
        return f"{d['lower']:.{nd}f}"
    return f"[{d['lower']:.{nd}f}, {d['upper']:.{nd}f}] (mid {d['midpoint']:.{nd}f})"


def build_object(cal, res):
    L = []
    A = L.append
    A("# RDT — The frontier / distance / hazard object (reserve-side exit trajectory)")
    A("")
    A("**STATUS: OUTPUT — NOT ESTABLISHED until the verifier artifact exists** "
      "(`build/reserve/RDT_verify.json`, all_pass=true).")
    A("")
    A("SOURCE: every number below is computed by `build/reserve/RDT_recompute.py` from "
      "two inputs — `build/reserve/RDT_coordinates.parquet` (primary; includes the "
      "`_AGG_COFER`/`_LMW_PCTL`/`_PREF`/`_SAFE_ANCHOR` input rows) and "
      "`build/reserve/rd0_evidence/lmw_Data.xls` sheet DATA (secondary-trajectory scan only) — "
      "plus `wb_pinksheet_MYFETCH.xlsx` solely as the P_ref equality cross-check. No network. "
      "Design pre-registered in `build/reserve/RDT_prediction.md`.")
    A("")
    A("**No date. No probability. No composite is sold as \"the\" number.** Every distance and "
      "velocity is " + DV_CAVEAT + ".")
    A("")
    A("## 1. The frontier (Russia's calibrated terminal state)")
    A("")
    A("| coord | definition | terminal x_F | frontier REGION (2019-2021 range) | onset found "
      "(primary rule, origin end-2013) | onset (alt variant, origin end-2017) |")
    A("|---|---|---|---|---|---|")
    for k in ["k1", "k2", "k3", "k4"]:
        f = cal["frontier"][k]
        A(f"| {k} | {K_LABEL[k].replace('%%','%')} | {f['terminal']:.3f} | "
          f"[{f['region_2019_2021'][0]:.3f}, {f['region_2019_2021'][1]:.3f}] | "
          f"{cal['move_onset_ordering']['realized_onsets'][k]} | "
          f"{cal['move_onset_ordering']['alternative_origin2017_variant_onsets'][k]} |")
    A("")
    mo = cal["move_onset_ordering"]
    A(f"Realized move-onset ordering (earliest first): **{' -> '.join(mo['realized_order_earliest_first'])}** "
      f"({', '.join(k + ' ' + str(mo['realized_onsets'][k]) for k in mo['realized_order_earliest_first'])}). "
      f"Verdict vs the pre-registered expected pattern: **{mo['verdict_vs_expected']}** — "
      + mo["verdict_note"] + ".")
    A("")
    rus = cal["russia_trajectory"]
    alt_on = mo["alternative_origin2017_variant_onsets"]
    n2018 = sum(1 for v in alt_on.values() if v == 2018)
    A("Onset sensitivity: under the alternative origin (end-2017) the mechanical onsets are "
      + "; ".join(f"{k} {alt_on[k]}" for k in ["k1", "k2", "k3", "k4"])
      + f" — {n2018} of 4 coordinates cross the threshold in 2018 itself, so the alternative "
        "origin does not resolve an ordering at annual resolution. Russia's full-path "
      "d-velocity (origin-2014 scaling, path-fractions/yr): "
      + "; ".join(f"{k} {rus[k]['velocity_path_fraction_per_yr']['full_path_2014_2021']}"
                  for k in ["k1", "k2", "k3", "k4"])
      + ". Phase velocities show the regime shifts: "
      + "; ".join(f"{k} {rus[k]['velocity_path_fraction_per_yr']['phase_2014_2018']} (2014-18) vs "
                  f"{rus[k]['velocity_path_fraction_per_yr']['phase_2018_2021']} (2018-21)"
                  for k in ["k1", "k2", "k3", "k4"]) + ".")
    A("")
    scan = cal["secondary_trajectory_scan"]
    A(f"Secondary trajectories (mechanical scan of {scan['n_disclosers_scanned']} LMW disclosers): "
      f"**{scan['n_qualifiers']} qualifiers** (USD-share decline >=15pp within <=10y, no recovery "
      "above start-10pp): "
      + "; ".join(f"{q['country']} {q['window'][0]}->{q['window'][1]} "
                  f"({q['start_usd_pp']:.1f}->{q['end_usd_pp']:.1f}pp, -{q['decline_pp']:.1f}pp, "
                  f"final {q['final_usd_pp']:.1f})" for q in scan["qualifiers"]) + ".")
    for q in scan["qualifiers"]:
        if "onsets_over_window" in q and q["country"] != "Russia":
            A(f"  - {q['country']} move-ordering over its window (adapted rule): "
              + ", ".join(f"{k}={q['onsets_over_window'][k]}" for k in ["k1", "k2", "k3", "k4"])
              + " — vs Russia's k2->k3->k4->k1; where a qualifier is not one of the six holders "
                "its k2/k3 are not in the coordinates file and its ordering is not computed.")
    A("")
    A(scan["n1_statement"] + ".")
    A("")
    A("## 2. Distances and velocities (per coordinate FIRST; composite second)")
    for h in HOLDERS:
        hd = res["holders"][h]
        A("")
        A(f"### {h}" + (" — CALIBRANT (position ~ frontier by construction)" if h == "Russia" else ""))
        if "coverage_note" in hd:
            A("")
            A("_" + hd["coverage_note"] + "_")
        A("")
        A("| coord | flag | vintage | raw position | d (2014 origin) | d (2018 origin) | "
          "v recent-3y (d/yr) | v full-window (d/yr) |")
        A("|---|---|---|---|---|---|---|---|")
        for k in ["k1", "k2", "k3", "k4"]:
            b = hd["per_coordinate_FIRST"][k]
            if "status" in b:
                A(f"| {k} | {b['status']} | — | — | — | — | — | — |")
                continue
            if h == "China" and k == "k1":
                pos = fmt_ij(b["headline_envelope_union_of_routes"]["value_pp"]) + " pp (envelope; INFERRED-BOUNDED)"
                d14 = fmt_ij(b["primary_onset_2014"]["d_headline"])
                d18 = fmt_ij(b["alt_onset_2018"]["d_headline"])
                v3 = vf = "not computable on envelope"
                vint = b["vintage_latest_both_routes"]
                flag = "INFERRED-BOUNDED"
            else:
                pos = fmt_ij(b["position_raw"]) + (" (band)" if h == "China" and k == "k3" else "")
                p14, p18 = b["primary_onset_2014"], b["alt_onset_2018"]
                d14 = (p14["d"].get("status") or fmt_ij(p14["d"])) if isinstance(p14.get("d"), dict) else "—"
                d18 = (p18["d"].get("status") or fmt_ij(p18["d"])) if isinstance(p18.get("d"), dict) else "—"
                vel = p14.get("velocities", {})
                v3 = fmt_ij(vel["recent_3y"]["v_path_fraction_per_yr"]) if "recent_3y" in vel else "—"
                vf = fmt_ij(vel["full_window"]["v_path_fraction_per_yr"]) if "full_window" in vel else "—"
                vint = b.get("vintage_latest", "—")
                flag = b.get("observability", "OBSERVED")
            A(f"| {k} | {flag} | {vint} | {pos} | {d14} | {d18} | {v3} | {vf} |")
        if h == "China":
            b1 = hd["per_coordinate_FIRST"]["k1"]
            A("")
            A("China k1 (INFERRED-BOUNDED everywhere it appears): headline envelope "
              + fmt_ij(b1["headline_envelope_union_of_routes"]["value_pp"])
              + " pp — the union with the [0,100]-clipped residual route is effectively [0,100]; "
                "raw residual endpoints (unclipped): 2014 "
              + str(b1["headline_envelope_union_of_routes"]["residual_raw_endpoints_echo_pp"]["origin_2014"])
              + ", 2025 "
              + str(b1["headline_envelope_union_of_routes"]["residual_raw_endpoints_echo_pp"]["latest_2025"])
              + " pp. d is UNBOUNDED by interval arithmetic (the origin envelope straddles the "
                "frontier), so China's headline composite is degenerate — reported, not smoothed. "
                "SAFE-route SENSITIVITY (labelled, NOT the headline): position "
              + fmt_ij(b1["safe_route_sensitivity"]["position_pp"]) + " pp, d(2014 origin) "
              + fmt_ij(b1["safe_route_sensitivity"]["primary_onset_2014"]["d"]) + ", d(2018 origin) "
              + fmt_ij(b1["safe_route_sensitivity"]["alt_onset_2018"]["d"]) + ".")
            act = hd["per_coordinate_FIRST"]["k3"]["active_basis_PRIMARY_velocity"]["primary_onset_2014"]
            coh = hd["per_coordinate_FIRST"]["k3"]["coherent_custody_pairing_sensitivity"]["primary_onset_2014"]
            A("")
            A("China k3 (custody BAND, INFERRED-BOUNDED everywhere it appears): ACTIVE-basis "
              "(primary) — cumulative net long-term Treasury transactions from 2014 on the TIC "
              "band, over WB denominators: H_active(2025) = "
              + fmt_ij(act["H_active_latest_busd"], 1) + " $bn, x_active = "
              + fmt_ij(act["x_active_latest_pct"], 2) + "%, d_active = "
              + fmt_ij(act["d_active_latest"]) + "; v_active recent-3y "
              + fmt_ij(act["v_active_recent_3y_path_fraction_per_yr"]) + " d/yr, full-window "
              + fmt_ij(act["v_active_full_window_path_fraction_per_yr"]) + " d/yr; raw active flow "
              + fmt_ij(act["v_active_raw_busd_per_yr"]["recent_3y"], 1) + " $bn/yr (recent-3y, = mean "
              "net transactions) vs market-value holdings drift "
              + str(act["raw_holdings_market_value_v_busd_per_yr_alongside"]["recent_3y"]["china_alone"])
              + " (China-alone) / "
              + str(act["raw_holdings_market_value_v_busd_per_yr_alongside"]["recent_3y"]["china_plus_bel_lux"])
              + " (China+BEL+LUX) $bn/yr — the valuation confound is why the active basis is primary. Coherent "
                "custody-pairing sensitivity: d = " + str(coh["d_china_alone_path"])
              + " (China-alone path) vs " + str(coh["d_china_plus_bel_lux_path"])
              + " (China+BEL+LUX path); both paths approach on recent-3y ("
              + str(coh["v_recent_3y_path_fraction_per_yr"]["china_alone"]) + " / "
              + str(coh["v_recent_3y_path_fraction_per_yr"]["china_plus_bel_lux"]) + " d/yr).")
        comp = hd["composite_SECOND"]["primary_onset_2014"]
        A("")
        line = (f"Composite ({comp['label'].split(':')[0]}): C = {fmt_ij(comp['C'])}"
                + (f" — {comp['C']['flag']}" if comp["C"].get("flag") else "")
                + f"; members {'+'.join(comp['members'])}")
        s1 = comp.get("S1_median", {})
        s3 = comp.get("S3_min", {})
        s2 = comp.get("S2_observed_only_mean")
        line += ("; S1 median " + (str(s1.get("value_of_midpoints")) if "value_of_midpoints" in s1 else s1.get("flag", "—")))
        if s2:
            line += f"; S2 OBSERVED-only {fmt_ij(s2['value'])} ({'+'.join(s2['members'])})"
        line += ("; S3 min " + (f"{s3.get('coordinate')} {fmt_ij(s3.get('d'))}" if "coordinate" in s3 else s3.get("flag", "—")))
        alt = hd["composite_SECOND"]["alt_onset_2018"]["C"]
        line += f". Alt-onset (2018) C = {fmt_ij(alt)}" + (f" — {alt['flag']}" if alt.get("flag") else "") + "."
        A(line)
        if h == "China":
            sc = hd["composite_SECOND"]["safe_route_sensitivity_composite"]
            A("SAFE-route sensitivity composite (labelled, NOT the headline): C = "
              + fmt_ij(sc["primary_onset_2014"]["C"]) + " (2014 origin); "
              + fmt_ij(sc["alt_onset_2018"]["C"]) + " (2018 origin).")
    A("")
    ee = res["expectation_evaluation_mechanical"]
    A("Pre-registered expectation, evaluated mechanically: (i) Russia ordering **"
      + ee["i_russia_ordering"]["verdict"] + "**; (ii) China headline C midpoint = "
      + ("DEGENERATE (unbounded interval)" if ee["ii_china_position"]["headline_C_midpoint"] is None
         else str(ee["ii_china_position"]["headline_C_midpoint"])) + " -> branch: "
      + ee["ii_china_position"]["headline_branch"] + "; SAFE-route sensitivity C midpoint (labelled) = "
      + str(ee["ii_china_position"]["SAFE_route_sensitivity_C_midpoint_labelled"]) + " -> "
      + ee["ii_china_position"]["SAFE_route_sensitivity_branch_labelled"]
      + "; (iii) comparator composite midpoints: "
      + ", ".join(f"{h} {v}" for h, v in ee["iii_comparators_dispersion"].items()) + ".")
    A("")
    A("## 3. The hazard — conditional kinematics only")
    A("")
    A("For every holder-coordinate with d > 0 and v > 0, tau = d/v — each tau strictly \""
      + TAU_CAVEAT + "\". If v <= 0: not approaching at current velocity, no tau.")
    A("")
    A("| holder | coord | d (2014 origin) | v recent-3y | tau recent-3y (yr) | v full | tau full (yr) |")
    A("|---|---|---|---|---|---|---|")
    for h in HOLDERS:
        for k in ["k1", "k2", "k3", "k4"]:
            b = res["holders"][h]["per_coordinate_FIRST"][k]
            if "status" in b:
                continue
            if h == "China" and k == "k1":
                A(f"| {h} | k1 | UNBOUNDED (envelope) | — | not computable (unbounded interval input) | — | — |")
                continue
            p = b["primary_onset_2014"]
            if "d" not in p or (isinstance(p["d"], dict) and "status" in p["d"]):
                continue
            vel = p.get("velocities", {})
            taus = p.get("tau_if_velocity_persists", {})

            def tcell(w):
                if w not in taus:
                    return "—", "—"
                t = taus[w]
                vtxt = fmt_ij(vel[w]["v_path_fraction_per_yr"]) if w in vel else "—"
                if "tau_years" in t:
                    ty = t["tau_years"]
                    return vtxt, (f"[{ty['lower']:.1f}, {ty['upper']:.1f}]"
                                  if abs(ty["lower"] - ty["upper"]) > 5e-7 else f"{ty['lower']:.1f}")
                return vtxt, t.get("status", "—")
            v3, t3 = tcell("recent_3y")
            vf, tf = tcell("full_window")
            A(f"| {h} | {k} | {fmt_ij(p['d'])} | {v3} | {t3} | {vf} | {tf} |")
    act = res["holders"]["China"]["per_coordinate_FIRST"]["k3"]["active_basis_PRIMARY_velocity"]["primary_onset_2014"]
    A("")
    A("China k3 ACTIVE-basis kinematics (primary construction for China's k3 velocity): "
      "tau recent-3y: " + json.dumps(act["tau_active_if_velocity_persists"]["recent_3y"].get("tau_years")
                                     or act["tau_active_if_velocity_persists"]["recent_3y"].get("status"))
      + "; tau full-window: " + json.dumps(act["tau_active_if_velocity_persists"]["full_window"].get("tau_years")
                                           or act["tau_active_if_velocity_persists"]["full_window"].get("status"))
      + " — each \"" + TAU_CAVEAT + "\".")
    A("")
    A("**Regime-shift statement:** velocities regime-shift — Russia's own velocity changed "
      "discontinuously in 2014 and again in 2018 (phase velocities in section 1) — so every tau "
      "above is a kinematic descriptor under a frozen velocity, never a forecast and never a date.")
    A("")
    A("**Boundary statement:** " + res["binding_mode_boundary"] + ".")
    A("")
    A("## 4. Limitations (in the object, not a footnote)")
    A("")
    ch_k1 = res["holders"]["China"]["per_coordinate_FIRST"]["k1"]
    ch_k3 = res["holders"]["China"]["per_coordinate_FIRST"]["k3"]
    band = ch_k3["raw_beside"]["ust_busd_latest_published"]
    band_vint = ch_k3["raw_beside"]["ust_vintage"]
    width = band["upper"] - band["lower"]
    A("1. **Path calibration rests on Russia (N=1 completed exit).** The scan found "
      f"{scan['n_qualifiers']} USD-share-decline qualifiers, but none is a completed all-"
      "coordinate anticipatory exit; Turkey's ordering over its own decline window differs from "
      "Russia's (currency first, gold/UST later), so the Russia ordering is not a universal law.")
    A("2. **China k1 is INFERRED-BOUNDED, never a point.** The residual route is nearly "
      "uninformative: raw endpoints "
      + str(ch_k1["headline_envelope_union_of_routes"]["residual_raw_endpoints_echo_pp"]["origin_2014"])
      + " pp (2014) and "
      + str(ch_k1["headline_envelope_union_of_routes"]["residual_raw_endpoints_echo_pp"]["latest_2025"])
      + " pp (2025), clipped to [0,100]; the headline envelope is effectively [0,100] and every "
        "downstream headline number carries that width (hence the degenerate headline composite).")
    A(f"3. **China k3 custody band width**: at the latest published month ({band_vint}) the band "
      f"is [{band['lower']:.1f}, {band['upper']:.1f}] $bn UST — **{width:.1f} $bn wide** "
      "(China-alone vs China+Belgium+Luxembourg; Euroclear/Clearstream custody also serves "
      "non-China clients, so the band is intentionally wide).")
    A("4. **k4 is coarse**: CIPS per-country participation NOT-AVAILABLE (publisher does not "
      "publish it); LMW CNY shares are grounded zeros for Turkey/Poland and NOT-AVAILABLE for "
      "India/Saudi Arabia; swap lines are context flags only (India 0, Turkey 35, Saudi 50, "
      "Russia 150 bn CNY), never composite inputs.")
    A("5. **COFER 2025Q3 methodology break** (unallocated eliminated; IMF-staff imputation back "
      "to 2000Q1, TNM/2025/14) rides every residual-route input; **LMW thins in 2023** (n=31 "
      "disclosers vs ~49-56 earlier), so the 2023 percentiles behind the 2024-2026 residual and "
      "SAFE corridors rest on a thinner cross-section that freezes after 2023.")
    A("6. **The valuation split is a residual construction**: by-country valuation change exists "
      "only from 2023-02 (basis break marked in the 2023 rows); pre-2023 the split is bounded, "
      "and the residual absorbs coverage/custody reclassification, not only price — the "
      "2022-2023 rates selloff cut market values with zero selling (the false-positive-exit "
      "confound), which is why China's k3 velocity is computed on the active basis.")
    A("7. Russia k2 denominators end 2024 and Poland k3 2026 is unpublished; each coordinate is "
      "measured at its own latest vintage, stated per cell.")
    A("")
    A("STATUS: OUTPUT — NOT ESTABLISHED until the verifier artifact exists.")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ serialize + verify
def serialize(obj):
    return json.dumps(obj, indent=1, ensure_ascii=True, sort_keys=False)


def main():
    cal1, res1 = compute(), compute_result()
    obj1 = build_object(cal1, res1)
    s_cal1, s_res1 = serialize(cal1), serialize(res1)
    with open(OUT_CAL, "w") as f:
        f.write(s_cal1 + "\n")
    with open(OUT_RES, "w") as f:
        f.write(s_res1 + "\n")
    with open(OUT_OBJ, "w") as f:
        f.write(obj1)

    # full second pass (re-run the same code path; byte-compare)
    cal2, res2 = compute(), compute_result()
    obj2 = build_object(cal2, res2)
    cal_match = serialize(cal2) == s_cal1
    res_match = serialize(res2) == s_res1
    obj_match = obj2 == obj1

    # integrity anchors, quoted from the assembled parquet (a failed anchor halts)
    rus_ust = point_series("Russia", "k3_ust_busd")
    anchor_2018 = (abs(rus_ust[2017] - 102.5) < 1e-9 and abs(rus_ust[2018] - 13.2) < 1e-9)
    rus_t = point_series("Russia", "k2_gold_tonnes")
    anchor_gold = (abs(rus_t[2013] - 1035.21) < 1e-9 and abs(rus_t[2020] - 2298.53) < 1e-9)

    verify = {
        "purpose": ("verifier artifact for RDT Parts 2-4: records that every output was "
                    "regenerated from the two committed inputs alone by the same code path and "
                    "byte-matches what was written; until all_pass=true every number in "
                    "RDT_calibration.json / RDT_result.json / RDT_breaking_point_object.md is "
                    "an OUTPUT, not established"),
        "input_basis_disclosed": {
            "primary": "build/reserve/RDT_coordinates.parquet",
            "secondary_scan_only": "build/reserve/rd0_evidence/lmw_Data.xls (sheet DATA, engine xlrd)",
            "cross_check_only": "build/reserve/rd2_evidence/wb_pinksheet_MYFETCH.xlsx (P_ref equality only)",
            "network": "none"},
        "input_sha256": {"RDT_coordinates.parquet": sha256(PARQ),
                         "lmw_Data.xls": sha256(LMW_XLS),
                         "wb_pinksheet_MYFETCH.xlsx": sha256(PINK)},
        "output_sha256": {"RDT_calibration.json": sha256(OUT_CAL),
                          "RDT_result.json": sha256(OUT_RES),
                          "RDT_breaking_point_object.md": sha256(OUT_OBJ)},
        "match_flags": {
            "p_ref_parquet_equals_pinksheet_rederivation": bool(P_REF_MATCH),
            "recompute_second_pass_byte_identical_calibration": bool(cal_match),
            "recompute_second_pass_byte_identical_result": bool(res_match),
            "recompute_second_pass_byte_identical_object": bool(obj_match),
            "anchor_russia_2018_ust_collapse_replicated": bool(anchor_2018),
            "anchor_russia_gold_accumulation_replicated": bool(anchor_gold),
        },
        "anchor_quotes": {
            "russia_ust_busd_dec2017_dec2018": [r6(rus_ust[2017]), r6(rus_ust[2018])],
            "russia_gold_tonnes_end2013_end2020": [r6(rus_t[2013]), r6(rus_t[2020])]},
        "all_pass": bool(P_REF_MATCH and cal_match and res_match and obj_match
                         and anchor_2018 and anchor_gold),
    }
    with open(OUT_VER, "w") as f:
        f.write(serialize(verify) + "\n")
    print("all_pass =", verify["all_pass"])
    for k, v in verify["match_flags"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
