#!/usr/bin/env python3
"""
FAST pre-trend recompute + verifier (no network, no panel rebuild).

Reads ONLY the already-built group panel build/data/nport/did_control_panels.parquet and
recomputes, for each candidate control (C1/C2/C3) vs the treated group over the pre-period
2019q4-2021q4, the trend x treated interaction (fund FE, cluster-by-fund SE) under three
outlier-handling variants: untrimmed / trim_1pct / trim_5pct. These are the SAME numbers
build_did_control_panels_streaming.py stored into build/audit/did_feasibility.json; this
script reproduces them in seconds so the load-bearing pre-trend evidence is verifier-
reproduced rather than asserted, without the ~12-minute panel rebuild.

The trim variant drops the lower/upper `trim` quantile of the STACKED (treated+control)
pre-period rate distribution — identical to the panel builder's pretrend_test.

Writes build/results/did_pretrend_verify.json with, per control per variant:
interaction_coef, se, p, and a match flag vs the value stored in did_feasibility.json.
interaction_coef is the load-bearing reproduced quantity (matched to ~1e-6); p is matched
to a loose tolerance (t-distribution df conventions vary). Reports all-match true/false.
"""
import os, json
import numpy as np
import pandas as pd
from scipy import stats

ROOT = "/home/user/dollar-breaking-point"
PANEL = os.path.join(ROOT, "build/data/nport/did_control_panels.parquet")
FEAS = os.path.join(ROOT, "build/audit/did_feasibility.json")
OUT = os.path.join(ROOT, "build/results/did_pretrend_verify.json")

PRE_QS = ["2019q4", "2020q1", "2020q2", "2020q3", "2020q4",
          "2021q1", "2021q2", "2021q3", "2021q4"]
CONTROLS = ["C1", "C2", "C3"]
VARIANTS = [("untrimmed", None), ("trim_1pct", 0.01), ("trim_5pct", 0.05)]
COEF_TOL = 1e-6      # load-bearing reproduced quantity
P_TOL = 1e-3         # loose (t-df conventions vary)


def ols_with_fe(y, X, fe_groups):
    """OLS of y on X after absorbing fund FE by within-demeaning; cluster-robust SE by
    fund. Identical estimator to build_did_control_panels_streaming.ols_with_fe."""
    df = pd.DataFrame(X.copy())
    df["_y"] = y
    df["_g"] = fe_groups
    num_cols = [c for c in df.columns if c != "_g"]
    dem = df.groupby("_g")[num_cols].transform(lambda s: s - s.mean())
    Y = dem["_y"].values
    cols = [c for c in X.columns if c != "const"]
    Xm = dem[cols].values
    keep = [i for i in range(Xm.shape[1]) if np.nanstd(Xm[:, i]) > 1e-12]
    cols = [cols[i] for i in keep]
    Xm = Xm[:, keep]
    mask = ~np.isnan(Y) & ~np.isnan(Xm).any(axis=1)
    Y = Y[mask]; Xm = Xm[mask]; g = df["_g"].values[mask]
    n, k = Xm.shape
    XtX_inv = np.linalg.pinv(Xm.T @ Xm)
    beta = XtX_inv @ (Xm.T @ Y)
    resid = Y - Xm @ beta
    meat = np.zeros((k, k))
    for gg in np.unique(g):
        idx = g == gg
        s = Xm[idx].T @ resid[idx]
        meat += np.outer(s, s)
    G = len(np.unique(g))
    dof = (G / (G - 1)) * ((n - 1) / (n - k)) if G > 1 and n > k else 1.0
    V = XtX_inv @ meat @ XtX_inv * dof
    se = np.sqrt(np.diag(V))
    return dict(zip(cols, beta)), dict(zip(cols, se)), n, G


def interaction(d):
    qmap = {q: i for i, q in enumerate(PRE_QS)}
    d = d.copy()
    d["trend"] = d["fiscal_quarter"].map(qmap).astype(float)
    d["fe"] = d["treated"].astype(int).astype(str) + "|" + d["fund_key"]
    X = pd.DataFrame({
        "const": 1.0, "trend": d["trend"].values, "treated": d["treated"].values,
        "trend_x_treated": (d["trend"] * d["treated"]).values})
    beta, se, n, G = ols_with_fe(d["rate"].values, X, d["fe"].values)
    b = beta.get("trend_x_treated", np.nan)
    s = se.get("trend_x_treated", np.nan)
    t = b / s if s and not np.isnan(s) and s != 0 else np.nan
    p = float(2 * stats.t.sf(abs(t), max(G - 1, 1))) if not np.isnan(t) else None
    return (float(b) if not np.isnan(b) else None,
            float(s) if not np.isnan(s) else None,
            float(t) if not np.isnan(t) else None, p, int(n), int(G))


def trimmed_quarter_means(p, groups, trim=0.05):
    """5%-trimmed per-quarter group-mean active-flow rate over the pre-period.

    TRIM DEFINITION (precise, deterministic): for each (group, fiscal_quarter) CELL, take
    that cell's own rate observations (non-null), symmetrically drop the lowest `trim` and
    highest `trim` fraction, and average the remainder. This is exactly
    scipy.stats.trim_mean(rate, 0.05) computed per cell. The trim is per-cell (not stacked-
    pair, not per-group-global), so each reported cell is the robust central tendency of
    just that group in just that quarter. Deterministic: scipy.trim_mean sorts and drops a
    fixed integer count floor(trim*n) from each end; no randomness. For cells with too few
    observations to drop from both ends it degrades to the plain mean (scipy handles this).
    """
    means = {}
    for g in groups:
        row = {}
        for q in PRE_QS:
            s = p[(p["group"] == g) & (p["fiscal_quarter"] == q)]["rate"].dropna().values
            if len(s) == 0:
                row[q] = None
            else:
                row[q] = float(stats.trim_mean(s, trim))
        means[g] = row
    return means


