#!/usr/bin/env python3
"""
DiD F3 Part 0(b) RE-PARSE: extract C2 (EM equity) + C3 (DM equity) control-group
holdings from the 22 N-PORT dissemination quarters, with BALANCE + UNIT + CURRENCY_VALUE,
in ONE pass per quarter (split by country classification), then delete each ZIP.

Reuses build_us_china_panel.build_quarter machinery patterns (download, extract, merge)
but with a DIFFERENT country/asset filter:
  C2 EM-equity:  INVESTMENT_COUNTRY in EM_A2, ASSET_CAT == 'EC'
  C3 DM-equity:  INVESTMENT_COUNTRY in DM_A2, ASSET_CAT == 'EC'
BALANCE + UNIT extracted (needed for the constant-price decomposition, identical to treated).

Stream + DELETE each ZIP after parse. Writes per-quarter parquet parts under
haven_bal_parts-sibling dir did_control_parts/ (gitignored large intermediate).
"""
import os, sys, json, zipfile, subprocess, gc, shutil
import pandas as pd
import numpy as np

ROOT = "/home/user/dollar-breaking-point"
OUT_PARTS = os.path.join(ROOT, "build/data/nport/did_control_parts")
BASE_URL = "https://www.sec.gov/files/dera/data/form-n-port-data-sets"
EMAIL = "milevsky@hotmail.com"
UA = f"dollar-breaking-point research {EMAIL}"

# ---- Country sets (ISO alpha-2, as N-PORT C.5.a uses). STATED EXPLICITLY.
# EM equity (large EM economies; CN excluded = treated; haven residences excluded).
EM_A2 = {"KR", "TW", "IN", "BR", "ZA", "MX", "ID", "TH", "MY", "PH", "TR", "PL"}
# DM non-US equity.
DM_A2 = {"GB", "JP", "DE", "FR", "CA", "CH", "AU", "NL", "SE", "IT", "ES"}
TARGET_A2 = EM_A2 | DM_A2
EQUITY_CAT = "EC"   # equity common (SEC N-PORT ASSET_CAT dictionary)

NEEDED_TABLES = ["FUND_REPORTED_HOLDING.tsv", "SUBMISSION.tsv", "IDENTIFIERS.tsv",
                 "FUND_REPORTED_INFO.tsv", "REGISTRANT.tsv"]
NA_VALUES = ["#N/A", "#N/A N/A", "#NA", "<NA>", "NULL", "NaN", "nan",
             "n/a", "null", "N/A", "", "XXX", "XX"]


def previous_quarter(zip_q):
    year = int(zip_q[:4]); q = int(zip_q[5])
    return f"{year-1}q4" if q == 1 else f"{year}q{q-1}"


