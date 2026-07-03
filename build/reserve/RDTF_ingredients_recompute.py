#!/usr/bin/env python3
"""RDT-F Phase 1 -- INGREDIENT TABLES ONLY (no branch verdict, no M_hi_global).

Deterministic recompute. Regenerates byte-for-byte:
  build/reserve/RDTF_ingredients.json
  build/reserve/RDTF_ingredients_panel.parquet

Contract: build/reserve/RDTF_prediction.md (pre-registered; the two ceiling
constructions, the windows, and the basis-reconciliation method are fixed there
and implemented exactly).

TABLE A: per-candidate-center ceilings, BOTH constructions (gross and window-net),
computed mechanically for EVERY country line in the TIC SLT Table 1 by-country
by-class file (no pre-filtering; the grounded center set is derived elsewhere and
Phase-2 assembly filters this superset).
TABLE B: leave-one-center-out needs only the exact per-center totals (subtraction);
they are emitted at full precision.
TABLE C: basis-reconciliation STAGING numbers only -- FRBNY H.4.1 custody leg,
TIC official legs (MFH-basis and SLT LT-official row with the stated valuation-
change column), raw and basis-adjusted divergences. NO verdict is rendered here.

Everything computed from on-disk inputs. The only literals are the pre-registered
window endpoints; every reproduction target (RDT-E capA figures, the 446.493 cap
constant, the committed -232.223 / +116.8 changes) is READ from the committed
artifacts at run time, never typed in. No network. No date, no probability.
"""

import hashlib
import json
import os
import re
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- inputs (all read-only) -------------------------------------------------
# NOTE (path finding): the tasking named build/reserve/rdt_evidence/tic/slt_table1.txt;
# that path does NOT exist on disk. The actual on-disk copy of the TIC SLT Table 1
# by-country by-class file is the one below (verified; also the very file the
# committed RDTC_class_panel.parquet names in its pos_source/tx_source columns).
P_SLT1 = os.path.join(ROOT, "build/data/treasury_tic/current/slt_tables/slt_table1.txt")
P_RDTC_PANEL = os.path.join(ROOT, "build/reserve/RDTC_class_panel.parquet")
P_OFFICIAL = os.path.join(ROOT, "build/reserve/rdte_official_series.csv")
P_SLT2D = os.path.join(ROOT, "build/data/treasury_tic/current/slt2d.txt")
P_SLT1D = os.path.join(ROOT, "build/data/treasury_tic/current/slt1d.txt")
P_RDTC_FLOWS = os.path.join(ROOT, "build/reserve/RDTC_class_flows.json")
P_RDTE_ING = os.path.join(ROOT, "build/reserve/RDTE_ingredients.json")
P_RDTE_RES = os.path.join(ROOT, "build/reserve/RDTE_result.json")
P_PRED = os.path.join(ROOT, "build/reserve/RDTF_prediction.md")

OUT_JSON = os.path.join(ROOT, "build/reserve/RDTF_ingredients.json")
OUT_PARQUET = os.path.join(ROOT, "build/reserve/RDTF_ingredients_panel.parquet")

# Pre-registered windows (RDTF_prediction.md / RDTE lineage; the ONLY literals).
AXIS_START, AXIS_END = "2023-05", "2026-04"
AXIS_REF = "2023-04"  # holdings/levels reference month (committed RDT-D/E convention)

CHINA = "China, Mainland"
KNOWN_CANDIDATES = ["Belgium", "Luxembourg", "Switzerland", "United Kingdom"]
CLASSES = ["treasury_lt", "agency_lt", "corp_other_bonds_lt", "equity_lt"]
# slt_table1 column stems, in file order, mapped to the RDTC/RDTE class names
STEM2CLASS = [("tre", "treasury_lt"), ("agc", "agency_lt"),
              ("cor", "corp_other_bonds_lt"), ("eqt", "equity_lt"),
              ("tot", "total_lt")]

TOL = 5e-4  # reproduction tolerance vs committed 3-decimal busd figures


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def months_range(a, b):
    return [str(p) for p in pd.period_range(a, b, freq="M")]


def busd(x_musd):
    """Exact musd -> busd (source values are integer millions; 3 decimals exact)."""
    if x_musd is None or (isinstance(x_musd, float) and np.isnan(x_musd)):
        return None
    return round(float(x_musd) / 1000.0, 6)


# ----------------------------------------------------------------------------
# 0. Parse slt_table1.txt -- the schema is a FINDING, read from the real file
# ----------------------------------------------------------------------------
raw_lines = open(P_SLT1, encoding="utf-8").read().splitlines()
COLS = ["country", "code", "month",
        "tot_pos", "tot_net", "tot_val",
        "tre_pos", "tre_net", "tre_val",
        "agc_pos", "agc_net", "agc_val",
        "cor_pos", "cor_net", "cor_val",
        "eqt_pos", "eqt_net", "eqt_val"]
date_re = re.compile(r"^\d{4}-\d{2}$")
rows, nondata = [], []
for ln in raw_lines:
    f = [x.strip() for x in ln.split("\t")]
    if len(f) >= 18 and date_re.match(f[2]):
        rows.append(f[:18])
    else:
        nondata.append(f[0])
df = pd.DataFrame(rows, columns=COLS)
for c in COLS[3:]:
    df[c] = pd.to_numeric(df[c].replace({"n.a.": None, "": None}))
df = df.sort_values(["country", "code", "month"]).reset_index(drop=True)

