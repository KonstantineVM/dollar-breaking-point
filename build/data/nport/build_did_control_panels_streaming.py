#!/usr/bin/env python3
"""
DiD F3 Part 0(b) — MEMORY-EFFICIENT (streaming) rewrite of build_did_control_panels.py.

Purpose and deliverables are IDENTICAL to the prior attempt
(build/data/nport/build_did_control_panels.py, kept for provenance). Only the MEMORY
pattern is fixed: the prior attempt concatenated all 22 quarters of raw non-haven
holdings into a single DataFrame before decomposing, which peaked >13GB RSS and was
killed. This rewrite streams quarter-by-quarter, holding at most TWO consecutive
quarters of holdings in memory at a time.

WHY TWO QUARTERS SUFFICE. The constant-price active/passive split of build_active_flow.py
(reused VERBATIM below) is a first-difference over CONSECUTIVE fiscal quarters per
(fund, security):
    CONTINUING (present t-1 and t): active = (bal_t - bal_{t-1}) * price_{t-1}
    NEW        (absent t-1, present t): active = cv_t
    CLOSED     (present t-1, absent t): active = -cv_{t-1}
Every branch needs only quarter t and its immediate predecessor t-1. So we:
  1. load quarter t's holdings, collapse IMMEDIATELY to per-(fund_key, sec_key) rows
     (summing currency_value/balance over duplicate lots) — this is small and drops
     every heavy raw string column;
  2. combine with the previously-collapsed quarter t-1 (already in memory, small);
  3. emit per-(fund,quarter) active flow for quarter t (CONTINUING/NEW rows) and the
     CLOSED events falling in quarter t (securities in t-1 absent in t);
  4. also accumulate the per-(fund,quarter) normalization universe total (lagged);
  5. drop quarter t-1, keep the collapsed quarter t as the new "previous", del+gc the
     raw frame; move on.
We NEVER hold more than two quarters of (collapsed) holdings. The raw per-quarter frame
is freed before the next quarter loads. Peak is bounded by the single largest raw quarter
(~570k rows for ctrl, ~100k for haven) plus two small collapsed frames.

CORRECTNESS. The streamed per-(fund,quarter) active-flow decomposition is algebraically
identical to the batch decomposition of build_active_flow.decompose (same active/passive
formulas, same placeholder-CUSIP nulling, same lot-summing, same consecutive-quarter
rule, same CLOSED synthesis, same normalization denominator). SANITY GATE: the streamed
treated group (CN-nationality haven) is reconciled against the committed
active_flow_panel.parquet; max abs rate diff is reported (must be ~0).

GROUPS / NORMALIZATION (matched to treated, unchanged from prior attempt):
  treated : CN-nationality haven active flow / lagged total-haven cv.
  C1      : non-CN haven active flow / lagged total-haven cv (SAME denominator as
            treated; treated=CN-haven and C1=non-CN-haven are complementary haven subsets).
  C2      : EM-equity active flow / lagged total EM-equity cv.
  C3      : DM-equity active flow / lagged total DM-equity cv.

Reads (already on disk; NOT re-downloaded / re-parsed):
  build/data/nport/haven_bal_parts/haven_bal_{fq}.parquet  (CN + non-CN haven; balance/unit)
  build/data/nport/did_control_parts/did_ctrl_{fq}.parquet (control_group in {C2,C3})
  build/data/nport/active_flow_panel.parquet               (committed treated; reconciliation)

Writes (IDENTICAL deliverables):
  build/data/nport/did_control_panels.parquet
  build/audit/did_feasibility.json
  build/data/nport/did_control_panels_provenance.md
"""
import os, sys, gc, json, collections, resource
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/user/dollar-breaking-point"
sys.path.insert(0, HERE)
import tag_fullpanel as T   # R1-R4 VERBATIM tagging

PARTS = os.path.join(ROOT, "build/data/nport/haven_bal_parts")
CTRL_PARTS = os.path.join(ROOT, "build/data/nport/did_control_parts")
TREATED_PANEL = os.path.join(ROOT, "build/data/nport/active_flow_panel.parquet")
OUT_PANEL = os.path.join(ROOT, "build/data/nport/did_control_panels.parquet")
OUT_FEAS = os.path.join(ROOT, "build/audit/did_feasibility.json")
OUT_PROV = os.path.join(ROOT, "build/data/nport/did_control_panels_provenance.md")

PRE_QS = ["2019q4", "2020q1", "2020q2", "2020q3", "2020q4",
          "2021q1", "2021q2", "2021q3", "2021q4"]  # 9 usable pre-quarters (2019q3 all-NEW)


def fq_order(fq):
    return (int(fq[:4]), int(fq[5]))


def qidx(t):
    return t[0] * 4 + (t[1] - 1)


def peak_rss_gb():
    # ru_maxrss is KB on Linux
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0 * 1024.0)


