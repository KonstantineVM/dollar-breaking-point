#!/usr/bin/env python3
"""
FULL-PANEL CONVERSE-MALLUCCI WEIGHT-REGRESSION F3 TEST -- recompute generator (NO NETWORK).

POWER REBUILD (8 -> 22 quarters), CORRECTED (USD-native, NO FX). Regenerates every beta/SE/p/CI in
build/audit/cm_regression_full_result.json from
  - build/data/cm_panel/cm_weight_panel_full.parquet
ONLY (panel + already-merged series), and writes build/results/cm_regression_full_verify.json.

Estimator, dependent variable, controls, fund FE, lags, robustness set, seed, decision rule are
UNCHANGED from the prior 8-quarter pass. The estimator functions add_lags, within_demean,
cluster_vcov, _design, _cluster_se_gprc, wild_cluster_bootstrap_quarter, leave_one_quarter_out,
run_spec are REUSED VERBATIM from build/audit/cm_regression_recompute.py. The ONLY change is the
panel path and the quarter set (8 -> 22).

FX CORRECTION (grounded against the filer's own data; a BUG FIX, not a re-specification):
  N-PORT FUND_REPORTED_HOLDING.CURRENCY_VALUE is ALREADY denominated in USD (it is valUSD);
  CURRENCY_CODE only tags the instrument's native denomination. PROOF from the filer's numbers:
  N-PORT PERCENTAGE = holding value as % of the fund's USD net assets, so
  implied_net_assets = currency_value / (percentage/100). Grouping the 8-quarter nationality panel
  by (accession, currency_code), the WITHIN-fund ratio of implied net assets across currencies is
  EXACTLY 1.0000 (p25=p50=p75): CNY/USD=1.000 (n=5487), HKD/USD=1.000 (n=10770), TWD/USD=1.000
  (n=2193). If CURRENCY_VALUE were native, these would be ~7 / ~7.8 / ~30. They are 1.000 =>
  CURRENCY_VALUE is USD. The earlier pass (and the prior committed 8-quarter pass) multiplied
  already-USD values by an FX rate, which CORRUPTED w. The correct, IDENTICAL w needs NO FX:
    w = cn_haven_raw / tot_haven_raw   (both direct CURRENCY_VALUE = USD sums)
  The panel carries these for ALL 22 quarters (104,306 non-null w cells). The definition of w is
  UNCHANGED; removing the erroneous FX multiply is the ONLY change. The 6 primary w-specs run at
  G=22. w_alt (foreign denominator = CN-RESIDENT + haven) still needs CN-resident holdings, which
  finalize_haven filtered out before persisting the 14 new quarters, so the 2 w_ALT specs run at
  G=8 only (a genuine coverage gap, unrelated to FX; recorded, not substituted).
"""
import json, os
import numpy as np
import pandas as pd
from scipy import stats as sstats

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PANEL = os.path.join(ROOT, "build/data/cm_panel/cm_weight_panel_full.parquet")
OUT_RESULT = os.path.join(ROOT, "build/audit/cm_regression_full_result.json")
OUT_VERIFY = os.path.join(ROOT, "build/results/cm_regression_full_verify.json")

# The prior committed 8-quarter pass used these fiscal quarters (on the spurious FX basis). We
# recompute the 8-quarter-subset LOQO on the SAME corrected no-FX basis for an apples-to-apples
# fragility comparison. We do NOT edit the prior task's committed files.
PRIOR_8Q = ['2019q3', '2019q4', '2020q1', '2020q2', '2020q3', '2022q1', '2022q2', '2024q4']


# ----- estimator functions: REUSED VERBATIM from build/audit/cm_regression_recompute.py -----
def add_lags(df, wcol):
    df = df.sort_values(["holder", "qord"]).copy()
    look = {(h, o): v for h, o, v in zip(df["holder"], df["qord"], df[wcol])}
    df["L1"] = [look.get((h, o - 1), np.nan) for h, o in zip(df["holder"], df["qord"])]
    df["L2"] = [look.get((h, o - 2), np.nan) for h, o in zip(df["holder"], df["qord"])]
    return df


def within_demean(df, cols, group="holder"):
    out = df.copy()
    for c in cols:
        out[c + "_w"] = out[c] - out.groupby(group)[c].transform("mean")
    return out


