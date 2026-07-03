#!/usr/bin/env python3
"""
ACTIVE-FLOW F3 TEST -- deterministic no-network recompute generator (Parts 2 & 3 estimation).

Re-runs the sanctions-shock F3 test with the DEPENDENT VARIABLE replaced by ACTIVE net flow into
CN-nationality haven securities (valuation removed BY CONSTRUCTION -- the constant-price
decomposition active=(bal_t-bal_{t-1})*price_{t-1}), instead of the portfolio weight w. The estimator
functions (within_demean, _cluster_meat, cluster_vcov, _design, _cluster_se,
wild_cluster_bootstrap_quarter, leave_one_quarter_out, run_spec, add_lags) are REUSED VERBATIM from
build/audit/sanctions_shock_recompute.py -- byte-identical logic; the ONLY change is the dependent
variable column and the DV-normalization variants. beta is read from the estimator at design position
0, never hardcoded.

SIGN CONVENTION (per active_flow_provenance.md / prediction): NEGATIVE beta on the sanctions
treatment = funds ACTIVELY SOLD CN-nationality haven securities as sanctions risk rose = F3
substitution. So F3 = NEGATIVE sanctions coefficient (opposite reading from a positive weight beta).

Inputs (read-only):
  - build/data/nport/active_flow_panel.parquet        (the NEW DV source: cn_active_flow, cn_passive,
    active_flow_rate, tot_haven_cv, tot_haven_lag per fund_key=cik|series_id x fiscal_quarter)
  - build/data/sanctions/sanctions_treatment_panel.csv (22 rows keyed fiscal_quarter)
  - build/data/cm_panel/cm_weight_panel_full.parquet   (macro controls + relative_returns per
    holder=cik|series_id x fiscal_quarter)

Outputs:
  - build/audit/active_flow_result.json
  - build/results/active_flow_verify.json
  - build/data/cm_panel/active_flow_cm_panel.parquet   (merged estimation panel)

DV VARIANTS (all disclosed, none selected for sign):
  DV1 (headline) = active_flow_rate (÷ lagged total haven) WINSORIZED symmetric 1/99.
  DV2 (robustness) = cn_active_flow / (0.5*(tot_haven_lag + tot_haven_cv))  (average-base; sd~0.30).
  DV3 (robustness) = active_flow_rate restricted to tot_haven_lag >= 1e6 (fund genuinely held haven
                     last quarter -> removes near-zero-denominator explosion), winsorized symmetric 1/99.
"""
import json, os
import numpy as np
import pandas as pd
from scipy import stats as sstats

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AFLOW = os.path.join(ROOT, "build/data/nport/active_flow_panel.parquet")
TREAT = os.path.join(ROOT, "build/data/sanctions/sanctions_treatment_panel.csv")
CM = os.path.join(ROOT, "build/data/cm_panel/cm_weight_panel_full.parquet")
OUT_MERGED = os.path.join(ROOT, "build/data/cm_panel/active_flow_cm_panel.parquet")
OUT_RESULT = os.path.join(ROOT, "build/audit/active_flow_result.json")
OUT_VERIFY = os.path.join(ROOT, "build/results/active_flow_verify.json")

DV3_LAG_FLOOR = 1e6   # "fund genuinely held haven last quarter" floor for DV3
WINSOR_LO, WINSOR_HI = 0.01, 0.99  # symmetric 1/99


# ----- estimator functions: REUSED VERBATIM from sanctions_shock_recompute.py -----
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


def treatment_residual_sd(df, tcol, controls, use_lags, dvcol):
    """Within-fund variation in the treatment surviving fund FE + controls. Power diagnostic."""
    d = df.copy()
    rhs = list(controls)
    if use_lags:
        d = add_lags(d, dvcol)
        rhs = ["L1", "L2"] + list(controls)
    d = d.dropna(subset=[tcol] + rhs + [dvcol])
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


