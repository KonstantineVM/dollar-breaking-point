import os
import pandas as pd
import sys
import traceback
import gc

# ---------------------------------------------------------
# Execute N-PORT build using processing functions from B
# ---------------------------------------------------------
# Read arguments from NPORT_Master.do
if len(sys.argv) != 5:
    print("Usage: python C_nport_build.py <quarter> <code_path> <raw_data_dir> <output_dir>")
    sys.exit(1)

quarter_name = sys.argv[1]
CODE_PATH = sys.argv[2]
DATA_DIR = sys.argv[3]
OUTPUT_DIR = sys.argv[4]

# Add local module path
sys.path.append(CODE_PATH)
from B_processing_functions_nport import (
    load_holdings, load_submission, load_identifiers,
    enrich_data, load_fund_info, load_registrant, validate_and_clean_data
)

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Helper: shift one quarter back
def previous_quarter(quarter_name):
    year = int(quarter_name[:4])
    q = int(quarter_name[5])
    return f"{year-1}q4" if q == 1 else f"{year}q{q-1}"
data_path = os.path.join(DATA_DIR, f"{quarter_name}")
actual_quarter = previous_quarter(quarter_name)
output_file = os.path.join(OUTPUT_DIR, f"{quarter_name}.dta")
print(f"Processing {quarter_name} (data for {actual_quarter}) ...")

try:
    # Load data
    df = load_holdings(data_path)
    submission = load_submission(data_path)
    identifiers = load_identifiers(data_path)

    # Enrich with submission + identifiers
    df = enrich_data(df, submission, identifiers)

    # Merge with fund- and registrant-level info
    fund_info = load_fund_info(data_path)
    registrant = load_registrant(data_path)
    df = df.merge(fund_info, on="ACCESSION_NUMBER", how="left")
    df = df.merge(registrant, on="ACCESSION_NUMBER", how="left")

    # Add quarter and apply validation checks
    df["QUARTER"] = actual_quarter
    df = validate_and_clean_data(df)
    df = df.rename(columns=str.lower)

    # Save to Stata (version=118 works for wide files)
    df.to_stata(output_file, write_index=False, version=118)
    print(f"Saved to {output_file}")

except Exception as e:
    print(f"Error processing {quarter_name}: {e}")
    traceback.print_exc()

# Cleanup memory
del df, submission, identifiers, fund_info, registrant
gc.collect()