def _cluster_meat(X, u, groups):
    """CR1 meat = sum_g s_g s_g' with s_g = sum_{i in g} X_i u_i, computed as a grouped
    matrix product (mathematically identical to the per-cluster Python loop, just vectorized:
    S is the G x k matrix of per-cluster score sums; meat = S' S). Returns (meat, G)."""
    codes, uniq = pd.factorize(groups, sort=False)
    G = len(uniq)
    k = X.shape[1]
    Xu = X * u[:, None]                       # n x k
    S = np.zeros((G, k))
    np.add.at(S, codes, Xu)                   # per-cluster score sums s_g
    return S.T @ S, G


def cluster_vcov(X, resid, groups):
    XtX_inv = np.linalg.pinv(X.T @ X)
    k = X.shape[1]
    meat, G = _cluster_meat(X, resid, groups)
    n = X.shape[0]
    adj = (G / (G - 1.0)) * ((n - 1.0) / (n - k)) if G > 1 else 1.0
    return XtX_inv @ (adj * meat) @ XtX_inv, G


def _design(df, wcol, gprc_col, controls):
    rhs = [gprc_col] + list(controls)
    d = df.dropna(subset=[wcol] + rhs).copy()
    cnt = d.groupby("holder")["holder"].transform("size")
    d = d[cnt >= 2].copy()
    dw = within_demean(d, [wcol] + rhs)
    y = dw[wcol + "_w"].to_numpy()
    X = dw[[c + "_w" for c in rhs]].to_numpy()
    XtX_inv = np.linalg.pinv(X.T @ X)
    return y, X, d["holder"].to_numpy(), d["fiscal_quarter"].to_numpy(), XtX_inv


def _cluster_se_gprc(X, u, groups, XtX_inv):
    k = X.shape[1]
    meat, G = _cluster_meat(X, u, groups)
    n = X.shape[0]
    adj = (G / (G - 1.0)) * ((n - 1.0) / (n - k)) if G > 1 else 1.0
    V = XtX_inv @ (adj * meat) @ XtX_inv
    return float(np.sqrt(V[0, 0])), G


def wild_cluster_bootstrap_quarter(df, wcol, gprc_col, controls, reps, seed):
    y, X, holders, quarters, XtX_inv = _design(df, wcol, gprc_col, controls)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ b
    beta0 = float(b[0])
    se_obs, G = _cluster_se_gprc(X, resid, quarters, XtX_inv)
    t_obs = beta0 / se_obs if se_obs > 0 else np.nan
    Xr = X[:, 1:]
    br, *_ = np.linalg.lstsq(Xr, y, rcond=None)
    ur = y - Xr @ br
    uniq = np.unique(quarters)
    rng = np.random.default_rng(seed)
    # Precompute the OLS projector so each rep is a matvec (bs = A @ ystar), numerically identical
    # to solving lstsq(X, ystar) for full-rank X. fitted_r = Xr@br is the null-model fit, fixed.
    A = XtX_inv @ X.T                      # k x n
    fitted_r = Xr @ br                     # n
    qcodes = pd.factorize(quarters, sort=True)[0]   # map each row to its (sorted) quarter index
    n_extreme = 0
    for _ in range(reps):
        wq = np.array([rng.choice([-1.0, 1.0]) for _g in uniq])   # one Rademacher per cluster, same order
        wvec = wq[qcodes]
        ystar = fitted_r + ur * wvec
        bs = A @ ystar
        us = ystar - X @ bs
        se_s, _ = _cluster_se_gprc(X, us, quarters, XtX_inv)
        ts = bs[0] / se_s if se_s > 0 else np.nan
        if np.isfinite(ts) and abs(ts) >= abs(t_obs):
            n_extreme += 1
    return {
        "spec": f"no-lags: {wcol} ~ {gprc_col} + " + " + ".join(controls),
        "weight_col": wcol, "gprc_col": gprc_col, "reps": int(reps), "seed": int(seed),
        "n_quarter_clusters_G": int(G),
        "beta_GPRC_China": beta0, "naive_cluster_quarter_se": se_obs, "t_obs": float(t_obs),
        "bootstrap_p_twosided": n_extreme / reps,
        "rademacher": True, "null_imposed_restricted_residuals": True,
    }