# schema finding: quote the real structure (verbatim header lines from the file)
hdr_title = raw_lines[0].split("\t")[0].strip()
hdr_scope = raw_lines[1].split("\t")[0].strip()
hdr_sign = raw_lines[2].split("\t")[0].strip()
hdr_units = raw_lines[3].split("\t")[0].strip()
hdr_link = raw_lines[4].split("\t")[0].strip()
class_header = [x.strip() for x in raw_lines[6].split("\t")]
col_header = [x.strip() for x in raw_lines[7].split("\t")]
mnemo_header = [x.strip() for x in raw_lines[8].split("\t")]
assert hdr_title.startswith("Table 1: U.S. Long-Term Securities Held by Foreign Residents"), \
    "slt_table1 title drift -- schema finding template would be wrong; failing loudly"
assert hdr_units == "Millions of dollars", "slt_table1 units drift"
assert col_header[:3] == ["Country", "Country Code", "Date"], "slt_table1 header drift"
assert mnemo_header[3:6] == ["for_lt_total_pos", "for_lt_total_net", "for_lt_total_valchg"], \
    "slt_table1 mnemonic-row drift"

n_lines = df.groupby(["country", "code"]).ngroups
pos_first = df.dropna(subset=["tre_pos"])["month"].min()
pos_last = df.dropna(subset=["tre_pos"])["month"].max()
net_nonnull = df.dropna(subset=["tre_net"])
net_first, net_last = net_nonnull["month"].min(), net_nonnull["month"].max()
month_min, month_max = df["month"].min(), df["month"].max()

# every net-bearing line covers the identical span (verify, then state)
cov = net_nonnull.groupby("country")["month"].agg(["min", "max", "count"])
assert (cov["min"] == net_first).all() and (cov["max"] == net_last).all(), \
    "net coverage differs across lines -- staging text below would be wrong"
assert net_first == "2023-02", (
    "by-country active (Net U.S. Sales) basis no longer starts 2023-02 -- the "
    "pre-registered claim that the verdict axis lies fully on it must be re-verified")
assert AXIS_START >= net_first and AXIS_END <= net_last, "verdict axis off the active basis"
assert month_min == "2020-01", "positions no longer start 2020-01 -- schema finding drift"

axis_months = months_range(AXIS_START, AXIS_END)
full_months = months_range(net_first, net_last)  # full window on the ACTIVE basis

schema_finding = {
    "file_used": os.path.relpath(P_SLT1, ROOT),
    "path_finding": ("the tasking named build/reserve/rdt_evidence/tic/slt_table1.txt; "
                     "that path does not exist on disk -- the on-disk copy of the TIC "
                     "SLT Table 1 file is " + os.path.relpath(P_SLT1, ROOT) + ", the same "
                     "file the committed RDTC_class_panel.parquet names in its "
                     "pos_source/tx_source columns ('slt_table1.txt')"),
    "title_line_verbatim": hdr_title,
    "scope_line_verbatim": hdr_scope,
    "sign_convention_verbatim": hdr_sign,
    "units_line_verbatim": hdr_units,
    "link_line_verbatim": hdr_link,
    "layout": ("tab-separated; one row per (country line, month); columns: Country, "
               "Country Code, Date, then 5 blocks x 3 columns -- [Total U.S. Securities, "
               "U.S. Treasuries, U.S. Agency Bonds, U.S. Corp. & Other Bonds, U.S. Corp. "
               "Equity] x [Holdings, Net U.S. Sales, Valuation Change]; missing values "
               "are the literal string 'n.a.'"),
    "class_header_row_verbatim": [c for c in class_header if c],
    "column_header_row_verbatim": col_header,
    "mnemonic_row_verbatim": mnemo_header,
    "country_line_naming": ("plain-English country names with numeric country codes "
                            "(e.g. 'Belgium'/10251, 'China, Mainland'/41408, "
                            "'Switzerland'/12688, 'United Kingdom'/13005); aggregate "
                            "lines 'All Countries'/69995 and 'Grand Total'/99996; "
                            "regional 'Total ...' lines; 'Memo: Euro Area'/'Memo: "
                            "European Union'; sector/official splits as 'Of Which: ...' "
                            "lines (e.g. 'Of Which: Foreign Official'/99990)"),
    "n_country_lines": int(n_lines),
    "n_data_rows": int(len(df)),
    "month_span_all_rows": [month_min, month_max],
    "positions_span": [str(pos_first), str(pos_last)],
    "transactions_valchg_span": [str(net_first), str(net_last)],
    "verified_axis_on_active_basis": (
        "VERIFIED from the file: by-country Net U.S. Sales and Valuation Change are "
        "non-'n.a.' from 2023-02 through " + str(net_last) + " on every net-bearing "
        "line, so the verdict axis 2023-05..2026-04 lies fully on the by-country "
        "active basis"),
    "lines_with_no_transactions_data": sorted(
        set(df["country"]) - set(net_nonnull["country"])),
    "SOURCE": os.path.relpath(P_SLT1, ROOT),
}


def line_type(name, code):
    if name in ("All Countries", "Grand Total"):
        return "aggregate_total"
    if name.startswith("Total "):
        return "regional_aggregate"
    if name.startswith("Memo:"):
        return "memo_aggregate"
    if name.startswith("Of Which:"):
        return "of_which_split"
    if name == "International":
        return "international_orgs_line"
    return "country"


# ----------------------------------------------------------------------------
# 1. TABLE A -- both ceiling constructions, EVERY line, both windows
# ----------------------------------------------------------------------------
def window_frame(months):
    return df[df["month"].isin(months)]


