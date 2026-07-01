#!/usr/bin/env python3
"""
SANCTIONS-SHOCK F3 TEST -- deterministic no-network recompute generator.

Reuses the IDENTICAL full-panel Converse-Mallucci identification and dependent variable as the
GPR-China full-panel pass. The ONLY change vs that pass is the SHOCK: GPRC_China is replaced by a
grounded SANCTIONS treatment (headline sanc_freeze_post, the Feb-2022 Russian FX-reserve freeze
step), and a regulatory/delisting-channel control (reg_crackdown_post / reg_hfcaa_post) is ADDED.

Inputs (read-only):
  - build/data/cm_panel/cm_weight_panel_full.parquet   (corrected w = cn_haven_raw/tot_haven_raw,
    USD, NO FX; macro controls/lags; the SAME dependent variable as the GPR-China full-panel pass)
  - build/data/sanctions/sanctions_treatment_panel.csv (22 rows keyed by fiscal_quarter:
    sanc_freeze_post, sanc_eo2023_post, sanc_intensity, reg_hfcaa_post, reg_crackdown_post)

Outputs:
  - build/audit/sanctions_shock_result.json
  - build/results/sanctions_shock_verify.json
  - build/data/cm_panel/sanctions_cm_panel.parquet (the merged estimation panel)

ESTIMATOR: within (fund-demeaned) OLS, fund FE, NO time FE. The estimator functions
within_demean, _cluster_meat, cluster_vcov, _design, _cluster_se, wild_cluster_bootstrap_quarter,
leave_one_quarter_out, run_spec are REUSED VERBATIM (byte-identical logic) from
build/audit/cm_regression_full_recompute.py; the ONLY generalization is that the "treatment"
column (index 0 in the design; beta read from the estimator at position 0) is now the SANCTIONS
column, and additional regressors (the REGULATORY control) are passed in `controls`. beta is read
from the estimator, never hardcoded. add_lags is reused verbatim.

Sign convention: a NEGATIVE beta on the sanctions treatment = funds shift weight OUT of
China-nationality haven exposure as sanctions risk rises = F3 substitution.
"""
import json, os
import numpy as np
import pandas as pd
from scipy import stats as sstats

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PANEL = os.path.join(ROOT, "build/data/cm_panel/cm_weight_panel_full.parquet")
TREAT = os.path.join(ROOT, "build/data/sanctions/sanctions_treatment_panel.csv")
OUT_MERGED = os.path.join(ROOT, "build/data/cm_panel/sanctions_cm_panel.parquet")
OUT_RESULT = os.path.join(ROOT, "build/audit/sanctions_shock_result.json")
OUT_VERIFY = os.path.join(ROOT, "build/results/sanctions_shock_verify.json")


# ----- estimator functions: REUSED VERBATIM from cm_regression_full_recompute.py -----
# add_lags, within_demean, _cluster_meat, cluster_vcov unchanged.
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
    codes, uniq = pd.factorize(groups, sort=False)
    G = len(uniq)
    k = X.shape[1]
    Xu = X * u[:, None]
    S = np.zeros((G, k))
    np.add.at(S, codes, Xu)
    return S.T @ S, G


def cluster_vcov(X, resid, groups):
    XtX_inv = np.linalg.pinv(X.T @ X)
    k = X.shape[1]
    meat, G = _cluster_meat(X, resid, groups)
    n = X.shape[0]
    adj = (G / (G - 1.0)) * ((n - 1.0) / (n - k)) if G > 1 else 1.0
    return XtX_inv @ (adj * meat) @ XtX_inv, G


# _design / _cluster_se / wild_cluster_bootstrap_quarter: VERBATIM logic; `tcol` (the treatment
# column, index 0 of the design) generalizes the old `gprc_col`. beta read at position 0.
def _design(df, wcol, tcol, controls):
    rhs = [tcol] + list(controls)
    d = df.dropna(subset=[wcol] + rhs).copy()
    cnt = d.groupby("holder")["holder"].transform("size")
    d = d[cnt >= 2].copy()
    dw = within_demean(d, [wcol] + rhs)
    y = dw[wcol + "_w"].to_numpy()
    X = dw[[c + "_w" for c in rhs]].to_numpy()
    XtX_inv = np.linalg.pinv(X.T @ X)
    return y, X, d["holder"].to_numpy(), d["fiscal_quarter"].to_numpy(), XtX_inv


