#!/usr/bin/env python3
"""
ACTIVE-FLOW F3 TEST -- Part 1, step A: rebuild the 22-quarter haven panel WITH BALANCE.

Reuses build_us_china_panel.build_quarter's parse VERBATIM in spirit (same download,
same early INVESTMENT_COUNTRY filter, same identifier consolidation and fund-identity
merges, same NA handling, same fiscal_quarter convention), adding only BALANCE, UNIT,
OTHER_UNIT_DESC to the extracted holding columns. Persists each quarter's haven subset
(residence CYM/HKG/VGB) to its own parquet and deletes the raw ZIP between quarters.

Tagging is NOT done here -- tag_fullpanel.py's R1-R4 is re-applied verbatim afterward.

Output parts: build/data/nport/haven_bal_parts/haven_bal_<fiscal>.parquet
"""
import os, sys, json, zipfile, gc, shutil
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/user/dollar-breaking-point"
sys.path.insert(0, HERE)
import build_us_china_panel as B

PARTS = os.path.join(ROOT, "build/data/nport/haven_bal_parts")


def build_quarter_bal(zip_q, work):
    """Same as B.build_quarter but extracts BALANCE/UNIT/OTHER_UNIT_DESC and keeps
    the residence-haven+CN subset with those columns. Filter EARLY, delete ZIP."""
    qdir = os.path.join(work, f"q_{zip_q}")
    zip_path = os.path.join(work, f"{zip_q}_nport.zip")
    url, zip_bytes = B.download_zip(zip_q, zip_path)
    B.extract_tables(zip_path, qdir)   # reused: extracts the NEEDED_TABLES verbatim
    fiscal_q = B.previous_quarter(zip_q)

    hold_cols = ["ACCESSION_NUMBER", "HOLDING_ID", "ISSUER_NAME", "ISSUER_LEI",
                 "ISSUER_TITLE", "ISSUER_CUSIP", "CURRENCY_CODE", "CURRENCY_VALUE",
                 "PERCENTAGE", "ASSET_CAT", "ISSUER_TYPE", "INVESTMENT_COUNTRY",
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

    if h.empty:
        shutil.rmtree(qdir, ignore_errors=True); os.remove(zip_path)
        return None, {"zip_quarter": zip_q, "fiscal_quarter": fiscal_q, "zip_url": url,
                      "zip_bytes": zip_bytes, "total_holdings_in_quarter": total_rows,
                      "panel_rows": 0, "haven_rows": 0}

    keep_ids = set(h["HOLDING_ID"]); keep_acc = set(h["ACCESSION_NUMBER"])

    # identifiers -- verbatim consolidation from B.build_quarter
    idf = pd.read_csv(os.path.join(qdir, "IDENTIFIERS.tsv"), sep="\t", dtype=str,
                      na_values=B.NA_VALUES, low_memory=False)
    idf = idf[idf["HOLDING_ID"].isin(keep_ids)]

    def first_nn(s):
        nn = s.dropna(); return nn.iloc[0] if len(nn) else pd.NA
    if len(idf):
        ids = idf.groupby("HOLDING_ID", as_index=False).agg(
            IDENTIFIER_ISIN=("IDENTIFIER_ISIN", first_nn),
            IDENTIFIER_TICKER=("IDENTIFIER_TICKER", first_nn),
            OTHER_IDENTIFIER=("OTHER_IDENTIFIER", first_nn),
            OTHER_IDENTIFIER_DESC=("OTHER_IDENTIFIER_DESC", first_nn))
    else:
        ids = pd.DataFrame(columns=["HOLDING_ID", "IDENTIFIER_ISIN", "IDENTIFIER_TICKER",
                                    "OTHER_IDENTIFIER", "OTHER_IDENTIFIER_DESC"])

    sub = pd.read_csv(os.path.join(qdir, "SUBMISSION.tsv"), sep="\t", dtype=str,
                      usecols=["ACCESSION_NUMBER", "SUB_TYPE", "REPORT_ENDING_PERIOD",
                               "REPORT_DATE", "FILING_DATE"],
                      na_values=B.NA_VALUES, low_memory=False)
    sub = sub[sub["ACCESSION_NUMBER"].isin(keep_acc)]

    fi = pd.read_csv(os.path.join(qdir, "FUND_REPORTED_INFO.tsv"), sep="\t", dtype=str,
                     usecols=["ACCESSION_NUMBER", "SERIES_NAME", "SERIES_ID",
                              "SERIES_LEI", "TOTAL_ASSETS", "NET_ASSETS"],
                     na_values=B.NA_VALUES, low_memory=False)
    fi = fi[fi["ACCESSION_NUMBER"].isin(keep_acc)]

    reg = pd.read_csv(os.path.join(qdir, "REGISTRANT.tsv"), sep="\t", dtype=str,
                      usecols=["ACCESSION_NUMBER", "CIK", "REGISTRANT_NAME",
                               "FILE_NUM", "LEI"],
                      na_values=B.NA_VALUES, low_memory=False)
    reg = reg[reg["ACCESSION_NUMBER"].isin(keep_acc)]

    h["ISSUER_CUSIP"] = h["ISSUER_CUSIP"].replace(B.NA_VALUES, pd.NA)
    df = h.merge(ids, on="HOLDING_ID", how="left")
    df = df.merge(sub, on="ACCESSION_NUMBER", how="left")
    df = df.merge(fi, on="ACCESSION_NUMBER", how="left")
    df = df.merge(reg, on="ACCESSION_NUMBER", how="left")
    df["zip_quarter"] = zip_q
    df["fiscal_quarter"] = fiscal_q

    shutil.rmtree(qdir, ignore_errors=True); os.remove(zip_path)

    # finalize identical to build_fullpanel_haven.finalize_haven + carry balance/unit
    df = df.rename(columns={
        "ACCESSION_NUMBER": "accession_number", "HOLDING_ID": "holding_id",
        "REPORT_ENDING_PERIOD": "report_period", "REPORT_DATE": "as_of_date",
        "CIK": "cik", "SERIES_ID": "series_id", "REGISTRANT_NAME": "registrant_name",
        "ISSUER_NAME": "issuer_name", "ISSUER_LEI": "issuer_lei",
        "ISSUER_CUSIP": "cusip", "IDENTIFIER_ISIN": "isin",
        "ASSET_CAT": "asset_cat", "ISSUER_TYPE": "issuer_type",
        "CURRENCY_VALUE": "currency_value", "CURRENCY_CODE": "currency_code",
        "PERCENTAGE": "percentage", "INVESTMENT_COUNTRY": "investment_country",
        "BALANCE": "balance", "UNIT": "unit", "OTHER_UNIT_DESC": "other_unit_desc",
    })
    df["currency_value"] = pd.to_numeric(df["currency_value"], errors="coerce")
    df["percentage"] = pd.to_numeric(df["percentage"], errors="coerce")
    df["balance"] = pd.to_numeric(df["balance"], errors="coerce")
    a2_to_a3 = {**B.HAVEN_A2, **B.CHINA_A2}
    df["investment_country_iso3"] = df["investment_country"].map(a2_to_a3)
    df["is_haven_resident"] = df["investment_country"].isin(B.HAVEN_A2)
    df["issuer_nationality"] = "UNDETERMINED-NO-PUBLIC-CROSSWALK"
    col_order = [
        "accession_number", "holding_id", "report_period", "as_of_date",
        "zip_quarter", "fiscal_quarter", "cik", "series_id", "registrant_name",
        "issuer_name", "issuer_lei", "cusip", "isin", "asset_cat", "issuer_type",
        "currency_value", "currency_code", "percentage",
        "balance", "unit", "other_unit_desc",
        "investment_country", "investment_country_iso3", "is_haven_resident",
        "issuer_nationality",
    ]
    df = df[[c for c in col_order if c in df.columns]]
    hv = df[df["is_haven_resident"] == True].copy()   # FILTER EARLY to haven residence
    meta = {"zip_quarter": zip_q, "fiscal_quarter": fiscal_q, "zip_url": url,
            "zip_bytes": zip_bytes, "total_holdings_in_quarter": total_rows,
            "haven_rows": int(len(hv))}
    return hv, meta


def main():
    work = sys.argv[1]
    zip_quarters = sys.argv[2].split(",")
    os.makedirs(work, exist_ok=True); os.makedirs(PARTS, exist_ok=True)
    meta_all = []
    for zq in zip_quarters:
        fq = B.previous_quarter(zq)
        out_part = os.path.join(PARTS, f"haven_bal_{fq}.parquet")
        if os.path.exists(out_part):
            print(f"[skip-exists] {zq} fiscal={fq}", flush=True); continue
        try:
            print(f"[build] {zq} fiscal={fq} ...", flush=True)
            hv, meta = build_quarter_bal(zq, work)
            if hv is None or len(hv) == 0:
                meta_all.append(meta); print(f"[build] {zq} -> 0 rows", flush=True); continue
            hv.to_parquet(out_part, index=False)
            meta_all.append(meta)
            print(f"[build] {zq} fiscal={fq} haven_rows={len(hv)} -> {out_part}", flush=True)
            del hv; gc.collect()
        except Exception as e:
            print(f"[ERROR] {zq}: {e}", flush=True)
            meta_all.append({"zip_quarter": zq, "fiscal_quarter": fq, "error": str(e)})
    with open(os.path.join(PARTS, f"_meta_{zip_quarters[0]}_{zip_quarters[-1]}.json"), "w") as f:
        json.dump(meta_all, f, indent=2)
    print("DRIVER_DONE", flush=True)


if __name__ == "__main__":
    main()
