#!/usr/bin/env python3
"""
DP1-REOPEN Part 1 — Build the RESIDENCE-resolved N-PORT panel.

Builds a quarterly panel of US-registered-fund holdings whose issuer
INVESTMENT_COUNTRY (item C.5.a, the issuer's country of ORGANIZATION = RESIDENCE)
is in the haven set {KY Cayman, HK Hong Kong, VG British Virgin Islands} or is
CN (China mainland, resident-issued).

This is RESIDENCE basis only. The NATIONALITY (haven->China ultimate-parent)
reattribution is a commercially-gated HOLE per build/contracts/nport_gcap_contract.json
(GCAP/CMNS crosswalk needs CGS, Dealogic, SDC, Capital IQ, ORBIS, FactSet,
Morningstar — none redistributed). issuer_nationality is therefore set to
"UNDETERMINED-NO-PUBLIC-CROSSWALK" on every row and is NOT filled.

Scope limit: US-registered-fund HOLDERS only (the dense US-holder leg). Not the
global holder matrix.

Each quarter is downloaded, the needed TSV tables extracted, holdings filtered
EARLY to the target issuer-countries, then raw files deleted before the next
quarter. Column/table names follow the GCAP public-US-funds-data pipeline
(B_processing_functions_nport.py) and the SEC nport_readme data dictionary.

N-PORT public-data convention (per GCAP C_nport_build.py and the SEC dissemination
rule): the ZIP labelled <YYYY>qQ contains filings disseminated in that quarter,
whose holdings are as-of the PREVIOUS fiscal quarter-end. We record BOTH the
zip label (zip_quarter) and the GCAP "actual" data quarter (fiscal_quarter), and
the per-filing REPORT_DATE / REPORT_ENDING_PERIOD as the authoritative as-of date.
"""
import os, sys, json, zipfile, subprocess, gc, shutil
import pandas as pd
import numpy as np

# ---- ISO alpha-2 target set. N-PORT C.5.a uses ISO-3166 alpha-2 (verified in data).
#      Task spec named alpha-3 (CYM/HKG/VGB/CHN); mapping recorded in provenance.
HAVEN_A2 = {"KY": "CYM", "HK": "HKG", "VG": "VGB"}   # residence havens
CHINA_A2 = {"CN": "CHN"}                              # China mainland residence
TARGET_A2 = set(HAVEN_A2) | set(CHINA_A2)

NEEDED_TABLES = [
    "FUND_REPORTED_HOLDING.tsv", "SUBMISSION.tsv", "IDENTIFIERS.tsv",
    "FUND_REPORTED_INFO.tsv", "REGISTRANT.tsv",
]

BASE_URL = "https://www.sec.gov/files/dera/data/form-n-port-data-sets"
EMAIL = "milevsky@hotmail.com"
UA = f"dollar-breaking-point research {EMAIL}"

NA_VALUES = ["#N/A", "#N/A N/A", "#NA", "<NA>", "NULL", "NaN", "nan",
             "n/a", "null", "N/A", "", "XXX", "XX"]


def previous_quarter(zip_q):
    """GCAP convention: zip <YYYY>qQ holds data for the previous fiscal quarter."""
    year = int(zip_q[:4]); q = int(zip_q[5])
    return f"{year-1}q4" if q == 1 else f"{year}q{q-1}"


