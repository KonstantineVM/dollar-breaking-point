#!/usr/bin/env python3
"""RDT-G Phase 3 -- ASSEMBLY: the I.B verdict (Part A), the receiving-leg tests
(Part B), the sweep verdict (Part C), and the insert-only object amendment +
verifier (Part D).

Deterministic recompute. Regenerates:
  1. build/reserve/RDTG_result.json
  2. build/reserve/RDT_breaking_point_object.md -- insert-only RDTG-AMEND blocks
     (stripping them reproduces the post-RDT-F object byte-for-byte, checked
     against the sha256 recorded in RDTF_verify.json BEFORE amending)
  3. build/reserve/RDTG_verify.json -- result two-pass + byte-reproduction;
     stripped-base sha; amended-object fixed point; all_pass.

Contract: build/reserve/RDTG_prediction.md (committed 7ad70d2; pre-registered).
Every number is read from committed inputs or computed here at run time --
nothing is typed in. Permitted literals per the tasking: window endpoints,
marker strings, file paths, regexes whose captured values are the parsed rule
constants, and the pre-registered rule constants 0.5 (leg-consistency
multiplier), one half / three quarters (sweep fractions) and 3 (minimum powered
legs). The I.B threshold multiplier (0.05) is PARSED from the committed
pre-registration and applied to the RDTD field at run time. The magnitude bars
are READ from the committed RDTG_bars.json, never recomputed here. Every
pre-registered branch (I.B: SURGE/DECLINE/FLAT + the SUPPRESSED clause; sweep:
DESTINATION-CONSISTENT / DESTINATION-ABSENT / UNPOWERED / INDETERMINATE;
interval annotation: toward-true-departure / toward-re-parking-masking-capped /
unmoved) is implemented and assertion-guarded -- an unfired branch cannot
silently emit its text; changed data fail loud. No network. No breaking-point
date, no probability, no destination-currency guess (the k1 wall).
"""

import csv
import hashlib
import io
import json
import re
import statistics
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
RES = ROOT / "build/reserve"
EV = RES / "rdtg_evidence"

PRED = RES / "RDTG_prediction.md"
BARS = RES / "RDTG_bars.json"
IB_CSV = RES / "RDTG_ib_series.csv"
IB_STAGING = RES / "RDTG_ib_staging.json"
LEGS_MANIFEST = RES / "RDTG_legs_manifest.json"
LEGS_PROV = RES / "RDTG_legs_provenance.md"
DENOMS = RES / "RDTG_denominators.json"
RDTD_RESULT = RES / "RDTD_result.json"
RDTE_RESULT = RES / "RDTE_result.json"
RDTF_RESULT = RES / "RDTF_result.json"
RDTF_VERIFY = RES / "RDTF_verify.json"
OBJECT_MD = RES / "RDT_breaking_point_object.md"

OUT_RESULT = RES / "RDTG_result.json"
OUT_VERIFY = RES / "RDTG_verify.json"

LEG_A_ZIP = EV / "leg_a_boj_regbp_q_en.zip"
LEG_B_CSV = EV / "leg_b_ecb_bp6_ea19_cn_pi_liab_position.csv"
LEG_C_FILES = {ed: EV / (f"leg_c_ons_pinkbook{ed}_chapter10." + ("xls" if ed <= 2021 else "xlsx"))
               for ed in range(2016, 2026)}
LEG_E_HTML = EV / "leg_e_finanzagentur_investor_structure.html"
LEG_F_ZIP = EV / "leg_f_boj_fof2_en.zip"
LEG_G_CSV = EV / "leg_g_ons_hewd_ukea_overseas_gilt_holdings.csv"
LEG_I_CSV = EV / "leg_i_abs_iip_653B_gg_foreign_liab_debtsec.csv"

# Pre-registered windows (window endpoints are permitted literals).
BASE_Y0, BASE_Y1 = 2015, 2021           # baseline: calendar 2015->2021
VERD_Y0, VERD_Y1 = 2022, 2025           # verdict: calendar 2022->2025
VERD_YEARS_FULL = VERD_Y1 - BASE_Y1     # 4
# Pre-registered rule constants (as tasked: "the 0.5 and 3-leg rule constants
# AS PRE-REGISTERED"); the sweep fractions are the pre-registration's
# ">= half" and ">= three-quarters" written as numbers.
LEG_CONSISTENT_MULT = 0.5
SWEEP_HALF = 0.5
SWEEP_THREE_QUARTERS = 0.75
MIN_POWERED_LEGS = 3


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


def sdev(xs):
    # Sample standard deviation (ddof=1) of the baseline annual changes --
    # the larger-sigma convention, conservative for the power test; stated in
    # the payload.
    return statistics.stdev(xs)


# ---------------------------------------------------------------------------
# 0. Load committed inputs; shas
# ---------------------------------------------------------------------------

PRED_TEXT = PRED.read_text(encoding="utf-8")
BARS_J = json.load(open(BARS, encoding="utf-8"))
IB_STAG = json.load(open(IB_STAGING, encoding="utf-8"))
MANIFEST = json.load(open(LEGS_MANIFEST, encoding="utf-8"))
RDTD = json.load(open(RDTD_RESULT, encoding="utf-8"))
RDTE = json.load(open(RDTE_RESULT, encoding="utf-8"))
RDTF = json.load(open(RDTF_RESULT, encoding="utf-8"))
RDTFV = json.load(open(RDTF_VERIFY, encoding="utf-8"))

INPUT_FILES = [PRED, BARS, IB_CSV, IB_STAGING, LEGS_MANIFEST, LEGS_PROV, DENOMS,
               RDTD_RESULT, RDTE_RESULT, RDTF_RESULT, RDTF_VERIFY,
               LEG_A_ZIP, LEG_B_CSV, LEG_E_HTML, LEG_F_ZIP, LEG_G_CSV, LEG_I_CSV] \
              + [LEG_C_FILES[ed] for ed in sorted(LEG_C_FILES)]
INPUTS_SHA = {str(p.relative_to(ROOT)): sha256_file(p) for p in INPUT_FILES}

# vintage coherence: the bars were built against exactly the artifacts on disk
for f, want in BARS_J["inputs_sha256"].items():
    p = ROOT / f
    if p.exists():
        guard(sha256_file(p) == want,
              f"{f} on disk differs from the vintage RDTG_bars.json was built on")


# ---------------------------------------------------------------------------
# 1. Committed constants -- READ at run time from field paths, never typed in
# ---------------------------------------------------------------------------

UPPER_MASS = float(RDTD["identity"]["china_alone"]["delta_non_us_busd"])          # 494.977
CROSS_FLOW = float(RDTE["cross_flow_sensitivity_detail (labelled; not caps)"]
                   ["positive_months_proxy_variant"]["total_busd"])               # 354.028
FORK_INTERVAL = [float(x) for x in RDTF["part1_route_robust_ceiling"]
                 ["route_robust_interval"]["interval_busd"]]                      # [48.484, 494.977]
LOWER_MASS = r3(UPPER_MASS - CROSS_FLOW)                                          # 140.949
guard(r3(BARS_J["mass_endpoints_busd"]["lower"]) == LOWER_MASS
      and r3(BARS_J["mass_endpoints_busd"]["upper"]) == r3(UPPER_MASS),
      "bars' mass endpoints do not reproduce from the committed RDTD/RDTE fields")
guard([r3(x) for x in BARS_J["mass_endpoints_busd"]["fork_interval_context_busd"]]
      == [r3(x) for x in FORK_INTERVAL],
      "bars' fork-interval context differs from RDTF_result.json")

# I.B threshold multiplier: PARSED from the committed pre-registration, applied
# to the RDTD field at run time (the exact matched substring is recorded).
m = re.search(r"\*\*SURGE\*\* iff ΔI\.B_total ≥ (0\.\d+) × (\d+\.\d+)", PRED_TEXT)
guard(m is not None, "could not parse the I.B SURGE threshold rule from RDTG_prediction.md")
IB_MULT = float(m.group(1))
guard(r3(float(m.group(2))) == r3(UPPER_MASS),
      "pre-registration's displayed upper mass differs from the RDTD field")
IB_THRESHOLD = IB_MULT * UPPER_MASS      # 24.74885, reproduced at run time
IB_RULE_SUBSTRING = m.group(0)

# Masking-mechanism consequences: PARSED verbatim from the pre-registration.
m1c = re.search(r"\*\*Consequence: (a null on any leg[^*]+?)\*\*", PRED_TEXT)
m2c = re.search(r"\*\*Consequence: (a surge is CONSISTENCY[^*]+?)\*\*", PRED_TEXT)
guard(m1c is not None and m2c is not None,
      "could not parse the M1/M2 consequence sentences from RDTG_prediction.md")
M1_CONSEQUENCE = re.sub(r"\s+", " ", m1c.group(1)).strip()
M2_CONSEQUENCE = re.sub(r"\s+", " ", m2c.group(1)).strip()
M1_TIC_QUOTE = MANIFEST["m1_external_manager_custodian_grounding"][
    "attribution_consequence_citation"]["quote_2"]
guard("custodial bias" in M1_TIC_QUOTE, "M1 TIC custodial-bias quote missing from the manifest")


# ---------------------------------------------------------------------------
# 2. Part A -- the I.B verdict (re-derived from RDTG_ib_series.csv)
# ---------------------------------------------------------------------------

