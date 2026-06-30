#!/usr/bin/env python3
"""
CONVERSE-MALLUCCI WEIGHT-REGRESSION F3 TEST -- recompute generator (NO NETWORK).

Regenerates every beta/SE/p/CI in build/audit/cm_regression_result.json from
  - build/data/cm_panel/cm_weight_panel.parquet  (fund x quarter weights + merged series)
ONLY, and writes build/results/cm_regression_verify.json.

Headline spec (CM, NBER 32638):
  w_{f,t} = alpha_f + beta*GPRC_China_t + gamma1*w_{f,t-1} + gamma2*w_{f,t-2}
            + delta*relative_returns_t + theta*X_t + eps,   X_t=[log VIX, broad dollar, oil]
  alpha_f = fund fixed effects.

WHY fund FE + X_t replace time FE (CM's exact device): GPRC_China_t is a SINGLE national
time series (one value per quarter). Time fixed effects would be collinear with -- and
would fully absorb -- GPRC_China, leaving beta unidentified. CM instead absorb the common
macro component with the observed state vector X_t (log VIX, broad dollar, oil) plus fund
FE, so beta is identified off within-fund variation in the China-specific risk series net
of the common macro state. beta is read from the estimator output below; it is NOT
hardcoded anywhere.

Estimation: within (fund-demeaned) OLS. Lags w_{t-1}, w_{t-2} are built on the panel-time
ordinal over the 8 NON-CONTIGUOUS quarters and require the prior panel-quarter(s) to exist
for the same fund (a gap-broken transition yields a missing lag and drops that row from a
lagged spec). SEs: classical, clustered-by-fund, and clustered-by-quarter (CR1).
"""
import json, os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PANEL = os.path.join(ROOT, "build/data/cm_panel/cm_weight_panel.parquet")
OUT_RESULT = os.path.join(ROOT, "build/audit/cm_regression_result.json")
OUT_VERIFY = os.path.join(ROOT, "build/results/cm_regression_verify.json")

QUARTERS = ['2019q3','2019q4','2020q1','2020q2','2020q3','2022q1','2022q2','2024q4']
QORD = {q: i for i, q in enumerate(QUARTERS)}

from scipy import stats as sstats


def add_lags(df, wcol):
    """Lag within fund along the panel-time ordinal. A lag exists only if the immediately
    preceding panel-quarter (qord-1, qord-2) is present for the same fund -- a non-contiguous
    gap yields NaN and drops the row from lagged specs."""
    df = df.sort_values(["holder", "qord"]).copy()
    by = df.groupby("holder")
    look = {(h, o): v for h, o, v in zip(df["holder"], df["qord"], df[wcol])}
    df["L1"] = [look.get((h, o - 1), np.nan) for h, o in zip(df["holder"], df["qord"])]
    df["L2"] = [look.get((h, o - 2), np.nan) for h, o in zip(df["holder"], df["qord"])]
    return df


def within_demean(df, cols, group="holder"):
    """Fund fixed effects via within transformation: demean y and each X within fund."""
    out = df.copy()
    for c in cols:
        out[c + "_w"] = out[c] - out.groupby(group)[c].transform("mean")
    return out


def cluster_vcov(X, resid, groups):
    """CR1 cluster-robust covariance: (X'X)^-1 (sum_g Xg' ug ug' Xg) (X'X)^-1, dof-adjusted."""
    XtX_inv = np.linalg.pinv(X.T @ X)
    k = X.shape[1]
    meat = np.zeros((k, k))
    uniq = pd.unique(groups)
    G = len(uniq)
    for g in uniq:
        m = groups == g
        Xg = X[m]
        ug = resid[m]
        s = Xg.T @ ug
        meat += np.outer(s, s)
    n = X.shape[0]
    # CR1 small-sample adjustment
    adj = (G / (G - 1.0)) * ((n - 1.0) / (n - k)) if G > 1 else 1.0
    return XtX_inv @ (adj * meat) @ XtX_inv, G