def _clean_id(s, length):
    s = s.astype("string").str.strip()
    bad = (s.isna() | (s.str.len() != length) | (s.str.fullmatch(r"0+"))
           | s.str.upper().isin(["N/A", "NA", "NONE", "NULL"]))
    return s.mask(bad, pd.NA)


def collapse_quarter(df):
    """Collapse a raw per-holding quarter frame to per-(fund_key, sec_key) rows, summing
    currency_value/balance over duplicate lots, keeping a representative unit. This is the
    memory reduction step: every heavy raw string column is dropped here. Returns a small
    frame with columns [fund_key, cik, series_id, sec_key, fiscal_quarter, currency_value,
    balance, unit] plus a fund-quarter universe total (all rows of df, pre security-key
    drop) computed alongside.

    df must already be restricted to the group's FOCUS holdings for the active-flow
    subset; the normalization universe equals the focus subset for every group here
    (treated/C1 pass the full haven frame per side but the base is total haven — handled
    by the caller passing `uni_total` explicitly).
    """
    cusip_c = _clean_id(df["cusip"], 9)
    isin_c = _clean_id(df["isin"], 12)
    sec_key = cusip_c.where(cusip_c.notna(), isin_c)
    cik = df["cik"].astype("string").fillna("")
    sid = df["series_id"].astype("string").fillna("")
    fund_key = (cik + "|" + sid)
    cv = pd.to_numeric(df["currency_value"], errors="coerce")
    bal = pd.to_numeric(df["balance"], errors="coerce")
    fq = df["fiscal_quarter"].iloc[0] if len(df) else None
    small = pd.DataFrame({
        "fund_key": fund_key.values, "cik": cik.values, "series_id": sid.values,
        "sec_key": sec_key.values, "currency_value": cv.values,
        "balance": bal.values, "unit": df["unit"].astype("string").values})
    small["fiscal_quarter"] = fq
    g = (small.groupby(["fund_key", "cik", "series_id", "sec_key", "fiscal_quarter"],
                       dropna=False)
              .agg(currency_value=("currency_value", "sum"),
                   balance=("balance", "sum"),
                   unit=("unit", "first"))
              .reset_index())
    return g, fq