def part_a():
    rows = list(csv.DictReader(open(IB_CSV, encoding="utf-8")))
    guard(len(rows) == 132, f"I.B series has {len(rows)} months, expected 132")
    total = {}
    flags = {k: {} for k in ["ib_total", "ib_securities", "ib_deposits", "ib_loans",
                             "ib_fin_derivatives", "ib_gold", "ib_other"]}
    for r in rows:
        mth = r["data_month"]
        guard(r["ib_total_flag"] == "PUBLISHED", f"I.B total not PUBLISHED in {mth}")
        total[mth] = float(r["ib_total_usd_bn"])
        for k in flags:
            flags[k][mth] = r[f"{k}_flag"]
    months = sorted(total)
    latest = months[-1]
    guard(months[0] == "2015-06" and latest == "2026-05",
          "I.B corpus span differs from the staged 2015-06..2026-05")

    delta = total[latest] - total["2022-01"]
    delta_var = total[latest] - total["2021-12"]
    delta_base_ctx = total["2021-12"] - total["2015-06"]

    # cross-check the committed staging (same numbers, independently re-derived)
    stg = IB_STAG["axis_numbers_STAGING_ONLY"]
    guard(r3(stg["delta_ib_total_verdict_window"]["value_usd_bn"]) == r3(delta),
          "re-derived verdict-window ΔI.B differs from the committed staging")
    guard(r3(stg["delta_ib_total_verdict_window"]["variant_2021_12_base"]["value_usd_bn"])
          == r3(delta_var), "re-derived 2021-12-base ΔI.B differs from the committed staging")
    guard(r3(stg["threshold_reproduction"]["threshold_busd"]) == r3(IB_THRESHOLD),
          "staged threshold differs from the run-time reproduction 0.05 x RDTD field")

    # branch functions -- each guards its own condition; unfired branches fail loud
    def ib_surge(d):
        guard(d >= IB_THRESHOLD, "SURGE branch invoked with delta below threshold")
        return "SURGE"

    def ib_decline(d):
        guard(d <= -IB_THRESHOLD, "DECLINE branch invoked with delta above -threshold")
        return "DECLINE"

    def ib_flat(d):
        guard(-IB_THRESHOLD < d < IB_THRESHOLD, "FLAT branch invoked outside the open interval")
        return "FLAT"

    def render(d):
        if d >= IB_THRESHOLD:
            return ib_surge(d)
        if d <= -IB_THRESHOLD:
            return ib_decline(d)
        return ib_flat(d)

    verdict = render(delta)
    verdict_var = render(delta_var)
    guard(verdict == "FLAT" and verdict_var == "FLAT",
          "the assembled I.B narration below renders the FLAT landing under both endpoint "
          "conventions; another landing computed -- extend the narration before amending")

    # SUPPRESSED clause: the total is published in all 132 months -> SUPPRESSED
    # does not attach to the total; persistent sub-line blanks are a DISCLOSURE
    # finding riding the verdict (sub-lines reported wherever published).
    blanks = {k: sum(1 for v in flags[k].values() if v == "BLANK") for k in flags}
    guard(blanks["ib_total"] == 0, "I.B total has blank months -- SUPPRESSED clause re-opens")
    stg_pl = IB_STAG["suppression_assessment_STAGING_ONLY"]["per_line_status"]
    for k in blanks:
        guard(stg_pl[k]["blank_months"] == blanks[k],
              f"re-derived blank count for {k} differs from the committed staging")
    loans_blank = sorted(mth for mth, v in flags["ib_loans"].items() if v == "BLANK")
    n_months = len(rows)

    sec = {mth: float(r["ib_securities_usd_bn"]) for mth, r in
           ((row["data_month"], row) for row in rows) if r["ib_securities_flag"] == "PUBLISHED"}
    loans = {r["data_month"]: float(r["ib_loans_usd_bn"]) for r in rows
             if r["ib_loans_flag"] == "PUBLISHED"}
    loans_last = max(loans)
    disclosure = {
        "finding": (f"DISCLOSURE finding riding the I.B verdict (not a SUPPRESSED verdict -- "
                    f"the total is published in all {n_months} months): gold and 'other' "
                    f"sub-lines are BLANK in {blanks['ib_gold']}/{n_months} and "
                    f"{blanks['ib_other']}/{n_months} months; deposits BLANK in "
                    f"{blanks['ib_deposits']}/{n_months} (single explicit 0 in 2017-04); "
                    "loans BLANK in " + ", ".join(loans_blank) + " (explicit 0.0 in "
                    "2026-03..04); securities published in all "
                    f"{n_months - blanks['ib_securities']} months and carries essentially the "
                    f"whole line. Blanks are a disclosure state, never interpolated."),
        "blank_months_per_sub_line": blanks,
        "months_in_corpus": n_months,
        "loans_blank_months": loans_blank,
        "sub_lines_reported_wherever_published": {
            "ib_securities_usd_bn": {"2015-06": r3(sec["2015-06"]), "2021-12": r3(sec["2021-12"]),
                                     "2022-01": r3(sec["2022-01"]), latest: r3(sec[latest]),
                                     "verdict_window_delta": r3(sec[latest] - sec["2022-01"])},
            "ib_loans_usd_bn": {"2015-06": r3(loans["2015-06"]), "2021-12": r3(loans["2021-12"]),
                                "2022-01": r3(loans["2022-01"]),
                                "last_published": {"month": loans_last,
                                                   "value": r3(loans[loans_last])},
                                "note": "re-derived from the committed CSV (flags cross-checked "
                                        "against the staging above); latest month BLANK so no "
                                        "verdict-window delta"},
            "ib_fin_derivatives": "explicit values (incl. 0.0) most months; verdict-window delta 0.0",
            "ib_deposits / ib_gold / ib_other": "no published verdict-window values (see blank counts)",
        },
        "SOURCE": "build/reserve/RDTG_ib_series.csv (re-derived here) cross-checked against "
                  "build/reserve/RDTG_ib_staging.json; upstream corpus build/reserve/rdtd_evidence/",
    }
    guard(r3(IB_STAG["axis_numbers_STAGING_ONLY"]["sub_line_deltas"]["ib_loans"]
             ["endpoint_values_usd_bn"]["2015-06"]) == r3(loans["2015-06"]),
          "re-derived loans 2015-06 endpoint differs from the committed staging")

    sentence = (
        f"MECHANICAL I.B VERDICT: FLAT -- ΔI.B_total over the verdict window (2022-01 -> "
        f"{latest}, latest published) = {s3(delta)} $bn, strictly between -{m3(IB_THRESHOLD)} "
        f"and +{m3(IB_THRESHOLD)} (threshold reproduced at run time as {IB_MULT} x "
        f"{m3(UPPER_MASS)}, the RDTD upper-mass field); endpoint-convention variant "
        f"(2021-12 base): {s3(delta_var)} $bn -- FLAT under BOTH conventions. The sign is "
        f"NEGATIVE (I.B fell) but does not reach the -{m3(IB_THRESHOLD)} DECLINE bar. "
        f"SUPPRESSED does not attach to the total (published in all {n_months} months); the "
        f"persistent sub-line blanks ride as a DISCLOSURE finding."
    )
    return {
        "axis": "I.B (SAFE SDDS Section I.B, 'other foreign currency assets'), monthly, USD bn",
        "threshold_reproduction": {
            "multiplier_parsed_from_preregistration": IB_MULT,
            "parsed_rule_substring": IB_RULE_SUBSTRING,
            "upper_mass_busd_read_from": "build/reserve/RDTD_result.json :: "
                                         "identity.china_alone.delta_non_us_busd",
            "upper_mass_busd": r3(UPPER_MASS),
            "threshold_busd": round(IB_THRESHOLD, 5),
        },
        "delta_verdict_window_usd_bn": {
            "convention_2022_01_base (pre-registered wording)": {
                "endpoints": {"2022-01": r3(total["2022-01"]), latest: r3(total[latest])},
                "value": r3(delta), "verdict": verdict},
            "convention_2021_12_base (sensitivity)": {
                "endpoints": {"2021-12": r3(total["2021-12"]), latest: r3(total[latest])},
                "value": r3(delta_var), "verdict": verdict_var},
        },
        "baseline_window_context_usd_bn": {
            "endpoints": {"2015-06 (data floor)": r3(total["2015-06"]),
                          "2021-12": r3(total["2021-12"])},
            "value": r3(delta_base_ctx)},
        "verdict": verdict,
        "verdict_sentence": sentence,
        "disclosure_finding": disclosure,
        "perimeter": ("I.B movement is a within-China's-own-books discriminator (re-parking into "
                      "non-reserve FX assets would surface here); it attributes nothing beyond "
                      "China's own reporting perimeter (pre-registered)."),
        "SOURCE": "build/reserve/RDTG_ib_series.csv | 132 SAFE SDDS templates (RDT-D corpus, "
                  "disk-only) | re-derived here and cross-checked against RDTG_ib_staging.json | "
                  "read 2026-07-02",
    }, sentence, verdict


# ---------------------------------------------------------------------------
# 3. Bars -- read the per-market yardsticks from the committed artifact
# ---------------------------------------------------------------------------

S1 = BARS_J["scheme1_market_size_proportional"]["markets_headline_de_incl_own_holdings"]
S2 = BARS_J["scheme2_cofer_currency_share_proportional"]["allocations"]


def bar_s1(market):
    return float(S1[market]["bar_low_local_bn"]), float(S1[market]["bar_high_local_bn"])


def bar_s2(key):
    return float(S2[key]["bar_low_local_bn"]), float(S2[key]["bar_high_local_bn"])


BAR = {
    "a": {"s1": bar_s1("JGB_JP"), "s2": bar_s2("JPY__JGB_JP"), "ccy": "JPY bn",
          "market": "JGB_JP"},
    "b": {"s1": (bar_s1("Bund_DE")[0] + bar_s1("OAT_FR")[0],
                 bar_s1("Bund_DE")[1] + bar_s1("OAT_FR")[1]),
          "s2": (bar_s2("EUR__Bund_DE")[0] + bar_s2("EUR__OAT_FR")[0],
                 bar_s2("EUR__Bund_DE")[1] + bar_s2("EUR__OAT_FR")[1]),
          "ccy": "EUR bn", "market": "Bund_DE + OAT_FR (euro-area candidate markets, summed; "
                                     "context only -- the leg is NOT-TESTABLE)"},
    "c": {"s1": bar_s1("gilt_UK"), "s2": bar_s2("GBP__gilt_UK"), "ccy": "GBP bn",
          "market": "gilt_UK"},
    "d": {"s1": bar_s1("GoC_CA"), "s2": bar_s2("CAD__GoC_CA"), "ccy": "CAD bn",
          "market": "GoC_CA (context only -- the leg is NOT-AVAILABLE)"},
    "e": {"s1": bar_s1("Bund_DE"), "s2": bar_s2("EUR__Bund_DE"), "ccy": "EUR bn",
          "market": "Bund_DE"},
    "f": {"s1": bar_s1("JGB_JP"), "s2": bar_s2("JPY__JGB_JP"), "ccy": "JPY bn",
          "market": "JGB_JP"},
    "g": {"s1": bar_s1("gilt_UK"), "s2": bar_s2("GBP__gilt_UK"), "ccy": "GBP bn",
          "market": "gilt_UK"},
    "h": {"s1": bar_s1("OAT_FR"), "s2": bar_s2("EUR__OAT_FR"), "ccy": "EUR bn",
          "market": "OAT_FR (context only -- the leg is NOT-AVAILABLE)"},
    "i": {"s1": None,  # AGS_AU drops out of Scheme 1 (outstanding NOT-GROUNDED) -- stated
          "s2": bar_s2("AUD__AGS_AU"), "ccy": "AUD bn",
          "market": "AGS_AU (Scheme-1 bar NOT-COMPUTABLE: outstanding NOT-GROUNDED; the "
                    "Scheme-2 AUD bar is used for the power test, stated)"},
}
guard("DROPS OUT" in BARS_J["scheme1_market_size_proportional"]["au_drop"],
      "bars artifact no longer drops AGS_AU from Scheme 1 -- revisit the leg-i bar rule")


# ---------------------------------------------------------------------------
# 4. Part B -- leg parsers (raw retained files; local currency throughout)
# ---------------------------------------------------------------------------

def read_zip_csv(zpath, member):
    with zipfile.ZipFile(zpath) as z:
        with z.open(member) as f:
            return list(csv.reader(io.TextIOWrapper(f, encoding="utf-8-sig")))


def leg_a_series():
    rows = read_zip_csv(LEG_A_ZIP, "regbp_q_en.csv")
    hdr = rows[0]
    out = {}
    for code, label_frag in [("BPBP6QFLCN2", "Portfolio investment/P.R. China/Net(Liabilities)"),
                             ("BPBP6QFLCN22", "Debt securities/P.R. China/Net(Liabilities)")]:
        row = next(r for r in rows[1:] if r and r[0] == code)
        guard(label_frag in row[2], f"leg a: label for {code} changed: {row[2]}")
        guard(row[3] == "100 million Yen", f"leg a: unit for {code} is {row[3]}")
        # 100 million Yen -> JPY bn: /10
        out[code] = {hdr[i]: float(row[i]) / 10 for i in range(4, len(row)) if row[i] != ""}
    return out


def leg_f_series():
    rows = read_zip_csv(LEG_F_ZIP, "ff_dl_fof_quarterly_en.csv")
    hdr = rows[0]
    out = {}
    labels = {
        "FOF_FFAS500A311": "Assets/-Central government securities and FILP bonds/Overseas/Stock",
        "FOF_FFAS500A310": "Assets/-Treasury discount bills/Overseas/Stock",
        "FOF_FFALC08G500": "Total/Holder:Overseas/Amount outstanding/Issuer:Central government",
    }
    for code, frag in labels.items():
        row = next(r for r in rows[1:] if r and r[0] == code)
        guard(frag in row[2], f"leg f: label for {code} changed: {row[2]}")
        # unit: 100 million yen (verified from the retained BoJ sjpre_units.xlsx
        # header '(100 million yen)' per RDTG_legs_manifest.json) -> JPY bn: /10
        out[code] = {hdr[i]: float(row[i]) / 10 for i in range(3, len(row))
                     if i < len(row) and row[i] != ""}
    # from-whom-to-whom cross-check: Overseas total = JGB+FILP + T-bills rows
    for q in ("202104", "202504"):
        guard(abs(out["FOF_FFALC08G500"][q]
                  - (out["FOF_FFAS500A311"][q] + out["FOF_FFAS500A310"][q])) < 0.05,
              f"leg f: from-whom-to-whom row does not equal the two stock rows at {q}")
    return out


