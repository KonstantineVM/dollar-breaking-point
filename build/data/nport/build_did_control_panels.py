#!/usr/bin/env python3
"""
DiD F3 Part 0(b): assemble control-group active-flow panels + pre-trend parallelism test.

GROUPS
  treated: US-fund active flow into CN-nationality haven securities (REUSED from the
           committed active_flow_panel.parquet -- NOT recomputed).
  C1:      non-CN haven securities. Built from haven_bal_parts/ (persists; no re-download)
           by applying R1-R4 tagging VERBATIM (tag_fullpanel) then taking parent!=CN.
  C2:      non-haven EM equity (re-parsed did_control_parts/, control_group=='C2').
  C3:      developed-market non-US equity (did_control_parts/, control_group=='C3').

DECOMPOSITION: the IDENTICAL constant-price active/passive split from build_active_flow.py
is applied verbatim (imported as _decompose_group), restricted to each group's focus
holdings, per fund (cik|series_id) per security (cusip; isin fallback, placeholder CUSIP
nulled) across CONSECUTIVE fiscal quarters. Correctness gate (active+passive == dCV) run
per group.

NORMALIZATION (matched to treated): treated active_flow_rate = cn_active_flow /
lagged-total-HAVEN currency_value. Same scale rule for each control: control active flow /
the fund's lagged total currency_value of THAT GROUP'S UNIVERSE.
  - C1 universe = total haven (SAME denominator as treated, since treated=CN-haven and
    C1=non-CN-haven are complementary subsets of the haven universe). Treated & C1 thus
    sit on an identical per-fund-quarter base.
  - C2 universe = total EM-equity holdings of the fund (EM_A2 x EC).
  - C3 universe = total DM-equity holdings of the fund (DM_A2 x EC).

PRE-TREND TEST (the gate), over PRE window 2019q4-2021q4 (excludes 2019q3, the all-NEW
first quarter with no lag and no rate): for treated-vs-each-control, stack fund-quarter
active_flow_rate, regress rate ~ trend + treated + trend:treated with fund fixed effects;
PARALLEL iff the trend:treated interaction coef ~0 and insignificant. Report coef/SE/p
per candidate + per-quarter pre-period group-mean rate. Also report event-study-style
leads jointly (informative). Selection by flat pre-trend ONLY; NOT-IDENTIFIED if none.

Writes:
  build/data/nport/did_control_panels.parquet   (treated + C1/C2/C3, all 22 quarters)
  build/audit/did_feasibility.json
"""
import os, sys, json, collections
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/user/dollar-breaking-point"
sys.path.insert(0, HERE)
import tag_fullpanel as T   # R1-R4 VERBATIM

PARTS = os.path.join(ROOT, "build/data/nport/haven_bal_parts")
CTRL_PARTS = os.path.join(ROOT, "build/data/nport/did_control_parts")
TREATED_PANEL = os.path.join(ROOT, "build/data/nport/active_flow_panel.parquet")
OUT_PANEL = os.path.join(ROOT, "build/data/nport/did_control_panels.parquet")
OUT_FEAS = os.path.join(ROOT, "build/audit/did_feasibility.json")
OUT_PROV = os.path.join(ROOT, "build/data/nport/did_control_panels_provenance.md")

PRE_QS = ["2019q4", "2020q1", "2020q2", "2020q3", "2020q4",
          "2021q1", "2021q2", "2021q3", "2021q4"]  # 9 usable pre-quarters (2019q3 has no lag/rate)
POST_Q0 = (2022, 1)


def fq_order(fq):
    return (int(fq[:4]), int(fq[5]))


def qidx(t):
    return t[0] * 4 + (t[1] - 1)