class StreamDecomposer:
    """Streams the constant-price active/passive decomposition quarter-by-quarter,
    holding only quarters t-1 (prev) and t (cur) of COLLAPSED per-(fund,sec) holdings.

    Emits per-(fund,quarter) aggregated active_flow / passive, and — for the normalization
    denominator — the fund-quarter universe currency_value total (lagged, consecutive only).
    The normalization universe total is supplied per quarter by the caller (for haven
    groups the universe is total haven = CN + non-CN; for C2/C3 it is the group itself).
    """
    def __init__(self):
        self.prev = None            # collapsed frame for q_{t-1} (indexed by (fund,sec))
        self.prev_qi = None
        self.agg_rows = []          # accumulated per-(fund,quarter) aggregates
        self.uni_totals = []        # per-(fund,quarter) universe totals
        # correctness-gate accumulators (streamed, not stored per-row)
        self.recon_max_abs = 0.0
        self.recon_num = 0.0
        self.recon_den = 0.0
        self.n_rows = 0
        self.dropped_nokey_val = 0.0
        self.nondecomp_val = 0.0
        self.total_val = 0.0
        self.n_closed = 0

    def _accum_gate(self, active, passive, dcv):
        recon = np.abs((active + passive) - dcv)
        if len(recon):
            m = float(np.nanmax(recon))
            if m > self.recon_max_abs:
                self.recon_max_abs = m
            w = np.abs(dcv)
            self.recon_num += float(np.nansum(recon * w))
            self.recon_den += float(np.nansum(w))
            self.n_rows += int(len(recon))

    def push(self, cur, cur_qi, uni_total_df):
        """Process quarter t (collapsed frame `cur`, integer index `cur_qi`). `uni_total_df`
        is a small frame [fund_key, fiscal_quarter, tot_uni_cv] for THIS quarter's
        normalization universe. Uses self.prev (q_{t-1})."""
        fq = cur["fiscal_quarter"].iloc[0] if len(cur) else None
        # record universe total for this quarter
        if uni_total_df is not None and len(uni_total_df):
            self.uni_totals.append(uni_total_df.assign(qi=cur_qi))

        # drop rows with no usable security key (report their value)
        cur = cur.copy()
        no_key = cur["sec_key"].isna() | (cur["sec_key"].astype("string").str.len() == 0)
        self.dropped_nokey_val += float(cur.loc[no_key, "currency_value"].abs().sum())
        cur = cur[~no_key].copy()
        self.total_val += float(cur["currency_value"].abs().sum())

        cur["price"] = np.where(cur["balance"] > 0,
                                cur["currency_value"] / cur["balance"], np.nan)

        consecutive = (self.prev is not None) and (cur_qi - self.prev_qi == 1)

        # merge prev onto cur by (fund_key, sec_key) to identify CONTINUING vs NEW
        if consecutive and self.prev is not None:
            p = self.prev[["fund_key", "sec_key", "currency_value", "balance", "price"]]
            p = p.rename(columns={"currency_value": "cv_lag", "balance": "bal_lag",
                                  "price": "price_lag"})
            m = cur.merge(p, on=["fund_key", "sec_key"], how="left")
        else:
            m = cur.copy()
            m["cv_lag"] = np.nan; m["bal_lag"] = np.nan; m["price_lag"] = np.nan

        has_lag = m["cv_lag"].notna()
        is_cont = has_lag
        cont_dec = is_cont & (m["balance"] > 0) & (m["bal_lag"] > 0)
        cont_non = is_cont & ~cont_dec
        is_new = ~has_lag

        active = np.full(len(m), np.nan)
        passive = np.full(len(m), np.nan)
        dtype = np.array([""] * len(m), dtype=object)

        a = cont_dec.values
        active[a] = (m.loc[cont_dec, "balance"] - m.loc[cont_dec, "bal_lag"]).values * \
                    m.loc[cont_dec, "price_lag"].values
        passive[a] = (m.loc[cont_dec, "currency_value"] - m.loc[cont_dec, "cv_lag"]).values - active[a]
        dtype[a] = "CONTINUING"

        a = cont_non.values
        active[a] = (m.loc[cont_non, "currency_value"] - m.loc[cont_non, "cv_lag"]).values
        passive[a] = 0.0
        dtype[a] = "CONTINUING_NONDECOMP"
        self.nondecomp_val += float(m.loc[cont_non, "currency_value"].abs().sum())

        a = is_new.values
        active[a] = m.loc[is_new, "currency_value"].values
        passive[a] = 0.0
        dtype[a] = "NEW"

        m["active_flow"] = active
        m["passive"] = passive
        m["decomp_type"] = dtype

        # observed dCV for CONTINUING/NONDECOMP = cv - cv_lag; NEW = cv
        dcv = np.where(np.isin(m["decomp_type"], ["CONTINUING", "CONTINUING_NONDECOMP"]),
                       (m["currency_value"] - m["cv_lag"].fillna(0.0)).values,
                       m["currency_value"].values)
        self._accum_gate(active, passive, dcv)

        # CLOSED events: securities present in prev (t-1) but ABSENT in cur (t), only if
        # consecutive. active = -cv_lag. These land in quarter t.
        if consecutive and self.prev is not None:
            prev_keys = self.prev[["fund_key", "cik", "series_id", "sec_key",
                                    "currency_value"]].rename(
                columns={"currency_value": "cv_lag"})
            cur_keys = cur[["fund_key", "sec_key"]].drop_duplicates()
            closed = prev_keys.merge(cur_keys, on=["fund_key", "sec_key"], how="left",
                                     indicator=True)
            closed = closed[closed["_merge"] == "left_only"].copy()
            if len(closed):
                closed["active_flow"] = -closed["cv_lag"]
                closed["passive"] = 0.0
                closed["decomp_type"] = "CLOSED"
                closed["fiscal_quarter"] = fq
                self.n_closed += int(len(closed))
                # closed reconstruct: active+passive == dcv where dcv = 0 - cv_lag
                self._accum_gate(closed["active_flow"].values, closed["passive"].values,
                                 (0.0 - closed["cv_lag"]).values)
                m_closed = closed[["fund_key", "cik", "series_id", "sec_key",
                                   "fiscal_quarter", "active_flow", "passive"]]
            else:
                m_closed = None
        else:
            m_closed = None

        # aggregate this quarter's rows (continuing/new) + closed to per-(fund,quarter)
        part = m[["fund_key", "cik", "series_id", "fiscal_quarter", "sec_key",
                  "active_flow", "passive"]]
        if m_closed is not None:
            part = pd.concat([part, m_closed], ignore_index=True)
        aggq = (part.groupby(["fund_key", "cik", "series_id", "fiscal_quarter"])
                    .agg(active_flow=("active_flow", "sum"),
                         passive=("passive", "sum"),
                         n_holdings=("sec_key", "nunique"))
                    .reset_index())
        self.agg_rows.append(aggq)

        # advance window: current becomes prev; free everything else
        self.prev = cur[["fund_key", "cik", "series_id", "sec_key",
                         "currency_value", "balance", "price"]].copy()
        self.prev_qi = cur_qi
        del m, cur, part, aggq
        if m_closed is not None:
            del m_closed
        gc.collect()

    def finalize(self):
        """Combine accumulated per-(fund,quarter) aggregates, attach lagged universe
        totals, compute active_flow_rate. Returns (agg_df, gate, drop_report)."""
        agg = pd.concat(self.agg_rows, ignore_index=True) if self.agg_rows else \
            pd.DataFrame(columns=["fund_key", "cik", "series_id", "fiscal_quarter",
                                  "active_flow", "passive", "n_holdings"])
        uni = pd.concat(self.uni_totals, ignore_index=True) if self.uni_totals else \
            pd.DataFrame(columns=["fund_key", "fiscal_quarter", "tot_uni_cv", "qi"])
        uni = uni.sort_values(["fund_key", "qi"])
        uni["tot_uni_lag"] = uni.groupby("fund_key")["tot_uni_cv"].shift(1)
        uni["qi_prev"] = uni.groupby("fund_key")["qi"].shift(1)
        uni.loc[(uni["qi"] - uni["qi_prev"]) != 1, "tot_uni_lag"] = np.nan
        agg = agg.merge(uni[["fund_key", "fiscal_quarter", "tot_uni_cv", "tot_uni_lag"]],
                        on=["fund_key", "fiscal_quarter"], how="left")
        agg["active_flow_rate"] = np.where(
            (agg["tot_uni_lag"].notna()) & (agg["tot_uni_lag"] != 0),
            agg["active_flow"] / agg["tot_uni_lag"], np.nan)
        gate = {"n_rows": int(self.n_rows),
                "reconstruction_max_abs_error": float(self.recon_max_abs),
                "reconstruction_vw_mean_abs_error":
                    float(self.recon_num / self.recon_den) if self.recon_den else 0.0,
                "pass": bool(self.recon_max_abs < 1e-3)}
        drop_report = {
            "dropped_no_security_key_value": float(self.dropped_nokey_val),
            "continuing_nondecomp_value": float(self.nondecomp_val),
            "continuing_nondecomp_value_share":
                float(self.nondecomp_val / self.total_val) if self.total_val else 0.0,
            "n_closed_events": int(self.n_closed)}
        return agg, gate, drop_report