def leg_c_series():
    vals, cells = {}, {}
    for ed in sorted(LEG_C_FILES):
        p = LEG_C_FILES[ed]
        df = pd.read_excel(p, sheet_name="10.1", header=None)
        if ed <= 2021:
            year = None
            for i in range(6):
                for x in df.iloc[i].tolist():
                    mm = re.fullmatch(r"\s*(20\d\d)(\.0)?\s*", str(x))
                    if mm:
                        year = int(mm.group(1))
            guard(any("£ billion" in str(x) for i in range(6)
                      for x in df.iloc[i].tolist()),
                  f"leg c {ed}: unit '£ billion' not found in the header rows")
            hdr_i = next(i for i in range(20)
                         if sum("Portfolio" in str(x) for x in df.iloc[i].tolist()) >= 2)
            pcols = [j for j, x in enumerate(df.iloc[hdr_i].tolist()) if "Portfolio" in str(x)]
            guard(len(pcols) == 2, f"leg c {ed}: expected 2 Portfolio columns, got {pcols}")
            liab_col = None
            for i in range(hdr_i):
                for j, x in enumerate(df.iloc[i].tolist()):
                    if "Liabilit" in str(x):
                        liab_col = j
            guard(liab_col is not None and pcols[1] >= liab_col,
                  f"leg c {ed}: liabilities Portfolio column not right of the Liabilities marker")
            col = pcols[1]
        else:
            title = str(df.iloc[0, 0])
            mm = re.search(r"end of year \[note1\] (20\d\d)", title)
            guard(mm is not None, f"leg c {ed}: reference year not in title: {title}")
            year = int(mm.group(1))
            guard("poun" in str(df.iloc[2, 0]).lower(),
                  f"leg c {ed}: pounds unit statement not found")
            hdr_i = next(i for i in range(10) if str(df.iloc[i, 0]).strip() == "Country")
            col = next(j for j, x in enumerate(df.iloc[hdr_i].tolist())
                       if str(x).strip() == "Portfolio investment liabilities")
        guard(year == ed - 2, f"leg c {ed}: reference year {year} != edition-2 (one-year lag)")
        crow = next(i for i in range(len(df))
                    if any(str(df.iloc[i, j]).strip() == "China" for j in range(2)))
        cell = df.iloc[crow, col]
        cells[year] = str(cell).strip()
        if cells[year] == "-":
            vals[year] = None  # ONS '-': nil or less than half the final digit shown
        else:
            vals[year] = float(cell)
    return vals, cells


def leg_e_table():
    t = LEG_E_HTML.read_text(encoding="utf-8", errors="replace")
    tabs = re.findall(r"<table.*?</table>", t, re.S | re.I)
    guard(len(tabs) == 1, f"leg e: expected exactly 1 table, got {len(tabs)}")
    import html as _html
    txt = re.sub(r"<[^>]+>", "|", tabs[0])
    txt = _html.unescape(txt)
    cellsf = [c.strip() for c in re.split(r"\|+", txt) if c.strip()]
    dates = ["2025-06-30", "2024-12-31", "2023-12-31", "2022-12-31", "2021-12-31", "2020-12-31"]
    guard(cellsf[:6] == dates, f"leg e: date columns changed: {cellsf[:6]}")
    rows, i = {}, 6
    while i + 6 < len(cellsf) + 1 and i < len(cellsf):
        label = cellsf[i]
        vals = cellsf[i + 1:i + 7]
        guard(all(re.fullmatch(r"\d+ %", v) for v in vals),
              f"leg e: non-percent cells under {label}: {vals}")
        rows[label] = {d: int(v.split()[0]) for d, v in zip(dates, vals)}
        i += 7
    guard("Central banks and government sector - third countries" in rows
          and "Other investors - third countries" in rows,
          f"leg e: expected investor-group rows missing: {sorted(rows)}")
    return rows


def leg_g_series():
    ann, qt = {}, {}
    for r in csv.reader(open(LEG_G_CSV, encoding="utf-8")):
        if len(r) != 2:
            continue
        if re.fullmatch(r"\d{4}", r[0]):
            ann[int(r[0])] = float(r[1]) / 1000.0   # GBP m -> GBP bn
        elif re.fullmatch(r"\d{4} Q[1-4]", r[0]):
            y, q = r[0].split(" Q")
            qt[(int(y), int(q))] = float(r[1]) / 1000.0
    for y in range(2014, 2026):
        guard(abs(ann[y] - qt[(y, 4)]) < 1e-9,
              f"leg g: annual row {y} != Q4 value (annual/Q4 coherence)")
    mm = re.search(r"HEWD = ([\d,]+) = DMO",
                   MANIFEST["legs"]["g_gilt_overseas_holdings"]["series"]["cross_check"])
    guard(mm is not None and float(mm.group(1).replace(",", "")) / 1000.0 == qt[(2025, 4)],
          "leg g: manifest DMO cross-check value does not match the retained ONS series")
    return qt


def leg_i_series():
    rows = list(csv.DictReader(open(LEG_I_CSV, encoding="utf-8")))
    guard(all(r["UNIT_MEASURE"] == "AUD" and r["UNIT_MULT"] == "6" for r in rows),
          "leg i: unit is not AUD millions")
    pos_end = {r["TIME_PERIOD"]: float(r["OBS_VALUE"]) / 1000.0
               for r in rows if r["MEASURE"] == "6"}   # AUD mn -> AUD bn
    pos_beg = {r["TIME_PERIOD"]: float(r["OBS_VALUE"]) / 1000.0
               for r in rows if r["MEASURE"] == "1"}
    tx = {r["TIME_PERIOD"]: float(r["OBS_VALUE"]) / 1000.0
          for r in rows if r["MEASURE"] == "2"}
    # beginning/end coherence (measure 1 of q+1 == measure 6 of q)
    for (q, qn) in [("2021-Q4", "2022-Q1"), ("2024-Q4", "2025-Q1")]:
        guard(abs(pos_beg[qn] - pos_end[q]) < 1e-9,
              f"leg i: measure-1({qn}) != measure-6({q})")
    return pos_end, tx


def leg_b_series():
    b = {}
    for r in csv.DictReader(open(LEG_B_CSV, encoding="utf-8")):
        guard(r["KEY"] == "BP6.Q.N.I8.CN.S1.S1.LE.L.FA.P.F._Z.EUR._T.M.N",
              f"leg b: unexpected series key {r['KEY']}")
        b[r["TIME_PERIOD"]] = float(r["OBS_VALUE"]) / 1000.0   # EUR mn -> EUR bn
    guard(max(b) == "2022-Q3", f"leg b: series end {max(b)} != 2022-Q3 (as grounded)")
    return b


# ---------------------------------------------------------------------------
# 5. Part B -- the mechanical leg test
# ---------------------------------------------------------------------------

def leg_test(leg_id, base_changes, verdict_change, verdict_years):
    """Pre-registered mechanics: excess = verdict change - baseline mean annual
    change x verdict years; POWERED iff Bar_low >= sigma_baseline; CONSISTENT
    iff excess >= 0.5 x Bar_low (powered); ABSENT iff excess < 0.5 x Bar_low
    (powered). Scheme 1 = headline bar; Scheme 2 alongside."""
    mean_b = statistics.mean(base_changes)
    sig = sdev(base_changes)
    excess = verdict_change - mean_b * verdict_years
    bars1, bars2 = BAR[leg_id]["s1"], BAR[leg_id]["s2"]
    bar_low_headline = bars1[0] if bars1 is not None else bars2[0]
    powered_headline = bar_low_headline >= sig
    powered_s2 = bars2[0] >= sig

    def v_consistent():
        guard(powered_headline and excess >= LEG_CONSISTENT_MULT * bar_low_headline,
              f"leg {leg_id}: CONSISTENT branch invoked out of condition")
        return "leg-CONSISTENT"

    def v_absent():
        guard(powered_headline and excess < LEG_CONSISTENT_MULT * bar_low_headline,
              f"leg {leg_id}: ABSENT branch invoked out of condition")
        return "leg-ABSENT"

    def v_unpowered():
        guard(not powered_headline, f"leg {leg_id}: UNPOWERED branch invoked while powered")
        return "UNPOWERED -- reported, never counted"

    if not powered_headline:
        verdict = v_unpowered()
    elif excess >= LEG_CONSISTENT_MULT * bar_low_headline:
        verdict = v_consistent()
    else:
        verdict = v_absent()

    return {
        "baseline_annual_changes": [r3(x) for x in base_changes],
        "baseline_mean_annual_change": r3(mean_b),
        "sigma_baseline (sample stdev, ddof=1 -- larger-sigma convention, "
        "conservative for the power test)": r3(sig),
        "verdict_window_change": r3(verdict_change),
        "verdict_window_years": verdict_years,
        "excess (= verdict change - baseline mean x years)": r3(excess),
        "bar_low_scheme1_local_bn": r3(bars1[0]) if bars1 is not None else
            "NOT-COMPUTABLE (AGS outstanding NOT-GROUNDED; Scheme-2 AUD bar used, stated)",
        "bar_high_scheme1_local_bn": r3(bars1[1]) if bars1 is not None else
            "NOT-COMPUTABLE (see bar_low)",
        "bar_low_scheme2_local_bn": r3(bars2[0]),
        "bar_high_scheme2_local_bn": r3(bars2[1]),
        "bar_low_used_for_headline_power_test": r3(bar_low_headline),
        "half_bar_low_headline": r3(LEG_CONSISTENT_MULT * bar_low_headline),
        "powered_headline (Bar_low >= sigma_baseline)": bool(powered_headline),
        "powered_scheme2_variant": bool(powered_s2),
        "leg_verdict_headline": verdict,
        "leg_verdict_scheme2_variant": (
            ("leg-CONSISTENT" if excess >= LEG_CONSISTENT_MULT * bars2[0] else "leg-ABSENT")
            if powered_s2 else "UNPOWERED -- reported, never counted"),
    }, verdict, powered_headline, powered_s2, excess


