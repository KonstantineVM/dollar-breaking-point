#!/usr/bin/env python3
"""RDT-E Part 1(i)-(iii)+(vi) -- on-disk ingredients for the migration bound.

Deterministic recompute. Regenerates:
  build/reserve/RDTE_ingredients.json
  build/reserve/RDTE_ingredients_panel.parquet

Contract: build/reserve/RDTE_prediction.md (pre-registered; windows, classes, cap
constructions, blind spots and the flipped guard are fixed there and applied exactly).

Everything computed from on-disk inputs; nothing hardcoded except the pre-registered
window boundaries and the reconciliation TARGETS quoted from the committed RDT-C/D
ledgers (each target is read from the committed JSON at run time, never typed in).
No network. No breaking-point date, no probability.
"""

import csv
import hashlib
import json
import os
import re
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

P_PANEL = os.path.join(ROOT, "build/reserve/RDTC_class_panel.parquet")
P_FLOWS = os.path.join(ROOT, "build/reserve/RDTC_class_flows.json")
P_RDTD = os.path.join(ROOT, "build/reserve/RDTD_result.json")
P_FRAG = os.path.join(ROOT, "build/reserve/RDTD_fragility.json")
P_MFH = os.path.join(ROOT, "build/reserve/rdt_evidence/tic/mfhhis01.csv")
P_PRED = os.path.join(ROOT, "build/reserve/RDTE_prediction.md")

OUT_JSON = os.path.join(ROOT, "build/reserve/RDTE_ingredients.json")
OUT_PARQUET = os.path.join(ROOT, "build/reserve/RDTE_ingredients_panel.parquet")

CLASSES = ["treasury_lt", "agency_lt", "corp_other_bonds_lt", "equity_lt"]
ALL_CLASSES = CLASSES + ["total_lt"]
CHINA = "China, Mainland"
BE = "Belgium"
LU = "Luxembourg"
BELU = "Belgium+Luxembourg"

# Pre-registered windows (RDTE_prediction.md: "Windows fixed").
AXIS_START, AXIS_END = "2023-05", "2026-04"
AXIS_REF = "2023-04"  # holdings reference month, committed RDT-D convention
FULL_START = "2013-01"  # active-flow series start (panel, Form S basis)

R3 = lambda x: None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 3)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def months_range(a, b):
    return [str(p) for p in pd.period_range(a, b, freq="M")]


# ----------------------------------------------------------------------------
# 0. Load inputs; verify the panel schema (the committed basis)
# ----------------------------------------------------------------------------

panel = pd.read_parquet(P_PANEL)
flows = json.load(open(P_FLOWS))
rdtd = json.load(open(P_RDTD))
frag = json.load(open(P_FRAG))
pred_text = open(P_PRED, encoding="utf-8").read()

schema_checks = {
    "columns_expected": ["country", "month", "asset_class", "pos_musd", "active_musd",
                         "valchg_musd", "basis", "pos_source", "tx_source"],
    "columns_found": list(panel.columns),
    "countries_found": sorted(panel["country"].unique().tolist()),
    "classes_found": sorted(panel["asset_class"].unique().tolist()),
    "month_span": [str(panel["month"].min()), str(panel["month"].max())],
    "native_unit": "millions of USD (musd); this artifact reports busd = musd/1000",
}
assert schema_checks["columns_found"] == schema_checks["columns_expected"], "panel schema drift"
assert schema_checks["countries_found"] == sorted([CHINA, BE, LU]), "panel countries drift"
assert schema_checks["classes_found"] == sorted(ALL_CLASSES), "panel classes drift"

# positions begin 2020-01; active flows begin 2013-01 (verified, not asserted from memory)
pos_first = panel.dropna(subset=["pos_musd"])["month"].min()
act_first = panel.dropna(subset=["active_musd"])["month"].min()
schema_checks["positions_first_month"] = str(pos_first)
schema_checks["active_first_month"] = str(act_first)
assert pos_first == "2020-01" and act_first == "2013-01"

axis_months = months_range(AXIS_START, AXIS_END)
assert panel[panel["month"].isin(axis_months)]["active_musd"].notna().all(), "NaN active inside axis"

# convenience pivots (busd)
act = panel.pivot_table(index=["country", "month"], columns="asset_class",
                        values="active_musd", aggfunc="sum") / 1000.0
pos = panel.pivot_table(index=["country", "month"], columns="asset_class",
                        values="pos_musd", aggfunc="sum") / 1000.0


def series(country, cls, table):
    """country in {CHINA, BE, LU, BELU} -> pd.Series indexed by month (busd)."""
    if country == BELU:
        s = table.loc[BE][cls].add(table.loc[LU][cls], fill_value=np.nan)
        # BELU = BE + LU only where both defined (identical coverage in this panel)
        s = table.loc[BE][cls] + table.loc[LU][cls]
    else:
        s = table.loc[country][cls]
    return s.sort_index()


# ----------------------------------------------------------------------------
# 1. Levels and first differences -- summaries (detail goes to the parquet)
# ----------------------------------------------------------------------------

