#!/usr/bin/env python3
"""
CONSTRUCT-THE-CROSSWALK Parts 3 & 4 — coverage recompute generator (no network).

Re-measures coverage on the crosswalk-tagged haven panel using the SAME statistic and
the SAME value treatment as the prior freemap pass (build/audit/freemap_coverage.json,
prior A=0.686 / B=0.287), so the new B is directly comparable to the prior 0.287.

Inputs (on disk only; no fetches):
  - build/data/nport/panel_crosswalk_tagged.parquet      (the 663,325-row tagged haven panel)
  - build/data/nport/us_china_nationality_panel.parquet  (the source panel; haven subset is
        the SAME 663,325 rows in the SAME order -- verified -- and carries currency_code +
        fiscal_quarter, which the tagged parquet dropped)
  - build/data/gleif/lei_parent_country.csv              (prior GLEIF L2 parent map; SELF=own
        jurisdiction) -- used to build the apples-to-apples UNION nationality.

------------------------------------------------------------------------------------------
VALUE-UNIT HONESTY (load-bearing). Two facts established by inspection, both reported:

  (a) The tagged parquet's `currency_value` column is byte-for-byte the source panel's RAW
      per-row `currency_value`, denominated in the per-row `currency_code` (NOT USD). The
      construction's verify file reports HAVEN_VALUE = 3.4225e12 and CN-share = 0.2090 on
      that RAW mixed-currency denominator. The prior freemap B=0.287 used the USD-EQUIVALENT
      denominator (1.8772e12). RAW and USD-equiv are NOT the same scale (HKD value is ~half
      the haven total and is divided by 7.8 to reach USD), so 0.2090-on-raw is NOT directly
      comparable to 0.287-on-USD-equiv.

  (b) To make the comparison apples-to-apples we apply the IDENTICAL conversion the prior
      pass used: USD x1; HKD /7.80 (HKMA Linked Exchange Rate System peg midpoint, source
      https://www.hkma.gov.hk/eng/key-functions/monetary-stability/linked-exchange-rate-system/);
      the <=1.4% minor tail at the same fixed representative rates. We attach currency_code
      (and fiscal_quarter) from the aligned source haven subset by position.

  We report the CN-share BOTH ways: on the RAW denominator (to reproduce the construction's
  0.2090) AND on the USD-equivalent denominator (to compare to 0.287). The headline B_constr
  / B_union are USD-equivalent, matching the prior statistic.

POSITIVE-VALUE FILTER: the prior pass dropped 8,031 nonpositive/null currency_value rows
(655,294 positive haven rows remain). We drop the SAME rows so denominators match.

ROW ALIGNMENT (verified in this script, asserted): the tagged parquet's haven rows are the
source panel's haven subset in identical order. We assert issuer_name + cusip equality on
all rows before attaching currency_code / fiscal_quarter by position; a mismatch aborts.

ISO CODES: prior comparison is ISO2 (investment_country, GLEIF parent_country_iso, handmap
parent_nationality are ISO2). The tagged panel residence is ISO3 (CYM/HKG/VGB). For the
constructed parent_nationality the only non-residence value is "CN"; we compare it against
residence mapped to ISO2 (CYM->KY, HKG->HK, VGB->VG). For the UNION we compare the best
nationality (ISO2) against residence (ISO2).
------------------------------------------------------------------------------------------

TWO measures, each per fiscal_quarter AND pooled, all by VALUE:

  (i) CONSTRUCTION-ONLY:
      A_constr = (value with any constructed parent_nationality, i.e. CN-tagged) / haven
      B_constr = (value where constructed parent_nationality != residence) / haven
      All CN tags sit on KY/HK/VG residents, so B_constr == the CN-tagged share; confirmed.

  (ii) UNION (apples-to-apples with prior 0.287):
      best nationality = constructed crosswalk CN where a rule fired,
                         ELSE prior GLEIF nationality (lei_parent_country.csv;
                              ULTIMATE/DIRECT -> parent_country_iso; SELF -> own jurisdiction),
                         ELSE uncovered.
      A_union = (value with any best nationality) / haven
      B_union = (value where best nationality != residence) / haven   <- the fair "best free
                                                                          coverage" number.
      NOTE: the prior pass ALSO used a hand-map (china_haven_issuer_handmap.csv, 9 issuers)
      ahead of GLEIF. The construction's R1-R4 supersede that hand-map (the same Alibaba/JD/
      Baidu/etc. names are HFCAA/XBRL/F-6 tagged here), so the UNION below uses
      crosswalk-CN -> GLEIF, WITHOUT the prior hand-map, to measure the construction's own
      best-free coverage. We ALSO report B_union_with_handmap (crosswalk-CN -> handmap ->
      GLEIF) so the reader can see the hand-map contributes nothing the crosswalk did not
      already capture among CN names.

Uncovered tail (under the UNION, no-handmap): value share, residence split, issuer HHI,
top-10 share, top-20 untagged issuers by pooled USD-equiv value, with obvious-CN name flags.
"""
import json, csv, os
import pandas as pd
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TAGGED = os.path.join(ROOT, "build/data/nport/panel_crosswalk_tagged.parquet")
SRC    = os.path.join(ROOT, "build/data/nport/us_china_nationality_panel.parquet")
GLEIF  = os.path.join(ROOT, "build/data/gleif/lei_parent_country.csv")
HANDMAP= os.path.join(ROOT, "build/audit/china_haven_issuer_handmap.csv")
OUT_AUDIT  = os.path.join(ROOT, "build/audit/crosswalk_coverage.json")
OUT_VERIFY = os.path.join(ROOT, "build/results/crosswalk_coverage_verify.json")