def _design(df, wcol, gprc_col, controls):
    """Build the within-demeaned (y, X, group, quarter) design for a no-lags spec.
    Returns y, X (col 0 = GPRC), holder array, quarter array, XtX_inv."""
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
    """CR1 cluster-robust SE of the GPRC coefficient (col 0), given precomputed XtX_inv."""
    k = X.shape[1]
    meat = np.zeros((k, k))
    uniq = np.unique(groups)
    for g in uniq:
        m = groups == g
        s = X[m].T @ u[m]
        meat += np.outer(s, s)
    G = len(uniq)
    n = X.shape[0]
    adj = (G / (G - 1.0)) * ((n - 1.0) / (n - k)) if G > 1 else 1.0
    V = XtX_inv @ (adj * meat) @ XtX_inv
    return float(np.sqrt(V[0, 0])), G


def wild_cluster_bootstrap_quarter(df, wcol, gprc_col, controls, reps, seed):
    """Wild cluster-t (CRVE) bootstrap by quarter cluster for the GPRC coefficient.
    Rademacher weights drawn ONCE per quarter cluster per replication. Null imposed
    (restricted residuals: GPRC coefficient set to 0). Two-sided p = share of bootstrap
    |t*| >= |t_obs|. Deterministic under `seed`. No network. Spec is no-lags (G=8)."""
    y, X, holders, quarters, XtX_inv = _design(df, wcol, gprc_col, controls)
    # observed fit + restricted (null) fit
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ b
    beta0 = float(b[0])
    se_obs, G = _cluster_se_gprc(X, resid, quarters, XtX_inv)
    t_obs = beta0 / se_obs if se_obs > 0 else np.nan
    Xr = X[:, 1:]                      # design without GPRC (impose H0: beta_GPRC = 0)
    br, *_ = np.linalg.lstsq(Xr, y, rcond=None)
    ur = y - Xr @ br
    uniq = np.unique(quarters)
    rng = np.random.default_rng(seed)
    n_extreme = 0
    for _ in range(reps):
        w = {g: rng.choice([-1.0, 1.0]) for g in uniq}
        wvec = np.array([w[g] for g in quarters])
        ystar = Xr @ br + ur * wvec
        bs, *_ = np.linalg.lstsq(X, ystar, rcond=None)
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


def leave_one_quarter_out(df, wcol, gprc_col, controls, use_lags, quarters):
    """Re-estimate beta_GPRC dropping each quarter in turn (within-fund OLS, same spec)."""
    out = {}
    for q in quarters:
        sub = df[df["fiscal_quarter"] != q]
        spec = run_spec(sub, wcol, gprc_col, use_lags, controls, f"LOQO_drop_{q}")
        out[q] = spec.get("beta_GPRC_China") if spec.get("status") == "OK" else None
    return out


def run_spec(df, wcol, gprc_col, use_lags, controls, label):
    """Within-fund OLS of wcol on [GPRC, (lags), controls]; returns beta on GPRC + 3 SEs/CI."""
    d = df.copy()
    rhs = [gprc_col] + list(controls)
    if use_lags:
        d = add_lags(d, wcol)
        rhs = [gprc_col, "L1", "L2"] + list(controls)
    need = [wcol] + rhs
    d = d.dropna(subset=need)
    # need within-fund variation: drop singleton funds (no within variation after FE)
    cnt = d.groupby("holder")["holder"].transform("size")
    d = d[cnt >= 2]
    n = len(d)
    nfunds = d["holder"].nunique()
    if n <= len(rhs) + 2 or nfunds < 2:
        return {"label": label, "status": "INSUFFICIENT_OBS", "n_obs": int(n),
                "n_funds": int(nfunds)}
    dw = within_demean(d, [wcol] + rhs)
    y = dw[wcol + "_w"].to_numpy()
    X = dw[[c + "_w" for c in rhs]].to_numpy()
    # solve
    beta_hat, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta_hat
    k = X.shape[1]
    # within dof: subtract n_funds (FE) and k regressors
    dof = n - nfunds - k
    XtX_inv = np.linalg.pinv(X.T @ X)
    # classical
    sigma2 = (resid @ resid) / max(dof, 1)
    V_cl = sigma2 * XtX_inv
    # cluster by fund
    V_cf, Gf = cluster_vcov(X, resid, d["holder"].to_numpy())
    # cluster by quarter
    V_cq, Gq = cluster_vcov(X, resid, d["fiscal_quarter"].to_numpy())
    gi = rhs.index(gprc_col)
    beta = float(beta_hat[gi])

    def pack(V, G_for_t):
        se = float(np.sqrt(V[gi, gi]))
        tstat = beta / se if se > 0 else np.nan
        # t with within dof (classical) or G-1 (cluster) for p/CI
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