def _decompose_group(df, focus_mask_col, focus_val, base_universe_mask=None):
    """VERBATIM constant-price decomposition (mirrors build_active_flow.decompose) restricted
    to the focus subset. Returns (agg_fund_quarter, gate, drop_report).

    focus_mask_col/focus_val select the FOCUS holdings whose active flow is measured.
    base_universe_mask (a boolean Series over df) defines the normalization universe whose
    lagged total currency_value is the denominator; if None, uses the focus subset itself.
    """
    df = df.copy()
    df["cusip"] = df["cusip"].astype("string")
    df["isin"] = df["isin"].astype("string")

    def _clean_id(s, length):
        s = s.astype("string").str.strip()
        bad = (s.isna() | (s.str.len() != length) | (s.str.fullmatch(r"0+"))
               | s.str.upper().isin(["N/A", "NA", "NONE", "NULL"]))
        return s.mask(bad, pd.NA)

    cusip_c = _clean_id(df["cusip"], 9)
    isin_c = _clean_id(df["isin"], 12)
    df["sec_key"] = cusip_c.where(cusip_c.notna(), isin_c)
    df["cik"] = df["cik"].astype("string").fillna("")
    df["series_id"] = df["series_id"].astype("string").fillna("")
    df["fund_key"] = df["cik"] + "|" + df["series_id"]
    df["currency_value"] = pd.to_numeric(df["currency_value"], errors="coerce")
    df["balance"] = pd.to_numeric(df["balance"], errors="coerce")

    # normalization universe total per fund-quarter (lagged base)
    if base_universe_mask is None:
        uni = df[df[focus_mask_col] == focus_val]
    else:
        uni = df[base_universe_mask]
    tot_uni = (uni.groupby(["fund_key", "fiscal_quarter"])["currency_value"]
                  .sum().rename("tot_uni_cv").reset_index())

    fo = df[df[focus_mask_col] == focus_val].copy()

    grp = (fo.groupby(["fund_key", "cik", "series_id", "sec_key", "fiscal_quarter"],
                      dropna=False)
             .agg(currency_value=("currency_value", "sum"),
                  balance=("balance", "sum"),
                  unit=("unit", "first"))
             .reset_index())

    no_key = grp["sec_key"].isna() | (grp["sec_key"].astype("string").str.len() == 0)
    dropped_nokey_val = float(grp.loc[no_key, "currency_value"].abs().sum())
    grp = grp[~no_key].copy()

    grp["q_ord"] = grp["fiscal_quarter"].map(fq_order)
    grp = grp.sort_values(["fund_key", "sec_key", "q_ord"]).reset_index(drop=True)
    grp["price"] = np.where(grp["balance"] > 0, grp["currency_value"] / grp["balance"], np.nan)

    g = grp.groupby(["fund_key", "sec_key"], sort=False)
    grp["bal_lag"] = g["balance"].shift(1)
    grp["cv_lag"] = g["currency_value"].shift(1)
    grp["price_lag"] = g["price"].shift(1)
    grp["q_lag"] = g["q_ord"].shift(1)

    grp["qi"] = grp["q_ord"].map(qidx)
    grp["qi_lag"] = grp["q_lag"].map(lambda t: qidx(t) if isinstance(t, tuple) else np.nan)
    consecutive = (grp["qi"] - grp["qi_lag"]) == 1
    has_lag = grp["cv_lag"].notna()

    grp["active_flow"] = np.nan
    grp["passive"] = np.nan
    grp["decomp_type"] = ""
    is_new = ~(has_lag & consecutive)
    is_cont = has_lag & consecutive
    cont_decomposable = is_cont & (grp["balance"] > 0) & (grp["bal_lag"] > 0)
    cont_nondecomp = is_cont & ~cont_decomposable

    m = cont_decomposable
    grp.loc[m, "active_flow"] = (grp.loc[m, "balance"] - grp.loc[m, "bal_lag"]) * grp.loc[m, "price_lag"]
    grp.loc[m, "passive"] = (grp.loc[m, "currency_value"] - grp.loc[m, "cv_lag"]) - grp.loc[m, "active_flow"]
    grp.loc[m, "decomp_type"] = "CONTINUING"
    m = cont_nondecomp
    grp.loc[m, "active_flow"] = grp.loc[m, "currency_value"] - grp.loc[m, "cv_lag"]
    grp.loc[m, "passive"] = 0.0
    grp.loc[m, "decomp_type"] = "CONTINUING_NONDECOMP"
    m = is_new
    grp.loc[m, "active_flow"] = grp.loc[m, "currency_value"]
    grp.loc[m, "passive"] = 0.0
    grp.loc[m, "decomp_type"] = "NEW"

    present = set(zip(grp["fund_key"], grp["sec_key"], grp["qi"]))
    all_qis = sorted(grp["qi"].unique())
    qi_max = max(all_qis) if all_qis else 0
    lastqi_by_pair = collections.defaultdict(list)
    for fk, sk, qi in present:
        lastqi_by_pair[(fk, sk)].append(qi)
    cv_map = {(r.fund_key, r.sec_key, r.qi): r.currency_value for r in grp.itertuples(index=False)}
    unit_map = {(r.fund_key, r.sec_key, r.qi): r.unit for r in grp.itertuples(index=False)}
    ck_map = {(r.fund_key, r.sec_key): (r.cik, r.series_id) for r in grp.itertuples(index=False)}
    closed_rows = []
    for (fk, sk), qis in lastqi_by_pair.items():
        sq = set(qis)
        for qi in qis:
            nxt = qi + 1
            if nxt <= qi_max and nxt not in sq:
                cvlag = cv_map[(fk, sk, qi)]
                cik_v, sid_v = ck_map[(fk, sk)]
                yr = nxt // 4; qn = nxt % 4 + 1
                closed_rows.append({
                    "fund_key": fk, "cik": cik_v, "series_id": sid_v, "sec_key": sk,
                    "fiscal_quarter": f"{yr}q{qn}", "currency_value": 0.0, "balance": 0.0,
                    "unit": unit_map.get((fk, sk, qi)), "cv_lag": cvlag,
                    "active_flow": -cvlag, "passive": 0.0, "decomp_type": "CLOSED", "qi": nxt})
    closed_df = pd.DataFrame(closed_rows)

    keep_cols = ["fund_key", "cik", "series_id", "sec_key", "fiscal_quarter",
                 "currency_value", "cv_lag", "balance", "unit", "active_flow",
                 "passive", "decomp_type", "qi"]
    hold = grp.copy()
    hold["cv_lag"] = hold["cv_lag"].fillna(0.0)
    hold = hold[keep_cols]
    if len(closed_df):
        hold = pd.concat([hold, closed_df[keep_cols]], ignore_index=True)

    nondecomp_val = float(grp.loc[grp["decomp_type"] == "CONTINUING_NONDECOMP", "currency_value"].abs().sum())
    total_val = float(grp["currency_value"].abs().sum())
    drop_report = {
        "dropped_no_security_key_value": dropped_nokey_val,
        "continuing_nondecomp_value": nondecomp_val,
        "continuing_nondecomp_value_share": (nondecomp_val / total_val) if total_val else 0.0,
        "n_closed_events": int(len(closed_df))}

    # correctness gate
    h = hold.copy()
    dcv = np.where(h["decomp_type"].isin(["CONTINUING", "CONTINUING_NONDECOMP"]),
                   h["currency_value"] - h["cv_lag"],
          np.where(h["decomp_type"] == "NEW", h["currency_value"], 0.0 - h["cv_lag"]))
    recon = h["active_flow"] + h["passive"] - dcv
    max_abs = float(np.nanmax(np.abs(recon))) if len(h) else 0.0
    w = np.abs(dcv)
    vw = float((np.abs(recon) * w).sum() / w.sum()) if w.sum() else 0.0
    gate = {"n_rows": int(len(h)), "reconstruction_max_abs_error": max_abs,
            "reconstruction_vw_mean_abs_error": vw,
            "pass": bool(max_abs < 1e-3)}

    agg = (hold.groupby(["fund_key", "cik", "series_id", "fiscal_quarter"])
                .agg(active_flow=("active_flow", "sum"),
                     passive=("passive", "sum"),
                     n_holdings=("sec_key", "nunique"))
                .reset_index())

    tot_uni["qi"] = tot_uni["fiscal_quarter"].map(lambda s: qidx(fq_order(s)))
    tot_uni = tot_uni.sort_values(["fund_key", "qi"])
    tot_uni["tot_uni_lag"] = tot_uni.groupby("fund_key")["tot_uni_cv"].shift(1)
    tot_uni["qi_prev"] = tot_uni.groupby("fund_key")["qi"].shift(1)
    tot_uni.loc[(tot_uni["qi"] - tot_uni["qi_prev"]) != 1, "tot_uni_lag"] = np.nan

    agg = agg.merge(tot_uni[["fund_key", "fiscal_quarter", "tot_uni_cv", "tot_uni_lag"]],
                    on=["fund_key", "fiscal_quarter"], how="left")
    agg["active_flow_rate"] = np.where(
        (agg["tot_uni_lag"].notna()) & (agg["tot_uni_lag"] != 0),
        agg["active_flow"] / agg["tot_uni_lag"], np.nan)
    return agg, gate, drop_report