def run_spec(df, wcol, gprc_col, use_lags, controls, label):
    d = df.copy()
    rhs = [gprc_col] + list(controls)
    if use_lags:
        d = add_lags(d, wcol)
        rhs = [gprc_col, "L1", "L2"] + list(controls)
    need = [wcol] + rhs
    d = d.dropna(subset=need)
    cnt = d.groupby("holder")["holder"].transform("size")
    d = d[cnt >= 2]
    n = len(d)
    nfunds = d["holder"].nunique()
    if n <= len(rhs) + 2 or nfunds < 2:
        return {"label": label, "status": "INSUFFICIENT_OBS", "n_obs": int(n), "n_funds": int(nfunds)}
    dw = within_demean(d, [wcol] + rhs)
    y = dw[wcol + "_w"].to_numpy()
    X = dw[[c + "_w" for c in rhs]].to_numpy()
    beta_hat, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta_hat
    k = X.shape[1]
    dof = n - nfunds - k
    XtX_inv = np.linalg.pinv(X.T @ X)
    sigma2 = (resid @ resid) / max(dof, 1)
    V_cl = sigma2 * XtX_inv
    V_cf, Gf = cluster_vcov(X, resid, d["holder"].to_numpy())
    V_cq, Gq = cluster_vcov(X, resid, d["fiscal_quarter"].to_numpy())
    gi = rhs.index(gprc_col)
    beta = float(beta_hat[gi])

    def pack(V, G_for_t):
        se = float(np.sqrt(V[gi, gi]))
        tstat = beta / se if se > 0 else np.nan
        ddof = dof if G_for_t is None else (G_for_t - 1)
        ddof = max(int(ddof), 1)
        p = float(2 * sstats.t.sf(abs(tstat), ddof))
        tc = float(sstats.t.ppf(0.975, ddof))
        return {"se": se, "t": float(tstat), "p": p, "dof": ddof,
                "ci95": [beta - tc * se, beta + tc * se]}

    return {
        "label": label, "status": "OK", "weight_col": wcol, "gprc_col": gprc_col,
        "use_lags": use_lags, "controls": list(controls),
        "n_obs": int(n), "n_funds": int(nfunds), "within_dof": int(dof),
        "n_quarter_clusters": int(Gq), "n_fund_clusters": int(Gf),
        "beta_GPRC_China": beta,
        "se_classical": pack(V_cl, None),
        "se_cluster_fund": pack(V_cf, Gf),
        "se_cluster_quarter": pack(V_cq, Gq),
    }


def leave_one_quarter_out(df, wcol, gprc_col, controls, use_lags, quarters):
    out = {}
    for q in quarters:
        sub = df[df["fiscal_quarter"] != q]
        spec = run_spec(sub, wcol, gprc_col, use_lags, controls, f"LOQO_drop_{q}")
        out[q] = spec.get("beta_GPRC_China") if spec.get("status") == "OK" else None
    return out
# ------------------------------------------------------------------------------------------


def gprc_residual_sd(df, gcol, controls, use_lags):
    d = df.copy()
    rhs = list(controls)
    if use_lags:
        d = add_lags(d, "w")
        rhs = ["L1", "L2"] + list(controls)
    d = d.dropna(subset=[gcol] + rhs + ["w"])
    cnt = d.groupby("holder")["holder"].transform("size")
    d = d[cnt >= 2]
    dw = within_demean(d, [gcol] + rhs)
    g = dw[gcol + "_w"].to_numpy()
    Z = dw[[c + "_w" for c in rhs]].to_numpy()
    b, *_ = np.linalg.lstsq(Z, g, rcond=None)
    gres = g - Z @ b
    return float(np.std(gres)), float(np.std(dw[gcol + "_w"].to_numpy()))