def part_b():
    legs = {}

    # ---- (a) Japan BOP vis-a-vis China, portfolio liabilities (China-attributed)
    a = leg_a_series()
    cn = a["BPBP6QFLCN2"]

    def ann_flow(s, y):
        return sum(s[f"{y}0{q}"] for q in range(1, 5))

    a_base = [ann_flow(cn, y) for y in range(BASE_Y0, BASE_Y1 + 1)]
    a_verd = sum(ann_flow(cn, y) for y in range(VERD_Y0, VERD_Y1 + 1))
    a_test, a_verdict, a_pow, a_pow2, _ = leg_test("a", a_base, a_verd, VERD_YEARS_FULL)
    guard(a_verd < 0 and statistics.mean(a_base) > 0,
          "leg a reading narrates net sales against a positive baseline -- rewrite it")
    legs["a_japan_bop_vs_china_pi_liabilities"] = {
        "class": "CHINA-ATTRIBUTED",
        "status": "GROUNDED-PRIMARY -- TESTED",
        "construction": ("FLOWS, stated as such (mechanical extension of the pre-registered "
                         "level-change construction: Japan publishes bilateral vis-a-vis-China "
                         "portfolio-investment TRANSACTIONS, not positions, in the regional BOP; "
                         "cumulative net incurrence of liabilities over a window is the "
                         "level-change equivalent under zero valuation effects -- positions "
                         "preferred per the pre-registration but not published on this line). "
                         "Series BPBP6QFLCN2, quarterly, 100 million Yen converted to JPY bn."),
        "windows": "baseline 2015Q1->2021Q4 annual flow sums; verdict 2022Q1->2025Q4 cumulative",
        "debt_securities_only_verdict_cum_jpy_bn": r3(sum(
            ann_flow(a["BPBP6QFLCN22"], y) for y in range(VERD_Y0, VERD_Y1 + 1))),
        "test": a_test,
        "reading": ("China's net transactions in Japanese portfolio securities were NEGATIVE "
                    "over the verdict window (net sales), against a positive baseline mean -- "
                    "the excess is deeply negative. M2 caveat rides: transactions via non-China "
                    "intermediaries attribute to the intermediary's economy, so this line's "
                    "absence is not the absence of China."),
        "custody_caveat": "BoJ FAQ Q10 verbatim in RDTG_legs_manifest.json (transactor-economy "
                          "attribution; foreign custodian redemptions attribute to the custodian)",
        "SOURCE": "build/reserve/rdtg_evidence/leg_a_boj_regbp_q_en.zip :: regbp_q_en.csv rows "
                  "BPBP6QFLCN2/BPBP6QFLCN22 | BoJ/MoF regional BOP | parsed 2026-07-02",
    }

    # ---- (b) euro-area BOP by counterpart, China PI liabilities positions
    b = leg_b_series()
    b_base = [b[f"{y}-Q4"] - b[f"{y-1}-Q4"] for y in range(BASE_Y0, BASE_Y1 + 1)]
    b_partial = b["2022-Q3"] - b["2021-Q4"]
    legs["b_euroarea_bop_china_pi_liabilities"] = {
        "class": "CHINA-ATTRIBUTED",
        "status": "NOT-TESTABLE -- the position series ends 2022Q3 (3 verdict quarters of 16); "
                  "the pre-registered test cannot run; reported, never counted",
        "construction": "POSITIONS, EUR bn, market value, quarterly (ECB BP6, EA19 vis-a-vis "
                        "China, PI liabilities; every observation flagged E=estimated)",
        "windows": "baseline 2014Q4->2021Q4 (computable, context); verdict window essentially "
                   "unsupported (published boundary 2022Q3)",
        "baseline_annual_changes_eur_bn": [r3(x) for x in b_base],
        "sigma_baseline_context_eur_bn": r3(sdev(b_base)),
        "level_2021Q4_eur_bn": r3(b["2021-Q4"]),
        "partial_verdict_change_2021Q4_to_2022Q3_eur_bn (context only)": r3(b_partial),
        "bar_context_eur_bn (Bund_DE + OAT_FR, S1 low/high; S2 low/high)": [
            r3(BAR["b"]["s1"][0]), r3(BAR["b"]["s1"][1]),
            r3(BAR["b"]["s2"][0]), r3(BAR["b"]["s2"][1])],
        "structural_absence_finding": (
            "The euro-area flows-by-counterpart LIABILITIES cell does not exist: Eurostat "
            "bop_eu6_q returns 130 observations for the China-partner portfolio ASSETS flow and "
            "0 for LIABILITIES (probes retained), and the ECB position series stops at 2022Q3. "
            "A China-attributed leg whose absence is itself informative about the compiler "
            "perimeter: euro-area compilers estimate portfolio liabilities RESIDUALLY (quality-"
            "report footnote, retained) because end-holder residency is not observable -- the "
            "cell's absence is a disclosure/methodology fact, not evidence of absence of flows."),
        "custody_caveat": "ECB quality report June 2024 footnote 8 verbatim in "
                          "RDTG_legs_manifest.json (residual estimation of PI liabilities)",
        "SOURCE": "build/reserve/rdtg_evidence/leg_b_ecb_bp6_ea19_cn_pi_liab_position.csv | ECB "
                  "Data Portal BP6 | parsed 2026-07-02",
    }

    # ---- (c) UK Pink Book China portfolio liabilities (China-attributed)
    c_vals, c_cells = leg_c_series()
    guard(c_vals[2014] is None and c_cells[2014] == "-",
          "leg c: end-2014 China PI-liabilities cell expected '-' (nil/<GBP 0.05bn)")
    c_series = {y: c_vals[y] for y in range(2015, 2024)}
    guard(all(v is not None for v in c_series.values()),
          "leg c: missing China PI-liabilities value in 2015..2023")
    c_base = [c_series[y] - c_series[y - 1] for y in range(2016, BASE_Y1 + 1)]  # 6 changes
    C_VERD_Y1 = 2023  # nearest published boundary (PB2025 table 10.1 lags one year), stated
    c_years = C_VERD_Y1 - BASE_Y1  # 2
    c_verd = c_series[C_VERD_Y1] - c_series[BASE_Y1]
    c_test, c_verdict, c_pow, c_pow2, c_excess = leg_test("c", c_base, c_verd, c_years)
    legs["c_uk_pinkbook_china_pi_liabilities"] = {
        "class": "CHINA-ATTRIBUTED",
        "status": "GROUNDED-PRIMARY -- TESTED (verdict window TRUNCATED to end-2023, the "
                  "nearest published boundary; mixed-vintage friction carried: each year's "
                  "value comes from a different edition)",
        "construction": "POSITIONS, GBP bn (Pink Book table 10.1, China row, 'Portfolio "
                        "investment liabilities' column; one reference year per edition, "
                        "stitched PB2016->PB2025; end-2014 cell is '-' (nil/<GBP 0.05bn))",
        "windows": f"baseline end-2015->end-2021 (6 annual changes); verdict end-2021->end-{C_VERD_Y1}",
        "levels_gbp_bn": {str(y): r3(v) for y, v in sorted(c_series.items())},
        "test": c_test,
        "reading": (f"The China line ROSE ({m3(c_series[BASE_Y1])} -> "
                    f"{m3(c_series[C_VERD_Y1])} GBP bn, {s3(c_verd)} over {c_years} years; "
                    f"excess {s3(c_excess)} above baseline trend) -- a real, above-trend "
                    f"rise, but below the leg-CONSISTENT bar (0.5 x Bar_low = "
                    f"{m3(LEG_CONSISTENT_MULT * BAR['c']['s1'][0])}): the Scheme-1 bar_low "
                    f"alone ({m3(BAR['c']['s1'][0])}) is "
                    f"{m3(100 * BAR['c']['s1'][0] / c_series[BASE_Y1])}% of the ENTIRE "
                    f"end-2021 China line ({m3(c_series[BASE_Y1])}), and bar_high "
                    f"({m3(BAR['c']['s1'][1])}) is a multiple of it. Rendered leg-ABSENT by "
                    f"the pre-registered rule; the rise is reported, not suppressed. M2 "
                    f"caveat rides: the Pink Book China row is a CPIS-mirror construction and "
                    f"center-routed holdings attribute to the center."),
        "custody_caveat": "ONS Pink Book 2014 CPIS-mirror statement verbatim in "
                          "RDTG_legs_manifest.json",
        "SOURCE": "build/reserve/rdtg_evidence/leg_c_ons_pinkbook{2016..2025}_chapter10.xls[x] "
                  ":: sheet 10.1 China row | ONS Pink Book | parsed 2026-07-02",
    }

    # ---- (d) Canada by-country securities transactions
    legs["d_canada_securities_transactions_china"] = {
        "class": "CHINA-ATTRIBUTED",
        "status": "NOT-AVAILABLE -- absence by construction, not a fetch failure: StatCan's "
                  "international-securities geographic split has no China line (China sits "
                  "inside 'All other countries'); reported, never counted",
        "test": "none (no series to test)",
        "custody_caveat": "StatCan IMDB 1535 intermediary-collection statement verbatim in "
                          "RDTG_legs_manifest.json",
        "SOURCE": "build/reserve/RDTG_legs_manifest.json :: legs."
                  "d_canada_securities_transactions_by_country_china | grounded 2026-07-02",
    }

    # ---- (e) Bund investor structure (aggregate; official split exists)
    e_rows = leg_e_table()
    cb3 = e_rows["Central banks and government sector - third countries"]
    oth3 = e_rows["Other investors - third countries"]
    e_base_pp = cb3["2021-12-31"] - cb3["2020-12-31"]          # single annual change
    e_verd_pp = cb3["2025-06-30"] - cb3["2021-12-31"]          # verdict move, pp
    e_years = 3.5                                              # 2021-12-31 -> 2025-06-30
    de_entry = json.load(open(DENOMS, encoding="utf-8"))["market_outstandings"]["Bund_DE"]
    de_out_2021 = float(de_entry["value"]) / 1e9   # EUR -> EUR bn
    guard(r3(de_out_2021) == r3(float(S1["Bund_DE"]["outstanding_local_bn"])),
          "leg e: denominators Bund outstanding differs from the bars' quoted outstanding")
    legs["e_bund_investor_structure_official_split"] = {
        "class": "AGGREGATE (with an OFFICIAL third-country split -- the closest thing to an "
                 "official split in the sweep)",
        "status": "GROUNDED-PRIMARY -- POWER NOT-COMPUTABLE: baseline support is the single "
                  "annual change 2020-12->2021-12, so sigma_baseline cannot be computed from "
                  "one change and the power test cannot run; the leg is reported with its "
                  "numbers but EXCLUDED from powered counts (within the pre-registered rule: "
                  "unpowered/untestable legs report, never count)",
        "construction": ("SHARES (% of total volume of Federal securities, whole percent, "
                         "point-in-time table 2020-12..2025-06). Conversion to EUR amounts per "
                         "the tasking uses the leg's own publisher denominator: only the "
                         f"end-2021 outstanding (EUR {m3(de_out_2021)} bn incl own holdings, "
                         "RDTG_denominators.json, same publisher) is grounded, so EUR "
                         "equivalents are YARDSTICK-ONLY conversions at the CONSTANT end-2021 "
                         "outstanding, stated; pp moves are the primary numbers."),
        "windows": "baseline 2020-12-31->2021-12-31 ONLY (nearest published boundaries); "
                   "verdict 2021-12-31->2025-06-30 (nearest published boundary), 3.5 years",
        "shares_pct": {
            "central_banks_and_government_third_countries": cb3,
            "other_investors_third_countries": oth3},
        "baseline_single_annual_change_pp": e_base_pp,
        "verdict_window_change_pp": e_verd_pp,
        "verdict_window_change_eur_bn_at_constant_end2021_outstanding (yardstick only)":
            r3(e_verd_pp / 100.0 * de_out_2021),
        "excess_pp_mechanical (= verdict pp - single-change baseline x 3.5; power untestable)":
            r3(e_verd_pp - e_base_pp * e_years),
        "sigma_baseline": "NOT-COMPUTABLE (single baseline annual change)",
        "powered": "NOT-COMPUTABLE -- excluded from powered counts, exclusion stated",
        "bar_low_scheme1_eur_bn_context": r3(BAR["e"]["s1"][0]),
        "bar_low_scheme2_eur_bn_context": r3(BAR["e"]["s2"][0]),
        "prominent_context_reading": (
            f"The OFFICIAL third-country line -- 'Central banks and government sector - third "
            f"countries' -- FELL from {cb3['2021-12-31']}% (2021-12) to {cb3['2025-06-30']}% "
            f"(2025-06) of Federal securities ({e_verd_pp:+d} pp, ~"
            f"{s3(e_verd_pp / 100.0 * de_out_2021)} EUR bn at the constant end-2021 "
            f"outstanding, yardstick only), while 'Other investors - third countries' ROSE "
            f"{oth3['2021-12-31']}% -> {oth3['2025-06-30']}% "
            f"({oth3['2025-06-30'] - oth3['2021-12-31']:+d} pp). The only official-sector "
            f"split in the sweep moved AWAY from official third-country holders over the "
            f"verdict window -- direction ABSENT-side; never counted (power not computable); "
            f"the publisher's 2024 model revision rides the series."),
        "custody_caveat": "Finanzagentur estimation-basis statement + Bundesbank 2018 "
                          "custody-channel corroboration verbatim in RDTG_legs_manifest.json",
        "SOURCE": "build/reserve/rdtg_evidence/leg_e_finanzagentur_investor_structure.html | "
                  "Finanzagentur investor-structure table | parsed 2026-07-02",
    }

    # ---- (f) JGB overseas holdings (aggregate)
    f = leg_f_series()
    jgb, tbill = f["FOF_FFAS500A311"], f["FOF_FFAS500A310"]
    f_base = [jgb[f"{y}04"] - jgb[f"{y-1}04"] for y in range(BASE_Y0, BASE_Y1 + 1)]
    f_verd = jgb["202504"] - jgb["202104"]
    f_test, f_verdict, f_pow, f_pow2, _ = leg_test("f", f_base, f_verd, VERD_YEARS_FULL)
    comb = {q: jgb[q] + tbill[q] for q in jgb if q in tbill}
    comb_base = [comb[f"{y}04"] - comb[f"{y-1}04"] for y in range(BASE_Y0, BASE_Y1 + 1)]
    comb_verd = comb["202504"] - comb["202104"]
    comb_excess = comb_verd - statistics.mean(comb_base) * VERD_YEARS_FULL
    tb_base = [tbill[f"{y}04"] - tbill[f"{y-1}04"] for y in range(BASE_Y0, BASE_Y1 + 1)]
    # variant landings, assertion-guarded (fail loud if the data change):
    guard(BAR["f"]["s1"][0] < sdev(tb_base),
          "leg f T-bill variant no longer unpowered -- extend the variant narration")
    tb_variant_note = "unpowered under the Scheme-1 bar (sigma exceeds it); reported only"
    guard(BAR["f"]["s1"][0] >= sdev(comb_base)
          and comb_excess < LEG_CONSISTENT_MULT * BAR["f"]["s1"][0],
          "leg f combined variant no longer powered+ABSENT -- extend the variant narration")
    comb_variant_verdict = "leg-ABSENT (powered; excess below 0.5 x Bar_low)"
    guard(f_verd < 0, "leg f headline verdict change is not a FALL -- rewrite the reading")
    legs["f_jgb_overseas_holdings"] = {
        "class": "AGGREGATE",
        "status": "GROUNDED-PRIMARY -- TESTED",
        "construction": ("POSITIONS (stocks), quarterly, unit 100 million yen (verified from "
                         "the retained BoJ sjpre_units.xlsx header) converted to JPY bn. "
                         "HEADLINE row: FOF_FFAS500A311 'Central government securities and "
                         "FILP bonds / Overseas / Stock' -- the perimeter closest to the bar's "
                         "MoF General-Bonds outstanding denominator (which excludes Treasury "
                         "discount bills); the T-bill row and the combined sum are carried as "
                         "stated variants; the from-whom-to-whom Overseas row equals the two "
                         "stock rows at both window endpoints (guarded cross-check). FILP-bond "
                         "inclusion in the FOF row vs the General-Bonds denominator is a "
                         "stated perimeter friction."),
        "windows": "baseline Q4/2014->Q4/2021 annual changes; verdict 2021Q4->2025Q4",
        "levels_jpy_bn": {"2021Q4": r3(jgb["202104"]), "2025Q4": r3(jgb["202504"])},
        "test": f_test,
        "variants": {
            "treasury_discount_bills_row (FOF_FFAS500A310)": {
                "baseline_annual_changes": [r3(x) for x in tb_base],
                "sigma_baseline": r3(sdev(tb_base)),
                "verdict_change": r3(tbill["202504"] - tbill["202104"]),
                "powered_scheme1": bool(BAR["f"]["s1"][0] >= sdev(tb_base)),
                "note": tb_variant_note},
            "combined_incl_t_bills": {
                "baseline_annual_changes": [r3(x) for x in comb_base],
                "sigma_baseline": r3(sdev(comb_base)),
                "verdict_change": r3(comb_verd),
                "excess": r3(comb_excess),
                "powered_scheme1": bool(BAR["f"]["s1"][0] >= sdev(comb_base)),
                "leg_verdict_if_it_were_the_headline": comb_variant_verdict,
            }},
        "reading": (f"Overseas holdings of JGBs+FILP bonds FELL {m3(-f_verd)} JPY bn over the "
                    f"verdict window against a {s3(statistics.mean(f_base))}/yr baseline mean "
                    f"-- excess {s3(f_test['excess (= verdict change - baseline mean x years)'])} "
                    f"JPY bn, deeply below the bar. The combined-incl-bills variant lands the "
                    f"same side. M1/M2 caveats ride (the FOF Overseas sector inherits the BOP "
                    f"custodian-attribution perimeter)."),
        "custody_caveat": "BoJ FOF guide (Overseas sector = BOP nonresidents) + BoJ FAQ Q10, "
                          "verbatim in RDTG_legs_manifest.json",
        "SOURCE": "build/reserve/rdtg_evidence/leg_f_boj_fof2_en.zip :: "
                  "ff_dl_fof_quarterly_en.csv rows FOF_FFAS500A311/310, FOF_FFALC08G500 | "
                  "BoJ Flow of Funds | parsed 2026-07-02",
    }

    # ---- (g) gilt overseas holdings (aggregate)
    g = leg_g_series()
    g_base = [g[(y, 4)] - g[(y - 1, 4)] for y in range(BASE_Y0, BASE_Y1 + 1)]
    g_verd = g[(2025, 4)] - g[(2021, 4)]
    g_test, g_verdict, g_pow, g_pow2, _ = leg_test("g", g_base, g_verd, VERD_YEARS_FULL)
    guard(not g_pow and not g_pow2,
          "leg g status narrates UNPOWERED at both bars -- another landing computed")
    legs["g_gilt_overseas_holdings"] = {
        "class": "AGGREGATE",
        "status": "GROUNDED-PRIMARY -- TESTED; UNPOWERED at both bars (sigma_baseline exceeds "
                  "Bar_low under Scheme 1 and Scheme 2): reported, never counted",
        "construction": ("POSITIONS, GBP bn, ONS CDID HEWD (UKEA), quarterly, MARKET VALUE "
                         "current prices -- the bars are built on NOMINAL outstandings: a "
                         "stated basis friction (the tonnage-not-value lesson says flag it and "
                         "compute on what the leg publishes; the 2022 gilt-price fall moves "
                         "this series without any tonnage change). Annual rows equal Q4 rows "
                         "(guarded)."),
        "windows": "baseline Q4/2014->Q4/2021 annual changes; verdict 2021Q4->2025Q4",
        "levels_gbp_bn": {"2021Q4": r3(g[(2021, 4)]), "2022Q4 (gilt-price crash year, context)":
                          r3(g[(2022, 4)]), "2025Q4": r3(g[(2025, 4)])},
        "test": g_test,
        "reading": (f"Overseas gilt holdings at market value were near-FLAT over the verdict "
                    f"window ({s3(g_verd)} GBP bn on a {m3(g[(2021, 4)])} base) against a "
                    f"{s3(statistics.mean(g_base))}/yr baseline mean -- excess "
                    f"{s3(g_test['excess (= verdict change - baseline mean x years)'])} GBP bn "
                    f"-- but sigma_baseline {m3(sdev(g_base))} exceeds Bar_low "
                    f"{m3(BAR['g']['s1'][0])}, so the leg is UNPOWERED and never counted; the "
                    f"market-value basis makes both the baseline sigma and the verdict change "
                    f"price-contaminated (stated)."),
        "custody_caveat": "no custody-specific ONS caveat found for HEWD; the same compiler's "
                          "CPIS-mirror attribution basis (leg c) stated in "
                          "RDTG_legs_manifest.json; DMO revision note quoted there",
        "SOURCE": "build/reserve/rdtg_evidence/leg_g_ons_hewd_ukea_overseas_gilt_holdings.csv "
                  "| ONS UKEA HEWD | parsed 2026-07-02",
    }

    # ---- (h) OAT nonresident share
    hm = MANIFEST["legs"]["h_oat_nonresident_share"]
    chart_vals = re.findall(r"(\d+\.\d+) \.\.\. (\d+\.\d+) %",
                            hm["partial_compiler_published_data_retained"])
    guard(len(chart_vals) == 1, "leg h: could not parse the BdF chart endpoint values from "
                                "the committed manifest")
    legs["h_oat_nonresident_share"] = {
        "class": "AGGREGATE",
        "status": "NOT-AVAILABLE -- the series exists at the publisher but is unfetchable from "
                  "this egress (AFT Cloudflare-blocked; BdF webstat exports empty portal-wide; "
                  "BdF API requires credentials -- evidence retained); no baseline -> no test; "
                  "reported, never counted",
        "test": "none (observations not obtainable)",
        "context_only_no_test": {
            "bdf_chart_general_government_nonresident_share_of_long_term_debt_pct": {
                "2022Q3": float(chart_vals[0][0]), "2025Q3": float(chart_vals[0][1]),
                "note": "compiler chart data, 2022Q3->2025Q3 only (verdict-window-partial; "
                        "perimeter differs from the State-debt share); CONTEXT ONLY, no "
                        "baseline exists on disk so no test is run"},
            "publisher_metadata_last_two_obs_of_the_blocked_series_pct":
                hm["series_grounded_from_publisher_metadata"]["last_two_observations_from_metadata"],
        },
        "custody_caveat": "BdF Stat Info holdings-from-custodian-statements sentence verbatim "
                          "in RDTG_legs_manifest.json",
        "SOURCE": "build/reserve/RDTG_legs_manifest.json :: legs.h_oat_nonresident_share | "
                  "grounded 2026-07-02",
    }

    # ---- (i) AGS nonresident general-government debt securities (aggregate)
    pos, tx = leg_i_series()
    i_base = [pos[f"{y}-Q4"] - pos[f"{y-1}-Q4"] for y in range(BASE_Y0, BASE_Y1 + 1)]
    i_verd = pos["2025-Q4"] - pos["2021-Q4"]
    i_test, i_verdict, i_pow, i_pow2, _ = leg_test("i", i_base, i_verd, VERD_YEARS_FULL)
    guard(not i_pow and not i_pow2,
          "leg i status narrates UNPOWERED -- another landing computed")
    t_base = [sum(tx[f"{y}-Q{q}"] for q in range(1, 5)) for y in range(BASE_Y0, BASE_Y1 + 1)]
    t_verd = sum(tx[f"{y}-Q{q}"] for y in range(VERD_Y0, VERD_Y1 + 1) for q in range(1, 5))
    t_sig = sdev(t_base)
    t_excess = t_verd - statistics.mean(t_base) * VERD_YEARS_FULL
    guard(BAR["i"]["s2"][0] < t_sig,
          "leg i transactions variant no longer unpowered -- extend the variant narration")
    t_variant_verdict = "UNPOWERED -- reported, never counted"
    guard(i_verd > 0, "leg i positions verdict change is not a rise -- rewrite the reading")
    legs["i_ags_nonresident_gg_debt_securities"] = {
        "class": "AGGREGATE",
        "status": "GROUNDED-ALTERNATE-OFFICIAL (ABS 5302.0 IIP; AOFM primary blocked) -- "
                  "TESTED; UNPOWERED at the Scheme-2 bar in BOTH variants: reported, never "
                  "counted. Scheme-1 bar NOT-COMPUTABLE for AU (outstanding NOT-GROUNDED) -> "
                  "the Scheme-2 AUD bar is the power yardstick, stated.",
        "construction": ("HEADLINE: POSITIONS, end-of-period (ABS measure 6, 'Position at end "
                         "of period'), AUD bn, market-value IIP convention; the leg is GENERAL "
                         "GOVERNMENT total (AGS plus state/territory issuers -- broader than "
                         "AGS-only, dilution stated). FLOW-TEST VARIANT: transactions (measure "
                         "2, 'Changes in position reflecting - transactions'), both reported. "
                         "Beginning/end-of-period coherence guarded."),
        "windows": "baseline Q4/2014->Q4/2021 annual changes; verdict 2021Q4->2025Q4 "
                   "(transactions variant: annual sums / cumulative)",
        "levels_aud_bn": {"2021Q4": r3(pos["2021-Q4"]), "2025Q4": r3(pos["2025-Q4"])},
        "test": i_test,
        "transactions_variant": {
            "baseline_annual_flow_sums": [r3(x) for x in t_base],
            "sigma_baseline": r3(t_sig),
            "verdict_cumulative": r3(t_verd),
            "excess": r3(t_excess),
            "powered_at_scheme2_bar": bool(BAR["i"]["s2"][0] >= t_sig),
            "leg_verdict": t_variant_verdict,
        },
        "reading": (f"Nonresident holdings of Australian general-government debt securities "
                    f"rose {s3(i_verd)} AUD bn over the verdict window, below the "
                    f"baseline-trend expectation (excess "
                    f"{s3(i_test['excess (= verdict change - baseline mean x years)'])} "
                    f"positions / {s3(t_excess)} transactions), but sigma_baseline "
                    f"({m3(sdev(i_base))} positions / {m3(t_sig)} transactions) exceeds the "
                    f"Scheme-2 bar_low {m3(BAR['i']['s2'][0])} -- UNPOWERED both ways, never "
                    f"counted."),
        "custody_caveat": "ABS Form-85L nominee-survey sentence verbatim in "
                          "RDTG_legs_manifest.json",
        "SOURCE": "build/reserve/rdtg_evidence/leg_i_abs_iip_653B_gg_foreign_liab_debtsec.csv "
                  "| ABS IIP (5302.0) via SDMX | parsed 2026-07-02",
    }

    # % of the leg's own nonresident level (bars promised this column per leg)
    legs["c_uk_pinkbook_china_pi_liabilities"]["bar_low_s1_pct_of_leg_end2021_level"] = \
        r3(100 * BAR["c"]["s1"][0] / c_series[2021])
    legs["f_jgb_overseas_holdings"]["bar_low_s1_pct_of_leg_end2021_level"] = \
        r3(100 * BAR["f"]["s1"][0] / jgb["202104"])
    legs["g_gilt_overseas_holdings"]["bar_low_s1_pct_of_leg_end2021_level"] = \
        r3(100 * BAR["g"]["s1"][0] / g[(2021, 4)])
    legs["i_ags_nonresident_gg_debt_securities"]["bar_low_s2_pct_of_leg_end2021_level"] = \
        r3(100 * BAR["i"]["s2"][0] / pos["2021-Q4"])
    legs["b_euroarea_bop_china_pi_liabilities"]["bar_context_s1_pct_of_leg_end2021_level"] = \
        r3(100 * BAR["b"]["s1"][0] / b["2021-Q4"])

    summary = {
        "tested": {"a": a_verdict, "c": c_verdict, "f": f_verdict, "g": g_verdict,
                   "i": i_verdict},
        "powered_headline": {"a": a_pow, "c": c_pow, "f": f_pow, "g": g_pow, "i": i_pow},
        "powered_scheme2": {"a": a_pow2, "c": c_pow2, "f": f_pow2, "g": g_pow2, "i": i_pow2},
        "china_attributed_ids": ["a", "b", "c", "d"],
        "aggregate_ids": ["e", "f", "g", "h", "i"],
        "excluded": {"b": "NOT-TESTABLE", "d": "NOT-AVAILABLE",
                     "e": "POWER NOT-COMPUTABLE", "h": "NOT-AVAILABLE"},
    }
    return legs, summary