def build_C1():
    """C1: non-CN haven. Tag haven_bal parts R1-R4 VERBATIM; focus = parent!=CN; base
    universe = ALL haven (matches treated denominator = total haven)."""
    S = T.build_rule_sets()
    files = sorted([f for f in os.listdir(PARTS)
                    if f.startswith("haven_bal_") and f.endswith(".parquet")],
                   key=lambda f: fq_order(f[len("haven_bal_"):-len(".parquet")]))
    frames = []
    for f in files:
        t = pq.read_table(os.path.join(PARTS, f)).to_pandas()
        c6 = [T.norm6(c) for c in t["cusip"].tolist()]
        isin = t["isin"].tolist(); lei = t["issuer_lei"].tolist()
        fired = [T.tag_rows(isin[i], c6[i], lei[i], S) for i in range(len(t))]
        t["parent_nationality"] = ["CN" if x else "NON_CN" for x in fired]
        frames.append(t)
    df = pd.concat(frames, ignore_index=True)
    # focus = NON_CN haven; base universe = ALL haven (df is haven-only already)
    df["focus"] = np.where(df["parent_nationality"] == "NON_CN", "FOCUS", "OTHER")
    base = pd.Series(True, index=df.index)  # all rows = total haven
    agg, gate, drop = _decompose_group(df, "focus", "FOCUS", base_universe_mask=base)
    return agg, gate, drop