PRIOR_A = 0.6858636844496402
PRIOR_B = 0.2870821902171556

HKD_PER_USD = 7.80
MINOR_RATES = {
    "TWD": 30.0, "EUR": 0.90, "CAD": 1.30, "GBP": 0.78, "CNY": 7.0, "BRL": 5.0,
    "AUD": 1.45, "JPY": 130.0, "ILS": 3.5, "NOK": 9.5, "ZAR": 16.0, "SGD": 1.35,
    "KRW": 1200.0, "KYD": 0.82, "RUB": 75.0, "IDR": 14500.0, "TRY": 15.0,
    "MXN": 19.0, "AED": 3.67, "INR": 80.0,
}
ISO3_TO_2 = {"CYM": "KY", "HKG": "HK", "VGB": "VG"}

OBVIOUS_CN = {
    "tencent", "meituan", "xiaomi", "kuaishou", "byd", "nio", "li auto",
    "xpeng", "weibo", "bilibili", "didi", "anta", "geely", "great wall",
    "smic", "semiconductor manufacturing", "ping an", "wuxi", "sunny optical",
    "shenzhou", "country garden", "longfor", "vipshop", "yum china",
    "new oriental", "futu", "tencent music", "lufax", "miniso", "beigene",
    "zai lab", "legend biotech", "gds holdings", "kingsoft", "autohome",
    "21vianet", "kanzhun", "full truck", "huya", "joyy", "tuya", "ke holdings",
    "lexinfintech", "qudian", "pinduoduo", "weimob", "atour", "alibaba", "baidu",
    "jd.com", "netease", "trip.com", "zto", "huazhu", "tal education", "h world",
    "pdd", "li ning", "haier", "crrc", "air china", "nongfu", "wuxi", "hansoh",
    "innovent", "sino", "china ", "chinese",
}


def to_usd(value, code):
    if value is None:
        return None
    if code == "USD":
        return value
    if code == "HKD":
        return value / HKD_PER_USD
    r = MINOR_RATES.get(code)
    if r is not None:
        return value / r
    return value  # unknown code: 1:1 (negligible tail)


def flag_cn(name):
    nm = (name or "").lower()
    hits = sorted({k.strip() for k in OBVIOUS_CN if k in nm})
    return hits if hits else None


def load_gleif(path):
    g = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            g[row["issuer_lei"].strip()] = (
                row["parent_country_iso"].strip(),
                row["relationship_type"].strip(),
            )
    return g


def load_handmap(path):
    m = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            m[row["match_key"].strip()] = row["parent_nationality"].strip()
    return m