# ---------------------------------------------------------------------------
# 6. Part C -- the sweep verdict (mechanical, over powered grounded legs)
# ---------------------------------------------------------------------------

def sweep(summary):
    verdicts = summary["tested"]
    powered = {k for k, v in summary["powered_headline"].items() if v}
    n_pow = len(powered)
    n_cons = sum(1 for k in powered if verdicts[k] == "leg-CONSISTENT")
    n_abs = sum(1 for k in powered if verdicts[k] == "leg-ABSENT")
    china_pow = powered & set(summary["china_attributed_ids"])
    china_consistent = any(verdicts[k] == "leg-CONSISTENT" for k in china_pow)

    def v_consistent():
        guard(n_pow >= MIN_POWERED_LEGS and (n_cons >= SWEEP_HALF * n_pow or china_consistent),
              "DESTINATION-CONSISTENT branch invoked out of condition")
        return "DESTINATION-CONSISTENT", None

    def v_absent():
        guard(n_pow >= MIN_POWERED_LEGS and n_abs >= SWEEP_THREE_QUARTERS * n_pow
              and not china_consistent, "DESTINATION-ABSENT branch invoked out of condition")
        sentence = (
            f"MECHANICAL SWEEP VERDICT: DESTINATION-ABSENT -- {n_abs} of {n_pow} powered "
            f"grounded legs are leg-ABSENT (>= three-quarters) and no China-attributed leg is "
            f"leg-CONSISTENT -- AND, per the pre-registration, this verdict sentence carries "
            f"its own masking caveat: {M1_CONSEQUENCE} Reserve assets bought through external "
            f"managers, custodians or financial centers would NOT appear on these legs (M1: "
            f"the destination compilers' own 'custodial bias'; M2: {M2_CONSEQUENCE}) -- so "
            f"DESTINATION-ABSENT is weak evidence against arrival in these six sovereign "
            f"markets under these compilers' attribution, not disposal of the true-departure "
            f"branch."
        )
        return "DESTINATION-ABSENT", sentence

    def v_unpowered():
        guard(n_pow < MIN_POWERED_LEGS, "UNPOWERED branch invoked with >= 3 powered legs")
        return "UNPOWERED", None

    def v_indeterminate():
        guard(n_pow >= MIN_POWERED_LEGS
              and not (n_cons >= SWEEP_HALF * n_pow or china_consistent)
              and not (n_abs >= SWEEP_THREE_QUARTERS * n_pow and not china_consistent),
              "INDETERMINATE branch invoked out of condition")
        return "INDETERMINATE", None

    if n_pow < MIN_POWERED_LEGS:
        verdict, sentence = v_unpowered()
    elif n_cons >= SWEEP_HALF * n_pow or china_consistent:
        verdict, sentence = v_consistent()
    elif n_abs >= SWEEP_THREE_QUARTERS * n_pow and not china_consistent:
        verdict, sentence = v_absent()
    else:
        verdict, sentence = v_indeterminate()

    guard(verdict == "DESTINATION-ABSENT" and sentence is not None,
          "the assembled narration below renders the DESTINATION-ABSENT landing; another "
          "landing computed -- extend the narration for it before amending")

    # Scheme-2 variant sweep (bars alongside per the pre-registration)
    powered2 = {k for k, v in summary["powered_scheme2"].items() if v}
    n_pow2 = len(powered2)
    guard(n_pow2 < MIN_POWERED_LEGS,
          "Scheme-2 variant no longer UNPOWERED -- extend the variant narration")
    variant = (
        f"Scheme-2 (COFER-share) bars variant: UNPOWERED -- only {n_pow2} powered grounded "
        f"leg(s) ({', '.join(sorted(powered2))}) because the JPY bar shrinks to the COFER JPY "
        f"share; the headline sweep is Scheme 1 (market-size-proportional) as tasked, the "
        f"variant stated alongside."
    )
    return {
        "rule": ("DESTINATION-CONSISTENT iff >= half of powered grounded legs are "
                 "leg-CONSISTENT or any China-attributed leg is; DESTINATION-ABSENT iff >= "
                 "three-quarters are leg-ABSENT and no China-attributed leg is leg-CONSISTENT "
                 "(the verdict sentence itself carries the masking caveat); UNPOWERED iff "
                 "fewer than 3 powered grounded legs; INDETERMINATE otherwise (pre-registered)"),
        "powered_grounded_legs_headline_scheme1": sorted(powered),
        "n_powered": n_pow,
        "n_leg_consistent": n_cons,
        "n_leg_absent": n_abs,
        "china_attributed_leg_consistent": bool(china_consistent),
        "unpowered_reported_not_counted": sorted(k for k, v in
                                                 summary["powered_headline"].items() if not v),
        "excluded_reported_not_counted": summary["excluded"],
        "verdict": verdict,
        "verdict_sentence": sentence,
        "scheme2_variant": {"powered_legs": sorted(powered2), "n_powered": n_pow2,
                            "verdict": "UNPOWERED", "statement": variant},
        "preregistered_expectation_check": (
            "Pre-registered primary was 'UNPOWERED or INDETERMINATE on the sweep and "
            "FLAT-or-SUPPRESSED on I.B'. I.B landed FLAT (the expected side). The Scheme-1 "
            "sweep landed DESTINATION-ABSENT -- the pre-registered primary is REFUTED toward "
            "DESTINATION-ABSENT on the pre-stated branch ('REFUTED toward DESTINATION-ABSENT "
            "if powered legs sit flat across the sweep'); the Scheme-2 variant lands the "
            "expected UNPOWERED. All landings promotable; recorded, not smoothed."),
    }, sentence, verdict