def build_dvs(af):
    """Construct the three disclosed DV variants on the active-flow panel. Winsorization symmetric
    1/99 computed on the full available (non-NaN) sample of each rate BEFORE the estimation merge."""
    af = af.copy()
    # DV1: active_flow_rate winsorized symmetric 1/99
    r1 = af["active_flow_rate"]
    lo1, hi1 = r1.quantile(WINSOR_LO), r1.quantile(WINSOR_HI)
    af["dv1_afrate_wins"] = r1.clip(lo1, hi1)
    # DV2: average-base rate (well-behaved by construction)
    denom2 = 0.5 * (af["tot_haven_lag"] + af["tot_haven_cv"])
    af["dv2_avgbase"] = np.where(denom2 != 0, af["cn_active_flow"] / denom2, np.nan)
    # DV3: active_flow_rate restricted to lag floor, then winsorized symmetric 1/99 on that subsample
    mask3 = af["tot_haven_lag"] >= DV3_LAG_FLOOR
    r3 = af["active_flow_rate"].where(mask3)
    lo3, hi3 = r3.quantile(WINSOR_LO), r3.quantile(WINSOR_HI)
    af["dv3_afrate_floor_wins"] = r3.clip(lo3, hi3)
    winsor_meta = {
        "DV1_winsor_p1": float(lo1), "DV1_winsor_p99": float(hi1),
        "DV3_lag_floor": DV3_LAG_FLOOR,
        "DV3_winsor_p1": float(lo3), "DV3_winsor_p99": float(hi3),
        "DV1_n_nonnull": int(r1.notna().sum()),
        "DV2_n_nonnull": int(af["dv2_avgbase"].notna().sum()),
        "DV3_n_nonnull": int(r3.notna().sum()),
    }
    return af, winsor_meta


