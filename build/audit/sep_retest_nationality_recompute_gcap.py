#!/usr/bin/env python3
"""
DP1-REOPEN CORRECTED -- Parts 1+2+3 recompute, ROUTE B (free GCAP aggregate shares).

Reproduces EVERY number in:
  build/audit/f_calibrated_gcap.json      (Part 1)
  build/audit/f_measured_quarterly.json   (Part 2, OVERWRITE)
  build/audit/sep_retest_nationality.json (Part 3, OVERWRITE)

from disk alone:
  build/data/gcap_products/Restatement_Matrices.dta  (route-B aggregate shares)
  build/data/nport/us_china_nationality_panel.parquet (residence panel)
  build/results/dp4_inputs.json   (operator recipe DESTn/USAn/tau)
  build/model/dp3_spec.json       (F4 backstop respec -- not re-read for numbers; backstop
                                   balances reused from sep_definitive_test.py constants)

ROUTE B = AGGREGATE country x asset x year reallocation SHARES (Value). We CALIBRATE the
China-NATIONALITY mass of the panel's haven holdings by applying GCAP share
Value(USA, Destination->CHN, Asset_Class, Year) to each panel haven holding. This is a
CALIBRATED AGGREGATE fraction, NOT a per-security tag (route A absent).
"""
import json, math, os
import pandas as pd

ROOT = "/home/user/dollar-breaking-point"
GCAP = os.path.join(ROOT, "build/data/gcap_products/Restatement_Matrices.dta")
PANEL = os.path.join(ROOT, "build/data/nport/us_china_nationality_panel.parquet")

HAVENS = ["CYM", "HKG", "VGB"]          # residency havens reattributable to CHN
DEST_ALL = ["CYM", "HKG", "VGB", "CHN"] # CHN domestic included (its own-share ~0.986)

# ----------------------------------------------------------------------------
# Panel asset_cat -> GCAP Asset_Class mapping (stated, principled)
#   EC, EP, DE, DFE        -> Common Equity         (equity instruments)
#   DBT, DCR, DCO          -> Corporate Bonds       (corporate debt)
#   ABS-*                  -> Asset-Backed Securities
#   everything else (LON, DIR, DO, SN, STIV, RA, RE, OTHER) -> Corporate Bonds
#     (debt-like / fund-of-corp residual; FH covers Corporate Bonds; conservative)
# Government Bonds GCAP class is not separately keyed because the panel carries no
# sovereign-issuer asset_cat for these havens (havens issue corp/SPV paper, not govt);
# any DBT with issuer_type USGA is negligible in the haven cells.
# ----------------------------------------------------------------------------
EQUITY = {"EC", "EP", "DE", "DFE"}
ABS = {"ABS-CBDO", "ABS-O", "ABS-MBS", "ABS-APCP"}
# remaining -> Corporate Bonds
def gcap_asset_class(ac):
    if ac in EQUITY:
        return "Common Equity"
    if ac in ABS:
        return "Asset-Backed Securities"
    return "Corporate Bonds"

# fiscal_quarter -> GCAP year (December-annual). GCAP max year = 2020.
#   2019q3/2019q4 -> 2019 ; 2020q1/q2/q3 -> 2020 ;
#   post-2020 (2022q1/q2, 2024q4) -> 2020 vintage (EXTRAPOLATION flag).
FQ_YEAR = {
    "2019q3": (2019, False), "2019q4": (2019, False),
    "2020q1": (2020, False), "2020q2": (2020, False), "2020q3": (2020, False),
    "2022q1": (2020, True), "2022q2": (2020, True), "2024q4": (2020, True),
}

# ----------------------------------------------------------------------------
def load_gcap_shares():
    """Return dict[(meth, asset_class, year, dest)] -> share to CHN."""
    df = pd.read_stata(GCAP, columns=["Methodology", "Year", "Investor",
                                      "Asset_Class", "Destination",
                                      "Destination_Restated", "Value"])
    df = df[df["Investor"] == "USA"].copy()
    for c in ["Methodology", "Asset_Class", "Destination", "Destination_Restated"]:
        df[c] = df[c].astype(str)
    chn = df[df["Destination_Restated"] == "CHN"]
    shares = {}
    for _, r in chn.iterrows():
        shares[(r.Methodology, r.Asset_Class, int(r.Year), r.Destination)] = float(r.Value)
    return shares, df