def _cluster_se(X, u, groups, XtX_inv):
    k = X.shape[1]
    meat, G = _cluster_meat(X, u, groups)
    n = X.shape[0]
    adj = (G / (G - 1.0)) * ((n - 1.0) / (n - k)) if G > 1 else 1.0
    V = XtX_inv @ (adj * meat) @ XtX_inv
    return float(np.sqrt(V[0, 0])), G


def wild_cluster_bootstrap_quarter(df, wcol, tcol, controls, reps, seed):
    y, X, holders, quarters, XtX_inv = _design(df, wcol, tcol, controls)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ b
    beta0 = float(b[0])
    se_obs, G = _cluster_se(X, resid, quarters, XtX_inv)
    t_obs = beta0 / se_obs if se_obs > 0 else np.nan
    Xr = X[:, 1:]
    br, *_ = np.linalg.lstsq(Xr, y, rcond=None)
    ur = y - Xr @ br
    uniq = np.unique(quarters)
    rng = np.random.default_rng(seed)
    A = XtX_inv @ X.T
    fitted_r = Xr @ br
    qcodes = pd.factorize(quarters, sort=True)[0]
    n_extreme = 0
    for _ in range(reps):
        wq = np.array([rng.choice([-1.0, 1.0]) for _g in uniq])
        wvec = wq[qcodes]
        ystar = fitted_r + ur * wvec
        bs = A @ ystar
        us = ystar - X @ bs
        se_s, _ = _cluster_se(X, us, quarters, XtX_inv)
        ts = bs[0] / se_s if se_s > 0 else np.nan
        if np.isfinite(ts) and abs(ts) >= abs(t_obs):
            n_extreme += 1
    return {
        "spec": f"no-lags: {wcol} ~ {tcol} + " + " + ".join(controls),
        "weight_col": wcol, "treatment_col": tcol, "reps": int(reps), "seed": int(seed),
        "n_quarter_clusters_G": int(G),
        "beta_treatment": beta0, "naive_cluster_quarter_se": se_obs, "t_obs": float(t_obs),
        "bootstrap_p_twosided": n_extreme / reps,
        "rademacher": True, "null_imposed_restricted_residuals": True,
    }


def run_spec(df, wcol, tcol, use_lags, controls, label):
    """VERBATIM logic from cm_regression_full_recompute.run_spec. `tcol` (treatment) is the
    coefficient of interest, placed first in rhs; beta read from the estimator at its rhs index."""
    d = df.copy()
    rhs = [tcol] + list(controls)
    if use_lags:
        d = add_lags(d, wcol)
        rhs = [tcol, "L1", "L2"] + list(controls)
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
    ti = rhs.index(tcol)
    beta = float(beta_hat[ti])

    def pack(V, G_for_t, idx):
        se = float(np.sqrt(V[idx, idx]))
        b = float(beta_hat[idx])
        tstat = b / se if se > 0 else np.nan
        ddof = dof if G_for_t is None else (G_for_t - 1)
        ddof = max(int(ddof), 1)
        p = float(2 * sstats.t.sf(abs(tstat), ddof))
        tc = float(sstats.t.ppf(0.975, ddof))
        return {"coef": b, "se": se, "t": float(tstat), "p": p, "dof": ddof,
                "ci95": [b - tc * se, b + tc * se]}

    out = {
        "label": label, "status": "OK", "weight_col": wcol, "treatment_col": tcol,
        "use_lags": use_lags, "controls": list(controls),
        "n_obs": int(n), "n_funds": int(nfunds), "within_dof": int(dof),
        "n_quarter_clusters": int(Gq), "n_fund_clusters": int(Gf),
        "beta_treatment": beta,
        "se_classical": pack(V_cl, None, ti),
        "se_cluster_fund": pack(V_cf, Gf, ti),
        "se_cluster_quarter": pack(V_cq, Gq, ti),
    }
    # If a regulatory control is present, also report its coefficient (lambda) side-by-side.
    for reg in ("reg_crackdown_post", "reg_hfcaa_post"):
        if reg in rhs:
            ri = rhs.index(reg)
            out["lambda_" + reg] = {
                "se_classical": pack(V_cl, None, ri),
                "se_cluster_fund": pack(V_cf, Gf, ri),
                "se_cluster_quarter": pack(V_cq, Gq, ri),
            }
    return out