def stats_block(s, window_months):
    v = s.reindex(window_months).dropna()
    if len(v) == 0:
        return {"n_months": 0, "note": "no data in window"}
    return {
        "n_months": int(len(v)),
        "cum_busd": R3(v.sum()),
        "mean_busd": R3(v.mean()),
        "sd_busd": R3(v.std(ddof=1)) if len(v) > 1 else None,
        "min_busd": R3(v.min()), "min_month": str(v.idxmin()),
        "max_busd": R3(v.max()), "max_month": str(v.idxmax()),
    }


def level_block(s, window_months, ref_month=None):
    v = s.reindex(window_months).dropna()
    if len(v) == 0:
        return {"n_months": 0, "note": "no position data in window (positions begin 2020-01)"}
    out = {
        "n_months": int(len(v)),
        "first_month": str(v.index[0]), "first_busd": R3(v.iloc[0]),
        "last_month": str(v.index[-1]), "last_busd": R3(v.iloc[-1]),
        "delta_first_to_last_busd": R3(v.iloc[-1] - v.iloc[0]),
    }
    if ref_month is not None and ref_month in s.index and not np.isnan(s.loc[ref_month]):
        out["reference_month"] = ref_month
        out["reference_level_busd"] = R3(s.loc[ref_month])
        out["delta_vs_reference_busd"] = R3(v.iloc[-1] - s.loc[ref_month])
    return out


full_months = months_range(FULL_START, AXIS_END)
series_summaries = {}
for country in [CHINA, BE, LU, BELU]:
    series_summaries[country] = {}
    for cls in ALL_CLASSES:
        a = series(country, cls, act)
        p = series(country, cls, pos)
        dpos = p.diff()
        series_summaries[country][cls] = {
            "active_flows_busd (PRIMARY first-difference basis)": {
                "verdict_axis_2023_05_to_2026_04": stats_block(a, axis_months),
                "full_window_from_series_start_2013_01": stats_block(a, full_months),
            },
            "holdings_levels_busd (alongside)": {
                "verdict_axis (reference month 2023-04, committed RDT-D convention)":
                    level_block(p, axis_months, ref_month=AXIS_REF),
                "full_window_from_series_start_2020_01": level_block(p, full_months),
            },
            "holdings_first_differences_busd (alongside)": {
                "verdict_axis_2023_05_to_2026_04": stats_block(dpos, axis_months),
                "full_window_from_series_start_2020_01_diffs_from_2020_02":
                    stats_block(dpos, full_months),
            },
        }

# ----------------------------------------------------------------------------
# 2. Cap A -- class-matched accretion cap (verdict axis, active basis)
# ----------------------------------------------------------------------------

capA_rows, capA_total = {}, 0.0
for cls in CLASSES:
    dch = float(series(CHINA, cls, act).reindex(axis_months).sum())    # window active sum
    dbl = float(series(BELU, cls, act).reindex(axis_months).sum())
    room_decline = max(-dch, 0.0)
    room_accrete = max(dbl, 0.0)
    capc = min(room_decline, room_accrete)
    capA_total += capc
    if room_decline == 0.0:
        why = "caps out mechanically: China did NOT actively sell this class over the axis"
    elif room_accrete == 0.0:
        why = "caps out mechanically: BE/LU had NO net active accretion in this class over the axis"
    elif capc == room_accrete:
        why = "binds on the BE/LU accretion side (accretion smaller than China's decline)"
    else:
        why = "binds on the China decline side (decline smaller than BE/LU accretion)"
    capA_rows[cls] = {
        "china_active_window_sum_busd": R3(dch),
        "belu_active_window_sum_busd": R3(dbl),
        "china_decline_room_busd": R3(room_decline),
        "belu_accretion_room_busd": R3(room_accrete),
        "capA_class_busd": R3(capc),
        "binding": why,
    }

# holdings-basis variant (labelled context; reference-month convention)
capA_hold_rows, capA_hold_total = {}, 0.0
for cls in CLASSES:
    pch = series(CHINA, cls, pos)
    pbl = series(BELU, cls, pos)
    dch = float(pch.loc[AXIS_END] - pch.loc[AXIS_REF])
    dbl = float(pbl.loc[AXIS_END] - pbl.loc[AXIS_REF])
    capc = min(max(-dch, 0.0), max(dbl, 0.0))
    capA_hold_total += capc
    capA_hold_rows[cls] = {
        "china_delta_holdings_busd": R3(dch),
        "belu_delta_holdings_busd": R3(dbl),
        "capA_holdings_class_busd": R3(capc),
    }

# blind spot -- extracted VERBATIM from the pre-registration (assert found)
m = re.search(r"Blind spot: (within-window netting.*?safe direction for a cap)\.",
              pred_text, re.S)
assert m, "capA blind-spot passage not found verbatim in RDTE_prediction.md"
capA_blindspot = re.sub(r"\s+", " ", m.group(1)) + "."