def build_C1_treated_check():
    """Correctness cross-check: run the SAME generalized decomposition with focus=CN-haven
    and base=total-haven; it must reproduce the committed treated active_flow_rate."""
    S = T.build_rule_sets()
    files = sorted([f for f in os.listdir(PARTS)
                    if f.startswith("haven_bal_") and f.endswith(".parquet")],
                   key=lambda f: fq_order(f[len("haven_bal_"):-len(".parquet")]))
    frames = []
    for f in files:
        t = pq.read_table(os.path.join(PARTS, f)).to_pandas()
        c6 = [T.norm6(c) for c in t["cusip"].tolist()]
        isin = t["isin"].tolist(); lei = t["issuer_lei"].tolist()
        fired = [T.tag_rows(isin[i], c6[i], lei[i], S) for i in range(len(t))]
        t["parent_nationality"] = ["CN" if x else "NON_CN" for x in fired]
        frames.append(t)
    df = pd.concat(frames, ignore_index=True)
    df["focus"] = np.where(df["parent_nationality"] == "CN", "FOCUS", "OTHER")
    base = pd.Series(True, index=df.index)
    agg, gate, drop = _decompose_group(df, "focus", "FOCUS", base_universe_mask=base)
    return agg


def build_C_reparse(group_label):
    """C2 or C3 from did_control_parts. focus = the group's holdings; base universe =
    same group (its own EM/DM-equity universe)."""
    files = sorted([f for f in os.listdir(CTRL_PARTS)
                    if f.startswith("did_ctrl_") and f.endswith(".parquet")],
                   key=lambda f: fq_order(f[len("did_ctrl_"):-len(".parquet")]))
    frames = []
    for f in files:
        t = pq.read_table(os.path.join(CTRL_PARTS, f)).to_pandas()
        t = t[t["control_group"] == group_label]
        if len(t):
            frames.append(t)
    if not frames:
        return None, None, None
    df = pd.concat(frames, ignore_index=True)
    df["focus"] = "FOCUS"
    base = pd.Series(True, index=df.index)  # base = this group's universe (already filtered)
    agg, gate, drop = _decompose_group(df, "focus", "FOCUS", base_universe_mask=base)
    return agg, gate, drop