def china_rooms(months):
    """Per class: gross decline room and |net| decline room (busd), from monthly actives."""
    cn = window_frame(months)
    cn = cn[cn["country"] == CHINA]
    out = {}
    for stem, cls in STEM2CLASS:
        if cls == "total_lt":
            continue
        s = cn[stem + "_net"].dropna()
        assert len(s) == len(months), "China active series incomplete inside window"
        gross_decline = float((-s).clip(lower=0).sum())          # musd
        net_sum = float(s.sum())                                  # musd
        out[cls] = {
            "china_active_window_sum_busd": busd(net_sum),
            "china_gross_decline_busd": busd(gross_decline),
            "china_net_decline_room_busd": busd(max(-net_sum, 0.0)),
        }
        assert gross_decline >= max(-net_sum, 0.0) - 1e-9, \
            "sanity (ii) violated: gross decline < net decline room"
    return out


def center_table(months, rooms):
    """Per line: per-class gross inflow / window-net, min() vs China rooms, totals."""
    win = window_frame(months)
    result = {}
    for (name, code), g in win.groupby(["country", "code"]):
        if name == CHINA:
            pass  # China is also emitted (its own line: inflow room vs itself; kept for completeness)
        per_class = {}
        m_gross = 0.0
        m_net = 0.0
        n_cov = None
        any_data = False
        for stem, cls in STEM2CLASS:
            if cls == "total_lt":
                continue
            s = g[stem + "_net"].dropna()
            n_cov = int(len(s)) if n_cov is None else n_cov
            if len(s) == 0:
                per_class[cls] = {
                    "center_gross_inflow_busd": None,
                    "gross_min_vs_china_busd": None,
                    "center_active_window_sum_busd": None,
                    "windownet_min_vs_china_busd": None,
                }
                continue
            assert len(s) == len(months), (
                "partial active coverage inside window for line %r -- the mechanical "
                "sum would silently understate; failing loudly" % name)
            any_data = True
            gross_in = float(s.clip(lower=0).sum())               # musd
            net_sum = float(s.sum())                              # musd
            g_room = rooms[cls]["china_gross_decline_busd"] * 1000.0
            n_room = rooms[cls]["china_net_decline_room_busd"] * 1000.0
            g_min = min(g_room, gross_in)
            n_min = min(n_room, max(net_sum, 0.0))
            m_gross += g_min
            m_net += n_min
            per_class[cls] = {
                "center_gross_inflow_busd": busd(gross_in),
                "gross_min_vs_china_busd": busd(g_min),
                "center_active_window_sum_busd": busd(net_sum),
                "windownet_min_vs_china_busd": busd(n_min),
            }
        result[name] = {
            "country_code": str(code),
            "line_type": line_type(name, code),
            "is_known_candidate": name in KNOWN_CANDIDATES,
            "is_china_line": name == CHINA,
            "n_active_months_in_window": 0 if not any_data else int(len(months)),
            "per_class": per_class,
            "M_center_gross_busd": busd(m_gross) if any_data else None,
            "M_center_windownet_busd": busd(m_net) if any_data else None,
        }
        if any_data:
            assert m_gross >= m_net - 1e-9, \
                "sanity (iii) violated: gross < net for line %r" % name
    return result


rooms_axis = china_rooms(axis_months)
rooms_full = china_rooms(full_months)
tableA_axis = center_table(axis_months, rooms_axis)
tableA_full = center_table(full_months, rooms_full)

# pooled BE+LU (RDT-E's counterparty pooling), both windows
def pooled_belu(months, rooms):
    win = window_frame(months)
    be = win[win["country"] == "Belgium"].set_index("month")
    lu = win[win["country"] == "Luxembourg"].set_index("month")
    per_class = {}
    m_gross = 0.0
    m_net = 0.0
    for stem, cls in STEM2CLASS:
        if cls == "total_lt":
            continue
        s = (be[stem + "_net"] + lu[stem + "_net"]).dropna()
        assert len(s) == len(months), "BE+LU pooled series incomplete inside window"
        gross_in = float(s.clip(lower=0).sum())
        net_sum = float(s.sum())
        g_min = min(rooms[cls]["china_gross_decline_busd"] * 1000.0, gross_in)
        n_min = min(rooms[cls]["china_net_decline_room_busd"] * 1000.0,
                    max(net_sum, 0.0))
        m_gross += g_min
        m_net += n_min
        per_class[cls] = {
            "pooled_gross_inflow_busd": busd(gross_in),
            "gross_min_vs_china_busd": busd(g_min),
            "pooled_active_window_sum_busd": busd(net_sum),
            "windownet_min_vs_china_busd": busd(n_min),
        }
    return {"per_class": per_class,
            "M_pooled_gross_busd": busd(m_gross),
            "M_pooled_windownet_busd": busd(m_net)}


belu_axis = pooled_belu(axis_months, rooms_axis)
belu_full = pooled_belu(full_months, rooms_full)

# ----------------------------------------------------------------------------
# 2. Reproduction target: RDT-E capA (read from the committed artifact)
# ----------------------------------------------------------------------------
rdte_ing = json.load(open(P_RDTE_ING, encoding="utf-8"))
rdte_capA = rdte_ing["cap_A_class_matched_accretion"]
rdte_capA_per_class = {
    cls: float(rdte_capA["per_class"][cls]["capA_class_busd"]) for cls in CLASSES}
rdte_capA_total = float(rdte_capA["capA_total_busd"])
rdte_belu_net = {
    cls: float(rdte_capA["per_class"][cls]["belu_active_window_sum_busd"])
    for cls in CLASSES}
