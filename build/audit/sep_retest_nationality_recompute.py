#!/usr/bin/env python3
"""
DP1-REOPEN Parts 2 & 3 recompute.

Reads ONLY the on-disk N-PORT residence panel and recomputes:
  PART 2  -- residence-only CN-vs-haven USD holdings per fiscal quarter, the
             RESIDENCE ratio CN/(CN+haven) (explicitly NOT the nationality f),
             and the 2019->2024 residence trend.
  PART 3  -- a RESIDENCE-only secondary co-movement sign on the quarterly N-PORT
             panel (CN-resident vs haven-resident US-fund holdings), labelled as
             residence-basis, NOT the nationality F3 test.

NO nationality fraction is computed: issuer_nationality is uniformly
'UNDETERMINED-NO-PUBLIC-CROSSWALK' (the commercially-gated HOLE). This script
asserts that and refuses to fabricate f.

Run: python3 build/audit/sep_retest_nationality_recompute.py
"""
import json
import math
import pandas as pd

PANEL = "build/data/nport/us_china_nationality_panel.parquet"

# Fiscal-quarter chronological order for the 8-quarter documented subset.
FQ_ORDER = ["2019q3", "2019q4", "2020q1", "2020q2", "2020q3", "2022q1", "2022q2", "2024q4"]
HAVEN = ["CYM", "HKG", "VGB"]


def load():
    return pd.read_parquet(
        PANEL,
        columns=[
            "fiscal_quarter",
            "investment_country_iso3",
            "issuer_nationality",
            "currency_value",
        ],
    )


def assert_hole(df):
    vals = set(df["issuer_nationality"].unique().tolist())
    assert vals == {"UNDETERMINED-NO-PUBLIC-CROSSWALK"}, (
        "issuer_nationality is NOT uniformly the HOLE value; refusing to proceed: %r" % vals
    )
    return sorted(vals)


def part2(df):
    """Residence-only USD holdings of CN-resident vs haven-resident issuers, per fiscal quarter."""
    g = df.groupby(["fiscal_quarter", "investment_country_iso3"])["currency_value"].sum().unstack(fill_value=0.0)
    rows = []
    for fq in FQ_ORDER:
        cn = float(g.loc[fq, "CHN"]) if "CHN" in g.columns else 0.0
        cym = float(g.loc[fq, "CYM"]) if "CYM" in g.columns else 0.0
        hkg = float(g.loc[fq, "HKG"]) if "HKG" in g.columns else 0.0
        vgb = float(g.loc[fq, "VGB"]) if "VGB" in g.columns else 0.0
        haven = cym + hkg + vgb
        denom = cn + haven
        ratio = (cn / denom) if denom != 0 else None
        rows.append(
            {
                "fiscal_quarter": fq,
                "cn_resident_usd_value": round(cn, 1),
                "cym_resident_usd_value": round(cym, 1),
                "hkg_resident_usd_value": round(hkg, 1),
                "vgb_resident_usd_value": round(vgb, 1),
                "haven_resident_usd_value": round(haven, 1),
                "residence_ratio_cn_over_cn_plus_haven": round(ratio, 6) if ratio is not None else None,
            }
        )
    return rows


def part3(df):
    """RESIDENCE-only secondary co-movement: q-o-q log-change of CN-resident vs
    haven-resident US-fund total USD holdings, across the 5 consecutive
    fiscal-quarter transitions in the subset (2019q3->2020q3). The 2020q3->2022q1
    etc. gaps are NOT contiguous, so transitions are restricted to adjacent
    calendar quarters."""
    g = df.groupby(["fiscal_quarter", "investment_country_iso3"])["currency_value"].sum().unstack(fill_value=0.0)
    cn = {fq: float(g.loc[fq, "CHN"]) for fq in FQ_ORDER}
    haven = {fq: float(sum(g.loc[fq, c] for c in HAVEN if c in g.columns)) for fq in FQ_ORDER}

    # contiguous calendar-quarter pairs only
    contiguous_pairs = [
        ("2019q3", "2019q4"),
        ("2019q4", "2020q1"),
        ("2020q1", "2020q2"),
        ("2020q2", "2020q3"),
        ("2022q1", "2022q2"),
    ]
    cn_chg, hv_chg, used = [], [], []
    for a, b in contiguous_pairs:
        if cn[a] > 0 and cn[b] > 0 and haven[a] > 0 and haven[b] > 0:
            cn_chg.append(math.log(cn[b]) - math.log(cn[a]))
            hv_chg.append(math.log(haven[b]) - math.log(haven[a]))
            used.append("%s->%s" % (a, b))

    def corr(x, y):
        n = len(x)
        mx = sum(x) / n
        my = sum(y) / n
        num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        dx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
        dy = math.sqrt(sum((yi - my) ** 2 for yi in y))
        return num / (dx * dy) if dx > 0 and dy > 0 else None

    r_logchange = corr(cn_chg, hv_chg)

    # levels across all 8 fiscal quarters (coarser, includes gaps)
    cn_lvl = [cn[fq] for fq in FQ_ORDER]
    hv_lvl = [haven[fq] for fq in FQ_ORDER]
    r_levels = corr(cn_lvl, hv_lvl)

    return {
        "contiguous_transitions_used": used,
        "n_contiguous_transitions": len(used),
        "cn_resident_logchange": [round(v, 6) for v in cn_chg],
        "haven_resident_logchange": [round(v, 6) for v in hv_chg],
        "residence_logchange_corr_cn_vs_haven": round(r_logchange, 6) if r_logchange is not None else None,
        "residence_level_corr_cn_vs_haven_all8q": round(r_levels, 6) if r_levels is not None else None,
    }


def main():
    df = load()
    hole = assert_hole(df)
    p2 = part2(df)
    p3 = part3(df)
    out = {
        "issuer_nationality_distinct_values": hole,
        "part2_residence_per_quarter": p2,
        "part2_residence_trend_2019q3_to_2024q4": {
            "first": p2[0]["residence_ratio_cn_over_cn_plus_haven"],
            "last": p2[-1]["residence_ratio_cn_over_cn_plus_haven"],
            "delta": round(p2[-1]["residence_ratio_cn_over_cn_plus_haven"] - p2[0]["residence_ratio_cn_over_cn_plus_haven"], 6),
        },
        "part3_residence_secondary_check": p3,
    }
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
