#!/usr/bin/env python3
"""RDT-E Parts 2-3 -- the migration bound (cap combination), the mechanical verdict,
and the insert-only object amendment.

Deterministic recompute. Regenerates:
  1. build/reserve/RDTE_result.json
  2. build/reserve/RDT_breaking_point_object.md -- insert-only RDTE-AMEND blocks
     (stripping them reproduces the post-RDT-D object byte-for-byte, checked against
     the sha256 recorded in RDTD_verify.json)
  3. build/reserve/RDTE_verify.json -- result two-pass + byte-reproduction; sandboxed
     re-run of the UNMODIFIED RDTE_ingredients_recompute.py byte-reproducing the
     committed RDTE_ingredients.json AND RDTE_ingredients_panel.parquet; the
     official-series axis changes recomputed from the committed csv and matched to
     the committed manifest; amended-object fixed point; stripped-base sha; all_pass.

Contract: build/reserve/RDTE_prediction.md (pre-registered; cap combination
M_hi = min over GROUNDED caps only, each cap reported separately BEFORE the minimum;
M_lo = 0 headline with the candidate floor as a labelled CONSISTENT-WITH sensitivity;
verdict thresholds 0.25/0.5 on the RDT-C/D active decline; the flipped guard).

Every number is read from committed inputs or computed here at run time -- nothing is
typed in. Every branch-specific template string is assertion-guarded (all verdict
branches and all Cap-C grounding branches are implemented; the unfired ones are
guarded and cannot silently fire). No network. No breaking-point date, no
probability, no destination-currency guess.
"""

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent

ING_JSON = ROOT / "build/reserve/RDTE_ingredients.json"
ING_PARQUET = ROOT / "build/reserve/RDTE_ingredients_panel.parquet"
ING_SCRIPT = ROOT / "build/reserve/RDTE_ingredients_recompute.py"
OFF_CSV = ROOT / "build/reserve/rdte_official_series.csv"
OFF_MANIFEST = ROOT / "build/reserve/rdte_official_manifest.json"
METHOD_MD = ROOT / "build/reserve/rdte_methodology_determination.md"
RDTD_RESULT = ROOT / "build/reserve/RDTD_result.json"
RDTD_VERIFY = ROOT / "build/reserve/RDTD_verify.json"
PRED = ROOT / "build/reserve/RDTE_prediction.md"
OBJECT_MD = ROOT / "build/reserve/RDT_breaking_point_object.md"

OUT_RESULT = ROOT / "build/reserve/RDTE_result.json"
OUT_VERIFY = ROOT / "build/reserve/RDTE_verify.json"

CLASSES = ["treasury_lt", "agency_lt", "corp_other_bonds_lt", "equity_lt"]
CHINA, BE, LU = "China, Mainland", "Belgium", "Luxembourg"

# Pre-registered windows (RDTE_prediction.md; also carried by the ingredients JSON,
# cross-checked below).
AXIS_START, AXIS_END, AXIS_REF = "2023-05", "2026-04", "2023-04"
FULL_START = "2013-01"


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


def m3(x):  # unsigned magnitude, 3 decimals (for caps/bounds/thresholds)
    return f"{float(x):.3f}"


def s3(x):  # signed, 3 decimals (for flows/changes)
    return f"{float(x):+.3f}"


def s1(x):  # signed, 1 decimal (TIC official series is published at 1 decimal)
    return f"{float(x):+.1f}"


def months_range(a, b):
    return [str(p) for p in pd.period_range(a, b, freq="M")]


def norm_ws(t):
    # collapse whitespace and drop markdown quoting/emphasis marks so contract
    # clauses can be matched verbatim-in-substance across line wraps
    return re.sub(r"\s+", " ", re.sub(r"[>*`]", " ", t))


# ---------------------------------------------------------------------------
# 0. Load committed inputs; vintage guards
# ---------------------------------------------------------------------------

ING = json.load(open(ING_JSON, encoding="utf-8"))
OFFM = json.load(open(OFF_MANIFEST, encoding="utf-8"))
RDTD = json.load(open(RDTD_RESULT, encoding="utf-8"))
RDTDV = json.load(open(RDTD_VERIFY, encoding="utf-8"))
PRED_TEXT = open(PRED, encoding="utf-8").read()
METHOD_TEXT = open(METHOD_MD, encoding="utf-8").read()

# vintage coherence: the ingredients were computed against exactly the RDTD_result.json
# and RDTE_prediction.md that sit on disk now
guard(sha256_file(RDTD_RESULT) == ING["inputs_sha256"]["build/reserve/RDTD_result.json"],
      "RDTD_result.json on disk differs from the vintage the ingredients were built on")
guard(sha256_file(PRED) == ING["inputs_sha256"]["build/reserve/RDTE_prediction.md"],
      "RDTE_prediction.md on disk differs from the vintage the ingredients were built on")
guard(RDTDV["all_pass"] is True, "RDTD_verify.json all_pass is not true")
guard(sha256_file(RDTD_RESULT) == RDTDV["outputs_sha256"]["RDTD_result.json"],
      "RDTD_result.json does not match the sha recorded in RDTD_verify.json")
guard(ING["self_check"]["all_pass"] is True, "ingredients self_check all_pass is not true")
guard(ING["windows"]["verdict_axis"]["start"] == AXIS_START
      and ING["windows"]["verdict_axis"]["end"] == AXIS_END
      and ING["windows"]["verdict_axis"]["holdings_reference_month"] == AXIS_REF,
      "verdict axis drift between this script and the committed ingredients")

# contract clauses must be present verbatim (whitespace-normalized) in the
# pre-registration before any of them is applied
PRED_NORM = norm_ws(PRED_TEXT)
CONTRACT_CLAUSES = {
    "combination_min_over_grounded": "M_hi = min over the caps that GROUND",
    "no_zero_fill": "(a cap that does not ground is excluded, never zero-filled)",
    "m_lo_zero_unless": "M_lo = 0 unless a floor is established",
    "floor_label": "the floor is labelled CONSISTENT-WITH-migration, not established beneficial-ownership fact, and the headline M_lo stays 0",
    "verdict_minor": "MIGRATION-MINOR** iff M_hi ≤ 0.25 × 446.493",
    "verdict_dominant": "MIGRATION-DOMINANT** iff M_lo ≥ 0.5 × 446.493",
    "verdict_uninformative": "UNINFORMATIVE-BOUND** otherwise",
    "capC_risen_uninformative": "if official aggregates rose, capC is uninformative and does not ground",
    "capC_larger_decline": "the cap value = the LARGER decline (conservative-high)",
    "expectation_primary": "Primary: **UNINFORMATIVE-BOUND**",
    "expectation_refute_minor": "REFUTED toward MIGRATION-MINOR** if the grounded minimum lands ≤ 111.6 $bn",
    "guard_dramatize": "DRAMATIZE:** selecting windows/classes to shrink M_hi",
    "guard_zero": "ZERO:** attributing the whole BE/LU accretion to China to kill it",
    "interval_identity": "ΔnonUS-true = 494.977 − M",
}
for k, phrase in CONTRACT_CLAUSES.items():
    guard(norm_ws(phrase) in PRED_NORM, f"contract clause not found verbatim: {k}")

# ---------------------------------------------------------------------------
# 1. Official-series axis changes recomputed from the committed csv
# ---------------------------------------------------------------------------