rdte_china_net = {
    cls: float(rdte_capA["per_class"][cls]["china_active_window_sum_busd"])
    for cls in CLASSES}

repro_rows = {}
for cls in CLASSES:
    mine = belu_axis["per_class"][cls]["windownet_min_vs_china_busd"]
    tgt = rdte_capA_per_class[cls]
    repro_rows[cls] = {
        "computed_pooled_windownet_min_busd": mine,
        "rdte_committed_capA_class_busd": tgt,
        "diff_busd": round(mine - tgt, 6),
        "computed_pooled_active_sum_busd": belu_axis["per_class"][cls]["pooled_active_window_sum_busd"],
        "rdte_committed_belu_active_sum_busd": rdte_belu_net[cls],
        "computed_china_active_sum_busd": rooms_axis[cls]["china_active_window_sum_busd"],
        "rdte_committed_china_active_sum_busd": rdte_china_net[cls],
    }
    assert abs(mine - tgt) < TOL, "RDT-E capA per-class reproduction FAILED for " + cls
    assert abs(belu_axis["per_class"][cls]["pooled_active_window_sum_busd"]
               - rdte_belu_net[cls]) < TOL, "BE+LU pooled net reproduction FAILED for " + cls
    assert abs(rooms_axis[cls]["china_active_window_sum_busd"]
               - rdte_china_net[cls]) < TOL, "China net reproduction FAILED for " + cls
repro_total_diff = round(belu_axis["M_pooled_windownet_busd"] - rdte_capA_total, 6)
assert abs(repro_total_diff) < TOL, "RDT-E capA TOTAL reproduction FAILED"

be_net = tableA_axis["Belgium"]["M_center_windownet_busd"]
lu_net = tableA_axis["Luxembourg"]["M_center_windownet_busd"]
sum_sep = round(be_net + lu_net, 6)
pooled = belu_axis["M_pooled_windownet_busd"]
assert sum_sep >= pooled - 1e-9, "convexity of min violated: sum-of-separates < pooled"
pooling_note = (
    "RDT-E pooled BE+LU as ONE counterparty. Pooled window-net total {p} busd "
    "reproduces RDT-E's committed capA total {t} busd exactly. The separate "
    "per-center window-net figures are Belgium {b} + Luxembourg {l} = {s} busd; "
    "sum-of-separates >= pooled holds ({s} >= {p}), as expected from convexity of "
    "min(): netting BE's negative class sums against LU's positive ones before the "
    "min() is what shrinks the pooled figure.").format(
        p=pooled, t=rdte_capA_total, b=be_net, l=lu_net, s=sum_sep)

# sanity (ii) recorded per class, both windows
sanity_ii = {}
for wname, rooms in [("verdict_axis", rooms_axis), ("full_window", rooms_full)]:
    sanity_ii[wname] = {
        cls: {
            "china_gross_decline_busd": rooms[cls]["china_gross_decline_busd"],
            "china_net_decline_room_busd": rooms[cls]["china_net_decline_room_busd"],
            "gross_geq_net": rooms[cls]["china_gross_decline_busd"]
                             >= rooms[cls]["china_net_decline_room_busd"] - 1e-9,
        } for cls in CLASSES}
    assert all(v["gross_geq_net"] for v in sanity_ii[wname].values())

# sanity (iii) recorded: gross >= net for every line with data, both windows
def sanity_iii(table):
    worst = None
    for name, rec in table.items():
        if rec["M_center_gross_busd"] is None:
            continue
        gap = rec["M_center_gross_busd"] - rec["M_center_windownet_busd"]
        if worst is None or gap < worst[1]:
            worst = (name, round(gap, 6))
    return {"holds_for_every_line_with_data": True,
            "smallest_gross_minus_net_busd": worst[1],
            "smallest_gap_line": worst[0]}


sanity_iii_axis = sanity_iii(tableA_axis)
sanity_iii_full = sanity_iii(tableA_full)

# ----------------------------------------------------------------------------
# 3. Staging sum over the KNOWN candidate set (labelled staging) + cap constant
# ----------------------------------------------------------------------------
staging_gross = round(sum(tableA_axis[c]["M_center_gross_busd"]
                          for c in KNOWN_CANDIDATES), 6)
staging_net = round(sum(tableA_axis[c]["M_center_windownet_busd"]
                        for c in KNOWN_CANDIDATES), 6)

rdtc_flows = json.load(open(P_RDTC_FLOWS, encoding="utf-8"))
cap_from_rdtc = float(
    rdtc_flows["ledgers"]["recent_3y_verdict_axis"]["china_alone"]["residual_left_us_busd"])
rdte_res = json.load(open(P_RDTE_RES, encoding="utf-8"))
cap_from_rdte = float(
    rdte_res["mechanical_verdict"]["active_decline_busd (read from RDTD_result.json)"])
assert abs(cap_from_rdtc - cap_from_rdte) < 1e-9, "cap constant differs across committed artifacts"
# the cap constant is also China's axis |net| total recomputed here from slt_table1:
china_axis_total = round(sum(rooms_axis[cls]["china_active_window_sum_busd"]
                             for cls in CLASSES), 6)
assert abs(-china_axis_total - cap_from_rdtc) < TOL, \
    "recomputed China axis active total does not match the committed cap constant"

