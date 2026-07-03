#!/usr/bin/env python3
"""
FULL-PANEL POWER REBUILD, Part 1 driver.

Reuses build_us_china_panel.build_quarter VERBATIM (same per-quarter N-PORT parse:
ZIP download, structured-table read, fund identity + fiscal_quarter, residence
investment_country -> ISO2/ISO3 + is_haven_resident, currency_value, issuer keys).
This driver ONLY orchestrates the missing quarters, filters EARLY to haven-residence
rows (is_haven_resident True = residence CYM/HKG/VGB), persists each quarter's haven
subset to its own parquet, and deletes the raw ZIP between quarters (disk management).

No tagging here -- tagging is the separate reused R1-R4 step.
"""
import os, sys, json, gc
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_us_china_panel as B   # the reused parse module

# Haven-residence echo (same mapping as B): KY/HK/VG -> CYM/HKG/VGB.
def finalize_haven(df):
    """Apply B's exact column-finalize + residence echo, then FILTER to haven rows.
    Mirrors build_us_china_panel.main()'s rename/echo so the schema is identical."""
    df = df.rename(columns={
        "ACCESSION_NUMBER": "accession_number", "HOLDING_ID": "holding_id",
        "REPORT_ENDING_PERIOD": "report_period", "REPORT_DATE": "as_of_date",
        "CIK": "cik", "SERIES_ID": "series_id", "REGISTRANT_NAME": "registrant_name",
        "ISSUER_NAME": "issuer_name", "ISSUER_LEI": "issuer_lei",
        "ISSUER_CUSIP": "cusip", "IDENTIFIER_ISIN": "isin",
        "ASSET_CAT": "asset_cat", "ISSUER_TYPE": "issuer_type",
        "CURRENCY_VALUE": "currency_value", "CURRENCY_CODE": "currency_code",
        "PERCENTAGE": "percentage", "INVESTMENT_COUNTRY": "investment_country",
    })
    df["currency_value"] = pd.to_numeric(df["currency_value"], errors="coerce")
    df["percentage"] = pd.to_numeric(df["percentage"], errors="coerce")
    a2_to_a3 = {**B.HAVEN_A2, **B.CHINA_A2}
    df["investment_country_iso3"] = df["investment_country"].map(a2_to_a3)
    df["is_haven_resident"] = df["investment_country"].isin(B.HAVEN_A2)
    df["issuer_nationality"] = "UNDETERMINED-NO-PUBLIC-CROSSWALK"
    col_order = [
        "accession_number", "holding_id", "report_period", "as_of_date",
        "zip_quarter", "fiscal_quarter",
        "cik", "series_id", "registrant_name",
        "issuer_name", "issuer_lei", "cusip", "isin", "asset_cat", "issuer_type",
        "currency_value", "currency_code", "percentage",
        "investment_country", "investment_country_iso3", "is_haven_resident",
        "issuer_nationality",
    ]
    df = df[[c for c in col_order if c in df.columns]]
    # FILTER EARLY to haven-residence to keep the panel committable.
    return df[df["is_haven_resident"] == True].copy()


def main():
    work = sys.argv[1]
    parts_dir = sys.argv[2]
    zip_quarters = sys.argv[3].split(",")
    os.makedirs(work, exist_ok=True)
    os.makedirs(parts_dir, exist_ok=True)

    meta_all = []
    for zq in zip_quarters:
        fq = B.previous_quarter(zq)
        out_part = os.path.join(parts_dir, f"haven_{fq}.parquet")
        if os.path.exists(out_part):
            print(f"[skip-exists] {zq} fiscal={fq} already built", flush=True)
            continue
        try:
            print(f"[build] {zq} fiscal={fq} downloading+parsing ...", flush=True)
            df, meta = B.build_quarter(zq, work)   # REUSED verbatim
            if df is None or len(df) == 0:
                meta["haven_rows"] = 0
                meta_all.append(meta)
                print(f"[build] {zq} -> 0 target rows", flush=True)
                continue
            hv = finalize_haven(df)
            hv.to_parquet(out_part, index=False)
            meta["haven_rows"] = int(len(hv))
            meta_all.append(meta)
            print(f"[build] {zq} fiscal={fq} haven_rows={len(hv)} "
                  f"(of {meta['total_holdings_in_quarter']} holdings) -> {out_part}",
                  flush=True)
            del df, hv; gc.collect()
        except Exception as e:
            print(f"[ERROR] {zq}: {e}", flush=True)
            meta_all.append({"zip_quarter": zq, "fiscal_quarter": fq, "error": str(e)})

    with open(os.path.join(parts_dir, f"_meta_{zip_quarters[0]}.json"), "w") as f:
        json.dump(meta_all, f, indent=2)
    print("DRIVER_DONE", json.dumps(meta_all, default=str), flush=True)


if __name__ == "__main__":
    main()