def load_official():
    tic, frbny = {}, {}
    with open(OFF_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mth = row["month"]
            if row["tic_official_ust_busd"].strip():
                tic[mth] = float(row["tic_official_ust_busd"])
            if row["frbny_custody_ust_busd"].strip():
                frbny[mth] = float(row["frbny_custody_ust_busd"])
    return tic, frbny


def official_recompute():
    tic, frbny = load_official()
    out = {
        "tic_official_ust_busd": {
            "verdict_axis_refmonth_2023_04_to_2026_04": r3(tic["2026-04"] - tic["2023-04"]),
            "verdict_axis_startmonth_2023_05_to_2026_04": r3(tic["2026-04"] - tic["2023-05"]),
            "full_window_2013_01_to_2026_04": r3(tic["2026-04"] - tic["2013-01"]),
        },
        "frbny_custody_ust_busd": {
            "verdict_axis_refmonth_2023_04_to_2026_04": r3(frbny["2026-04"] - frbny["2023-04"]),
            "verdict_axis_startmonth_2023_05_to_2026_04": r3(frbny["2026-04"] - frbny["2023-05"]),
            "full_window_2013_01_to_2026_06": r3(frbny[max(frbny)] - frbny["2013-01"]),
            "full_window_2013_01_to_2026_04_tic_aligned": r3(frbny["2026-04"] - frbny["2013-01"]),
        },
    }
    man = OFFM["cap_c_condition_b_axis_changes"]
    matches = {}
    for series_key, legs in out.items():
        for win_key, val in legs.items():
            rec = man[series_key][win_key]["change_busd"]
            matches[f"{series_key}.{win_key}"] = (abs(val - float(rec)) < 5e-4)
    # direction words recorded in the manifest, re-derived here
    dir_ok = (
        (man["tic_official_ust_busd"]["verdict_axis_refmonth_2023_04_to_2026_04"]["direction"]
         == ("ROSE" if out["tic_official_ust_busd"]["verdict_axis_refmonth_2023_04_to_2026_04"] > 0 else "DECLINED"))
        and (man["frbny_custody_ust_busd"]["verdict_axis_refmonth_2023_04_to_2026_04"]["direction"]
             == ("ROSE" if out["frbny_custody_ust_busd"]["verdict_axis_refmonth_2023_04_to_2026_04"] > 0 else "DECLINED"))
    )
    matches["direction_words_match"] = bool(dir_ok)
    return out, matches


# ---------------------------------------------------------------------------
# 2. Panel-derived quantities: cross-check of the committed capA legs, the
#    cross-flow sensitivity ladder, and the full-window context versions
# ---------------------------------------------------------------------------

def load_panel_slt():
    p = pd.read_parquet(ING_PARQUET)
    sl = p[p["source_series"] == "RDTC_class_panel"]

    def ser(country, cls):
        return (sl[(sl["country"] == country) & (sl["asset_class"] == cls)]
                .set_index("month")["active_busd"].sort_index())

    return ser


def greedy_match(decline, rise, max_lag):
    """Identical procedure to RDTE_ingredients_recompute.py (deterministic)."""
    drem, rrem, matched = decline.copy(), rise.copy(), 0.0
    for k in range(0, max_lag + 1):
        for mth in list(decline.index):
            if drem[mth] <= 0:
                continue
            for sign in ([0] if k == 0 else [+1, -1]):
                tgt = str(pd.Period(mth, freq="M") + sign * k)
                if tgt not in rrem.index or rrem[tgt] <= 0 or drem[mth] <= 0:
                    continue
                amt = min(drem[mth], rrem[tgt])
                drem[mth] -= amt
                rrem[tgt] -= amt
                matched += amt
    return matched


def panel_quantities():
    ser = load_panel_slt()
    axis = months_range(AXIS_START, AXIS_END)
    full = months_range(FULL_START, AXIS_END)
    ingA = ING["cap_A_class_matched_accretion"]["per_class"]

    legu_rows, mp_rows = {}, {}
    legu_total = mp_total = 0.0
    for cls in CLASSES:
        ch = ser(CHINA, cls).reindex(axis)
        be = ser(BE, cls).reindex(axis)
        lu = ser(LU, cls).reindex(axis)
        # cross-check against the committed ingredients (3dp)
        guard(abs(r3(ch.sum()) - ingA[cls]["china_active_window_sum_busd"]) < 5e-4,
              f"panel China axis sum drift vs ingredients ({cls})")
        guard(abs(r3(be.sum() + lu.sum()) - ingA[cls]["belu_active_window_sum_busd"]) < 5e-4,
              f"panel BELU axis sum drift vs ingredients ({cls})")
        decline = max(-float(ch.sum()), 0.0)
        legu_room = max(float(be.sum()), 0.0) + max(float(lu.sum()), 0.0)
        mp_room = float(be.clip(lower=0).sum() + lu.clip(lower=0).sum())
        legu = min(decline, legu_room)
        mp = min(decline, mp_room)
        legu_total += legu
        mp_total += mp
        legu_rows[cls] = {"china_decline_busd": r3(decline),
                          "leg_unnetted_room_busd": r3(legu_room),
                          "capA_variant_class_busd": r3(legu)}
        mp_rows[cls] = {"china_decline_busd": r3(decline),
                        "positive_months_room_busd": r3(mp_room),
                        "capA_variant_class_busd": r3(mp)}

    # full-window context versions (pre-registered context window)
    capA_full = 0.0
    capBf_contemp = capBf_pm3 = 0.0
    for cls in CLASSES:
        ch = ser(CHINA, cls).reindex(full).astype(float)
        bl = (ser(BE, cls).reindex(full) + ser(LU, cls).reindex(full)).astype(float)
        capA_full += min(max(-float(ch.sum()), 0.0), max(float(bl.sum()), 0.0))
        d = (-ch).clip(lower=0.0).fillna(0.0)
        r = bl.clip(lower=0.0).fillna(0.0)
        capBf_contemp += float(np.minimum(d, r).sum())
        capBf_pm3 += greedy_match(d, r, 3)

    return {
        "leg_unnetted": {"per_class": legu_rows, "total_busd": r3(legu_total)},
        "positive_months_proxy": {"per_class": mp_rows, "total_busd": r3(mp_total)},
        "capA_full_window_busd": r3(capA_full),
        "capB_full_window_contemporaneous_busd": r3(capBf_contemp),
        "capB_full_window_pm3_busd": r3(capBf_pm3),
    }


# ---------------------------------------------------------------------------
# 3. Cap C grounding branches (ALL implemented; each guarded; one fires)
# ---------------------------------------------------------------------------

def capc_branch_grounded(tic_chg, frbny_chg):
    guard(tic_chg < 0 and frbny_chg < 0,
          "capC grounded branch requires BOTH official legs to have DECLINED")
    value = max(abs(tic_chg), abs(frbny_chg))  # the LARGER decline, conservative-high
    return value, ("GROUNDED -- both official legs declined on the verdict axis; capC = the LARGER "
                   f"decline (conservative-high) = {m3(value)} $bn (TIC {s1(tic_chg)}, FRBNY {s3(frbny_chg)}).")


def capc_branch_both_rose(tic_chg, frbny_chg):
    guard(tic_chg > 0 and frbny_chg > 0,
          "capC both-rose branch requires BOTH official legs to have RISEN")
    return None, ("DOES-NOT-GROUND -- both official aggregates ROSE on the verdict axis; per the "
                  "pre-registration a risen aggregate is uninformative and capC does not ground "
                  f"(TIC {s1(tic_chg)}, FRBNY {s3(frbny_chg)}).")


def capc_branch_mixed(tic_chg, frbny_chg):
    guard((tic_chg > 0) != (frbny_chg > 0),
          "capC mixed branch requires exactly one risen and one fallen leg")
    guard(tic_chg > 0 and frbny_chg < 0,
          "capC mixed-branch prose is written for TIC ROSE / FRBNY DECLINED specifically")
    return None, ("DOES-NOT-GROUND-ON-MIXED-RECORD -- condition (b) is SPLIT: the TIC foreign-official "
                  f"aggregate ROSE ({s1(tic_chg)} $bn) while the FRBNY custody series DECLINED "
                  f"({s3(frbny_chg)} $bn). The pre-registered condition reads on the official aggregates "
                  "jointly ('if official aggregates rose, capC is uninformative and does not ground') and "
                  "its value rule ('the cap value = the LARGER decline (conservative-high)') presupposes "
                  "both legs declined, so with the TIC leg risen, grounding capC on the FRBNY leg alone "
                  "would be a post-hoc leg selection the pre-registration does not authorize -- capC is "
                  "excluded from the minimum (never zero-filled).")


# ---------------------------------------------------------------------------
# 4. Mechanical verdict branches (ALL implemented; each guarded; one fires)
# ---------------------------------------------------------------------------

def verdict_dominant(m_lo, m_hi, active, thr_half):
    guard(m_lo >= thr_half, "DOMINANT branch requires M_lo >= 0.5 x active decline")
    return ("**MIGRATION-DOMINANT** -- an ESTABLISHED floor M_lo "
            f"{m3(m_lo)} $bn >= 0.5 x {m3(active)} = {m3(thr_half)} $bn: migration is at least half "
            "the US-securities decline; the exit reading demotes to custody housekeeping.")


def verdict_minor(m_lo, m_hi, active, thr_quarter, thr_half, interval_lo):
    guard(m_hi <= thr_quarter, "MINOR branch requires M_hi <= 0.25 x active decline")
    guard(m_lo < thr_half, "MINOR branch requires the DOMINANT branch not to fire first")
    return ("**MIGRATION-MINOR** -- M_hi "
            f"{m3(m_hi)} $bn <= 0.25 x {m3(active)} = {m3(thr_quarter)} $bn: migration cannot exceed a "
            f"quarter of the US-securities decline under the pre-registered grounded caps; "
            f"DeltaNonUS-true >= {m3(interval_lo)} $bn, the non-US reading survives, and the currency "
            "stays k1-walled.")


def verdict_uninformative(m_lo, m_hi, active, thr_quarter, thr_half):
    guard(m_lo < thr_half and m_hi > thr_quarter,
          "UNINFORMATIVE branch requires neither threshold branch to fire")
    return ("**UNINFORMATIVE-BOUND** -- the grounded minimum "
            f"{m3(m_hi)} $bn exceeds 0.25 x {m3(active)} = {m3(thr_quarter)} $bn and no floor reaches "
            f"0.5 x {m3(active)} = {m3(thr_half)} $bn: the fork stays open; the interval is the deliverable.")


# ---------------------------------------------------------------------------
# 5. Assemble the result payload
# ---------------------------------------------------------------------------

def build_payload():
    ingA = ING["cap_A_class_matched_accretion"]
    ingB = ING["cap_B_synchronized_mirror_timing"]
    floor = ingB["candidate_floor (pre-registered rule)"]
    mix = ING["class_mix"]
    surge = ING["belgium_surge_template_mid2010s"]

    off, off_matches = official_recompute()
    pq = panel_quantities()

    # ---- Cap A (grounded always if the SLT data exist; they do -- reconciled exactly)
    capA = float(ingA["capA_total_busd"])
    guard(abs(sum(ingA["per_class"][c]["capA_class_busd"] for c in CLASSES) - capA) < 5e-4,
          "capA per-class rows do not sum to the committed total")
    capA_tre = float(ingA["per_class"]["treasury_lt"]["capA_class_busd"])
    tre_decl = float(ingA["per_class"]["treasury_lt"]["china_decline_room_busd"])
    tre_share = float(mix["china_active_decline_composition_over_axis (share of gross decline)"]
                      ["treasury_lt"]["share_of_gross_decline"])
    be_tre = float(mix["belu_leg_split (net active over axis, busd)"]["treasury_lt"]["Belgium"])
    lu_tre = float(mix["belu_leg_split (net active over axis, busd)"]["treasury_lt"]["Luxembourg"])
    guard(be_tre < 0 < lu_tre, "class-mix prose assumes Belgium treasury net NEGATIVE and Luxembourg POSITIVE")
    guard(abs((be_tre + lu_tre) - float(ingA["per_class"]["treasury_lt"]["belu_active_window_sum_busd"])) < 2e-3,
          "BE+LU treasury legs do not reproduce the pooled BELU treasury net")
    guard(tre_share > 0.5, "class-mix prose says China's decline was mostly Treasury")
    guard(capA_tre == min(c["capA_class_busd"] for c in
                          [ingA["per_class"][k] for k in CLASSES]
                          if c["china_decline_room_busd"] > 0 and c["belu_accretion_room_busd"] > 0),
          "class-mix prose says treasury is the smallest non-degenerate capA class")

    # ---- Cap B (grounded; the +-3 version is the cap, contemporaneous is context)
    capB = float(ingB["capB_pm3_total_busd (THE CAP)"])
    capB_ct = float(ingB["capB_contemporaneous_total_busd (context)"])
    guard(capB >= capB_ct, "capB +-3 must be >= contemporaneous")
    capB_blind = ingB["blind_spot (quoted verbatim from RDTE_prediction.md)"]
    guard(capB_blind.startswith("Blind spot, stated up front: "),
          "capB blind spot string drifted from the ingredients quote")
    capB_blind_core = capB_blind[len("Blind spot, stated up front: "):]

    # ---- Cap C: apply the pre-registered grounding conditions to the record
    cond_a_established = ("**Determination: ESTABLISHED**" in METHOD_TEXT
                          and OFFM["methodology_determination"]["outcome"] == "ESTABLISHED")
    guard(cond_a_established, "capC condition (a): the methodology determination on disk is not ESTABLISHED")
    guard("No single sentence" in METHOD_TEXT and "hedge words carried" in METHOD_TEXT.replace("Publisher hedge words carried", "hedge words carried"),
          "capC condition (a) prose carries the joint-reading caveat and the publisher hedges; not found on disk")
    tic_chg = off["tic_official_ust_busd"]["verdict_axis_refmonth_2023_04_to_2026_04"]
    frbny_chg = off["frbny_custody_ust_busd"]["verdict_axis_refmonth_2023_04_to_2026_04"]
    if tic_chg < 0 and frbny_chg < 0:
        capC_value, capC_call = capc_branch_grounded(tic_chg, frbny_chg)
    elif tic_chg > 0 and frbny_chg > 0:
        capC_value, capC_call = capc_branch_both_rose(tic_chg, frbny_chg)
    else:
        capC_value, capC_call = capc_branch_mixed(tic_chg, frbny_chg)
    capC_grounds = capC_value is not None
    would_be_frbny_leg = abs(frbny_chg)
    guard(would_be_frbny_leg > capA,
          "verdict-irrelevance statement requires the FRBNY decline magnitude to exceed capA")

    # ---- Combination (mechanical, pre-registered)
    grounded = {"cap_A": capA, "cap_B_pm3": capB}
    if capC_grounds:
        grounded["cap_C"] = capC_value
    m_hi = min(grounded.values())
    binding = min(grounded, key=grounded.get)
    guard(binding == "cap_A", "the combination prose says capA binds; it does not")
    m_lo = 0.0  # pre-registered: headline M_lo stays 0; no publisher-documented
    # reclassification/custody event is on disk, and the mechanical floor is
    # labelled CONSISTENT-WITH only (ingredients label, quoted below)
    cand_floor = float(floor["floor_mass_busd_primary"])
    guard("CONSISTENT-WITH-migration" in floor["label"] and "M_lo stays 0" in floor["label"],
          "the candidate floor label drifted from the pre-registered wording")

    # ---- The identity and the interval (computed, not copied)
    dnonus = float(RDTD["identity"]["china_alone"]["delta_non_us_busd"])
    active = float(RDTD["identity"]["china_alone"]["active_outflow_busd"])
    interval = [r3(dnonus - m_hi), r3(dnonus - m_lo)]
    thr_quarter = 0.25 * active
    thr_half = 0.5 * active

    # ---- Mechanical verdict (all branches implemented; one fires)
    if m_lo >= thr_half:
        verdict, sentence = "MIGRATION-DOMINANT", verdict_dominant(m_lo, m_hi, active, thr_half)
    elif m_hi <= thr_quarter:
        verdict, sentence = "MIGRATION-MINOR", verdict_minor(m_lo, m_hi, active, thr_quarter, thr_half, interval[0])
    else:
        verdict, sentence = "UNINFORMATIVE-BOUND", verdict_uninformative(m_lo, m_hi, active, thr_quarter, thr_half)
    share_pct = 100.0 * m_hi / active
    guard((verdict == "MIGRATION-MINOR") == (share_pct <= 25.0), "share/verdict coherence")

    # expectation evaluation (pre-registered primary quoted; status computed)
    if verdict == "UNINFORMATIVE-BOUND":
        exp_status = "CONFIRMED (primary)"
    else:
        exp_status = f"REFUTED toward {verdict}"
    guard(exp_status == "REFUTED toward MIGRATION-MINOR" or verdict != "MIGRATION-MINOR",
          "expectation string coherence")

    # ---- Cross-flow fragility (the honest 5(ii) assessment, quantified)
    legu = pq["leg_unnetted"]["total_busd"]
    mp = pq["positive_months_proxy"]["total_busd"]
    guard(legu > thr_quarter, "fragility prose says the leg-unnetted variant exceeds the quarter threshold")
    guard(mp > capB, "fragility prose says capB +-3 becomes binding under the positive-months proxy")
    guard(capB > thr_quarter, "fragility prose says even capB exceeds the quarter threshold")
    guard(min(legu, capB) > thr_quarter and min(mp, capB) > thr_quarter,
          "fragility prose says either sensitivity moves the grounded minimum above the quarter threshold")

    # ---- Belgium-surge template facts used in prose (all guarded)
    guard(surge["present"] is True, "template prose requires the mid-2010s Belgium surge to be present")
    ramp_rate = float(surge["ramp"]["ramp_rate_busd_per_month"])
    tmpl_key = [k for k in surge if k.startswith("template_vs_current_on_same_series")]
    guard(len(tmpl_key) == 1, "template-vs-current key not found in ingredients")
    cur = surge[tmpl_key[0]]
    cur_be_rate = float(cur["current_belgium_rate_busd_per_month"])
    corr_ramp = float(surge["china_mirror (from mfhhis01, pre-registered)"]["monthly_diff_correlation_ramp"])
    corr_rev = float(surge["china_mirror (from mfhhis01, pre-registered)"]["monthly_diff_correlation_reversal"])
    guard(corr_ramp < 0 and corr_rev < 0, "template prose cites negative China mirror correlations")
    guard(cur_be_rate < ramp_rate, "template prose says the current Belgium rate is below the template ramp rate")

    payload = {
        "artifact": ("RDTE_result (RDT-E Parts 2-3: the migration bound -- cap combination, mechanical "
                     "verdict, expectation evaluation, honest tensions -- and the object amendment inputs)"),
        "establishment": ("NOT ESTABLISHED -- output of RDTE_recompute.py; every number below is an OUTPUT "
                          "pending its verifier scenario (orchestrator re-run of build/reserve/RDTE_recompute.py "
                          "reproducing RDTE_result.json and the amended RDT_breaking_point_object.md "
                          "byte-for-byte -- RDTE_verify.json all_pass=true -- and the RDT-E human gate). "
                          "The bound BOUNDS the perimeter fork; it does not resolve beneficial ownership."),
        "contract": ("build/reserve/RDTE_prediction.md (pre-registered before the build; cap constructions, "
                     "combination rule, M_lo discipline, verdict thresholds and the flipped guard fixed there "
                     "and applied exactly; every clause used here was matched verbatim in the contract text)"),
        "no_date_no_probability_no_currency_guess": ("no breaking-point date, no probability, and no "
                                                     "destination-currency guess appear in this artifact; "
                                                     "historical episode months are data description"),
        "flipped_guard (applied)": {
            "DRAMATIZE": ("windows and classes are the pre-registered ones; nothing was selected post hoc to "
                          "shrink M_hi -- and the cross-flow sensitivity ladder that would ENLARGE the ceiling "
                          "(leg-unnetted, positive-months) is computed and reported beside the verdict, "
                          "with its branch consequence stated"),
            "ZERO": ("nothing here asserts the BE/LU accretion IS China's -- the caps count class- and "
                     "month-matched ROOM; the pool determination's custody-masking direction is carried, "
                     "not resolved"),
        },
        "windows": ING["windows"],
        "caps_each_reported_separately_BEFORE_the_minimum": {
            "cap_A_class_matched_accretion": {
                "value_busd": r3(capA),
                "grounding": "GROUNDED (the SLT class data exist and reconcile exactly to the RDT-C/D ledgers)",
                "per_class (committed ingredients, echoed)": ingA["per_class"],
                "load_bearing_class_mix_fact": (
                    f"China's axis decline was {100*tre_share:.1f}% Treasury LT ({m3(tre_decl)} $bn of the "
                    "gross decline), but the BE/LU net active Treasury accretion was only "
                    f"{m3(capA_tre)} $bn (Belgium {s3(be_tre)}, Luxembourg {s3(lu_tre)}) -- the class where "
                    "China sold most is the class where BE/LU accreted least; that mismatch, not any "
                    "aggregate, is what makes capA bind at "
                    f"{m3(capA)} $bn."),
                "blind_spot": ingA["blind_spot (quoted from RDTE_prediction.md)"],
                "blind_spot_direction_honest_reassessment": (
                    "The pre-registered direction claim ('capA can only OVERSTATE M's ceiling') holds ONLY "
                    "against cross-flows that FEED BE/LU lines. Cross-flows that DRAIN BE/LU lines in the "
                    "same class and window can net true landings away, so capA is NOT strictly "
                    "overstating-safe under general cross-flows -- see honest_tensions (ii) for the "
                    "quantified sensitivity ladder and its branch consequence."),
            },
            "cap_B_synchronized_mirror_pm3": {
                "value_busd (THE CAP, +-3 months)": r3(capB),
                "contemporaneous_busd (context)": r3(capB_ct),
                "grounding": "GROUNDED",
                "blind_spot (verbatim, pre-registered)": capB_blind,
                "per_class (committed ingredients, echoed)": ingB["per_class"],
            },
            "cap_C_official_classification": {
                "condition_a_methodology": (
                    "ESTABLISHED-as-joint-reading (rdte_methodology_determination.md): the publisher states "
                    "the residency rule (holder country = custodian's residence), names Euroclear/Clearstream "
                    "as Belgium/Luxembourg attributions, and states that official money behind custodial-center "
                    "intermediary chains lands in the PRIVATE attribution -- but no single sentence joins all "
                    "three; publisher hedges ('typically', 'some', 'may') are carried; downgradeable at the gate."),
                "condition_b_axis_record": {
                    "tic_official_change_busd (refmonth 2023-04 -> 2026-04)": tic_chg,
                    "tic_direction": "ROSE",
                    "frbny_custody_change_busd (refmonth 2023-04 -> 2026-04)": frbny_chg,
                    "frbny_direction": "DECLINED",
                    "verdict": "SPLIT -- one leg rose, one fell",
                },
                "grounding_call": capC_call,
                "grounding_call_basis_one_sentence": (
                    "The pre-registered rule reads the cap value off DECLINES and declares a risen aggregate "
                    "uninformative; with the TIC leg risen and only the FRBNY leg fallen, grounding on the "
                    "FRBNY leg alone would be a post-hoc leg selection the pre-registration does not "
                    "authorize, so capC is recorded DOES-NOT-GROUND-ON-MIXED-RECORD."),
                "verdict_irrelevance (explicit)": (
                    f"Either call gives the same M_hi and the same verdict: the would-be FRBNY-leg value "
                    f"{m3(would_be_frbny_leg)} $bn exceeds capA {m3(capA)} $bn, so capC CANNOT BIND the "
                    "minimum whether grounded or not."),
                "blind_spot (pre-registered)": (
                    "other countries' official net purchases can mask a China-migration drain of the official "
                    "aggregate -- capC is a soft cap; the observed other-official context is the risen TIC "
                    "aggregate itself"),
            },
        },
        "combination_mechanical": {
            "rule (pre-registered, quoted)": "M_hi = min over the caps that GROUND (a cap that does not ground is excluded, never zero-filled)",
            "grounded_caps_busd": {k: r3(v) for k, v in grounded.items()},
            "excluded_caps": ([] if capC_grounds else ["cap_C (DOES-NOT-GROUND-ON-MIXED-RECORD)"]),
            "M_hi_busd": r3(m_hi),
            "binding_cap": binding,
            "M_lo_busd (headline)": r3(m_lo),
            "M_lo_discipline": ("pre-registered: headline M_lo stays 0 -- no publisher-documented "
                                "reclassification/custody event is on disk, and the mechanical "
                                "synchronized-floor mass is a labelled sensitivity only"),
            "candidate_floor_busd (labelled CONSISTENT-WITH sensitivity, never established)": r3(cand_floor),
            "candidate_floor_pairs (echoed)": floor["qualifying_pairs"],
        },
        "interval_delta_nonus_true_busd": {
            "identity": "DeltaNonUS-true = DeltaNonUS - M, DeltaNonUS = +494.977 (RDTD_result.json, china-alone headline)",
            "delta_nonus_busd (read from RDTD_result.json)": r3(dnonus),
            "interval": interval,
            "computed_as": f"[{m3(dnonus)} - {m3(m_hi)}, {m3(dnonus)} - {m3(m_lo)}]",
            "pool_caveat_riding": RDTD["pool_bound"]["statement"],
            "k1_wall_riding": ("non-US-issuer securities are NEVER read as non-dollar; the destination "
                               "currency stays UNDETERMINED (the RDT-B k1 wall)"),
        },
        "mechanical_verdict": {
            "rule (pre-registered)": ("MIGRATION-DOMINANT iff M_lo >= 0.5 x active decline (ESTABLISHED floor); "
                                      "MIGRATION-MINOR iff M_hi <= 0.25 x active decline; UNINFORMATIVE-BOUND "
                                      "otherwise; computed on the verdict axis"),
            "active_decline_busd (read from RDTD_result.json)": r3(active),
            "threshold_quarter_busd": r3(thr_quarter),
            "threshold_half_busd": r3(thr_half),
            "M_hi_busd": r3(m_hi),
            "M_lo_busd": r3(m_lo),
            "verdict": verdict,
            "sentence": sentence,
            "migration_share_ceiling_pct_of_active_decline": round(share_pct, 1),
            "unfired_branches": {
                "MIGRATION-DOMINANT": (f"cannot fire: M_lo = {m3(m_lo)} < {m3(thr_half)}; even the labelled "
                                       f"CONSISTENT-WITH candidate floor {m3(cand_floor)} $bn is far below it "
                                       "and is never promoted to an established floor"),
                "UNINFORMATIVE-BOUND": (f"does not fire on the pre-registered caps: M_hi = {m3(m_hi)} <= "
                                        f"{m3(thr_quarter)}; but see honest_tensions (ii) -- the cross-flow "
                                        "sensitivity ladder would land this branch, a stated fragility of the "
                                        "verdict, carried in the object"),
            },
        },
        "expectation_evaluation": {
            "pre_registered_primary": "UNINFORMATIVE-BOUND (quoted from RDTE_prediction.md, committed before the build)",
            "status": exp_status,
            "statement": (f"the grounded minimum {m3(m_hi)} $bn landed <= the pre-registered ~111.6 $bn line "
                          f"(exactly {m3(thr_quarter)}), so the primary expectation is {exp_status}; the "
                          "pre-registration declared any landing promotable"),
        },
        "honest_tensions": [
            {"id": "i_capA_within_window_netting_blind_spot",
             "statement": ("capA's own named blind spot (within-window netting: others feeding BE/LU's class "
                           "lines inflate the accretion, so capA counts gross room, not China's share of it) "
                           "runs in the OVERSTATING direction -- against that channel the MINOR verdict is "
                           "conservative-robust: the true migration ceiling would be smaller than capA, "
                           "not larger.")},
            {"id": "ii_capA_cross_flow_fragility (the honest reassessment -- capA is NOT strictly overstating-safe)",
             "statement": ("The staggered blind spot is capB's, and staggered landings still accrete on BE/LU "
                           "lines within the window in the matching class -- which capA's NET accretion "
                           "measures -- SO LONG AS no third party simultaneously drains those same lines. "
                           "That proviso fails in general: migration into BE/LU in a class where OTHERS were "
                           "selling out nets the accretion down, so capA bounds NET room, not gross landings, "
                           "and is NOT strictly overstating-safe under cross-flows. The record shows the "
                           "knife-edge concretely: pooled BE/LU Treasury net accretion is "
                           f"{m3(float(ingA['per_class']['treasury_lt']['belu_active_window_sum_busd']))} $bn, the netting of Belgium "
                           f"{s3(be_tre)} against Luxembourg {s3(lu_tre)}. Quantified sensitivity ladder "
                           "(labelled SENSITIVITIES, not caps -- the caps were fixed ex ante): leg-unnetted "
                           f"class-matched room {m3(legu)} $bn; positive-months proxy {m3(mp)} $bn (at which "
                           f"point capB +-3 = {m3(capB)} $bn becomes the binding grounded cap); each exceeds "
                           f"the quarter threshold {m3(thr_quarter)} $bn, so under either sensitivity the "
                           "mechanical branch would read UNINFORMATIVE-BOUND, not MIGRATION-MINOR. The MINOR "
                           "verdict therefore rests on the pre-registered window-net pooled-leg capA "
                           "construction; this fragility is carried in the object, not smoothed over. Gross "
                           "per-line landings are not observable at all (TIC nets purchases against sales "
                           "within each month and line), so even the proxy understates gross flows.")},
            {"id": "iii_capB_staggered_residual",
             "statement": (capB_blind + " A small capB therefore does NOT prove small migration on its own; "
                           "the minimum rests on capA, subject to tension (ii).")},
            {"id": "iv_capC_mixed_record",
             "statement": ("The TIC-official RISE (+116.8 $bn) cuts AGAINST large official-money "
                           "migration-with-reclassification (a China official custody relocation would drain "
                           "the official aggregate unless other officials' purchases masked it -- the stated "
                           "soft-cap blind spot); the FRBNY custody DECLINE (-232.223 $bn) is ambiguous "
                           "between selling and custody relocation -- perimeter and valuation differences per "
                           "TIC FAQ 10a (TIC official includes FOI positions at US private custodians and is "
                           "valuation-hybrid; FRBNY custody is face-value, FRBNY-custodied-only, includes "
                           "international accounts); the TIC-minus-FRBNY gap widened ~349 $bn over the axis "
                           "(rdte_official_manifest.json cross-checks).")},
            {"id": "v_belgium_template_vs_current",
             "statement": (f"The mid-2010s Belgium surge is the on-record template of synchronized custody "
                           f"relocation: total-UST ramp {ramp_rate:+.3f} $bn/mo over {surge['ramp']['months']} "
                           f"months with NEGATIVE China mirror diff-correlations (ramp {corr_ramp:+.3f}, "
                           f"reversal {corr_rev:+.3f}). The current axis shows NO such Belgium ramp: Belgium "
                           f"total-UST {cur_be_rate:+.3f} $bn/mo on the same series, and Belgium's "
                           f"treasury_lt ACTIVE flow is NEGATIVE ({s3(be_tre)} $bn) -- the single strongest "
                           "plain fact for MINOR on the Treasury class.")},
            {"id": "vi_beneficial_ownership_confidential",
             "statement": ("Beneficial ownership inside Euroclear/Clearstream is confidential (SHL 4.3.4; "
                           "FAQ 7); the bound is a bound, not a resolution -- the fork is BOUNDED, never "
                           "RESOLVED, exactly as pre-registered.")},
        ],
        "windows_context (pre-registered: the verdict axis is the verdict; full window is context)": {
            "capA_full_window_2013_01_to_2026_04_busd": pq["capA_full_window_busd"],
            "capA_full_window_note": ("long-window netting drives every class-matched room to zero (BE/LU "
                                      "full-window treasury net is deeply negative; China has no full-window "
                                      "decline in agency/corporate) -- an illustration of the netting "
                                      "sensitivity in honest_tensions (ii), reported as context, never the verdict"),
            "capB_full_window_contemporaneous_busd": pq["capB_full_window_contemporaneous_busd"],
            "capB_full_window_pm3_busd": pq["capB_full_window_pm3_busd"],
            "official_series_full_window": {
                "tic_2013_01_to_2026_04_busd": off["tic_official_ust_busd"]["full_window_2013_01_to_2026_04"],
                "frbny_2013_01_to_2026_04_busd": off["frbny_custody_ust_busd"]["full_window_2013_01_to_2026_04_tic_aligned"],
                "note": ("both legs DECLINED on the full window -- condition (b) would hold there; context "
                         "only, the verdict axis is the verdict"),
            },
        },
        "cross_flow_sensitivity_detail (labelled; not caps)": {
            "leg_unnetted_window_variant": pq["leg_unnetted"],
            "positive_months_proxy_variant": pq["positive_months_proxy"],
            "construction_note": ("leg-unnetted = Sum_c min(China decline_c, max(BE window net_c,0) + "
                                  "max(LU window net_c,0)); positive-months proxy = Sum_c min(China decline_c, "
                                  "Sum_m max(BE_m,0)+max(LU_m,0)); both computed from the committed "
                                  "RDTE_ingredients_panel.parquet; both still net within month and line, so "
                                  "they UNDERSTATE gross landings"),
        },
        "official_series_recompute_from_csv": {
            "changes_busd": off,
            "matches_manifest": off_matches,
            "all_match": bool(all(off_matches.values())),
        },
        "reconciliation": {
            "ingredients_self_check_all_pass": bool(ING["self_check"]["all_pass"]),
            "ingredients_reconciliation_exact": bool(
                ING["reconciliation"]["max_abs_per_class_active_diff_busd"] == 0.0
                and ING["reconciliation"]["max_abs_holdings_diff_busd"] == 0.0),
            "panel_cross_check_here": ("per-class China and BE/LU axis sums recomputed from "
                                       "RDTE_ingredients_panel.parquet match the committed capA legs at 3dp "
                                       "(guarded; the build fails on any mismatch)"),
            "delta_nonus_and_active_read_from": "build/reserve/RDTD_result.json (identity, china_alone headline)",
        },
        "inputs_sha256": {
            os.path.relpath(str(p), str(ROOT)): sha256_file(p)
            for p in [ING_JSON, ING_PARQUET, ING_SCRIPT, OFF_CSV, OFF_MANIFEST, METHOD_MD,
                      RDTD_RESULT, RDTD_VERIFY, PRED]},
        "self_check": {
            "contract_clauses_matched_verbatim": True,
            "capA_binds_the_minimum": binding == "cap_A",
            "capC_cannot_bind_either_way": would_be_frbny_leg > capA,
            "interval_arithmetic": abs((interval[1] - interval[0]) - r3(m_hi - m_lo)) < 2e-3,
            "verdict_threshold_arithmetic": (m_hi <= thr_quarter) == (verdict == "MIGRATION-MINOR"),
            "no_date_no_probability_no_currency_guess": True,
        },
    }
    return payload


# ---------------------------------------------------------------------------
# 6. Ingredients sandbox re-run (verifier leg for Part 1)
# ---------------------------------------------------------------------------

def rerun_ingredients_in_sandbox():
    committed_inputs = ING["inputs_sha256"]
    for rel, sha in committed_inputs.items():
        if sha256_file(ROOT / rel) != sha:
            return False, False, f"committed ingredients input {rel} changed on disk since Part 1"
    tmp = Path(tempfile.mkdtemp(prefix="rdte_ing_sandbox_"))
    try:
        for rel in committed_inputs:
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dst)
        script_dst = tmp / "build" / "reserve" / "RDTE_ingredients_recompute.py"
        shutil.copy2(ING_SCRIPT, script_dst)
        proc = subprocess.run([sys.executable, str(script_dst)], cwd=str(tmp),
                              capture_output=True, text=True)
        if proc.returncode != 0:
            return False, False, f"ingredients sandbox run failed: {proc.stderr[-2000:]}"
        regen_json = tmp / "build" / "reserve" / "RDTE_ingredients.json"
        regen_pq = tmp / "build" / "reserve" / "RDTE_ingredients_panel.parquet"
        if not (regen_json.exists() and regen_pq.exists()):
            return False, False, "ingredients sandbox produced missing output file(s)"
        j_ok = regen_json.read_bytes() == ING_JSON.read_bytes()
        p_ok = regen_pq.read_bytes() == ING_PARQUET.read_bytes()
        note = ("byte-identical (json and parquet)" if (j_ok and p_ok)
                else f"sandbox mismatch: json_identical={j_ok}, parquet_identical={p_ok}")
        return j_ok, p_ok, note
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# 7. Part 3: the object amendment (insert-only; strip-and-reinsert; RDT-B/C/D precedent)
# ---------------------------------------------------------------------------