cap_constant = {
    "value_busd": cap_from_rdtc,
    "read_from": {
        "primary": {
            "file": os.path.relpath(P_RDTC_FLOWS, ROOT),
            "field": "ledgers.recent_3y_verdict_axis.china_alone.residual_left_us_busd"},
        "cross_read": {
            "file": os.path.relpath(P_RDTE_RES, ROOT),
            "field": "mechanical_verdict.'active_decline_busd (read from RDTD_result.json)'"},
    },
    "recomputed_here_busd": round(-china_axis_total, 6),
    "recompute_matches": True,
    "role": ("Phase-2 assembly constant: M_hi_global = min(Sum_grounded-centers "
             "M_center(gross), this value) -- NOT applied here; no M_hi_global is "
             "computed in this artifact"),
    "SOURCE": os.path.relpath(P_RDTC_FLOWS, ROOT) + "; " + os.path.relpath(P_RDTE_RES, ROOT),
}

# ----------------------------------------------------------------------------
# 4. Cross-check: RDTC committed panel vs this re-derivation (CN/BE/LU)
# ----------------------------------------------------------------------------
rdtc_panel = pd.read_parquet(P_RDTC_PANEL)
mine_long = []
for (name, code), g in df[df["country"].isin([CHINA, "Belgium", "Luxembourg"])].groupby(
        ["country", "code"]):
    for stem, cls in STEM2CLASS:
        sub = g[["month", stem + "_pos", stem + "_net", stem + "_val"]].copy()
        sub.columns = ["month", "pos_musd", "active_musd", "valchg_musd"]
        sub["country"] = name
        sub["asset_class"] = cls
        mine_long.append(sub)
mine_long = pd.concat(mine_long, ignore_index=True)

merged = rdtc_panel.merge(mine_long, on=["country", "month", "asset_class"],
                          how="inner", suffixes=("_rdtc", "_slt1"))
xchk = {}
for field in ["pos_musd", "active_musd", "valchg_musd"]:
    both = merged.dropna(subset=[field + "_rdtc", field + "_slt1"])
    d = (both[field + "_rdtc"] - both[field + "_slt1"]).abs()
    mism = both[d > 0.5]
    xchk[field] = {
        "n_overlapping_obs_compared": int(len(both)),
        "max_abs_diff_musd": float(d.max()) if len(both) else None,
        "n_mismatches_beyond_rounding_0p5musd": int(len(mism)),
        "mismatches": [
            {"country": r["country"], "month": r["month"], "asset_class": r["asset_class"],
             "rdtc_musd": float(r[field + "_rdtc"]), "slt1_musd": float(r[field + "_slt1"])}
            for _, r in mism.iterrows()],
    }
    # coverage difference (an expected structural fact, recorded not smoothed):
    only_rdtc = merged[merged[field + "_rdtc"].notna() & merged[field + "_slt1"].isna()]
    only_mine = merged[merged[field + "_slt1"].notna() & merged[field + "_rdtc"].isna()]
    xchk[field]["n_obs_only_in_rdtc_panel"] = int(len(only_rdtc))
    xchk[field]["n_obs_only_in_slt1_rederivation"] = int(len(only_mine))
xchk["note_coverage"] = (
    "the committed RDTC panel carries actives back to 2013-01 on the Form S basis "
    "(tx_source s1_globl.txt) and switches to slt_table1.txt/SLT from 2023-02; this "
    "re-derivation is slt_table1-only, so pre-2023-02 actives exist only in the RDTC "
    "panel -- the comparison above is over the overlapping non-null observations")
xchk["all_overlaps_match_within_rounding"] = all(
    xchk[f]["n_mismatches_beyond_rounding_0p5musd"] == 0
    for f in ["pos_musd", "active_musd", "valchg_musd"])
assert xchk["all_overlaps_match_within_rounding"], \
    "RDTC panel vs slt_table1 re-derivation mismatch beyond rounding -- a finding; failing loudly"
xchk["SOURCE"] = (os.path.relpath(P_RDTC_PANEL, ROOT) + "; " + os.path.relpath(P_SLT1, ROOT))

# ----------------------------------------------------------------------------
# 5. TABLE C -- basis-reconciliation staging numbers (NO verdict)
# ----------------------------------------------------------------------------
off_csv = pd.read_csv(P_OFFICIAL, dtype={"month": str})
off_csv = off_csv.set_index("month")

# committed targets, READ from RDTE_result.json (never typed in)
rdte_off = rdte_res["official_series_recompute_from_csv"]["changes_busd"]
tgt_frbny_ref = float(rdte_off["frbny_custody_ust_busd"]["verdict_axis_refmonth_2023_04_to_2026_04"])
tgt_frbny_start = float(rdte_off["frbny_custody_ust_busd"]["verdict_axis_startmonth_2023_05_to_2026_04"])
tgt_tic_ref = float(rdte_off["tic_official_ust_busd"]["verdict_axis_refmonth_2023_04_to_2026_04"])

frbny_l0 = float(off_csv.loc[AXIS_REF, "frbny_custody_ust_busd"])
frbny_l1 = float(off_csv.loc[AXIS_END, "frbny_custody_ust_busd"])
frbny_ls = float(off_csv.loc[AXIS_START, "frbny_custody_ust_busd"])
frbny_ref_chg = round(frbny_l1 - frbny_l0, 6)
frbny_start_chg = round(frbny_l1 - frbny_ls, 6)
assert abs(frbny_ref_chg - tgt_frbny_ref) < TOL, "FRBNY refmonth change does not reproduce committed"
assert abs(frbny_start_chg - tgt_frbny_start) < TOL, "FRBNY startmonth change does not reproduce committed"