# ---------------------------------------------------------------------------
# 7. Part D -- the fork-interval annotation (consequence rules pre-committed)
# ---------------------------------------------------------------------------

def interval_annotation(sweep_verdict, china_consistent):
    def toward_true_departure():
        guard(sweep_verdict == "DESTINATION-CONSISTENT",
              "toward-true-departure annotation invoked out of condition")
        return "weight toward TRUE-DEPARTURE"

    def toward_reparking():
        guard(sweep_verdict == "DESTINATION-ABSENT",
              "toward-re-parking annotation invoked out of condition")
        return ("weight toward RE-PARKING, MASKING-CAPPED (the pre-committed consequence of "
                "DESTINATION-ABSENT: a null is weak evidence, not disposal)")

    def unmoved():
        guard(sweep_verdict in ("UNPOWERED", "INDETERMINATE"),
              "unmoved annotation invoked out of condition")
        return "weight UNMOVED"

    if sweep_verdict == "DESTINATION-CONSISTENT":
        ann = toward_true_departure()
    elif sweep_verdict == "DESTINATION-ABSENT":
        ann = toward_reparking()
    else:
        ann = unmoved()

    # Endpoints change ONLY on construction-grade attribution; the pre-registration
    # states no receiving leg can carry it (a rising China line is attribution-grade
    # for that compiler perimeter only) -- and no China-attributed leg is even
    # leg-CONSISTENT here. Both facts guarded.
    guard(not china_consistent, "a China-attributed leg is CONSISTENT -- re-read the "
                                "pre-registration's endpoint rule before amending")
    return {
        "fork_interval_busd (read from RDTF_result.json :: part1_route_robust_ceiling."
        "route_robust_interval.interval_busd)": [r3(x) for x in FORK_INTERVAL],
        "endpoints": "UNCHANGED -- no leg carried construction-grade attribution (the "
                     "pre-registration: no receiving leg above can; and no China-attributed "
                     "leg is leg-CONSISTENT). Expected amendment: annotation only -- met.",
        "annotation": ann,
        "annotation_with_ib": (
            "Both untried discriminators landed on the same side and neither resolves the "
            "fork: the destination sweep is DESTINATION-ABSENT (masking-capped) and China's "
            "own I.B line is FLAT (slightly negative) -- no visible arrival in the candidate "
            "sovereign markets under their compilers' attribution, and no re-parking surge "
            "into China's own disclosed non-reserve FX assets. The pre-committed consequence "
            "rule moves weight toward re-parking/masking-capped readings of the fork; the "
            "interval's endpoints stand at " + m3(FORK_INTERVAL[0]) + ".." +
            m3(FORK_INTERVAL[1]) + " $bn."),
        "masking_consequences_pre_committed": {"M1": M1_CONSEQUENCE, "M2": M2_CONSEQUENCE},
    }


# ---------------------------------------------------------------------------
# 8. Payload
# ---------------------------------------------------------------------------

def build_payload():
    part_a_obj, ib_sentence, ib_verdict = part_a()
    legs, summary = part_b()
    sweep_obj, sweep_sentence, sweep_verdict = sweep(summary)
    ann_obj = interval_annotation(sweep_verdict, sweep_obj["china_attributed_leg_consistent"])

    payload = {
        "task": "RDT-G Phase 3 ASSEMBLY (pre-registration: build/reserve/RDTG_prediction.md, "
                "commit 7ad70d2)",
        "establishment": (
            "NOT ESTABLISHED -- output of RDTG_recompute.py; every number and every verdict "
            "below is an OUTPUT, not established, until the RDT-G verifier scenario runs "
            "(build/reserve/RDTG_verify.json with all_pass=true, byte-reproducing this file "
            "and the amended object from the committed inputs) AND the human gate reviews "
            "this stage."),
        "built_utc_date": "2026-07-02",
        "windows": {
            "baseline": "calendar 2015->2021 (leg-specific nearest published boundaries "
                        "stated per leg)",
            "verdict_legs": "calendar 2022->2025 (leg-specific truncations stated per leg)",
            "verdict_ib": "2022-01 -> latest published (2026-05), per the pre-registered "
                          "I.B wording; both endpoint conventions reported",
            "note": "RDT-G freeze-era windows, deliberately distinct from the RDT-B..F "
                    "monthly verdict axis; both facts stated (pre-registered)."},
        "part_a_ib_verdict": part_a_obj,
        "part_b_leg_tests": {
            "rule": ("Per grounded leg, local currency: excess = verdict-window change - "
                     "baseline mean annual change x verdict years; POWERED iff Bar_low >= "
                     "sigma_baseline; leg-CONSISTENT iff excess >= 0.5 x Bar_low (powered); "
                     "leg-ABSENT iff excess < 0.5 x Bar_low (powered); unpowered/untestable "
                     "legs report, never count. Scheme 1 bars = headline; Scheme 2 alongside. "
                     "China-attributed legs reported separately from aggregate legs."),
            "china_attributed_legs": {k: v for k, v in legs.items()
                                      if v.get("class", "").startswith("CHINA")},
            "aggregate_legs": {k: v for k, v in legs.items()
                               if not v.get("class", "").startswith("CHINA")},
        },
        "part_c_sweep_verdict": sweep_obj,
        "part_d_fork_interval_annotation": ann_obj,
        "masking_mechanisms": {
            "M1_external_managers_custodians": {
                "grounding": "IMF Revised Guidelines (2013) + US Treasury/TIC SHL2024r "
                             "'custodial bias' passages, verbatim in RDTG_legs_manifest.json "
                             "(retained PDFs in rdtg_evidence/)",
                "tic_quote": M1_TIC_QUOTE,
                "consequence_pre_committed": M1_CONSEQUENCE},
            "M2_counterpart_attribution": {
                "grounding": "compiler-side statements retained per leg (BoJ FAQ Q10; ECB "
                             "quality report fn. 8; ONS CPIS-mirror; StatCan IMDB 1535; ABS "
                             "Form 85L; BdF custodian statements) -- RDTG_legs_manifest.json",
                "consequence_pre_committed": M2_CONSEQUENCE},
        },
        "mass_and_bars": {
            "mass_endpoints_busd": [r3(LOWER_MASS), r3(UPPER_MASS)],
            "bars_artifact": "build/reserve/RDTG_bars.json (committed BEFORE any "
                             "discriminator was read; sequencing attestation carried there)",
            "stated_limitation_direction": BARS_J["stated_limitation"],
        },
        "inputs_sha256": INPUTS_SHA,
        "no_date_no_probability_no_currency_guess": (
            "no breaking-point date, no probability, and no destination-currency guess "
            "anywhere in the RDT-G outputs (the k1 wall stands)"),
        "SOURCE": [
            "build/reserve/RDTG_prediction.md (commit 7ad70d2) | pre-registration | every "
            "rule above implemented as committed | read 2026-07-02",
            "build/reserve/RDTG_bars.json | committed magnitude bars | yardsticks read, "
            "never recomputed | read 2026-07-02",
            "build/reserve/RDTG_ib_series.csv + RDTG_ib_staging.json | committed I.B parse | "
            "re-derived and cross-checked here | read 2026-07-02",
            "build/reserve/RDTG_legs_manifest.json + RDTG_legs_provenance.md + "
            "rdtg_evidence/leg_* | committed leg grounding + RAW retained series | all leg "
            "tests computed from the raw files | read 2026-07-02",
            "build/reserve/RDTD_result.json :: identity.china_alone.delta_non_us_busd | "
            "upper mass + I.B threshold base | read 2026-07-02",
            "build/reserve/RDTE_result.json :: cross_flow_sensitivity_detail.positive_months_"
            "proxy_variant.total_busd | lower-mass derivation | read 2026-07-02",
            "build/reserve/RDTF_result.json :: part1_route_robust_ceiling."
            "route_robust_interval.interval_busd | the fork interval annotated | read "
            "2026-07-02",
        ],
    }
    ctx = {"ib_sentence": ib_sentence, "ib_verdict": ib_verdict, "legs": legs,
           "summary": summary, "sweep": sweep_obj, "sweep_sentence": sweep_sentence,
           "sweep_verdict": sweep_verdict, "ann": ann_obj, "part_a": part_a_obj}
    return payload, ctx