def main():
    tag = pd.read_parquet(TAGGED)
    src = pd.read_parquet(SRC, columns=[
        "is_haven_resident", "currency_value", "currency_code", "fiscal_quarter",
        "investment_country", "issuer_name", "cusip", "isin", "issuer_lei",
    ])
    hav = src[src["is_haven_resident"] == True].reset_index(drop=True)

    # --- assert exact row alignment before attaching by position ---
    assert len(hav) == len(tag) == 663325, (len(hav), len(tag))
    assert (hav["issuer_name"].fillna("").values == tag["issuer_name"].fillna("").values).all(), \
        "issuer_name misaligned"
    assert (hav["cusip"].fillna("").values == tag["cusip"].fillna("").values).all(), \
        "cusip misaligned"
    assert np.allclose(np.nan_to_num(hav["currency_value"].values),
                       np.nan_to_num(tag["currency_value"].values), rtol=1e-9), \
        "currency_value misaligned (tagged cv is NOT the source raw cv)"

    h = tag.copy()
    h["currency_code"] = hav["currency_code"].values
    h["fiscal_quarter"] = hav["fiscal_quarter"].values
    h["res2"] = pd.Series(tag["residence_iso3"].values).map(ISO3_TO_2).values
    h["lei"] = h["issuer_lei"].fillna("").astype(str).str.strip()
    h["isin_s"] = h["isin"].fillna("").astype(str).str.strip()

    # positive-value filter (same as prior)
    cv = h["currency_value"]
    valid = cv.notna() & (cv > 0)
    n_excluded = int((~valid).sum())
    h = h[valid].copy()

    # USD-equivalent and RAW value columns
    h["usd"] = [to_usd(v, c) for v, c in zip(h["currency_value"], h["currency_code"])]
    h["raw"] = h["currency_value"].astype(float)

    # ---------------- constructed nationality ----------------
    h["constr_cn"] = (h["parent_nationality"] == "CN")
    # constructed best nationality (ISO2): CN where rule fired, else None
    h["constr_nat2"] = np.where(h["constr_cn"], "CN", None)
    h["constr_cov"] = h["constr_nat2"].notna()
    h["constr_ne"] = h["constr_cov"] & (h["constr_nat2"] != h["res2"])  # CN != KY/HK/VG always

    # ---------------- UNION nationality (crosswalk-CN -> GLEIF) ----------------
    gleif = load_gleif(GLEIF)
    handmap = load_handmap(HANDMAP)

    union_nat = []
    union_src = []
    union_nat_hm = []  # variant: crosswalk-CN -> handmap -> GLEIF
    for cn, lei, isin_s in zip(h["constr_cn"], h["lei"], h["isin_s"]):
        if cn:
            union_nat.append("CN"); union_src.append("crosswalk_cn")
            union_nat_hm.append("CN")
            continue
        # GLEIF
        g = gleif.get(lei) if lei else None
        if g is not None:
            pc, rel = g
            if rel in ("ULTIMATE", "DIRECT", "SELF"):
                union_nat.append(pc); union_src.append("gleif_" + rel.lower())
            else:
                union_nat.append(None); union_src.append("uncovered")
        else:
            union_nat.append(None); union_src.append("uncovered")
        # handmap variant
        if isin_s and isin_s in handmap:
            union_nat_hm.append(handmap[isin_s])
        elif g is not None and g[1] in ("ULTIMATE", "DIRECT", "SELF"):
            union_nat_hm.append(g[0])
        else:
            union_nat_hm.append(None)

    h["union_nat2"] = union_nat
    h["union_src"] = union_src
    h["union_nat2_hm"] = union_nat_hm
    h["union_cov"] = h["union_nat2"].notna()
    h["union_ne"] = h["union_cov"] & (h["union_nat2"] != h["res2"])
    h["union_cn"] = h["union_nat2"] == "CN"
    h["union_cov_hm"] = pd.Series(union_nat_hm).notna().values
    h["union_ne_hm"] = h["union_cov_hm"] & (pd.Series(union_nat_hm).values != h["res2"].values)

    def agg(frame):
        tot_v = float(frame["usd"].sum())
        tot_raw = float(frame["raw"].sum())
        tot_n = int(len(frame))

        def vshare(mask):
            return float(frame.loc[mask, "usd"].sum()) / tot_v if tot_v else 0.0
        def vshare_raw(mask):
            return float(frame.loc[mask, "raw"].sum()) / tot_raw if tot_raw else 0.0

        return {
            "total_haven_value_usd_equiv": tot_v,
            "total_haven_value_raw_mixed_ccy": tot_raw,
            "total_haven_count": tot_n,
            # construction-only
            "A_constr_by_value": vshare(frame["constr_cov"]),
            "B_constr_by_value": vshare(frame["constr_ne"]),
            "A_constr_by_count": float(frame["constr_cov"].sum()) / tot_n if tot_n else 0.0,
            "B_constr_by_count": float(frame["constr_ne"].sum()) / tot_n if tot_n else 0.0,
            # union
            "A_union_by_value": vshare(frame["union_cov"]),
            "B_union_by_value": vshare(frame["union_ne"]),
            "A_union_by_count": float(frame["union_cov"].sum()) / tot_n if tot_n else 0.0,
            "B_union_by_count": float(frame["union_ne"].sum()) / tot_n if tot_n else 0.0,
            # union with prior handmap (should be ~identical for CN)
            "A_union_with_handmap_by_value": vshare(frame["union_cov_hm"]),
            "B_union_with_handmap_by_value": vshare(frame["union_ne_hm"]),
            # CN-parent share of TOTAL haven value
            "C_cn_share_of_total_haven_usd_equiv": vshare(frame["constr_cn"]),
            "C_cn_share_of_total_haven_RAW_mixed_ccy": vshare_raw(frame["constr_cn"]),
            "C_cn_count": int(frame["constr_cn"].sum()),
            # uncovered (union)
            "D_union_uncovered_value_share": vshare(~frame["union_cov"]),
            "D_union_uncovered_count_share": float((~frame["union_cov"]).sum()) / tot_n if tot_n else 0.0,
            "_cn_value_usd_equiv": float(frame.loc[frame["constr_cn"], "usd"].sum()),
            "_cn_value_raw": float(frame.loc[frame["constr_cn"], "raw"].sum()),
        }

    pooled = agg(h)
    per_q = {q: agg(frame) for q, frame in h.groupby("fiscal_quarter")}

    # ---------------- uncovered tail (UNION, no handmap) ----------------
    unc = h[~h["union_cov"]].copy()
    tot_haven_v = pooled["total_haven_value_usd_equiv"]
    unc_res_v = unc.groupby("res2")["usd"].sum()
    unc_res_n = unc.groupby("res2").size()
    uncov_res_split = {
        res: {
            "value_usd_equiv": float(unc_res_v.get(res, 0.0)),
            "share_of_total_haven_value": float(unc_res_v.get(res, 0.0) / tot_haven_v),
            "count": int(unc_res_n.get(res, 0)),
        }
        for res in ["KY", "HK", "VG"]
    }
    unc_iss_v = unc.groupby("issuer_name")["usd"].sum().sort_values(ascending=False)
    unc_total = float(unc["usd"].sum())
    shares = (unc_iss_v / unc_total) if unc_total else unc_iss_v * 0
    hhi = float((shares ** 2).sum())
    top10_share = float(shares.head(10).sum())
    top = unc.groupby(["issuer_name", "res2"])["usd"].sum().sort_values(ascending=False).head(20)
    top_untagged = [{
        "issuer_name": name,
        "residence_iso2": res,
        "pooled_value_usd_equiv": float(v),
        "share_of_total_haven_value": float(v / tot_haven_v),
        "obvious_chinese_name_flag": flag_cn(name),
    } for (name, res), v in top.items()]
    flagged_cn_in_tail = [t for t in top_untagged if t["obvious_chinese_name_flag"]]

    # quarter ranges
    def rng(key):
        vals = [per_q[q][key] for q in per_q]
        return {"min": min(vals), "max": max(vals)}

    result = {
        "what_this_is": (
            "CONSTRUCT-THE-CROSSWALK Parts 3-4 coverage. Re-measures parent-nationality "
            "coverage on the crosswalk-tagged haven panel using the SAME statistic and SAME "
            "USD-equivalent value treatment as the prior freemap pass, so B is directly "
            "comparable to the prior 0.287. Coverage RATIOS only -- does NOT re-tag the "
            "operator, re-run separability, or touch DP2-DP6/ledger."
        ),
        "inputs": {
            "tagged_panel": TAGGED,
            "source_panel_for_ccy_and_quarter": SRC,
            "gleif_map": GLEIF,
            "handmap_for_variant_only": HANDMAP,
            "tagged_haven_rows_total": int(len(tag)),
            "positive_value_haven_rows": int(len(h)),
            "rows_excluded_nonpositive_or_null": n_excluded,
        },
        "value_unit_treatment": {
            "headline_basis": "USD-EQUIVALENT (matches prior freemap pass; B comparable to 0.287)",
            "raw_vs_usd_note": (
                "The tagged parquet currency_value is the source panel RAW per-row value in "
                "native currency_code (verified byte-identical), NOT USD. The construction "
                "verify file's CN-share 0.2090 and HAVEN_VALUE 3.4225e12 are on that RAW "
                "mixed-currency denominator. Prior B=0.287 is on the USD-equivalent "
                "denominator (1.8772e12). They are different scales; headline numbers here "
                "are USD-equivalent. CN-share is reported BOTH ways (see C_cn_share_*)."),
            "USD": "x1",
            "HKD": f"/{HKD_PER_USD} (HKMA Linked Exchange Rate System peg midpoint; "
                   "https://www.hkma.gov.hk/eng/key-functions/monetary-stability/linked-exchange-rate-system/)",
            "minor_currencies": "fixed representative period rates (units/USD); <=1.4% of value",
        },
        "prior_comparison_anchors": {"prior_A_by_value": PRIOR_A, "prior_B_by_value": PRIOR_B,
                                     "source": "build/audit/freemap_coverage.json"},
        "pooled": pooled,
        "pooled_vs_prior": {
            "A_constr_minus_prior_A": pooled["A_constr_by_value"] - PRIOR_A,
            "B_constr_minus_prior_B": pooled["B_constr_by_value"] - PRIOR_B,
            "A_union_minus_prior_A": pooled["A_union_by_value"] - PRIOR_A,
            "B_union_minus_prior_B": pooled["B_union_by_value"] - PRIOR_B,
            "B_union_direction_vs_0287": (
                "UP" if pooled["B_union_by_value"] > PRIOR_B + 0.005 else
                "DOWN" if pooled["B_union_by_value"] < PRIOR_B - 0.005 else "FLAT"),
        },
        "per_fiscal_quarter": per_q,
        "ranges_across_quarters": {
            "A_constr_by_value": rng("A_constr_by_value"),
            "B_constr_by_value": rng("B_constr_by_value"),
            "A_union_by_value": rng("A_union_by_value"),
            "B_union_by_value": rng("B_union_by_value"),
            "C_cn_share_of_total_haven_usd_equiv": rng("C_cn_share_of_total_haven_usd_equiv"),
        },
        "D_uncovered_tail_union": {
            "pooled_value_share": pooled["D_union_uncovered_value_share"],
            "pooled_count_share": pooled["D_union_uncovered_count_share"],
            "residence_split": uncov_res_split,
            "concentration": {
                "hhi_by_issuer": hhi,
                "top10_issuer_value_share_of_uncovered": top10_share,
                "interpretation": "computed on uncovered USD-equiv value by issuer; "
                                  "higher => concentrated, lower => diffuse.",
            },
            "top20_untagged_issuers_by_pooled_value": top_untagged,
            "obvious_chinese_names_still_in_tail": flagged_cn_in_tail,
            "obvious_cn_in_tail_note": (
                "Any obvious-CN name here means the construction is INCOMPLETE for that name, "
                "not that the tail is non-Chinese. Tencent/Meituan/Xiaomi are HKEX-listed, not "
                "SEC HFCAA filers, so they are genuinely unreachable by this free SEC/XBRL route."),
        },
    }
    return result