tic_l0 = float(off_csv.loc[AXIS_REF, "tic_official_ust_busd"])
tic_l1 = float(off_csv.loc[AXIS_END, "tic_official_ust_busd"])
tic_ref_chg = round(tic_l1 - tic_l0, 6)
assert abs(tic_ref_chg - tgt_tic_ref) < TOL, "TIC official refmonth change does not reproduce committed"

# SLT LT-official Treasury row (the on-disk official rows CARRYING the stated
# valuation-change column). Finding: slt2d.txt on disk is a holdings-only wide
# table (span stated below) with NO valuation-change column; the official rows
# with the stated valchg column are slt_table1's 'Of Which: Foreign Official' line.
slt2d_lines = open(P_SLT2D, encoding="utf-8").read().splitlines()
slt2d_title = next(ln.strip() for ln in slt2d_lines if ln.strip())
assert slt2d_title.startswith("Table 2D:"), "slt2d.txt structure drift"
assert not any("aluation" in ln for ln in slt2d_lines), \
    "slt2d.txt now carries a valuation column -- the Table C source note would be wrong"
yr_row = next(ln for ln in slt2d_lines if re.search(r"\b20\d\d\b", ln))
slt2d_years = sorted(set(re.findall(r"\b20\d\d\b", yr_row)))

offl = df[df["country"] == "Of Which: Foreign Official"].set_index("month")
assert len(offl) > 0, "official line absent from slt_table1"
slt_h0 = float(offl.loc[AXIS_REF, "tre_pos"])
slt_h1 = float(offl.loc[AXIS_END, "tre_pos"])
offl_axis = offl.loc[offl.index.isin(axis_months)]
assert offl_axis["tre_val"].notna().all() and offl_axis["tre_net"].notna().all() \
    and len(offl_axis) == len(axis_months), "official line valchg/net incomplete on axis"
slt_dH = round(slt_h1 - slt_h0, 6)                    # musd
slt_cumval = float(offl_axis["tre_val"].sum())        # musd
slt_cumnet = float(offl_axis["tre_net"].sum())        # musd
slt_txbasis = round(slt_dH - slt_cumval, 6)           # musd
slt_gap = round(slt_dH - slt_cumval - slt_cumnet, 6)  # musd

raw_div = round(abs(frbny_ref_chg - tic_ref_chg), 6)
basis_adj_div = round(abs(frbny_ref_chg - busd(slt_txbasis)), 6)

tableC = {
    "NO_VERDICT": ("staging numbers only -- Phase-2 assembly renders "
                   "TENSION-ARTIFACT / TENSION-REAL / PARTIAL against the "
                   "pre-registered thresholds in RDTF_prediction.md; nothing here is a verdict"),
    "month_alignment_convention": (
        "read from the committed RDTE_result.json official_series_recompute_from_csv "
        "key naming: the committed verdict-axis change is the REFMONTH convention -- "
        "level(2026-04) minus level(2023-04) of the monthly series ('verdict_axis_"
        "refmonth_2023_04_to_2026_04'); the startmonth variant (2023-05 base) is "
        "carried as context. FRBNY monthly levels are the within-month H.4.1 weekly "
        "observation dated in the csv's frbny_obs_date column."),
    "frbny_leg": {
        "series": "frbny_custody_ust_busd (H.4.1 memo: marketable U.S. Treasury securities held in custody for foreign official and international accounts)",
        "level_refmonth_busd": frbny_l0,
        "level_refmonth_obs_date": str(off_csv.loc[AXIS_REF, "frbny_obs_date"]),
        "level_end_busd": frbny_l1,
        "level_end_obs_date": str(off_csv.loc[AXIS_END, "frbny_obs_date"]),
        "change_refmonth_2023_04_to_2026_04_busd": frbny_ref_chg,
        "rdte_committed_target_busd": tgt_frbny_ref,
        "reproduces_committed": True,
        "change_startmonth_2023_05_to_2026_04_busd_context": frbny_start_chg,
        "SOURCE": os.path.relpath(P_OFFICIAL, ROOT),
    },
    "tic_official_mfh_leg": {
        "series": "tic_official_ust_busd (TIC MFH-basis foreign official holdings of U.S. Treasury securities, incl. short-term; sources named per-row in the csv)",
        "level_refmonth_busd": tic_l0,
        "level_end_busd": tic_l1,
        "change_refmonth_2023_04_to_2026_04_busd": tic_ref_chg,
        "rdte_committed_target_busd": tgt_tic_ref,
        "reproduces_committed": True,
        "SOURCE": os.path.relpath(P_OFFICIAL, ROOT),
    },
    "which_file_carries_official_valchg": {
        "finding": ("the on-disk " + os.path.relpath(P_SLT2D, ROOT) + " is a holdings-"
                    "only wide table (title '" + slt2d_title + "', years " +
                    "/".join(slt2d_years) + ") with NO valuation-change column; the "
                    "official Treasury rows WITH the stated valuation-change column on "
                    "disk are slt_table1's 'Of Which: Foreign Official' line (code "
                    "99990), columns Holdings / Net U.S. Sales / Valuation Change per "
                    "class, published from 2023-02"),
        "SOURCE": os.path.relpath(P_SLT2D, ROOT) + "; " + os.path.relpath(P_SLT1, ROOT),
    },
    "tic_official_slt_lt_leg": {
        "series": "slt_table1 'Of Which: Foreign Official' (99990), U.S. Treasuries (LONG-TERM only), musd -> busd",
        "holdings_refmonth_busd": busd(slt_h0),
        "holdings_end_busd": busd(slt_h1),
        "delta_holdings_refmonth_busd": busd(slt_dH),
        "cumulative_stated_valchg_axis_busd": busd(slt_cumval),
        "transactions_basis_change_busd (= delta_holdings - cum_valchg, the pre-registered adjustment)": busd(slt_txbasis),
        "cumulative_net_us_sales_axis_busd_context": busd(slt_cumnet),
        "slt_identity_gap_busd_context (= dH - cum_net - cum_valchg; coverage/reclassification gap G)": busd(slt_gap),
        "basis_note_finding": (
            "the committed +116.8 is on the MFH basis (ALL foreign-official Treasury "
            "holdings incl. short-term); the SLT LT-official row -- the only on-disk "
            "official series carrying a stated valuation-change column -- moves " +
            str(busd(slt_dH)) + " busd over the same axis. Both are reported; the "
            "difference is a basis fact of the two publishers' tables, recorded here, "
            "not reconciled here."),
        "SOURCE": os.path.relpath(P_SLT1, ROOT),
    },
    "divergences": {
        "raw_divergence_busd (= |FRBNY_change - TIC_official_delta_holdings(MFH basis, committed)|)": raw_div,
        "basis_adjusted_divergence_busd (= |FRBNY_par_change - TIC_official_txbasis_change(SLT LT-official)|)": basis_adj_div,
        "context_divergence_vs_slt_lt_delta_holdings_busd": round(abs(frbny_ref_chg - busd(slt_dH)), 6),
        "context_divergence_vs_slt_lt_cum_net_busd": round(abs(frbny_ref_chg - busd(slt_cumnet)), 6),
    },
    "SOURCE": (os.path.relpath(P_OFFICIAL, ROOT) + "; " + os.path.relpath(P_SLT1, ROOT)
               + "; " + os.path.relpath(P_SLT2D, ROOT) + "; " + os.path.relpath(P_RDTE_RES, ROOT)),
}

