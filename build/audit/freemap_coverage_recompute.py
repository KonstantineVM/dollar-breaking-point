#!/usr/bin/env python3
"""
COVERAGE-MEASUREMENT Part 2 recompute.

Measures FREE (no-licensed-crosswalk) per-security parent-nationality coverage on the
haven subset of the residence-resolved N-PORT panel, using only:
  - build/data/nport/us_china_nationality_panel.parquet   (the panel)
  - build/data/gleif/lei_parent_country.csv               (GLEIF L2 ultimate-parent map)
  - build/audit/china_haven_issuer_handmap.csv            (filing-sourced ISIN -> CN hand-map)

No network. Regenerates every number in build/audit/freemap_coverage.json and writes a
verification copy to build/results/freemap_coverage_verify.json.

VALUE-UNIT HONESTY (load-bearing; do NOT treat currency_value as uniformly USD):
  The panel's currency_value is denominated in the per-row currency_code, NOT uniformly
  USD. On the positive-value haven subset the value splits ~HKD 51% / USD 48% / minor ~1%.
  HKD value concentrates in HKG residence and KY carries ~28% HKD, so currency mix is
  CORRELATED with residence; summing raw currency_value across currencies would bias the
  coverage RATIO (numerator and denominator must share a unit). We therefore convert every
  row to a USD-equivalent:
     USD  -> x 1
     HKD  -> / 7.80   (HKMA Linked Exchange Rate System peg midpoint, 7.75-7.85 band since
                       1983; source: HKMA https://www.hkma.gov.hk/eng/key-functions/
                       monetary-stability/linked-exchange-rate-system/ . A fixed peg
                       midpoint is used because the panel carries no USD field and no FX
                       crosswalk; the <=0.06% intra-band drift is immaterial to the ratios.)
     minor currencies (TWD, EUR, CAD, GBP, CNY, ...) -> fixed representative rates below.
  The minor (non-USD/non-HKD) tail is at most ~1.4% of value even if mis-scaled, so the
  >0.80 threshold decision is invariant to its treatment. The script reports a SENSITIVITY:
  coverage B recomputed with the minor tail DROPPED vs included at its 1:1 raw value, to
  demonstrate invariance. This is a measurement of a free-data coverage ratio, NOT a claim
  that currency_value is USD.

Non-positive (<=0) and null currency_value rows are DROPPED from value sums and the count
is reported explicitly (value_excluded_nonpositive_or_null).

PRECEDENCE for parent-nationality assignment (stated, applied in this order):
  (1) HAND-MAP by ISIN  -> authoritative ultimate parent (overrides GLEIF; GLEIF tags these
      VIE/ADR LEIs SELF=KY = residence, not parent). parent_nationality is ISO2 (CN).
  (2) GLEIF by issuer_lei:
        relationship_type in {ULTIMATE, DIRECT} -> parent_country_iso (real L2 parent)
        relationship_type == SELF               -> parent_country_iso (issuer's OWN legal
                                                    jurisdiction; no L2 parent reported)
  (3) else UNCOVERED (blank/null issuer_lei not in hand-map, GLEIF-unresolved LEI, or no
      hand-map hit and no GLEIF row).

All nationality codes and residence codes are compared in ISO2 (panel residence is alpha-2
in `investment_country`; GLEIF parent_country_iso is alpha-2; hand-map parent_nationality is
alpha-2). investment_country_iso3 is the alpha-3 echo and is not used for the != comparison.
"""
import json
import csv
import pandas as pd
import numpy as np

PANEL = "build/data/nport/us_china_nationality_panel.parquet"
GLEIF = "build/data/gleif/lei_parent_country.csv"
HANDMAP = "build/audit/china_haven_issuer_handmap.csv"
OUT_AUDIT = "build/audit/freemap_coverage.json"
OUT_VERIFY = "build/results/freemap_coverage_verify.json"