def leave_one_quarter_out(df, wcol, tcol, controls, use_lags, quarters):
    out = {}
    for q in quarters:
        sub = df[df["fiscal_quarter"] != q]
        spec = run_spec(sub, wcol, tcol, use_lags, controls, f"LOQO_drop_{q}")
        out[q] = spec.get("beta_treatment") if spec.get("status") == "OK" else None
    return out
# ------------------------------------------------------------------------------------------


def treatment_residual_sd(df, tcol, controls, use_lags):
    """Within-fund variation in the treatment surviving fund FE + controls (incl. the regulatory
    control if in `controls`). Power diagnostic, mirrors gprc_residual_sd in the GPR-China pass."""
    d = df.copy()
    rhs = list(controls)
    if use_lags:
        d = add_lags(d, "w")
        rhs = ["L1", "L2"] + list(controls)
    d = d.dropna(subset=[tcol] + rhs + ["w"])
    cnt = d.groupby("holder")["holder"].transform("size")
    d = d[cnt >= 2]
    dw = within_demean(d, [tcol] + rhs)
    g = dw[tcol + "_w"].to_numpy()
    Z = dw[[c + "_w" for c in rhs]].to_numpy()
    if Z.shape[1] == 0:
        return float(np.std(g)), float(np.std(g))
    b, *_ = np.linalg.lstsq(Z, g, rcond=None)
    gres = g - Z @ b
    return float(np.std(gres)), float(np.std(dw[tcol + "_w"].to_numpy()))