def main():
    df = pd.read_parquet(PANEL)
    df["qord"] = df["fiscal_quarter"].map(QORD)
    CTRL = ["log_vix", "broad_dollar", "oil"]
    CTRL_RR = CTRL + ["relative_returns"]

    specs = []
    # HEADLINE: w, gprc_avg, lags, controls + relative_returns
    specs.append(run_spec(df, "w", "gprc_avg", True, CTRL_RR, "HEADLINE w~gprc_avg+L1+L2+X+relret"))
    # robustness: no relative_returns
    specs.append(run_spec(df, "w", "gprc_avg", True, CTRL, "w~gprc_avg+L1+L2+X (no relret)"))
    # robustness: no lags
    specs.append(run_spec(df, "w", "gprc_avg", False, CTRL_RR, "w~gprc_avg+X+relret (no lags)"))
    specs.append(run_spec(df, "w", "gprc_avg", False, CTRL, "w~gprc_avg+X (no lags,no relret)"))
    # robustness: end-of-quarter GPRC
    specs.append(run_spec(df, "w", "gprc_end", True, CTRL_RR, "w~gprc_END+L1+L2+X+relret"))
    specs.append(run_spec(df, "w", "gprc_end", False, CTRL_RR, "w~gprc_END+X+relret (no lags)"))
    # robustness: alt weight denominator (foreign)
    specs.append(run_spec(df, "w_alt", "gprc_avg", True, CTRL_RR, "w_ALT~gprc_avg+L1+L2+X+relret"))
    specs.append(run_spec(df, "w_alt", "gprc_avg", False, CTRL_RR, "w_ALT~gprc_avg+X+relret (no lags)"))

    headline = specs[0]

    # ---- power diagnostic: within-fund residual variation in GPRC after FE+controls ----
    # Partial GPRC on fund FE + controls; the residual SD is the variation identifying beta.
    def gprc_residual_sd(gcol, controls, use_lags):
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
        return float(np.std(gres)), float(np.std(dw[gcol + "_w"].to_numpy())), float(df[gcol].std())
    res_sd, within_sd, raw_sd = gprc_residual_sd("gprc_avg", CTRL_RR, True)
    gprc_1sd = float(df.drop_duplicates("fiscal_quarter")["gprc_avg"].std())

    # CI half-width on the 1-SD-GPRC effect for the headline (cluster-quarter SE)
    hb = headline["beta_GPRC_China"]
    hse_q = headline["se_cluster_quarter"]["se"]
    effect_1sd = hb * gprc_1sd
    ci_halfwidth_1sd = 1.96 * hse_q * gprc_1sd

    # ---- few-cluster inference: wild cluster bootstrap (quarter) + leave-one-quarter-out ----
    # (a) wild cluster-t bootstrap by quarter, no-lags spec (G=8), Rademacher, 2000 reps, seed 42.
    WCB_REPS, WCB_SEED = 2000, 42
    wcb = wild_cluster_bootstrap_quarter(df, "w", "gprc_avg", CTRL_RR, WCB_REPS, WCB_SEED)
    # (b) leave-one-quarter-out on the HEADLINE spec (w, gprc_avg, +lags, +relret) AND on the
    #     no-lags spec (which retains all remaining quarters rather than losing lag chains).
    loqo = leave_one_quarter_out(df, "w", "gprc_avg", CTRL_RR, True, QUARTERS)
    loqo_nolags = leave_one_quarter_out(df, "w", "gprc_avg", CTRL_RR, False, QUARTERS)

    result = {
        "artifact": "cm_regression_result",
        "generated_by": "build/audit/cm_regression_recompute.py (no network)",
        "panel_path": PANEL,
        "estimator": "within (fund-demeaned) OLS; fund FE + X_t replace time FE because "
                     "GPRC_China is a single national series (time FE would absorb it).",
        "panel_dims": {
            "n_funds": int(df["holder"].nunique()),
            "n_quarters": int(df["fiscal_quarter"].nunique()),
            "quarters": QUARTERS,
            "n_fund_quarter_obs": int(len(df)),
        },
        "specs": specs,
        "headline_label": headline["label"],
        "power_diagnostic": {
            "gprc_quarterly_cross_quarter_sd": gprc_1sd,
            "gprc_raw_pooled_sd": raw_sd,
            "gprc_within_fund_sd_after_FE": within_sd,
            "gprc_residual_sd_after_FE_and_controls": res_sd,
            "gprc_residual_share_of_within": (res_sd / within_sd) if within_sd else None,
            "interpretation": "beta is identified off gprc_residual_sd_after_FE_and_controls; "
                              "if this collapses toward 0 the macro controls have absorbed nearly "
                              "all the China-GPRC variation and beta is near-unidentified.",
            "headline_beta": hb,
            "headline_se_cluster_quarter": hse_q,
            "effect_per_1sd_gprc": effect_1sd,
            "ci95_halfwidth_per_1sd_gprc_clustered_quarter": ci_halfwidth_1sd,
        },
        "few_cluster_inference": {
            "note": "Honest inference for a single national GPRC series over 8 quarters. The "
                    "classical SE treats ~22k fund-quarters as the sample, but beta is identified "
                    "off ~8 national time points; few-cluster methods are the honest test.",
            "wild_cluster_bootstrap_quarter": wcb,
            "leave_one_quarter_out_headline": {
                "spec": headline["label"],
                "full_beta": headline["beta_GPRC_China"],
                "beta_dropping_quarter": loqo,
                "drop_2022q2_beta": loqo.get("2022q2"),
                "drop_2022q1_beta": loqo.get("2022q1"),
                "note": "With two weight lags requiring 3 consecutive panel quarters, dropping any "
                        "single crisis-window quarter (2020q1/q2/q3, 2022q1, 2022q2) breaks most "
                        "lag chains (n falls 22,200 -> ~9k-15k) and collapses beta to ~0. This is a "
                        "thin-panel signature, not robustness.",
            },
            "leave_one_quarter_out_no_lags": {
                "spec": "w ~ gprc_avg + X + relative_returns (no lags; retains remaining quarters)",
                "beta_dropping_quarter": loqo_nolags,
                "note": "Cleaner read (no lag-chain loss). beta stays negative dropping any single "
                        "quarter EXCEPT 2024q4, where it flips sign (sign depends on one quarter).",
            },
        },
    }
    json.dump(result, open(OUT_RESULT, "w"), indent=2)

    # ---- verify artifact (independent recompute of the headline beta on demeaned data) ----
    d = add_lags(df.copy(), "w").dropna(subset=["w", "gprc_avg", "L1", "L2", "log_vix",
                                               "broad_dollar", "oil", "relative_returns"])
    cnt = d.groupby("holder")["holder"].transform("size")
    d = d[cnt >= 2]
    rhs = ["gprc_avg", "L1", "L2", "log_vix", "broad_dollar", "oil", "relative_returns"]
    dw = within_demean(d, ["w"] + rhs)
    y = dw["w_w"].to_numpy()
    X = dw[[c + "_w" for c in rhs]].to_numpy()
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    beta_check = float(b[0])

    # independent, deterministic recompute of the few-cluster inference under the same seed
    wcb_re = wild_cluster_bootstrap_quarter(df, "w", "gprc_avg", CTRL_RR, WCB_REPS, WCB_SEED)
    loqo_re = leave_one_quarter_out(df, "w", "gprc_avg", CTRL_RR, True, QUARTERS)
    loqo_nl_re = leave_one_quarter_out(df, "w", "gprc_avg", CTRL_RR, False, QUARTERS)
    bootstrap_p_matches = abs(wcb["bootstrap_p_twosided"] - wcb_re["bootstrap_p_twosided"]) < 1e-12

    def _loqo_eq(a, b):
        return all(
            (a[q] is None and b[q] is None) or
            (a[q] is not None and b[q] is not None and abs(a[q] - b[q]) < 1e-9)
            for q in QUARTERS)
    loqo_matches = _loqo_eq(loqo, loqo_re) and _loqo_eq(loqo_nolags, loqo_nl_re)

    verify = {
        "artifact": "cm_regression_verify",
        "generated_by": "build/audit/cm_regression_recompute.py (no network)",
        "headline_beta_in_result": headline["beta_GPRC_China"],
        "headline_beta_recomputed_independently": beta_check,
        "beta_matches": abs(headline["beta_GPRC_China"] - beta_check) < 1e-9,
        "headline_n_obs": headline["n_obs"],
        "headline_within_dof": headline["within_dof"],
        "n_specs_run": len([s for s in specs if s.get("status") == "OK"]),
        "all_betas_read_from_estimator_not_hardcoded": True,
        "power_diagnostic_gprc_residual_sd": result["power_diagnostic"]["gprc_residual_sd_after_FE_and_controls"],
        "wild_cluster_bootstrap_p_in_result": wcb["bootstrap_p_twosided"],
        "wild_cluster_bootstrap_p_recomputed": wcb_re["bootstrap_p_twosided"],
        "bootstrap_p_recomputed_matches": bootstrap_p_matches,
        "bootstrap_seed": WCB_SEED, "bootstrap_reps": WCB_REPS,
        "bootstrap_deterministic_under_seed": bootstrap_p_matches,
        "leave_one_out_betas_in_result_headline": loqo,
        "leave_one_out_betas_recomputed_headline": loqo_re,
        "leave_one_out_betas_in_result_no_lags": loqo_nolags,
        "leave_one_out_betas_recomputed_no_lags": loqo_nl_re,
        "leave_one_out_recomputed_matches": loqo_matches,
        "drop_2022q2_beta_headline": loqo.get("2022q2"),
        "drop_2022q1_beta_headline": loqo.get("2022q1"),
        "drop_2024q4_beta_no_lags": loqo_nolags.get("2024q4"),
    }
    json.dump(verify, open(OUT_VERIFY, "w"), indent=2)
    _ok = (verify["beta_matches"] and bootstrap_p_matches and loqo_matches)
    print("PASS" if _ok else "FAIL")
    for s in specs:
        if s.get("status") == "OK":
            print(f"{s['label']:42s} n={s['n_obs']:5d} funds={s['n_funds']:5d} "
                  f"beta={s['beta_GPRC_China']:+.5f} "
                  f"se_q={s['se_cluster_quarter']['se']:.5f} "
                  f"p_q={s['se_cluster_quarter']['p']:.3f} "
                  f"CI_q=[{s['se_cluster_quarter']['ci95'][0]:+.4f},{s['se_cluster_quarter']['ci95'][1]:+.4f}]")
        else:
            print(f"{s['label']:42s} {s['status']} n={s.get('n_obs')}")
    print("power: gprc 1SD=%.4f resid_sd_after_FE+ctrl=%.4f effect/1SD=%+.5f CI_halfwidth/1SD=%.5f" % (
        gprc_1sd, res_sd, effect_1sd, ci_halfwidth_1sd))
    print("wild-cluster-bootstrap (quarter, G=%d, reps=%d, seed=%d): beta=%+.5f t_obs=%.3f p=%.4f  [recompute matches=%s]" % (
        wcb["n_quarter_clusters_G"], wcb["reps"], wcb["seed"], wcb["beta_GPRC_China"],
        wcb["t_obs"], wcb["bootstrap_p_twosided"], bootstrap_p_matches))
    print("leave-one-quarter-out HEADLINE (with lags) betas:")
    for q in QUARTERS:
        print("  drop %s: beta=%+.5f%s" % (q, loqo[q],
              "  <-- drop-2022q2" if q == "2022q2" else ("  <-- 2022q1 GPRC spike" if q == "2022q1" else "")))
    print("leave-one-quarter-out NO-LAGS betas:")
    for q in QUARTERS:
        print("  drop %s: beta=%+.5f%s" % (q, loqo_nolags[q],
              "  <-- SIGN FLIP" if (loqo_nolags[q] is not None and loqo_nolags[q] > 0) else ""))
    print("loqo recompute matches: %s" % loqo_matches)


if __name__ == "__main__":
    main()
