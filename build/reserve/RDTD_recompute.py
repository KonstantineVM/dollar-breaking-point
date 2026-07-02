#!/usr/bin/env python3
"""RDT-D Parts 0+4 -- assemble the identity, apply the mechanical SDDS verdict,
amend the breaking-point object.

Deterministic recompute. Regenerates:
  1. build/reserve/RDTD_result.json          -- the identity per custody variant, the
     fragility integration, the SDDS ledger + netting rule, the mechanical verdict
     (pre-registered 0.5 thresholds), the expectation evaluation, the honest tensions.
  2. build/reserve/RDT_breaking_point_object.md -- insert-only RDTD-AMEND blocks
     (stripping them reproduces the post-RDT-C object byte-for-byte, checked against
     the sha256 recorded in RDTC_verify.json).
  3. build/reserve/RDTD_verify.json          -- byte-reproduction flags: result
     two-pass + rewrite; sandboxed re-run of the UNMODIFIED RDTD_fragility_recompute.py
     byte-reproducing RDTD_fragility.json; sdds-series recompute-from-csv match;
     amended-object fixed point; stripped-base-matches-post-RDT-C-sha; all_pass.

Contract: build/reserve/RDTD_prediction.md (pre-registered BEFORE the build).
Every number is computed here from committed on-disk inputs; nothing hardcoded.
Every branch-specific template string is ASSERTION-GUARDED: regeneration on changed
data must fail loudly, never misdescribe (the RDT-C GATE lesson).

No network. No date, no probability, no currency guess (the k1 wall stands).

NOT ESTABLISHED: the outputs are estimation outputs pending their verifier scenario
(orchestrator re-run of this script reproducing them byte-for-byte, and the RDT-D gate).
"""

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent          # <repo>/build/reserve
ROOT = HERE.parents[1]                          # <repo>

PREDICTION = HERE / "RDTD_prediction.md"
FRAGILITY_JSON = HERE / "RDTD_fragility.json"
FRAGILITY_SCRIPT = HERE / "RDTD_fragility_recompute.py"
SDDS_CSV = HERE / "rdtd_sdds_series.csv"
SDDS_MANIFEST = HERE / "rdtd_sdds_manifest.json"
POOL_MD = HERE / "rdtd_pool_determination.md"
SAFE_CSV = HERE / "rdtc_safe_totals.csv"
PANEL = HERE / "RDTC_class_panel.parquet"
FLOWS = HERE / "RDTC_class_flows.json"
RDTC_RESULT = HERE / "RDTC_result.json"
RDTC_VERIFY = HERE / "RDTC_verify.json"
SLT_TABLE3 = HERE / "rdt_evidence" / "tic" / "slt_table3.txt"

OBJECT_MD = HERE / "RDT_breaking_point_object.md"
OUT_RESULT = HERE / "RDTD_result.json"
OUT_VERIFY = HERE / "RDTD_verify.json"

CLASSES = ["treasury_lt", "agency_lt", "corp_other_bonds_lt", "equity_lt"]
VARIANTS = {
    "china_alone": ["China, Mainland"],
    "china_belgium_luxembourg": ["China, Mainland", "Belgium", "Luxembourg"],
}
THRESHOLD_FRAC = 0.5          # pre-registered verdict threshold; asserted vs contract
FRAG_THRESHOLD_FRAC = 0.25    # pre-registered fragility threshold; echoed from Part 1

# fragility-sandbox inputs = exactly the committed inputs of RDTD_fragility.json
FRAG_SANDBOX_INPUTS = [
    "build/reserve/RDTC_class_panel.parquet",
    "build/reserve/RDTC_class_flows.json",
    "build/reserve/RDTD_prediction.md",
    "build/reserve/rdt_evidence/tic/mfh.txt",
    "build/reserve/rdt_evidence/tic/tic_seca_page.html",
    "build/reserve/rdtb_evidence/shl2025r_extracted.txt",
]
# aux file for the sandbox mirror only: NOT a computation input (hence not in the fragility
# inputs_sha256); the fragility script existence-guards its Part-2 retention statement and
# records this file's sha in attribution_mechanism.tic_faq_note
FRAG_SANDBOX_AUX = ["build/reserve/rdtd_evidence/tic_faq2.html"]


def guard(cond, msg):
    """Assertion guard for every branch-specific template string.

    Regeneration on changed data must FAIL LOUDLY here, never misdescribe."""
    if not cond:
        raise AssertionError(f"TEMPLATE GUARD FAILED (refusing to write misdescribing prose): {msg}")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def r3(x) -> float:
    return round(float(x) + 0.0, 3)


def f3(x) -> str:
    """signed 3-decimal busd string"""
    return f"{x:+.3f}"


def p3(x) -> str:
    """plain 3-decimal busd string"""
    return f"{x:.3f}"


def month_range(start: str, end: str):
    out = []
    y, m = int(start[:4]), int(start[5:7])
    ye, me = int(end[:4]), int(end[5:7])
    while (y, m) <= (ye, me):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


# ---------------------------------------------------------------------------
# input legs
# ---------------------------------------------------------------------------

def contract_clauses():
    t = PREDICTION.read_text(encoding="utf-8")
    clauses = {
        "verdict_axis": "2023-05..2026-04" in t,
        "identity_form": "ΔNonUS ≡ ΔTotal(ex-gold) − ΔH_us_LT" in t,
        "threshold_0_5": "0.5 × ΔNonUS" in t,
        "deposits_positivity_guard": "(and ΔNonUS > 0)" in t,
        "netting_rule": "`Δsec_SDDS − ΔH_us_LT`" in t,
        "band_rule": "[active − |G|, active + |G|]" in t,
        "band_honest": "band-honest OTHER-OR-SUPPRESSED" in t,
        "primary_expectation": "OTHER-OR-SUPPRESSED or MIXED-COMPOSITION" in t,
    }
    for k, v in clauses.items():
        guard(v, f"pre-registered clause '{k}' not found verbatim in RDTD_prediction.md")
    return clauses


def load_windows():
    flows = json.load(open(FLOWS, encoding="utf-8"))
    w = flows["windows"]["recent_3y_verdict_axis"]
    guard(w["start"] == "2023-05" and w["end"] == "2026-04",
          "verdict axis in RDTC_class_flows.json is not 2023-05..2026-04")
    ref = flows["ledgers"]["recent_3y_verdict_axis"]["china_alone"]["holdings_reference_month"]
    guard(ref == "2023-04", "holdings reference month is not 2023-04")
    return flows, w["start"], w["end"], ref


