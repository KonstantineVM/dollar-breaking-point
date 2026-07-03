#!/usr/bin/env python3
"""
ACTIVE-FLOW F3 TEST -- Part 0 FEASIBILITY.

Confirm from REAL N-PORT data (not the schema alone) whether the haven-CN holdings
carry a populated, positive BALANCE with a usable UNIT, so that a constant-price
active/passive decomposition (branch A) is buildable.

Method:
  - Download 1-2 representative fiscal quarters (a crisis quarter fiscal 2022q1 =
    zip 2022q2, plus fiscal 2021q3 = zip 2021q4) via the SAME machinery as
    build_us_china_panel.build_quarter, but extract BALANCE/UNIT/OTHER_UNIT_DESC too.
  - Restrict to the CN-nationality haven set by merging parent_nationality=CN from the
    committed tagged panel on the stable key (fiscal_quarter, cik, series_id, cusip)
    with an isin fallback. (Part 1 re-applies R1-R4 verbatim; here we only need to
    identify the CN-nationality rows to measure balance population on them.)
  - MEASURE for haven-CN holdings: fraction with populated positive BALANCE (by count
    and by currency_value), the UNIT distribution, and whether
    price = currency_value/balance is finite and positive.
  - Emit the branch decision (A/B/C) to build/audit/active_flow_feasibility.json.
"""
import os, sys, json, zipfile, subprocess, gc, shutil
import pandas as pd
import numpy as np
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/user/dollar-breaking-point"
sys.path.insert(0, HERE)
import build_us_china_panel as B

TAGGED = os.path.join(ROOT, "build/data/nport/panel_crosswalk_tagged_full.parquet")
OUT = os.path.join(ROOT, "build/audit/active_flow_feasibility.json")

# zip quarters to test: 2022q2 (fiscal 2022q1, crisis) and 2021q4 (fiscal 2021q3)
TEST_ZIPS = ["2022q2", "2021q4"]


def extract_holdings_with_balance(zip_q, work):
    """Reuse B.download_zip + B.extract_tables, but read BALANCE/UNIT too and filter
    EARLY to haven+CN residence (same TARGET_A2 set the panel used)."""
    qdir = os.path.join(work, f"q_{zip_q}")
    zip_path = os.path.join(work, f"{zip_q}_nport.zip")
    url, zip_bytes = B.download_zip(zip_q, zip_path)
    # extract only FUND_REPORTED_HOLDING for feasibility (we merge CN set from tagged panel)
    os.makedirs(qdir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        if "FUND_REPORTED_HOLDING.tsv" not in names:
            raise RuntimeError("FUND_REPORTED_HOLDING.tsv missing")
        z.extract("FUND_REPORTED_HOLDING.tsv", qdir)
        # also need REGISTRANT + FUND_REPORTED_INFO to attach cik/series_id for the merge
        for t in ("REGISTRANT.tsv", "FUND_REPORTED_INFO.tsv"):
            if t in names:
                z.extract(t, qdir)
    fiscal_q = B.previous_quarter(zip_q)

    hold_cols = ["ACCESSION_NUMBER", "HOLDING_ID", "ISSUER_NAME", "ISSUER_LEI",
                 "ISSUER_CUSIP", "CURRENCY_CODE", "CURRENCY_VALUE", "PERCENTAGE",
                 "ASSET_CAT", "ISSUER_TYPE", "INVESTMENT_COUNTRY",
                 "BALANCE", "UNIT", "OTHER_UNIT_DESC"]
    parts = []
    reader = pd.read_csv(os.path.join(qdir, "FUND_REPORTED_HOLDING.tsv"),
                         sep="\t", dtype=str, usecols=hold_cols,
                         keep_default_na=False, na_values=[], chunksize=200_000,
                         low_memory=False)
    total_rows = 0
    for ch in reader:
        total_rows += len(ch)
        ch = ch[ch["INVESTMENT_COUNTRY"].isin(B.TARGET_A2)]
        if len(ch):
            parts.append(ch)
    h = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=hold_cols)
    del parts; gc.collect()

    keep_acc = set(h["ACCESSION_NUMBER"])
    # attach cik + series_id
    reg = pd.read_csv(os.path.join(qdir, "REGISTRANT.tsv"), sep="\t", dtype=str,
                      usecols=["ACCESSION_NUMBER", "CIK"],
                      na_values=B.NA_VALUES, low_memory=False)
    reg = reg[reg["ACCESSION_NUMBER"].isin(keep_acc)]
    fi = pd.read_csv(os.path.join(qdir, "FUND_REPORTED_INFO.tsv"), sep="\t", dtype=str,
                     usecols=["ACCESSION_NUMBER", "SERIES_ID"],
                     na_values=B.NA_VALUES, low_memory=False)
    fi = fi[fi["ACCESSION_NUMBER"].isin(keep_acc)]

    h = h.merge(reg, on="ACCESSION_NUMBER", how="left")
    h = h.merge(fi, on="ACCESSION_NUMBER", how="left")
    h["fiscal_quarter"] = fiscal_q

    shutil.rmtree(qdir, ignore_errors=True)
    os.remove(zip_path)
    return h, {"zip_quarter": zip_q, "fiscal_quarter": fiscal_q, "zip_url": url,
               "zip_bytes": zip_bytes, "total_holdings_in_quarter": total_rows,
               "target_residence_rows": int(len(h))}