def download_zip(zip_q, zip_path):
    url = f"{BASE_URL}/{zip_q}_nport.zip"
    r = subprocess.run(
        ["curl", "-fsSL", "-A", UA, "-H", f"From: {EMAIL}", url, "-o", zip_path],
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

    # --- holdings: filter EARLY by INVESTMENT_COUNTRY, chunked to bound memory.
    hold_cols = ["ACCESSION_NUMBER", "HOLDING_ID", "ISSUER_NAME", "ISSUER_LEI",
                 "ISSUER_TITLE", "ISSUER_CUSIP", "CURRENCY_CODE", "CURRENCY_VALUE",
                 "PERCENTAGE", "ASSET_CAT", "ISSUER_TYPE", "INVESTMENT_COUNTRY"]
    parts = []
    reader = pd.read_csv(os.path.join(qdir, "FUND_REPORTED_HOLDING.tsv"),
                         sep="\t", dtype=str, usecols=hold_cols,
                         keep_default_na=False, na_values=[], chunksize=200_000,
                         low_memory=False)
    total_rows = 0
    for ch in reader:
        total_rows += len(ch)
        ch = ch[ch["INVESTMENT_COUNTRY"].isin(TARGET_A2)]
        if len(ch):
            parts.append(ch)
    if parts:
        h = pd.concat(parts, ignore_index=True)
    else:
        h = pd.DataFrame(columns=hold_cols)
    del parts; gc.collect()

    if h.empty:
        shutil.rmtree(qdir, ignore_errors=True)
        os.remove(zip_path)
        return None, {"zip_quarter": zip_q, "fiscal_quarter": fiscal_q,
                      "zip_url": url, "zip_bytes": zip_bytes,
                      "total_holdings_in_quarter": total_rows, "panel_rows": 0}

    keep_ids = set(h["HOLDING_ID"])
    keep_acc = set(h["ACCESSION_NUMBER"])

    # --- identifiers: consolidate per HOLDING_ID, keep only matched holdings.
    idf = pd.read_csv(os.path.join(qdir, "IDENTIFIERS.tsv"), sep="\t", dtype=str,
                      na_values=NA_VALUES, low_memory=False)
    idf = idf[idf["HOLDING_ID"].isin(keep_ids)]

    def first_nn(s):
        nn = s.dropna()
        return nn.iloc[0] if len(nn) else pd.NA

    if len(idf):
        ids = idf.groupby("HOLDING_ID", as_index=False).agg(
            IDENTIFIER_ISIN=("IDENTIFIER_ISIN", first_nn),
            IDENTIFIER_TICKER=("IDENTIFIER_TICKER", first_nn),
            OTHER_IDENTIFIER=("OTHER_IDENTIFIER", first_nn),
            OTHER_IDENTIFIER_DESC=("OTHER_IDENTIFIER_DESC", first_nn))
    else:
        ids = pd.DataFrame(columns=["HOLDING_ID", "IDENTIFIER_ISIN",
                                    "IDENTIFIER_TICKER", "OTHER_IDENTIFIER",
                                    "OTHER_IDENTIFIER_DESC"])

    # --- submission: as-of date keyed on accession.
    sub = pd.read_csv(os.path.join(qdir, "SUBMISSION.tsv"), sep="\t", dtype=str,
                      usecols=["ACCESSION_NUMBER", "SUB_TYPE", "REPORT_ENDING_PERIOD",
                               "REPORT_DATE", "FILING_DATE"],
                      na_values=NA_VALUES, low_memory=False)
    sub = sub[sub["ACCESSION_NUMBER"].isin(keep_acc)]

    # --- fund info.
    fi = pd.read_csv(os.path.join(qdir, "FUND_REPORTED_INFO.tsv"), sep="\t", dtype=str,
                     usecols=["ACCESSION_NUMBER", "SERIES_NAME", "SERIES_ID",
                              "SERIES_LEI", "TOTAL_ASSETS", "NET_ASSETS"],
                     na_values=NA_VALUES, low_memory=False)
    fi = fi[fi["ACCESSION_NUMBER"].isin(keep_acc)]

    # --- registrant.
    reg = pd.read_csv(os.path.join(qdir, "REGISTRANT.tsv"), sep="\t", dtype=str,
                      usecols=["ACCESSION_NUMBER", "CIK", "REGISTRANT_NAME",
                               "FILE_NUM", "LEI"],
                      na_values=NA_VALUES, low_memory=False)
    reg = reg[reg["ACCESSION_NUMBER"].isin(keep_acc)]

    # --- merge.
    h["ISSUER_CUSIP"] = h["ISSUER_CUSIP"].replace(NA_VALUES, pd.NA)
    df = h.merge(ids, on="HOLDING_ID", how="left")
    df = df.merge(sub, on="ACCESSION_NUMBER", how="left")
    df = df.merge(fi, on="ACCESSION_NUMBER", how="left")
    df = df.merge(reg, on="ACCESSION_NUMBER", how="left")

    df["zip_quarter"] = zip_q
    df["fiscal_quarter"] = fiscal_q

    # cleanup raw files for this quarter before returning
    shutil.rmtree(qdir, ignore_errors=True)
    os.remove(zip_path)

    meta = {"zip_quarter": zip_q, "fiscal_quarter": fiscal_q, "zip_url": url,
            "zip_bytes": zip_bytes, "total_holdings_in_quarter": total_rows,
            "panel_rows": len(df)}
    return df, meta


def main():
    work = sys.argv[1]
    out_dir = sys.argv[2]
    quarters = sys.argv[3].split(",")   # zip-quarter labels
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(work, exist_ok=True)

    all_parts = []
    per_quarter = []
    skipped = []
    for zq in quarters:
        try:
            print(f"[build] {zq} ...", flush=True)
            df, meta = build_quarter(zq, work)
            per_quarter.append(meta)
            if df is not None and len(df):
                all_parts.append(df)
            print(f"[build] {zq} fiscal={meta['fiscal_quarter']} "
                  f"panel_rows={meta['panel_rows']} "
                  f"(of {meta['total_holdings_in_quarter']} holdings)", flush=True)
        except Exception as e:
            print(f"[SKIP] {zq}: {e}", flush=True)
            skipped.append({"zip_quarter": zq, "reason": str(e)})

    panel = pd.concat(all_parts, ignore_index=True)

    # ---- finalize columns / naming per task spec.
    panel = panel.rename(columns={
        "ACCESSION_NUMBER": "accession_number", "HOLDING_ID": "holding_id",
        "REPORT_ENDING_PERIOD": "report_period", "REPORT_DATE": "as_of_date",
        "CIK": "cik", "SERIES_ID": "series_id", "REGISTRANT_NAME": "registrant_name",
        "ISSUER_NAME": "issuer_name", "ISSUER_LEI": "issuer_lei",
        "ISSUER_CUSIP": "cusip", "IDENTIFIER_ISIN": "isin",
        "ASSET_CAT": "asset_cat", "ISSUER_TYPE": "issuer_type",
        "CURRENCY_VALUE": "currency_value", "CURRENCY_CODE": "currency_code",
        "PERCENTAGE": "percentage", "INVESTMENT_COUNTRY": "investment_country",
    })

    # numeric coercions
    panel["currency_value"] = pd.to_numeric(panel["currency_value"], errors="coerce")
    panel["percentage"] = pd.to_numeric(panel["percentage"], errors="coerce")

    # RESIDENCE -> alpha-3 echo for readability (issuer country of ORGANIZATION)
    a2_to_a3 = {**HAVEN_A2, **CHINA_A2}
    panel["investment_country_iso3"] = panel["investment_country"].map(a2_to_a3)

    # is_haven_resident — RESIDENCE flag, NOT parent-nationality.
    panel["is_haven_resident"] = panel["investment_country"].isin(HAVEN_A2)

    # NATIONALITY — the HOLE. Not filled.
    panel["issuer_nationality"] = "UNDETERMINED-NO-PUBLIC-CROSSWALK"

    # identifier-coverage check: share carrying a usable ISIN or CUSIP.
    isin_ok = panel["isin"].notna() & (panel["isin"].astype(str).str.len() == 12)
    cusip_ok = panel["cusip"].notna() & (panel["cusip"].astype(str).str.len() == 9)
    usable = isin_ok | cusip_ok
    cov = float(usable.mean() * 100) if len(panel) else 0.0

    col_order = [
        "accession_number", "holding_id", "report_period", "as_of_date",
        "zip_quarter", "fiscal_quarter",
        "cik", "series_id", "registrant_name",
        "issuer_name", "issuer_lei", "cusip", "isin", "asset_cat", "issuer_type",
        "currency_value", "currency_code", "percentage",
        "investment_country", "investment_country_iso3", "is_haven_resident",
        "issuer_nationality",
    ]
    panel = panel[[c for c in col_order if c in panel.columns]]

    out_path = os.path.join(out_dir, "us_china_nationality_panel.parquet")
    panel.to_parquet(out_path, index=False)

    # per-residence-country breakdown
    by_country = (panel.groupby("investment_country_iso3").size()
                  .to_dict())
    by_q = (panel.groupby(["zip_quarter", "fiscal_quarter"]).size()
            .reset_index(name="rows").to_dict("records"))

    summary = {
        "out_path": out_path,
        "total_rows": int(len(panel)),
        "identifier_coverage_pct": round(cov, 4),
        "identifier_coverage_n_usable": int(usable.sum()),
        "isin_usable_n": int(isin_ok.sum()),
        "cusip_usable_n": int(cusip_ok.sum()),
        "rows_by_residence_iso3": by_country,
        "rows_by_quarter": by_q,
        "per_quarter_meta": per_quarter,
        "skipped": skipped,
        "distinct_accessions": int(panel["accession_number"].nunique()),
        "distinct_ciks": int(panel["cik"].nunique()),
    }
    with open(os.path.join(work, "_build_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("SUMMARY_JSON_BEGIN")
    print(json.dumps(summary, indent=2))
    print("SUMMARY_JSON_END")


if __name__ == "__main__":
    main()