# --------------------------- pre-trend test ---------------------------
def ols_with_fe(y, X, fe_groups):
    """OLS of y on X (incl intercept col) after within-transform on fund FE. Returns
    (beta, se, resid_df). Cluster-robust SE by fund. Absorb fund FE by demeaning."""
    df = pd.DataFrame(X.copy())
    df["_y"] = y
    df["_g"] = fe_groups
    # demean within fund (absorb FE)
    num_cols = [c for c in df.columns if c not in ("_g",)]
    dem = df.groupby("_g")[num_cols].transform(lambda s: s - s.mean())
    Y = dem["_y"].values
    cols = [c for c in X.columns if c != "const"]  # const absorbed by FE
    Xm = dem[cols].values
    # drop columns that are all ~0 after demeaning (collinear w/ FE)
    keep = [i for i in range(Xm.shape[1]) if np.nanstd(Xm[:, i]) > 1e-12]
    cols = [cols[i] for i in keep]
    Xm = Xm[:, keep]
    mask = ~np.isnan(Y) & ~np.isnan(Xm).any(axis=1)
    Y = Y[mask]; Xm = Xm[mask]; g = df["_g"].values[mask]
    n, k = Xm.shape
    XtX = Xm.T @ Xm
    XtX_inv = np.linalg.pinv(XtX)
    beta = XtX_inv @ (Xm.T @ Y)
    resid = Y - Xm @ beta
    # cluster-robust by fund
    meat = np.zeros((k, k))
    for gg in np.unique(g):
        idx = g == gg
        Xg = Xm[idx]; ug = resid[idx]
        s = Xg.T @ ug
        meat += np.outer(s, s)
    G = len(np.unique(g))
    dof = (G / (G - 1)) * ((n - 1) / (n - k)) if G > 1 and n > k else 1.0
    V = XtX_inv @ meat @ XtX_inv * dof
    se = np.sqrt(np.diag(V))
    return dict(zip(cols, beta)), dict(zip(cols, se)), n, G


def pretrend_test(treated_df, control_df):
    """Stack treated (treated=1) & control (treated=0) fund-quarter rates over PRE_QS.
    Regress rate ~ trend + treated + trend:treated with fund FE, cluster by fund.
    Report the trend:treated interaction coef/SE/p. Also per-quarter group means."""
    from scipy import stats
    tt = treated_df[["fund_key", "fiscal_quarter", "rate"]].copy(); tt["treated"] = 1.0
    cc = control_df[["fund_key", "fiscal_quarter", "rate"]].copy(); cc["treated"] = 0.0
    d = pd.concat([tt, cc], ignore_index=True)
    d = d[d["fiscal_quarter"].isin(PRE_QS)].copy()
    d = d.dropna(subset=["rate"])
    # trend = 0..8 over the 9 pre-quarters
    qmap = {q: i for i, q in enumerate(PRE_QS)}
    d["trend"] = d["fiscal_quarter"].map(qmap).astype(float)
    # FE key: unique fund WITHIN group (a fund could appear in both treated & control)
    d["fe"] = d["treated"].astype(int).astype(str) + "|" + d["fund_key"]
    X = pd.DataFrame({
        "const": 1.0,
        "trend": d["trend"].values,
        "treated": d["treated"].values,
        "trend_x_treated": (d["trend"] * d["treated"]).values,
    })
    beta, se, n, G = ols_with_fe(d["rate"].values, X, d["fe"].values)
    # interaction
    b = beta.get("trend_x_treated", np.nan)
    s = se.get("trend_x_treated", np.nan)
    tval = b / s if s and not np.isnan(s) and s != 0 else np.nan
    p = float(2 * stats.t.sf(abs(tval), max(G - 1, 1))) if not np.isnan(tval) else None
    # per-quarter group means
    means = []
    for q in PRE_QS:
        tq = tt[(tt["fiscal_quarter"] == q)]["rate"].dropna()
        cq = cc[(cc["fiscal_quarter"] == q)]["rate"].dropna()
        means.append({"fiscal_quarter": q,
                      "treated_mean_rate": float(tq.mean()) if len(tq) else None,
                      "treated_n": int(len(tq)),
                      "control_mean_rate": float(cq.mean()) if len(cq) else None,
                      "control_n": int(len(cq))})
    return {
        "interaction_coef_trend_x_treated": float(b) if not np.isnan(b) else None,
        "interaction_se_cluster_fund": float(s) if not np.isnan(s) else None,
        "interaction_t": float(tval) if not np.isnan(tval) else None,
        "interaction_p": p,
        "n_obs_pre": int(n), "n_fund_fe": int(G),
        "parallel": (p is not None and p > 0.10),
        "per_quarter_group_means": means,
    }


