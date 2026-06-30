#!/usr/bin/env python3
"""
FWTW-RECONSTRUCTION Part 3 -- F3 separability statistic on EACH recovered interior.

NO NETWORK. Regenerates every number in build/audit/fwtw_recon_f3test.json from disk:
  build/audit/fwtw_recon_interiors.parquet         (the two interiors; per-holder China leg)
  build/data/nport/us_china_nationality_panel.parquet (US-leg source = haven-pool residual;
                                                        SAME panel the prior nationality test used)

SAME STATISTIC AS THE PRIOR TESTS (comparability is the point):
  - within-holder substitution sign = corr of q-o-q LOG-CHANGE (contemporaneous) between
    the China-nationality leg and the NON-CHINA haven leg.
  - The US Treasury / dollar leg is NOT in the N-PORT panel (0 USA rows; the panel is
    US-fund holdings of FOREIGN issuers only). The prior nationality separability test
    (build/audit/sep_retest_nationality_recompute_gcap.py, lines 159-172) documented this
    and used the NON-CHINA HAVEN LEG = haven_pool - china_nationality_mass as the
    substitution counter-leg. We use the IDENTICAL counter-leg here, now HOLDER-RESOLVED.
    (The TIC-SLT monthly test sep_definitive_test.py used a genuine TIC Table-1 US-leg, but
    that series lives in the TIC SLT extract, NOT this panel; the interiors parquet is built
    on this panel, so the panel's own prior nationality test is the matching construction.)
  - F3 substitution = US-leg / non-China haven leg DOWN while China-nationality exposure UP
    => NEGATIVE q-o-q co-movement = F3-LOADING (correct sign). POSITIVE = common growth = NO-F3.
  - footprint cosine = cosine of the mean per-haven log-change direction vectors (China leg
    vs non-China leg), SAME construction as part3_footprint_cosine.
  - lead/lag at quarterly resolution k in {-1,0,+1}, SAME xcorr definition.
  - 5 CONTIGUOUS calendar-quarter transitions only (exclude the two multi-quarter gaps),
    SAME window as the prior Part-3.

ANTI-PLANTING: the ~+0.5 / ~+0.521 predicted signs are OUTPUTS measured here from the
interiors, never inputs. No interior's F3 loading is assumed.
"""
import json, math, os
import pandas as pd

ROOT = "/home/user/dollar-breaking-point"
INTERIORS = os.path.join(ROOT, "build/audit/fwtw_recon_interiors.parquet")
PANEL = os.path.join(ROOT, "build/data/nport/us_china_nationality_panel.parquet")

HAVENS = ["CYM", "HKG", "VGB"]
ORDER = ["2019q3", "2019q4", "2020q1", "2020q2", "2020q3", "2022q1", "2022q2", "2024q4"]
# contiguous calendar-quarter transitions only -- IDENTICAL to prior Part-3 convention.
CONTIG = [("2019q3", "2019q4"), ("2019q4", "2020q1"), ("2020q1", "2020q2"),
          ("2020q2", "2020q3"), ("2022q1", "2022q2")]

# --- FX dict IDENTICAL to build/audit/freemap_coverage_recompute.py (provenance cites it) ---
HKD_PER_USD = 7.80
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
    return value

# ---------- correlation helpers (IDENTICAL to prior recompute) ----------
def logdiff_pairs(d, pairs):
    return [math.log(d[b]) - math.log(d[a]) for a, b in pairs]
def demean(x):
    m = sum(x) / len(x); return [xi - m for xi in x]
def corr(x, y):
    x = demean(x); y = demean(y)
    sx = math.sqrt(sum(i * i for i in x)); sy = math.sqrt(sum(i * i for i in y))
    if sx == 0 or sy == 0:
        return float("nan")
    return sum(a * b for a, b in zip(x, y)) / (sx * sy)
def cosine(u, v):
    du = math.sqrt(sum(a * a for a in u)); dv = math.sqrt(sum(b * b for b in v))
    if du == 0 or dv == 0:
        return float("nan")
    return sum(a * b for a, b in zip(u, v)) / (du * dv)
def xcorr(x, y, k):
    if k >= 0:
        xx, yy = x[:len(x) - k], y[k:]
    else:
        xx, yy = x[-k:], y[:len(y) + k]
    if len(xx) < 4:
        return None
    return corr(xx, yy)


