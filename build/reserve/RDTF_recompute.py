#!/usr/bin/env python3
"""RDT-F Phase 2 -- ASSEMBLY: the route-robust global migration ceiling (Part 1),
the custody-basis reconciliation verdict (Part 2), and the insert-only object
amendment (Part 3).

Deterministic recompute. Regenerates:
  1. build/reserve/RDTF_result.json
  2. build/reserve/RDT_breaking_point_object.md -- insert-only RDTF-AMEND blocks
     (stripping them reproduces the post-RDT-E object byte-for-byte, checked against
     the sha256 recorded in RDTE_verify.json BEFORE amending)
  3. build/reserve/RDTF_verify.json -- result two-pass + byte-reproduction; the
     committed-ingredients sha pin; stripped-base sha; amended-object fixed point;
     all_pass.

Contract: build/reserve/RDTF_prediction.md (committed 6701b5c; pre-registered).
The branch verdict is rendered on the OVERSTATING-SAFE (gross) ceiling; window-net
is carried as the tighter, DISPUTED sensitivity, never the verdict. The MINOR
threshold is parsed programmatically from the committed RDTE_prediction.md (the
multiplier is extracted, the threshold is reproduced from the 446.493 read from the
RDTC artifacts, and the exact matched substring is recorded for the gate's
byte-match). The Part-2 thresholds (ARTIFACT <= 50, REAL >= 150, PARTIAL between)
are parsed programmatically from the committed RDTF_prediction.md.

Every number is read from committed inputs or computed here at run time -- nothing
is typed in (permitted literals: window endpoints, marker strings, file paths, and
regexes whose captured values are the parsed thresholds). Every branch of every
pre-registered landing combination (Part 1: MINOR-ROBUST / FORK-REOPENED; Part 2:
TENSION-ARTIFACT / TENSION-REAL / PARTIAL) is implemented and assertion-guarded --
an unfired branch cannot silently emit its text; changed data fail loud. No
network. No breaking-point date, no probability, no destination-currency guess.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent

ING_JSON = ROOT / "build/reserve/RDTF_ingredients.json"
ING_PARQUET = ROOT / "build/reserve/RDTF_ingredients_panel.parquet"
CENTERS_MANIFEST = ROOT / "build/reserve/RDTF_centers_manifest.json"
CENTERS_PROV = ROOT / "build/reserve/RDTF_centers_provenance.md"
BASIS_QUOTES = ROOT / "build/reserve/RDTF_basis_quotes.md"
SECB_EXTRACT = ROOT / "build/reserve/rdtf_evidence/tic_secb_live_extracted.txt"
RDTE_PRED = ROOT / "build/reserve/RDTE_prediction.md"
RDTF_PRED = ROOT / "build/reserve/RDTF_prediction.md"
RDTE_RESULT = ROOT / "build/reserve/RDTE_result.json"
RDTE_VERIFY = ROOT / "build/reserve/RDTE_verify.json"
RDTC_FLOWS = ROOT / "build/reserve/RDTC_class_flows.json"
RDTC_RESULT = ROOT / "build/reserve/RDTC_result.json"
RDTD_RESULT = ROOT / "build/reserve/RDTD_result.json"
OBJECT_MD = ROOT / "build/reserve/RDT_breaking_point_object.md"

OUT_RESULT = ROOT / "build/reserve/RDTF_result.json"
OUT_VERIFY = ROOT / "build/reserve/RDTF_verify.json"

# Pin: the committed Phase-1 ingredients this assembly was tasked against.
EXPECTED_ING_SHA = "537697007a1249254fe5acf7b5993141100b2e571ea2c916ba88f69f3a99f2aa"

CLASSES = ["treasury_lt", "agency_lt", "corp_other_bonds_lt", "equity_lt"]
AXIS_START, AXIS_END, AXIS_REF = "2023-05", "2026-04", "2023-04"

BELU4 = ["Belgium", "Luxembourg", "Switzerland", "United Kingdom"]
GROUP_CODE = "CARIB-BC"

# Publisher-defined Caribbean-banking-centers member names (each name is
# guard-checked below against the verbatim publisher quotes read from the
# committed manifest / retained evidence -- the lists fail loud if the quotes
# change; the names themselves are name strings, not numbers).
CBC_MFHHIS01 = ["Bahamas", "Bermuda", "Cayman Islands", "Netherlands Antilles",
                "Panama", "British Virgin Islands"]
CBC_SECB2016 = ["Bahamas", "Bermuda", "Bonaire/Sint Eustatius/Saba",
                "British Virgin Islands", "Cayman Islands", "Curaçao",
                "Panama", "Sint Maarten"]
SHL_CFC = ["Bermuda", "Bonaire, Sint Eustatius, and Saba",
           "British Virgin Islands", "Cayman Islands", "Curacao", "Panama"]
# Map of publisher member names -> slt_table1 country-line names (identity except
# for the diacritic on Curacao); members with no line on the axis are stated.
NAME_TO_LINE = {"Bahamas": "Bahamas", "Bermuda": "Bermuda",
                "Cayman Islands": "Cayman Islands",
                "British Virgin Islands": "British Virgin Islands",
                "Panama": "Panama", "Curaçao": "Curacao",
                "Curacao": "Curacao"}
# Caribbean-region country lines published in slt_table1 (the SLT aggregate's
# implied membership is tested mechanically against these lines below).
SLT_CARIB_LINES = ["Anguilla", "Aruba", "Bahamas", "Barbados", "Bermuda",
                   "British Virgin Islands", "Cayman Islands", "Cuba", "Curacao",
                   "Jamaica", "Saint Kitts and Nevis", "Trinidad and Tobago"]


def guard(cond, msg):
    if not cond:
        raise AssertionError("GUARD FAILED: " + msg)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def r3(x):
    return round(float(x), 3)


def m3(x):  # unsigned magnitude, 3 decimals
    return f"{float(x):.3f}"


def s3(x):  # signed, 3 decimals
    return f"{float(x):+.3f}"


def s1(x):  # signed, 1 decimal (TIC MFH official series is published at 1 decimal)
    return f"{float(x):+.1f}"


def norm_ws(t):
    return re.sub(r"\s+", " ", t)


# ---------------------------------------------------------------------------
# 0. Load committed inputs; vintage pins
# ---------------------------------------------------------------------------

ING_SHA = sha256_file(ING_JSON)
guard(ING_SHA == EXPECTED_ING_SHA,
      f"RDTF_ingredients.json sha {ING_SHA} != tasked pin {EXPECTED_ING_SHA}")

ING = json.load(open(ING_JSON, encoding="utf-8"))
MANIFEST = json.load(open(CENTERS_MANIFEST, encoding="utf-8"))
RDTE = json.load(open(RDTE_RESULT, encoding="utf-8"))
RDTEV = json.load(open(RDTE_VERIFY, encoding="utf-8"))
RDTC = json.load(open(RDTC_FLOWS, encoding="utf-8"))
RDTCR = json.load(open(RDTC_RESULT, encoding="utf-8"))
RDTD = json.load(open(RDTD_RESULT, encoding="utf-8"))
RDTE_PRED_TEXT = open(RDTE_PRED, encoding="utf-8").read()
RDTF_PRED_TEXT = open(RDTF_PRED, encoding="utf-8").read()
BASIS_TEXT = open(BASIS_QUOTES, encoding="utf-8").read()
SECB_TEXT = open(SECB_EXTRACT, encoding="utf-8").read()

# vintage coherence: the ingredients were built against exactly the artifacts on disk
for f, want in ING["inputs_sha256"].items():
    p = ROOT / f
    if p.exists():
        guard(sha256_file(p) == want,
              f"{f} on disk differs from the vintage the RDTF ingredients were built on")

INPUTS_SHA = {
    "build/reserve/RDTF_ingredients.json": ING_SHA,
    "build/reserve/RDTF_ingredients_panel.parquet": sha256_file(ING_PARQUET),
    "build/reserve/RDTF_centers_manifest.json": sha256_file(CENTERS_MANIFEST),
    "build/reserve/RDTF_centers_provenance.md": sha256_file(CENTERS_PROV),
    "build/reserve/RDTF_basis_quotes.md": sha256_file(BASIS_QUOTES),
    "build/reserve/rdtf_evidence/tic_secb_live_extracted.txt": sha256_file(SECB_EXTRACT),
    "build/reserve/RDTE_prediction.md": sha256_file(RDTE_PRED),
    "build/reserve/RDTF_prediction.md": sha256_file(RDTF_PRED),
    "build/reserve/RDTE_result.json": sha256_file(RDTE_RESULT),
    "build/reserve/RDTE_verify.json": sha256_file(RDTE_VERIFY),
    "build/reserve/RDTC_class_flows.json": sha256_file(RDTC_FLOWS),
    "build/reserve/RDTC_result.json": sha256_file(RDTC_RESULT),
    "build/reserve/RDTD_result.json": sha256_file(RDTD_RESULT),
}


# ---------------------------------------------------------------------------
# 1. Constants -- READ from committed artifacts (field paths recorded), never typed
# ---------------------------------------------------------------------------

def read_constants():
    cap_primary = float(RDTC["ledgers"]["recent_3y_verdict_axis"]["china_alone"]
                        ["residual_left_us_busd"])
    cap_cross1 = float(RDTCR["ledgers"]["recent_3y_verdict_axis"]["china_alone"]
                       ["residual_left_us_busd"])
    cap_cross2 = float(RDTD["identity"]["china_alone"]["active_outflow_busd"])
    cap_cross3 = float(ING["cap_constant_446p493"]["value_busd"])
    guard(cap_primary == cap_cross1 == cap_cross2 == cap_cross3,
          "the 446.493 constant disagrees across RDTC/RDTD/RDTF artifacts")

    dnonus = float(RDTD["identity"]["china_alone"]["delta_non_us_busd"])
    dnonus_cross = float(RDTE["interval_delta_nonus_true_busd"]
                         ["delta_nonus_busd (read from RDTD_result.json)"])
    guard(dnonus == dnonus_cross,
          "the 494.977 constant disagrees between RDTD_result.json and RDTE_result.json")

    cap = {
        "value_busd": r3(cap_primary),
        "SOURCE": {
            "primary": {"file": "build/reserve/RDTC_class_flows.json",
                        "field": "ledgers.recent_3y_verdict_axis.china_alone.residual_left_us_busd"},
            "cross_reads": [
                {"file": "build/reserve/RDTC_result.json",
                 "field": "ledgers.recent_3y_verdict_axis.china_alone.residual_left_us_busd"},
                {"file": "build/reserve/RDTD_result.json",
                 "field": "identity.china_alone.active_outflow_busd"},
                {"file": "build/reserve/RDTF_ingredients.json",
                 "field": "cap_constant_446p493.value_busd"},
            ],
        },
        "role": "M_hi_global = min(Sum_grounded-centers M_center(gross), this value) -- the ceiling cannot exceed the net decline it explains",
    }
    dn = {
        "value_busd": r3(dnonus),
        "SOURCE": {
            "primary": {"file": "build/reserve/RDTD_result.json",
                        "field": "identity.china_alone.delta_non_us_busd"},
            "cross_reads": [
                {"file": "build/reserve/RDTE_result.json",
                 "field": "interval_delta_nonus_true_busd.'delta_nonus_busd (read from RDTD_result.json)'"},
            ],
        },
        "role": "DeltaNonUS-true in [494.977 - M_hi_global, 494.977] (pool caveat and k1 wall riding)",
    }
    return cap, dn, cap_primary, dnonus


# ---------------------------------------------------------------------------
# 2. Thresholds -- parsed programmatically from the committed prediction texts
# ---------------------------------------------------------------------------

def parse_thresholds(cap446):
    m = re.search(r"M_hi\s*≤\s*([0-9.]+)\s*×\s*" + re.escape(f"{cap446:.3f}"),
                  RDTE_PRED_TEXT)
    guard(m is not None, "MINOR threshold rule not found in RDTE_prediction.md")
    mult = float(m.group(1))
    thr = r3(mult * cap446)
    n = norm_ws(RDTF_PRED_TEXT)
    mm = re.search(r"MINOR-ROBUST\*\* iff M_hi_global ≤ ([0-9.]+)", n)
    guard(mm is not None, "MINOR-ROBUST restatement not found in RDTF_prediction.md")
    guard(float(mm.group(1)) == thr,
          f"RDTF_prediction.md restates the MINOR threshold as {mm.group(1)} but "
          f"multiplier x cap = {thr}")
    vac = re.search(r"if the sum reaches the cap, the ceiling is VACUOUS and the "
                    r"branch is FORK-REOPENED regardless", n)
    guard(vac is not None, "vacuous-cap rule not found in RDTF_prediction.md")
    a = re.search(r"TENSION-ARTIFACT\*\* iff the basis-adjusted divergence ≤ (\d+) \$bn", n)
    r_ = re.search(r"TENSION-REAL\*\* iff ≥ (\d+) \$bn", n)
    guard(a is not None and r_ is not None,
          "Part-2 thresholds not found in RDTF_prediction.md")
    art_thr, real_thr = float(a.group(1)), float(r_.group(1))
    guard(art_thr < real_thr, "Part-2 thresholds out of order")
    return {
        "minor_threshold_busd": thr,
        "multiplier_as_parsed": mult,
        "matched_substring_of_RDTE_prediction_md (exact bytes, for the gate's byte-match)": m.group(0),
        "matched_substring_of_RDTF_prediction_md_restatement": mm.group(0),
        "vacuous_cap_rule_matched_substring_of_RDTF_prediction_md": vac.group(0),
        "computed_as": f"{mult} x {cap446:.3f} (446.493 read from RDTC artifacts, never typed) = {thr:.3f}",
        "part2_artifact_leq_busd": art_thr,
        "part2_real_geq_busd": real_thr,
        "part2_matched_substrings_of_RDTF_prediction_md": [a.group(0), r_.group(0)],
        "SOURCE": "build/reserve/RDTE_prediction.md (MINOR multiplier); build/reserve/RDTF_prediction.md (branch mapping + Part-2 thresholds); build/reserve/RDTC_class_flows.json (the 446.493)",
    }, thr, art_thr, real_thr


# ---------------------------------------------------------------------------
# 3. Part 1 -- the grounded set, the CARIB-BC group, the global ceiling
# ---------------------------------------------------------------------------

def grounded_set():
    entries = MANIFEST["grounded_centers"]
    names = [e["name"] for e in entries]
    codes = [e["code"] for e in entries]
    guard(codes == ["BEL", "LUX", "CHE", "GBR", "CARIB-BC"],
          f"grounded set changed: {codes} -- the assembly is written for BEL/LUX/CHE/GBR + CARIB-BC")
    ptr = []
    for e in entries:
        ptr.append({"code": e["code"], "name": e["name"],
                    "grounding_quote_verbatim": e["quote"],
                    "quote_source_path": e["quote_source_path"]})
    return names, ptr


def membership_comparison():
    """MECHANICAL RULE (tasked): compare SLT's 'Total Caribbean' membership against the
    publisher-defined Caribbean-banking-centers membership quoted in the manifest."""
    carib = [e for e in MANIFEST["grounded_centers"] if e["code"] == GROUP_CODE][0]
    q_mfh = [q for q in carib["supporting_quotes"] if "mfhhis01" in q["quote_source_path"]]
    q_shl = [q for q in carib["supporting_quotes"] if "shl2025r" in q["quote_source_path"]]
    guard(len(q_mfh) == 1 and len(q_shl) == 1,
          "manifest no longer carries the mfhhis01-fn4 and SHL-3.3 membership quotes")
    q_mfh, q_shl = q_mfh[0], q_shl[0]
    for name in CBC_MFHHIS01:
        guard(name in q_mfh["quote"], f"'{name}' not in the mfhhis01 footnote-4 quote")
    for name in SHL_CFC:
        guard(name in q_shl["quote"], f"'{name}' not in the SHL 3.3 quote")
    msec = re.search(r"Caribbean Banking Centers \(([^)]*)\)", SECB_TEXT)
    guard(msec is not None, "the 5-16-2016 CBC membership restatement not found in tic_secb_live_extracted.txt")
    for name in CBC_SECB2016:
        guard(name in msec.group(1), f"'{name}' not in the securities(b) 2016 CBC restatement")

    # No SLT documentation/footnote on disk defines 'Total Caribbean' membership:
    # slt_table1.txt's own Definitions block defines only the Euro area and the
    # European Union. Per the tasked rule, membership is taken from what the
    # country lines under it imply -- tested mechanically on the committed panel.
    slt1 = open(ROOT / "build/data/treasury_tic/current/slt_tables/slt_table1.txt",
                encoding="utf-8", errors="replace").read()
    guard("Total Caribbean" in slt1 and "Caribbean" not in
          slt1.split("Definitions:")[-1],
          "slt_table1.txt now carries a Caribbean definition -- re-derive membership from it")

    df = pd.read_parquet(ING_PARQUET)
    pos = df.pivot_table(index="month", columns="country", values="pos_musd",
                         aggfunc="sum")  # sums the 4 asset classes
    tc = pos["Total Caribbean"].dropna()
    months = tc.index
    res_wo = (tc - pos.loc[months, SLT_CARIB_LINES].sum(axis=1))
    res_w = (tc - pos.loc[months, SLT_CARIB_LINES + ["Panama"]].sum(axis=1))
    guard((res_wo >= 0).all(),
          "Total Caribbean minus the 12 published Caribbean lines went negative -- membership test broken")
    guard((res_w < 0).all(),
          "Total Caribbean minus (12 lines + Panama) is not negative in every month -- Panama-exclusion test broken")

    slt_implied = {
        "published_country_lines_implied_inside (12)": SLT_CARIB_LINES,
        "panama_implied_OUTSIDE": True,
        "test": ("per month over all {} months with positions (2020-01..2026-04, all four classes summed): "
                 "Total Caribbean minus the 12 published Caribbean lines is ALWAYS >= 0 "
                 "(min {:+.3f}, max {:+.3f} $bn -- a small unpublished-country residual), "
                 "while adding Panama makes it negative in EVERY month "
                 "(min {:+.3f}, max {:+.3f} $bn), which is impossible if Panama were a member"
                 ).format(len(months), r3(res_wo.min() / 1000.0), r3(res_wo.max() / 1000.0),
                          r3(res_w.min() / 1000.0), r3(res_w.max() / 1000.0)),
        "unpublished_residual_note": "the always-nonnegative residual implies further member countries whose lines slt_table1 does not publish; they cannot be enumerated from the file",
    }

    slt_set = set(SLT_CARIB_LINES)
    cbc_lines = sorted({NAME_TO_LINE[n] for n in CBC_MFHHIS01 + CBC_SECB2016
                        if n in NAME_TO_LINE})
    in_slt_not_cbc = sorted(slt_set - set(cbc_lines))
    in_cbc_not_slt = sorted(set(cbc_lines) - slt_set)
    differ = (len(in_slt_not_cbc) > 0) or (len(in_cbc_not_slt) > 0)
    guard(differ, "memberships unexpectedly match -- branch (a) would apply; re-run the assembly for it")

    return {
        "rule": "tasked MECHANICAL RULE: if the memberships match, the SLT 'Total Caribbean' gross enters as the group ceiling; if they differ, construct the group ceiling from the publisher-defined member country lines at GROUP level",
        "publisher_defined_CBC_membership": {
            "mfhhis01_footnote4_verbatim": q_mfh["quote"],
            "mfhhis01_source_path": q_mfh["quote_source_path"],
            "securities_b_2016_restatement_verbatim": msec.group(0),
            "securities_b_2016_source_path": "build/reserve/rdtf_evidence/tic_secb_live_extracted.txt (5-16-2016 notice); reading aid of build/reserve/rdtb_evidence/tic_secb_live.html",
            "shl_3_3_closely_related_grouping_verbatim": q_shl["quote"],
            "shl_3_3_source_path": q_shl["quote_source_path"],
            "member_names_mfhhis01": CBC_MFHHIS01,
            "member_names_securities_b_2016 (post-Netherlands-Antilles-dissolution restatement)": CBC_SECB2016,
            "member_names_shl_3_3_variant": SHL_CFC,
        },
        "slt_total_caribbean_membership_implied": slt_implied,
        "slt_documentation_finding": "no on-disk SLT documentation or footnote defines 'Total Caribbean' membership (slt_table1.txt's Definitions block defines only the Euro area and the European Union), so per the tasked rule the membership is taken from what the country lines imply",
        "comparison_verbatim": {
            "in_SLT_TotalCaribbean_but_NOT_publisher_CBC": in_slt_not_cbc,
            "in_publisher_CBC_but_NOT_SLT_TotalCaribbean": in_cbc_not_slt + ["(plus the unpublished-member residual cannot be checked)"],
            "verdict": "MEMBERSHIPS DIFFER",
            "plainly": ("SLT 'Total Caribbean' contains at least seven published country lines that are NOT "
                        "Caribbean-banking-centers members (" + ", ".join(in_slt_not_cbc) + ") plus an "
                        "unpublished-member residual, and it EXCLUDES Panama, which IS a publisher-defined "
                        "member; therefore branch (b) applies: the group ceiling is constructed from the "
                        "publisher-defined member country lines at GROUP level"),
        },
        "branch_taken": "(b) construct from publisher-defined member lines at GROUP level",
    }


def group_ceiling(window_key):
    """Rule (b): per class k, min(ChinaGrossDecline_k, Sum_publisher-members
    CenterGrossInflow_k), members at GROUP level; the window-net analogue is
    carried alongside (never the verdict)."""
    tblA = ING["table_A_per_center_ceilings"][window_key]
    rooms = ING["china_gross_decline_rooms"][window_key]
    n_months_expected = ING["windows"][
        "verdict_axis" if window_key == "verdict_axis" else "full_window"]["n_months"]

    members_on_axis, members_missing = [], []
    for name in CBC_MFHHIS01:
        if name == "Netherlands Antilles":
            members_missing.append(
                "Netherlands Antilles: no country line in slt_table1 on the axis (the publisher's "
                "5-16-2016 restatement maps it to Bonaire/Sint Eustatius/Saba, Curacao and Sint Maarten; "
                "Curacao has a line and is included; Bonaire/Sint Eustatius/Saba and Sint Maarten have "
                "no lines -- stated, not fabricated)")
            members_on_axis.append("Curacao")
        else:
            members_on_axis.append(NAME_TO_LINE[name])
    members_on_axis = sorted(set(members_on_axis))
    guard(members_on_axis == sorted(["Bahamas", "Bermuda", "British Virgin Islands",
                                     "Cayman Islands", "Curacao", "Panama"]),
          "unexpected member-line set for the CBC group")

    per_class, total_g, total_n = {}, 0.0, 0.0
    for k in CLASSES:
        china_g = float(rooms[k]["china_gross_decline_busd"])
        china_n = float(rooms[k]["china_net_decline_room_busd"])
        sg, sn = 0.0, 0.0
        for c in members_on_axis:
            e = tblA[c]
            guard(e["n_active_months_in_window"] == n_months_expected,
                  f"{c} lacks full per-class active data on {window_key}")
            sg += float(e["per_class"][k]["center_gross_inflow_busd"])
            sn += float(e["per_class"][k]["center_active_window_sum_busd"])
        g = r3(min(china_g, r3(sg)))
        n_ = r3(min(china_n, max(r3(sn), 0.0)))
        per_class[k] = {
            "china_gross_decline_busd": r3(china_g),
            "sum_member_gross_inflow_busd": r3(sg),
            "group_gross_min_busd": g,
            "china_net_room_busd": r3(china_n),
            "sum_member_net_busd": r3(sn),
            "group_windownet_min_busd (sensitivity)": n_,
        }
        total_g, total_n = r3(total_g + g), r3(total_n + n_)

    # SHL-3.3 membership variant (drops Bahamas; Bonaire/SES has no line), labelled
    var_lines = sorted({NAME_TO_LINE[n] for n in SHL_CFC if n in NAME_TO_LINE})
    vt = 0.0
    for k in CLASSES:
        vs = sum(float(tblA[c]["per_class"][k]["center_gross_inflow_busd"]) for c in var_lines)
        vt = r3(vt + min(float(rooms[k]["china_gross_decline_busd"]), r3(vs)))

    return {
        "construction": "rule (b), GROUP level: per class k, min(ChinaGrossDecline_k, Sum_publisher-members CenterGrossInflow_k); components from RDTF_ingredients.json table_A_per_center_ceilings." + window_key + ".<member>.per_class and china_gross_decline_rooms." + window_key,
        "member_lines_used": members_on_axis,
        "member_lines_missing_stated": members_missing,
        "per_class": per_class,
        "M_group_gross_busd": total_g,
        "M_group_windownet_busd (sensitivity, never the verdict)": total_n,
        "shl_3_3_membership_variant_gross_busd (labelled variant: drops Bahamas; Bonaire/Sint Eustatius/Saba has no line)": vt,
        "slt_total_caribbean_line_context (NOT used -- memberships differ)": {
            "M_gross_busd": r3(tblA["Total Caribbean"]["M_center_gross_busd"]),
            "M_windownet_busd": r3(tblA["Total Caribbean"]["M_center_windownet_busd"]),
            "line": "slt_table1 'Total Caribbean' (code 34401), " + str(tblA["Total Caribbean"]["n_active_months_in_window"]) + " active months",
        },
    }, total_g, total_n, vt


def branch_minor_robust(m, thr):
    guard(m <= thr, "MINOR-ROBUST branch fired with M_hi_global > threshold")
    return ("MINOR-ROBUST -- M_hi_global {} <= {}: RDT-E's MINOR survives its strongest "
            "route-robust test on the overstating-safe gross basis".format(m3(m), m3(thr)))


def branch_fork_reopened(m, thr):
    guard(m > thr, "FORK-REOPENED branch fired with M_hi_global <= threshold")
    return ("FORK-REOPENED -- M_hi_global {} > {}: the route-robust gross ceiling does not "
            "sustain MINOR; the interval is the deliverable and RDT-E's BE/LU MINOR is "
            "re-labelled ROUTE-SPECIFIC (BE/LU only)".format(m3(m), m3(thr)))


def part1(cap446, dnonus, thr):
    names, quote_ptrs = grounded_set()
    tblA_va = ING["table_A_per_center_ceilings"]["verdict_axis"]
    tblA_fw = ING["table_A_per_center_ceilings"]["full_window"]

    comparison = membership_comparison()
    grp_va, grp_g, grp_n, grp_var = group_ceiling("verdict_axis")
    grp_fw, grp_g_fw, grp_n_fw, _ = group_ceiling("full_window")

    per_center, sum4_g, sum4_n, sum4_gfw = {}, 0.0, 0.0, 0.0
    for c in BELU4:
        g, n_ = r3(tblA_va[c]["M_center_gross_busd"]), r3(tblA_va[c]["M_center_windownet_busd"])
        per_center[c] = {
            "M_gross_busd (VERDICT basis)": g,
            "M_windownet_busd (tighter, DISPUTED sensitivity)": n_,
            "full_window_context": {"M_gross_busd": r3(tblA_fw[c]["M_center_gross_busd"]),
                                    "M_windownet_busd": r3(tblA_fw[c]["M_center_windownet_busd"])},
            "SOURCE": "build/reserve/RDTF_ingredients.json table_A_per_center_ceilings.{verdict_axis,full_window}." + c,
        }
        sum4_g, sum4_n = r3(sum4_g + g), r3(sum4_n + n_)
        sum4_gfw = r3(sum4_gfw + r3(tblA_fw[c]["M_center_gross_busd"]))
    per_center["Caribbean banking centers (GROUP, constructed -- rule (b))"] = {
        "M_gross_busd (VERDICT basis)": grp_g,
        "M_windownet_busd (tighter, DISPUTED sensitivity)": grp_n,
        "full_window_context": {"M_gross_busd": grp_g_fw, "M_windownet_busd": grp_n_fw},
        "SOURCE": "constructed at GROUP level from RDTF_ingredients.json table_A per_class member blocks (see carib_bc_group.construction)",
    }

    guard(sum4_g == r3(ING["staging_sum_known_candidate_set"]["sum_M_center_gross_verdict_axis_busd"]),
          "BE/LU/CH/UK gross sum does not cross-foot the committed staging sum")
    guard(sum4_n == r3(ING["staging_sum_known_candidate_set"]["sum_M_center_windownet_verdict_axis_busd"]),
          "BE/LU/CH/UK windownet sum does not cross-foot the committed staging sum")

    sum_g = r3(sum4_g + grp_g)
    sum_n = r3(sum4_n + grp_n)
    m_hi_global = r3(min(sum_g, cap446))
    cap_binds = sum_g >= cap446
    guard(cap_binds, "the cap was expected to bind only if the sum reaches it; it did not -- "
                     "the ceiling is then the sum itself and this guard must be rewritten "
                     "against the committed rule before any verdict is rendered")
    branch = ("MINOR-ROBUST" if m_hi_global <= thr else "FORK-REOPENED")
    sentence = (branch_minor_robust(m_hi_global, thr) if branch == "MINOR-ROBUST"
                else branch_fork_reopened(m_hi_global, thr))

    # without-group sensitivity (labelled; the group is never dropped by choice)
    m_wo = r3(min(sum4_g, cap446))
    br_wo = "MINOR-ROBUST" if m_wo <= thr else "FORK-REOPENED"
    # SHL-membership-variant sensitivity
    m_var = r3(min(r3(sum4_g + grp_var), cap446))
    # SLT-line-as-group context
    m_slt = r3(min(r3(sum4_g + grp_va["slt_total_caribbean_line_context (NOT used -- memberships differ)"]["M_gross_busd"]), cap446))

    # leave-one-center-out (mandatory)
    loco = []
    centers_for_loco = list(BELU4) + ["Caribbean banking centers (GROUP)"]
    vals = [r3(tblA_va[c]["M_center_gross_busd"]) for c in BELU4] + [grp_g]
    for c, v in zip(centers_for_loco, vals):
        rest = r3(sum_g - v)
        m = r3(min(rest, cap446))
        loco.append({"dropped_center": c, "M_center_gross_busd": v,
                     "sum_remaining_gross_busd": rest,
                     "M_hi_global_without_it_busd": m,
                     "cap_binds": rest >= cap446,
                     "branch_implied": "MINOR-ROBUST" if m <= thr else "FORK-REOPENED"})
    loco_robust = all(row["branch_implied"] == branch for row in loco)

    interval = [r3(dnonus - m_hi_global), r3(dnonus)]
    rdte_mhi = r3(RDTE["combination_mechanical"]["M_hi_busd"])
    rdte_itv = [r3(x) for x in RDTE["interval_delta_nonus_true_busd"]["interval"]]
    guard(RDTE["mechanical_verdict"]["verdict"] == "MIGRATION-MINOR",
          "RDT-E's committed verdict is no longer MIGRATION-MINOR -- the re-labelling text is wrong")
    guard(r3(dnonus - rdte_mhi) == rdte_itv[0] and r3(dnonus) == rdte_itv[1],
          "RDT-E interval does not recompute from its own M_hi")

    relabel = ("ROUTE-SPECIFIC (BE/LU only)" if branch == "FORK-REOPENED"
               else "MIGRATION-MINOR (route-robust)")
    if branch == "FORK-REOPENED":
        guard(m_hi_global > thr, "re-label branch mismatch")
    else:
        guard(m_hi_global <= thr, "re-label branch mismatch")

    width = r3(interval[1] - interval[0])
    plain = ("the route-robust interval is NEARLY UNINFORMATIVE: its width is {} $bn of a possible {} "
             "$bn -- on the overstating-safe gross basis the grounded custody routes could absorb up to "
             "the entire {} $bn US-securities decline, so route-robust data alone cannot separate true "
             "departure from custody migration; only the BE/LU-specific bound (nested below) is tight, "
             "and it holds only on the assumption that BE/LU is the only migration route"
             ).format(m3(width), m3(dnonus), m3(cap446))
    guard(width == r3(cap446), "plain-statement arithmetic: width must equal the binding cap")

    return {
        "verdict_basis": "GROSS (overstating-safe, pre-registered); window-net carried alongside as the tighter, DISPUTED sensitivity, never the verdict",
        "grounded_set (DERIVED, not chosen -- quotes are the audit trail)": quote_ptrs,
        "per_center_ceilings_busd (verdict axis 2023-05..2026-04; full window 2023-02..2026-04 as context)": per_center,
        "carib_bc_membership_comparison": comparison,
        "carib_bc_group": {"verdict_axis": grp_va, "full_window_context": grp_fw},
        "carib_bc_group_confidence_caveat (MEDIUM -- rides the result, reported, never used to drop the group)": (
            "the group's custodial naming is GROUP-LEVEL ONLY and comes from the 2012-era TIC methodology "
            "documents (MFH methodology note; TIC FAQ 7), not from the current-vintage SHL 4.3.4 custodial-bias "
            "passage (which names only BE/LU/CH/UK); two member jurisdictions (Cayman Islands, British Virgin "
            "Islands) carry the pre-registration's beneficial-owner tagging and are NOT individually grounded "
            "(the zero-guard forbids admitting them individually); the TIC aggregate line for the group was "
            "discontinued after February 2016 data, so the group is operationalized here through publisher-defined "
            "member country lines at GROUP level -- see the without-group sensitivity, which the branch does not depend on"),
        "global_ceiling": {
            "sum_grounded_gross_busd": sum_g,
            "sum_grounded_windownet_busd (sensitivity, never the verdict)": sum_n,
            "cap_busd (read from RDTC artifacts)": r3(cap446),
            "M_hi_global_busd": m_hi_global,
            "cap_binds": bool(cap_binds),
            "ceiling_vacuous": bool(cap_binds),
            "vacuous_statement": ("the grounded gross sum {} reaches the {} cap, so the ceiling is VACUOUS "
                                  "per the pre-registered rule (the ceiling cannot exceed the net decline it "
                                  "explains) -- computed, not asserted: the BE/LU/CH/UK sum alone is {} and "
                                  "already exceeds the cap").format(m3(sum_g), m3(cap446), m3(sum4_g)),
            "windownet_min_vs_cap_busd (sensitivity)": r3(min(sum_n, cap446)),
        },
        "branch": {"label": branch, "sentence": sentence,
                   "rule": "MINOR-ROBUST iff M_hi_global <= {th}; FORK-REOPENED otherwise (threshold parsed from RDTE_prediction.md, restated in RDTF_prediction.md)".format(th=m3(thr))},
        "without_group_sensitivity (labelled -- the group is never dropped by choice)": {
            "sum_gross_busd": sum4_g, "M_hi_global_busd": m_wo, "branch_implied": br_wo,
            "note": "the branch is IDENTICAL with or without the MEDIUM-confidence group entry" if br_wo == branch else "the branch DEPENDS on the group entry",
        },
        "membership_variant_sensitivities (labelled)": {
            "shl_3_3_membership_group_variant": {"group_gross_busd": grp_var, "M_hi_global_busd": m_var},
            "slt_total_caribbean_line_as_group_context": {"M_hi_global_busd": m_slt},
        },
        "leave_one_center_out (mandatory)": {
            "table": loco,
            "finding": ("FORK-REOPENED is LOCO-ROBUST: the cap still binds after dropping any single grounded "
                        "center (minimum remaining sum {} > cap {})".format(
                            m3(min(row["sum_remaining_gross_busd"] for row in loco)), m3(cap446))
                        if (loco_robust and branch == "FORK-REOPENED") else
                        ("branch is LOCO-robust" if loco_robust else
                         "a single-center drop FLIPS the branch -- see table")),
            "loco_robust": bool(loco_robust),
        },
        "route_robust_interval": {
            "identity": "DeltaNonUS-true in [494.977 - M_hi_global, 494.977] (the 494.977 read from RDTD_result.json identity.china_alone.delta_non_us_busd; cross-read in RDTE_result.json)",
            "interval_busd": interval,
            "plain_statement": plain,
            "supersedes": "the RDT-E BE/LU-only interval as the ROUTE-ROBUST bound; the BE/LU figures stay nested below as the route-SPECIFIC bound",
        },
        "rdte_nested_route_specific_bound": {
            "M_hi_busd": rdte_mhi,
            "interval_busd": rdte_itv,
            "SOURCE": "build/reserve/RDTE_result.json combination_mechanical.M_hi_busd; interval_delta_nonus_true_busd.interval",
            "label_re_rendered": relabel,
            "re_render_rule": "pre-registered: if FORK-REOPENED, RDT-E's MIGRATION-MINOR is re-labelled ROUTE-SPECIFIC (BE/LU only), not robust",
            "survives_only_on": "the BE/LU route -- i.e. on the assumption that custody migration ran only through Euroclear/Clearstream" if branch == "FORK-REOPENED" else "all grounded routes",
        },
        "caveats_riding_everywhere": "the k1 wall (no destination currency is identified) and the pool caveat (TIC 'China, Mainland' != the SAFE reserve pool; rdtd_pool_determination.md) ride the interval and every label above",
    }, m_hi_global, branch, interval, loco, sum_g, sum4_g, sum_n, grp_g, m_wo, br_wo, relabel, plain


# ---------------------------------------------------------------------------
# 4. Part 2 -- the basis reconciliation verdict
# ---------------------------------------------------------------------------

def q_extract(pattern, text, what):
    m = re.search(pattern, text, re.S)
    guard(m is not None, f"basis quote not found: {what}")
    return norm_ws(m.group(1)).strip()


def verdict_artifact(adj, art_thr, real_thr):
    guard(adj <= art_thr, "TENSION-ARTIFACT branch fired out of range")
    return ("TENSION-ARTIFACT -- basis-adjusted divergence {} <= {}: the raw divergence collapses "
            "under the stated valuation adjustment".format(m3(adj), m3(art_thr)))


def verdict_real(adj, art_thr, real_thr):
    guard(adj >= real_thr, "TENSION-REAL branch fired out of range")
    return ("TENSION-REAL -- basis-adjusted divergence {} >= {}: a quantified residual of official "
            "custody leaving the Fed, unattributed".format(m3(adj), m3(real_thr)))


def verdict_partial(adj, art_thr, real_thr):
    guard(art_thr < adj < real_thr, "PARTIAL branch fired out of range")
    return ("PARTIAL -- basis-adjusted divergence {} lies between {} and {}: the stated valuation "
            "adjustment closes most but not all of the raw divergence; the residual is stated"
            .format(m3(adj), m3(art_thr), m3(real_thr)))


def part2(art_thr, real_thr):
    C = ING["table_C_basis_reconciliation_staging"]
    frbny = float(C["frbny_leg"]["change_refmonth_2023_04_to_2026_04_busd"])
    mfh = float(C["tic_official_mfh_leg"]["change_refmonth_2023_04_to_2026_04_busd"])
    slt = C["tic_official_slt_lt_leg"]
    dh = float(slt["delta_holdings_refmonth_busd"])
    valchg = float(slt["cumulative_stated_valchg_axis_busd"])
    tx = float(slt["transactions_basis_change_busd (= delta_holdings - cum_valchg, the pre-registered adjustment)"])
    cumnet = float(slt["cumulative_net_us_sales_axis_busd_context"])
    guard(r3(dh - valchg) == r3(tx), "SLT transactions-basis change does not recompute")

    raw = r3(abs(frbny - mfh))
    adj = r3(abs(frbny - tx))
    ctx_dh = r3(abs(frbny - dh))
    ctx_net = r3(abs(frbny - cumnet))
    D = C["divergences"]
    guard(raw == r3(D["raw_divergence_busd (= |FRBNY_change - TIC_official_delta_holdings(MFH basis, committed)|)"]),
          "raw divergence does not reproduce the committed staging number")
    guard(adj == r3(D["basis_adjusted_divergence_busd (= |FRBNY_par_change - TIC_official_txbasis_change(SLT LT-official)|)"]),
          "basis-adjusted divergence does not reproduce the committed staging number")
    guard(ctx_dh == r3(D["context_divergence_vs_slt_lt_delta_holdings_busd"]) and
          ctx_net == r3(D["context_divergence_vs_slt_lt_cum_net_busd"]),
          "context divergence variants do not reproduce the committed staging numbers")

    if adj <= art_thr:
        label, sentence = "TENSION-ARTIFACT", verdict_artifact(adj, art_thr, real_thr)
    elif adj >= real_thr:
        label, sentence = "TENSION-REAL", verdict_real(adj, art_thr, real_thr)
    else:
        label, sentence = "PARTIAL", verdict_partial(adj, art_thr, real_thr)

    residual_material = adj > art_thr
    live = None
    if label in ("TENSION-REAL", "PARTIAL") and residual_material:
        live = ("official custody leaving the Fed at scale is structurally live in-window and bears on "
                "Part 1's interpretation: {} $bn of the FRBNY official-custody decline is unexplained by "
                "the stated valuation adjustment, and since FRBNY custody is a subset of TIC official "
                "(officials can custody outside the Fed), a real residual is custody RELOCATION away from "
                "the Fed -- exactly the migration channel Part 1 bounds".format(m3(adj)))

    h41_fn = q_extract(r'> "(Includes securities and U\.S\. Treasury STRIPS at face value[^"]*)"',
                       BASIS_TEXT, "H.4.1 Table 1A footnote 1 (face value)")
    faq10a = q_extract(r'"(Differences in valuation: The custody holdings at FRBNY are reported at face value\.[^"]*)"',
                       BASIS_TEXT, "TIC FAQ 10a valuation passage")
    mfh_val = q_extract(r'> "(Valuation of securities\.[^"]*)"', BASIS_TEXT,
                        "MFH methodology 'Valuation of securities' paragraph")
    m_sup = re.search(r"The .slt_table1\.html.[^\n]*slt2d_history\.", SECB_TEXT)
    guard(m_sup is not None, "slt2d-supersession notice not found in tic_secb_live_extracted.txt")

    return {
        "legs (staged in RDTF_ingredients.json table_C_basis_reconciliation_staging; reproduced here)": {
            "frbny_face_value_custody_change_busd": r3(frbny),
            "frbny_basis_quote_verbatim (H.4.1 Table 1A footnote 1)": h41_fn,
            "tic_mfh_official_delta_holdings_busd (estimated market value, hybrid bills-at-face)": r3(mfh),
            "tic_basis_quote_verbatim (TIC FAQ 10a)": faq10a,
            "mfh_hybrid_basis_quote_verbatim (MFH methodology note)": mfh_val,
            "slt_lt_official_delta_holdings_busd": r3(dh),
            "slt_lt_official_cumulative_stated_valchg_busd": r3(valchg),
            "slt_lt_official_transactions_basis_change_busd (= delta_holdings - cum_valchg)": r3(tx),
            "SOURCE": "build/reserve/RDTF_ingredients.json table_C_basis_reconciliation_staging.{frbny_leg,tic_official_mfh_leg,tic_official_slt_lt_leg}; quotes from build/reserve/RDTF_basis_quotes.md",
        },
        "divergences_busd": {
            "raw (= |FRBNY_change - MFH_official_delta_holdings|)": raw,
            "basis_adjusted (= |FRBNY_par_change - SLT_LT_official_txbasis_change|)": adj,
            "context_vs_slt_lt_delta_holdings": ctx_dh,
            "context_vs_slt_lt_cumulative_net_sales": ctx_net,
        },
        "verdict": {"label": label, "sentence": sentence,
                    "rule": "TENSION-ARTIFACT iff <= {a}; TENSION-REAL iff >= {r}; PARTIAL between (thresholds parsed from RDTF_prediction.md)".format(a=m3(art_thr), r=m3(real_thr)),
                    "residual_busd (official custody change unexplained by the stated valuation adjustment)": adj,
                    "residual_material": bool(residual_material)},
        "structurally_live_statement (REQUIRED by the pre-registration for PARTIAL/REAL with a material residual)": live,
        "carried_plainly": {
            "i_universe_switch": ("the adjustment simultaneously switches universe: the raw divergence uses the "
                                  "MFH official leg ({} $bn; total UST INCLUDING bills, hybrid basis) while the "
                                  "adjusted divergence uses the SLT LT-official leg ({} $bn; LONG-TERM only, "
                                  "market value with a stated valchg column) -- the bills gap is a stated limit "
                                  "of the reconciliation; context variants carried: {} (vs SLT delta-holdings) "
                                  "and {} (vs SLT cumulative net sales)"
                                  ).format(s1(mfh), s3(dh), m3(ctx_dh), m3(ctx_net)),
            "ii_input_path_friction": ("the pre-registration referenced 'the on-disk slt2d/official rows'; the "
                                       "publisher's 03-31-2023 notice superseded the slt2d files -- verbatim: '"
                                       + norm_ws(m_sup.group(0)).strip() + "' -- and the official valchg used here "
                                       "is the SLT tables' Of-Which-Foreign-Official line (country code 99990); "
                                       "disclosed, method unchanged"),
            "iii_sign_structure": ("FRBNY custody FELL {} while SLT LT-official transactions-basis FELL {} and "
                                   "MFH official ROSE {}: what converges under the adjustment is the two DECLINE "
                                   "legs (FRBNY par vs SLT tx-basis); the {} residual and the MFH contrast are "
                                   "STATED, not reconciled").format(s3(frbny), s3(tx), s1(mfh), m3(adj)),
        },
        "perimeter_fact_riding": "FRBNY custody is a subset of TIC official (officials can custody outside the Fed): a real residual is custody relocation away from the Fed, the migration channel Part 1 bounds",
    }, label, adj, raw, frbny, mfh, tx, dh, valchg, live, ctx_dh, ctx_net


# ---------------------------------------------------------------------------
# 5. Result payload
# ---------------------------------------------------------------------------

def build_payload():
    cap_obj, dn_obj, cap446, dnonus = read_constants()
    thr_obj, thr, art_thr, real_thr = parse_thresholds(cap446)
    (p1, m_hi_global, branch, interval, loco, sum_g, sum4_g, sum_n, grp_g,
     m_wo, br_wo, relabel, plain) = part1(cap446, dnonus, thr)
    (p2, p2_label, adj, raw, frbny, mfh, tx, dh, valchg, live,
     ctx_dh, ctx_net) = part2(art_thr, real_thr)

    payload = {
        "artifact": ("RDTF_result (RDT-F Phase 2 ASSEMBLY: Part 1 route-robust global migration ceiling on the "
                     "grounded custody-center set, verdict on the overstating-safe GROSS basis; Part 2 "
                     "custody-basis reconciliation verdict; branch labels rendered mechanically from the "
                     "pre-registered thresholds)"),
        "establishment": ("NOT ESTABLISHED -- output of RDTF_recompute.py; every number and label below is an "
                          "OUTPUT, not established, until build/reserve/RDTF_verify.json exists with "
                          "all_pass=true AND the human gate reviews this stage"),
        "contract": "build/reserve/RDTF_prediction.md (committed 6701b5c; pre-registered constructions, windows, thresholds, branch mapping, flipped guard)",
        "no_date_no_probability_no_currency_guess": "no breaking-point date, no probability, no destination-currency guess appears in this artifact or the amendment; the k1 wall stands",
        "windows": ING["windows"],
        "constants_read_not_hardcoded": {"cap_446p493": cap_obj, "delta_nonus_494p977": dn_obj},
        "thresholds_parsed": thr_obj,
        "part1_route_robust_ceiling": p1,
        "part2_basis_reconciliation": p2,
        "flipped_guard (carried)": {
            "DRAMATIZE": "no grounded center is omitted (the without-group figure is a labelled sensitivity, and the branch does not change without the group); the verdict is rendered on gross, never on net",
            "ZERO": "the min() against China's per-class gross decline zeroes accretion in classes China never sold (honored by construction in every center and in the group construction); beneficial-owner jurisdictions enter only through the publisher-named GROUP, never individually",
        },
        "inputs_sha256": INPUTS_SHA,
        "self_check": {
            "belu4_sum_crossfoots_staging": True,
            "cap_binds_and_ceiling_vacuous": bool(m_hi_global == r3(cap446)),
            "branch_rendered_mechanically": branch in ("MINOR-ROBUST", "FORK-REOPENED"),
            "loco_full_table_present": len(loco) == 5,
            "part2_divergences_reproduce_staging": True,
            "structurally_live_statement_present_iff_required": bool(
                (live is not None) == (p2_label in ("TENSION-REAL", "PARTIAL") and adj > art_thr)),
            "verdict_on_gross_never_net": True,
            "no_date_no_probability_no_currency_guess": True,
        },
    }
    ctx = dict(cap446=cap446, dnonus=dnonus, thr=thr, m_hi_global=m_hi_global,
               branch=branch, interval=interval, loco=loco, sum_g=sum_g,
               sum4_g=sum4_g, sum_n=sum_n, grp_g=grp_g, m_wo=m_wo, br_wo=br_wo,
               relabel=relabel, plain=plain, p2_label=p2_label, adj=adj, raw=raw,
               frbny=frbny, mfh=mfh, tx=tx, dh=dh, valchg=valchg, live=live,
               ctx_dh=ctx_dh, ctx_net=ctx_net, art_thr=art_thr, real_thr=real_thr,
               p1=p1)
    return payload, ctx


# ---------------------------------------------------------------------------
# 6. Part 3 -- the object amendment (insert-only; strip-and-reinsert; precedent)
# ---------------------------------------------------------------------------

MARK_BEGIN = "<!-- RDTF-AMEND:BEGIN"
MARK_END = "<!-- RDTF-AMEND:END"


def strip_amendment(text):
    out, skip = [], False
    for line in text.splitlines(keepends=True):
        s = line.lstrip()
        if s.startswith(MARK_BEGIN):
            guard(not skip, "nested RDTF-AMEND BEGIN")
            skip = True
            continue
        if s.startswith(MARK_END):
            guard(skip, "RDTF-AMEND END without BEGIN")
            skip = False
            continue
        if not skip:
            out.append(line)
    guard(not skip, "unterminated RDTF-AMEND block")
    return "".join(out)


def part1_object_fragment(ctx):
    if ctx["branch"] == "FORK-REOPENED":
        guard(ctx["m_hi_global"] > ctx["thr"], "FORK-REOPENED object text with M <= threshold")
        return (
            f"**MECHANICAL BRANCH: FORK-REOPENED** — M_hi_global {m3(ctx['m_hi_global'])} > 0.25 × "
            f"{m3(ctx['cap446'])} = {m3(ctx['thr'])}: the route-robust gross ceiling does not sustain MINOR. "
            f"RDT-E's MIGRATION-MINOR is hereby RE-LABELLED **{ctx['relabel']}**, not robust: its bound "
        )
    guard(ctx["m_hi_global"] <= ctx["thr"], "MINOR-ROBUST object text with M > threshold")
    return (
        f"**MECHANICAL BRANCH: MINOR-ROBUST** — M_hi_global {m3(ctx['m_hi_global'])} ≤ 0.25 × "
        f"{m3(ctx['cap446'])} = {m3(ctx['thr'])}: RDT-E's MINOR survives its strongest route-robust test "
        f"on the overstating-safe basis and is re-rendered **{ctx['relabel']}**: its bound "
    )


def part2_object_fragment(ctx):
    lab = ctx["p2_label"]
    if lab == "PARTIAL":
        guard(ctx["art_thr"] < ctx["adj"] < ctx["real_thr"], "PARTIAL object text out of range")
        head = (f"**BASIS VERDICT: PARTIAL** — the stated valuation adjustment closes most but not all of the "
                f"raw {m3(ctx['raw'])} $bn divergence: basis-adjusted divergence "
                f"|{s3(ctx['frbny'])} − ({s3(ctx['tx'])})| = {m3(ctx['adj'])} $bn, between the pre-registered "
                f"{m3(ctx['art_thr'])} (ARTIFACT) and {m3(ctx['real_thr'])} (REAL) thresholds — "
                f"**{m3(ctx['adj'])} $bn of official custody change is unexplained by the stated valuation "
                f"adjustment**. ")
    elif lab == "TENSION-REAL":
        guard(ctx["adj"] >= ctx["real_thr"], "REAL object text out of range")
        head = (f"**BASIS VERDICT: TENSION-REAL** — basis-adjusted divergence {m3(ctx['adj'])} $bn ≥ "
                f"{m3(ctx['real_thr'])}: a quantified residual of official custody leaving the Fed, "
                f"unattributed. ")
    else:
        guard(ctx["adj"] <= ctx["art_thr"], "ARTIFACT object text out of range")
        head = (f"**BASIS VERDICT: TENSION-ARTIFACT** — basis-adjusted divergence {m3(ctx['adj'])} $bn ≤ "
                f"{m3(ctx['art_thr'])}: the raw {m3(ctx['raw'])} $bn divergence collapses under the stated "
                f"valuation adjustment. ")
    if ctx["live"] is not None:
        guard(lab in ("PARTIAL", "TENSION-REAL") and ctx["adj"] > ctx["art_thr"],
              "structurally-live statement attached outside its pre-registered condition")
        head += ("Per the pre-registration this requires the plain statement: **official custody leaving the "
                 "Fed at scale is structurally live in-window and bears on Part 1's interpretation** — since "
                 "FRBNY custody ⊂ TIC official, a real residual is custody RELOCATION away from the Fed, "
                 "exactly the migration channel Part 1 bounds. ")
    return head


def build_blocks(payload, ctx, post_rdte_sha):
    p1 = ctx["p1"]
    guard(ctx["branch"] == "FORK-REOPENED" and ctx["p2_label"] == "PARTIAL",
          "the assembled k3 block below narrates the FORK-REOPENED + PARTIAL landing; "
          "another landing computed -- extend the narration for it before amending")
    guard(ctx["br_wo"] == ctx["branch"], "without-group sensitivity text says the branch is group-independent")
    guard(all(row["branch_implied"] == ctx["branch"] for row in ctx["loco"]),
          "LOCO-robust wording used but a drop flips the branch")
    vals = {c: p1["per_center_ceilings_busd (verdict axis 2023-05..2026-04; full window 2023-02..2026-04 as context)"][c]["M_gross_busd (VERDICT basis)"] for c in BELU4}
    nets = {c: p1["per_center_ceilings_busd (verdict axis 2023-05..2026-04; full window 2023-02..2026-04 as context)"][c]["M_windownet_busd (tighter, DISPUTED sensitivity)"] for c in BELU4}
    grp_net = p1["per_center_ceilings_busd (verdict axis 2023-05..2026-04; full window 2023-02..2026-04 as context)"]["Caribbean banking centers (GROUP, constructed -- rule (b))"]["M_windownet_busd (tighter, DISPUTED sensitivity)"]

    loco_rows = "".join(
        f"| {row['dropped_center']} | {m3(row['M_center_gross_busd'])} | "
        f"{m3(row['sum_remaining_gross_busd'])} | {m3(row['M_hi_global_without_it_busd'])} | "
        f"{row['branch_implied']} |\n" for row in ctx["loco"])

    block_k3 = (
        "<!-- RDTF-AMEND:BEGIN k3-route-robust-ceiling -->\n"
        f"**RDT-F annotation (the route-robust migration ceiling — the BE/LU-only bound superseded, "
        f"`RDTF_result.json`):** RDT-E bounded ONE custody route (pooled BE/LU); RDT-F recomputes the ceiling "
        f"over the DERIVED grounded custody-center set — Belgium, Luxembourg, Switzerland, United Kingdom, plus "
        f"the TIC publisher grouping “Caribbean banking centers” — every entry carrying its verbatim "
        f"publisher grounding quote (`RDTF_centers_manifest.json` / `RDTF_centers_provenance.md`; the group's "
        f"naming is GROUP-LEVEL only, from the 2012-era TIC methodology documents — a MEDIUM-confidence entry "
        f"whose caveat rides this result and is never used to drop the group). Verdict basis: the pre-registered "
        f"OVERSTATING-SAFE GROSS construction (window-net beside it, never the verdict). Per-center gross "
        f"ceilings on the verdict axis: Belgium {m3(vals['Belgium'])}, Luxembourg {m3(vals['Luxembourg'])}, "
        f"Switzerland {m3(vals['Switzerland'])}, United Kingdom {m3(vals['United Kingdom'])}, "
        f"Caribbean-banking-centers group {m3(ctx['grp_g'])} $bn — the group constructed at GROUP level "
        f"(per class: min(China gross decline, Σ member gross inflows)) from the publisher-defined member lines "
        f"Bahamas/Bermuda/British Virgin Islands/Cayman Islands/Curacao/Panama, because the SLT “Total "
        f"Caribbean” aggregate's membership DIFFERS from the publisher's group definition (Panama sits "
        f"outside the SLT aggregate in every month while at least seven non-member Caribbean lines sit inside "
        f"it; Netherlands Antilles has no line on the axis — its publisher-restated successors Bonaire/Sint "
        f"Eustatius/Saba and Sint Maarten have no lines either, and Curacao's line is included). "
        f"Σ_grounded gross = {m3(ctx['sum_g'])} $bn (window-net {m3(ctx['sum_n'])} as the tighter, DISPUTED "
        f"sensitivity; without the group: {m3(ctx['sum4_g'])}). **M_hi_global = min({m3(ctx['sum_g'])}, "
        f"{m3(ctx['cap446'])}) = {m3(ctx['m_hi_global'])} $bn — the cap BINDS and the ceiling is VACUOUS** "
        f"(pre-registered: the ceiling cannot exceed the net decline it explains; computed, not asserted — the "
        f"four-jurisdiction sum alone, {m3(ctx['sum4_g'])}, already exceeds the cap, so neither the branch nor "
        f"the ceiling depends on the MEDIUM-confidence group entry). "
        + part1_object_fragment(ctx) +
        f"M_hi {m3(RDTE['combination_mechanical']['M_hi_busd'])}, ΔnonUS-true ∈ "
        f"[{m3(RDTE['interval_delta_nonus_true_busd']['interval'][0])}, "
        f"{m3(RDTE['interval_delta_nonus_true_busd']['interval'][1])}] survives ONLY on the assumption that "
        f"custody migration ran solely through Euroclear/Clearstream (BE/LU); it stays in this object as the "
        f"route-specific bound. **Route-robust interval: ΔnonUS-true ∈ [{m3(ctx['interval'][0])}, "
        f"{m3(ctx['interval'][1])}] $bn — NEARLY UNINFORMATIVE, stated plainly:** "
        f"{ctx['plain']}. Leave-one-center-out (mandatory; full table): dropping ANY single grounded center "
        f"leaves the remaining sum above the cap, so **{ctx['branch']} is LOCO-ROBUST**.\n"
        f"\n"
        f"| dropped center | its M_gross | Σ remaining | M_hi_global without it | branch implied |\n"
        f"|---|---|---|---|---|\n"
        + loco_rows +
        f"\n"
        + part2_object_fragment(ctx) +
        f"Carried plainly with the basis verdict: (i) the adjustment switches universe (MFH total-UST-incl-bills "
        f"official {s1(ctx['mfh'])} vs SLT LT-only official Δholdings {s3(ctx['dh'])}, cumulative stated valchg "
        f"{s3(ctx['valchg'])}, transactions-basis {s3(ctx['tx'])}) — the bills gap is a stated limit, context "
        f"variants {m3(ctx['ctx_dh'])} and {m3(ctx['ctx_net'])} carried; (ii) the sign structure: FRBNY custody "
        f"FELL {s3(ctx['frbny'])} while SLT LT-official transactions-basis FELL {s3(ctx['tx'])} and MFH official "
        f"ROSE {s1(ctx['mfh'])} — what converges under the adjustment is the two DECLINE legs; the residual and "
        f"the MFH contrast are stated, not reconciled. Pool caveat and k1 wall ride everywhere. No date, no "
        f"probability, no currency guess.\n"
        "<!-- RDTF-AMEND:END k3-route-robust-ceiling -->\n"
    )

    block_hazard = (
        "<!-- RDTF-AMEND:BEGIN hazard-route-robust -->\n"
        f"**RDT-F annotation on the perimeter fork, route-robustly (`RDTF_result.json`):** the fork RDT-E "
        f"bounded on the BE/LU route is **{ctx['branch']}** over the full grounded custody-center set "
        f"(BE/LU/CH/UK + the Caribbean-banking-centers group): the route-robust gross ceiling is VACUOUS "
        f"(M_hi_global = {m3(ctx['m_hi_global'])} $bn, the cap itself), so route-robust data cannot separate "
        f"true departure from custody migration — ΔnonUS-true ∈ [{m3(ctx['interval'][0])}, "
        f"{m3(ctx['interval'][1])}] $bn, and the MIGRATION-MINOR label above holds only as "
        f"**{ctx['relabel']}**. The basis check lands **{ctx['p2_label']}**: {m3(ctx['adj'])} $bn of official "
        f"custody leaving the Fed is unexplained by the stated valuation adjustment — official custody leaving "
        f"the Fed at scale is structurally live in-window. LOCO-robust; window-net beside, never the verdict. "
        f"The destination currency stays UNDETERMINED (the k1 wall); the pool caveat rides. Ledger descriptor "
        f"on the pre-registered axis; not a forecast, no date, no probability.\n"
        "<!-- RDTF-AMEND:END hazard-route-robust -->\n"
    )

    block_lim = (
        "<!-- RDTF-AMEND:BEGIN limitations-rdtf -->\n"
        f"   - **RDT-F caveats on the route-robust ceiling and the basis verdict (`RDTF_result.json`):** "
        f"(i) the {ctx['branch']} branch is rendered on the pre-registered overstating-safe GROSS basis; the "
        f"window-net construction (Σ {m3(ctx['sum_n'])} $bn; RDT-E's construction) is tighter but DISPUTED "
        f"(within-window netting can hide migration) and is never the verdict — on gross, 36-month sums of "
        f"positive monthly inflows are large for every major financial center, which is exactly why the "
        f"ceiling saturates its cap and goes VACUOUS rather than informative; (ii) the Caribbean-banking-centers "
        f"entry is MEDIUM-confidence (group-level naming only, 2012-era TIC methodology vintage, "
        f"beneficial-owner-tagged members admitted only through the publisher-named GROUP under the zero-guard) "
        f"— reported, never used to drop the group; the branch and ceiling are IDENTICAL without it "
        f"(without-group Σ {m3(ctx['sum4_g'])} > cap {m3(ctx['cap446'])}); membership construction and the "
        f"SLT-vs-publisher membership comparison are verbatim in `RDTF_result.json`; (iii) the basis "
        f"reconciliation switches universe (MFH total UST incl. bills vs SLT LT-only) — the bills gap is a "
        f"stated limit, context variants {m3(ctx['ctx_dh'])}/{m3(ctx['ctx_net'])} $bn carried; (iv) input-path "
        f"friction: the pre-registered slt2d rows were superseded by the slt_table# files per the publisher's "
        f"2023-03-31 notice; the official valchg used is the SLT tables' Of-Which-Foreign-Official line (99990) "
        f"— disclosed, method unchanged; (v) the {m3(ctx['adj'])} $bn residual is a quantified unknown: "
        f"ambiguous between price/coverage effects the stated valchg column does not capture and genuine "
        f"official custody relocation away from the Fed — stated, not resolved, and the MFH-official RISE "
        f"({s1(ctx['mfh'])}) against both decline legs is stated, not reconciled; (vi) the k1 wall and the "
        f"pool caveat ride every interval and label above; no date, no probability, no currency guess.\n"
        "<!-- RDTF-AMEND:END limitations-rdtf -->\n"
    )

    block_prov = (
        "<!-- RDTF-AMEND:BEGIN provenance -->\n"
        f"**RDT-F amendment provenance:** this file was further amended by RDT-F (pre-registered in "
        f"`build/reserve/RDTF_prediction.md`, committed 6701b5c). All RDT-F content is delimited by RDTF-AMEND "
        f"marker comments and every number in it is computed by `build/reserve/RDTF_recompute.py` from "
        f"`RDTF_ingredients.json`/`RDTF_ingredients_panel.parquet`, `RDTF_centers_manifest.json`, "
        f"`RDTF_basis_quotes.md`, `RDTE_prediction.md` (threshold parse), `RDTE_result.json`/`RDTE_verify.json`, "
        f"`RDTC_class_flows.json` and `RDTD_result.json` — stripping the RDTF-AMEND blocks reproduces the "
        f"post-RDT-E object byte-for-byte (base sha256 {post_rdte_sha}, as recorded in `RDTE_verify.json`). "
        f"`RDT_recompute.py`, `RDTB_recompute.py`, `RDTC_recompute.py`, `RDTD_recompute.py`, "
        f"`RDTD_fragility_recompute.py`, `RDTE_ingredients_recompute.py`, `RDTE_recompute.py` and "
        f"`RDTF_ingredients_recompute.py` are NOT modified; the RDTB-, RDTC-, RDTD- and RDTE-AMEND blocks are "
        f"untouched; `RDTF_verify.json` carries the further-amended object's byte-reproduction. No composite is "
        f"recomputed (k1 unchanged).\n"
        "<!-- RDTF-AMEND:END provenance -->\n"
    )

    return [
        ("<!-- RDTE-AMEND:END k3-migration-bound -->", block_k3),
        ("<!-- RDTE-AMEND:END hazard-migration-bound -->", block_hazard),
        ("<!-- RDTE-AMEND:END limitations-rdte -->", block_lim),
        ("<!-- RDTE-AMEND:END provenance -->", block_prov),
    ]


def amend(base, blocks):
    lines = base.splitlines(keepends=True)
    anchors = {a: 0 for a, _ in blocks}
    out = []
    for line in lines:
        out.append(line)
        key = line.rstrip("\n")
        for a, block in blocks:
            if key == a:
                out.append(block)
                anchors[a] += 1
    for a, n in anchors.items():
        guard(n == 1, f"anchor {a!r} matched {n} times (need exactly 1)")
    return "".join(out)


def amend_object(payload, ctx):
    post_rdte_sha = RDTEV["outputs_sha256"]["RDT_breaking_point_object.md"]
    current = OBJECT_MD.read_text(encoding="utf-8")
    base = strip_amendment(current)
    base_sha = hashlib.sha256(base.encode("utf-8")).hexdigest()
    base_ok = base_sha == post_rdte_sha
    guard(base_ok, f"stripped base sha {base_sha} != post-RDT-E sha {post_rdte_sha} -- refusing to amend a wrong base")
    blocks = build_blocks(payload, ctx, post_rdte_sha)
    amended = amend(base, blocks)
    repro = (strip_amendment(amended) == base) and (amend(strip_amendment(amended), blocks) == amended)
    OBJECT_MD.write_text(amended, encoding="utf-8")
    rewritten_ok = OBJECT_MD.read_text(encoding="utf-8") == amended
    return bool(repro and rewritten_ok), base_ok, base_sha, post_rdte_sha


# ---------------------------------------------------------------------------

def main():
    payload1, ctx1 = build_payload()
    payload2, _ = build_payload()
    s1_ = json.dumps(payload1, indent=1, ensure_ascii=False, sort_keys=True)
    s2_ = json.dumps(payload2, indent=1, ensure_ascii=False, sort_keys=True)
    two_pass = s1_ == s2_
    guard(two_pass, "two independent payload builds differ -- non-deterministic build")
    OUT_RESULT.write_text(s1_ + "\n", encoding="utf-8")
    result_repro = OUT_RESULT.read_text(encoding="utf-8") == s1_ + "\n"

    obj_repro, base_ok, base_sha, post_rdte_sha = amend_object(payload1, ctx1)

    flags = {
        "result_two_pass_payload_identical": bool(two_pass),
        "result_byte_reproduction": bool(result_repro),
        "ingredients_sha256_matches_tasked_pin": bool(ING_SHA == EXPECTED_ING_SHA),
        "amended_object_byte_reproduction (strip-and-reinsert fixed point)": bool(obj_repro),
        "stripped_base_matches_post_rdte_sha256": bool(base_ok),
    }
    all_pass = all(flags.values())
    verify = {
        "purpose": ("verifier artifact for RDT-F Phase 2 ASSEMBLY: records that RDTF_result.json and the "
                    "amended RDT_breaking_point_object.md were regenerated deterministically from the committed "
                    "inputs by build/reserve/RDTF_recompute.py; that the committed RDTF_ingredients.json matches "
                    "the tasked sha pin; and that stripping the RDTF-AMEND blocks reproduces the post-RDT-E "
                    "object byte-for-byte against the sha recorded in RDTE_verify.json (checked BEFORE amending). "
                    "Until all_pass=true AND the human gate reviews this stage, every number in these outputs is "
                    "an OUTPUT, not established."),
        "no_date_no_probability_no_currency_guess": ("no date, no probability, and no destination-currency "
                                                     "guess anywhere in the RDT-F outputs"),
        "network": "none",
        "inputs_sha256": INPUTS_SHA,
        "outputs_sha256": {
            "RDTF_result.json": sha256_file(OUT_RESULT),
            "RDT_breaking_point_object.md": sha256_file(OBJECT_MD),
        },
        "match_flags": flags,
        "post_rdte_object_sha256": {
            "stripped_base_recomputed_here": base_sha,
            "recorded_in_RDTE_verify_json": post_rdte_sha,
            "note": ("RDTE_verify.json's object sha256 is the RDT-F amendment base; the further-amended "
                     "object's byte-reproduction is carried here"),
        },
        "all_pass": bool(all_pass),
    }
    OUT_VERIFY.write_text(json.dumps(verify, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                          encoding="utf-8")
    print(json.dumps({"all_pass": all_pass, **flags}, indent=1))
    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