# ---------------------------------------------------------------------------
# 9. Object amendment (insert-only; strip-and-reinsert; RDTB..RDTF precedent)
# ---------------------------------------------------------------------------

MARK_BEGIN = "<!-- RDTG-AMEND:BEGIN"
MARK_END = "<!-- RDTG-AMEND:END"


def strip_amendment(text):
    out, skip = [], False
    for line in text.splitlines(keepends=True):
        s = line.lstrip()
        if s.startswith(MARK_BEGIN):
            guard(not skip, "nested RDTG-AMEND BEGIN")
            skip = True
            continue
        if s.startswith(MARK_END):
            guard(skip, "RDTG-AMEND END without BEGIN")
            skip = False
            continue
        if not skip:
            out.append(line)
    guard(not skip, "unterminated RDTG-AMEND block")
    return "".join(out)


def leg_table_rows(ctx):
    L = ctx["legs"]

    def row(label, leg, tkey="test"):
        t = leg.get(tkey)
        if not isinstance(t, dict):
            return None
        b1 = t["bar_low_scheme1_local_bn"]
        b1s = m3(b1) if isinstance(b1, float) else "N/C"
        pw = "POWERED" if t["powered_headline (Bar_low >= sigma_baseline)"] else "unpowered"
        pw2 = "POWERED" if t["powered_scheme2_variant"] else "unpowered"
        return (f"| {label} | {s3(t['baseline_mean_annual_change'])} | "
                f"{m3(t['sigma_baseline (sample stdev, ddof=1 -- larger-sigma convention, conservative for the power test)'])} | "
                f"{s3(t['verdict_window_change'])} | "
                f"{s3(t['excess (= verdict change - baseline mean x years)'])} | "
                f"{b1s} / {m3(t['bar_low_scheme2_local_bn'])} | {pw} (S2: {pw2}) | "
                f"**{t['leg_verdict_headline'].split(' --')[0]}** |\n")

    a = row("(a) Japan BOP vs China PI liabilities, JPY bn, FLOWS (cumulative; stated "
            "extension), verdict 2022Q1->2025Q4", L["a_japan_bop_vs_china_pi_liabilities"])
    c = row("(c) UK Pink Book China PI liabilities, GBP bn, positions, verdict end-2021->"
            "end-2023 (truncated, stated)", L["c_uk_pinkbook_china_pi_liabilities"])
    f = row("(f) JGB overseas holdings (JGB+FILP excl bills), JPY bn, positions, verdict "
            "2021Q4->2025Q4", L["f_jgb_overseas_holdings"])
    g = row("(g) gilt overseas holdings (HEWD, market value -- stated friction), GBP bn, "
            "positions, verdict 2021Q4->2025Q4", L["g_gilt_overseas_holdings"])
    i = row("(i) AGS nonresident general-government debt securities (ABS IIP; GG>AGS "
            "dilution stated), AUD bn, positions, verdict 2021Q4->2025Q4",
            L["i_ags_nonresident_gg_debt_securities"])
    guard(all(x is not None for x in (a, c, f, g, i)), "leg table row missing")

    Lb = L["b_euroarea_bop_china_pi_liabilities"]
    b = (f"| (b) euro-area BOP China PI liabilities, EUR bn, positions | -- | "
         f"{m3(Lb['sigma_baseline_context_eur_bn'])} (context) | "
         f"{s3(Lb['partial_verdict_change_2021Q4_to_2022Q3_eur_bn (context only)'])} "
         f"(2021Q4->2022Q3 PARTIAL, context) | -- | "
         f"{m3(BAR['b']['s1'][0])} / {m3(BAR['b']['s2'][0])} (context) | -- | "
         f"**NOT-TESTABLE** (series ends 2022Q3; flows-liabilities cell structurally absent) |\n")
    d = ("| (d) Canada by-country securities transactions | -- | -- | -- | -- | -- | -- | "
         "**NOT-AVAILABLE** (absence by construction: no China line, China inside 'All "
         "other countries') |\n")
    Le = L["e_bund_investor_structure_official_split"]
    e = (f"| (e) Bund investor structure (Finanzagentur; OFFICIAL third-country split), % "
         f"shares -> EUR yardstick | {Le['baseline_single_annual_change_pp']:+d} pp (single "
         f"change) | NOT-COMPUTABLE | {Le['verdict_window_change_pp']:+d} pp (~"
         f"{s3(Le['verdict_window_change_eur_bn_at_constant_end2021_outstanding (yardstick only)'])} "
         f"EUR bn at constant end-2021 outstanding, yardstick) | "
         f"{s3(Le['excess_pp_mechanical (= verdict pp - single-change baseline x 3.5; power untestable)'])} pp | "
         f"{m3(BAR['e']['s1'][0])} / {m3(BAR['e']['s2'][0])} | power NOT-COMPUTABLE | "
         f"**reported, never counted** |\n")
    Lh = L["h_oat_nonresident_share"]["context_only_no_test"][
        "bdf_chart_general_government_nonresident_share_of_long_term_debt_pct"]
    h = (f"| (h) OAT nonresident share | -- | -- | (context: BdF chart GG nonresident "
         f"LT-debt share {Lh['2022Q3']}% (2022Q3) -> {Lh['2025Q3']}% (2025Q3), no baseline) "
         f"| -- | {m3(BAR['h']['s1'][0])} / {m3(BAR['h']['s2'][0])} (context) | -- | "
         "**NOT-AVAILABLE** (unfetchable from this egress; evidence retained) |\n")
    header = ("| leg (construction; verdict window) | baseline mean ann. Δ | σ_baseline | "
              "verdict Δ | excess | Bar_low S1 / S2 | power | leg verdict |\n"
              "|---|---|---|---|---|---|---|---|\n")
    china_table = header + a + b + c + d
    agg_table = header + e + f + g + h + i
    return china_table, agg_table