def measure(h, cn_keys_cusip, cn_keys_isin, fiscal_q):
    """h: haven+CN-residence holdings this quarter with BALANCE/UNIT.
    cn_keys_*: sets of (cik, series_id, cusip)/(cik, series_id, isin) that are
    parent_nationality==CN in the committed tagged panel for this fiscal quarter."""
    h = h.copy()
    h["ISSUER_CUSIP"] = h["ISSUER_CUSIP"].replace(B.NA_VALUES, "")
    h["cv"] = pd.to_numeric(h["CURRENCY_VALUE"], errors="coerce")
    h["bal"] = pd.to_numeric(h["BALANCE"], errors="coerce")
    h["cik"] = h["CIK"].fillna("")
    h["sid"] = h["SERIES_ID"].fillna("")

    # build CN-nationality mask by matching the committed tagged CN key set
    def is_cn(r):
        k1 = (r["cik"], r["sid"], r["ISSUER_CUSIP"])
        if r["ISSUER_CUSIP"] and k1 in cn_keys_cusip:
            return True
        return False
    # vectorized cusip match
    hk = list(zip(h["cik"], h["sid"], h["ISSUER_CUSIP"]))
    cn_mask = pd.Series([bool(c and (a, b, c) in cn_keys_cusip) for (a, b, c) in hk],
                        index=h.index, dtype=bool)

    cn = h[cn_mask].copy()

    def rate(sub, wcol=None):
        n = len(sub)
        if n == 0:
            return {"n": 0}
        bal = sub["bal"].to_numpy(dtype=float)
        cv = sub["cv"].to_numpy(dtype=float)
        cv_ok = np.isfinite(cv)
        pos = np.isfinite(bal) & (bal > 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            price = np.where(bal > 0, cv / bal, np.nan)
        price_ok = np.isfinite(price) & (price > 0)
        tot_v = float(np.abs(cv[cv_ok]).sum())
        pos_v = float(np.abs(cv[pos & cv_ok]).sum())
        priceok_v = float(np.abs(cv[price_ok & cv_ok]).sum())
        pr = price[price_ok]
        return {
            "n": int(n),
            "n_balance_positive": int(pos.sum()),
            "frac_balance_positive_by_count": round(float(pos.mean()), 6),
            "total_abs_currency_value": tot_v,
            "abs_value_balance_positive": pos_v,
            "frac_balance_positive_by_value": round(pos_v / tot_v, 6) if tot_v else None,
            "n_price_finite_positive": int(price_ok.sum()),
            "abs_value_price_ok": priceok_v,
            "frac_price_ok_by_value": round(priceok_v / tot_v, 6) if tot_v else None,
            "price_p50": round(float(np.median(pr)), 6) if pr.size else None,
            "price_p05": round(float(np.percentile(pr, 5)), 6) if pr.size else None,
            "price_p95": round(float(np.percentile(pr, 95)), 6) if pr.size else None,
        }

    unit_mix = (cn.assign(u=cn["UNIT"].replace("", "<blank>"))
                  .groupby("u")
                  .agg(n=("cv", "size"), abs_val=("cv", lambda s: float(s.abs().sum())))
                  .sort_values("abs_val", ascending=False))
    unit_mix_d = [{"unit": u, "n": int(r["n"]), "abs_currency_value": r["abs_val"]}
                  for u, r in unit_mix.iterrows()]

    return {
        "fiscal_quarter": fiscal_q,
        "haven_all_residence_n": int(len(h)),
        "haven_cn_nationality_n": int(len(cn)),
        "cn_balance_stats": rate(cn),
        "cn_unit_mix": unit_mix_d,
        "all_haven_balance_stats": rate(h),
    }


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-0/-home-user-dollar-breaking-point/060d2c58-c106-5eed-9b8f-e9daf06281e7/scratchpad/af_work"
    os.makedirs(work, exist_ok=True)

    # load committed tagged panel CN key sets per fiscal quarter
    t = pq.read_table(TAGGED, columns=["fiscal_quarter", "cik", "series_id",
                                       "cusip", "isin", "parent_nationality"])
    df = t.to_pandas()
    cn = df[df["parent_nationality"] == "CN"]
    cn_by_q_cusip = {}
    cn_by_q_isin = {}
    for fq, g in cn.groupby("fiscal_quarter"):
        cn_by_q_cusip[fq] = set(
            (str(a), str(b), str(c)) for a, b, c in
            zip(g["cik"].fillna(""), g["series_id"].fillna(""), g["cusip"].fillna(""))
            if c and str(c) != "")
        cn_by_q_isin[fq] = set(
            (str(a), str(b), str(c)) for a, b, c in
            zip(g["cik"].fillna(""), g["series_id"].fillna(""), g["isin"].fillna(""))
            if c and str(c) != "")

    per_q = []
    metas = []
    for zq in TEST_ZIPS:
        print(f"[feas] {zq} ...", flush=True)
        h, meta = extract_holdings_with_balance(zq, work)
        metas.append(meta)
        fq = meta["fiscal_quarter"]
        m = measure(h, cn_by_q_cusip.get(fq, set()), cn_by_q_isin.get(fq, set()), fq)
        per_q.append(m)
        print(json.dumps(m, indent=2), flush=True)
        del h; gc.collect()

    # branch decision: aggregate CN value-weighted balance-positive fraction across tested quarters
    tot_v = sum(q["cn_balance_stats"].get("total_abs_currency_value", 0) or 0 for q in per_q)
    pos_v = sum(q["cn_balance_stats"].get("abs_value_balance_positive", 0) or 0 for q in per_q)
    priceok_v = sum(q["cn_balance_stats"].get("abs_value_price_ok", 0) or 0 for q in per_q)
    frac_pos = (pos_v / tot_v) if tot_v else 0.0
    frac_price_ok = (priceok_v / tot_v) if tot_v else 0.0

    if frac_pos >= 0.90:
        branch = "A"
        branch_reason = (f"BALANCE populated+positive for {frac_pos:.4f} of haven-CN "
                         f"currency_value across tested quarters (>=0.90). Constant-price "
                         f"decomposition buildable DIRECTLY.")
    elif frac_pos >= 0.50:
        branch = "A-PARTIAL"
        branch_reason = (f"BALANCE populated+positive for {frac_pos:.4f} of haven-CN value "
                         f"(0.50-0.90). Branch A buildable for the populated majority; "
                         f"non-decomposable rows dropped and value share reported.")
    else:
        branch = "B-OR-C"
        branch_reason = (f"BALANCE populated+positive for only {frac_pos:.4f} of haven-CN "
                         f"value (<0.50). Direct branch A not supported; evaluate B "
                         f"(valuation-strip via total return) or terminal C.")

    out = {
        "task": "ACTIVE-FLOW F3 TEST Part 0 feasibility",
        "source": "SEC N-PORT dissemination ZIPs FUND_REPORTED_HOLDING structured data",
        "tested_zip_quarters": TEST_ZIPS,
        "cn_nationality_set_source": ("parent_nationality==CN merged from committed "
                                      "panel_crosswalk_tagged_full.parquet on "
                                      "(cik, series_id, cusip)"),
        "per_quarter_meta": metas,
        "per_quarter_measurements": per_q,
        "aggregate_cn_value_frac_balance_positive": round(frac_pos, 6),
        "aggregate_cn_value_frac_price_ok": round(frac_price_ok, 6),
        "branch": branch,
        "branch_reason": branch_reason,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print("FEASIBILITY_DONE", OUT, "branch=", branch, flush=True)


if __name__ == "__main__":
    main()