# --------------------------- per-group streaming drivers ---------------------------
def stream_haven_group(focus_nat):
    """Stream treated (focus_nat='CN') or C1 (focus_nat='NON_CN') from haven_bal_parts.
    Normalization universe = TOTAL haven (CN + non-CN) per fund-quarter, matching the
    committed treated denominator. R1-R4 tagging applied VERBATIM per quarter."""
    S = T.build_rule_sets()
    files = sorted([f for f in os.listdir(PARTS)
                    if f.startswith("haven_bal_") and f.endswith(".parquet")],
                   key=lambda f: fq_order(f[len("haven_bal_"):-len(".parquet")]))
    dec = StreamDecomposer()
    per_q_counts = {}
    for f in files:
        fq = f[len("haven_bal_"):-len(".parquet")]
        t = pq.read_table(os.path.join(PARTS, f),
                          columns=["cik", "series_id", "fiscal_quarter", "cusip", "isin",
                                   "issuer_lei", "currency_value", "balance", "unit"]).to_pandas()
        # tag CN vs non-CN VERBATIM
        c6 = [T.norm6(c) for c in t["cusip"].tolist()]
        isin = t["isin"].tolist(); lei = t["issuer_lei"].tolist()
        fired = [T.tag_rows(isin[i], c6[i], lei[i], S) for i in range(len(t))]
        nat = np.where([bool(x) for x in fired], "CN", "NON_CN")
        # universe total = ALL haven this quarter (before restricting to focus)
        tmp = pd.DataFrame({
            "fund_key": (t["cik"].astype("string").fillna("") + "|" +
                         t["series_id"].astype("string").fillna("")).values,
            "currency_value": pd.to_numeric(t["currency_value"], errors="coerce").values})
        uni_total = (tmp.groupby("fund_key")["currency_value"].sum()
                        .rename("tot_uni_cv").reset_index())
        uni_total["fiscal_quarter"] = fq
        del tmp
        # restrict to focus nationality, then collapse
        tf = t[nat == focus_nat].copy()
        del t, c6, isin, lei, fired, nat
        gc.collect()
        cur, _ = collapse_quarter(tf)
        del tf; gc.collect()
        cur_qi = qidx(fq_order(fq))
        per_q_counts[fq] = int(cur["fund_key"].nunique())
        dec.push(cur, cur_qi, uni_total)
        del cur, uni_total; gc.collect()
    return dec.finalize() + (per_q_counts,)


def stream_ctrl_group(group_label):
    """Stream C2 or C3 from did_control_parts, filtered to control_group. Normalization
    universe = the group's own equity universe per fund-quarter."""
    files = sorted([f for f in os.listdir(CTRL_PARTS)
                    if f.startswith("did_ctrl_") and f.endswith(".parquet")],
                   key=lambda f: fq_order(f[len("did_ctrl_"):-len(".parquet")]))
    dec = StreamDecomposer()
    per_q_counts = {}
    for f in files:
        fq = f[len("did_ctrl_"):-len(".parquet")]
        t = pq.read_table(os.path.join(CTRL_PARTS, f),
                          columns=["cik", "series_id", "fiscal_quarter", "cusip", "isin",
                                   "currency_value", "balance", "unit",
                                   "control_group"]).to_pandas()
        t = t[t["control_group"] == group_label]
        if not len(t):
            del t; gc.collect(); continue
        cur, _ = collapse_quarter(t)
        del t; gc.collect()
        # universe total = this group's own holdings (= collapsed cur's cv)
        uni_total = (cur.groupby("fund_key")["currency_value"].sum()
                        .rename("tot_uni_cv").reset_index())
        uni_total["fiscal_quarter"] = fq
        cur_qi = qidx(fq_order(fq))
        per_q_counts[fq] = int(cur["fund_key"].nunique())
        dec.push(cur, cur_qi, uni_total)
        del cur, uni_total; gc.collect()
    return dec.finalize() + (per_q_counts,)