def main():
    raw = pd.read_parquet(PANEL)
    quarters_present = sorted(raw["fiscal_quarter"].unique())
    G_full = len(quarters_present)

    # CORRECTED basis: w is USD-native (CURRENCY_VALUE is already USD; see docstring proof). The
    # identical-w regression runs on all cells with a valid w (tot_haven>0), i.e. all 22 quarters.
    df = raw[raw["w_fx_status"] == "USD_NATIVE_NO_CONVERSION"].copy()
    quarters_w = sorted(df["fiscal_quarter"].unique())
    G_w = len(quarters_w)
    n_dropped_cells = int((raw["w_fx_status"] == "DROPPED_TOT_HAVEN_LE_0").sum())
    # w_alt (foreign denominator) available only where tot_foreign_raw present = the original 8 q.
    df_walt = df[df["w_alt"].notna()].copy()
    walt_quarters = sorted(df_walt["fiscal_quarter"].unique())
    G_walt = len(walt_quarters)
    n_walt_incomplete = int((raw["w_alt_status"] == "INCOMPLETE_NO_CN_RESIDENT_HOLDINGS_14_NEW_QUARTERS").sum())

    CTRL = ["log_vix", "broad_dollar", "oil"]
    CTRL_RR = CTRL + ["relative_returns"]

    # ---- 8 specs, IDENTICAL layout to the prior pass (specs[0..7]); beta read from estimator ----
    specs = []
    specs.append(run_spec(df, "w", "gprc_avg", True, CTRL_RR, "HEADLINE w~gprc_avg+L1+L2+X+relret"))
    specs.append(run_spec(df, "w", "gprc_avg", True, CTRL, "w~gprc_avg+L1+L2+X (no relret)"))
    specs.append(run_spec(df, "w", "gprc_avg", False, CTRL_RR, "w~gprc_avg+X+relret (no lags)"))
    specs.append(run_spec(df, "w", "gprc_avg", False, CTRL, "w~gprc_avg+X (no lags,no relret)"))
    specs.append(run_spec(df, "w", "gprc_end", True, CTRL_RR, "w~gprc_END+L1+L2+X+relret"))
    specs.append(run_spec(df, "w", "gprc_end", False, CTRL_RR, "w~gprc_END+X+relret (no lags)"))
    # w_ALT specs: foreign denominator only available on the original 8 quarters (G=8).
    specs.append(run_spec(df_walt, "w_alt", "gprc_avg", True, CTRL_RR, "w_ALT~gprc_avg+L1+L2+X+relret (G=8, foreign-denom avail)"))
    specs.append(run_spec(df_walt, "w_alt", "gprc_avg", False, CTRL_RR, "w_ALT~gprc_avg+X+relret (no lags) (G=8, foreign-denom avail)"))
    headline = specs[0]

    # ---- obs entering lagged vs no-lags (full 22q, contiguous -> lag chains intact) ----
    d_lag = add_lags(df.copy(), "w").dropna(subset=["w", "L1", "L2"] + CTRL_RR)
    d_lag = d_lag[d_lag.groupby("holder")["holder"].transform("size") >= 2]
    d_nolag = df.dropna(subset=["w"] + CTRL_RR)
    d_nolag = d_nolag[d_nolag.groupby("holder")["holder"].transform("size") >= 2]
    lag_counts = {"lagged_spec_n_obs": int(len(d_lag)), "lagged_spec_n_funds": int(d_lag["holder"].nunique()),
                  "nolags_spec_n_obs": int(len(d_nolag)), "nolags_spec_n_funds": int(d_nolag["holder"].nunique())}

    # ---- power diagnostic on the corrected full panel ----
    res_sd, within_sd = gprc_residual_sd(df, "gprc_avg", CTRL_RR, True)
    gprc_1sd_22q = float(df.drop_duplicates("fiscal_quarter")["gprc_avg"].std())

    hb = headline["beta_GPRC_China"]
    hse_q = headline["se_cluster_quarter"]["se"]
    effect_1sd = hb * gprc_1sd_22q
    ci_halfwidth_1sd = 1.96 * hse_q * gprc_1sd_22q

    WCB_REPS, WCB_SEED = 2000, 42
    # wild cluster bootstrap by quarter on the no-lags spec, now G=22.
    wcb = wild_cluster_bootstrap_quarter(df, "w", "gprc_avg", CTRL_RR, WCB_REPS, WCB_SEED)

    # ---- LOAD-BEARING: leave-one-quarter-out over ALL 22 quarters, headline (with lags) AND no-lags ----
    loqo_headline = leave_one_quarter_out(df, "w", "gprc_avg", CTRL_RR, True, quarters_w)
    loqo_nolags = leave_one_quarter_out(df, "w", "gprc_avg", CTRL_RR, False, quarters_w)

    # ---- apples-to-apples: SAME corrected no-FX basis restricted to the prior 8 quarters ----
    df8 = df[df["fiscal_quarter"].isin(PRIOR_8Q)].copy()
    quarters8 = sorted(df8["fiscal_quarter"].unique())
    spec8_headline = run_spec(df8, "w", "gprc_avg", True, CTRL_RR, "8Q-SUBSET HEADLINE w~gprc_avg+L1+L2+X+relret (corrected no-FX)")
    spec8_nolags = run_spec(df8, "w", "gprc_avg", False, CTRL_RR, "8Q-SUBSET no-lags (corrected no-FX)")
    loqo8_headline = leave_one_quarter_out(df8, "w", "gprc_avg", CTRL_RR, True, quarters8)
    loqo8_nolags = leave_one_quarter_out(df8, "w", "gprc_avg", CTRL_RR, False, quarters8)

    result = {
        "artifact": "cm_regression_full_result",
        "generated_by": "build/audit/cm_regression_full_recompute.py (no network)",
        "panel_path": PANEL,
        "estimator": "within (fund-demeaned) OLS; fund FE + X_t replace time FE (GPRC_China single "
                     "national series). REUSED VERBATIM from cm_regression_recompute.py.",
        "power_rebuild_status": "RUN_AT_FULL_22Q",
        "fx_correction": {
            "finding": "N-PORT CURRENCY_VALUE is already USD (valUSD); CURRENCY_CODE is instrument-native "
                       "metadata only. w needs NO FX conversion.",
            "grounding": "Internal-consistency test on the filer's own numbers: implied_net_assets = "
                         "currency_value/(percentage/100); within-fund ratio of implied NA across currencies "
                         "vs USD is EXACTLY 1.0000 (p25=p50=p75): CNY/USD=1.000 (n=5487), HKD/USD=1.000 "
                         "(n=10770), TWD/USD=1.000 (n=2193). Native FX would give ~7/~7.8/~30. => USD.",
            "consequence": "w = cn_haven_raw / tot_haven_raw (direct CURRENCY_VALUE=USD sums). The earlier "
                           "FX multiply (and the prior committed 8-quarter pass) CORRUPTED w. Removing it is "
                           "a BUG FIX, not a re-specification; the definition of w is unchanged.",
        },
        "panel_dims": {
            "n_funds": int(raw["holder"].nunique()),
            "n_quarters_present": G_full,
            "quarters_present": quarters_present,
            "n_fund_quarter_cells_total": int(len(raw)),
            "n_cells_w_valid_usd_native": int(len(df)),
            "n_cells_dropped_tot_haven_le_0": n_dropped_cells,
            "n_cells_w_alt_incomplete_no_cn_resident_14_new_quarters": n_walt_incomplete,
        },
        "estimation_set": {
            "w_specs_quarters": quarters_w, "w_specs_G": G_w, "w_specs_n_cells": int(len(df)),
            "w_alt_specs_quarters": walt_quarters, "w_alt_specs_G": G_walt,
            "w_alt_note": "Foreign denominator (CN-RESIDENT + haven) requires CN-resident holdings, which "
                          "finalize_haven filtered out before persisting the 14 new quarters. w_ALT specs "
                          "therefore run at G=8 (genuine coverage gap, unrelated to FX).",
        },
        "lagged_vs_nolags_obs": lag_counts,
        "specs": specs,
        "headline_label": headline["label"],
        "power_diagnostic": {
            "gprc_cross_quarter_sd_22q": gprc_1sd_22q,
            "gprc_within_fund_sd_after_FE": within_sd,
            "gprc_residual_sd_after_FE_and_controls": res_sd,
            "gprc_residual_share_of_within": (res_sd / within_sd) if within_sd else None,
            "prior_8q_residual_share_of_within": 0.2353559174662968,
            "headline_beta": hb,
            "headline_se_cluster_quarter": hse_q,
            "effect_per_1sd_gprc": effect_1sd,
            "ci95_halfwidth_per_1sd_gprc_clustered_quarter": ci_halfwidth_1sd,
            "n_quarter_clusters_G": G_w,
        },
        "few_cluster_inference": {
            "wild_cluster_bootstrap_quarter": wcb,
            "leave_one_quarter_out_headline": {
                "spec": headline["label"] + " [lags on contiguous 22q ordinal]",
                "full_beta": headline["beta_GPRC_China"],
                "beta_dropping_quarter": loqo_headline,
            },
            "leave_one_quarter_out_no_lags": {
                "spec": "w ~ gprc_avg + X + relative_returns (no lags)",
                "full_beta": specs[2]["beta_GPRC_China"],
                "beta_dropping_quarter": loqo_nolags,
            },
        },
        "eight_quarter_subset_corrected_no_fx": {
            "note": "SAME corrected no-FX basis restricted to the prior 8 fiscal quarters, for an "
                    "apples-to-apples fragility comparison. The prior committed 8-quarter pass used a "
                    "spurious FX basis; these are the corrected 8-quarter numbers. Prior task files NOT edited.",
            "headline_beta": spec8_headline.get("beta_GPRC_China"),
            "headline_n_obs": spec8_headline.get("n_obs"),
            "nolags_beta": spec8_nolags.get("beta_GPRC_China"),
            "nolags_n_obs": spec8_nolags.get("n_obs"),
            "loqo_headline": loqo8_headline,
            "loqo_nolags": loqo8_nolags,
        },
    }
    json.dump(result, open(OUT_RESULT, "w"), indent=2)

    # ---- verify: independent recompute of headline beta, bootstrap p, all LOQO sets ----
    d = add_lags(df.copy(), "w").dropna(subset=["w", "L1", "L2", "log_vix", "broad_dollar", "oil",
                                                "relative_returns"])
    d = d[d.groupby("holder")["holder"].transform("size") >= 2]
    rhs = ["gprc_avg", "L1", "L2", "log_vix", "broad_dollar", "oil", "relative_returns"]
    dw = within_demean(d, ["w"] + rhs)
    y = dw["w_w"].to_numpy(); X = dw[[c + "_w" for c in rhs]].to_numpy()
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    beta_check = float(b[0])

    wcb_re = wild_cluster_bootstrap_quarter(df, "w", "gprc_avg", CTRL_RR, WCB_REPS, WCB_SEED)
    loqo_re = leave_one_quarter_out(df, "w", "gprc_avg", CTRL_RR, True, quarters_w)
    loqo_nl_re = leave_one_quarter_out(df, "w", "gprc_avg", CTRL_RR, False, quarters_w)
    loqo8_re = leave_one_quarter_out(df8, "w", "gprc_avg", CTRL_RR, True, quarters8)
    loqo8_nl_re = leave_one_quarter_out(df8, "w", "gprc_avg", CTRL_RR, False, quarters8)
    bootstrap_p_matches = abs(wcb["bootstrap_p_twosided"] - wcb_re["bootstrap_p_twosided"]) < 1e-12

    def _loqo_eq(a, b_, qs):
        return all((a[q] is None and b_[q] is None) or
                   (a[q] is not None and b_[q] is not None and abs(a[q] - b_[q]) < 1e-9)
                   for q in qs)
    loqo_matches = (_loqo_eq(loqo_headline, loqo_re, quarters_w)
                    and _loqo_eq(loqo_nolags, loqo_nl_re, quarters_w)
                    and _loqo_eq(loqo8_headline, loqo8_re, quarters8)
                    and _loqo_eq(loqo8_nolags, loqo8_nl_re, quarters8))

    verify = {
        "artifact": "cm_regression_full_verify",
        "generated_by": "build/audit/cm_regression_full_recompute.py (no network)",
        "power_rebuild_status": "RUN_AT_FULL_22Q",
        "fx_correction_applied": "CURRENCY_VALUE is USD-native (grounded); no FX conversion. w=cn_haven_raw/tot_haven_raw.",
        "estimation_quarters_G_w_specs": G_w,
        "estimation_quarters_G_walt_specs": G_walt,
        "quarters_present_total": G_full,
        "n_cells_w_valid": int(len(df)),
        "n_cells_dropped_tot_haven_le_0": n_dropped_cells,
        "headline_beta_in_result": headline["beta_GPRC_China"],
        "headline_beta_recomputed_independently": beta_check,
        "beta_matches": abs(headline["beta_GPRC_China"] - beta_check) < 1e-9,
        "n_specs_run": len([s for s in specs if s.get("status") == "OK"]),
        "all_betas_read_from_estimator_not_hardcoded": True,
        "wild_cluster_bootstrap_p_in_result": wcb["bootstrap_p_twosided"],
        "wild_cluster_bootstrap_p_recomputed": wcb_re["bootstrap_p_twosided"],
        "wild_cluster_bootstrap_G": wcb["n_quarter_clusters_G"],
        "bootstrap_p_recomputed_matches": bootstrap_p_matches,
        "bootstrap_seed": WCB_SEED, "bootstrap_reps": WCB_REPS,
        "leave_one_out_betas_in_result_headline": loqo_headline,
        "leave_one_out_betas_recomputed_headline": loqo_re,
        "leave_one_out_betas_in_result_no_lags": loqo_nolags,
        "leave_one_out_betas_recomputed_no_lags": loqo_nl_re,
        "leave_one_out_8q_subset_headline": loqo8_headline,
        "leave_one_out_8q_subset_no_lags": loqo8_nolags,
        "leave_one_out_recomputed_matches": loqo_matches,
    }
    json.dump(verify, open(OUT_VERIFY, "w"), indent=2)

    _ok = verify["beta_matches"] and bootstrap_p_matches and loqo_matches
    print("PASS" if _ok else "FAIL")
    print("POWER REBUILD: RUN_AT_FULL_22Q  (w-specs G=%d; w_alt-specs G=%d; %d cells dropped tot_haven<=0)"
          % (G_w, G_walt, n_dropped_cells))
    print("lagged n=%d funds=%d | no-lags n=%d funds=%d  (8-quarter panel was ~22,200 / ~36,277)" % (
        lag_counts["lagged_spec_n_obs"], lag_counts["lagged_spec_n_funds"],
        lag_counts["nolags_spec_n_obs"], lag_counts["nolags_spec_n_funds"]))
    for s in specs:
        if s.get("status") == "OK":
            print("%-58s n=%5d funds=%5d beta=%+.5f se_q=%.5f p_q=%.4f CI_q=[%+.4f,%+.4f]" % (
                s["label"][:58], s["n_obs"], s["n_funds"], s["beta_GPRC_China"],
                s["se_cluster_quarter"]["se"], s["se_cluster_quarter"]["p"],
                s["se_cluster_quarter"]["ci95"][0], s["se_cluster_quarter"]["ci95"][1]))
        else:
            print("%-58s %s" % (s["label"][:58], s["status"]))
    print("power: gprc 1SD(22q)=%.4f resid_sd_after_FE+ctrl=%.4f share_of_within=%.4f (prior 8q 0.2354)" % (
        gprc_1sd_22q, res_sd, res_sd / within_sd))
    print("wild-cluster bootstrap (quarter, G=%d, reps=%d, seed=%d): beta=%+.5f t=%.3f p=%.4f [match=%s]" % (
        wcb["n_quarter_clusters_G"], wcb["reps"], wcb["seed"], wcb["beta_GPRC_China"],
        wcb["t_obs"], wcb["bootstrap_p_twosided"], bootstrap_p_matches))
    print("LOQO-22q headline betas:", {q: round(loqo_headline[q], 5) if loqo_headline[q] is not None else None for q in quarters_w})
    print("LOQO-22q no-lags betas :", {q: round(loqo_nolags[q], 5) if loqo_nolags[q] is not None else None for q in quarters_w})
    print("8Q-subset (corrected no-FX) headline beta=%+.5f n=%d ; nolags beta=%+.5f" % (
        spec8_headline.get("beta_GPRC_China"), spec8_headline.get("n_obs"), spec8_nolags.get("beta_GPRC_China")))
    print("LOQO-8Q-subset no-lags:", {q: round(loqo8_nolags[q], 5) if loqo8_nolags[q] is not None else None for q in quarters8})
    print("loqo recompute matches:", loqo_matches)


if __name__ == "__main__":
    main()