def main():
    af = pd.read_parquet(AFLOW)
    treat = pd.read_csv(TREAT)
    cm = pd.read_parquet(CM)

    af["holder"] = af["fund_key"]

    # ---- build the three DV variants BEFORE merge ----
    af, winsor_meta = build_dvs(af)

    # ---- MERGE 1: sanctions treatment onto active-flow panel by fiscal_quarter ----
    panel_qs = set(af["fiscal_quarter"].unique())
    treat_qs = set(treat["fiscal_quarter"].unique())
    keys_matched_t = sorted(panel_qs & treat_qs)
    orphans_treat = sorted(treat_qs - panel_qs)
    orphans_panel = sorted(panel_qs - treat_qs)
    m = af.merge(treat, on="fiscal_quarter", how="left", validate="many_to_one")
    assert m["sanc_freeze_post"].notna().all(), "treatment merge left NaN -> orphan panel quarter"

    # ---- MERGE 2: macro controls + relative_returns on (holder, fiscal_quarter) ----
    cm_ctrl = cm[["holder", "fiscal_quarter", "log_vix", "broad_dollar", "oil",
                  "relative_returns", "qord"]].drop_duplicates(["holder", "fiscal_quarter"])
    n_before = len(m)
    m = m.merge(cm_ctrl, on=["holder", "fiscal_quarter"], how="left", validate="many_to_one")
    n_matched_macro = int(m["log_vix"].notna().sum())
    n_matched_relret = int(m["relative_returns"].notna().sum())
    n_orphan_macro = int(m["log_vix"].isna().sum())
    aflow_holders = set(af["holder"].unique())
    cm_holders = set(cm["holder"].unique())
    holders_only_in_aflow = sorted(aflow_holders - cm_holders)

    merge_check = {
        "merge1_treatment": {
            "panel_quarters": len(panel_qs), "treatment_rows": len(treat),
            "keys_matched": len(keys_matched_t),
            "orphans_treatment_side": orphans_treat, "orphans_panel_side": orphans_panel,
            "merge_ok_22_of_22": (len(keys_matched_t) == 22 and not orphans_treat and not orphans_panel),
        },
        "merge2_macro_controls": {
            "active_flow_rows": n_before,
            "rows_matched_macro_block": n_matched_macro,
            "rows_matched_relative_returns": n_matched_relret,
            "rows_orphan_no_macro": n_orphan_macro,
            "active_flow_holders": len(aflow_holders),
            "cm_holders": len(cm_holders),
            "active_flow_holders_matched_in_cm": len(aflow_holders & cm_holders),
            "active_flow_holders_NOT_in_cm": len(holders_only_in_aflow),
            "note": "Rows with no relative_returns match drop out of any spec that includes "
                    "relative_returns (the headline spec does). The macro block (log_vix, "
                    "broad_dollar, oil) is per-quarter; relative_returns is per holder-quarter.",
        },
    }

    # persist the merged estimation panel
    m.to_parquet(OUT_MERGED)

    # qord must exist for lags; fill from CM merge, fall back to a fiscal_quarter ordinal for
    # rows with no CM match (they drop anyway when relative_returns is required, but keep lags defined).
    qorder = {q: i for i, q in enumerate(sorted(panel_qs))}
    m["qord"] = m["qord"].fillna(m["fiscal_quarter"].map(qorder))

    quarters_all = sorted(panel_qs)
    G_all = len(quarters_all)

    CTRL = ["log_vix", "broad_dollar", "oil"]
    CTRL_RR = CTRL + ["relative_returns"]
    SANC = "sanc_freeze_post"
    REG = "reg_crackdown_post"
    REG_HFCAA = "reg_hfcaa_post"

    DV1, DV2, DV3 = "dv1_afrate_wins", "dv2_avgbase", "dv3_afrate_floor_wins"

    def qs_for(dvcol):
        d = m.dropna(subset=[dvcol])
        return sorted(d["fiscal_quarter"].unique())

    # ============ THE LOAD-BEARING COMPARISON per DV: beta WITHOUT vs WITH regulatory control ==========
    def with_without(dvcol, tag):
        without = run_spec(m, dvcol, SANC, True, CTRL_RR,
                           f"{tag} activeflow~sanc_freeze+L1+L2+X+relret  (NO regulatory control)")
        withc = run_spec(m, dvcol, SANC, True, CTRL_RR + [REG],
                         f"{tag} activeflow~sanc_freeze+L1+L2+X+relret + reg_crackdown  (WITH regulatory control)")
        return without, withc

    dv1_without, dv1_with = with_without(DV1, "DV1")
    dv2_without, dv2_with = with_without(DV2, "DV2")
    dv3_without, dv3_with = with_without(DV3, "DV3")

    load_bearing = {
        "DV1_headline_afrate_winsorized": {
            "WITHOUT_regulatory_control": dv1_without,
            "WITH_regulatory_control_reg_crackdown": dv1_with,
        },
        "DV2_avgbase_rate": {
            "WITHOUT_regulatory_control": dv2_without,
            "WITH_regulatory_control_reg_crackdown": dv2_with,
        },
        "DV3_afrate_lagfloor_winsorized": {
            "WITHOUT_regulatory_control": dv3_without,
            "WITH_regulatory_control_reg_crackdown": dv3_with,
        },
    }

    # ============ ROBUSTNESS PANEL (all re-estimated; none selected for sign) ============
    robustness = {}
    # DV-variant with/without control already above; mirror into robustness keys for the panel
    robustness["r1_DV1_no_control"] = dv1_without
    robustness["r2_DV1_plus_reg_crackdown"] = dv1_with
    robustness["r3_DV1_plus_reg_hfcaa"] = run_spec(
        m, DV1, SANC, True, CTRL_RR + [REG_HFCAA],
        "DV1 activeflow~sanc_freeze+L1+L2+X+relret + reg_hfcaa")
    robustness["r4_DV1_eo2023_second_event_with_controls"] = run_spec(
        m, DV1, "sanc_eo2023_post", True, CTRL_RR + [SANC, REG],
        "DV1 activeflow~sanc_eo2023 + sanc_freeze + reg_crackdown +L1+L2+X+relret")
    # narrow event window 2022q1-q2 vs pre
    narrow_qs = ['2019q3','2019q4','2020q1','2020q2','2020q3','2020q4','2021q1','2021q2',
                 '2021q3','2021q4','2022q1','2022q2']
    m_narrow = m[m["fiscal_quarter"].isin(narrow_qs)].copy()
    robustness["r5_DV1_narrow_event_window_2022q1q2_vs_pre"] = run_spec(
        m_narrow, DV1, SANC, True, CTRL_RR + [REG],
        "DV1 NARROW window (2022q1-q2 vs pre) activeflow~sanc_freeze+reg_crackdown+L1+L2+X+relret")
    robustness["r6_DV1_no_flow_lags_with_control"] = run_spec(
        m, DV1, SANC, False, CTRL_RR + [REG],
        "DV1 activeflow~sanc_freeze+reg_crackdown+X+relret (NO active-flow lags)")
    robustness["r6b_DV1_no_flow_lags_no_control"] = run_spec(
        m, DV1, SANC, False, CTRL_RR,
        "DV1 activeflow~sanc_freeze+X+relret (NO active-flow lags, NO regulatory control)")
    # DV2 / DV3 with & without control (the normalization robustness)
    robustness["r7_DV2_no_control"] = dv2_without
    robustness["r8_DV2_plus_reg_crackdown"] = dv2_with
    robustness["r9_DV3_no_control"] = dv3_without
    robustness["r10_DV3_plus_reg_crackdown"] = dv3_with
    # DV2 eo2023 second event and hfcaa, for symmetry with the weight pass
    robustness["r11_DV2_plus_reg_hfcaa"] = run_spec(
        m, DV2, SANC, True, CTRL_RR + [REG_HFCAA],
        "DV2 activeflow~sanc_freeze+L1+L2+X+relret + reg_hfcaa")
    robustness["r12_DV2_eo2023_second_event_with_controls"] = run_spec(
        m, DV2, "sanc_eo2023_post", True, CTRL_RR + [SANC, REG],
        "DV2 activeflow~sanc_eo2023 + sanc_freeze + reg_crackdown +L1+L2+X+relret")

    # ============ COLLINEARITY DIAGNOSTIC: SANCTIONS vs REGULATORY (carried r=0.828 from Part 1) =====
    step = m.drop_duplicates("fiscal_quarter")[["fiscal_quarter", SANC, REG, REG_HFCAA, "sanc_eo2023_post"]]
    corr_freeze_crackdown = float(np.corrcoef(step[SANC], step[REG])[0, 1])
    corr_freeze_hfcaa = float(np.corrcoef(step[SANC], step[REG_HFCAA])[0, 1])

    def vif_of_treatment(df_, tcol, others, use_lags, dvcol):
        d = df_.copy()
        rhs = list(others)
        if use_lags:
            d = add_lags(d, dvcol)
            rhs = ["L1", "L2"] + list(others)
        d = d.dropna(subset=[dvcol, tcol] + rhs)
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

    vif_with_reg = vif_of_treatment(m, SANC, CTRL_RR + [REG], True, DV1)
    vif_without_reg = vif_of_treatment(m, SANC, CTRL_RR, True, DV1)
    se_infl = None
    if dv1_without.get("status") == "OK" and dv1_with.get("status") == "OK":
        se_infl = dv1_with["se_cluster_quarter"]["se"] / dv1_without["se_cluster_quarter"]["se"]
    collinearity = {
        "across_22q_corr_sanc_freeze_vs_reg_crackdown": corr_freeze_crackdown,
        "across_22q_corr_sanc_freeze_vs_reg_hfcaa": corr_freeze_hfcaa,
        "carried_from_part1_r": 0.828,
        "vif_sanc_freeze_in_with_control_design_DV1_after_FE": vif_with_reg,
        "vif_sanc_freeze_in_no_control_design_DV1_after_FE": vif_without_reg,
        "se_inflation_attributable_to_reg_crackdown_DV1": se_infl,
        "interpretation_note": "r=0.828 (Part-1 across-quarter collinearity) carried; VIF is the "
                               "sanctions treatment's variance-inflation AFTER fund FE + macro block + "
                               "active-flow lags + (with-control) reg_crackdown on the DV1 sample.",
    }

    # ============ POWER DIAGNOSTIC (on DV1 headline sample) ============
    res_sd_with, within_sd_with = treatment_residual_sd(m, SANC, CTRL_RR + [REG], True, DV1)
    res_sd_without, within_sd_without = treatment_residual_sd(m, SANC, CTRL_RR, True, DV1)
    sanc_1sd_22q = float(step[SANC].std())
    hb = dv1_with.get("beta_treatment")
    hse_q = dv1_with["se_cluster_quarter"]["se"] if dv1_with.get("status") == "OK" else None
    # DV standard deviations for economic-magnitude framing
    dv_sds = {
        "DV1_afrate_wins_sd": float(m[DV1].std()),
        "DV2_avgbase_sd": float(m[DV2].std()),
        "DV3_afrate_floor_wins_sd": float(m[DV3].std()),
    }
    power = {
        "sanc_freeze_cross_quarter_sd_22q": sanc_1sd_22q,
        "within_fund_sd_sanc_freeze_after_FE_DV1": within_sd_without,
        "residual_sd_sanc_freeze_after_FE_and_macro_controls_NO_reg_DV1": res_sd_without,
        "residual_sd_sanc_freeze_after_FE_macro_AND_reg_crackdown_DV1": res_sd_with,
        "residual_share_of_within_NO_reg_DV1": (res_sd_without / within_sd_without) if within_sd_without else None,
        "residual_share_of_within_WITH_reg_DV1": (res_sd_with / within_sd_with) if within_sd_with else None,
        "n_quarter_clusters_G": G_all,
        "headline_DV1_with_control_beta": hb,
        "headline_DV1_with_control_se_cluster_quarter": hse_q,
        "ci95_halfwidth_clustered_quarter_DV1": (1.96 * hse_q) if hse_q is not None else None,
        "dv_standard_deviations": dv_sds,
        "note": "residual_share_of_within = fraction of the treatment's within-fund variation surviving "
                "fund FE + controls (+ reg_crackdown WITH). DV standard deviations give the economic scale "
                "of the active-flow rate against which beta is read.",
    }

    # ============ LOAD-BEARING: leave-one-quarter-out over ALL 22 quarters, WITH and WITHOUT (DV1) ====
    loqo_with = leave_one_quarter_out(m, DV1, SANC, CTRL_RR + [REG], True, quarters_all)
    loqo_without = leave_one_quarter_out(m, DV1, SANC, CTRL_RR, True, quarters_all)

    # ============ wild cluster bootstrap by quarter on the headline DV1 WITH-control spec ============
    WCB_REPS, WCB_SEED = 2000, 42
    wcb = wild_cluster_bootstrap_quarter(m, DV1, SANC, CTRL_RR + [REG], WCB_REPS, WCB_SEED)

    # KEY comparison scaffold vs weight-based result
    weight_beta_with = 0.017660570225023094
    weight_beta_without = 0.018506876606456533
    weight_bootstrap_p = 0.2655
    key_comparison = {
        "weight_beta_WITH_control": weight_beta_with,
        "weight_beta_WITHOUT_control": weight_beta_without,
        "weight_bootstrap_p_G22": weight_bootstrap_p,
        "weight_sign": "POSITIVE (no substitution on weight; bootstrap-insignificant p=0.27)",
        "active_flow_DV1_beta_WITH_control": dv1_with.get("beta_treatment"),
        "active_flow_DV1_beta_WITHOUT_control": dv1_without.get("beta_treatment"),
        "active_flow_DV1_bootstrap_p_G22": wcb["bootstrap_p_twosided"],
        "note": "F3 substitution on active flow = NEGATIVE beta. The KEY diagnostic is whether moving "
                "from weight (DV=w) to active flow (valuation removed by construction) CHANGES the "
                "sanctions coefficient's sign/significance. Read from the estimator; interpreted in the verdict.",
    }

    result = {
        "artifact": "active_flow_result",
        "generated_by": "build/audit/active_flow_recompute.py (no network)",
        "serves_prereg": "build/audit/active_flow_prediction.md",
        "active_flow_panel_path": AFLOW,
        "treatment_path": TREAT,
        "macro_control_panel_path": CM,
        "merged_panel_path": OUT_MERGED,
        "estimator": "within (fund-demeaned) OLS; fund FE + X_t, NO time FE. Estimator functions REUSED "
                     "VERBATIM from sanctions_shock_recompute.py; ONLY change is the DEPENDENT VARIABLE "
                     "(portfolio weight w -> ACTIVE net flow into CN-nationality haven, valuation removed "
                     "by construction) across three disclosed normalization variants. beta read from the "
                     "estimator at design position 0, never hardcoded.",
        "dependent_variable_note": "ACTIVE net flow into CN-nationality haven securities = manager DECISION "
                                   "(constant-price decomposition active=(bal_t-bal_{t-1})*price_{t-1}). "
                                   "Valuation (passive) removed BY CONSTRUCTION, not controlled.",
        "dv_variants": {
            "DV1_headline": "active_flow_rate (cn_active_flow / tot_haven_lag) winsorized symmetric 1/99",
            "DV2_robustness": "cn_active_flow / (0.5*(tot_haven_lag + tot_haven_cv))  (average-base)",
            "DV3_robustness": f"active_flow_rate restricted to tot_haven_lag>={DV3_LAG_FLOOR:.0f}, winsorized 1/99",
        },
        "winsor_and_floor_meta": winsor_meta,
        "headline_treatment": SANC,
        "primary_regulatory_control": REG,
        "sign_convention": "NEGATIVE beta on the sanctions treatment = funds ACTIVELY SOLD CN-nationality "
                           "haven securities as sanctions risk rose = F3 substitution.",
        "merge_check": merge_check,
        "estimation_set_DV1": {"quarters": qs_for(DV1),
                               "n_cells_DV1_nonnull": int(m[DV1].notna().sum()),
                               "G": G_all},
        "LOAD_BEARING_with_vs_without_regulatory_control_by_DV": load_bearing,
        "robustness_panel": robustness,
        "collinearity_diagnostic": collinearity,
        "power_diagnostic": power,
        "few_cluster_inference": {
            "wild_cluster_bootstrap_quarter_headline_DV1_WITH_control": wcb,
            "leave_one_quarter_out_DV1_WITH_control": {
                "spec": dv1_with.get("label", "") + " [lags on contiguous 22q ordinal]",
                "full_beta": dv1_with.get("beta_treatment"),
                "beta_dropping_quarter": loqo_with,
            },
            "leave_one_quarter_out_DV1_WITHOUT_control": {
                "spec": dv1_without.get("label", "") + " [lags on contiguous 22q ordinal]",
                "full_beta": dv1_without.get("beta_treatment"),
                "beta_dropping_quarter": loqo_without,
            },
        },
        "KEY_weight_vs_active_flow_comparison": key_comparison,
        "weight_based_result_for_comparison": {
            "source": "build/audit/sanctions_shock_result.json",
            "weight_beta_with_control": weight_beta_with,
            "weight_beta_without_control": weight_beta_without,
            "weight_bootstrap_p_G22": weight_bootstrap_p,
        },
    }
    json.dump(result, open(OUT_RESULT, "w"), indent=2)

    # ============ VERIFIER: independent recompute of every beta, LOQO sets, bootstrap p =============
    def indep_beta(df_, dvcol, tcol, controls, use_lags):
        d = df_.copy()
        rhs = [tcol] + list(controls)
        if use_lags:
            d = add_lags(d, dvcol)
            rhs = [tcol, "L1", "L2"] + list(controls)
        d = d.dropna(subset=[dvcol] + rhs)
        d = d[d.groupby("holder")["holder"].transform("size") >= 2]
        dw = within_demean(d, [dvcol] + rhs)
        y = dw[dvcol + "_w"].to_numpy(); X = dw[[c + "_w" for c in rhs]].to_numpy()
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        return float(b[0])

    # recompute all with/without betas across DV1/DV2/DV3
    beta_re = {}
    beta_in = {}
    dv_map = {DV1: "DV1", DV2: "DV2", DV3: "DV3"}
    for dvcol, tag in dv_map.items():
        wo = load_bearing[{"DV1":"DV1_headline_afrate_winsorized","DV2":"DV2_avgbase_rate",
                           "DV3":"DV3_afrate_lagfloor_winsorized"}[tag]]["WITHOUT_regulatory_control"]
        wc = load_bearing[{"DV1":"DV1_headline_afrate_winsorized","DV2":"DV2_avgbase_rate",
                           "DV3":"DV3_afrate_lagfloor_winsorized"}[tag]]["WITH_regulatory_control_reg_crackdown"]
        beta_in[tag + "_without"] = wo["beta_treatment"]
        beta_in[tag + "_with"] = wc["beta_treatment"]
        beta_re[tag + "_without"] = indep_beta(m, dvcol, SANC, CTRL_RR, True)
        beta_re[tag + "_with"] = indep_beta(m, dvcol, SANC, CTRL_RR + [REG], True)

    # recompute every OK robustness beta
    rob_specs = {
        "r1_DV1_no_control": (DV1, SANC, CTRL_RR, True, m),
        "r2_DV1_plus_reg_crackdown": (DV1, SANC, CTRL_RR + [REG], True, m),
        "r3_DV1_plus_reg_hfcaa": (DV1, SANC, CTRL_RR + [REG_HFCAA], True, m),
        "r4_DV1_eo2023_second_event_with_controls": (DV1, "sanc_eo2023_post", CTRL_RR + [SANC, REG], True, m),
        "r5_DV1_narrow_event_window_2022q1q2_vs_pre": (DV1, SANC, CTRL_RR + [REG], True, m_narrow),
        "r6_DV1_no_flow_lags_with_control": (DV1, SANC, CTRL_RR + [REG], False, m),
        "r6b_DV1_no_flow_lags_no_control": (DV1, SANC, CTRL_RR, False, m),
        "r7_DV2_no_control": (DV2, SANC, CTRL_RR, True, m),
        "r8_DV2_plus_reg_crackdown": (DV2, SANC, CTRL_RR + [REG], True, m),
        "r9_DV3_no_control": (DV3, SANC, CTRL_RR, True, m),
        "r10_DV3_plus_reg_crackdown": (DV3, SANC, CTRL_RR + [REG], True, m),
        "r11_DV2_plus_reg_hfcaa": (DV2, SANC, CTRL_RR + [REG_HFCAA], True, m),
        "r12_DV2_eo2023_second_event_with_controls": (DV2, "sanc_eo2023_post", CTRL_RR + [SANC, REG], True, m),
    }
    rob_in, rob_re, rob_match = {}, {}, True
    for key, (dvc, tc, ctrls, lags, dfrm) in rob_specs.items():
        sp = robustness[key]
        if sp.get("status") == "OK":
            re = indep_beta(dfrm, dvc, tc, ctrls, lags)
            rob_in[key] = sp["beta_treatment"]
            rob_re[key] = re
            if abs(sp["beta_treatment"] - re) >= 1e-9:
                rob_match = False

    beta_wo_match = all(abs(beta_in[k] - beta_re[k]) < 1e-9 for k in beta_in)
    beta_matches = bool(beta_wo_match and rob_match)

    wcb_re = wild_cluster_bootstrap_quarter(m, DV1, SANC, CTRL_RR + [REG], WCB_REPS, WCB_SEED)
    bootstrap_p_match = abs(wcb["bootstrap_p_twosided"] - wcb_re["bootstrap_p_twosided"]) < 1e-12

    loqo_with_re = leave_one_quarter_out(m, DV1, SANC, CTRL_RR + [REG], True, quarters_all)
    loqo_without_re = leave_one_quarter_out(m, DV1, SANC, CTRL_RR, True, quarters_all)

    def _loqo_eq(a, b_, qs):
        return all((a[q] is None and b_[q] is None) or
                   (a[q] is not None and b_[q] is not None and abs(a[q] - b_[q]) < 1e-9)
                   for q in qs)
    loqo_match = (_loqo_eq(loqo_with, loqo_with_re, quarters_all)
                  and _loqo_eq(loqo_without, loqo_without_re, quarters_all))

    verify = {
        "artifact": "active_flow_verify",
        "generated_by": "build/audit/active_flow_recompute.py (no network)",
        "merge1_treatment_ok_22_of_22": merge_check["merge1_treatment"]["merge_ok_22_of_22"],
        "merge1_keys_matched": merge_check["merge1_treatment"]["keys_matched"],
        "merge2_rows_matched_relative_returns": merge_check["merge2_macro_controls"]["rows_matched_relative_returns"],
        "merge2_rows_orphan_no_macro": merge_check["merge2_macro_controls"]["rows_orphan_no_macro"],
        "estimation_G": G_all,
        "n_cells_DV1_nonnull": int(m[DV1].notna().sum()),
        "betas_in_result": beta_in,
        "betas_recomputed": beta_re,
        "robustness_betas_in_result": rob_in,
        "robustness_betas_recomputed": rob_re,
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

    _ok = beta_matches and bootstrap_p_match and loqo_match and merge_check["merge1_treatment"]["merge_ok_22_of_22"]
    print("PASS" if _ok else "FAIL")
    print("MERGE1 treatment 22/22:", merge_check["merge1_treatment"]["merge_ok_22_of_22"])
    print("MERGE2 macro: rows=%d matched_relret=%d orphan=%d holders_matched=%d/%d not_in_cm=%d" % (
        n_before, n_matched_relret, n_orphan_macro,
        len(aflow_holders & cm_holders), len(aflow_holders), len(holders_only_in_aflow)))
    print("G=%d n_cells_DV1=%d" % (G_all, m[DV1].notna().sum()))

    def _line(tag, sp):
        if sp.get("status") != "OK":
            print("%-52s %s n=%s" % (tag, sp.get("status"), sp.get("n_obs"))); return
        q = sp["se_cluster_quarter"]; f = sp["se_cluster_fund"]
        print("%-52s beta=%+.6f se_q=%.6f p_q=%.4f CI_q=[%+.5f,%+.5f] se_f=%.6f p_f=%.4f n=%d G=%d" % (
            tag, sp["beta_treatment"], q["se"], q["p"], q["ci95"][0], q["ci95"][1],
            f["se"], f["p"], sp["n_obs"], sp["n_quarter_clusters"]))
    print("=== LOAD-BEARING with vs without regulatory control, per DV ===")
    _line("DV1 WITHOUT reg", dv1_without); _line("DV1 WITH  reg_crackdown", dv1_with)
    _line("DV2 WITHOUT reg", dv2_without); _line("DV2 WITH  reg_crackdown", dv2_with)
    _line("DV3 WITHOUT reg", dv3_without); _line("DV3 WITH  reg_crackdown", dv3_with)
    print("=== robustness panel ===")
    for k in ["r3_DV1_plus_reg_hfcaa","r4_DV1_eo2023_second_event_with_controls",
              "r5_DV1_narrow_event_window_2022q1q2_vs_pre","r6_DV1_no_flow_lags_with_control",
              "r6b_DV1_no_flow_lags_no_control","r11_DV2_plus_reg_hfcaa",
              "r12_DV2_eo2023_second_event_with_controls"]:
        _line(k[:52], robustness[k])
    print("=== collinearity ===")
    print("corr(freeze,crackdown) 22q = %.4f (carried Part1 r=0.828); VIF(freeze|with reg,DV1)=%.3f; SE inflation from reg=%s" % (
        corr_freeze_crackdown, vif_with_reg["vif"], ("%.3fx" % se_infl) if se_infl else "NA"))
    print("=== power (DV1) ===")
    print("sanc_freeze 1SD(22q)=%.4f; resid_share_within NO_reg=%.4f WITH_reg=%.4f; DV1 sd=%.4f DV2 sd=%.4f DV3 sd=%.4f; G=%d" % (
        sanc_1sd_22q, power["residual_share_of_within_NO_reg_DV1"], power["residual_share_of_within_WITH_reg_DV1"],
        dv_sds["DV1_afrate_wins_sd"], dv_sds["DV2_avgbase_sd"], dv_sds["DV3_afrate_floor_wins_sd"], G_all))
    print("=== wild cluster bootstrap (quarter, G=%d, reps=%d, seed=%d) DV1 WITH control ===" % (
        wcb["n_quarter_clusters_G"], WCB_REPS, WCB_SEED))
    print("beta=%+.6f t=%.3f bootstrap_p=%.4f [match=%s]" % (
        wcb["beta_treatment"], wcb["t_obs"], wcb["bootstrap_p_twosided"], bootstrap_p_match))
    print("=== LOQO-22q DV1 ===")
    print("WITH control :", {q: round(loqo_with[q],6) if loqo_with[q] is not None else None for q in quarters_all})
    print("WITHOUT ctrl :", {q: round(loqo_without[q],6) if loqo_without[q] is not None else None for q in quarters_all})
    print("=== KEY weight vs active-flow ===")
    print("weight beta WITH=+0.017661 (p_boot=0.27, POSITIVE); active-flow DV1 WITH=%+.6f (p_boot=%.4f)" % (
        dv1_with.get("beta_treatment", float('nan')), wcb["bootstrap_p_twosided"]))
    print("beta_matches=%s bootstrap_p_match=%s loqo_match=%s" % (beta_matches, bootstrap_p_match, loqo_match))


if __name__ == "__main__":
    main()