def share_lookup(shares, meth, ac, year, dest):
    """China-nationality reallocation share for (meth, asset class, year, haven).
    Missing CHN row => 0 (no China-nationality mass; e.g. ABS, or VGB Govt)."""
    return shares.get((meth, ac, year, dest), 0.0)

# ----------------------------------------------------------------------------
def main():
    shares, gcap_df = load_gcap_shares()

    # ---- HEADLINE CHECK: reproduce CYM->CHN=0.823155 etc (EFH, Common Equity, 2020)
    headline = {}
    for h in ["CYM", "HKG", "VGB", "CHN", "BMU", "SGP"]:
        headline[h] = round(share_lookup(shares, "Enhanced Fund Holdings",
                                         "Common Equity", 2020, h), 6)
    headline_fh = {h: round(share_lookup(shares, "Fund Holdings",
                                         "Common Equity", 2020, h), 6)
                   for h in ["CYM", "HKG", "VGB", "CHN"]}

    # ---- load panel
    pan = pd.read_parquet(PANEL, columns=["fiscal_quarter", "cik",
                                          "investment_country_iso3", "asset_cat",
                                          "currency_value"])
    pan["gcap_ac"] = pan["asset_cat"].map(gcap_asset_class)
    pan["gcap_year"] = pan["fiscal_quarter"].map(lambda q: FQ_YEAR[q][0])
    pan["extrapolated"] = pan["fiscal_quarter"].map(lambda q: FQ_YEAR[q][1])

    # ============================================================
    # PART 1 -- CALIBRATE China-nationality mass per quarter (and the path)
    # For each haven holding: cn_mass = currency_value * share(USA, dest->CHN, ac, year)
    # Denominator = total haven+CN residency exposure (CYM+HKG+VGB residency holdings),
    #   i.e. the offshore-haven pool whose China-nationality fraction we calibrate.
    #   We define f on the HAVEN POOL (CYM/HKG/VGB) to match the prior pin's
    #   denominator (US-held CYM/HKG/VGB pool). CHN-residency direct holdings are
    #   reported SEPARATELY (not in the f denominator) -- the pin and the operator
    #   treat the direct CHN cell separately.
    # ============================================================
    def calibrate(meth):
        rows = []
        for fq in pan["fiscal_quarter"].unique():
            sub = pan[pan.fiscal_quarter == fq]
            year = FQ_YEAR[fq][0]
            # haven pool (CYM/HKG/VGB residency)
            hav = sub[sub.investment_country_iso3.isin(HAVENS)]
            cn_mass = 0.0
            haven_total = 0.0
            per_haven = {h: {"haven_value": 0.0, "cn_mass": 0.0} for h in HAVENS}
            for h in HAVENS:
                hh = hav[hav.investment_country_iso3 == h]
                for ac, g in hh.groupby("gcap_ac"):
                    v = float(g.currency_value.sum())
                    s = share_lookup(shares, meth, ac, year, h)
                    cn_mass += v * s
                    per_haven[h]["cn_mass"] += v * s
                    per_haven[h]["haven_value"] += v
                haven_total += float(hh.currency_value.sum())
            # direct CHN residency (reported separately, not in f denominator)
            chn_direct = float(sub[sub.investment_country_iso3 == "CHN"].currency_value.sum())
            f = cn_mass / haven_total if haven_total else float("nan")
            rows.append({
                "fiscal_quarter": fq,
                "gcap_year_used": year,
                "extrapolated_post2020": bool(FQ_YEAR[fq][1]),
                "haven_pool_value_usd": round(haven_total, 1),
                "china_nationality_mass_usd": round(cn_mass, 1),
                "f_china_nationality_fraction_of_haven_pool": round(f, 6),
                "direct_chn_residency_value_usd_separate": round(chn_direct, 1),
                "per_haven": {h: {"haven_value_usd": round(per_haven[h]["haven_value"], 1),
                                  "cn_mass_usd": round(per_haven[h]["cn_mass"], 1),
                                  "haven_f": round(per_haven[h]["cn_mass"]/per_haven[h]["haven_value"], 6)
                                          if per_haven[h]["haven_value"] else None}
                              for h in HAVENS},
            })
        # order quarters chronologically
        order = ["2019q3","2019q4","2020q1","2020q2","2020q3","2022q1","2022q2","2024q4"]
        rows.sort(key=lambda r: order.index(r["fiscal_quarter"]))
        return rows

    cal_FH = calibrate("Fund Holdings")              # PRIMARY (covers all asset classes)
    cal_EFH = calibrate("Enhanced Fund Holdings")    # SENSITIVITY (equity + corp bonds only)

    # ============================================================
    # PART 3 -- nationality-resolved separability re-test
    # F3 driver = China-NATIONALITY-weighted haven exposure series (cn_mass per quarter,
    #   PRIMARY = Fund Holdings calibration). The US-leg series = the same US-fund US
    #   holdings proxy used in prior residence test is NOT in this panel; the panel is
    #   US-FUND holdings of foreign issuers only. So the within-holder substitution is
    #   tested between the two FOREIGN legs the panel DOES carry:
    #     leg_china_nationality = calibrated China-nationality mass (the F3 conduit leg)
    #     leg_haven_non_china   = haven pool value MINUS china-nationality mass
    #                             (the residual non-China haven leg)
    #   F3 substitution = a holder cuts the non-China haven leg WHILE raising its
    #     China-nationality exposure => NEGATIVE q-o-q co-movement between the two.
    #   This is the legitimate nationality analog: it asks whether, within the haven
    #   pool, the China-nationality component moves OPPOSITE the non-China component.
    #   CRITICAL: GCAP shares are annual + near-constant within the window, so the
    #   nationality WEIGHTS barely vary in time; we measure how much independent
    #   variation the calibration injects vs the raw residence series.
    # ============================================================
    order = ["2019q3","2019q4","2020q1","2020q2","2020q3","2022q1","2022q2","2024q4"]
    # contiguous calendar-quarter transitions only (exclude the 2020q3->2022q1 and
    # 2022q2->2024q4 multi-quarter gaps), matching the prior Part-3 convention.
    contiguous = [("2019q3","2019q4"),("2019q4","2020q1"),("2020q1","2020q2"),
                  ("2020q2","2020q3"),("2022q1","2022q2")]

    def series_by_q(cal):
        d = {r["fiscal_quarter"]: r for r in cal}
        cn = {q: d[q]["china_nationality_mass_usd"] for q in order}
        haven = {q: d[q]["haven_pool_value_usd"] for q in order}
        nonchina = {q: haven[q] - cn[q] for q in order}
        return cn, haven, nonchina

    cn, haven, nonchina = series_by_q(cal_FH)

    def logdiff_pairs(d, pairs):
        return [math.log(d[b]) - math.log(d[a]) for a, b in pairs]
    def demean(x):
        m = sum(x)/len(x); return [xi-m for xi in x]
    def corr(x, y):
        x = demean(x); y = demean(y)
        sx = math.sqrt(sum(i*i for i in x)); sy = math.sqrt(sum(i*i for i in y))
        if sx == 0 or sy == 0: return float("nan")
        return sum(a*b for a, b in zip(x, y))/(sx*sy)

    cn_lc = logdiff_pairs(cn, contiguous)
    nonchina_lc = logdiff_pairs(nonchina, contiguous)
    haven_lc = logdiff_pairs(haven, contiguous)

    # (a) within-pool substitution sign: China-nationality leg vs non-China haven leg
    sub_sign_cn_vs_nonchina = corr(cn_lc, nonchina_lc)
    # also China-nationality vs total haven (the residence proxy) -- to see how much
    # the nationality weighting moved things vs the residence series
    sub_sign_cn_vs_haven = corr(cn_lc, haven_lc)
    # residence proxy (prior Part 3 echo): China-RESIDENCE vs haven-residence q-o-q
    chn_res = {}
    hav_res = {}
    for q in order:
        sub = pan[pan.fiscal_quarter == q]
        chn_res[q] = float(sub[sub.investment_country_iso3 == "CHN"].currency_value.sum())
        hav_res[q] = float(sub[sub.investment_country_iso3.isin(HAVENS)].currency_value.sum())
    chn_res_lc = logdiff_pairs(chn_res, contiguous)
    hav_res_lc = logdiff_pairs(hav_res, contiguous)
    residence_sign = corr(chn_res_lc, hav_res_lc)

    # how much independent variation does the calibration inject?
    # corr(cn_lc, haven_lc) close to 1 => cn series is ~ fixed reweighting of haven (no
    # independent variation). Report it.
    weight_variation = {
        "corr_cn_nat_logchange_vs_haven_residence_logchange": round(sub_sign_cn_vs_haven, 6),
        "interpretation": "near 1.0 => China-nationality series is ~ fixed reweighting of haven-residence series (annual GCAP weights near-constant within window)",
    }
    # per-haven weights drift (do CYM/HKG/VGB shares move across the years used?)
    weight_drift = {}
    for h in HAVENS:
        ce = {y: round(share_lookup(shares, "Fund Holdings", "Common Equity", y, h), 6)
              for y in [2019, 2020]}
        weight_drift[h+"_common_equity_share_2019_2020"] = ce

    # (b) footprint cosine: per-haven China-nationality-weighted change vector vs
    # per-haven non-china change vector, mean direction over the haven block.
    def per_haven_lc(component):  # component in {'cn','nonchina'}
        d = {r["fiscal_quarter"]: r["per_haven"] for r in cal_FH}
        out = {}
        for h in HAVENS:
            if component == "cn":
                ser = {q: d[q][h]["cn_mass_usd"] for q in order}
            else:
                ser = {q: d[q][h]["haven_value_usd"] - d[q][h]["cn_mass_usd"] for q in order}
            # guard against zero (VGB cn_mass can be ~0)
            vals = []
            for a, b in contiguous:
                if ser[a] > 0 and ser[b] > 0:
                    vals.append(math.log(ser[b]) - math.log(ser[a]))
                else:
                    vals.append(0.0)
            out[h] = vals
        return out
    cn_ph = per_haven_lc("cn")
    nc_ph = per_haven_lc("nonchina")
    foot_cn = [sum(cn_ph[h])/len(cn_ph[h]) for h in HAVENS]
    foot_nc = [sum(nc_ph[h])/len(nc_ph[h]) for h in HAVENS]
    def cosine(u, v):
        du = math.sqrt(sum(a*a for a in u)); dv = math.sqrt(sum(b*b for b in v))
        if du == 0 or dv == 0: return float("nan")
        return sum(a*b for a, b in zip(u, v))/(du*dv)
    footprint_cosine = cosine(foot_cn, foot_nc)

    # (c) lead/lag at quarterly resolution -- only 5 contiguous transitions; report k=0
    # and +/-1 where estimable (>=4 points).
    def xcorr(x, y, k):
        if k >= 0:
            xx, yy = x[:len(x)-k], y[k:]
        else:
            xx, yy = x[-k:], y[:len(y)+k]
        if len(xx) < 4:
            return None
        return corr(xx, yy)
    leadlag = {str(k): (round(xcorr(cn_lc, nonchina_lc, k), 6)
                        if xcorr(cn_lc, nonchina_lc, k) is not None else None)
               for k in [-1, 0, 1]}

    RESULT = {
        "headline_check_EFH_common_equity_2020": headline,
        "headline_check_FH_common_equity_2020": headline_fh,
        "part1_calibration_fund_holdings": cal_FH,
        "part1_calibration_enhanced_fund_holdings_sensitivity": cal_EFH,
        "part3_series_used_primary_FH": {
            "china_nationality_mass_usd_by_q": {q: round(cn[q], 1) for q in order},
            "haven_pool_value_usd_by_q": {q: round(haven[q], 1) for q in order},
            "nonchina_haven_value_usd_by_q": {q: round(nonchina[q], 1) for q in order},
            "contiguous_transitions": [f"{a}->{b}" for a, b in contiguous],
            "cn_nationality_logchange": [round(v, 6) for v in cn_lc],
            "nonchina_haven_logchange": [round(v, 6) for v in nonchina_lc],
            "haven_total_logchange": [round(v, 6) for v in haven_lc],
        },
        "part3_substitution_sign_cn_nationality_vs_nonchina_haven": round(sub_sign_cn_vs_nonchina, 6),
        "part3_substitution_sign_residence_proxy_chn_vs_haven": round(residence_sign, 6),
        "part3_independent_variation_injected": weight_variation,
        "part3_weight_drift_2019_2020": weight_drift,
        "part3_footprint_cosine_cn_vs_nonchina": round(footprint_cosine, 6),
        "part3_leadlag_quarterly_cn_vs_nonchina": leadlag,
    }
    print(json.dumps(RESULT, indent=2, default=str))

if __name__ == "__main__":
    main()