cap_A = {
    "definition (verbatim construction, pre-registered)":
        "capA = Sum_c min( max(-DeltaChina_active_c, 0), max(DeltaBELU_active_c, 0) ), "
        "active basis, verdict axis 2023-05..2026-04, SLT classes",
    "per_class": capA_rows,
    "capA_total_busd": R3(capA_total),
    "blind_spot (quoted from RDTE_prediction.md)": capA_blindspot,
    "blind_spot_direction": "OVERSTATING-SAFE: capA counts gross class-matched room, not "
        "China's share of it, so it can only OVERSTATE the migration ceiling -- the safe "
        "direction for a cap (pre-registered).",
    "holdings_basis_variant (LABELLED CONTEXT, not the cap -- holdings deltas mix active "
    "flows with valuation and the SLT gap G; reference month 2023-04)": {
        "per_class": capA_hold_rows,
        "capA_holdings_total_busd": R3(capA_hold_total),
    },
}

# ----------------------------------------------------------------------------
# 3. Cap B -- synchronized-mirror timing cap
# ----------------------------------------------------------------------------

def mirror_masses(cls, rise_months):
    d = series(CHINA, cls, act).reindex(axis_months)
    r = series(BELU, cls, act).reindex(rise_months)
    decline = (-d).clip(lower=0.0)          # China monthly active decline, busd
    rise = r.clip(lower=0.0)                # BELU monthly active rise, busd
    return decline, rise


def greedy_match(decline, rise, max_lag):
    """Greedy nearest-month matching WITHOUT double-counting.

    Remaining masses are decremented as they are matched, so no BE/LU rise is ever
    matched against more than one China decline (and vice versa). Order: distance
    k = 0,1,...,max_lag; within each distance, China-decline months chronologically;
    within a month, LAG (BE/LU rise k months AFTER the decline) before LEAD (k months
    BEFORE). Deterministic.
    """
    drem = decline.copy()
    rrem = rise.copy()
    matched = 0.0
    pairs = []
    dmonths = list(decline.index)
    for k in range(0, max_lag + 1):
        for mth in dmonths:
            if drem[mth] <= 0:
                continue
            for sign in ([0] if k == 0 else [+1, -1]):  # lag first, then lead
                tgt = str(pd.Period(mth, freq="M") + sign * k)
                if tgt not in rrem.index or rrem[tgt] <= 0 or drem[mth] <= 0:
                    continue
                amt = min(drem[mth], rrem[tgt])
                drem[mth] -= amt
                rrem[tgt] -= amt
                matched += amt
                pairs.append((mth, tgt, amt))
    return matched, pairs


matching_description = (
    "Per class, per month m in the verdict axis: China decline d_m = max(-active_China_m, 0), "
    "BE/LU rise r_m = max(+active_BELU_m, 0) (BELU = Belgium + Luxembourg monthly active, "
    "busd). CONTEMPORANEOUS = Sum_m min(d_m, r_m). PLUS-MINUS-3 (THE CAP) = greedy "
    "nearest-month matching: iterate distance k = 0,1,2,3; within each k, iterate China "
    "months chronologically; within a month, match the rise k months AFTER the decline "
    "before the rise k months BEFORE; each match decrements BOTH remaining masses, so no "
    "BE/LU rise is double-counted against multiple China declines. Rises are restricted to "
    "axis months (window fixed by the pre-registration); edge truncation can only "
    "UNDERSTATE capB at the window boundary -- an extended-rise sensitivity "
    "(2023-02..2026-04) is reported beside it, labelled, to size that edge effect."
)

capB_rows = {}
capB_contemp_total = capB_pm3_total = capB_pm3_ext_total = 0.0
floor_pairs = []
floor_mass_primary = floor_mass_mean_variant = 0.0
ext_rise_months = months_range("2023-02", AXIS_END)  # sensitivity only

for cls in CLASSES:
    decline, rise = mirror_masses(cls, axis_months)
    contemp = float(np.minimum(decline.reindex(axis_months, fill_value=0.0),
                               rise.reindex(axis_months, fill_value=0.0)).sum())
    pm3, _ = greedy_match(decline, rise, 3)
    _, rise_ext = mirror_masses(cls, ext_rise_months)
    pm3_ext, _ = greedy_match(decline, rise_ext, 3)
    capB_contemp_total += contemp
    capB_pm3_total += pm3
    capB_pm3_ext_total += pm3_ext
    capB_rows[cls] = {
        "contemporaneous_busd (context)": R3(contemp),
        "pm3_busd (THE CAP)": R3(pm3),
        "pm3_extended_rise_window_busd (labelled sensitivity, rises 2023-02..2026-04)":
            R3(pm3_ext),
    }
    # candidate floor: same month, same class, near-equal masses
    for mth in axis_months:
        dm, rm = float(decline[mth]), float(rise[mth])
        if dm > 0 and rm > 0:
            pm_min = min(dm, rm)
            pm_mean = 0.5 * (dm + rm)
            if abs(dm - rm) <= 0.10 * pm_min:
                floor_mass_primary += pm_min
                floor_pairs.append({"month": mth, "class": cls,
                                    "china_decline_busd": R3(dm),
                                    "belu_rise_busd": R3(rm),
                                    "matched_mass_busd": R3(pm_min)})
            if abs(dm - rm) <= 0.10 * pm_mean:
                floor_mass_mean_variant += pm_min