def main():
    # treated (reused, committed)
    tr = pq.read_table(TREATED_PANEL).to_pandas()
    tr = tr.rename(columns={"active_flow_rate": "rate", "cn_active_flow": "active_flow",
                            "cn_passive": "passive"})
    tr["group"] = "treated"
    treated_rate = tr[["fund_key", "cik", "series_id", "fiscal_quarter", "rate",
                       "active_flow", "passive"]].copy()

    results = {}
    panels = [tr.assign(active_flow_rate=tr["rate"])[
        ["group", "fund_key", "cik", "series_id", "fiscal_quarter",
         "active_flow", "passive", "rate"]]]

    # ---- correctness cross-check: generalized decomp on CN reproduces committed treated
    chk = build_C1_treated_check()
    m = treated_rate.merge(chk[["fund_key", "fiscal_quarter", "active_flow_rate"]],
                           on=["fund_key", "fiscal_quarter"], how="inner",
                           suffixes=("_committed", "_recomp"))
    diff = (m["rate"] - m["active_flow_rate"]).abs()
    treated_recon = {"n_matched": int(len(m)),
                     "max_abs_rate_diff": float(diff.max()) if len(m) else None,
                     "reproduces_committed_treated": bool(len(m) and diff.max() < 1e-6)}

    # ---- C1
    c1, g1, d1 = build_C1()
    c1r = c1.rename(columns={"active_flow_rate": "rate"})
    c1r["group"] = "C1"
    panels.append(c1r[["group", "fund_key", "cik", "series_id", "fiscal_quarter",
                       "active_flow", "passive", "rate"]])
    res1 = pretrend_test(treated_rate.rename(columns={"rate": "rate"}), c1r)
    results["C1"] = {"label": "non-CN haven (CYM/HKG/VGB, parent!=CN)",
                     "gate": g1, "drop_report": d1, "pretrend": res1,
                     "n_fund_quarters": int(c1r["rate"].notna().sum())}

    # ---- C2 / C3 (if reparse present)
    for lab, name in [("C2", "non-haven EM equity"), ("C3", "developed-market non-US equity")]:
        if not os.path.isdir(CTRL_PARTS) or not any(
                f.startswith("did_ctrl_") for f in os.listdir(CTRL_PARTS)):
            results[lab] = {"label": name, "status": "INCOMPLETE_reparse_not_present"}
            continue
        agg, gate, drop = build_C_reparse(lab)
        if agg is None:
            results[lab] = {"label": name, "status": "INCOMPLETE_no_rows"}
            continue
        cr = agg.rename(columns={"active_flow_rate": "rate"})
        cr["group"] = lab
        panels.append(cr[["group", "fund_key", "cik", "series_id", "fiscal_quarter",
                          "active_flow", "passive", "rate"]])
        res = pretrend_test(treated_rate, cr)
        results[lab] = {"label": name, "gate": gate, "drop_report": drop,
                        "pretrend": res, "n_fund_quarters": int(cr["rate"].notna().sum())}

    # write panel
    allp = pd.concat(panels, ignore_index=True)
    allp.to_parquet(OUT_PANEL, index=False)

    # per-quarter row counts per group
    rowcounts = (allp.groupby(["group", "fiscal_quarter"])
                     .agg(n_fund_quarters=("fund_key", "nunique"),
                          n_rate_nonnull=("rate", lambda s: int(s.notna().sum())))
                     .reset_index())
    rc = collections.defaultdict(dict)
    for r in rowcounts.itertuples(index=False):
        rc[r.group][r.fiscal_quarter] = {"n_fund_quarters": int(r.n_fund_quarters),
                                          "n_rate_nonnull": int(r.n_rate_nonnull)}

    # branch decision
    parallel_controls = [k for k, v in results.items()
                         if v.get("pretrend", {}).get("parallel")]
    incomplete = [k for k, v in results.items() if "status" in v]
    if parallel_controls:
        branch = {"decision": "CONTROL_FOUND", "valid_controls": parallel_controls,
                  "rule": "flat pre-trend (trend x treated interaction insignificant at 10%)"}
    elif incomplete:
        branch = {"decision": "INCOMPLETE", "incomplete_controls": incomplete,
                  "note": "no parallel control among completed candidates; reparse pending"}
    else:
        branch = {"decision": "NOT-IDENTIFIED",
                  "note": "no candidate control has a flat pre-trend; DiD not identified"}

    feas = {
        "confirmed_quarter_list": {
            "all": sorted({q for q in allp["fiscal_quarter"].unique()}, key=fq_order),
            "pre_freeze": ["2019q3"] + PRE_QS,
            "pre_freeze_count": 10,
            "pre_usable_for_rate": PRE_QS,
            "pre_usable_count": len(PRE_QS),
            "post_freeze": ["2022q1", "2022q2", "2022q3", "2022q4", "2023q1", "2023q2",
                            "2023q3", "2023q4", "2024q1", "2024q2", "2024q3", "2024q4"],
            "post_freeze_count": 12,
            "freeze_quarter": "2022q1",
            "note": ("10 pre-freeze (2019q3-2021q4) confirmed from active_flow_panel; "
                     "2019q3 is all-NEW (no consecutive lag) so has no active_flow_rate; "
                     "the pre-trend test uses the 9 pre-quarters 2019q4-2021q4.")},
        "normalization": ("active_flow_rate = group active flow / fund's lagged total "
                          "currency_value of that group's universe. Treated & C1 share the "
                          "total-haven denominator (complementary haven subsets); C2/C3 use "
                          "their own EM/DM-equity universe."),
        "decomposition": "constant-price active/passive from build_active_flow.py, VERBATIM.",
        "treated_recon_crosscheck": treated_recon,
        "country_sets": {
            "C2_EM_A2": None, "C3_DM_A2": None},  # filled from reparse summary below
        "candidate_controls": results,
        "per_quarter_row_counts": dict(rc),
        "branch_decision": branch,
        "artifacts": {"control_panels_parquet": OUT_PANEL, "feasibility_json": OUT_FEAS},
    }
    # attach country sets from reparse summary if present
    rs = os.path.join(CTRL_PARTS, "_reparse_summary.json")
    if os.path.exists(rs):
        rss = json.load(open(rs))
        feas["country_sets"]["C2_EM_A2"] = rss.get("em_a2")
        feas["country_sets"]["C3_DM_A2"] = rss.get("dm_a2")
        feas["reparse_per_quarter"] = rss.get("per_quarter")
        feas["reparse_skipped"] = rss.get("skipped")

    os.makedirs(os.path.dirname(OUT_FEAS), exist_ok=True)
    with open(OUT_FEAS, "w") as f:
        json.dump(feas, f, indent=2, default=str)

    print("DID_CONTROLS_DONE")
    print(json.dumps({"branch": branch, "treated_recon": treated_recon,
                      "results_summary": {k: {"parallel": v.get("pretrend", {}).get("parallel"),
                                              "coef": v.get("pretrend", {}).get("interaction_coef_trend_x_treated"),
                                              "p": v.get("pretrend", {}).get("interaction_p"),
                                              "status": v.get("status")}
                                          for k, v in results.items()}},
                     indent=2, default=str))
    write_prov(feas, results)