def main():
    inter = pd.read_parquet(INTERIORS)
    # interiors carry, per (quarter, holder, nationality): the China-nationality mass under
    # each method on the China row, and row_mass_usd = the holder's haven pool (same on both rows).
    china = inter[inter.nationality == "China"].copy()

    # ---------------- AGGREGATE per-quarter legs (directly comparable to prior +0.521) -------
    agg = {}
    for q in ORDER:
        sub = china[china.fiscal_quarter == q]
        agg[q] = {
            "haven_pool": float(sub["row_mass_usd"].sum()),
            "m1_china": float(sub["method1_maxent_usd"].sum()),
            "m2_china": float(sub["method2_ras_usd"].sum()),
        }

    def method_block(china_key):
        cn = {q: agg[q][china_key] for q in ORDER}
        haven = {q: agg[q]["haven_pool"] for q in ORDER}
        nonchina = {q: haven[q] - cn[q] for q in ORDER}
        cn_lc = logdiff_pairs(cn, CONTIG)
        nc_lc = logdiff_pairs(nonchina, CONTIG)
        hav_lc = logdiff_pairs(haven, CONTIG)
        sub_sign = corr(cn_lc, nc_lc)                # within-pool substitution sign (pooled, aggregate)
        cn_vs_haven = corr(cn_lc, hav_lc)            # vs total haven (residence-proxy analog)
        leadlag = {str(k): (round(xcorr(cn_lc, nc_lc, k), 6)
                            if xcorr(cn_lc, nc_lc, k) is not None else None)
                   for k in [-1, 0, 1]}
        return {
            "china_leg_usd_by_q": {q: round(cn[q], 1) for q in ORDER},
            "nonchina_leg_usd_by_q": {q: round(nonchina[q], 1) for q in ORDER},
            "cn_logchange": [round(v, 6) for v in cn_lc],
            "nonchina_logchange": [round(v, 6) for v in nc_lc],
            "substitution_sign_aggregate_cn_vs_nonchina": round(sub_sign, 6),
            "cn_vs_total_haven_sign": round(cn_vs_haven, 6),
            "leadlag_quarterly_cn_vs_nonchina": leadlag,
        }

    m1 = method_block("m1_china")
    m2 = method_block("m2_china")

    # ---------------- GENUINELY WITHIN-HOLDER POOLED substitution sign ----------------------
    # Per holder, per contiguous transition: log-change of the holder's China leg vs the
    # holder's NON-CHINA haven leg (row_mass - china). Pool ALL (holder,transition) pairs with
    # both quarters present and all four masses > 0. This is the holder-varying dimension where
    # Method 1 (uniform aggregate fraction) and Method 2 (RAS holder-varying) can DIFFER.
    def within_holder_pooled(col):
        d = china.pivot_table(index="holder", columns="fiscal_quarter",
                              values=[col, "row_mass_usd"], aggfunc="sum")
        cn_lc, nc_lc = [], []
        for _, row in d.iterrows():
            for a, b in CONTIG:
                try:
                    ca, cb = row[(col, a)], row[(col, b)]
                    ra, rb = row[("row_mass_usd", a)], row[("row_mass_usd", b)]
                except KeyError:
                    continue
                if any(pd.isna(x) for x in [ca, cb, ra, rb]):
                    continue
                na, nb = ra - ca, rb - cb
                if ca > 0 and cb > 0 and na > 0 and nb > 0:
                    cn_lc.append(math.log(cb) - math.log(ca))
                    nc_lc.append(math.log(nb) - math.log(na))
        return {"n_holder_transition_pairs": len(cn_lc),
                "substitution_sign_within_holder_pooled": round(corr(cn_lc, nc_lc), 6)}
    m1_wh = within_holder_pooled("method1_maxent_usd")
    m2_wh = within_holder_pooled("method2_ras_usd")

    # ---------------- PER-HAVEN legs (need haven attribution from the panel) ----------------
    pan = pd.read_parquet(PANEL, columns=["fiscal_quarter", "cik", "series_id",
                                          "investment_country_iso3", "currency_value",
                                          "currency_code"])
    pan["holder"] = pan["cik"].astype(str).str.zfill(10) + "|" + pan["series_id"].astype(str)
    pan = pan[pan.investment_country_iso3.isin(HAVENS)].copy()
    pan = pan[(pan.currency_value.notna()) & (pan.currency_value > 0)].copy()  # sign filter
    pan["usd"] = [to_usd(v, c) for v, c in zip(pan.currency_value, pan.currency_code)]
    pool = (pan.groupby(["fiscal_quarter", "holder", "investment_country_iso3"])["usd"]
              .sum().reset_index())
    holder_pool = pool.groupby(["fiscal_quarter", "holder"])["usd"].sum().rename("holder_pool")
    pool = pool.merge(holder_pool, on=["fiscal_quarter", "holder"])
    pool["w_haven"] = pool["usd"] / pool["holder_pool"]   # holder's share in this haven

    ch = china[["fiscal_quarter", "holder", "method1_maxent_usd", "method2_ras_usd",
                "row_mass_usd"]].copy()
    pm = pool.merge(ch, on=["fiscal_quarter", "holder"], how="inner")
    pm["m1_china_h"] = pm["method1_maxent_usd"] * pm["w_haven"]
    pm["m2_china_h"] = pm["method2_ras_usd"] * pm["w_haven"]
    pm["nonchina_m1_h"] = pm["usd"] - pm["m1_china_h"]
    pm["nonchina_m2_h"] = pm["usd"] - pm["m2_china_h"]

    perhaven = pm.groupby(["fiscal_quarter", "investment_country_iso3"]).agg(
        haven_value=("usd", "sum"),
        m1_china=("m1_china_h", "sum"), m2_china=("m2_china_h", "sum"),
        nonchina_m1=("nonchina_m1_h", "sum"), nonchina_m2=("nonchina_m2_h", "sum"),
    ).reset_index()

    def per_haven_signs(china_col, nonchina_col):
        signs = {}
        foot_cn, foot_nc = [], []
        for h in HAVENS:
            hh = perhaven[perhaven.investment_country_iso3 == h].set_index("fiscal_quarter")
            cn = {q: float(hh.loc[q, china_col]) for q in ORDER if q in hh.index}
            nc = {q: float(hh.loc[q, nonchina_col]) for q in ORDER if q in hh.index}
            cn_lc, nc_lc = [], []
            for a, b in CONTIG:
                if cn.get(a, 0) > 0 and cn.get(b, 0) > 0 and nc.get(a, 0) > 0 and nc.get(b, 0) > 0:
                    cn_lc.append(math.log(cn[b]) - math.log(cn[a]))
                    nc_lc.append(math.log(nc[b]) - math.log(nc[a]))
                else:
                    cn_lc.append(0.0); nc_lc.append(0.0)
            s = corr(cn_lc, nc_lc)
            signs[h] = round(s, 6) if not math.isnan(s) else None
            foot_cn.append(sum(cn_lc) / len(cn_lc))
            foot_nc.append(sum(nc_lc) / len(nc_lc))
        fc = cosine(foot_cn, foot_nc)
        return signs, (round(fc, 6) if not math.isnan(fc) else None)

    m1_perhaven, m1_footprint = per_haven_signs("m1_china", "nonchina_m1")
    m2_perhaven, m2_footprint = per_haven_signs("m2_china", "nonchina_m2")

    # ---- holder-varying diagnostic: spread of per-holder China FRACTION across holders ----
    def frac_spread(col):
        f = (china[col] / china["row_mass_usd"]).replace([float("inf")], float("nan")).dropna()
        return {"min": round(float(f.min()), 6), "max": round(float(f.max()), 6),
                "std": round(float(f.std()), 6), "mean": round(float(f.mean()), 6)}
    m1_spread = frac_spread("method1_maxent_usd")
    m2_spread = frac_spread("method2_ras_usd")

    RESULT = {
        "n_holders_total": int(china["holder"].nunique()),
        "method1_maxent": {
            **m1, **m1_wh, "footprint_cosine_cn_vs_nonchina": m1_footprint,
            "per_haven_substitution_sign": m1_perhaven,
            "holder_china_fraction_spread": m1_spread,
        },
        "method2_ras": {
            **m2, **m2_wh, "footprint_cosine_cn_vs_nonchina": m2_footprint,
            "per_haven_substitution_sign": m2_perhaven,
            "holder_china_fraction_spread": m2_spread,
        },
    }
    print(json.dumps(RESULT, indent=2, default=str))
    return RESULT


if __name__ == "__main__":
    main()