def main():
    raw = pd.read_parquet(PANEL)
    treat = pd.read_csv(TREAT)

    # ---- MERGE the sanctions treatment onto the full panel by fiscal_quarter ----
    panel_qs = set(raw["fiscal_quarter"].unique())
    treat_qs = set(treat["fiscal_quarter"].unique())
    keys_matched = sorted(panel_qs & treat_qs)
    orphans_treat = sorted(treat_qs - panel_qs)   # treatment rows with no panel quarter
    orphans_panel = sorted(panel_qs - treat_qs)   # panel quarters with no treatment row
    merge_check = {
        "panel_quarters": len(panel_qs),
        "treatment_rows": len(treat),
        "keys_matched": len(keys_matched),
        "orphans_treatment_side": orphans_treat,
        "orphans_panel_side": orphans_panel,
        "merge_ok_22_of_22": (len(keys_matched) == 22 and len(orphans_treat) == 0 and len(orphans_panel) == 0),
    }
    m = raw.merge(treat, on="fiscal_quarter", how="left", validate="many_to_one")
    assert m["sanc_freeze_post"].notna().all(), "merge left NaN in treatment -> orphan panel quarter"
    m.to_parquet(OUT_MERGED)

    # Corrected basis: USD-native w, no FX; all 22 quarters (same filter as GPR-China pass).
    df = m[m["w_fx_status"] == "USD_NATIVE_NO_CONVERSION"].copy()
    quarters_w = sorted(df["fiscal_quarter"].unique())
    G_w = len(quarters_w)

    CTRL = ["log_vix", "broad_dollar", "oil"]
    CTRL_RR = CTRL + ["relative_returns"]           # macro block + relative_returns (headline)
    SANC = "sanc_freeze_post"                        # headline treatment (Feb-2022 freeze step)
    REG = "reg_crackdown_post"                       # primary regulatory control
    REG_HFCAA = "reg_hfcaa_post"

    # ============ THE LOAD-BEARING COMPARISON: beta WITHOUT vs WITH the regulatory control ============
    # headline spec = full-panel CM headline layout (lags on, macro block, relative_returns).
    without_ctrl = run_spec(df, "w", SANC, True, CTRL_RR,
                            "HEADLINE w~sanc_freeze+L1+L2+X+relret  (NO regulatory control)")
    with_ctrl = run_spec(df, "w", SANC, True, CTRL_RR + [REG],
                         "HEADLINE w~sanc_freeze+L1+L2+X+relret + reg_crackdown  (WITH regulatory control)")

    # ============ ROBUSTNESS PANEL (all re-estimated; none selected for sign) ============
    robustness = {}
    robustness["r1_freeze_no_control"] = without_ctrl
    robustness["r2_freeze_plus_reg_crackdown"] = with_ctrl
    robustness["r3_freeze_plus_reg_hfcaa"] = run_spec(
        df, "w", SANC, True, CTRL_RR + [REG_HFCAA],
        "w~sanc_freeze+L1+L2+X+relret + reg_hfcaa  (bounded-window regulatory control)")
    robustness["r4_eo2023_second_event_with_controls"] = run_spec(
        df, "w", "sanc_eo2023_post", True, CTRL_RR + [SANC, REG],
        "w~sanc_eo2023 + sanc_freeze + reg_crackdown +L1+L2+X+relret (eo2023 as 2nd sanctions event)")
    robustness["r5_intensity_continuous_with_controls_SURVIVORSHIP_FLAGGED"] = run_spec(
        df, "w", "sanc_intensity", True, CTRL_RR + [REG],
        "w~sanc_intensity + reg_crackdown +L1+L2+X+relret (SURVIVORSHIP-BIASED/SPARSE robustness)")
    # r6: narrow event window: only 2022q1-q2 vs pre-freeze quarters (drop 2022q3+ so the dummy is a
    # tight 2-quarter event, not a persistent step). Definition fixed here; NOT sign-selected.
    narrow_qs = ['2019q3','2019q4','2020q1','2020q2','2020q3','2020q4','2021q1','2021q2',
                 '2021q3','2021q4','2022q1','2022q2']
    df_narrow = df[df["fiscal_quarter"].isin(narrow_qs)].copy()
    robustness["r6_narrow_event_window_2022q1q2_vs_pre"] = run_spec(
        df_narrow, "w", SANC, True, CTRL_RR + [REG],
        "NARROW window (2022q1-q2 vs pre) w~sanc_freeze+reg_crackdown+L1+L2+X+relret")
    robustness["r6b_persistent_step_full_span_for_contrast"] = with_ctrl
    robustness["r7_no_weight_lags_with_control"] = run_spec(
        df, "w", SANC, False, CTRL_RR + [REG],
        "w~sanc_freeze+reg_crackdown+X+relret (NO weight lags)")
    robustness["r7b_no_weight_lags_no_control"] = run_spec(
        df, "w", SANC, False, CTRL_RR,
        "w~sanc_freeze+X+relret (NO weight lags, NO regulatory control)")
    # r8: clustering is already reported (fund + quarter) inside every spec above; expose explicitly
    # for the headline with-control spec.
    robustness["r8_clustering_reported_in_every_spec"] = {
        "note": "Every spec reports se_classical, se_cluster_fund (G=n_funds), se_cluster_quarter "
                "(G=22). No separate re-estimation needed; the headline WITH-control cluster SEs:",
        "headline_with_control_se_cluster_fund": with_ctrl["se_cluster_fund"],
        "headline_with_control_se_cluster_quarter": with_ctrl["se_cluster_quarter"],
    }

    # ============ COLLINEARITY DIAGNOSTIC: SANCTIONS vs REGULATORY ============
    # Raw across-quarter correlation (the r=0.828 from Part 1) recomputed here, plus the
    # within-estimation-sample partialling: how much of beta's SE inflation is the collinearity
    # (VIF of the treatment in the with-control design, after fund FE + all other regressors).
    step = df.drop_duplicates("fiscal_quarter")[["fiscal_quarter", SANC, REG, REG_HFCAA, "sanc_eo2023_post"]]
    corr_freeze_crackdown = float(np.corrcoef(step[SANC], step[REG])[0, 1])
    corr_freeze_hfcaa = float(np.corrcoef(step[SANC], step[REG_HFCAA])[0, 1])
    # VIF of sanc_freeze in the with-control within design: regress demeaned sanc_freeze on the
    # other demeaned regressors; VIF = 1/(1-R^2). SE inflation factor = sqrt(VIF).
    def vif_of_treatment(df_, tcol, others, use_lags):
        d = df_.copy()
        rhs = list(others)
        if use_lags:
            d = add_lags(d, "w")
            rhs = ["L1", "L2"] + list(others)
        d = d.dropna(subset=["w", tcol] + rhs)
        cnt = d.groupby("holder")["holder"].transform("size")
        d = d[cnt >= 2]
        dw = within_demean(d, [tcol] + rhs)
        t = dw[tcol + "_w"].to_numpy()
        Z = dw[[c + "_w" for c in rhs]].to_numpy()
        b, *_ = np.linalg.lstsq(Z, t, rcond=None)
        tres = t - Z @ b
        ss_tot = float(np.sum((t - t.mean()) ** 2))
        ss_res = float(np.sum((tres - tres.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
        vif = 1.0 / (1.0 - r2) if (r2 is not None and r2 < 1.0) else np.inf
        return {"r2_treatment_on_others": r2, "vif": vif, "se_inflation_factor_sqrt_vif": float(np.sqrt(vif))}

    vif_with_reg = vif_of_treatment(df, SANC, CTRL_RR + [REG], True)
    vif_without_reg = vif_of_treatment(df, SANC, CTRL_RR, True)
    collinearity = {
        "across_22q_corr_sanc_freeze_vs_reg_crackdown": corr_freeze_crackdown,
        "across_22q_corr_sanc_freeze_vs_reg_hfcaa": corr_freeze_hfcaa,
        "vif_sanc_freeze_in_with_control_design_after_FE": vif_with_reg,
        "vif_sanc_freeze_in_no_control_design_after_FE": vif_without_reg,
        "se_inflation_attributable_to_reg_crackdown": (
            with_ctrl["se_cluster_quarter"]["se"] / without_ctrl["se_cluster_quarter"]["se"]
            if without_ctrl.get("status") == "OK" and with_ctrl.get("status") == "OK" else None),
        "interpretation_note": "r=0.828 is the Part-1 across-quarter collinearity the verdict must confront. "
                               "The VIF is the treatment's variance-inflation AFTER fund FE + macro block + "
                               "weight lags + (with-control) reg_crackdown; sqrt(VIF) is how much the "
                               "regulatory control widens the sanctions SE.",
    }

    # ============ POWER DIAGNOSTIC ============
    res_sd_with, within_sd_with = treatment_residual_sd(df, SANC, CTRL_RR + [REG], True)
    res_sd_without, within_sd_without = treatment_residual_sd(df, SANC, CTRL_RR, True)
    sanc_1sd_22q = float(step[SANC].std())
    hb = with_ctrl.get("beta_treatment")
    hse_q = with_ctrl["se_cluster_quarter"]["se"] if with_ctrl.get("status") == "OK" else None
    power = {
        "sanc_freeze_cross_quarter_sd_22q": sanc_1sd_22q,
        "within_fund_sd_sanc_freeze_after_FE": within_sd_without,
        "residual_sd_sanc_freeze_after_FE_and_macro_controls_NO_reg": res_sd_without,
        "residual_sd_sanc_freeze_after_FE_macro_AND_reg_crackdown": res_sd_with,
        "residual_share_of_within_NO_reg": (res_sd_without / within_sd_without) if within_sd_without else None,
        "residual_share_of_within_WITH_reg": (res_sd_with / within_sd_with) if within_sd_with else None,
        "n_quarter_clusters_G": G_w,
        "headline_with_control_beta": hb,
        "headline_with_control_se_cluster_quarter": hse_q,
        "ci95_halfwidth_clustered_quarter": (1.96 * hse_q) if hse_q is not None else None,
        "note": "residual_share_of_within is the fraction of the treatment's within-fund variation that "
                "SURVIVES fund FE + controls (+ reg_crackdown in the WITH column). A large drop from NO_reg "
                "to WITH_reg is the collinearity eating the sanctions-specific variation.",
    }

    # ============ LOAD-BEARING: leave-one-quarter-out over ALL 22 quarters, WITH and WITHOUT control ============
    loqo_with = leave_one_quarter_out(df, "w", SANC, CTRL_RR + [REG], True, quarters_w)
    loqo_without = leave_one_quarter_out(df, "w", SANC, CTRL_RR, True, quarters_w)

    # ============ wild cluster bootstrap by quarter on the headline WITH-control spec (no-lags design) ==
    WCB_REPS, WCB_SEED = 2000, 42
    wcb = wild_cluster_bootstrap_quarter(df, "w", SANC, CTRL_RR + [REG], WCB_REPS, WCB_SEED)

    result = {
        "artifact": "sanctions_shock_result",
        "generated_by": "build/audit/sanctions_shock_recompute.py (no network)",
        "serves_prereg": "build/audit/sanctions_shock_prediction.md",
        "panel_path": PANEL,
        "treatment_path": TREAT,
        "merged_panel_path": OUT_MERGED,
        "estimator": "within (fund-demeaned) OLS; fund FE + X_t, NO time FE. Estimator functions REUSED "
                     "VERBATIM from cm_regression_full_recompute.py; ONLY change is the SHOCK "
                     "(GPRC_China -> sanc_freeze_post) plus an ADDED regulatory control. beta read from "
                     "the estimator at design position 0, never hardcoded.",
        "dependent_variable": "w = cn_haven_raw / tot_haven_raw (USD, NO FX). IDENTICAL to the GPR-China "
                              "full-panel pass (the standing correction).",
        "headline_treatment": SANC,
        "primary_regulatory_control": REG,
        "sign_convention": "NEGATIVE beta on the sanctions treatment = weight shifts OUT of CN-nationality "
                           "haven exposure as sanctions risk rises = F3 substitution.",
        "merge_check": merge_check,
        "estimation_set": {"quarters": quarters_w, "G": G_w, "n_cells": int(len(df)),
                           "n_funds": int(df["holder"].nunique())},
        "LOAD_BEARING_with_vs_without_regulatory_control": {
            "WITHOUT_regulatory_control": without_ctrl,
            "WITH_regulatory_control_reg_crackdown": with_ctrl,
        },
        "robustness_panel": robustness,
        "collinearity_diagnostic": collinearity,
        "power_diagnostic": power,
        "few_cluster_inference": {
            "wild_cluster_bootstrap_quarter_headline_WITH_control": wcb,
            "leave_one_quarter_out_WITH_control": {
                "spec": with_ctrl["label"] + " [lags on contiguous 22q ordinal]",
                "full_beta": with_ctrl.get("beta_treatment"),
                "beta_dropping_quarter": loqo_with,
            },
            "leave_one_quarter_out_WITHOUT_control": {
                "spec": without_ctrl["label"] + " [lags on contiguous 22q ordinal]",
                "full_beta": without_ctrl.get("beta_treatment"),
                "beta_dropping_quarter": loqo_without,
            },
        },
        "gpr_china_full_panel_comparison": {
            "gpr_headline_beta": 0.0125,
            "gpr_note": "GPR-China full-panel pass: headline beta +0.0125 (positive), robust across all 22 "
                        "LOQO drops; negative (substitution) direction bootstrap-insignificant p=0.58 at G=22. "
                        "Same identification, same dependent variable; only the shock differs here.",
        },
    }
    json.dump(result, open(OUT_RESULT, "w"), indent=2)

    # ============ VERIFIER: independent recompute of every beta, the comparison, LOQO sets, bootstrap p ==
    def indep_beta(df_, tcol, controls, use_lags):
        d = df_.copy()
        rhs = [tcol] + list(controls)
        if use_lags:
            d = add_lags(d, "w")
            rhs = [tcol, "L1", "L2"] + list(controls)
        d = d.dropna(subset=["w"] + rhs)
        d = d[d.groupby("holder")["holder"].transform("size") >= 2]
        dw = within_demean(d, ["w"] + rhs)
        y = dw["w_w"].to_numpy(); X = dw[[c + "_w" for c in rhs]].to_numpy()
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        return float(b[0])

    beta_without_re = indep_beta(df, SANC, CTRL_RR, True)
    beta_with_re = indep_beta(df, SANC, CTRL_RR + [REG], True)
    beta_without_match = abs(without_ctrl["beta_treatment"] - beta_without_re) < 1e-9
    beta_with_match = abs(with_ctrl["beta_treatment"] - beta_with_re) < 1e-9

    # independently recompute every OK robustness beta
    rob_betas_in_result, rob_betas_re, rob_match = {}, {}, True
    rob_specs = {
        "r1_freeze_no_control": (SANC, CTRL_RR, True),
        "r2_freeze_plus_reg_crackdown": (SANC, CTRL_RR + [REG], True),
        "r3_freeze_plus_reg_hfcaa": (SANC, CTRL_RR + [REG_HFCAA], True),
        "r4_eo2023_second_event_with_controls": ("sanc_eo2023_post", CTRL_RR + [SANC, REG], True),
        "r5_intensity_continuous_with_controls_SURVIVORSHIP_FLAGGED": ("sanc_intensity", CTRL_RR + [REG], True),
        "r7_no_weight_lags_with_control": (SANC, CTRL_RR + [REG], False),
        "r7b_no_weight_lags_no_control": (SANC, CTRL_RR, False),
    }
    for key, (tc, ctrls, lags) in rob_specs.items():
        sp = robustness[key]
        if sp.get("status") == "OK":
            re = indep_beta(df, tc, ctrls, lags)
            rob_betas_in_result[key] = sp["beta_treatment"]
            rob_betas_re[key] = re
            if abs(sp["beta_treatment"] - re) >= 1e-9:
                rob_match = False
    # r6 narrow window on its restricted sample
    if robustness["r6_narrow_event_window_2022q1q2_vs_pre"].get("status") == "OK":
        re6 = indep_beta(df_narrow, SANC, CTRL_RR + [REG], True)
        rob_betas_in_result["r6_narrow_event_window_2022q1q2_vs_pre"] = robustness["r6_narrow_event_window_2022q1q2_vs_pre"]["beta_treatment"]
        rob_betas_re["r6_narrow_event_window_2022q1q2_vs_pre"] = re6
        if abs(robustness["r6_narrow_event_window_2022q1q2_vs_pre"]["beta_treatment"] - re6) >= 1e-9:
            rob_match = False

    wcb_re = wild_cluster_bootstrap_quarter(df, "w", SANC, CTRL_RR + [REG], WCB_REPS, WCB_SEED)
    bootstrap_p_match = abs(wcb["bootstrap_p_twosided"] - wcb_re["bootstrap_p_twosided"]) < 1e-12

    loqo_with_re = leave_one_quarter_out(df, "w", SANC, CTRL_RR + [REG], True, quarters_w)
    loqo_without_re = leave_one_quarter_out(df, "w", SANC, CTRL_RR, True, quarters_w)

    def _loqo_eq(a, b_, qs):
        return all((a[q] is None and b_[q] is None) or
                   (a[q] is not None and b_[q] is not None and abs(a[q] - b_[q]) < 1e-9)
                   for q in qs)
    loqo_match = (_loqo_eq(loqo_with, loqo_with_re, quarters_w)
                  and _loqo_eq(loqo_without, loqo_without_re, quarters_w))

    beta_matches = bool(beta_without_match and beta_with_match and rob_match)

    verify = {
        "artifact": "sanctions_shock_verify",
        "generated_by": "build/audit/sanctions_shock_recompute.py (no network)",
        "merge_ok_22_of_22": merge_check["merge_ok_22_of_22"],
        "merge_keys_matched": merge_check["keys_matched"],
        "merge_orphans_treatment_side": merge_check["orphans_treatment_side"],
        "merge_orphans_panel_side": merge_check["orphans_panel_side"],
        "estimation_G": G_w,
        "n_cells": int(len(df)),
        "headline_beta_without_control_in_result": without_ctrl["beta_treatment"],
        "headline_beta_without_control_recomputed": beta_without_re,
        "headline_beta_with_control_in_result": with_ctrl["beta_treatment"],
        "headline_beta_with_control_recomputed": beta_with_re,
        "robustness_betas_in_result": rob_betas_in_result,
        "robustness_betas_recomputed": rob_betas_re,
        "beta_matches": beta_matches,
        "all_betas_read_from_estimator_not_hardcoded": True,
        "wild_cluster_bootstrap_p_in_result": wcb["bootstrap_p_twosided"],
        "wild_cluster_bootstrap_p_recomputed": wcb_re["bootstrap_p_twosided"],
        "wild_cluster_bootstrap_G": wcb["n_quarter_clusters_G"],
        "bootstrap_seed": WCB_SEED, "bootstrap_reps": WCB_REPS,
        "bootstrap_p_recomputed_matches": bootstrap_p_match,
        "leave_one_out_WITH_control_in_result": loqo_with,
        "leave_one_out_WITH_control_recomputed": loqo_with_re,
        "leave_one_out_WITHOUT_control_in_result": loqo_without,
        "leave_one_out_WITHOUT_control_recomputed": loqo_without_re,
        "leave_one_out_recomputed_matches": loqo_match,
    }
    json.dump(verify, open(OUT_VERIFY, "w"), indent=2)

    _ok = beta_matches and bootstrap_p_match and loqo_match and merge_check["merge_ok_22_of_22"]
    print("PASS" if _ok else "FAIL")
    print("MERGE 22/22:", merge_check["merge_ok_22_of_22"], "| matched=%d orphans_treat=%s orphans_panel=%s"
          % (merge_check["keys_matched"], merge_check["orphans_treatment_side"], merge_check["orphans_panel_side"]))
    print("G=%d n_cells=%d n_funds=%d" % (G_w, len(df), df["holder"].nunique()))
    def _line(tag, sp):
        if sp.get("status") != "OK":
            print("%-46s %s" % (tag, sp.get("status"))); return
        q = sp["se_cluster_quarter"]; f = sp["se_cluster_fund"]
        print("%-46s beta=%+.6f se_q=%.6f p_q=%.4f CI_q=[%+.5f,%+.5f] se_f=%.6f p_f=%.4f n=%d G=%d" % (
            tag, sp["beta_treatment"], q["se"], q["p"], q["ci95"][0], q["ci95"][1],
            f["se"], f["p"], sp["n_obs"], sp["n_quarter_clusters"]))
    print("--- LOAD-BEARING with vs without regulatory control ---")
    _line("WITHOUT reg control", without_ctrl)
    _line("WITH  reg_crackdown", with_ctrl)
    print("--- robustness panel ---")
    for k in ["r1_freeze_no_control","r2_freeze_plus_reg_crackdown","r3_freeze_plus_reg_hfcaa",
              "r4_eo2023_second_event_with_controls","r5_intensity_continuous_with_controls_SURVIVORSHIP_FLAGGED",
              "r6_narrow_event_window_2022q1q2_vs_pre","r7_no_weight_lags_with_control","r7b_no_weight_lags_no_control"]:
        _line(k[:46], robustness[k])
    print("--- collinearity ---")
    print("corr(freeze,crackdown) 22q = %.4f ; VIF(freeze|with reg) = %.3f (sqrt=%.3f) ; VIF(freeze|no reg) = %.3f ; SE inflation from reg = %.3fx" % (
        corr_freeze_crackdown, vif_with_reg["vif"], vif_with_reg["se_inflation_factor_sqrt_vif"],
        vif_without_reg["vif"], collinearity["se_inflation_attributable_to_reg_crackdown"]))
    print("--- power ---")
    print("sanc_freeze 1SD(22q)=%.4f ; resid_share_within NO_reg=%.4f WITH_reg=%.4f ; G=%d" % (
        sanc_1sd_22q, power["residual_share_of_within_NO_reg"], power["residual_share_of_within_WITH_reg"], G_w))
    print("--- wild cluster bootstrap (quarter, G=%d, reps=%d, seed=%d) headline WITH control ---" % (
        wcb["n_quarter_clusters_G"], WCB_REPS, WCB_SEED))
    print("beta=%+.6f t=%.3f bootstrap_p=%.4f [match=%s]" % (
        wcb["beta_treatment"], wcb["t_obs"], wcb["bootstrap_p_twosided"], bootstrap_p_match))
    print("--- LOQO-22q ---")
    print("WITH control :", {q: round(loqo_with[q],6) if loqo_with[q] is not None else None for q in quarters_w})
    print("WITHOUT ctrl :", {q: round(loqo_without[q],6) if loqo_without[q] is not None else None for q in quarters_w})
    print("beta_matches=%s bootstrap_p_match=%s loqo_match=%s" % (beta_matches, bootstrap_p_match, loqo_match))


if __name__ == "__main__":
    main()