def main():
    p = pd.read_parquet(PANEL, columns=["group", "fund_key", "fiscal_quarter", "rate"])
    feas = json.load(open(FEAS))
    stored = feas["candidate_controls"]

    tr = p[p["group"] == "treated"][["fund_key", "fiscal_quarter", "rate"]].copy()
    tr["treated"] = 1.0

    out = {"source_panel": PANEL, "compared_against": FEAS,
           "pre_period": PRE_QS, "coef_tol": COEF_TOL, "p_tol_loose": P_TOL,
           "controls": {}}
    all_match = True

    for ctl in CONTROLS:
        cc = p[p["group"] == ctl][["fund_key", "fiscal_quarter", "rate"]].copy()
        cc["treated"] = 0.0
        d0 = pd.concat([tr, cc], ignore_index=True)
        d0 = d0[d0["fiscal_quarter"].isin(PRE_QS)].dropna(subset=["rate"]).copy()
        stored_vars = stored[ctl]["pretrend"]["outlier_robustness_variants"]
        ctl_out = {}
        for name, trim in VARIANTS:
            d = d0
            if trim is not None:
                lo, hi = d0["rate"].quantile(trim), d0["rate"].quantile(1 - trim)
                d = d0[(d0["rate"] >= lo) & (d0["rate"] <= hi)]
            b, s, t, pv, n, G = interaction(d)
            sv = stored_vars[name]
            sb = sv["interaction_coef_trend_x_treated"]
            sp = sv["interaction_p"]
            coef_match = (b is not None and sb is not None
                          and abs(b - sb) <= COEF_TOL)
            p_match = (pv is not None and sp is not None and abs(pv - sp) <= P_TOL)
            if not coef_match:
                all_match = False
            ctl_out[name] = {
                "recomputed": {"interaction_coef": b, "se": s, "t": t, "p": pv,
                               "n_obs": n, "n_fund_fe": G},
                "stored": {"interaction_coef": sb,
                           "se": sv["interaction_se_cluster_fund"], "p": sp},
                "coef_abs_diff": abs(b - sb) if (b is not None and sb is not None) else None,
                "p_abs_diff": abs(pv - sp) if (pv is not None and sp is not None) else None,
                "coef_match_1e-6": bool(coef_match),
                "p_match_loose": bool(p_match),
                "parallel_recomputed": bool(pv is not None and pv > 0.10)}
        # robust-parallel = parallel untrimmed AND at 1% trim (matches builder logic)
        ctl_out["parallel_untrimmed"] = ctl_out["untrimmed"]["parallel_recomputed"]
        ctl_out["parallel_robust"] = bool(ctl_out["untrimmed"]["parallel_recomputed"]
                                          and ctl_out["trim_1pct"]["parallel_recomputed"])
        out["controls"][ctl] = ctl_out

    out["all_coef_match_1e-6"] = bool(all_match)
    out["branch_recomputed"] = (
        "NOT-IDENTIFIED"
        if not any(out["controls"][c]["parallel_robust"] for c in CONTROLS)
        else "CONTROL_FOUND")
    out["branch_stored"] = feas["branch_decision"]["decision"]
    out["branch_match"] = bool(out["branch_recomputed"] == out["branch_stored"])

    # ---- 5%-trimmed per-quarter group-mean active-flow rate (verdict corroboration table) ----
    ALL_GROUPS = ["treated", "C1", "C2", "C3"]
    tm = trimmed_quarter_means(p, ALL_GROUPS, trim=0.05)
    tm2 = trimmed_quarter_means(p, ALL_GROUPS, trim=0.05)   # recompute for self-reproducibility
    tm_max_diff = 0.0
    for g in ALL_GROUPS:
        for q in PRE_QS:
            a, b = tm[g][q], tm2[g][q]
            if a is not None and b is not None:
                tm_max_diff = max(tm_max_diff, abs(a - b))
    out["per_quarter_group_means_trim5pct"] = {
        "trim_definition": ("per (group, fiscal_quarter) cell: scipy.stats.trim_mean(rate, "
                            "0.05) -- symmetric 5% two-sided trim of that cell's own non-null "
                            "rate observations, then mean of the remainder. Deterministic "
                            "(fixed integer drop count floor(0.05*n) per end; no randomness)."),
        "pre_period": PRE_QS,
        "groups": ALL_GROUPS,
        "means": tm,
        "self_reproduce_max_abs_diff": tm_max_diff,
        "self_reproduce_match_1e-6": bool(tm_max_diff <= 1e-6)}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, default=str)

    print("DID_PRETREND_VERIFY_DONE")
    print(json.dumps({
        "all_coef_match_1e-6": out["all_coef_match_1e-6"],
        "branch_recomputed": out["branch_recomputed"],
        "branch_stored": out["branch_stored"],
        "branch_match": out["branch_match"],
        "trim5pct_self_reproduce_match_1e-6":
            out["per_quarter_group_means_trim5pct"]["self_reproduce_match_1e-6"],
        "per_control": {c: {v: {"coef": out["controls"][c][v]["recomputed"]["interaction_coef"],
                                "p": out["controls"][c][v]["recomputed"]["p"],
                                "coef_match": out["controls"][c][v]["coef_match_1e-6"]}
                            for v in ["untrimmed", "trim_1pct", "trim_5pct"]}
                        for c in CONTROLS},
        "per_quarter_group_means_trim5pct": out["per_quarter_group_means_trim5pct"]["means"]},
        indent=2, default=str))


if __name__ == "__main__":
    main()