# ----------------------------------------------------------------------------
# 6. Detail parquet (the full re-derived per-line panel, deterministic order)
# ----------------------------------------------------------------------------
panel_rows = []
for (name, code), g in df.groupby(["country", "code"]):
    for stem, cls in STEM2CLASS:
        sub = g[["month", stem + "_pos", stem + "_net", stem + "_val"]].copy()
        sub.columns = ["month", "pos_musd", "active_musd", "valchg_musd"]
        sub.insert(0, "country", name)
        sub.insert(1, "country_code", str(code))
        sub.insert(2, "line_type", line_type(name, code))
        sub.insert(3, "asset_class", cls)
        panel_rows.append(sub)
panel_out = pd.concat(panel_rows, ignore_index=True)
panel_out = panel_out.sort_values(
    ["country", "country_code", "asset_class", "month"]).reset_index(drop=True)
panel_out.to_parquet(OUT_PARQUET, index=False)

# ----------------------------------------------------------------------------
# 7. Self-check + artifact
# ----------------------------------------------------------------------------
n_lines_with_data = sum(1 for r in tableA_axis.values()
                        if r["M_center_gross_busd"] is not None)
checks = {
    "axis_lies_fully_on_by_country_active_basis": True,
    "every_line_computed_no_prefilter": len(tableA_axis) == n_lines,
    "n_lines_total": int(n_lines),
    "n_lines_with_active_data": int(n_lines_with_data),
    "rdte_capA_reproduced_per_class_and_total": True,
    "china_axis_total_matches_cap_constant": True,
    "sanity_ii_china_gross_geq_net_every_class_both_windows": True,
    "sanity_iii_gross_geq_net_every_line_both_windows": True,
    "pooled_leq_sum_of_separates": bool(sum_sep >= pooled - 1e-9),
    "rdtc_panel_crosscheck_within_rounding": xchk["all_overlaps_match_within_rounding"],
    "frbny_and_tic_committed_changes_reproduced": True,
    "no_branch_verdict_emitted": True,
    "no_M_hi_global_emitted": True,
}
checks["all_pass"] = all(v is True or (not isinstance(v, bool)) for v in checks.values())