def safe_delta_total(start, end, ref):
    fx = {}
    with open(SAFE_CSV, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            fx[row["month"]] = float(row["fx_reserves_usd_bn"])
    for m in (start, end, ref):
        guard(m in fx, f"rdtc_safe_totals.csv missing month {m}")
    d_committed = r3(fx[end] - fx[start])      # RDT-C committed convention (endpoint - start-month value)
    d_refconv = r3(fx[end] - fx[ref])          # reference-month convention, stated beside
    rc = json.load(open(RDTC_RESULT, encoding="utf-8"))
    ax = rc["branch_a_closure_test"]["windows"]["recent_3y_verdict_axis"]
    guard(r3(ax["delta_bn"]) == d_committed,
          f"SAFE ex-gold delta recomputed {d_committed} != committed RDTC {ax['delta_bn']}")
    guard(r3(ax["reference_month_convention"]["delta_bn"]) == d_refconv,
          "SAFE reference-month-convention delta does not reconcile to committed RDTC value")
    return d_committed, d_refconv, fx[start], fx[end]


def panel_terms(start, end, ref, flows):
    """Recompute active, dH_us_LT, V_us per custody variant from the committed panel;
    reconcile EXACTLY (3dp) to the committed RDT-C ledgers and the fragility artifact."""
    df = pd.read_parquet(PANEL)
    guard(set(CLASSES) <= set(df["asset_class"].unique()),
          "panel asset classes changed")
    axis = set(month_range(start, end))
    frag = json.load(open(FRAGILITY_JSON, encoding="utf-8"))
    out = {}
    for variant, countries in VARIANTS.items():
        sub = df[df["country"].isin(countries) & df["asset_class"].isin(CLASSES)]
        a = sub[sub["month"].isin(axis)]
        for c in countries:
            for cl in CLASSES:
                n = a[(a["country"] == c) & (a["asset_class"] == cl)]["active_musd"].notna().sum()
                guard(n == len(axis), f"{variant}/{c}/{cl}: {n} != {len(axis)} active months on axis")
        active_musd = float(a["active_musd"].sum())
        pos_end = sub[sub["month"] == end]["pos_musd"]
        pos_ref = sub[sub["month"] == ref]["pos_musd"]
        guard(len(pos_end) == len(countries) * len(CLASSES) and pos_end.notna().all(),
              f"{variant}: incomplete positions at {end}")
        guard(len(pos_ref) == len(countries) * len(CLASSES) and pos_ref.notna().all(),
              f"{variant}: incomplete positions at reference month {ref}")
        dH_musd = float(pos_end.sum()) - float(pos_ref.sum())
        active = r3(active_musd / 1000.0)
        dH = r3(dH_musd / 1000.0)
        v_us = r3((dH_musd - active_musd) / 1000.0)
        # exact reconciliation to the committed RDT-C ledger
        led = flows["ledgers"]["recent_3y_verdict_axis"][variant]
        guard(r3(-active) == r3(led["residual_left_us_busd"]),
              f"{variant}: -active {r3(-active)} != committed residual_left_us_busd {led['residual_left_us_busd']}")
        x_musd = float(a[a["asset_class"] == "treasury_lt"]["active_musd"].sum())
        guard(r3(x_musd / 1000.0) == r3(led["X_ust_active_busd"]),
              f"{variant}: recomputed X(UST) != committed ledger X")
        guard(r3((active_musd - x_musd) / 1000.0) == r3(led["A_nonust_active_busd"]["total"]),
              f"{variant}: recomputed A != committed ledger A")
        # exact reconciliation to the committed fragility artifact (total LT row)
        ft = frag["G_tables"]["recent_3y_verdict_axis"][variant]["total_lt"]
        guard(active == r3(ft["active_cum_busd"]), f"{variant}: active != fragility active_cum_busd")
        guard(dH == r3(ft["delta_holdings_busd"]), f"{variant}: dH != fragility delta_holdings_busd")
        guard(v_us == r3(ft["dH_minus_active_busd"]), f"{variant}: V_us != fragility dH_minus_active_busd")
        out[variant] = {"active_busd": active, "delta_H_us_LT_busd": dH, "V_us_busd": v_us}
    return out, frag


def fragility_echo(frag):
    mf = frag["mechanical_flag"]
    flag = mf["flag"]
    guard(flag in ("RELIABLE-WITHIN-GAP", "446.5-UNRELIABLE"),
          f"unknown fragility flag {flag!r}")
    ratio = round(abs(mf["G_total_busd"]) / abs(mf["active_total_busd"]), 4)
    guard(ratio == mf["ratio_absG_over_absActive"],
          "fragility ratio does not recompute from its own G/active")
    guard((ratio > FRAG_THRESHOLD_FRAC) == (flag == "446.5-UNRELIABLE"),
          "fragility flag inconsistent with its own ratio/threshold")
    ctx = mf["context_variant_cn_be_lu"]
    ctx_ratio = round(abs(ctx["G_total_busd"]) / abs(ctx["active_total_busd"]), 4)
    guard(ctx_ratio == ctx["ratio_absG_over_absActive"],
          "CN+BE+LU context ratio does not recompute")
    return {
        "flag": flag,
        "G_total_busd": r3(mf["G_total_busd"]),
        "abs_G_total_busd": r3(mf["abs_G_total_busd"]),
        "active_total_busd": r3(mf["active_total_busd"]),
        "threshold_busd": r3(mf["threshold_busd"]),
        "ratio_absG_over_absActive": ratio,
        "context_cn_be_lu": {
            "G_total_busd": r3(ctx["G_total_busd"]),
            "active_total_busd": r3(ctx["active_total_busd"]),
            "ratio_absG_over_absActive": ctx_ratio,
            "would_trip_own_threshold": bool(ctx["would_trip_own_threshold"]),
        },
        "source": "build/reserve/RDTD_fragility.json (Part 1, committed; recomputed values cross-checked here)",
    }


def sdds_ledger(start, end, dT_committed):
    rows = {}
    with open(SDDS_CSV, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows[row["data_month"]] = row
    months = sorted(rows)
    axis_months = month_range(start, end)
    for m in axis_months:
        guard(m in rows, f"SDDS series missing axis month {m}")
    full = month_range("2015-06", "2026-05")
    guard(months == full, "SDDS series is not the full 132-month 2015-06..2026-05 panel")
    guard(len(months) == 132, "SDDS series month count != 132")
    guard(months[-1] >= end, "latest SDDS template month does not cover the axis end")

    def val(m, col):
        return float(rows[m][col])

    cols = {
        "securities": "securities_usd_bn",
        "dep_cb_bis_imf": "dep_cb_bis_imf_usd_bn",
        "dep_banks_hq_in": "dep_banks_hq_in_usd_bn",
        "dep_banks_hq_out": "dep_banks_hq_out_usd_bn",
        "other_reserve_assets": "other_reserve_assets_usd_bn",
    }
    # deltas on the RDT-C committed convention: value(end) - value(start-month), matching ΔTotal(+234.039)
    d = {k: r3(val(end, c) - val(start, c)) for k, c in cols.items()}
    d_dep_total = r3(d["dep_cb_bis_imf"] + d["dep_banks_hq_in"] + d["dep_banks_hq_out"])
    # internal identity: SDDS FX line = securities + deposits; must reproduce the committed ΔTotal(ex-gold)
    guard(r3(d["securities"] + d_dep_total) == r3(dT_committed),
          f"Δsec+Δdep {r3(d['securities'] + d_dep_total)} != committed ΔTotal(ex-gold) {dT_committed}")
    # recompute-from-csv match against the committed manifest context block
    man = json.load(open(SDDS_MANIFEST, encoding="utf-8"))
    ctx = man["context_deltas_NOT_verdict"]
    manifest_match = (
        r3(ctx["delta_securities_bn"]) == d["securities"]
        and r3(ctx["delta_dep_cb_bis_imf_bn"]) == d["dep_cb_bis_imf"]
        and r3(ctx["delta_dep_banks_hq_in_bn"]) == d["dep_banks_hq_in"]
        and r3(ctx["delta_dep_banks_hq_out_bn"]) == d["dep_banks_hq_out"]
        and r3(ctx["delta_other_reserve_assets_bn"]) == d["other_reserve_assets"]
    )
    guard(manifest_match, "SDDS deltas recomputed from csv do not match the committed manifest")
    # deposits share of the FX line, every month (the near-absence finding)
    shares = []
    for m in months:
        dep = val(m, cols["dep_cb_bis_imf"]) + val(m, cols["dep_banks_hq_in"]) + val(m, cols["dep_banks_hq_out"])
        fxl = val(m, cols["securities"]) + dep
        shares.append((100.0 * dep / fxl, m))
    smin, smin_m = min(shares)
    smax, smax_m = max(shares)
    # suppression status: a verdict input; guarded against the committed manifest finding
    findings = man["line_map_section_IA"]["structural_findings"]
    no_suppression = any("No suppression of the required Part-3 lines" in s for s in findings)
    guard(no_suppression, "manifest no-suppression finding absent -- suppression status cannot be assumed")
    blanks = man["line_map_section_IA"]["blank_or_zero_lines"]
    return {
        "axis_note": (f"SDDS covers the full verdict axis {start}..{end} (no truncation needed); "
                      f"latest published template month {months[-1]} exceeds the axis end"),
        "delta_securities_busd": d["securities"],
        "delta_dep_cb_bis_imf_busd": d["dep_cb_bis_imf"],
        "delta_dep_banks_hq_in_busd": d["dep_banks_hq_in"],
        "delta_dep_banks_hq_out_busd": d["dep_banks_hq_out"],
        "delta_deposits_total_busd": d_dep_total,
        "delta_other_reserve_assets_busd": d["other_reserve_assets"],
        "delta_convention": (f"value({end}) - value({start}), the RDT-C committed convention; "
                             f"Δsec+Δdep reproduces the committed ΔTotal(ex-gold) {f3(dT_committed)} exactly"),
        "deposits_share_of_fx_line_pct": {
            "min": round(smin, 2), "min_month": smin_m,
            "max": round(smax, 2), "max_month": smax_m,
            "n_months": len(months),
        },
        "no_suppression_of_required_lines": True,
        "blank_of_which_sub_lines": [b["line"] + " -- " + b["status"] for b in blanks],
        "manifest_match": manifest_match,
        "source": "build/reserve/rdtd_sdds_series.csv (recomputed here) + rdtd_sdds_manifest.json (cross-checked)",
    }


def st_leg(start, end, ref):
    """Short-term US leg from the on-disk SLT table (labelled ADJUSTMENT, never silently
    added/dropped). slt_table3.txt carries a by-country short-term U.S. Treasury (bill)
    POSITION column; Δposition over the axis (reference-month convention, matching ΔH_us_LT)."""
    pos = {}
    with open(SLT_TABLE3, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 10 and len(parts[2]) == 7 and parts[2][4] == "-":
                try:
                    pos[(parts[0], parts[2])] = int(parts[8])
                except ValueError:
                    continue
    needed = set(VARIANTS["china_belgium_luxembourg"])
    have = {c: ((c, ref) in pos and (c, end) in pos) for c in needed}
    if not have["China, Mainland"]:
        return {"status": "NOT-ON-DISK",
                "statement": "no China short-term position column spanning the axis found in the on-disk SLT tables"}
    out = {"status": "ON-DISK",
           "source": "build/reserve/rdt_evidence/tic/slt_table3.txt column for_st_treas_pos (short-term U.S. Treasuries)",
           "instrument_caveat": ("short-term U.S. TREASURY (bill) positions only -- no on-disk by-country "
                                 "position series exists for other US short-term instruments (agency discount "
                                 "notes, CP); bills sit near par so the position change is mostly flow"),
           "convention": f"Δposition = pos({end}) - pos({ref}) (reference-month convention, matching ΔH_us_LT)"}
    d_cn = r3((pos[("China, Mainland", end)] - pos[("China, Mainland", ref)]) / 1000.0)
    out["delta_us_st_busd"] = {"china_alone": d_cn}
    out["positions_busd"] = {"china_alone": {ref: r3(pos[("China, Mainland", ref)] / 1000.0),
                                             end: r3(pos[("China, Mainland", end)] / 1000.0)}}
    if all(have.values()):
        d_pool = r3(sum(pos[(c, end)] - pos[(c, ref)] for c in needed) / 1000.0)
        out["delta_us_st_busd"]["china_belgium_luxembourg"] = d_pool
    else:
        out["delta_us_st_busd"]["china_belgium_luxembourg"] = "NOT-ON-DISK (a pooled country lacks axis rows)"
    return out


def pool_bound_echo():
    t = " ".join(POOL_MD.read_text(encoding="utf-8").split())  # collapse line-wraps
    for frag_s in ["Neither perimeter contains the other", "OVERSTATE", "UNDERSTATES",
                   "not publicly quantifiable"]:
        guard(frag_s in t, f"pool determination no longer carries '{frag_s}' -- bound cannot be echoed")
    return {
        "statement": ("BOUND, not a number (rdtd_pool_determination.md): TIC 'China, Mainland' and the SAFE "
                      "reserve pool are different perimeters -- neither contains the other. Direction (i): "
                      "non-reserve mainland holders (CIC, state banks, private residents) make TIC-China "
                      "OVERSTATE the reserve pool's US holdings; no on-ledger mitigation. Direction (ii): "
                      "third-country custody (Euroclear/Belgium, Clearstream/Luxembourg, UK, Switzerland) "
                      "makes TIC-China UNDERSTATE the pool's US holdings -- the CN+BE+LU custody variant is "
                      "the on-ledger mitigation. Opposite signs, magnitudes not publicly quantifiable; no "
                      "split is fabricated. The bound rides ΔH_us_LT, hence ΔNonUS AND the netted "
                      "non-US-securities discriminator, in every use below."),
        "source": "build/reserve/rdtd_pool_determination.md (Part 2, committed)",
    }


# ---------------------------------------------------------------------------
# the mechanical verdict (pre-registered 0.5 thresholds)
# ---------------------------------------------------------------------------

def apply_thresholds(dep_total, disc, dnonus):
    """Literal pre-registered rule. DEPOSITS-SURGE iff dep >= 0.5*ΔNonUS AND ΔNonUS>0;
    NON-US-SECURITIES iff disc >= 0.5*ΔNonUS; both -> MIXED; neither -> OTHER-OR-SUPPRESSED."""
    thr = 0.5 * dnonus
    dep_axis = (dnonus > 0) and (dep_total >= thr)
    sec_axis = disc >= thr
    if dnonus <= 0 and sec_axis:
        # the literal inequality is degenerate when ΔNonUS <= 0 (any value above a negative
        # half-threshold would 'pass'); refusing to emit a verdict from a degenerate threshold.
        raise AssertionError("DEGENERATE THRESHOLD: ΔNonUS <= 0 and the literal securities axis fires -- "
                             "human review required; no verdict emitted")
    if dep_axis and sec_axis:
        v = "MIXED-COMPOSITION"
    elif dep_axis:
        v = "DEPOSITS-SURGE"
    elif sec_axis:
        v = "NON-US-SECURITIES"
    else:
        v = "OTHER-OR-SUPPRESSED"
    return {"verdict": v, "dep_axis": bool(dep_axis), "sec_axis": bool(sec_axis),
            "threshold_busd": thr, "delta_non_us_busd": dnonus,
            "deposits_total_busd": dep_total, "netted_discriminator_busd": disc}


def thr_str(v):
    s = f"{v['threshold_busd']:.4f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def verdict_sentence(v, variant_label):
    """Branch-specific prose, every branch guarded by the condition it describes."""
    V = v["verdict"]
    if V == "NON-US-SECURITIES":
        guard(v["sec_axis"] and not v["dep_axis"] and v["delta_non_us_busd"] > 0,
              f"{variant_label}: NON-US-SECURITIES prose vs axes mismatch")
        share = 100.0 * v["netted_discriminator_busd"] / v["delta_non_us_busd"]
        guard(share >= 50.0, f"{variant_label}: share below half under NON-US-SECURITIES")
        return (f"**NON-US-SECURITIES** -- the netted discriminator {f3(v['netted_discriminator_busd'])} $bn "
                f">= 0.5 x ΔNonUS ({thr_str(v)} $bn) and absorbs {share:.1f}% of ΔNonUS; the deposits axis "
                f"fails ({f3(v['deposits_total_busd'])} $bn)")
    if V == "DEPOSITS-SURGE":
        guard(v["dep_axis"] and not v["sec_axis"], f"{variant_label}: DEPOSITS-SURGE prose vs axes mismatch")
        return (f"**DEPOSITS-SURGE** -- deposits {f3(v['deposits_total_busd'])} $bn >= 0.5 x ΔNonUS "
                f"({thr_str(v)} $bn); the securities axis fails ({f3(v['netted_discriminator_busd'])} $bn)")
    if V == "MIXED-COMPOSITION":
        guard(v["dep_axis"] and v["sec_axis"], f"{variant_label}: MIXED prose vs axes mismatch")
        return (f"**MIXED-COMPOSITION** -- both axes >= 0.5 x ΔNonUS ({thr_str(v)} $bn): deposits "
                f"{f3(v['deposits_total_busd'])}, netted securities {f3(v['netted_discriminator_busd'])} $bn")
    guard(V == "OTHER-OR-SUPPRESSED" and not v["dep_axis"] and not v["sec_axis"],
          f"{variant_label}: OTHER-OR-SUPPRESSED prose vs axes mismatch")
    neg = ""
    if v["delta_non_us_busd"] <= 0:
        neg = (f"; ΔNonUS is NEGATIVE ({f3(v['delta_non_us_busd'])} $bn) -- this perimeter's US LT holdings "
               f"rose by more than the entire ex-gold reserve line")
    return (f"**OTHER-OR-SUPPRESSED** (sub-threshold, NOT suppression: every required SDDS line is populated "
            f"in all 132 months; neither deposits {f3(v['deposits_total_busd'])} nor the netted discriminator "
            f"{f3(v['netted_discriminator_busd'])} $bn reaches 0.5 x ΔNonUS = {thr_str(v)} $bn{neg})")


def band_verdict(dep_total, dT, active, v_us, abs_G, dsec):
    """Pre-registered band branch (fires only under 446.5-UNRELIABLE): the flow leg is
    carried as [active-|G|, active+|G|]; verdict on the band; straddle -> band-honest
    OTHER-OR-SUPPRESSED."""
    ends = []
    for a in (active - abs_G, active + abs_G):
        dH = a + v_us                    # dH = active + V_us by construction
        dnonus = r3(dT - dH)
        disc = r3(dsec - dH)
        ends.append(apply_thresholds(dep_total, disc, dnonus))
    if ends[0]["verdict"] == ends[1]["verdict"]:
        return ends, ends[0]["verdict"], False
    return ends, "OTHER-OR-SUPPRESSED", True   # band-honest, straddle stated by caller (guarded)


# ---------------------------------------------------------------------------
# payload
# ---------------------------------------------------------------------------

def build_payload():
    clauses = contract_clauses()
    flows, start, end, ref = load_windows()
    dT, dT_ref, fx_start, fx_end = safe_delta_total(start, end, ref)
    terms, frag = panel_terms(start, end, ref, flows)
    frag_echo = fragility_echo(frag)
    sdds = sdds_ledger(start, end, dT)
    st = st_leg(start, end, ref)
    pool = pool_bound_echo()

    dep_total = sdds["delta_deposits_total_busd"]
    dsec = sdds["delta_securities_busd"]

    identity = {}
    for variant, t in terms.items():
        dnonus = r3(dT - t["delta_H_us_LT_busd"])
        alt = r3(dT + (-t["active_busd"]) - t["V_us_busd"])
        guard(abs(dnonus - alt) < 0.002,
              f"{variant}: the two identity forms disagree ({dnonus} vs {alt})")
        disc = r3(dsec - t["delta_H_us_LT_busd"])
        entry = {
            "delta_total_ex_gold_busd": dT,
            "delta_total_source": ("build/reserve/rdtc_safe_totals.csv fx_reserves_usd_bn: "
                                   f"{p3(fx_start)} ({start}) -> {p3(fx_end)} ({end}); committed RDT-C "
                                   "convention, reconciled to RDTC_result.json branch_a delta_bn"),
            "delta_total_reference_month_convention_busd": dT_ref,
            "active_outflow_busd": r3(-t["active_busd"]),
            "active_source": ("build/reserve/RDTC_class_panel.parquet active_musd summed over the axis; "
                              "reconciled exactly to RDTC_class_flows.json residual_left_us_busd"),
            "delta_H_us_LT_busd": t["delta_H_us_LT_busd"],
            "delta_H_source": (f"build/reserve/RDTC_class_panel.parquet pos_musd: {end} minus reference "
                               f"month {ref}; reconciled exactly to RDTD_fragility.json delta_holdings_busd"),
            "V_us_busd": t["V_us_busd"],
            "V_us_definition": ("ΔH_us_LT - active (valuation residual); ABSORBS the SLT reconciliation "
                                "gap G (sized separately in RDTD_fragility.json)"),
            "delta_non_us_busd": dnonus,
            "identity_check": (f"ΔNonUS = ΔTotal(ex-gold) - ΔH_us_LT: {f3(dT)} - ({f3(t['delta_H_us_LT_busd'])}) "
                               f"= {f3(dnonus)} $bn; equivalently ΔTotal + active - V_us = {f3(dT)} + "
                               f"{f3(-t['active_busd'])} - ({f3(t['V_us_busd'])}) = {f3(alt)} $bn"),
            "netted_discriminator_busd": disc,
            "meaning_discipline": ("ΔNonUS = the change in SAFE ex-gold reserves NOT accounted for by "
                                   "TIC-measured US LT securities; it still includes US T-bills (see the ST "
                                   "adjustment), USD deposits anywhere, and US assets in non-US custody. "
                                   "ΔNonUS != 'non-dollar'."),
        }
        if st["status"] == "ON-DISK" and isinstance(st["delta_us_st_busd"].get(variant), float):
            dst = st["delta_us_st_busd"][variant]
            entry["st_leg_adjustment"] = {
                "delta_us_st_busd": dst,
                "adjusted_delta_non_us_busd": r3(dnonus - dst),
                "adjusted_netted_discriminator_busd": r3(disc - dst),
                "labelled": "ADJUSTMENT beside the headline (LT-only identity is the headline), never silently added",
            }
        identity[variant] = entry

    # ---- mechanical verdict --------------------------------------------------
    flag = frag_echo["flag"]
    verdicts = {}
    band_used = False
    for variant, entry in identity.items():
        if flag == "RELIABLE-WITHIN-GAP":
            guard(frag_echo["ratio_absG_over_absActive"] <= FRAG_THRESHOLD_FRAC,
                  "RELIABLE-WITHIN-GAP branch entered with ratio above 0.25")
            v = apply_thresholds(dep_total, entry["netted_discriminator_busd"],
                                 entry["delta_non_us_busd"])
            v["threshold_busd_str"] = thr_str(v)
            v["form"] = "point (no band override; Part 1 flag RELIABLE-WITHIN-GAP)"
            v["sentence"] = verdict_sentence(v, variant)
        else:
            guard(frag_echo["ratio_absG_over_absActive"] > FRAG_THRESHOLD_FRAC,
                  "band branch entered without the 0.25 threshold tripping")
            band_used = True
            ends, bv, straddle = band_verdict(dep_total, dT, -identity[variant]["active_outflow_busd"],
                                              entry["V_us_busd"], frag_echo["abs_G_total_busd"], dsec)
            v = {"verdict": bv, "form": "BAND (446.5-UNRELIABLE override)",
                 "band_endpoints": ends, "straddle": straddle}
            if straddle:
                v["sentence"] = ("**OTHER-OR-SUPPRESSED** (band-honest: the identity band straddles a 0.5 "
                                 "threshold; endpoint verdicts differ: "
                                 f"{ends[0]['verdict']} vs {ends[1]['verdict']})")
            else:
                v["sentence"] = f"band verdict (both endpoints agree): {verdict_sentence(ends[0], variant)}"
        verdicts[variant] = v

    headline = verdicts["china_alone"]
    pooled = verdicts["china_belgium_luxembourg"]

    # ST-adjusted sensitivity on the headline (labelled; never the verdict)
    st_sens = None
    if "st_leg_adjustment" in identity["china_alone"] and flag == "RELIABLE-WITHIN-GAP":
        adj = identity["china_alone"]["st_leg_adjustment"]
        v_adj = apply_thresholds(dep_total, adj["adjusted_netted_discriminator_busd"],
                                 adj["adjusted_delta_non_us_busd"])
        st_sens = {"verdict_under_st_adjustment": v_adj["verdict"],
                   "axes": {"dep_axis": v_adj["dep_axis"], "sec_axis": v_adj["sec_axis"]},
                   "threshold_busd": r3(v_adj["threshold_busd"]),
                   "labelled": ("SENSITIVITY only -- the pre-registered verdict is computed on the LT-only "
                                "headline identity; the ST leg is reported beside it")}

    # ---- expectation, evaluated mechanically ---------------------------------
    primary = {"OTHER-OR-SUPPRESSED", "MIXED-COMPOSITION"}
    if headline["verdict"] in primary:
        guard(headline["verdict"] in primary, "expectation HELD branch mismatch")
        expectation = {"pre_registered_primary": "OTHER-OR-SUPPRESSED or MIXED-COMPOSITION",
                       "status": "HELD",
                       "statement": f"headline verdict {headline['verdict']} is in the pre-registered primary set"}
    else:
        guard(headline["verdict"] not in primary, "expectation REFUTED branch mismatch")
        guard(headline["verdict"] in ("NON-US-SECURITIES", "DEPOSITS-SURGE"),
              "REFUTED-toward branch requires a named axis")
        expectation = {"pre_registered_primary": "OTHER-OR-SUPPRESSED or MIXED-COMPOSITION",
                       "status": f"REFUTED toward {headline['verdict']}",
                       "statement": (f"the pre-registered primary expectation is REFUTED: the "
                                     f"{'netted securities move' if headline['verdict'] == 'NON-US-SECURITIES' else 'deposits lines'} "
                                     f"absorb(s) >= half of ΔNonUS on the China-alone headline")}
    if band_used:
        expectation["band_note"] = "446.5-UNRELIABLE override was IN FORCE; verdicts reported on the band"

    # ---- honest tensions ------------------------------------------------------
    share = sdds["deposits_share_of_fx_line_pct"]
    guard(share["max"] < 2.0 and dep_total < 0.05 * abs(identity["china_alone"]["delta_non_us_busd"]),
          "deposits 'near-absence' prose no longer supported by the numbers")
    tensions = [
        ("pool_bound", pool["statement"]),
        ("currency_blindness_k1_wall",
         "The SDDS securities line is total-of-all-currencies. The netted discriminator therefore identifies "
         "NON-US-ISSUER securities, NEVER non-dollar: a non-US issuer can issue USD paper, and US-issuer USD "
         "vs non-US-issuer is the ONLY distinction the netting makes. The k1 wall (RDT-B/C) stands; no "
         "currency is guessed."),
        ("deposits_near_absence_is_a_finding",
         f"Deposits are {share['min']:.2f}%..{share['max']:.2f}% of the SDDS FX line in every one of "
         f"{share['n_months']} months, and moved {f3(dep_total)} $bn over the axis. A CIPS/deposit-channel "
         "reallocation of reserves would surface on these lines and does not -- at reserve level, per China's "
         "own SDDS reporting, the deposit channel has no footprint. This is itself a finding, not a gap."),
        ("blank_of_which_sub_lines",
         "The template's of-which sub-lines are blank across the whole 2015-06..2026-05 panel (structural "
         "disclosure state, not interpolated): " + "; ".join(sdds["blank_of_which_sub_lines"])),
        ("V_us_conflation",
         f"V_us ({f3(identity['china_alone']['V_us_busd'])} $bn china_alone) conflates true valuation change "
         f"with the TIC transactions-vs-positions reconciliation gap: small for China-alone (G "
         f"{f3(frag_echo['G_total_busd'])} $bn, ratio {frag_echo['ratio_absG_over_absActive']}) but "
         f"{frag_echo['context_cn_be_lu']['ratio_absG_over_absActive']} for CN+BE+LU (G "
         f"{f3(frag_echo['context_cn_be_lu']['G_total_busd'])} $bn) -- the custody-center contrast that keeps "
         "the pooled variant context-only."),
    ]

    payload = {
        "artifact": "RDTD_result (RDT-D Parts 0+4: the identity, the SDDS mechanical verdict, the amendment inputs)",
        "establishment": ("NOT ESTABLISHED -- output of RDTD_recompute.py; every number below is an OUTPUT "
                          "pending its verifier scenario (orchestrator re-run of build/reserve/RDTD_recompute.py "
                          "reproducing this file and the amended object byte-for-byte -- RDTD_verify.json "
                          "all_pass=true -- and the RDT-D human gate)."),
        "contract": "build/reserve/RDTD_prediction.md (pre-registered before this build)",
        "no_date_no_probability_no_currency_guess": ("no breaking-point date, no probability, and no "
                                                     "destination-currency guess appear in this artifact"),
        "contract_clauses_found_verbatim": clauses,
        "verdict_axis": {"start": start, "end": end, "holdings_reference_month": ref,
                         "source": "RDTC_class_flows.json windows (RDT-B recent-3y window verbatim)"},
        "units": "all *_busd fields are billions of USD, 3 decimals",
        "identity": identity,
        "st_leg": st,
        "pool_bound": pool,
        "fragility_integration": dict(frag_echo, **{
            "band_override": ("NONE -- flag RELIABLE-WITHIN-GAP: the identity is carried in point form; "
                              "G still reported and absorbed inside V_us"
                              if flag == "RELIABLE-WITHIN-GAP" else
                              "IN FORCE -- 446.5-UNRELIABLE: the flow leg is carried as the band "
                              "[active-|G|, active+|G|] and the verdict is band-honest")}),
        "sdds_ledger": sdds,
        "netting_rule": ("pre-registered: the SDDS securities line INCLUDES US securities; the "
                         "non-US-securities discriminator is Δsec_SDDS - ΔH_us_LT (per custody variant; the "
                         "pool caveat rides it). Reading raw Δsec_SDDS as non-US purchases is the named "
                         "dramatization vector and is not done anywhere here."),
        "mechanical_verdict": {
            "rule": ("pre-registered 0.5 thresholds on the ΔNonUS midpoint, China-alone headline: "
                     "DEPOSITS-SURGE iff Δdeposits_total >= 0.5 x ΔNonUS (and ΔNonUS > 0); NON-US-SECURITIES "
                     "iff (Δsec_SDDS - ΔH_us_LT) >= 0.5 x ΔNonUS; both -> MIXED-COMPOSITION; neither/"
                     "suppression -> OTHER-OR-SUPPRESSED (stating which)"),
            "headline_variant": "china_alone",
            "china_alone": headline,
            "china_belgium_luxembourg_beside_it": pooled,
            "st_adjusted_sensitivity_headline": st_sens,
            "suppression_note": ("the manifest found NO suppression of required Section-I.A lines in any of "
                                 "132 months; the suppression branch cannot fire on disclosure grounds -- "
                                 "the axes were evaluated numerically"),
        },
        "expectation_evaluation": expectation,
        "honest_tensions": [{"id": k, "statement": s} for k, s in tensions],
        "reconciliation": {
            "rdtc_ledgers_exact_3dp": True,
            "fragility_totals_exact_3dp": True,
            "safe_delta_matches_committed_rdtc": True,
            "sdds_deltas_match_committed_manifest": bool(sdds["manifest_match"]),
            "note": "every guard above raises (build fails) rather than writing a mismatched number",
        },
        "inputs_sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in [
            PREDICTION, FRAGILITY_JSON, FRAGILITY_SCRIPT, SDDS_CSV, SDDS_MANIFEST, POOL_MD,
            SAFE_CSV, PANEL, FLOWS, RDTC_RESULT, RDTC_VERIFY, SLT_TABLE3]},
        "self_check": {
            "identity_two_forms_agree_within_2musd": True,
            "delta_sec_plus_dep_equals_delta_total": True,
            "axis_fully_covered_by_sdds": True,
            "band_override_used": band_used,
            "no_date_no_probability": True,
        },
    }
    return payload


# ---------------------------------------------------------------------------
# fragility sandbox re-run (verifier leg for Part 1)
# ---------------------------------------------------------------------------

def rerun_fragility_in_sandbox():
    frag = json.load(open(FRAGILITY_JSON, encoding="utf-8"))
    committed_inputs = frag["inputs_sha256"]
    guard(sorted(committed_inputs) == sorted(FRAG_SANDBOX_INPUTS),
          "fragility input list changed; sandbox mirror would be wrong")
    for rel, sha in committed_inputs.items():
        if sha256_file(ROOT / rel) != sha:
            return False, f"committed fragility input {rel} changed on disk since Part 1"
    # aux mirror file: the committed fragility JSON records its sha (tic_faq_note); verify
    # the on-disk file matches before mirroring it, or the sandbox would not be faithful
    faq_rec = frag["attribution_mechanism"]["tic_faq_note"]
    guard(faq_rec["tic_faq_file"] == FRAG_SANDBOX_AUX[0],
          "fragility tic_faq_note names a different aux file than the sandbox mirrors")
    if sha256_file(ROOT / FRAG_SANDBOX_AUX[0]) != faq_rec["tic_faq_sha256"]:
        return False, f"aux file {FRAG_SANDBOX_AUX[0]} changed on disk since the fragility regeneration"
    tmp = Path(tempfile.mkdtemp(prefix="rdtd_frag_sandbox_"))
    try:
        for rel in FRAG_SANDBOX_INPUTS + FRAG_SANDBOX_AUX:
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dst)
        script_dst = tmp / "build" / "reserve" / "RDTD_fragility_recompute.py"
        shutil.copy2(FRAGILITY_SCRIPT, script_dst)
        proc = subprocess.run([sys.executable, str(script_dst)], cwd=str(tmp),
                              capture_output=True, text=True)
        if proc.returncode != 0:
            return False, f"fragility sandbox run failed: {proc.stderr[-2000:]}"
        regen = tmp / "build" / "reserve" / "RDTD_fragility.json"
        if not regen.exists():
            return False, "fragility sandbox produced no output file"
        identical = regen.read_bytes() == FRAGILITY_JSON.read_bytes()
        return identical, ("byte-identical" if identical
                           else "sandbox output differs from committed RDTD_fragility.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Part 4: the object amendment (insert-only; strip-and-reinsert; RDT-B/C precedent)
# ---------------------------------------------------------------------------

MARK_BEGIN = "<!-- RDTD-AMEND:BEGIN"
MARK_END = "<!-- RDTD-AMEND:END"


def strip_amendment(text):
    out, skip = [], False
    for line in text.splitlines(keepends=True):
        s = line.lstrip()
        if s.startswith(MARK_BEGIN):
            guard(not skip, "nested RDTD-AMEND BEGIN")
            skip = True
            continue
        if s.startswith(MARK_END):
            guard(skip, "RDTD-AMEND END without BEGIN")
            skip = False
            continue
        if not skip:
            out.append(line)
    guard(not skip, "unterminated RDTD-AMEND block")
    return "".join(out)


def build_blocks(payload, post_rdtc_sha):
    idc = payload["identity"]["china_alone"]
    idp = payload["identity"]["china_belgium_luxembourg"]
    fr = payload["fragility_integration"]
    sd = payload["sdds_ledger"]
    mv = payload["mechanical_verdict"]
    hv = mv["china_alone"]
    pv = mv["china_belgium_luxembourg_beside_it"]
    exp = payload["expectation_evaluation"]
    st = payload["st_leg"]
    share = sd["deposits_share_of_fx_line_pct"]

    # guards for every direction/branch word used below
    guard(fr["flag"] == "RELIABLE-WITHIN-GAP" and fr["band_override"].startswith("NONE"),
          "object prose assumes RELIABLE-WITHIN-GAP / no band override")
    guard(fr["context_cn_be_lu"]["would_trip_own_threshold"],
          "object prose says the CN+BE+LU ratio would trip its own threshold")
    guard(hv["verdict"] == "NON-US-SECURITIES" and hv["sec_axis"] and not hv["dep_axis"],
          "object prose assumes headline NON-US-SECURITIES")
    guard(pv["verdict"] == "OTHER-OR-SUPPRESSED" and not pv["dep_axis"] and not pv["sec_axis"],
          "object prose assumes pooled OTHER-OR-SUPPRESSED (sub-threshold)")
    guard(idp["delta_non_us_busd"] < 0 < idc["delta_non_us_busd"],
          "object prose assumes ΔNonUS positive china-alone and negative pooled")
    guard(idp["delta_H_us_LT_busd"] > idc["delta_total_ex_gold_busd"] > 0,
          "object prose: pooled ΔH_us_LT exceeds the whole ex-gold rise")
    guard(exp["status"].startswith("REFUTED toward NON-US-SECURITIES"),
          "object prose assumes expectation REFUTED toward NON-US-SECURITIES")
    guard(st["status"] == "ON-DISK", "object prose assumes the ST leg is on disk")
    dst_cn = st["delta_us_st_busd"]["china_alone"]
    dst_pool = st["delta_us_st_busd"]["china_belgium_luxembourg"]
    guard(isinstance(dst_pool, float), "object prose assumes a pooled ST delta on disk")
    guard(dst_cn > 0, "object prose says the China T-bill position ROSE")
    share_pct = 100.0 * hv["netted_discriminator_busd"] / hv["delta_non_us_busd"]
    guard(share_pct >= 50.0, "object prose share must be >= half under NON-US-SECURITIES")
    sens = mv["st_adjusted_sensitivity_headline"]
    guard(sens is not None and sens["verdict_under_st_adjustment"] == hv["verdict"],
          "object prose says the ST-adjusted sensitivity leaves the verdict unchanged")
    guard(sd["no_suppression_of_required_lines"] and len(sd["blank_of_which_sub_lines"]) == 3,
          "object prose assumes no suppression and exactly the three blank of-which sub-lines")

    block_k3 = (
        "<!-- RDTD-AMEND:BEGIN k3-identity-sdds -->\n"
        f"**RDT-D annotation (the reserve-side identity and the SDDS instrument split, `RDTD_result.json`):** "
        f"over the verdict axis (2023-05..2026-04) the pre-registered identity ΔNonUS ≡ ΔTotal(ex-gold) − ΔH_us_LT "
        f"lands at **{f3(idc['delta_non_us_busd'])} $bn** china-alone: ΔTotal {f3(idc['delta_total_ex_gold_busd'])} "
        f"(SAFE, `rdtc_safe_totals.csv`; reference-month convention {f3(idc['delta_total_reference_month_convention_busd'])} beside it) "
        f"− ΔH_us_LT {f3(idc['delta_H_us_LT_busd'])} (TIC, `RDTC_class_panel.parquet`); equivalently ΔTotal + active "
        f"{f3(idc['active_outflow_busd'])} − V_us {f3(idc['V_us_busd'])}. Pooled CN+BE+LU: **{f3(idp['delta_non_us_busd'])} $bn** "
        f"(ΔH_us_LT {f3(idp['delta_H_us_LT_busd'])} — the custody-center perimeter's US LT holdings rose by MORE than the "
        f"entire ex-gold line, and its own reconciliation ratio {fr['context_cn_be_lu']['ratio_absG_over_absActive']} would trip "
        f"the fragility threshold: context only). Short-term US leg (labelled ADJUSTMENT, on-disk `slt_table3.txt` T-bill "
        f"positions; never silently added): ΔUS_ST china-alone {f3(dst_cn)} $bn (bills ROSE) → adjusted ΔNonUS "
        f"{f3(idc['st_leg_adjustment']['adjusted_delta_non_us_busd'])}; pooled {f3(dst_pool)}. Flow-leg fragility "
        f"(`RDTD_fragility.json`): **{fr['flag']}** — China-alone G_total {f3(fr['G_total_busd'])} $bn, |G|/|active| = "
        f"{fr['ratio_absG_over_absActive']} vs the pre-registered 0.25 (threshold {p3(fr['threshold_busd'])} $bn) → NO band "
        f"override; the 446.5 flow leg is carried in point form. SDDS ledger (SAFE Reserves Data Template §I.A, "
        f"{share['n_months']} months; the axis is fully covered, latest template 2026-05): Δsecurities "
        f"{f3(sd['delta_securities_busd'])}, Δdeposits {f3(sd['delta_deposits_total_busd'])} (CB/BIS "
        f"{f3(sd['delta_dep_cb_bis_imf_busd'])}, banks-HQ-in {f3(sd['delta_dep_banks_hq_in_busd'])}, banks-HQ-out "
        f"{f3(sd['delta_dep_banks_hq_out_busd'])}), Δother {f3(sd['delta_other_reserve_assets_busd'])} $bn. NETTING RULE "
        f"(pre-registered): the SDDS securities line INCLUDES US securities — the non-US-securities discriminator is "
        f"Δsec_SDDS − ΔH_us_LT = **{f3(hv['netted_discriminator_busd'])} $bn** china-alone (pooled "
        f"{f3(pv['netted_discriminator_busd'])}); raw Δsec_SDDS is never read as non-US purchases. MECHANICAL VERDICT "
        f"(pre-registered 0.5 thresholds on the ΔNonUS midpoint, china-alone headline): **NON-US-SECURITIES** — the netted "
        f"discriminator {f3(hv['netted_discriminator_busd'])} ≥ 0.5×ΔNonUS ({hv['threshold_busd_str']}) and absorbs "
        f"{share_pct:.1f}% of ΔNonUS; deposits {f3(hv['deposits_total_busd'])} fail their axis; the ST-adjusted sensitivity "
        f"leaves the verdict unchanged. Pooled variant beside it: OTHER-OR-SUPPRESSED (sub-threshold, NOT suppression — every "
        f"required line is populated in all {share['n_months']} months; and pooled ΔNonUS is negative). Pre-registered "
        f"expectation (OTHER-OR-SUPPRESSED or MIXED-COMPOSITION): **REFUTED toward NON-US-SECURITIES**. POOL BOUND riding "
        f"every term (`rdtd_pool_determination.md`): TIC \"China, Mainland\" ≠ the SAFE reserve pool — neither perimeter "
        f"contains the other; non-reserve mainland holders (CIC, state banks, private) make TIC-China OVERSTATE the pool's "
        f"US holdings, third-country custody (Euroclear/Clearstream/UK) makes it UNDERSTATE them; opposite directions, not "
        f"publicly quantifiable, no split fabricated. The k1 wall stands: NON-US-ISSUER securities ≠ non-dollar — no currency "
        f"is identified.\n"
        "<!-- RDTD-AMEND:END k3-identity-sdds -->\n"
    )

    block_hazard = (
        "<!-- RDTD-AMEND:BEGIN hazard-sdds -->\n"
        f"**RDT-D annotation on where the outflow shows up at reserve level (`RDTD_result.json`):** per China's own SDDS "
        f"reserves template over the same axis, the reserve-side counterpart of the outflow sits in the SECURITIES line, not "
        f"deposits — mechanical verdict **NON-US-SECURITIES**: netted discriminator Δsec_SDDS − ΔH_us_LT = "
        f"{f3(hv['netted_discriminator_busd'])} $bn ({share_pct:.1f}% of ΔNonUS {f3(idc['delta_non_us_busd'])}) vs deposits "
        f"{f3(hv['deposits_total_busd'])} $bn (deposits are {share['min']:.2f}%–{share['max']:.2f}% of the FX line in every "
        f"month — the deposit/CIPS channel has no SDDS footprint at reserve level). k1 wall: NON-US-ISSUER securities is NOT "
        f"non-dollar — a non-US issuer can issue USD paper; the destination currency stays UNDETERMINED. Ledger descriptor on "
        f"the pre-registered axis with the pool bound riding it; not a forecast, no date, no probability.\n"
        "<!-- RDTD-AMEND:END hazard-sdds -->\n"
    )

    block_lim = (
        "<!-- RDTD-AMEND:BEGIN limitations-rdtd -->\n"
        f"   - **RDT-D caveats on the identity/SDDS annotation (`RDTD_result.json`):** (i) the POOL BOUND rides both ΔNonUS "
        f"and the netted discriminator, in BOTH directions — non-reserve mainland holders (CIC, state banks, private) make "
        f"TIC-China OVERSTATE the reserve pool's US holdings; third-country custody makes it UNDERSTATE them — opposite signs, "
        f"not publicly quantifiable, carried as a bound, never split; (ii) the SDDS securities line is total-of-all-currencies: "
        f"the netted discriminator identifies NON-US-ISSUER securities, NEVER non-dollar (the k1 wall; US-issuer vs "
        f"non-US-issuer is the only distinction made); (iii) deposits' near-absence ({share['min']:.2f}%–{share['max']:.2f}% "
        f"of the FX line across all {share['n_months']} months; Δ {f3(sd['delta_deposits_total_busd'])} $bn on the axis) is "
        f"itself a finding — a CIPS/deposit-channel reallocation would surface on these lines and does not, at reserve level, "
        f"per China's own SDDS reporting; (iv) the template's of-which sub-lines are BLANK across the whole 2015-06..2026-05 "
        f"panel (structural disclosure state, not interpolated); (v) V_us ({f3(idc['V_us_busd'])} $bn china-alone) conflates "
        f"true valuation with the TIC reconciliation gap — small china-alone (G {f3(fr['G_total_busd'])} $bn, ratio "
        f"{fr['ratio_absG_over_absActive']}) but {fr['context_cn_be_lu']['ratio_absG_over_absActive']} for CN+BE+LU (G "
        f"{f3(fr['context_cn_be_lu']['G_total_busd'])} $bn), the custody-center contrast that keeps the pooled variant "
        f"context-only.\n"
        "<!-- RDTD-AMEND:END limitations-rdtd -->\n"
    )

    block_prov = (
        "<!-- RDTD-AMEND:BEGIN provenance -->\n"
        f"**RDT-D amendment provenance:** this file was further amended by RDT-D (pre-registered in "
        f"`build/reserve/RDTD_prediction.md`). All RDT-D content is delimited by RDTD-AMEND marker comments and every number "
        f"in it is computed by `build/reserve/RDTD_recompute.py` from `RDTD_fragility.json`, `rdtd_sdds_series.csv`, "
        f"`rdtc_safe_totals.csv`, `RDTC_class_panel.parquet`/`RDTC_class_flows.json`, `rdtd_pool_determination.md` and "
        f"`rdt_evidence/tic/slt_table3.txt` — stripping the RDTD-AMEND blocks reproduces the post-RDT-C object byte-for-byte "
        f"(base sha256 {post_rdtc_sha}, as recorded in `RDTC_verify.json`). `RDT_recompute.py`, `RDTB_recompute.py`, "
        f"`RDTC_recompute.py` and `RDTD_fragility_recompute.py` are NOT modified; the RDTB-AMEND and RDTC-AMEND blocks are "
        f"untouched; `RDTD_verify.json` carries the further-amended object's byte-reproduction. No composite is recomputed "
        f"(k1 unchanged).\n"
        "<!-- RDTD-AMEND:END provenance -->\n"
    )

    return [
        ("<!-- RDTC-AMEND:END k3-destination -->", block_k3),
        ("<!-- RDTC-AMEND:END hazard-destination -->", block_hazard),
        ("<!-- RDTC-AMEND:END limitations-rdtc -->", block_lim),
        ("<!-- RDTC-AMEND:END provenance -->", block_prov),
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


def amend_object(payload):
    post_rdtc_sha = json.load(open(RDTC_VERIFY, encoding="utf-8"))["outputs_sha256"]["RDT_breaking_point_object.md"]
    current = OBJECT_MD.read_text(encoding="utf-8")
    base = strip_amendment(current)
    base_sha = hashlib.sha256(base.encode("utf-8")).hexdigest()
    base_ok = base_sha == post_rdtc_sha
    guard(base_ok, f"stripped base sha {base_sha} != post-RDT-C sha {post_rdtc_sha} -- refusing to amend a wrong base")
    blocks = build_blocks(payload, post_rdtc_sha)
    amended = amend(base, blocks)
    # fixed point: strip-and-reinsert on the amended text reproduces it byte-for-byte
    repro = (strip_amendment(amended) == base) and (amend(strip_amendment(amended), blocks) == amended)
    OBJECT_MD.write_text(amended, encoding="utf-8")
    rewritten_ok = OBJECT_MD.read_text(encoding="utf-8") == amended
    return bool(repro and rewritten_ok), base_ok, base_sha, post_rdtc_sha


# ---------------------------------------------------------------------------

def main():
    payload1 = build_payload()
    payload2 = build_payload()
    s1 = json.dumps(payload1, indent=1, ensure_ascii=False)
    s2 = json.dumps(payload2, indent=1, ensure_ascii=False)
    two_pass = s1 == s2
    guard(two_pass, "two independent payload builds differ -- non-deterministic build")
    OUT_RESULT.write_text(s1 + "\n", encoding="utf-8")
    result_repro = OUT_RESULT.read_text(encoding="utf-8") == s1 + "\n"

    frag_identical, frag_note = rerun_fragility_in_sandbox()

    obj_repro, base_ok, base_sha, post_rdtc_sha = amend_object(payload1)

    flags = {
        "result_two_pass_payload_identical": bool(two_pass),
        "result_byte_reproduction": bool(result_repro),
        "fragility_sandbox_rerun_byte_identical": bool(frag_identical),
        "fragility_sandbox_note": frag_note,
        "sdds_series_recompute_matches_manifest": bool(payload1["sdds_ledger"]["manifest_match"]),
        "rdtc_ledger_reconciliation_exact": bool(payload1["reconciliation"]["rdtc_ledgers_exact_3dp"]),
        "amended_object_byte_reproduction": bool(obj_repro),
        "stripped_base_matches_post_rdtc_sha256": bool(base_ok),
    }
    all_pass = all(v for k, v in flags.items() if k != "fragility_sandbox_note")
    verify = {
        "purpose": ("verifier artifact for RDT-D Parts 0+4: records that RDTD_result.json and the amended "
                    "RDT_breaking_point_object.md were regenerated deterministically from the committed inputs "
                    "by build/reserve/RDTD_recompute.py; that the UNMODIFIED RDTD_fragility_recompute.py, "
                    "re-run in a sandbox from the committed inputs alone, byte-reproduces the committed "
                    "RDTD_fragility.json; and that the SDDS verdict-axis deltas recompute from the csv. Until "
                    "all_pass=true every number in these outputs is an OUTPUT, not established."),
        "no_date_no_probability_no_currency_guess": ("no date, no probability, and no destination-currency "
                                                     "guess anywhere in the RDT-D outputs"),
        "network": "none",
        "inputs_sha256": payload1["inputs_sha256"],
        "outputs_sha256": {
            "RDTD_result.json": sha256_file(OUT_RESULT),
            "RDT_breaking_point_object.md": sha256_file(OBJECT_MD),
        },
        "match_flags": flags,
        "post_rdtc_object_sha256": {
            "stripped_base_recomputed_here": base_sha,
            "recorded_in_RDTC_verify_json": post_rdtc_sha,
            "note": ("RDTC_verify.json's object sha256 is the RDT-D amendment base; the further-amended "
                     "object's byte-reproduction is carried here"),
        },
        "all_pass": bool(all_pass),
    }
    OUT_VERIFY.write_text(json.dumps(verify, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"all_pass": all_pass, **flags}, indent=1))


if __name__ == "__main__":
    main()