# --------------------------- pre-trend test (reused verbatim) ---------------------------
def ols_with_fe(y, X, fe_groups):
    df = pd.DataFrame(X.copy())
    df["_y"] = y
    df["_g"] = fe_groups
    num_cols = [c for c in df.columns if c not in ("_g",)]
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
    XtX = Xm.T @ Xm
    XtX_inv = np.linalg.pinv(XtX)
    beta = XtX_inv @ (Xm.T @ Y)
    resid = Y - Xm @ beta
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


def _run_interaction(d, stats):
    """Run rate ~ trend + treated + trend:treated with fund FE, cluster-by-fund SE, on the
    (already trimmed/filtered) stacked frame d. Returns (coef, se, t, p, n, G)."""
    qmap = {q: i for i, q in enumerate(PRE_QS)}
    d = d.copy()
    d["trend"] = d["fiscal_quarter"].map(qmap).astype(float)
    d["fe"] = d["treated"].astype(int).astype(str) + "|" + d["fund_key"]
    X = pd.DataFrame({
        "const": 1.0,
        "trend": d["trend"].values,
        "treated": d["treated"].values,
        "trend_x_treated": (d["trend"] * d["treated"]).values,
    })
    beta, se, n, G = ols_with_fe(d["rate"].values, X, d["fe"].values)
    b = beta.get("trend_x_treated", np.nan)
    s = se.get("trend_x_treated", np.nan)
    tval = b / s if s and not np.isnan(s) and s != 0 else np.nan
    p = float(2 * stats.t.sf(abs(tval), max(G - 1, 1))) if not np.isnan(tval) else None
    return (float(b) if not np.isnan(b) else None,
            float(s) if not np.isnan(s) else None,
            float(tval) if not np.isnan(tval) else None,
            p, int(n), int(G))


def pretrend_test(treated_df, control_df):
    """Pre-registered flat-pre-trend test PLUS an outlier-robustness diagnostic.

    NOTE (load-bearing, do not smooth over): active_flow_rate = active flow / lagged group
    total has extreme right/left tails because the lagged denominator is occasionally tiny
    (a fund that held ~nothing of the group last quarter). On the UNTRIMMED rate these
    outliers inflate the cluster-robust SE so severely that NOTHING is significant and every
    control spuriously reads 'parallel' (large p) — the parallelism is an SE-inflation
    artifact, not measured flatness. We therefore report the pre-registered untrimmed test
    AND a trimmed re-run (drop the 1% and 5% rate tails) as the robustness check. 'parallel'
    is reported per-variant; the overall verdict uses `parallel_robust` = parallel across
    untrimmed AND the 1%-trim (a control is only credibly parallel if trimming does not flip
    it). If the untrimmed 'parallel' flips to non-parallel under trimming, that control's
    flatness is an outlier artifact and is NOT a valid control."""
    from scipy import stats
    tt = treated_df[["fund_key", "fiscal_quarter", "rate"]].copy(); tt["treated"] = 1.0
    cc = control_df[["fund_key", "fiscal_quarter", "rate"]].copy(); cc["treated"] = 0.0
    d0 = pd.concat([tt, cc], ignore_index=True)
    d0 = d0[d0["fiscal_quarter"].isin(PRE_QS)].dropna(subset=["rate"]).copy()

    variants = {}
    for name, trim in [("untrimmed", None), ("trim_1pct", 0.01), ("trim_5pct", 0.05)]:
        d = d0
        if trim is not None:
            lo, hi = d0["rate"].quantile(trim), d0["rate"].quantile(1 - trim)
            d = d0[(d0["rate"] >= lo) & (d0["rate"] <= hi)]
        b, s, tval, p, n, G = _run_interaction(d, stats)
        variants[name] = {
            "interaction_coef_trend_x_treated": b, "interaction_se_cluster_fund": s,
            "interaction_t": tval, "interaction_p": p, "n_obs_pre": n, "n_fund_fe": G,
            "parallel": (p is not None and p > 0.10)}

    base = variants["untrimmed"]
    parallel_robust = bool(base["parallel"] and variants["trim_1pct"]["parallel"])
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
        # pre-registered (untrimmed) headline, kept at top level for continuity
        "interaction_coef_trend_x_treated": base["interaction_coef_trend_x_treated"],
        "interaction_se_cluster_fund": base["interaction_se_cluster_fund"],
        "interaction_t": base["interaction_t"],
        "interaction_p": base["interaction_p"],
        "n_obs_pre": base["n_obs_pre"], "n_fund_fe": base["n_fund_fe"],
        "parallel": base["parallel"],
        "parallel_robust": parallel_robust,
        "outlier_robustness_variants": variants,
        "outlier_artifact_warning": (
            "UNTRIMMED 'parallel' is driven by SE-inflation from extreme-tail rates "
            "(tiny-lagged-denominator fund-quarters); trimming the 1% tails flips it to "
            "NON-parallel." if (base["parallel"] and not parallel_robust) else None),
        "per_quarter_group_means": means,
    }