def download_zip(zip_q, zip_path):
    url = f"{BASE_URL}/{zip_q}_nport.zip"
    r = subprocess.run(["curl", "-fsSL", "-A", UA, "-H", f"From: {EMAIL}", url, "-o", zip_path],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(zip_path) or os.path.getsize(zip_path) < 10000:
        raise RuntimeError(f"download failed for {zip_q}: {r.stderr[:300]}")
    return url, os.path.getsize(zip_path)


def extract_tables(zip_path, qdir):
    os.makedirs(qdir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        for t in NEEDED_TABLES:
            if t not in names:
                raise RuntimeError(f"{t} missing from {zip_path}")
            z.extract(t, qdir)


def build_quarter(zip_q, work):
    qdir = os.path.join(work, f"q_{zip_q}")
    zip_path = os.path.join(work, f"{zip_q}_nport.zip")
    url, zip_bytes = download_zip(zip_q, zip_path)
    extract_tables(zip_path, qdir)
    fiscal_q = previous_quarter(zip_q)

    # holdings: BALANCE + UNIT included; filter EARLY by INVESTMENT_COUNTRY and equity.
    hold_cols = ["ACCESSION_NUMBER", "HOLDING_ID", "ISSUER_NAME", "ISSUER_LEI",
                 "ISSUER_TITLE", "ISSUER_CUSIP", "CURRENCY_CODE", "CURRENCY_VALUE",
                 "BALANCE", "UNIT", "OTHER_UNIT_DESC",
                 "PERCENTAGE", "ASSET_CAT", "ISSUER_TYPE", "INVESTMENT_COUNTRY"]
    parts = []
    total_rows = 0
    reader = pd.read_csv(os.path.join(qdir, "FUND_REPORTED_HOLDING.tsv"),
                         sep="\t", dtype=str, usecols=hold_cols,
                         keep_default_na=False, na_values=[], chunksize=200_000,
                         low_memory=False)
    for ch in reader:
        total_rows += len(ch)
        ch = ch[ch["INVESTMENT_COUNTRY"].isin(TARGET_A2) & (ch["ASSET_CAT"] == EQUITY_CAT)]
        if len(ch):
            parts.append(ch)
    if parts:
        h = pd.concat(parts, ignore_index=True)
    else:
        h = pd.DataFrame(columns=hold_cols)
    del parts; gc.collect()

    if h.empty:
        shutil.rmtree(qdir, ignore_errors=True); os.remove(zip_path)
        return None, {"zip_quarter": zip_q, "fiscal_quarter": fiscal_q, "zip_url": url,
                      "zip_bytes": zip_bytes, "total_holdings_in_quarter": total_rows,
                      "panel_rows": 0, "c2_em_rows": 0, "c3_dm_rows": 0}

    keep_ids = set(h["HOLDING_ID"]); keep_acc = set(h["ACCESSION_NUMBER"])

    idf = pd.read_csv(os.path.join(qdir, "IDENTIFIERS.tsv"), sep="\t", dtype=str,
                      na_values=NA_VALUES, low_memory=False)
    idf = idf[idf["HOLDING_ID"].isin(keep_ids)]

    def first_nn(s):
        nn = s.dropna()
        return nn.iloc[0] if len(nn) else pd.NA

    if len(idf):
        ids = idf.groupby("HOLDING_ID", as_index=False).agg(
            IDENTIFIER_ISIN=("IDENTIFIER_ISIN", first_nn))
    else:
        ids = pd.DataFrame(columns=["HOLDING_ID", "IDENTIFIER_ISIN"])

    sub = pd.read_csv(os.path.join(qdir, "SUBMISSION.tsv"), sep="\t", dtype=str,
                      usecols=["ACCESSION_NUMBER", "REPORT_ENDING_PERIOD", "REPORT_DATE"],
                      na_values=NA_VALUES, low_memory=False)
    sub = sub[sub["ACCESSION_NUMBER"].isin(keep_acc)]

    fi = pd.read_csv(os.path.join(qdir, "FUND_REPORTED_INFO.tsv"), sep="\t", dtype=str,
                     usecols=["ACCESSION_NUMBER", "SERIES_ID"],
                     na_values=NA_VALUES, low_memory=False)
    fi = fi[fi["ACCESSION_NUMBER"].isin(keep_acc)]

    reg = pd.read_csv(os.path.join(qdir, "REGISTRANT.tsv"), sep="\t", dtype=str,
                      usecols=["ACCESSION_NUMBER", "CIK", "REGISTRANT_NAME"],
                      na_values=NA_VALUES, low_memory=False)
    reg = reg[reg["ACCESSION_NUMBER"].isin(keep_acc)]

    h["ISSUER_CUSIP"] = h["ISSUER_CUSIP"].replace(NA_VALUES, pd.NA)
    df = h.merge(ids, on="HOLDING_ID", how="left")
    df = df.merge(sub, on="ACCESSION_NUMBER", how="left")
    df = df.merge(fi, on="ACCESSION_NUMBER", how="left")
    df = df.merge(reg, on="ACCESSION_NUMBER", how="left")

    df = df.rename(columns={
        "ACCESSION_NUMBER": "accession_number", "HOLDING_ID": "holding_id",
        "REPORT_ENDING_PERIOD": "report_period", "REPORT_DATE": "as_of_date",
        "CIK": "cik", "SERIES_ID": "series_id", "REGISTRANT_NAME": "registrant_name",
        "ISSUER_NAME": "issuer_name", "ISSUER_LEI": "issuer_lei",
        "ISSUER_CUSIP": "cusip", "IDENTIFIER_ISIN": "isin",
        "ASSET_CAT": "asset_cat", "ISSUER_TYPE": "issuer_type",
        "CURRENCY_VALUE": "currency_value", "CURRENCY_CODE": "currency_code",
        "BALANCE": "balance", "UNIT": "unit", "OTHER_UNIT_DESC": "other_unit_desc",
        "PERCENTAGE": "percentage", "INVESTMENT_COUNTRY": "investment_country",
    })
    df["currency_value"] = pd.to_numeric(df["currency_value"], errors="coerce")
    df["balance"] = pd.to_numeric(df["balance"], errors="coerce")
    df["fiscal_quarter"] = fiscal_q
    df["zip_quarter"] = zip_q
    # group label: C2 (EM) vs C3 (DM)
    df["control_group"] = np.where(df["investment_country"].isin(EM_A2), "C2",
                          np.where(df["investment_country"].isin(DM_A2), "C3", "OTHER"))

    keep = ["accession_number", "holding_id", "report_period", "as_of_date",
            "zip_quarter", "fiscal_quarter", "cik", "series_id", "registrant_name",
            "issuer_name", "issuer_lei", "cusip", "isin", "asset_cat", "issuer_type",
            "currency_value", "currency_code", "balance", "unit", "other_unit_desc",
            "percentage", "investment_country", "control_group"]
    df = df[[c for c in keep if c in df.columns]]

    shutil.rmtree(qdir, ignore_errors=True); os.remove(zip_path)

    c2 = int((df["control_group"] == "C2").sum())
    c3 = int((df["control_group"] == "C3").sum())
    meta = {"zip_quarter": zip_q, "fiscal_quarter": fiscal_q, "zip_url": url,
            "zip_bytes": zip_bytes, "total_holdings_in_quarter": total_rows,
            "panel_rows": len(df), "c2_em_rows": c2, "c3_dm_rows": c3}
    return df, meta


def main():
    work = sys.argv[1]
    # zip-quarter labels: fiscal 2019q3..2024q4 => zip = fiscal + 1 quarter => 2019q4..2025q1
    zip_quarters = sys.argv[2].split(",")
    os.makedirs(OUT_PARTS, exist_ok=True)
    os.makedirs(work, exist_ok=True)

    per_quarter = []
    skipped = []
    for zq in zip_quarters:
        outp = os.path.join(OUT_PARTS, f"did_ctrl_{previous_quarter(zq)}.parquet")
        if os.path.exists(outp):
            import pyarrow.parquet as pq
            t = pq.read_table(outp)
            df = t.to_pandas()
            per_quarter.append({"zip_quarter": zq, "fiscal_quarter": previous_quarter(zq),
                                "panel_rows": len(df),
                                "c2_em_rows": int((df["control_group"] == "C2").sum()),
                                "c3_dm_rows": int((df["control_group"] == "C3").sum()),
                                "cached": True})
            print(f"[cached] {zq} rows={len(df)}", flush=True)
            continue
        try:
            print(f"[reparse] {zq} ...", flush=True)
            df, meta = build_quarter(zq, work)
            per_quarter.append(meta)
            if df is not None and len(df):
                df.to_parquet(outp, index=False)
            print(f"[reparse] {zq} fiscal={meta['fiscal_quarter']} rows={meta['panel_rows']} "
                  f"C2={meta['c2_em_rows']} C3={meta['c3_dm_rows']} "
                  f"(of {meta['total_holdings_in_quarter']})", flush=True)
        except Exception as e:
            print(f"[SKIP] {zq}: {e}", flush=True)
            skipped.append({"zip_quarter": zq, "reason": str(e)})

    summary = {"em_a2": sorted(EM_A2), "dm_a2": sorted(DM_A2), "equity_cat": EQUITY_CAT,
               "per_quarter": per_quarter, "skipped": skipped,
               "out_parts_dir": OUT_PARTS}
    with open(os.path.join(OUT_PARTS, "_reparse_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("REPARSE_DONE")
    print(json.dumps({"skipped": skipped,
                      "n_quarters": len(per_quarter)}, indent=2))


if __name__ == "__main__":
    main()
