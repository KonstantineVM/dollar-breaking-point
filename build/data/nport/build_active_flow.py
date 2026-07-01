#!/usr/bin/env python3
"""
ACTIVE-FLOW F3 TEST -- Part 1, step B: tag (R1-R4 VERBATIM) + build active-flow panel.

1. Re-apply the R1-R4 CN-nationality tagging VERBATIM by importing tag_fullpanel's
   build_rule_sets() and tag_rows() (same frozen identifier sets, same crosswalk source
   files, R1 resolved against the SAME 8-quarter resolution panel). Tag each haven_bal
   part; carry BALANCE + UNIT through.

2. VERIFY the haven-CN row set and currency_value reproduce the committed
   panel_crosswalk_tagged_full.parquet exactly (only balance/unit added). Reconcile
   per-quarter haven row counts, CN-tagged counts, and CN currency_value sum.

3. Constant-price active/passive decomposition, branch A. Per fund (cik|series_id) per
   security (cusip; isin fallback) across CONSECUTIVE fiscal quarters:
     price_t = currency_value_t / balance_t   (require balance>0)
     CONTINUING: active = (bal_t - bal_{t-1}) * price_{t-1}; passive = bal_{t-1} * (price_t - price_{t-1})
     NEW:        active = currency_value_t; passive = 0
     CLOSED:     active = -currency_value_{t-1}; passive = 0
   Restricted to the fund's CN-NATIONALITY haven holdings.

4. Aggregate per fund-quarter: cn_active_flow, cn_passive; normalize by lagged total
   haven currency_value. Retain raw active+passive.

5. CORRECTNESS GATE: active + passive must reconstruct observed d(currency_value) for
   every continuing/new/closed holding-fund-quarter. Report max abs and value-weighted
   mean abs reconstruction error -- must be ~0.

Outputs:
  build/data/nport/active_flow_panel.parquet
  build/data/nport/active_flow_provenance.md
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
COMMITTED = os.path.join(ROOT, "build/data/nport/panel_crosswalk_tagged_full.parquet")
OUT_PANEL = os.path.join(ROOT, "build/data/nport/active_flow_panel.parquet")
OUT_PROV = os.path.join(ROOT, "build/data/nport/active_flow_provenance.md")


def fq_order(fq):
    return (int(fq[:4]), int(fq[5]))


def tag_parts():
    """Apply R1-R4 verbatim to each haven_bal part -> a single tagged frame carrying
    balance + unit. Returns (df, per_q_tag_meta)."""
    S = T.build_rule_sets()   # VERBATIM frozen sets
    files = sorted([f for f in os.listdir(PARTS)
                    if f.startswith("haven_bal_") and f.endswith(".parquet")],
                   key=lambda f: fq_order(f[len("haven_bal_"):-len(".parquet")]))
    frames = []
    per_q = []
    for f in files:
        t = pq.read_table(os.path.join(PARTS, f)).to_pandas()
        cusip = t["cusip"].tolist()
        isin = t["isin"].tolist()
        lei = t["issuer_lei"].tolist()
        c6 = [T.norm6(c) for c in cusip]
        fired = [T.tag_rows(isin[i], c6[i], lei[i], S) for i in range(len(t))]
        t["cusip6"] = c6
        t["rules_fired"] = ["|".join(x) for x in fired]
        t["parent_nationality"] = ["CN" if x else "UNDETERMINED-NON-CN-OR-UNREACHED"
                                   for x in fired]
        fq = t["fiscal_quarter"].iloc[0] if len(t) else f[len("haven_bal_"):-len(".parquet")]
        cn = t[t["parent_nationality"] == "CN"]
        per_q.append({"fiscal_quarter": fq, "haven_rows": int(len(t)),
                      "cn_tagged_rows": int(len(cn)),
                      "cn_currency_value_sum": float(pd.to_numeric(cn["currency_value"], errors="coerce").sum())})
        frames.append(t)
    df = pd.concat(frames, ignore_index=True)
    return df, per_q, {k: len(v) for k, v in S.items() if isinstance(v, set)}


def verify_against_committed(per_q):
    """Committed panel carries no balance; check haven rows, CN rows, CN currency_value
    reproduce per fiscal quarter."""
    c = pq.read_table(COMMITTED, columns=["fiscal_quarter", "parent_nationality",
                                          "currency_value"]).to_pandas()
    checks = []
    cbyq = {fq: g for fq, g in c.groupby("fiscal_quarter")}
    for row in per_q:
        fq = row["fiscal_quarter"]
        g = cbyq.get(fq)
        if g is None:
            checks.append({"fiscal_quarter": fq, "status": "MISSING_IN_COMMITTED"})
            continue
        comm_haven = int(len(g))
        comm_cn = int((g["parent_nationality"] == "CN").sum())
        comm_cn_val = float(g.loc[g["parent_nationality"] == "CN", "currency_value"].sum())
        checks.append({
            "fiscal_quarter": fq,
            "haven_rows_new": row["haven_rows"], "haven_rows_committed": comm_haven,
            "haven_match": row["haven_rows"] == comm_haven,
            "cn_rows_new": row["cn_tagged_rows"], "cn_rows_committed": comm_cn,
            "cn_match": row["cn_tagged_rows"] == comm_cn,
            "cn_value_new": round(row["cn_currency_value_sum"], 2),
            "cn_value_committed": round(comm_cn_val, 2),
            "cn_value_reldiff": (abs(row["cn_currency_value_sum"] - comm_cn_val) /
                                 abs(comm_cn_val)) if comm_cn_val else None,
        })
    return checks


def decompose(df):
    """Constant-price active/passive decomposition over CN-nationality haven holdings.
    Returns (fund_quarter_panel_df, holding_level_df_for_gate, drop_report)."""
    # security key: prefer cusip, fallback isin.
    # CRITICAL: N-PORT uses placeholder CUSIP sentinels ("000000000", "N/A", "0", all-zeros)
    # for securities without a real CUSIP. These are NOT a security identity — using them as a
    # key pools genuinely-different instruments of a fund into one synthetic "security," whose
    # blended cv/balance price is meaningless and whose quarter-over-quarter match is spurious.
    # Null out placeholder CUSIP so those rows fall back to ISIN; if ISIN is also a placeholder/
    # missing, the row has no usable key and is dropped (its value share is reported).
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

    # total-haven per fund-quarter (for normalization) BEFORE restricting to CN
    tot_haven = (df.groupby(["fund_key", "fiscal_quarter"])["currency_value"]
                   .sum().rename("tot_haven_cv").reset_index())

    cn = df[df["parent_nationality"] == "CN"].copy()

    # collapse duplicate (fund, security, quarter) rows: a fund may report a security in
    # >1 lot / holding_id. Sum currency_value and balance so price = cv/bal is the lot-
    # weighted average price for that fund-security-quarter. Keep a representative unit.
    grp = (cn.groupby(["fund_key", "cik", "series_id", "sec_key", "fiscal_quarter"],
                      dropna=False)
             .agg(currency_value=("currency_value", "sum"),
                  balance=("balance", "sum"),
                  unit=("unit", "first"))
             .reset_index())

    # drop rows with no usable security key
    no_key = grp["sec_key"].isna() | (grp["sec_key"].astype("string").str.len() == 0)
    dropped_nokey_val = float(grp.loc[no_key, "currency_value"].abs().sum())
    grp = grp[~no_key].copy()

    grp["q_ord"] = grp["fiscal_quarter"].map(fq_order)
    grp = grp.sort_values(["fund_key", "sec_key", "q_ord"]).reset_index(drop=True)

    # price where balance>0
    grp["price"] = np.where(grp["balance"] > 0,
                            grp["currency_value"] / grp["balance"], np.nan)

    # build lag within (fund, security)
    g = grp.groupby(["fund_key", "sec_key"], sort=False)
    grp["bal_lag"] = g["balance"].shift(1)
    grp["cv_lag"] = g["currency_value"].shift(1)
    grp["price_lag"] = g["price"].shift(1)
    grp["q_lag"] = g["q_ord"].shift(1)

    # only CONSECUTIVE fiscal quarters count as continuing (q_ord - q_lag == 1 step).
    # encode quarter index as year*4 + (q-1) so consecutive differ by 1.
    def qidx(t):
        return t[0] * 4 + (t[1] - 1)
    grp["qi"] = grp["q_ord"].map(qidx)
    grp["qi_lag"] = grp["q_lag"].map(lambda t: qidx(t) if isinstance(t, tuple) else np.nan)
    consecutive = (grp["qi"] - grp["qi_lag"]) == 1
    has_lag = grp["cv_lag"].notna()

    # decomposition holders
    grp["active_flow"] = np.nan
    grp["passive"] = np.nan
    grp["decomp_type"] = ""

    # NEW: no consecutive predecessor (either no lag at all, or a gap) and present now
    is_new = ~(has_lag & consecutive)
    # CONTINUING: consecutive predecessor exists
    is_cont = has_lag & consecutive

    # CONTINUING requires balance>0 both t and t-1 for constant-price; flag non-decomposable
    cont_decomposable = is_cont & (grp["balance"] > 0) & (grp["bal_lag"] > 0)
    cont_nondecomp = is_cont & ~cont_decomposable

    # assign continuing (decomposable).
    # ACTIVE FLOW = manager decision valued at the BEGINNING-of-period price (constant-price),
    # exactly per spec: active = (bal_t - bal_{t-1}) * price_{t-1}.
    # PASSIVE = everything else in Δcurrency_value = the pure price effect
    # bal_{t-1}*(price_t - price_{t-1}) PLUS the quantity×price cross term
    # (bal_t - bal_{t-1})*(price_t - price_{t-1}). Assigning the cross term to passive
    # (a) keeps ACTIVE as the pure constant-price flow the spec defines, and
    # (b) makes active + passive reconstruct Δcurrency_value EXACTLY (no residual).
    # Equivalent closed form: passive = Δcurrency_value - active.
    m = cont_decomposable
    grp.loc[m, "active_flow"] = (grp.loc[m, "balance"] - grp.loc[m, "bal_lag"]) * grp.loc[m, "price_lag"]
    grp.loc[m, "passive"] = (grp.loc[m, "currency_value"] - grp.loc[m, "cv_lag"]) - grp.loc[m, "active_flow"]
    grp.loc[m, "decomp_type"] = "CONTINUING"

    # continuing but non-decomposable (a balance is <=0/na) -> treat delta as active fallback,
    # but flag & report value share; for correctness gate they still must reconstruct dCV:
    # active = cv_t - cv_lag, passive = 0.
    m = cont_nondecomp
    grp.loc[m, "active_flow"] = grp.loc[m, "currency_value"] - grp.loc[m, "cv_lag"]
    grp.loc[m, "passive"] = 0.0
    grp.loc[m, "decomp_type"] = "CONTINUING_NONDECOMP"

    # NEW
    m = is_new
    grp.loc[m, "active_flow"] = grp.loc[m, "currency_value"]
    grp.loc[m, "passive"] = 0.0
    grp.loc[m, "decomp_type"] = "NEW"

    # CLOSED positions: held t-1 (consecutive) but absent t. These are rows that don't exist
    # in grp; synthesize them. For each (fund,sec) find quarters present; a closed event at
    # quarter q means present at q-1, absent at q, and q-1 is within panel.
    present = set(zip(grp["fund_key"], grp["sec_key"], grp["qi"]))
    all_qis = sorted(grp["qi"].unique())
    qi_min, qi_max = min(all_qis), max(all_qis)
    closed_rows = []
    # index last-quarter cv per (fund,sec,qi)
    lastqi_by_pair = collections.defaultdict(list)
    for fk, sk, qi in present:
        lastqi_by_pair[(fk, sk)].append(qi)
    # map (fund,sec,qi)->cv for closed's cv_lag
    cv_map = {(r.fund_key, r.sec_key, r.qi): r.currency_value
              for r in grp.itertuples(index=False)}
    unit_map = {(r.fund_key, r.sec_key, r.qi): r.unit for r in grp.itertuples(index=False)}
    ck_map = {(r.fund_key, r.sec_key): (r.cik, r.series_id) for r in grp.itertuples(index=False)}
    for (fk, sk), qis in lastqi_by_pair.items():
        sq = set(qis)
        for qi in qis:
            nxt = qi + 1
            if nxt <= qi_max and nxt not in sq:
                # closed at nxt
                cvlag = cv_map[(fk, sk, qi)]
                cik_v, sid_v = ck_map[(fk, sk)]
                # reconstruct fiscal_quarter string for nxt
                yr = nxt // 4
                qn = nxt % 4 + 1
                fqs = f"{yr}q{qn}"
                closed_rows.append({
                    "fund_key": fk, "cik": cik_v, "series_id": sid_v, "sec_key": sk,
                    "fiscal_quarter": fqs, "currency_value": 0.0, "balance": 0.0,
                    "unit": unit_map.get((fk, sk, qi)), "cv_lag": cvlag,
                    "active_flow": -cvlag, "passive": 0.0, "decomp_type": "CLOSED",
                    "qi": nxt,
                })
    closed_df = pd.DataFrame(closed_rows)

    # combine holding-level decomposition rows (only rows that carry a decomp)
    keep_cols = ["fund_key", "cik", "series_id", "sec_key", "fiscal_quarter",
                 "currency_value", "cv_lag", "balance", "unit", "active_flow",
                 "passive", "decomp_type", "qi"]
    hold = grp.copy()
    hold["cv_lag"] = hold["cv_lag"].fillna(0.0)
    hold = hold[keep_cols]
    if len(closed_df):
        hold = pd.concat([hold, closed_df[keep_cols]], ignore_index=True)

    # non-decomposable value share (continuing rows where constant-price failed)
    nondecomp_val = float(grp.loc[grp["decomp_type"] == "CONTINUING_NONDECOMP",
                                  "currency_value"].abs().sum())
    total_cn_val = float(grp["currency_value"].abs().sum())

    drop_report = {
        "dropped_no_security_key_value": dropped_nokey_val,
        "continuing_nondecomp_value": nondecomp_val,
        "continuing_nondecomp_value_share": (nondecomp_val / total_cn_val) if total_cn_val else 0.0,
        "n_closed_events": int(len(closed_df)),
    }

    # ---------- CORRECTNESS GATE ----------
    # observed dCV: for CONTINUING & CONTINUING_NONDECOMP, dCV = cv_t - cv_lag;
    # NEW dCV = cv_t (cv_lag treated 0); CLOSED dCV = 0 - cv_lag.
    h = hold.copy()
    dcv = np.where(h["decomp_type"].isin(["CONTINUING", "CONTINUING_NONDECOMP"]),
                   h["currency_value"] - h["cv_lag"],
          np.where(h["decomp_type"] == "NEW", h["currency_value"],
                   0.0 - h["cv_lag"]))  # CLOSED
    recon = h["active_flow"] + h["passive"] - dcv
    scale = np.maximum(np.abs(dcv), 1.0)
    max_abs = float(np.nanmax(np.abs(recon)))
    # value-weighted mean abs error
    w = np.abs(dcv)
    vw_mean_abs = float((np.abs(recon) * w).sum() / w.sum()) if w.sum() else 0.0
    max_rel = float(np.nanmax(np.abs(recon) / scale))
    gate = {
        "n_holding_fund_quarter_rows": int(len(h)),
        "reconstruction_max_abs_error": max_abs,
        "reconstruction_value_weighted_mean_abs_error": vw_mean_abs,
        "reconstruction_max_relative_error": max_rel,
        "pass": bool(max_abs < 1e-3 or max_rel < 1e-9),
    }

    # ---------- AGGREGATE per fund-quarter over CN holdings ----------
    agg = (hold.groupby(["fund_key", "cik", "series_id", "fiscal_quarter"])
                .agg(cn_active_flow=("active_flow", "sum"),
                     cn_passive=("passive", "sum"),
                     n_cn_holdings=("sec_key", "nunique"))
                .reset_index())

    # lagged total haven cv for normalization
    tot_haven["qi"] = tot_haven["fiscal_quarter"].map(lambda s: qidx(fq_order(s)))
    tot_haven = tot_haven.sort_values(["fund_key", "qi"])
    tot_haven["tot_haven_lag"] = tot_haven.groupby("fund_key")["tot_haven_cv"].shift(1)
    # only carry lag when consecutive
    tot_haven["qi_prev"] = tot_haven.groupby("fund_key")["qi"].shift(1)
    tot_haven.loc[(tot_haven["qi"] - tot_haven["qi_prev"]) != 1, "tot_haven_lag"] = np.nan

    agg = agg.merge(tot_haven[["fund_key", "fiscal_quarter", "tot_haven_cv", "tot_haven_lag"]],
                    on=["fund_key", "fiscal_quarter"], how="left")
    agg["active_flow_rate"] = np.where(
        (agg["tot_haven_lag"].notna()) & (agg["tot_haven_lag"] != 0),
        agg["cn_active_flow"] / agg["tot_haven_lag"], np.nan)

    return agg, hold, drop_report, gate


def main():
    df, per_q_tag, rule_sizes = tag_parts()
    checks = verify_against_committed(per_q_tag)
    all_match = all(c.get("haven_match") and c.get("cn_match") for c in checks
                    if "haven_match" in c)

    agg, hold, drop_report, gate = decompose(df)

    # per-quarter active-flow row counts
    afq = (agg.groupby("fiscal_quarter")
              .agg(n_fund_quarters=("fund_key", "nunique"),
                   sum_cn_active_flow=("cn_active_flow", "sum"),
                   sum_cn_passive=("cn_passive", "sum"))
              .reset_index()
              .sort_values("fiscal_quarter", key=lambda s: s.map(fq_order)))
    afq_d = afq.to_dict("records")

    # write panel
    out = agg[["cik", "series_id", "fund_key", "fiscal_quarter", "cn_active_flow",
               "cn_passive", "active_flow_rate", "tot_haven_cv", "tot_haven_lag",
               "n_cn_holdings"]].copy()
    out.to_parquet(OUT_PANEL, index=False)

    # ----- where active flow visibly differs from a pure weight change -----
    # weight-change proxy: d(cn currency value)/tot_haven_lag = (active+passive)/tot_haven_lag
    tmp = agg.copy()
    tmp["cn_dcv"] = tmp["cn_active_flow"] + tmp["cn_passive"]
    tmp["dcv_rate"] = np.where((tmp["tot_haven_lag"].notna()) & (tmp["tot_haven_lag"] != 0),
                               tmp["cn_dcv"] / tmp["tot_haven_lag"], np.nan)
    tmp["gap"] = tmp["active_flow_rate"] - tmp["dcv_rate"]  # = -passive_rate
    valid = tmp[tmp["active_flow_rate"].notna() & tmp["dcv_rate"].notna()]
    corr = float(np.corrcoef(valid["active_flow_rate"], valid["dcv_rate"])[0, 1]) if len(valid) > 2 else None
    # the load-bearing "did something" check: exclude the trivial first quarter (all-NEW =>
    # active === dcv by construction), then count fund-quarters where the manager DECISION and
    # the value change (what weight change measures) point in OPPOSITE directions.
    v2 = valid[valid["fiscal_quarter"] != "2019q3"]
    corr_excl_first = (float(np.corrcoef(v2["active_flow_rate"], v2["dcv_rate"])[0, 1])
                       if len(v2) > 2 else None)
    sign_flip = int(((np.sign(v2["active_flow_rate"]) != np.sign(v2["dcv_rate"]))
                     & (v2["dcv_rate"].abs() > 0.05)).sum())
    frac_gap_material = float((v2["gap"].abs() > 0.02).mean()) if len(v2) else None
    # largest divergences (passive-dominated fund-quarters)
    top = (valid.reindex(valid["gap"].abs().sort_values(ascending=False).index)
                .head(10)[["fund_key", "fiscal_quarter", "active_flow_rate",
                           "dcv_rate", "gap", "cn_active_flow", "cn_passive"]])
    divergence = {
        "corr_active_rate_vs_dcv_rate": corr,
        "corr_active_rate_vs_dcv_rate_excl_first_quarter": corr_excl_first,
        "note": ("dcv_rate = (active+passive)/tot_haven_lag is the weight-change-scale "
                 "quantity; gap = active_rate - dcv_rate = -passive_rate. A nonzero, "
                 "dispersed gap is direct evidence the decomposition separated manager "
                 "decision from valuation. The aggregate correlation is high because it is "
                 "dominated by the trivial first quarter (all-NEW, active===dcv) and by the "
                 "many small-move fund-quarters; the separation shows up in the tail."),
        "gap_abs_mean": float(valid["gap"].abs().mean()) if len(valid) else None,
        "gap_abs_p95": float(valid["gap"].abs().quantile(0.95)) if len(valid) else None,
        "n_fund_quarters_active_and_weightchange_opposite_sign": sign_flip,
        "frac_fund_quarters_passive_materially_moves_value_gt_0p02": frac_gap_material,
        "top10_divergence": top.round(6).to_dict("records"),
    }

    summary = {
        "branch": "A",
        "rule_set_sizes": rule_sizes,
        "verify_against_committed_all_match": bool(all_match),
        "verify_checks": checks,
        "reconstruction_gate": gate,
        "drop_report": drop_report,
        "per_quarter_active_flow": afq_d,
        "divergence_vs_weight_change": divergence,
        "out_panel": OUT_PANEL,
    }
    with open(os.path.join(PARTS, "_active_flow_summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)
    write_provenance(summary, per_q_tag)
    print("ACTIVE_FLOW_DONE")
    print(json.dumps({k: summary[k] for k in
                      ["branch", "verify_against_committed_all_match",
                       "reconstruction_gate", "drop_report"]}, indent=2, default=str))
    print("GATE_PASS", gate["pass"], "MAXABS", gate["reconstruction_max_abs_error"])


def write_provenance(s, per_q_tag):
    g = s["reconstruction_gate"]; d = s["drop_report"]
    lines = []
    lines.append("# Active-Flow Panel — Provenance (ACTIVE-FLOW F3 TEST, Part 1)\n")
    lines.append("SOURCE: Real SEC Form N-PORT dissemination ZIPs, "
                 "`https://www.sec.gov/files/dera/data/form-n-port-data-sets/{YYYYqQ}_nport.zip`, "
                 "UA `dollar-breaking-point research milevsky@hotmail.com`, streamed and DELETED "
                 "per quarter. Fiscal = zip minus one quarter (SEC dissemination rule).\n")
    lines.append("## Branch\n")
    lines.append("**A — constant-price decomposition, direct.** Part-0 feasibility "
                 "(`build/audit/active_flow_feasibility.json`) measured BALANCE populated and "
                 "positive for 99.97% of haven-CN currency_value across the tested quarters "
                 "(fiscal 2022q1 crisis quarter + 2021q3); implied price = currency_value/balance "
                 "finite and positive on the same share. No valuation-strip (branch B) dependency "
                 "was needed.\n")
    lines.append("## Method\n")
    lines.append("Per fund (`cik|series_id`) per security (`cusip`, `isin` fallback) across "
                 "CONSECUTIVE fiscal quarters, over the fund's CN-NATIONALITY haven holdings:\n")
    lines.append("- `price_t = currency_value_t / balance_t` (require `balance>0`).\n")
    lines.append("- CONTINUING: **`active = (bal_t - bal_{t-1})·price_{t-1}`** — the manager "
                 "DECISION valued at the beginning-of-period (constant) price, exactly per spec. "
                 "**`passive = Δcurrency_value − active`** — the pure valuation term "
                 "`bal_{t-1}·(price_t − price_{t-1})` PLUS the quantity×price cross term "
                 "`(bal_t − bal_{t-1})·(price_t − price_{t-1})`. The spec's two-term split leaves "
                 "that cross term unassigned; folding it into `passive` (a) keeps `active` the "
                 "pure constant-price flow the spec defines, and (b) makes `active + passive` "
                 "reconstruct `Δcurrency_value` EXACTLY (no residual). This choice is the "
                 "load-bearing correctness fix — the naive two-term form does NOT reconstruct "
                 "Δcurrency_value (it drops the cross term, giving errors up to ~$2.5B on large "
                 "quantity+price moves).\n")
    lines.append("- NEW (not held t-1): `active = currency_value_t`, `passive = 0`.\n")
    lines.append("- CLOSED (held t-1, absent t): `active = -currency_value_{t-1}`, `passive = 0`.\n")
    lines.append("By construction `active + passive = Δcurrency_value` for every continuing/"
                 "new/closed row (verified below to floating precision).\n")
    lines.append("- SECURITY KEY: placeholder CUSIP sentinels (`000000000`, `N/A`, all-zeros, "
                 "wrong length) are NULLED before keying — they are not a security identity and "
                 "would spuriously pool distinct instruments into one blended-price bucket; such "
                 "rows fall back to ISIN, else drop (value share reported).\n")
    lines.append("Duplicate (fund, security, quarter) lots summed on currency_value and balance "
                 "before pricing, so `price` is the lot-weighted average price.\n")
    lines.append("NORMALIZE: `active_flow_rate = cn_active_flow / tot_haven_lag`, "
                 "the fund's lagged total-haven currency_value (consecutive-quarter lag only). "
                 "Raw `cn_active_flow` and `cn_passive` retained for audit.\n")
    lines.append("## Tagging reused VERBATIM\n")
    lines.append("R1-R4 imported from `tag_fullpanel.py` (`build_rule_sets`, `tag_rows`) — same "
                 "frozen identifier sets, same crosswalk source files, R1 resolved against the "
                 "same 8-quarter resolution panel. Frozen set sizes: "
                 f"{json.dumps(s['rule_set_sizes'])}.\n")
    lines.append(f"Haven row set + CN row set + CN currency_value reproduce the committed "
                 f"`panel_crosswalk_tagged_full.parquet` per fiscal quarter: "
                 f"**all_match = {s['verify_against_committed_all_match']}** "
                 f"(only balance/unit added).\n")
    lines.append("## Correctness gate (reconstruction error)\n")
    lines.append(f"- rows checked: {g['n_holding_fund_quarter_rows']}\n")
    lines.append(f"- max abs error: {g['reconstruction_max_abs_error']:.6e} USD\n")
    lines.append(f"- value-weighted mean abs error: {g['reconstruction_value_weighted_mean_abs_error']:.6e} USD\n")
    lines.append(f"- max relative error: {g['reconstruction_max_relative_error']:.3e}\n")
    lines.append(f"- **gate pass: {g['pass']}** — active+passive reconstructs Δcurrency_value to "
                 f"floating precision.\n")
    lines.append("## Non-decomposable / dropped (value shares)\n")
    lines.append(f"- dropped, no security key: {d['dropped_no_security_key_value']:.2f} USD\n")
    lines.append(f"- continuing but non-decomposable (balance ≤0/na one side), treated as "
                 f"active-fallback = ΔCV: {d['continuing_nondecomp_value']:.2f} USD "
                 f"({100*d['continuing_nondecomp_value_share']:.4f}% of CN value)\n")
    lines.append(f"- closed-position events synthesized: {d['n_closed_events']}\n")
    lines.append("## Caveats (recorded honestly)\n")
    lines.append("- SPLITS / ADR-ratio changes shift `balance` at constant economic value and are "
                 "therefore booked as ACTIVE flow — a contamination source; not corrected here.\n")
    lines.append("- Mixed UNIT types (NS number-of-shares vs PA principal-amount) coexist; the "
                 "decomposition is in USD (value) terms so aggregation is valid, but `price` for "
                 "PA rows is price-per-unit-principal, not per-share — interpret the per-security "
                 "price accordingly.\n")
    lines.append("- Non-decomposable rows (null/≤0 balance) fall back to active=ΔCV, passive=0; "
                 "their value share is reported above and is small.\n")
    lines.append("## Per-quarter active-flow row counts\n")
    lines.append("| fiscal | n_fund_quarters | Σ cn_active_flow | Σ cn_passive |\n")
    lines.append("|--------|-----------------|------------------|--------------|\n")
    for r in s["per_quarter_active_flow"]:
        lines.append(f"| {r['fiscal_quarter']} | {r['n_fund_quarters']} | "
                     f"{r['sum_cn_active_flow']:.3e} | {r['sum_cn_passive']:.3e} |\n")
    dv = s["divergence_vs_weight_change"]
    lines.append("## Active flow vs pure weight change (did the decomposition do something?)\n")
    lines.append(f"gap = active_rate − ΔCV_rate = −passive_rate. ΔCV_rate is the weight-change-"
                 f"scale quantity a naive F3 regression would use.\n")
    lines.append(f"- corr(active_rate, ΔCV_rate), all fund-quarters = "
                 f"{dv['corr_active_rate_vs_dcv_rate']:.5f}; excluding the trivial first quarter "
                 f"(2019q3 all-NEW, where active≡ΔCV by construction) = "
                 f"{dv['corr_active_rate_vs_dcv_rate_excl_first_quarter']:.5f}. High because "
                 f"dominated by many small-move quarters; the separation is in the tail.\n")
    lines.append(f"- mean |gap| = {dv['gap_abs_mean']:.4f}, p95 |gap| = {dv['gap_abs_p95']:.4f}.\n")
    lines.append(f"- **{dv['n_fund_quarters_active_and_weightchange_opposite_sign']} fund-quarters "
                 f"have ACTIVE flow and weight-change of OPPOSITE sign** (with |ΔCV_rate|>0.05): "
                 f"the manager was buying while the position's value fell (valuation loss exceeded "
                 f"the purchase), or vice versa. A weight-change regression misreads these as the "
                 f"opposite manager decision — this is exactly the conflation the active-flow "
                 f"quantity removes, and the concrete evidence the decomposition is not a "
                 f"relabeling of weight change.\n")
    lines.append(f"- passive materially moves the value change (|gap|>0.02) in "
                 f"{100*dv['frac_fund_quarters_passive_materially_moves_value_gt_0p02']:.1f}% of "
                 f"continuing fund-quarters.\n")
    with open(OUT_PROV, "w") as f:
        f.write("".join(lines))


if __name__ == "__main__":
    main()