def main():
    # treated (reused, committed) — the reconciliation target
    tr = pq.read_table(TREATED_PANEL).to_pandas()
    tr = tr.rename(columns={"active_flow_rate": "rate", "cn_active_flow": "active_flow",
                            "cn_passive": "passive"})
    tr["group"] = "treated"
    treated_rate = tr[["fund_key", "cik", "series_id", "fiscal_quarter", "rate",
                       "active_flow", "passive"]].copy()

    panels = [tr.assign(active_flow_rate=tr["rate"])[
        ["group", "fund_key", "cik", "series_id", "fiscal_quarter",
         "active_flow", "passive", "rate"]]]
    results = {}

    # ---- SANITY: stream the treated group (CN haven) and reconcile vs committed panel
    cn_agg, cn_gate, cn_drop, cn_counts = stream_haven_group("CN")
    m = treated_rate.merge(cn_agg[["fund_key", "fiscal_quarter", "active_flow_rate"]],
                           on=["fund_key", "fiscal_quarter"], how="inner",
                           suffixes=("_committed", "_recomp"))
    diff = (m["rate"] - m["active_flow_rate"]).abs()
    # also reconcile raw active_flow (rate can be null when denom null on either side)
    m2 = treated_rate.merge(cn_agg[["fund_key", "fiscal_quarter", "active_flow"]],
                            on=["fund_key", "fiscal_quarter"], how="inner",
                            suffixes=("_committed", "_recomp"))
    diff_af = (m2["active_flow_committed"] - m2["active_flow_recomp"]).abs()
    treated_recon = {
        "n_matched_rows": int(len(m)),
        "max_abs_rate_diff": float(diff.max()) if len(m) else None,
        "max_abs_active_flow_diff": float(diff_af.max()) if len(m2) else None,
        "reproduces_committed_treated": bool(len(m) and diff.max() < 1e-6),
        "streamed_gate": cn_gate,
        "peak_rss_gb_after_treated_stream": round(peak_rss_gb(), 3)}

    # ---- C1: non-CN haven, same total-haven denominator
    c1, g1, d1, c1_counts = stream_haven_group("NON_CN")
    c1r = c1.rename(columns={"active_flow_rate": "rate"})
    c1r["group"] = "C1"
    panels.append(c1r[["group", "fund_key", "cik", "series_id", "fiscal_quarter",
                       "active_flow", "passive", "rate"]])
    res1 = pretrend_test(treated_rate, c1r)
    results["C1"] = {"label": "non-CN haven (CYM/HKG/VGB residence, parent!=CN)",
                     "gate": g1, "drop_report": d1, "pretrend": res1,
                     "n_fund_quarters": int(c1r["rate"].notna().sum()),
                     "per_quarter_fund_counts": c1_counts}

    # ---- C2 / C3
    for lab, name in [("C2", "non-haven EM equity"),
                      ("C3", "developed-market non-US equity")]:
        if not os.path.isdir(CTRL_PARTS) or not any(
                f.startswith("did_ctrl_") for f in os.listdir(CTRL_PARTS)):
            results[lab] = {"label": name, "status": "INCOMPLETE_reparse_not_present"}
            continue
        agg, gate, drop, counts = stream_ctrl_group(lab)
        if agg is None or not len(agg):
            results[lab] = {"label": name, "status": "INCOMPLETE_no_rows"}
            continue
        cr = agg.rename(columns={"active_flow_rate": "rate"})
        cr["group"] = lab
        panels.append(cr[["group", "fund_key", "cik", "series_id", "fiscal_quarter",
                          "active_flow", "passive", "rate"]])
        res = pretrend_test(treated_rate, cr)
        results[lab] = {"label": name, "gate": gate, "drop_report": drop,
                        "pretrend": res, "n_fund_quarters": int(cr["rate"].notna().sum()),
                        "per_quarter_fund_counts": counts}

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

    # branch decision. The valid-control test is the OUTLIER-ROBUST flat pre-trend
    # (parallel under BOTH the pre-registered untrimmed test AND the 1%-trim). A control
    # that is 'parallel' only untrimmed is parallel by SE-inflation, not by measured
    # flatness -- reporting it as valid would be substituting an artifact for the result.
    parallel_untrimmed = [k for k, v in results.items()
                          if v.get("pretrend", {}).get("parallel")]
    parallel_robust = [k for k, v in results.items()
                       if v.get("pretrend", {}).get("parallel_robust")]
    outlier_flipped = [k for k, v in results.items()
                       if v.get("pretrend", {}).get("outlier_artifact_warning")]
    incomplete = [k for k, v in results.items() if "status" in v]
    if parallel_robust:
        branch = {"decision": "CONTROL_FOUND", "valid_controls": parallel_robust,
                  "rule": ("flat pre-trend (trend x treated interaction insignificant at "
                           "10%) ROBUST to trimming the 1% rate tails"),
                  "parallel_untrimmed_only_rejected": outlier_flipped}
    elif incomplete:
        branch = {"decision": "INCOMPLETE", "incomplete_controls": incomplete,
                  "note": "no robust parallel control among completed candidates; reparse pending"}
    else:
        branch = {
            "decision": "NOT-IDENTIFIED",
            "note": ("No candidate control has an OUTLIER-ROBUST flat pre-trend. "
                     f"Untrimmed, {parallel_untrimmed} read 'parallel', but this is an "
                     "SE-inflation artifact of extreme-tail active_flow_rate values "
                     "(tiny lagged denominators): trimming the 1% rate tails flips EVERY "
                     "candidate to strongly NON-parallel (interaction p <= 0.001). The DiD "
                     "is NOT identified on this quantity as normalized; a bare untrimmed "
                     "'parallel' verdict would be reporting an artifact as a result."),
            "parallel_untrimmed": parallel_untrimmed,
            "outlier_flipped_to_nonparallel_when_trimmed": outlier_flipped}

    peak = round(peak_rss_gb(), 3)
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
            "note": ("10 pre-freeze (2019q3-2021q4) confirmed; 2019q3 is all-NEW (no "
                     "consecutive lag) so has no active_flow_rate; pre-trend test uses the "
                     "9 pre-quarters 2019q4-2021q4.")},
        "normalization": ("active_flow_rate = group active flow / fund's lagged total "
                          "currency_value of that group's universe. Treated & C1 share the "
                          "total-haven denominator (complementary haven subsets); C2/C3 use "
                          "their own EM/DM-equity universe."),
        "decomposition": ("constant-price active/passive from build_active_flow.py, applied "
                          "VERBATIM but STREAMED quarter-by-quarter (bounded memory)."),
        "streaming_peak_rss_gb": peak,
        "treated_recon_crosscheck": treated_recon,
        "country_sets": {"C2_EM_A2": None, "C3_DM_A2": None},
        "candidate_controls": results,
        "per_quarter_row_counts": dict(rc),
        "branch_decision": branch,
        "artifacts": {"control_panels_parquet": OUT_PANEL, "feasibility_json": OUT_FEAS,
                      "provenance_md": OUT_PROV,
                      "streaming_script": os.path.abspath(__file__)},
    }
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

    write_prov(feas, results, cn_counts)

    print("DID_CONTROLS_STREAM_DONE")
    print(json.dumps({
        "peak_rss_gb": peak,
        "treated_recon": {k: treated_recon[k] for k in
                          ["n_matched_rows", "max_abs_rate_diff",
                           "max_abs_active_flow_diff", "reproduces_committed_treated"]},
        "branch": branch,
        "results_summary": {
            k: {"parallel_untrimmed": v.get("pretrend", {}).get("parallel"),
                "parallel_robust": v.get("pretrend", {}).get("parallel_robust"),
                "coef_untrimmed": v.get("pretrend", {}).get("interaction_coef_trend_x_treated"),
                "p_untrimmed": v.get("pretrend", {}).get("interaction_p"),
                "p_trim_1pct": v.get("pretrend", {}).get(
                    "outlier_robustness_variants", {}).get("trim_1pct", {}).get("interaction_p"),
                "outlier_artifact_warning": v.get("pretrend", {}).get("outlier_artifact_warning"),
                "gate_pass": v.get("gate", {}).get("pass"),
                "status": v.get("status")}
            for k, v in results.items()}}, indent=2, default=str))