m = re.search(r"\*\*(Blind spot, stated up front: STAGGERED migration.*?evades this cap\s+entirely\.)\*\*", pred_text, re.S)
assert m, "capB staggered blind-spot passage not found verbatim in RDTE_prediction.md"
capB_blindspot_verbatim = re.sub(r"\s+", " ", m.group(1))

cap_B = {
    "matching_procedure": matching_description,
    "per_class": capB_rows,
    "capB_contemporaneous_total_busd (context)": R3(capB_contemp_total),
    "capB_pm3_total_busd (THE CAP)": R3(capB_pm3_total),
    "capB_pm3_extended_rise_sensitivity_busd (labelled, not the cap)": R3(capB_pm3_ext_total),
    "blind_spot (quoted verbatim from RDTE_prediction.md)": capB_blindspot_verbatim,
    "candidate_floor (pre-registered rule)": {
        "rule": "month+class-matched mirror pairs with |China decline - BE/LU rise| <= 10% "
                "of the pair mass, SAME month and class",
        "pair_mass_operationalization": "PRIMARY: pair mass = min(decline, rise) (the "
            "matched mirror mass; the stricter reading). SENSITIVITY: pair mass = "
            "(decline + rise)/2. Both reported; the pre-registration fixed the rule but "
            "not this arithmetic detail, so the stricter reading is primary.",
        "qualifying_pairs": floor_pairs,
        "floor_mass_busd_primary": R3(floor_mass_primary),
        "floor_mass_busd_mean_variant": R3(floor_mass_mean_variant),
        "label": "CONSISTENT-WITH-migration, NEVER established beneficial-ownership fact; "
                 "the headline M_lo stays 0 with this as a labelled sensitivity "
                 "(pre-registered).",
    },
}

# ----------------------------------------------------------------------------
# 4. Class-mix: China's pre-decline composition vs the BE/LU accretion mix
# ----------------------------------------------------------------------------

china_pos_ref = {cls: float(series(CHINA, cls, pos).loc[AXIS_REF]) for cls in CLASSES}
china_pos_sum = sum(china_pos_ref.values())
belu_acc = {cls: float(series(BELU, cls, act).reindex(axis_months).sum()) for cls in CLASSES}
belu_acc_pos_sum = sum(v for v in belu_acc.values() if v > 0)
china_decl = {cls: max(-float(series(CHINA, cls, act).reindex(axis_months).sum()), 0.0)
              for cls in CLASSES}
china_decl_sum = sum(china_decl.values())

class_mix = {
    "china_pre_decline_composition (positions at reference month 2023-04, share of the "
    "four-class total)": {
        cls: {"position_busd": R3(china_pos_ref[cls]),
              "share": R3(china_pos_ref[cls] / china_pos_sum)}
        for cls in CLASSES},
    "china_active_decline_composition_over_axis (share of gross decline)": {
        cls: {"decline_busd": R3(china_decl[cls]),
              "share_of_gross_decline": R3(china_decl[cls] / china_decl_sum)
              if china_decl_sum else None}
        for cls in CLASSES},
    "belu_accretion_composition_over_axis (net active by class; shares over the "
    "POSITIVE classes only)": {
        cls: {"net_active_busd": R3(belu_acc[cls]),
              "share_of_positive_accretion": R3(belu_acc[cls] / belu_acc_pos_sum)
              if belu_acc[cls] > 0 else None}
        for cls in CLASSES},
    "belu_leg_split (net active over axis, busd)": {
        cls: {"Belgium": R3(float(series(BE, cls, act).reindex(axis_months).sum())),
              "Luxembourg": R3(float(series(LU, cls, act).reindex(axis_months).sum()))}
        for cls in CLASSES},
    "plain_reading": (
        f"China's book at 2023-04 was {100*china_pos_ref['treasury_lt']/china_pos_sum:.1f}% "
        f"Treasury LT and its axis decline was "
        f"{100*china_decl['treasury_lt']/china_decl_sum:.1f}% Treasury LT "
        f"({china_decl['treasury_lt']:.1f} of {china_decl_sum:.1f} $bn gross decline), but "
        f"the BE/LU net active accretion in Treasury LT was only "
        f"{belu_acc['treasury_lt']:.1f} $bn (Belgium "
        f"{float(series(BE,'treasury_lt',act).reindex(axis_months).sum()):.1f}, Luxembourg "
        f"{float(series(LU,'treasury_lt',act).reindex(axis_months).sum()):.1f}) -- the BE/LU "
        f"accretion sits in agency ({belu_acc['agency_lt']:.1f}) and corporate "
        f"({belu_acc['corp_other_bonds_lt']:.1f}) with equity net NEGATIVE "
        f"({belu_acc['equity_lt']:.1f}). That mismatch is what makes capA bite: the class "
        f"where China sold most is the class where BE/LU accreted least."),
}