def build_blocks(ctx, post_rdtf_sha):
    guard(ctx["ib_verdict"] == "FLAT" and ctx["sweep_verdict"] == "DESTINATION-ABSENT",
          "the assembled RDTG blocks narrate the FLAT + DESTINATION-ABSENT landing; another "
          "landing computed -- extend the narration for it before amending")
    china_table, agg_table = leg_table_rows(ctx)
    sw = ctx["sweep"]
    Lc = ctx["legs"]["c_uk_pinkbook_china_pi_liabilities"]
    Le = ctx["legs"]["e_bund_investor_structure_official_split"]
    cb3v = Le["shares_pct"]["central_banks_and_government_third_countries"]
    oth3v = Le["shares_pct"]["other_investors_third_countries"]
    disc = ctx["part_a"]["disclosure_finding"]
    ib_blanks = disc["blank_months_per_sub_line"]
    ib_n = disc["months_in_corpus"]
    # the "(i)..(iii)" narration below names the powered sets explicitly -- guard them
    powered = {k for k, v in ctx["summary"]["powered_headline"].items() if v}
    guard(sorted(powered & set(ctx["summary"]["china_attributed_ids"])) == ["a", "c"]
          and sorted(powered & set(ctx["summary"]["aggregate_ids"])) == ["f"],
          "the narration names powered legs {a,c} (China) and {f} (aggregate); another set "
          "computed -- extend the narration")

    block_main = (
        "<!-- RDTG-AMEND:BEGIN receiving-side-ib -->\n"
        f"**RDT-G annotation (the receiving side + China's I.B line — the two untried "
        f"discriminators, `RDTG_result.json`):** RDT-F left the fork ΔnonUS-true ∈ "
        f"[{m3(FORK_INTERVAL[0])}, {m3(FORK_INTERVAL[1])}] $bn route-robustly open; RDT-G runs "
        f"the two pre-registered discriminators that were never tried — China's own SDDS "
        f"Section I.B and the destination countries' own books — on the freeze-era windows "
        f"(baseline 2015→2021, verdict 2022→2025; deliberately distinct from the RDT-B..F "
        f"monthly axis, both stated). Neither can RESOLVE the fork (both masking mechanisms "
        f"cap what any leg can claim, consequences pre-committed); each moves weight honestly. "
        f"**{ctx['ib_sentence']}** **{ctx['sweep_sentence']}** "
        f"{sw['scheme2_variant']['statement']} Pre-registered-expectation check: I.B landed "
        f"FLAT (the expected side); the Scheme-1 sweep REFUTED the pre-registered primary "
        f"(UNPOWERED/INDETERMINATE) toward DESTINATION-ABSENT on the pre-stated branch. "
        f"Magnitude bars (committed before any discriminator was read, "
        f"`RDTG_bars.json`): mass [{m3(LOWER_MASS)}, {m3(UPPER_MASS)}] $bn allocated per "
        f"market — bars OVERSTATE what any one market should show (candidate set is not the "
        f"universe of destinations), making a null WEAKER, never stronger. Per-leg tables "
        f"(all nine legs, China-attributed SEPARATE from aggregate, every leg reported "
        f"whatever it shows; local currency; excess = verdict Δ − baseline mean × years; "
        f"POWERED iff Bar_low ≥ σ_baseline; σ = sample stdev of baseline annual changes):\n"
        f"\n"
        f"China-attributed legs:\n"
        f"\n" + china_table +
        f"\n"
        f"Aggregate legs:\n"
        f"\n" + agg_table +
        f"\n"
        f"Read plainly, three facts carry the sweep: (i) the only two POWERED China-attributed "
        f"legs move the WRONG WAY or too little — China net SOLD Japanese portfolio "
        f"securities over the verdict window (cumulative "
        f"{s3(ctx['legs']['a_japan_bop_vs_china_pi_liabilities']['test']['verdict_window_change'])} "
        f"JPY bn against a positive baseline), and the UK Pink Book China line ROSE above "
        f"trend ({s3(Lc['test']['verdict_window_change'])} GBP bn, excess "
        f"{s3(Lc['test']['excess (= verdict change - baseline mean x years)'])}) but the "
        f"Scheme-1 bar_low allocated to the UK market alone ({m3(BAR['c']['s1'][0])} GBP bn) "
        f"is {m3(Lc['bar_low_s1_pct_of_leg_end2021_level'])}% of the ENTIRE end-2021 China "
        f"line ({Lc['levels_gbp_bn']['2021']}) — an above-trend rise below the "
        f"leg-CONSISTENT threshold (0.5 × Bar_low = "
        f"{m3(LEG_CONSISTENT_MULT * BAR['c']['s1'][0])}), rendered leg-ABSENT by the "
        f"pre-registered rule and reported, not suppressed; (ii) the powered aggregate leg "
        f"(JGB overseas holdings) FELL {s3(ctx['legs']['f_jgb_overseas_holdings']['test']['verdict_window_change'])} "
        f"JPY bn against a positive baseline mean; (iii) the closest thing to an official "
        f"split in the sweep — the Finanzagentur 'Central banks and government sector - third "
        f"countries' Bund line — FELL {cb3v['2021-12-31']}% → {cb3v['2025-06-30']}% of "
        f"Federal securities over the verdict window ({Le['verdict_window_change_pp']:+d} pp, "
        f"~{s3(Le['verdict_window_change_eur_bn_at_constant_end2021_outstanding (yardstick only)'])} "
        f"EUR bn at constant end-2021 outstanding, yardstick only) while 'Other investors - "
        f"third countries' rose {oth3v['2025-06-30'] - oth3v['2021-12-31']:+d} pp — direction "
        f"ABSENT-side, power NOT-COMPUTABLE, never counted. I.B DISCLOSURE finding riding the "
        f"FLAT verdict: the I.B total is published in all {ib_n} months (so SUPPRESSED does "
        f"not attach), but gold and 'other' sub-lines are blank in {ib_blanks['ib_gold']}/"
        f"{ib_n} and {ib_blanks['ib_other']}/{ib_n} months, deposits in "
        f"{ib_blanks['ib_deposits']}/{ib_n}, loans in "
        f"{', '.join(disc['loans_blank_months'])} — "
        f"sub-lines reported wherever published, blanks never interpolated. "
        f"**Fork interval [{m3(FORK_INTERVAL[0])}, {m3(FORK_INTERVAL[1])}] $bn — ENDPOINTS "
        f"UNCHANGED** (no leg carried construction-grade attribution; the pre-registration "
        f"expected annotation only, and that is what this is); **ANNOTATION (pre-committed "
        f"consequence rule): weight moves toward RE-PARKING, MASKING-CAPPED** — both "
        f"discriminators landed on the same side (destinations ABSENT under their compilers' "
        f"attribution; China's own disclosed non-reserve FX assets FLAT), which weighs toward "
        f"re-parking/masking-capped readings of the fork without resolving it. The k1 wall "
        f"stands: no destination currency is identified. No date, no probability, no currency "
        f"guess.\n"
        "<!-- RDTG-AMEND:END receiving-side-ib -->\n"
    )

    block_hazard = (
        "<!-- RDTG-AMEND:BEGIN hazard-receiving-side -->\n"
        f"**RDT-G annotation on the perimeter fork, from the receiving side "
        f"(`RDTG_result.json`):** the two untried discriminators both landed null-side and "
        f"neither resolves the fork: the destination sweep over the pre-registered nine legs "
        f"is **DESTINATION-ABSENT** ({sw['n_leg_absent']}/{sw['n_powered']} powered grounded "
        f"legs leg-ABSENT, no China-attributed leg leg-CONSISTENT; Scheme-2 bars variant "
        f"UNPOWERED, stated), and China's own SDDS Section I.B line is **FLAT** "
        f"(ΔI.B {s3(ctx['ib_delta'])} $bn vs the ±{m3(IB_THRESHOLD)} threshold, both endpoint "
        f"conventions). Per the pre-committed consequence rules the fork interval "
        f"[{m3(FORK_INTERVAL[0])}, {m3(FORK_INTERVAL[1])}] $bn keeps its ENDPOINTS and takes "
        f"weight toward RE-PARKING, MASKING-CAPPED — a null is weak evidence, not disposal: "
        f"reserves buying through external managers, custodians or financial centers would "
        f"not appear on any of these legs (M1/M2, grounded quotes in "
        f"`RDTG_legs_manifest.json`). The destination currency stays UNDETERMINED (the k1 "
        f"wall); the pool caveat rides. Not a forecast, no date, no probability.\n"
        "<!-- RDTG-AMEND:END hazard-receiving-side -->\n"
    )

    block_lim = (
        "<!-- RDTG-AMEND:BEGIN limitations-rdtg -->\n"
        f"   - **RDT-G caveats on the receiving-side sweep and the I.B verdict "
        f"(`RDTG_result.json`):** (i) **the masking mechanisms cap every claim above, "
        f"consequences pre-committed:** M1 external managers/custodians — the destination "
        f"compilers' own \"custodial bias\" (TIC SHL2024r, verbatim in "
        f"`RDTG_legs_manifest.json`; IMF reserve-management guidelines ground the practice) — "
        f"consequence: a null on any leg and on the sweep is WEAK evidence, not disposal; M2 "
        f"counterpart-attribution — center-routed transactions attribute to the center — "
        f"consequence: a surge is CONSISTENCY, not attribution, and the absence of a China "
        f"line is not the absence of China; (ii) **power limits ride the verdict sentence:** "
        f"only {sw['n_powered']} of nine legs are powered under the Scheme-1 bars (g and i "
        f"are UNPOWERED — σ_baseline exceeds their bars; e is POWER-NOT-COMPUTABLE on a "
        f"single baseline change; b is NOT-TESTABLE, its position series ends 2022Q3 and the "
        f"flows-liabilities cell is structurally absent; d and h are NOT-AVAILABLE), and "
        f"under the Scheme-2 bars the sweep is UNPOWERED outright — DESTINATION-ABSENT is a "
        f"Scheme-1 verdict over three powered legs; (iii) basis frictions, stated per leg and "
        f"computed on what each leg publishes (the tonnage-not-value lesson): gilt HEWD is "
        f"market value vs nominal bars; ABS IIP is market-value general government (broader "
        f"than AGS); Pink Book values are mixed-vintage; leg (a) is a cumulative-FLOWS "
        f"extension of the level-change construction (bilateral positions unpublished), "
        f"stated; leg (f)'s FOF row includes FILP bonds while the bar denominator is MoF "
        f"General Bonds; (iv) the I.B DISCLOSURE finding (persistent sub-line blanks under a "
        f"published total) is a fact about China's disclosure perimeter, never interpolated "
        f"and never converted into a SUPPRESSED verdict for the published total; (v) the "
        f"candidate market set is not the universe of non-US destinations, so the bars "
        f"OVERSTATE per-market arrivals and the null is weaker, never stronger "
        f"(pre-committed direction); (vi) no leg carries construction-grade attribution, so "
        f"the fork endpoints are annotated, never moved; the k1 wall and the pool caveat "
        f"ride everything; no date, no probability, no currency guess.\n"
        "<!-- RDTG-AMEND:END limitations-rdtg -->\n"
    )

    block_prov = (
        "<!-- RDTG-AMEND:BEGIN provenance -->\n"
        f"**RDT-G amendment provenance:** this file was further amended by RDT-G "
        f"(pre-registered in `build/reserve/RDTG_prediction.md`, committed 7ad70d2). All "
        f"RDT-G content is delimited by RDTG-AMEND marker comments and every number in it is "
        f"computed by `build/reserve/RDTG_recompute.py` from `RDTG_bars.json`, "
        f"`RDTG_ib_series.csv`/`RDTG_ib_staging.json`, `RDTG_legs_manifest.json`, the RAW "
        f"retained receiving-leg files under `rdtg_evidence/leg_*`, "
        f"`RDTG_denominators.json`, and the committed constants read from "
        f"`RDTD_result.json`/`RDTE_result.json`/`RDTF_result.json` — stripping the "
        f"RDTG-AMEND blocks reproduces the post-RDT-F object byte-for-byte (base sha256 "
        f"{post_rdtf_sha}, as recorded in `RDTF_verify.json`). `RDT_recompute.py`, "
        f"`RDTB_recompute.py`, `RDTC_recompute.py`, `RDTD_recompute.py`, "
        f"`RDTD_fragility_recompute.py`, `RDTE_ingredients_recompute.py`, "
        f"`RDTE_recompute.py`, `RDTF_ingredients_recompute.py`, `RDTF_recompute.py`, "
        f"`RDTG_bars_recompute.py` and `RDTG_ib_recompute.py` are NOT modified; the RDTB-, "
        f"RDTC-, RDTD-, RDTE- and RDTF-AMEND blocks are untouched; `RDTG_verify.json` "
        f"carries the further-amended object's byte-reproduction. No composite is recomputed "
        f"(k1 unchanged).\n"
        "<!-- RDTG-AMEND:END provenance -->\n"
    )

    return [
        ("<!-- RDTF-AMEND:END k3-route-robust-ceiling -->", block_main),
        ("<!-- RDTF-AMEND:END hazard-route-robust -->", block_hazard),
        ("<!-- RDTF-AMEND:END limitations-rdtf -->", block_lim),
        ("<!-- RDTF-AMEND:END provenance -->", block_prov),
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


def amend_object(ctx):
    post_rdtf_sha = RDTFV["outputs_sha256"]["RDT_breaking_point_object.md"]
    current = OBJECT_MD.read_text(encoding="utf-8")
    base = strip_amendment(current)
    base_sha = hashlib.sha256(base.encode("utf-8")).hexdigest()
    base_ok = base_sha == post_rdtf_sha
    guard(base_ok, f"stripped base sha {base_sha} != post-RDT-F sha {post_rdtf_sha} -- "
                   "refusing to amend a wrong base (checked BEFORE amending)")
    blocks = build_blocks(ctx, post_rdtf_sha)
    amended = amend(base, blocks)
    repro = (strip_amendment(amended) == base) and (amend(strip_amendment(amended), blocks)
                                                    == amended)
    OBJECT_MD.write_text(amended, encoding="utf-8")
    rewritten_ok = OBJECT_MD.read_text(encoding="utf-8") == amended
    return bool(repro and rewritten_ok), base_ok, base_sha, post_rdtf_sha


# ---------------------------------------------------------------------------

def main():
    payload1, ctx1 = build_payload()
    payload2, _ = build_payload()
    # the hazard block needs the verdict-window I.B delta in signed form
    ctx1["ib_delta"] = payload1["part_a_ib_verdict"]["delta_verdict_window_usd_bn"][
        "convention_2022_01_base (pre-registered wording)"]["value"]
    s1_ = json.dumps(payload1, indent=1, ensure_ascii=False, sort_keys=True)
    s2_ = json.dumps(payload2, indent=1, ensure_ascii=False, sort_keys=True)
    two_pass = s1_ == s2_
    guard(two_pass, "two independent payload builds differ -- non-deterministic build")
    OUT_RESULT.write_text(s1_ + "\n", encoding="utf-8")
    result_repro = OUT_RESULT.read_text(encoding="utf-8") == s1_ + "\n"

    obj_repro, base_ok, base_sha, post_rdtf_sha = amend_object(ctx1)

    flags = {
        "result_two_pass_payload_identical": bool(two_pass),
        "result_byte_reproduction": bool(result_repro),
        "amended_object_byte_reproduction (strip-and-reinsert fixed point)": bool(obj_repro),
        "stripped_base_matches_post_rdtf_sha256": bool(base_ok),
    }
    all_pass = all(flags.values())
    verify = {
        "purpose": ("verifier artifact for RDT-G Phase 3 ASSEMBLY: records that "
                    "RDTG_result.json and the amended RDT_breaking_point_object.md were "
                    "regenerated deterministically from the committed inputs by "
                    "build/reserve/RDTG_recompute.py, and that stripping the RDTG-AMEND "
                    "blocks reproduces the post-RDT-F object byte-for-byte against the sha "
                    "recorded in RDTF_verify.json (checked BEFORE amending). Until "
                    "all_pass=true AND the human gate reviews this stage, every number and "
                    "every verdict in these outputs is an OUTPUT, not established."),
        "no_date_no_probability_no_currency_guess": (
            "no date, no probability, and no destination-currency guess anywhere in the "
            "RDT-G outputs"),
        "network": "none (disk-only assembly)",
        "inputs_sha256": INPUTS_SHA,
        "outputs_sha256": {
            "RDTG_result.json": sha256_file(OUT_RESULT),
            "RDT_breaking_point_object.md": sha256_file(OBJECT_MD),
        },
        "match_flags": flags,
        "post_rdtf_object_sha256": {
            "stripped_base_recomputed_here": base_sha,
            "recorded_in_RDTF_verify_json": post_rdtf_sha,
            "note": ("RDTF_verify.json's object sha256 is the RDT-G amendment base; the "
                     "further-amended object's byte-reproduction is carried here"),
        },
        "all_pass": bool(all_pass),
    }
    OUT_VERIFY.write_text(json.dumps(verify, indent=1, ensure_ascii=False, sort_keys=True)
                          + "\n", encoding="utf-8")
    print(json.dumps({"all_pass": all_pass, **flags}, indent=1))
    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