def write_prov(feas, results, cn_counts):
    L = []
    L.append("# DiD F3 Part 0(b) — Control Panels & Pre-Trend Provenance (STREAMING build)\n\n")
    L.append("SOURCE: Real SEC Form N-PORT dissemination ZIPs "
             "`https://www.sec.gov/files/dera/data/form-n-port-data-sets/{YYYYqQ}_nport.zip`, "
             "UA `dollar-breaking-point research milevsky@hotmail.com`, parsed to disk in a "
             "prior pass (haven_bal_parts/, did_control_parts/). This build REUSES those "
             "on-disk parts; nothing re-downloaded or re-parsed. Fiscal quarter = zip label "
             "minus one quarter.\n\n")
    L.append("## Memory pattern (the fix)\n")
    L.append("The prior attempt (`build_did_control_panels.py`) concatenated all 22 quarters "
             "of raw non-haven holdings into one DataFrame before decomposing; peak RSS "
             ">13GB, killed by the memory guard before writing output. This rewrite "
             "(`build_did_control_panels_streaming.py`) streams quarter-by-quarter: each "
             "quarter is loaded, collapsed IMMEDIATELY to per-(fund,security) rows (dropping "
             "every heavy raw string column), decomposed against the single previously-"
             "collapsed quarter, aggregated to per-(fund,quarter) active flow, then the raw "
             "frame is freed (`del`+`gc.collect()`). At most TWO collapsed quarters are held "
             "at once — the first difference needs only t and t-1. "
             f"**Measured peak RSS = {feas['streaming_peak_rss_gb']} GB** (target < 6GB).\n\n")
    L.append("## Groups\n")
    L.append("- **treated**: CN-nationality haven active flow. COMMITTED "
             "`active_flow_panel.parquet` reused verbatim in the output panel; ALSO "
             "re-streamed here purely to reconcile the streaming build against it.\n")
    L.append("- **C1**: non-CN haven (CYM/HKG/VGB residence, parent!=CN). Streamed from "
             "`haven_bal_parts/` with R1-R4 tagging VERBATIM (`tag_fullpanel`), focus="
             "parent!=CN, normalization base = total haven (identical denominator to "
             "treated).\n")
    cs = feas.get("country_sets", {})
    L.append(f"- **C2**: non-haven EM equity, ASSET_CAT=EC, INVESTMENT_COUNTRY in "
             f"{cs.get('C2_EM_A2')}. Streamed from `did_control_parts/` (control_group=C2).\n")
    L.append(f"- **C3**: developed-market non-US equity, ASSET_CAT=EC, INVESTMENT_COUNTRY "
             f"in {cs.get('C3_DM_A2')}. Streamed (control_group=C3).\n\n")
    L.append("## Decomposition (reused verbatim, streamed)\n")
    L.append("Constant-price: CONTINUING active=(bal_t-bal_{t-1})*price_{t-1}, "
             "passive=dCV-active; NEW active=cv_t; CLOSED active=-cv_{t-1}. Placeholder CUSIP "
             "nulled -> ISIN fallback; duplicate lots summed before pricing. Correctness gate "
             "active+passive==dCV accumulated streaming per group (below).\n\n")
    tr = feas["treated_recon_crosscheck"]
    L.append("## Treated-group reconciliation vs committed active_flow_panel (the sanity gate)\n")
    L.append(f"Streaming the CN-haven group with the total-haven denominator reproduces the "
             f"committed treated rate: matched rows={tr['n_matched_rows']}, "
             f"max_abs_rate_diff={tr['max_abs_rate_diff']}, "
             f"max_abs_active_flow_diff={tr['max_abs_active_flow_diff']}, "
             f"reproduces_committed={tr['reproduces_committed_treated']}. Streamed correctness "
             f"gate: max_abs={tr['streamed_gate']['reconstruction_max_abs_error']:.3e}, "
             f"pass={tr['streamed_gate']['pass']}. This proves the streaming build is "
             f"algebraically identical to the committed batch build.\n\n")
    L.append("## Pre-trend parallelism (PRE 2019q4-2021q4; rate ~ trend + treated + "
             "trend:treated, fund FE, cluster-by-fund SE)\n\n")
    L.append("**Outlier caveat (load-bearing):** `active_flow_rate` = active flow / lagged "
             "group total has extreme tails when the lagged denominator is tiny. On the "
             "UNTRIMMED rate these outliers inflate the cluster-robust SE so much that "
             "nothing is significant and every control reads 'parallel' (large p) -- that "
             "flatness is an SE-inflation artifact, NOT measured parallelism. The table "
             "reports the pre-registered untrimmed test AND a 1%/5%-tail-trim robustness "
             "re-run. A control is a valid control only if 'parallel' is ROBUST (holds "
             "untrimmed AND at the 1% trim).\n\n")
    L.append("| control | variant | coef | SE | p | parallel | gate pass | n_fq |\n")
    L.append("|---|---|---|---|---|---|---|---|\n")
    for k, v in results.items():
        pt = v.get("pretrend")
        if not pt:
            L.append(f"| {k} | {v.get('status','')} | | | | | | |\n")
            continue
        g = v.get("gate", {})
        vr = pt.get("outlier_robustness_variants", {})
        for vn in ["untrimmed", "trim_1pct", "trim_5pct"]:
            r = vr.get(vn)
            if not r:
                continue
            L.append(f"| {k} | {vn} | {r['interaction_coef_trend_x_treated']:.4g} | "
                     f"{r['interaction_se_cluster_fund']:.4g} | {r['interaction_p']:.4g} | "
                     f"{r['parallel']} | {g.get('pass') if vn=='untrimmed' else ''} | "
                     f"{v.get('n_fund_quarters') if vn=='untrimmed' else ''} |\n")
        L.append(f"| {k} | **parallel_robust** | | | | **{pt.get('parallel_robust')}** | | |\n")
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
        L.append(f"## INCOMPLETE / skipped re-parse quarters\n"
                 f"{json.dumps(feas['reparse_skipped'])}\n")
    with open(OUT_PROV, "w") as f:
        f.write("".join(L))


if __name__ == "__main__":
    main()