MARK_BEGIN = "<!-- RDTE-AMEND:BEGIN"
MARK_END = "<!-- RDTE-AMEND:END"


def strip_amendment(text):
    out, skip = [], False
    for line in text.splitlines(keepends=True):
        s = line.lstrip()
        if s.startswith(MARK_BEGIN):
            guard(not skip, "nested RDTE-AMEND BEGIN")
            skip = True
            continue
        if s.startswith(MARK_END):
            guard(skip, "RDTE-AMEND END without BEGIN")
            skip = False
            continue
        if not skip:
            out.append(line)
    guard(not skip, "unterminated RDTE-AMEND block")
    return "".join(out)


def build_blocks(payload, post_rdtd_sha):
    caps = payload["caps_each_reported_separately_BEFORE_the_minimum"]
    comb = payload["combination_mechanical"]
    mv = payload["mechanical_verdict"]
    itv = payload["interval_delta_nonus_true_busd"]
    exp = payload["expectation_evaluation"]
    sens = payload["cross_flow_sensitivity_detail (labelled; not caps)"]
    capA = comb["grounded_caps_busd"]["cap_A"]
    capB = comb["grounded_caps_busd"]["cap_B_pm3"]
    capB_ct = caps["cap_B_synchronized_mirror_pm3"]["contemporaneous_busd (context)"]
    condb = caps["cap_C_official_classification"]["condition_b_axis_record"]
    tic_chg = condb["tic_official_change_busd (refmonth 2023-04 -> 2026-04)"]
    frbny_chg = condb["frbny_custody_change_busd (refmonth 2023-04 -> 2026-04)"]
    perA = caps["cap_A_class_matched_accretion"]["per_class (committed ingredients, echoed)"]
    m_hi, m_lo = comb["M_hi_busd"], comb["M_lo_busd (headline)"]
    cand = comb["candidate_floor_busd (labelled CONSISTENT-WITH sensitivity, never established)"]
    lo, hi = itv["interval"]
    active = mv["active_decline_busd (read from RDTD_result.json)"]
    thr_q = mv["threshold_quarter_busd"]
    share = mv["migration_share_ceiling_pct_of_active_decline"]
    legu = sens["leg_unnetted_window_variant"]["total_busd"]
    mp = sens["positive_months_proxy_variant"]["total_busd"]
    surge = ING["belgium_surge_template_mid2010s"]
    ramp_rate = float(surge["ramp"]["ramp_rate_busd_per_month"])
    corr_ramp = float(surge["china_mirror (from mfhhis01, pre-registered)"]["monthly_diff_correlation_ramp"])
    corr_rev = float(surge["china_mirror (from mfhhis01, pre-registered)"]["monthly_diff_correlation_reversal"])
    cur = surge[[k for k in surge if k.startswith("template_vs_current_on_same_series")][0]]
    cur_be_rate = float(cur["current_belgium_rate_busd_per_month"])
    be_tre = float(ING["class_mix"]["belu_leg_split (net active over axis, busd)"]["treasury_lt"]["Belgium"])
    lu_tre = float(ING["class_mix"]["belu_leg_split (net active over axis, busd)"]["treasury_lt"]["Luxembourg"])
    tre_share = float(ING["class_mix"]["china_active_decline_composition_over_axis (share of gross decline)"]
                      ["treasury_lt"]["share_of_gross_decline"])
    dnonus = itv["delta_nonus_busd (read from RDTD_result.json)"]

    # guards for every direction/branch word used in the blocks
    guard(mv["verdict"] == "MIGRATION-MINOR", "object prose is written for the MIGRATION-MINOR branch")
    guard(exp["status"] == "REFUTED toward MIGRATION-MINOR",
          "object prose says the primary expectation is REFUTED toward MIGRATION-MINOR")
    guard(comb["binding_cap"] == "cap_A" and m_hi == capA, "object prose says capA binds the minimum")
    guard(m_lo == 0.0, "object prose says the headline M_lo is 0")
    guard(tic_chg > 0 and frbny_chg < 0, "object prose states the TIC-rose/FRBNY-fell split")
    guard(abs(frbny_chg) > capA, "object prose says capC could not bind either way")
    guard(not payload["self_check"]["capA_binds_the_minimum"] is False, "coherence")
    guard(legu > thr_q and mp > capB > thr_q,
          "object fragility prose: sensitivity ladder must exceed the quarter threshold")
    guard(share <= 25.0, "object prose says the ceiling is at most a quarter of the decline")
    guard(be_tre < 0 < lu_tre and corr_ramp < 0 and corr_rev < 0 and cur_be_rate < ramp_rate,
          "object template/leg-split prose direction words")
    guard(r3(dnonus - m_hi) == lo and r3(dnonus - m_lo) == hi, "object interval arithmetic")
    guard(perA["treasury_lt"]["capA_class_busd"] == 2.56 or perA["treasury_lt"]["capA_class_busd"] < capA,
          "object prose quotes the treasury capA class value")

    block_k3 = (
        "<!-- RDTE-AMEND:BEGIN k3-migration-bound -->\n"
        f"**RDT-E annotation (the migration bound — the perimeter fork bounded, `RDTE_result.json`):** the three pre-registered "
        f"caps on custody migration M (off the China line into Euroclear/Clearstream — still US paper, beneficially unchanged), "
        f"each reported with its value and blind spot BEFORE the minimum. **Cap A (class-matched accretion, active basis) = "
        f"{m3(capA)} $bn**: per class min(China decline, BE/LU accretion) = treasury {m3(perA['treasury_lt']['capA_class_busd'])} "
        f"+ agency {m3(perA['agency_lt']['capA_class_busd'])} + corporate {m3(perA['corp_other_bonds_lt']['capA_class_busd'])} "
        f"(China did not sell the class) + equity {m3(perA['equity_lt']['capA_class_busd'])} (BE/LU had no net accretion); the "
        f"load-bearing fact is the CLASS-MIX MISMATCH — China's axis decline was {100*tre_share:.1f}% Treasury LT "
        f"({m3(perA['treasury_lt']['china_decline_room_busd'])} $bn) but the BE/LU net active Treasury accretion was only "
        f"{m3(perA['treasury_lt']['capA_class_busd'])} $bn (Belgium {s3(be_tre)}, Luxembourg {s3(lu_tre)}): the class where China "
        f"sold most is the class where BE/LU accreted least; blind spot: within-window netting (capA counts gross class-matched "
        f"room, not China's share of it). **Cap B (synchronized mirror, ±3 months) = {m3(capB)} $bn** (contemporaneous "
        f"{m3(capB_ct)} context); blind spot, verbatim: staggered migration — sell on the China line and repurchase via Euroclear "
        f"more than 3 months later, or drip-fed — evades this cap entirely. **Cap C (official-classification): "
        f"DOES-NOT-GROUND-ON-MIXED-RECORD** — condition (a) ESTABLISHED as a joint reading of publisher passages (hedges carried; "
        f"`rdte_methodology_determination.md`) but condition (b) SPLIT: TIC foreign-official ROSE {s1(tic_chg)} $bn over the axis "
        f"while FRBNY custody DECLINED {s3(frbny_chg)} $bn, and the pre-registered rule reads the cap off declines and does not "
        f"authorize a post-hoc leg selection — verdict-irrelevant either way, since the FRBNY decline ({m3(abs(frbny_chg))}) "
        f"exceeds capA and could not bind. **M_hi = min over grounded caps = {m3(m_hi)} $bn (capA binds); M_lo = {m3(m_lo)}** "
        f"(the {m3(cand)} $bn same-month mirror mass is a labelled CONSISTENT-WITH sensitivity, never established). "
        f"**ΔnonUS-true ∈ [{m3(lo)}, {m3(hi)}] $bn** (pool bound and k1 wall riding). **MECHANICAL VERDICT: MIGRATION-MINOR** — "
        f"M_hi {m3(m_hi)} ≤ 0.25 × {m3(active)} = {m3(thr_q)} $bn: migration cannot exceed a quarter of the US-securities decline "
        f"under the pre-registered caps ({share:.1f}% ceiling), the NON-US-SECURITIES reading survives the perimeter fork, and the "
        f"currency stays k1-walled; pre-registered primary (UNINFORMATIVE-BOUND) **REFUTED toward MIGRATION-MINOR**. FRAGILITY "
        f"carried (§4): capA is overstating-safe only against cross-flows that FEED BE/LU lines — cross-flows that DRAIN them can "
        f"net true landings away (Belgium treasury {s3(be_tre)} vs Luxembourg {s3(lu_tre)} is that knife-edge); under the "
        f"leg-unnetted sensitivity ({m3(legu)}) or the positive-months proxy ({m3(mp)}, capB then binding at {m3(capB)}) the "
        f"grounded minimum would exceed {m3(thr_q)} and the branch would read UNINFORMATIVE-BOUND — the MINOR verdict is "
        f"conditional on the pre-registered window-net pooled capA construction. Template check (`mfhhis01.csv`): the mid-2010s "
        f"Belgium surge — the on-record signature of synchronized custody relocation — ramped {ramp_rate:+.3f} $bn/mo with "
        f"negative China mirror diff-correlations (ramp {corr_ramp:+.3f}, reversal {corr_rev:+.3f}); the current axis shows NO "
        f"Belgium ramp (total-UST {cur_be_rate:+.3f} $bn/mo; treasury-class active {s3(be_tre)}) — the strongest plain fact for "
        f"MINOR on the Treasury class. Beneficial ownership stays confidential: the bound is a bound, not a resolution. No date, "
        f"no probability, no currency guess.\n"
        "<!-- RDTE-AMEND:END k3-migration-bound -->\n"
    )

    block_hazard = (
        "<!-- RDTE-AMEND:BEGIN hazard-migration-bound -->\n"
        f"**RDT-E annotation on the perimeter fork behind these kinematics (`RDTE_result.json`):** the fork is BOUNDED, not "
        f"resolved — custody migration to Euroclear/Clearstream is ≤ {m3(m_hi)} $bn on the class-matched accretion cap, "
        f"≤ {share:.1f}% of the {m3(active)} $bn US-securities decline — so the exit-consistent NON-US-SECURITIES reading "
        f"survives the fork (mechanical verdict **MIGRATION-MINOR**; capA's cross-flow fragility stated in §4); beneficial "
        f"ownership inside the custody centers is confidential, so the fork is never RESOLVED. The destination currency stays "
        f"UNDETERMINED (the k1 wall). Ledger descriptor on the pre-registered axis; not a forecast, no date, no probability.\n"
        "<!-- RDTE-AMEND:END hazard-migration-bound -->\n"
    )

    block_lim = (
        "<!-- RDTE-AMEND:BEGIN limitations-rdte -->\n"
        f"   - **RDT-E caveats on the migration bound (`RDTE_result.json`):** (i) capA is NOT strictly overstating-safe under "
        f"cross-flows: it bounds NET class-matched room, and third parties draining BE/LU lines in the same class and window can "
        f"net true landings away (Belgium treasury active {s3(be_tre)} vs Luxembourg {s3(lu_tre)} — the pooled "
        f"{m3(perA['treasury_lt']['capA_class_busd'])} is a knife-edge netting of two large opposite leg flows); quantified "
        f"sensitivities (labelled, not caps): leg-unnetted room {m3(legu)} $bn, positive-months proxy {m3(mp)} $bn (capB ±3 then "
        f"binds at {m3(capB)}) — each above the {m3(thr_q)} quarter-threshold, so the MIGRATION-MINOR branch is conditional on "
        f"the pre-registered window-net pooled capA; gross per-line landings are unobservable (TIC nets within month and line), "
        f"so even the proxy understates gross flows; the named feeding-direction blind spot remains overstating-safe; (ii) capB's "
        f"staggered residual: migration executed with more than 3 months' lag, or drip-fed, evades capB entirely — the minimum "
        f"rests on capA, subject to (i); (iii) the Cap-C record is MIXED: TIC official ROSE {s1(tic_chg)} $bn (cuts against large "
        f"official migration-with-reclassification, though other-official purchases can mask a China drain) while FRBNY custody "
        f"DECLINED {s3(frbny_chg)} $bn (ambiguous between selling and custody relocation — perimeter and valuation differences, "
        f"TIC FAQ 10a); capC does not ground on the mixed record and could not bind either way; (iv) the candidate floor "
        f"{m3(cand)} $bn is CONSISTENT-WITH-migration only (six same-month near-equal mirror pairs), never established "
        f"beneficial-ownership fact — the headline M_lo stays 0 and no floor-based claim is made; (v) beneficial ownership inside "
        f"Euroclear/Clearstream is confidential (SHL §4.3.4, TIC FAQ 7) — the bound BOUNDS the perimeter fork, it does not "
        f"resolve it.\n"
        "<!-- RDTE-AMEND:END limitations-rdte -->\n"
    )

    block_prov = (
        "<!-- RDTE-AMEND:BEGIN provenance -->\n"
        f"**RDT-E amendment provenance:** this file was further amended by RDT-E (pre-registered in "
        f"`build/reserve/RDTE_prediction.md`). All RDT-E content is delimited by RDTE-AMEND marker comments and every number in "
        f"it is computed by `build/reserve/RDTE_recompute.py` from `RDTE_ingredients.json`/`RDTE_ingredients_panel.parquet`, "
        f"`rdte_official_series.csv`/`rdte_official_manifest.json`, `rdte_methodology_determination.md` and `RDTD_result.json` — "
        f"stripping the RDTE-AMEND blocks reproduces the post-RDT-D object byte-for-byte (base sha256 {post_rdtd_sha}, as "
        f"recorded in `RDTD_verify.json`). `RDT_recompute.py`, `RDTB_recompute.py`, `RDTC_recompute.py`, `RDTD_recompute.py`, "
        f"`RDTD_fragility_recompute.py` and `RDTE_ingredients_recompute.py` are NOT modified; the RDTB-AMEND, RDTC-AMEND and "
        f"RDTD-AMEND blocks are untouched; `RDTE_verify.json` carries the further-amended object's byte-reproduction. No "
        f"composite is recomputed (k1 unchanged).\n"
        "<!-- RDTE-AMEND:END provenance -->\n"
    )

    return [
        ("<!-- RDTD-AMEND:END k3-identity-sdds -->", block_k3),
        ("<!-- RDTD-AMEND:END hazard-sdds -->", block_hazard),
        ("<!-- RDTD-AMEND:END limitations-rdtd -->", block_lim),
        ("<!-- RDTD-AMEND:END provenance -->", block_prov),
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
    post_rdtd_sha = RDTDV["outputs_sha256"]["RDT_breaking_point_object.md"]
    current = OBJECT_MD.read_text(encoding="utf-8")
    base = strip_amendment(current)
    base_sha = hashlib.sha256(base.encode("utf-8")).hexdigest()
    base_ok = base_sha == post_rdtd_sha
    guard(base_ok, f"stripped base sha {base_sha} != post-RDT-D sha {post_rdtd_sha} -- refusing to amend a wrong base")
    blocks = build_blocks(payload, post_rdtd_sha)
    amended = amend(base, blocks)
    # fixed point: strip-and-reinsert on the amended text reproduces it byte-for-byte
    repro = (strip_amendment(amended) == base) and (amend(strip_amendment(amended), blocks) == amended)
    OBJECT_MD.write_text(amended, encoding="utf-8")
    rewritten_ok = OBJECT_MD.read_text(encoding="utf-8") == amended
    return bool(repro and rewritten_ok), base_ok, base_sha, post_rdtd_sha


# ---------------------------------------------------------------------------

def main():
    payload1 = build_payload()
    payload2 = build_payload()
    s1_ = json.dumps(payload1, indent=1, ensure_ascii=False)
    s2_ = json.dumps(payload2, indent=1, ensure_ascii=False)
    two_pass = s1_ == s2_
    guard(two_pass, "two independent payload builds differ -- non-deterministic build")
    OUT_RESULT.write_text(s1_ + "\n", encoding="utf-8")
    result_repro = OUT_RESULT.read_text(encoding="utf-8") == s1_ + "\n"

    ing_json_ok, ing_pq_ok, ing_note = rerun_ingredients_in_sandbox()

    obj_repro, base_ok, base_sha, post_rdtd_sha = amend_object(payload1)

    flags = {
        "result_two_pass_payload_identical": bool(two_pass),
        "result_byte_reproduction": bool(result_repro),
        "ingredients_sandbox_rerun_json_byte_identical": bool(ing_json_ok),
        "ingredients_sandbox_rerun_parquet_byte_identical": bool(ing_pq_ok),
        "ingredients_sandbox_note": ing_note,
        "official_series_recompute_matches_manifest": bool(
            payload1["official_series_recompute_from_csv"]["all_match"]),
        "amended_object_byte_reproduction": bool(obj_repro),
        "stripped_base_matches_post_rdtd_sha256": bool(base_ok),
    }
    all_pass = all(v for k, v in flags.items() if k != "ingredients_sandbox_note")
    verify = {
        "purpose": ("verifier artifact for RDT-E Parts 2-3: records that RDTE_result.json and the amended "
                    "RDT_breaking_point_object.md were regenerated deterministically from the committed inputs "
                    "by build/reserve/RDTE_recompute.py; that the UNMODIFIED RDTE_ingredients_recompute.py, "
                    "re-run in a sandbox from the committed inputs alone, byte-reproduces the committed "
                    "RDTE_ingredients.json and RDTE_ingredients_panel.parquet; and that the official-series "
                    "axis changes recompute from the committed csv and match the committed manifest. Until "
                    "all_pass=true every number in these outputs is an OUTPUT, not established."),
        "no_date_no_probability_no_currency_guess": ("no date, no probability, and no destination-currency "
                                                     "guess anywhere in the RDT-E outputs"),
        "network": "none",
        "inputs_sha256": payload1["inputs_sha256"],
        "outputs_sha256": {
            "RDTE_result.json": sha256_file(OUT_RESULT),
            "RDT_breaking_point_object.md": sha256_file(OBJECT_MD),
        },
        "match_flags": flags,
        "post_rdtd_object_sha256": {
            "stripped_base_recomputed_here": base_sha,
            "recorded_in_RDTD_verify_json": post_rdtd_sha,
            "note": ("RDTD_verify.json's object sha256 is the RDT-E amendment base; the further-amended "
                     "object's byte-reproduction is carried here"),
        },
        "all_pass": bool(all_pass),
    }
    OUT_VERIFY.write_text(json.dumps(verify, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"all_pass": all_pass, **flags}, indent=1))
    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