artifact = {
    "artifact": ("RDTF_ingredients (RDT-F Phase 1: ingredient tables only -- Table A "
                 "per-center ceilings under BOTH pre-registered constructions for every "
                 "slt_table1 country line; Table B is subtraction over Table A's exact "
                 "totals; Table C basis-reconciliation staging numbers). No branch "
                 "verdict, no M_hi_global, no grounded-set selection here."),
    "establishment": ("NOT ESTABLISHED -- output of RDTF_ingredients_recompute.py; every "
                      "number below is an OUTPUT pending its verifier scenario "
                      "(deterministic re-run of build/reserve/RDTF_ingredients_recompute.py "
                      "reproducing this file byte-for-byte, and the RDT-F human gate). "
                      "No ceiling value here is a migration finding; ceilings bound, "
                      "they do not establish."),
    "contract": "build/reserve/RDTF_prediction.md (pre-registered; constructions, windows, and the basis-adjustment method fixed there and implemented exactly)",
    "no_date_no_probability_no_currency_guess": ("no breaking-point date, no probability, "
                                                 "no currency guess appears in this artifact"),
    "flipped_guard (carried from the pre-registration)": {
        "DRAMATIZE": ("no center is omitted here BY CONSTRUCTION: both constructions are "
                      "computed for every country line in the file; the verdict basis "
                      "(gross) is computed everywhere the net one is"),
        "ZERO": ("the min() against China's per-class gross decline zeroes accretion in "
                 "classes China never sold in any window month, mechanically; no "
                 "beneficial-owner taxonomy is applied here -- set membership is decided "
                 "in the parallel grounding pass, not in this artifact"),
    },
    "inputs_sha256": {os.path.relpath(p, ROOT): sha256(p) for p in
                      [P_SLT1, P_RDTC_PANEL, P_OFFICIAL, P_SLT2D, P_SLT1D,
                       P_RDTC_FLOWS, P_RDTE_ING, P_RDTE_RES, P_PRED]},
    "units": ("all *_busd fields are billions of USD (exact: the source file is integer "
              "millions, so busd values are exact at 3 decimals; emitted unrounded at "
              "full float precision via round(.,6))"),
    "windows": {
        "verdict_axis": {"start": AXIS_START, "end": AXIS_END, "n_months": len(axis_months),
                         "holdings_reference_month": AXIS_REF,
                         "role": "VERDICT AXIS (RDT-B/C/D/E lineage, pre-registered)",
                         "on_active_basis": schema_finding["verified_axis_on_active_basis"]},
        "full_window": {"start": str(net_first), "end": str(net_last),
                        "n_months": len(full_months),
                        "role": ("context -- earliest..latest available on slt_table1's "
                                 "by-country ACTIVE basis (this file's by-country "
                                 "transactions begin 2023-02; positions begin 2020-01)")},
    },
    "schema_finding": schema_finding,
    "cap_constant_446p493": cap_constant,
    "china_gross_decline_rooms": {
        "definition": ("ChinaGrossDecline_k = Sum_months max(-China_active_{k,m}, 0); "
                       "net room = max(-Sum_months China_active_{k,m}, 0); busd"),
        "verdict_axis": rooms_axis,
        "full_window": rooms_full,
        "sanity_ii_gross_geq_net": sanity_ii,
        "SOURCE": os.path.relpath(P_SLT1, ROOT),
    },
    "table_A_per_center_ceilings": {
        "definitions": {
            "GROSS (verdict basis, overstating-safe)": ("M_center_gross(c) = Sum_k min("
                "ChinaGrossDecline_k, CenterGrossInflow_k(c)); CenterGrossInflow_k(c) = "
                "Sum_months max(+C_active_{k,m}, 0)"),
            "WINDOW-NET (RDT-E's construction; tighter, disputed sensitivity)": (
                "M_center_net(c) = Sum_k min(max(-ChinaNetActive_k,0), "
                "max(CenterNetActive_k(c),0)), Net = plain window sum of monthly actives"),
            "null_totals": ("lines whose transactions columns are entirely 'n.a.' carry "
                            "null totals (no fabricated zeros); they are listed in "
                            "schema_finding.lines_with_no_transactions_data"),
        },
        "known_candidates_marked": KNOWN_CANDIDATES,
        "verdict_axis": tableA_axis,
        "full_window": tableA_full,
        "sanity_iii_gross_geq_net": {"verdict_axis": sanity_iii_axis,
                                     "full_window": sanity_iii_full},
        "SOURCE": os.path.relpath(P_SLT1, ROOT),
    },
    "table_A_pooled_BE_LU (RDT-E's single-counterparty pooling, nested for comparison)": {
        "verdict_axis": belu_axis,
        "full_window": belu_full,
        "SOURCE": os.path.relpath(P_SLT1, ROOT),
    },
    "table_B_leave_one_center_out_note": (
        "LOCO over any grounded set is subtraction of a center's M_center total from the "
        "set sum; Table A's per-center totals above are exact (integer-musd sums divided "
        "by 1000), so no separate LOCO table is needed at the ingredient stage"),
    "staging_sum_known_candidate_set": {
        "LABEL": ("STAGING ONLY -- the real global sum is over the grounded center set "
                  "derived in the parallel grounding pass; this sum is over the known "
                  "candidate lines {BE, LU, CH, UK} so Phase-2 can cross-foot"),
        "centers": KNOWN_CANDIDATES,
        "sum_M_center_gross_verdict_axis_busd": staging_gross,
        "sum_M_center_windownet_verdict_axis_busd": staging_net,
        "SOURCE": os.path.relpath(P_SLT1, ROOT),
    },
    "cross_check": {
        "rdtc_panel_vs_slt1_rederivation": xchk,
        "rdte_capA_reproduction": {
            "per_class": repro_rows,
            "computed_pooled_windownet_total_busd": pooled,
            "rdte_committed_capA_total_busd": rdte_capA_total,
            "total_diff_busd": repro_total_diff,
            "REPRODUCED": True,
            "SOURCE": os.path.relpath(P_RDTE_ING, ROOT),
        },
        "pooled_vs_separate": {
            "belgium_M_windownet_busd": be_net,
            "luxembourg_M_windownet_busd": lu_net,
            "sum_of_separates_busd": sum_sep,
            "pooled_busd": pooled,
            "note": pooling_note,
        },
    },
    "table_C_basis_reconciliation_staging": tableC,
    "detail_parquet": os.path.relpath(OUT_PARQUET, ROOT),
    "self_check": checks,
}

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(artifact, f, indent=1, ensure_ascii=False, sort_keys=True)
    f.write("\n")

print("wrote", OUT_JSON)
print("wrote", OUT_PARQUET)
print("self_check all_pass:", checks["all_pass"])
if not checks["all_pass"]:
    print({k: v for k, v in checks.items() if v is not True and isinstance(v, bool)})
    sys.exit(1)