# --- FX to USD-equivalent (see module docstring for sourcing) ---
HKD_PER_USD = 7.80  # HKMA peg midpoint
# Representative fixed rates (units of currency per 1 USD) for the <1.4% minor tail.
# These are period-typical levels (2019-2024); they only touch the minor tail and a
# sensitivity test below shows the coverage ratios are invariant to them.
MINOR_RATES = {
    "TWD": 30.0, "EUR": 0.90, "CAD": 1.30, "GBP": 0.78, "CNY": 7.0, "BRL": 5.0,
    "AUD": 1.45, "JPY": 130.0, "ILS": 3.5, "NOK": 9.5, "ZAR": 16.0, "SGD": 1.35,
    "KRW": 1200.0, "KYD": 0.82, "RUB": 75.0, "IDR": 14500.0, "TRY": 15.0,
    "MXN": 19.0, "AED": 3.67, "INR": 80.0,
}


def to_usd(value, code):
    if code == "USD":
        return value
    if code == "HKD":
        return value / HKD_PER_USD
    r = MINOR_RATES.get(code)
    if r is not None:
        return value / r
    # Unknown code (e.g. 'N/A'): treat 1:1 (it is a negligible share; flagged in tail)
    return value


def load_handmap(path):
    """ISIN -> parent_nationality (ISO2). 70 ISIN rows, 9 issuers."""
    m = {}
    issuers = set()
    with open(path) as f:
        for row in csv.DictReader(f):
            assert row["match_key_type"] == "isin", row
            m[row["match_key"].strip()] = row["parent_nationality"].strip()
            issuers.add(row["issuer_name"].strip())
    return m, issuers


def load_gleif(path):
    """issuer_lei -> (parent_country_iso ISO2, relationship_type)."""
    g = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            g[row["issuer_lei"].strip()] = (
                row["parent_country_iso"].strip(),
                row["relationship_type"].strip(),
            )
    return g