# ----------------------------------------------------------------------------
# 5. (vi) The mid-2010s Belgium surge (mfhhis01.csv, total UST) -- the template
# ----------------------------------------------------------------------------

def parse_mfhhis01(path):
    """Parse the TIC MFH historical file into {country: {YYYY-MM: busd}}.

    Blocks: a month-name header row immediately precedes each 'Country,YYYY,...' row.
    Some pre-2012 blocks carry 13 columns with a duplicated month at a series break
    (e.g. Jun,Jun in 2011): the LEFTMOST occurrence (the later series) is kept.
    'n.a.' and blanks are skipped. Country names are stripped of footnote markers.
    """
    MON = {m: i + 1 for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
    rows = list(csv.reader(open(path, encoding="utf-8-sig")))
    out = {}
    i = 0
    while i < len(rows):
        row = rows[i]
        if row and row[0].strip() == "Country":
            months_row = rows[i - 1]
            years = [c.strip() for c in row[1:]]
            mons = [c.strip() for c in months_row[1:]]
            cols = []  # (col_index, 'YYYY-MM') keeping leftmost duplicate only
            seen = set()
            for j, (mon, yr) in enumerate(zip(mons, years)):
                if mon in MON and re.fullmatch(r"\d{4}", yr or ""):
                    key = f"{yr}-{MON[mon]:02d}"
                    if key not in seen:
                        seen.add(key)
                        cols.append((j + 1, key))
            i += 1
            while i < len(rows):
                r = rows[i]
                name = (r[0] if r else "").strip()
                if name == "Country":
                    i -= 1
                    break
                if name and not set(name) <= {"-"}:
                    cname = re.sub(r"\s*\d+/\s*$", "", name).strip()
                    for j, key in cols:
                        if j < len(r):
                            v = r[j].strip()
                            if v and v.lower() != "n.a.":
                                try:
                                    out.setdefault(cname, {})[key] = float(v)
                                except ValueError:
                                    pass
                i += 1
        i += 1
    return out


mfh = parse_mfhhis01(P_MFH)
mfh_be = pd.Series(mfh[BE]).sort_index()
mfh_cn = pd.Series(mfh[CHINA]).sort_index()
mfh_lu = pd.Series(mfh[LU]).sort_index()

# Mechanical episode rule (disclosed): search domain = the pre-SLT-positions decade
# 2010-01..2019-12; peak = argmax(Belgium); ramp start = argmin over the 24 months
# before the peak; reversal end = argmin over the 24 months after the peak. The surge
# is declared PRESENT iff ramp rise >= 100 $bn AND reversal fall >= 100 $bn.
dom = mfh_be.loc["2010-01":"2019-12"]
peak_month = dom.idxmax()
pk = pd.Period(peak_month, freq="M")
pre = mfh_be.loc[str(pk - 24):peak_month]
post = mfh_be.loc[peak_month:str(pk + 24)]
ramp_start = pre.idxmin()
reversal_end = post.idxmin()
rise = float(dom[peak_month] - pre[ramp_start])
fall = float(dom[peak_month] - post[reversal_end])
ramp_n = (pk - pd.Period(ramp_start, freq="M")).n
rev_n = (pd.Period(reversal_end, freq="M") - pk).n
surge_present = (rise >= 100.0) and (fall >= 100.0)

# China mirror over the episode (from mfhhis01, as pre-registered)
ep_months = months_range(ramp_start, reversal_end)
be_d = mfh_be.reindex(ep_months).diff().dropna()
cn_d = mfh_cn.reindex(ep_months).diff().dropna()
common = be_d.index.intersection(cn_d.index)
corr_full = float(np.corrcoef(be_d[common], cn_d[common])[0, 1])
ramp_m = months_range(ramp_start, peak_month)
rev_m = months_range(peak_month, reversal_end)
bd_r, cd_r = mfh_be.reindex(ramp_m).diff().dropna(), mfh_cn.reindex(ramp_m).diff().dropna()
bd_v, cd_v = mfh_be.reindex(rev_m).diff().dropna(), mfh_cn.reindex(rev_m).diff().dropna()
corr_ramp = float(np.corrcoef(bd_r, cd_r[bd_r.index])[0, 1])
corr_rev = float(np.corrcoef(bd_v, cd_v[bd_v.index])[0, 1])

# what the by-class ON-DISK record can add: no by-class POSITIONS pre-2020, but the
# committed panel carries by-class ACTIVE flows from 2013-01 (Form S basis)
ep_in_panel = [mm for mm in ep_months if mm >= FULL_START]
be_tre_act = float(series(BE, "treasury_lt", act).reindex(ep_in_panel).sum())
cn_tre_act = float(series(CHINA, "treasury_lt", act).reindex(ep_in_panel).sum())

# current-episode comparison on the SAME total-UST series (mfhhis01 ends before the
# axis end; the overlap is used and stated)
mfh_last = str(mfh_be.index.max())
cur_months_avail = [mm for mm in months_range(AXIS_REF, AXIS_END) if mm in mfh_be.index]
cur_first, cur_last = cur_months_avail[0], cur_months_avail[-1]
cur_n = (pd.Period(cur_last, freq="M") - pd.Period(cur_first, freq="M")).n
be_cur = float(mfh_be[cur_last] - mfh_be[cur_first])
lu_cur = float(mfh_lu[cur_last] - mfh_lu[cur_first])
cn_cur = float(mfh_cn[cur_last] - mfh_cn[cur_first])

belgium_surge = {
    "present": bool(surge_present),
    "source": "build/reserve/rdt_evidence/tic/mfhhis01.csv (TIC MFH historical, total "
              "UST holdings incl. bills, monthly, from 2000)",
    "episode_detection_rule (mechanical, disclosed)": (
        "search domain 2010-01..2019-12; peak = argmax(Belgium); ramp start = argmin over "
        "the 24 months before the peak; reversal end = argmin over the 24 months after the "
        "peak; PRESENT iff rise >= 100 $bn and fall >= 100 $bn (disclosed thresholds)"),
    "ramp": {"start_month": ramp_start, "start_level_busd": R3(mfh_be[ramp_start]),
             "peak_month": peak_month, "peak_level_busd": R3(mfh_be[peak_month]),
             "rise_busd": R3(rise), "months": ramp_n,
             "ramp_rate_busd_per_month": R3(rise / ramp_n)},
    "reversal": {"trough_month": reversal_end,
                 "trough_level_busd": R3(mfh_be[reversal_end]),
                 "fall_busd": R3(fall), "months": rev_n,
                 "reversal_rate_busd_per_month": R3(-fall / rev_n)},
    "china_mirror (from mfhhis01, pre-registered)": {
        "china_delta_over_ramp_busd": R3(mfh_cn[peak_month] - mfh_cn[ramp_start]),
        "china_delta_over_reversal_busd": R3(mfh_cn[reversal_end] - mfh_cn[peak_month]),
        "monthly_diff_correlation_full_episode": R3(corr_full),
        "monthly_diff_correlation_ramp": R3(corr_ramp),
        "monthly_diff_correlation_reversal": R3(corr_rev),
        "reading": ("computed, not asserted: a NEGATIVE diff-correlation is the mirror "
                    "signature (China down in the months Belgium is up); a POSITIVE one is "
                    "co-movement, not mirroring"),
    },
    "class_signature_extent": (
        "Pre-2020 there is NO by-class POSITION record on disk -- the positions tables "
        "begin 2020-01, so the episode's position signature is total-UST timing/magnitude "
        "only (this series includes T-bills). The committed panel DOES carry by-class "
        "ACTIVE flows from 2013-01 (Form S basis): over the episode months on the panel "
        f"({ep_in_panel[0]}..{ep_in_panel[-1]}), Belgium treasury_lt cumulative active = "
        f"{be_tre_act:.1f} $bn and China treasury_lt cumulative active = {cn_tre_act:.1f} "
        "$bn -- reported as the only class-level trace the on-disk record carries; nothing "
        "is imported from memory or literature."),
    "luxembourg_over_episode_busd": R3(mfh_lu[reversal_end] - mfh_lu[ramp_start]),
    "template_vs_current_on_same_series (total UST, mfhhis01; the historical file ends "
    f"{mfh_last}, so the current leg is {cur_first}..{cur_last}, {cur_n} months of the "
    "36-month axis -- overlap stated, not extrapolated)": {
        "template_ramp_rate_busd_per_month": R3(rise / ramp_n),
        "current_belgium_delta_busd": R3(be_cur),
        "current_belgium_rate_busd_per_month": R3(be_cur / cur_n),
        "current_luxembourg_delta_busd": R3(lu_cur),
        "current_luxembourg_rate_busd_per_month": R3(lu_cur / cur_n),
        "current_china_delta_busd": R3(cn_cur),
    },
}

# ----------------------------------------------------------------------------
# 6. Reconciliation to the committed RDT-C/D ledgers (targets READ from the
#    committed JSONs at run time -- never typed in)
# ----------------------------------------------------------------------------

led_axis = flows["ledgers"]["recent_3y_verdict_axis"]
tgt_china_resid = float(led_axis["china_alone"]["residual_left_us_busd"])          # 446.493
tgt_cbl_resid = float(led_axis["china_belgium_luxembourg"]["residual_left_us_busd"])  # 326.323
tgt_rdtd_china = float(rdtd["identity"]["china_alone"]["active_outflow_busd"])
tgt_rdtd_cbl = float(rdtd["identity"]["china_belgium_luxembourg"]["active_outflow_busd"])

my_china_total = float(sum(series(CHINA, c, act).reindex(axis_months).sum() for c in CLASSES))
my_cbl_total = my_china_total + float(sum(series(BELU, c, act).reindex(axis_months).sum()
                                          for c in CLASSES))

diffs = {}
diffs["china_axis_active_total_vs_RDTC_residual"] = {
    "computed_busd": R3(my_china_total), "target_busd": R3(-tgt_china_resid),
    "diff_busd": R3(my_china_total + tgt_china_resid)}
diffs["china_axis_active_total_vs_RDTD"] = {
    "computed_busd": R3(my_china_total), "target_busd": R3(-tgt_rdtd_china),
    "diff_busd": R3(my_china_total + tgt_rdtd_china)}
diffs["cn_be_lu_axis_active_total_vs_RDTC_residual"] = {
    "computed_busd": R3(my_cbl_total), "target_busd": R3(-tgt_cbl_resid),
    "diff_busd": R3(my_cbl_total + tgt_cbl_resid)}
diffs["cn_be_lu_axis_active_total_vs_RDTD"] = {
    "computed_busd": R3(my_cbl_total), "target_busd": R3(-tgt_rdtd_cbl),
    "diff_busd": R3(my_cbl_total + tgt_rdtd_cbl)}

# per-class: China vs RDTC china_alone; BELU vs (combined - china) per class
perclass_diffs = {}
maxd = 0.0
for cls in CLASSES:
    t_ch = float(led_axis["china_alone"]["per_class"][cls]["active_cum_busd"])
    t_cbl = float(led_axis["china_belgium_luxembourg"]["per_class"][cls]["active_cum_busd"])
    c_ch = float(series(CHINA, cls, act).reindex(axis_months).sum())
    c_bl = float(series(BELU, cls, act).reindex(axis_months).sum())
    d1 = c_ch - t_ch
    d2 = c_bl - (t_cbl - t_ch)
    maxd = max(maxd, abs(d1), abs(d2))
    perclass_diffs[cls] = {"china_diff_busd": R3(d1),
                           "belu_vs_combined_minus_china_diff_busd": R3(d2)}

# holdings deltas vs RDTD_fragility (reference-month convention)
hold_diffs = {}
maxh = 0.0
for cls in CLASSES:
    t_ch = float(frag["G_tables"]["recent_3y_verdict_axis"]["china_alone"][cls][
        "delta_holdings_busd"])
    t_cbl = float(frag["G_tables"]["recent_3y_verdict_axis"]["china_belgium_luxembourg"][cls][
        "delta_holdings_busd"])
    pch = series(CHINA, cls, pos)
    pbl = series(BELU, cls, pos)
    d1 = float(pch.loc[AXIS_END] - pch.loc[AXIS_REF]) - t_ch
    d2 = float((pch + pbl).loc[AXIS_END] - (pch + pbl).loc[AXIS_REF]) - t_cbl
    maxh = max(maxh, abs(d1), abs(d2))
    hold_diffs[cls] = {"china_dH_diff_busd": R3(d1), "cn_be_lu_dH_diff_busd": R3(d2)}

# internal consistency: total_lt vs sum of the four classes
piv_a = panel.pivot_table(index=["country", "month"], columns="asset_class",
                          values="active_musd")
gap_active_musd = float((piv_a[CLASSES].sum(axis=1) - piv_a["total_lt"]).abs().max())
piv_p = panel.pivot_table(index=["country", "month"], columns="asset_class",
                          values="pos_musd")
gap_pos_musd = float((piv_p[CLASSES].sum(axis=1) - piv_p["total_lt"]).abs().max())

reconciliation = {
    "targets_read_from": [P_FLOWS.replace(ROOT + "/", ""), P_RDTD.replace(ROOT + "/", ""),
                          P_FRAG.replace(ROOT + "/", "")],
    "axis_totals": diffs,
    "per_class_active_diffs": perclass_diffs,
    "max_abs_per_class_active_diff_busd": R3(maxd),
    "holdings_delta_diffs_vs_RDTD_fragility": hold_diffs,
    "max_abs_holdings_diff_busd": R3(maxh),
    "panel_internal": {
        "max_abs_gap_sum_of_classes_vs_total_lt_active_musd": R3(gap_active_musd),
        "max_abs_gap_sum_of_classes_vs_total_lt_pos_musd": R3(gap_pos_musd),
        "note": "position gap of up to 1 musd (0.001 busd) is publisher rounding of the "
                "class rows vs the total row; caps are computed on the class rows",
    },
}

# ----------------------------------------------------------------------------
# 7. Detail parquet
# ----------------------------------------------------------------------------

rows = []
for country in [CHINA, BE, LU, BELU]:
    for cls in ALL_CLASSES:
        a = series(country, cls, act)
        p = series(country, cls, pos)
        dp = p.diff()
        for mth in a.index:
            rows.append({
                "country": country, "month": mth, "asset_class": cls,
                "source_series": "RDTC_class_panel",
                "pos_busd": float(p.get(mth, np.nan)),
                "d_pos_busd": float(dp.get(mth, np.nan)),
                "active_busd": float(a.get(mth, np.nan)),
                "in_verdict_axis": AXIS_START <= mth <= AXIS_END,
            })
for country, s in [(CHINA, mfh_cn), (BE, mfh_be), (LU, mfh_lu)]:
    d = s.diff()
    for mth in s.index:
        rows.append({
            "country": country, "month": mth, "asset_class": "total_ust_mfh",
            "source_series": "mfhhis01_total_ust_incl_bills",
            "pos_busd": float(s[mth]), "d_pos_busd": float(d[mth]),
            "active_busd": np.nan,
            "in_verdict_axis": AXIS_START <= mth <= AXIS_END,
        })
detail = pd.DataFrame(rows).sort_values(
    ["source_series", "country", "asset_class", "month"]).reset_index(drop=True)
detail.to_parquet(OUT_PARQUET, index=False)

# ----------------------------------------------------------------------------
# 8. Self-check flags and the artifact
# ----------------------------------------------------------------------------

checks = {
    "panel_schema_verified": True,
    "no_nan_active_inside_axis": True,
    "china_axis_total_reconciles_exactly": abs(my_china_total + tgt_china_resid) < 5e-4,
    "cn_be_lu_axis_total_reconciles_exactly": abs(my_cbl_total + tgt_cbl_resid) < 5e-4,
    "per_class_active_reconciles": maxd < 5e-4,
    "holdings_deltas_reconcile": maxh < 5e-4,
    "capB_pm3_geq_contemporaneous_every_class": all(
        capB_rows[c]["pm3_busd (THE CAP)"] >= capB_rows[c]["contemporaneous_busd (context)"]
        for c in CLASSES),
    "capA_classes_capping_out_have_zero": all(
        capA_rows[c]["capA_class_busd"] == 0.0
        for c in CLASSES
        if capA_rows[c]["china_decline_room_busd"] == 0.0
        or capA_rows[c]["belu_accretion_room_busd"] == 0.0),
    "floor_mass_leq_capB_contemporaneous": floor_mass_primary <= capB_contemp_total + 1e-9,
    "belgium_surge_thresholds_met": bool(surge_present),
    "blind_spots_extracted_verbatim_from_prediction": True,
}
checks["all_pass"] = all(checks.values())

artifact = {
    "artifact": "RDTE_ingredients (RDT-E Part 1(i)-(iii)+(vi): on-disk ingredients for "
                "the migration bound -- levels/diffs, capA, capB + candidate floor, "
                "class-mix, the mid-2010s Belgium-surge template, reconciliation)",
    "establishment": "NOT ESTABLISHED -- output of RDTE_ingredients_recompute.py; every "
        "number below is an OUTPUT pending its verifier scenario (orchestrator re-run of "
        "build/reserve/RDTE_ingredients_recompute.py reproducing this file and the detail "
        "parquet deterministically, and the RDT-E human gate). No cap value here is a "
        "migration finding; caps bound, they do not establish.",
    "contract": "build/reserve/RDTE_prediction.md (pre-registered before this build; "
                "windows, classes, cap constructions, blind spots and the flipped guard "
                "are fixed there and applied exactly)",
    "no_date_no_probability": "no breaking-point date and no probability appear in this "
                              "artifact; historical episode months are data description",
    "flipped_guard (carried from the pre-registration)": {
        "DRAMATIZE": "windows and classes are the pre-registered ones (verdict axis "
                     "2023-05..2026-04; SLT classes); nothing was selected post hoc to "
                     "shrink M_hi",
        "ZERO": "capA/capB count class- and month-matched ROOM; nothing here asserts the "
                "BE/LU accretion IS China's -- the custody-masking direction is carried, "
                "not resolved",
    },
    "inputs_sha256": {
        os.path.relpath(p, ROOT): sha256(p)
        for p in [P_PANEL, P_FLOWS, P_RDTD, P_FRAG, P_MFH, P_PRED]},
    "units": "all *_busd fields are billions of USD, 3 decimals; panel native unit is "
             "millions (musd)",
    "windows": {
        "verdict_axis": {"start": AXIS_START, "end": AXIS_END,
                         "holdings_reference_month": AXIS_REF,
                         "role": "VERDICT AXIS (RDT-B recent-3y window verbatim)"},
        "full_window": {"active_from": FULL_START, "positions_from": "2020-01",
                        "end": AXIS_END, "role": "context (from each series' start)"},
    },
    "panel_schema_verified": schema_checks,
    "series_summaries": series_summaries,
    "cap_A_class_matched_accretion": cap_A,
    "cap_B_synchronized_mirror_timing": cap_B,
    "class_mix": class_mix,
    "belgium_surge_template_mid2010s": belgium_surge,
    "reconciliation": reconciliation,
    "detail_parquet": os.path.relpath(OUT_PARQUET, ROOT),
    "self_check": checks,
}

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(artifact, f, indent=1, ensure_ascii=False)
    f.write("\n")

print("wrote", OUT_JSON)
print("wrote", OUT_PARQUET)
print("self_check all_pass:", checks["all_pass"])
if not checks["all_pass"]:
    print({k: v for k, v in checks.items() if not v})
    sys.exit(1)