def write_prov(feas, results):
    L = []
    L.append("# DiD F3 Part 0(b) — Control Panels & Pre-Trend Provenance\n\n")
    L.append("SOURCE: Real SEC Form N-PORT dissemination ZIPs "
             "`https://www.sec.gov/files/dera/data/form-n-port-data-sets/{YYYYqQ}_nport.zip`, "
             "UA `dollar-breaking-point research milevsky@hotmail.com`, streamed and DELETED "
             "per quarter. Fiscal quarter = zip label minus one quarter.\n\n")
    L.append("## Groups\n")
    L.append("- **treated**: CN-nationality haven active flow, REUSED verbatim from committed "
             "`active_flow_panel.parquet` (not recomputed).\n")
    L.append("- **C1**: non-CN haven (CYM/HKG/VGB residence, parent!=CN). Built from persisted "
             "`haven_bal_parts/` by R1-R4 tagging VERBATIM (`tag_fullpanel`), focus=parent!=CN, "
             "normalization base = total haven (identical denominator to treated). No re-download.\n")
    cs = feas.get("country_sets", {})
    L.append(f"- **C2**: non-haven EM equity, ASSET_CAT=EC, INVESTMENT_COUNTRY in "
             f"{cs.get('C2_EM_A2')}. Re-parsed (22 quarters).\n")
    L.append(f"- **C3**: developed-market non-US equity, ASSET_CAT=EC, INVESTMENT_COUNTRY in "
             f"{cs.get('C3_DM_A2')}. Same re-parse pass, split by country classification.\n\n")
    L.append("## Decomposition (reused verbatim)\n")
    L.append("Constant-price: CONTINUING active=(bal_t-bal_{t-1})*price_{t-1}, "
             "passive=dCV-active; NEW active=cv_t; CLOSED active=-cv_{t-1}. Placeholder CUSIP "
             "nulled -> ISIN fallback. Correctness gate active+passive==dCV per group below.\n\n")
    tr = feas["treated_recon_crosscheck"]
    L.append(f"## Treated reconstruction cross-check\n"
             f"Generalized decomposition run with focus=CN, base=total-haven reproduces the "
             f"committed treated rate: matched={tr['n_matched']}, "
             f"max_abs_rate_diff={tr['max_abs_rate_diff']}, "
             f"reproduces={tr['reproduces_committed_treated']}.\n\n")
    L.append("## Pre-trend parallelism (PRE 2019q4-2021q4; rate ~ trend + treated + "
             "trend:treated, fund FE, cluster-by-fund SE)\n\n")
    L.append("| control | interaction coef | SE | p | parallel | gate pass | n_fq |\n")
    L.append("|---|---|---|---|---|---|---|\n")
    for k, v in results.items():
        pt = v.get("pretrend")
        if not pt:
            L.append(f"| {k} | {v.get('status','')} | | | | | |\n")
            continue
        g = v.get("gate", {})
        L.append(f"| {k} | {pt['interaction_coef_trend_x_treated']:.4g} | "
                 f"{pt['interaction_se_cluster_fund']:.4g} | {pt['interaction_p']:.4g} | "
                 f"{pt['parallel']} | {g.get('pass')} | {v.get('n_fund_quarters')} |\n")
    L.append(f"\n## Branch decision\n{json.dumps(feas['branch_decision'], indent=2)}\n\n")
    L.append("## Per-quarter row counts (fund-quarters with non-null rate)\n\n")
    rc = feas["per_quarter_row_counts"]
    for grp in ["treated", "C1", "C2", "C3"]:
        if grp not in rc:
            continue
        L.append(f"**{grp}**: ")
        L.append(", ".join(f"{q}={rc[grp][q]['n_rate_nonnull']}"
                           for q in sorted(rc[grp], key=fq_order)))
        L.append("\n\n")
    if feas.get("reparse_skipped"):
        L.append(f"## INCOMPLETE / skipped re-parse quarters\n{json.dumps(feas['reparse_skipped'])}\n")
    with open(OUT_PROV, "w") as f:
        f.write("".join(L))


if __name__ == "__main__":
    main()