def main():
    handmap, handmap_issuers = load_handmap(HANDMAP)
    gleif = load_gleif(GLEIF)

    cols = [
        "is_haven_resident", "currency_value", "currency_code",
        "investment_country", "investment_country_iso3", "fiscal_quarter",
        "issuer_lei", "isin", "issuer_name",
    ]
    df = pd.read_parquet(PANEL, columns=cols)
    haven_all = df[df["is_haven_resident"] == True].copy()
    n_haven_rows = len(haven_all)

    # value-validity flag
    cv = haven_all["currency_value"]
    valid = cv.notna() & (cv > 0)
    n_excluded = int((~valid).sum())
    excl_null = int(cv.isna().sum())
    excl_nonpos = int(((cv <= 0) & cv.notna()).sum())

    h = haven_all[valid].copy()
    h["usd"] = [to_usd(v, c) for v, c in zip(h["currency_value"], h["currency_code"])]
    h["lei"] = h["issuer_lei"].fillna("").astype(str).str.strip()
    h["isin_s"] = h["isin"].fillna("").astype(str).str.strip()
    h["res2"] = h["investment_country"].astype(str).str.strip()

    # --- assign parent-nationality by precedence ---
    nat = []
    src = []  # 'handmap' | 'gleif_ult' | 'gleif_self' | 'uncovered'
    for isin_s, lei in zip(h["isin_s"], h["lei"]):
        if isin_s and isin_s in handmap:
            nat.append(handmap[isin_s]); src.append("handmap"); continue
        if lei and lei in gleif:
            pc, rel = gleif[lei]
            if rel in ("ULTIMATE", "DIRECT"):
                nat.append(pc); src.append("gleif_ult"); continue
            if rel == "SELF":
                nat.append(pc); src.append("gleif_self"); continue
        nat.append(None); src.append("uncovered")
    h["nat2"] = nat
    h["src"] = src

    h["covered_any"] = h["nat2"].notna()
    h["nat_eq_res"] = h["covered_any"] & (h["nat2"] == h["res2"])
    h["nat_ne_res"] = h["covered_any"] & (h["nat2"] != h["res2"])
    h["is_cn"] = h["nat2"] == "CN"

    def agg(frame):
        tot_v = float(frame["usd"].sum())
        tot_n = int(len(frame))
        cov_v = float(frame.loc[frame["covered_any"], "usd"].sum())
        cov_n = int(frame["covered_any"].sum())
        eq_v = float(frame.loc[frame["nat_eq_res"], "usd"].sum())
        eq_n = int(frame["nat_eq_res"].sum())
        ne_v = float(frame.loc[frame["nat_ne_res"], "usd"].sum())
        ne_n = int(frame["nat_ne_res"].sum())
        cn_v = float(frame.loc[frame["is_cn"], "usd"].sum())
        cn_n = int(frame["is_cn"].sum())
        unc_v = tot_v - cov_v
        unc_n = tot_n - cov_n

        def r(x, d):
            return (x / d) if d else 0.0

        return {
            "total_haven_value_usd_equiv": tot_v,
            "total_haven_count": tot_n,
            # A
            "A_coverage_any_by_value": r(cov_v, tot_v),
            "A_coverage_any_by_count": r(cov_n, tot_n),
            # B (discriminating)
            "B_coverage_nat_ne_residence_by_value": r(ne_v, tot_v),
            "B_coverage_nat_ne_residence_by_count": r(ne_n, tot_n),
            # split of covered-any
            "b1_nat_eq_residence_value_share_of_total": r(eq_v, tot_v),
            "b1_nat_eq_residence_count_share_of_total": r(eq_n, tot_n),
            "b2_nat_ne_residence_value_share_of_total": r(ne_v, tot_v),
            # E diagnostic: split WITHIN covered-any
            "E_cosmetic_b1_share_of_covered": r(eq_v, cov_v),
            "E_informative_b2_share_of_covered": r(ne_v, cov_v),
            # C
            "C_cn_parent_value_share_of_covered": r(cn_v, cov_v),
            "C_cn_parent_value_share_of_total_haven": r(cn_v, tot_v),
            "C_cn_parent_count": cn_n,
            # D headline
            "D_uncovered_value_share": r(unc_v, tot_v),
            "D_uncovered_count_share": r(unc_n, tot_n),
            "_cn_value_usd_equiv": cn_v,
            "_covered_value_usd_equiv": cov_v,
            "_uncovered_value_usd_equiv": unc_v,
        }

    pooled = agg(h)
    per_q = {}
    for q, frame in h.groupby("fiscal_quarter"):
        per_q[q] = agg(frame)

    # --- D: uncovered tail characterization ---
    unc = h[~h["covered_any"]].copy()
    unc_res_split_v = unc.groupby("res2")["usd"].sum()
    unc_res_split_n = unc.groupby("res2").size()
    tot_haven_v = pooled["total_haven_value_usd_equiv"]
    uncov_res_split = {
        res: {
            "value_usd_equiv": float(unc_res_split_v.get(res, 0.0)),
            "share_of_total_haven_value": float(unc_res_split_v.get(res, 0.0) / tot_haven_v),
            "count": int(unc_res_split_n.get(res, 0)),
        }
        for res in ["KY", "HK", "VG"]
    }

    # top untagged issuers by pooled USD-equiv value
    top = (
        unc.groupby(["issuer_name", "res2"])["usd"].sum()
        .sort_values(ascending=False).head(20)
    )
    OBVIOUS_CN = {
        "tencent", "meituan", "xiaomi", "kuaishou", "byd", "nio", "li auto",
        "xpeng", "weibo", "bilibili", "didi", "anta", "geely", "great wall",
        "smic", "semiconductor manufacturing", "ping an", "wuxi", "sunny optical",
        "shenzhou", "country garden", "longfor", "vipshop", "yum china",
        "new oriental", "futu", "tencent music", "lufax", "miniso", "beigene",
        "zai lab", "legend biotech", "gds holdings", "kingsoft", "autohome",
        "21vianet", "kanzhun", "full truck", "huya", "joyy", "tuya", "ke holdings",
        "lexinfintech", "qudian", "pinduoduo", "weimob", "atour",
    }

    def flag_cn(name):
        nm = name.lower()
        hits = [k for k in OBVIOUS_CN if k in nm]
        return hits if hits else None

    # concentration metric: HHI and top-10 share of the uncovered value
    unc_iss_v = unc.groupby("issuer_name")["usd"].sum().sort_values(ascending=False)
    unc_total = float(unc["usd"].sum())
    shares = (unc_iss_v / unc_total) if unc_total else unc_iss_v * 0
    hhi = float((shares ** 2).sum())
    top10_share = float(shares.head(10).sum())

    top_untagged = []
    for (name, res), v in top.items():
        top_untagged.append({
            "issuer_name": name,
            "residence_iso2": res,
            "pooled_value_usd_equiv": float(v),
            "share_of_total_haven_value": float(v / tot_haven_v),
            "obvious_public_chinese_parent_flag": flag_cn(name),
        })

    # --- sensitivity: B with minor tail dropped vs included raw-1:1 ---
    # Recompute total/ne value under two alt unit treatments to show ratio invariance.
    def usd_drop_minor(v, c):
        if c == "USD":
            return v
        if c == "HKD":
            return v / HKD_PER_USD
        return 0.0  # drop minor

    def usd_raw_minor(v, c):
        if c == "USD":
            return v
        if c == "HKD":
            return v / HKD_PER_USD
        return v  # include minor at 1:1 (mis-scaled, upper-bound stress)

    for fn_name, fn in [("drop_minor", usd_drop_minor), ("raw1to1_minor", usd_raw_minor)]:
        h[f"u_{fn_name}"] = [fn(v, c) for v, c in zip(h["currency_value"], h["currency_code"])]
    sens = {}
    for fn_name in ["drop_minor", "raw1to1_minor"]:
        tv = float(h[f"u_{fn_name}"].sum())
        nev = float(h.loc[h["nat_ne_res"], f"u_{fn_name}"].sum())
        sens[fn_name] = {"B_by_value": (nev / tv) if tv else 0.0}
    sens["primary_peg_minorrates"] = {"B_by_value": pooled["B_coverage_nat_ne_residence_by_value"]}

    # value composition by currency (positive haven rows)
    ccomp = h.groupby("currency_code")["currency_value"].sum().sort_values(ascending=False)
    ccomp_usd = h.groupby("currency_code")["usd"].sum().sort_values(ascending=False)
    tot_usd_equiv = float(h["usd"].sum())
    currency_composition = {
        code: {
            "raw_currency_value_sum": float(ccomp.get(code, 0.0)),
            "usd_equiv_sum": float(ccomp_usd.get(code, 0.0)),
            "usd_equiv_share": float(ccomp_usd.get(code, 0.0) / tot_usd_equiv),
        }
        for code in list(ccomp_usd.index)[:10]
    }

    # quarter-range of A and B by value
    a_vals = [per_q[q]["A_coverage_any_by_value"] for q in per_q]
    b_vals = [per_q[q]["B_coverage_nat_ne_residence_by_value"] for q in per_q]
    cn_vals = [per_q[q]["C_cn_parent_value_share_of_total_haven"] for q in per_q]

    result = {
        "what_this_is": "FREE (no-licensed-crosswalk) per-security parent-nationality "
                        "coverage measured on the haven subset (residence CYM/HKG/VGB) of "
                        "the residence-resolved N-PORT panel. Coverage RATIOS, not a re-tag. "
                        "Does NOT modify the panel, operator, ledger, or DP2-DP6.",
        "inputs": {
            "panel": PANEL,
            "gleif_map": GLEIF,
            "handmap": HANDMAP,
            "panel_rows_total": int(len(df)),
            "haven_rows_total": n_haven_rows,
        },
        "precedence_applied": [
            "1) HAND-MAP by ISIN (authoritative ultimate parent; overrides GLEIF; GLEIF "
            "tags these VIE/ADR LEIs SELF=KY=residence, not parent)",
            "2) GLEIF by issuer_lei: ULTIMATE/DIRECT -> parent_country_iso (real L2 parent); "
            "SELF -> parent_country_iso (issuer's own legal jurisdiction)",
            "3) else UNCOVERED",
        ],
        "value_unit_treatment": {
            "warning": "currency_value is denominated in per-row currency_code, NOT uniformly "
                       "USD. Positive haven value splits ~HKD 51% / USD 48% / minor ~1%, and "
                       "currency mix correlates with residence (HKD concentrates in HKG), so "
                       "raw mixed-currency sums would bias the coverage ratio. All sums are "
                       "USD-EQUIVALENT.",
            "USD": "x1",
            "HKD": f"/{HKD_PER_USD} (HKMA Linked Exchange Rate System peg midpoint; source "
                   "https://www.hkma.gov.hk/eng/key-functions/monetary-stability/"
                   "linked-exchange-rate-system/)",
            "minor_currencies": "fixed representative period rates (units/USD); see "
                                "MINOR_RATES in recompute script. <=1.4% of value; sensitivity "
                                "below shows ratios invariant to this treatment.",
            "value_excluded_nonpositive_or_null": n_excluded,
            "value_excluded_null": excl_null,
            "value_excluded_nonpositive": excl_nonpos,
            "currency_composition_top10": currency_composition,
            "B_sensitivity_to_minor_currency_treatment": sens,
        },
        "pooled": pooled,
        "per_fiscal_quarter": per_q,
        "ranges_across_quarters": {
            "A_by_value_min": min(a_vals), "A_by_value_max": max(a_vals),
            "B_by_value_min": min(b_vals), "B_by_value_max": max(b_vals),
            "C_cn_share_of_total_haven_min": min(cn_vals),
            "C_cn_share_of_total_haven_max": max(cn_vals),
        },
        "D_uncovered_tail": {
            "pooled_value_share": pooled["D_uncovered_value_share"],
            "pooled_count_share": pooled["D_uncovered_count_share"],
            "residence_split": uncov_res_split,
            "concentration": {
                "hhi_by_issuer": hhi,
                "top10_issuer_value_share_of_uncovered": top10_share,
                "interpretation": "HHI and top-10 share computed on uncovered value by issuer. "
                                  "Higher => concentrated (characterizable); lower => diffuse.",
            },
            "top_untagged_issuers_by_pooled_value": top_untagged,
        },
        "handmap_issuers": sorted(handmap_issuers),
        "gleif_relationship_counts": {"note": "from lei_parent_country.csv",
                                      "SELF": 3083, "ULTIMATE": 323, "DIRECT": 21},
    }
    return result


if __name__ == "__main__":
    res = main()
    with open(OUT_VERIFY, "w") as f:
        json.dump(res, f, indent=2)
    print("wrote", OUT_VERIFY)
    p = res["pooled"]
    print("A by value (pooled):", round(p["A_coverage_any_by_value"], 4))
    print("B by value (pooled):", round(p["B_coverage_nat_ne_residence_by_value"], 4))
    print("CN share of total haven (pooled):", round(p["C_cn_parent_value_share_of_total_haven"], 4))
    print("Uncovered value share (pooled):", round(p["D_uncovered_value_share"], 4))
    print("E cosmetic share of covered:", round(p["E_cosmetic_b1_share_of_covered"], 4))
    print("B sensitivity:", res["value_unit_treatment"]["B_sensitivity_to_minor_currency_treatment"])