if __name__ == "__main__":
    res = main()
    with open(OUT_AUDIT, "w") as f:
        json.dump(res, f, indent=2)
    with open(OUT_VERIFY, "w") as f:
        json.dump(res, f, indent=2)
    p = res["pooled"]
    print("wrote", OUT_AUDIT, "and", OUT_VERIFY)
    print("positive haven rows:", res["inputs"]["positive_value_haven_rows"],
          "excluded:", res["inputs"]["rows_excluded_nonpositive_or_null"])
    print(f"A_constr={p['A_constr_by_value']:.4f}  B_constr={p['B_constr_by_value']:.4f}")
    print(f"A_union ={p['A_union_by_value']:.4f}  B_union ={p['B_union_by_value']:.4f}  (prior A={PRIOR_A:.4f} B={PRIOR_B:.4f})")
    print(f"B_union_with_handmap={p['B_union_with_handmap_by_value']:.4f}")
    print(f"CN-share USD-equiv={p['C_cn_share_of_total_haven_usd_equiv']:.4f}  CN-share RAW={p['C_cn_share_of_total_haven_RAW_mixed_ccy']:.4f}")
    print(f"B_union vs 0.287: {res['pooled_vs_prior']['B_union_direction_vs_0287']} "
          f"(delta={res['pooled_vs_prior']['B_union_minus_prior_B']:+.4f})")
    print(f"uncovered tail value share (union)={p['D_union_uncovered_value_share']:.4f}")
    print("obvious-CN names still in top-20 tail:",
          [t['issuer_name'] for t in res['D_uncovered_tail_union']['obvious_chinese_names_still_in_tail']])
