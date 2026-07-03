import os
import pandas as pd
import numpy as np
import re
import unicodedata

# ---------------------------------------------------------
# Function: Load (security,fund)-level holdings file
# ---------------------------------------------------------
def load_holdings(data_dir):
    
    # Define what to be considered NA values in holdings data
    NA_VALUES = [
    "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN", "-NaN", "-nan",
    "1.#IND", "1.#QNAN", "<NA>", "NULL", "NaN", "nan", "n/a", "null",
    "N/A", "", "XXX"
    ]

    # Load raw N-PORT holdings data
    df = pd.read_csv(
        os.path.join(data_dir, "FUND_REPORTED_HOLDING.tsv"),
        sep="\t",
        keep_default_na=False,
        na_values=NA_VALUES,
        dtype=str,
        low_memory=False
    ) 
    assert not df.duplicated(["ACCESSION_NUMBER", "HOLDING_ID"]).any(), "Duplicate holdings found"
    return df

# ---------------------------------------------------------
# Function: Load fund-level submission file
# ---------------------------------------------------------
def load_submission(data_dir):
    
    # Define which columns to load
    cols = ["ACCESSION_NUMBER", "SUB_TYPE", "REPORT_ENDING_PERIOD", "REPORT_DATE", "FILING_DATE"]
    
    # Load raw N-PORT submission data
    df = pd.read_csv(
        os.path.join(data_dir, "SUBMISSION.tsv"),
        sep="\t",
        dtype=str,
        usecols=cols,
        na_values=["N/A", "n/a", "", "XXX"],
        low_memory=False
    )
    for col in cols[2:]:
        df[col] = pd.to_datetime(df[col], format="%d-%b-%Y", errors="coerce")
    return df

# ---------------------------------------------------------
# Function: Load and clean security-level identifiers file
#
# Note: In the raw data, one security can have multiple 
# identifier records (e.g., different CUSIPs), this function
# consolidates into single rows
# ---------------------------------------------------------
def load_identifiers(data_dir):
    
    # Set path
    path = os.path.join(data_dir, "IDENTIFIERS.tsv")
    
    # Load raw N-PORT security-identifiers data
    df = pd.read_csv(
        path,
        sep="\t",
        dtype=str,
        na_values=["N/A", "n/a", "", "XXX"],
        low_memory=False
    )

    # Return first non-null identifier and check it is unique
    def first_non_null_with_validation(series, field_name):
        """Return first non-null value, validating uniqueness"""
        non_null = series.dropna()
        if len(non_null) == 0:
            return pd.NA
        elif len(non_null) == 1:
            return non_null.iloc[0]
        else:
            # Check if all non-null values are the same
            unique_values = non_null.unique()
            if len(unique_values) == 1:
                return unique_values[0]
            else:
                # This should not happen based on data analysis, but good to catch
                holding_id = series.name if hasattr(series, 'name') else "unknown"
                raise ValueError(f"Multiple different {field_name} values found for HOLDING_ID {holding_id}: {list(unique_values)}")
    
    # Return first non-null identifier
    def first_non_null(series):
        """Return first non-null value or pd.NA"""
        non_null = series.dropna()
        return non_null.iloc[0] if len(non_null) > 0 else pd.NA
    
    # Return first non-null identifier using a priority order
    # CUSIP → ISIN → SEDOL → First Available
    def prioritize_other_identifier(group):
        """For OTHER_IDENTIFIER, prioritize CUSIP/ISIN, then SEDOL, then first available"""
        other_mask = group["OTHER_IDENTIFIER"].notna()
        if not other_mask.any():
            return pd.Series({"OTHER_IDENTIFIER": pd.NA, "OTHER_IDENTIFIER_DESC": pd.NA})
        
        other_data = group[other_mask]
        
        # Priority 1: CUSIP identifiers
        cusip_mask = other_data["OTHER_IDENTIFIER_DESC"].str.contains("cusip", case=False, na=False)
        if cusip_mask.any():
            cusip_row = other_data[cusip_mask].iloc[0]
            return pd.Series({
                "OTHER_IDENTIFIER": cusip_row["OTHER_IDENTIFIER"],
                "OTHER_IDENTIFIER_DESC": cusip_row["OTHER_IDENTIFIER_DESC"]
            })
        
        # Priority 2: ISIN identifiers (in OTHER_IDENTIFIER field)
        isin_mask = other_data["OTHER_IDENTIFIER_DESC"].str.contains("isin", case=False, na=False)
        if isin_mask.any():
            isin_row = other_data[isin_mask].iloc[0]
            return pd.Series({
                "OTHER_IDENTIFIER": isin_row["OTHER_IDENTIFIER"],
                "OTHER_IDENTIFIER_DESC": isin_row["OTHER_IDENTIFIER_DESC"]
            })
        
        # Priority 3: SEDOL identifiers
        sedol_mask = other_data["OTHER_IDENTIFIER_DESC"].str.contains("sedol", case=False, na=False)
        if sedol_mask.any():
            sedol_row = other_data[sedol_mask].iloc[0]
            return pd.Series({
                "OTHER_IDENTIFIER": sedol_row["OTHER_IDENTIFIER"],
                "OTHER_IDENTIFIER_DESC": sedol_row["OTHER_IDENTIFIER_DESC"]
            })
        
        # Priority 4: Use first available
        first_row = other_data.iloc[0]
        return pd.Series({
            "OTHER_IDENTIFIER": first_row["OTHER_IDENTIFIER"],
            "OTHER_IDENTIFIER_DESC": first_row["OTHER_IDENTIFIER_DESC"]
        })
    
    # Consolidate in two steps
    # Step 1: Basic aggregation for (unique) ISIN and (first) TICKER
    def validate_isin(series):
        return first_non_null_with_validation(series, "IDENTIFIER_ISIN")
    
    def first_ticker(series):
        """For ticker, pick first non-missing value (conflicts are rare)"""
        return first_non_null(series)
    
    basic_agg = df.groupby("HOLDING_ID", as_index=False).agg({
        "IDENTIFIER_ISIN": validate_isin,
        "IDENTIFIER_TICKER": first_ticker
    })
    
    # Step 2: Handle OTHER_IDENTIFIER with prioritization
    other_agg = df.groupby("HOLDING_ID").apply(prioritize_other_identifier).reset_index()
    
    # Merge results
    identifiers = basic_agg.merge(other_agg, on="HOLDING_ID", how="left")

    return identifiers

# ---------------------------------------------------------
# Function: Merge holdings, submission and identifiers data
# ---------------------------------------------------------
def enrich_data(df, submission, identifiers):
    df = df.merge(submission, on="ACCESSION_NUMBER", how="left")
    df = df.merge(identifiers, on="HOLDING_ID", how="left")
    df["INVESTMENT_COUNTRY"] = df["INVESTMENT_COUNTRY"].replace("XX", pd.NA)
    return df


# ---------------------------------------------------------
# Function: Load fund-level information data
# ---------------------------------------------------------
def load_fund_info(data_dir):
    cols = [
        "ACCESSION_NUMBER", "SERIES_NAME", "SERIES_ID",
        "SERIES_LEI", "TOTAL_ASSETS", "NET_ASSETS"
    ]
    df = pd.read_csv(
        os.path.join(data_dir, "FUND_REPORTED_INFO.tsv"),
        sep="\t", usecols=cols,
        dtype=str, na_values=["N/A", "n/a", "", "XXX"],
        low_memory=False
    )
    return df

# ---------------------------------------------------------
# Function: Load fund-level registrant info
# ---------------------------------------------------------
def load_registrant(data_dir):
    cols = ["ACCESSION_NUMBER", "CIK", "REGISTRANT_NAME", "FILE_NUM", "LEI"]
    df = pd.read_csv(
        os.path.join(data_dir, "REGISTRANT.tsv"),
        sep="\t", usecols=cols,
        dtype=str, na_values=["N/A", "n/a", "", "XXX"],
        low_memory=False
    )
    return df

# ------------------------------------
# Validation Functions
# ------------------------------------

def validate_isin(isin):
    """Validate ISIN format: 12 characters, uppercase, no punctuation"""
    if pd.isna(isin) or isin == "":
        return isin
    
    # Check length
    if len(isin) != 12:
        return pd.NA
    
    # Check if all characters are alphanumeric
    if not isin.isalnum():
        return pd.NA
    
    # Convert to uppercase
    return isin.upper()

def validate_cusip(cusip):
    """Validate CUSIP format: 9 alphanumeric characters"""
    if pd.isna(cusip) or cusip == "":
        return cusip
    
    # Check length
    if len(cusip) != 9:
        return pd.NA
    
    # Check if all characters are alphanumeric
    if not cusip.isalnum():
        return pd.NA
    
    return cusip

def validate_lei(lei):
    """Validate LEI format: 20 characters, uppercase"""
    if pd.isna(lei) or lei == "":
        return lei
    
    # Check length
    if len(lei) != 20:
        return pd.NA
    
    # Check if all characters are alphanumeric
    if not lei.isalnum():
        return pd.NA
    
    # Convert to uppercase
    return lei.upper()

def validate_country_code(country_code):
    """Validate ISO-3166 alpha-2 country code structure: 2 uppercase letters"""
    if pd.isna(country_code) or country_code == "":
        return country_code
    
    # Check length and format: exactly 2 letters
    if len(country_code) != 2 or not country_code.isalpha():
        return pd.NA
    
    # Convert to uppercase
    return country_code.upper()

def validate_currency_code(currency_code):
    """Validate ISO-4217 currency code structure: 3 uppercase letters"""
    if pd.isna(currency_code) or currency_code == "":
        return currency_code
    
    # Check length and format: exactly 3 letters
    if len(currency_code) != 3 or not currency_code.isalpha():
        return pd.NA
    
    # Convert to uppercase
    return currency_code.upper()

def normalize_issuer_name(name):
    """Normalize issuer names: uppercase, remove diacritics"""
    if pd.isna(name) or name == "":
        return name
    
    # Remove diacritics (accents)
    normalized = unicodedata.normalize('NFD', str(name))
    without_diacritics = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    
    # Convert to uppercase
    upper_name = without_diacritics.upper()
    
    # Split into words and clean punctuation
    words = upper_name.split()
    normalized_words = []
    
    for word in words:
        # Remove punctuation
        clean_word = re.sub(r'[^\w\s]', '', word)
        if clean_word:
            normalized_words.append(clean_word)
    
    return ' '.join(normalized_words)

def validate_and_clean_data(df):
    """
    Apply validation checks to key fields in the dataframe.
    This should be called as a final step after data enrichment.
    """
    df = df.copy()
    
    print("\n" + "="*60)
    print("VALIDATION REPORT")
    print("="*60)
    
    # Apply ISIN validation
    if 'IDENTIFIER_ISIN' in df.columns:
        original = df['IDENTIFIER_ISIN'].copy()
        df['IDENTIFIER_ISIN'] = df['IDENTIFIER_ISIN'].apply(validate_isin)
        # Count how many were set to NA (excluding originally missing)
        originally_not_na = original.notna()
        newly_na = originally_not_na & df['IDENTIFIER_ISIN'].isna()
        na_count = newly_na.sum()
        total_count = originally_not_na.sum()
        pct = (na_count / total_count * 100) if total_count > 0 else 0
        print(f"IDENTIFIER_ISIN: {na_count:,} values set to missing ({pct:.1f}%)")
    
    # Apply CUSIP validation
    if 'ISSUER_CUSIP' in df.columns:
        original = df['ISSUER_CUSIP'].copy()
        df['ISSUER_CUSIP'] = df['ISSUER_CUSIP'].apply(validate_cusip)
        originally_not_na = original.notna()
        newly_na = originally_not_na & df['ISSUER_CUSIP'].isna()
        na_count = newly_na.sum()
        total_count = originally_not_na.sum()
        pct = (na_count / total_count * 100) if total_count > 0 else 0
        print(f"ISSUER_CUSIP: {na_count:,} values set to missing ({pct:.1f}%)")
    
    # Apply LEI validation
    if 'LEI' in df.columns:
        original = df['LEI'].copy()
        df['LEI'] = df['LEI'].apply(validate_lei)
        originally_not_na = original.notna()
        newly_na = originally_not_na & df['LEI'].isna()
        na_count = newly_na.sum()
        total_count = originally_not_na.sum()
        pct = (na_count / total_count * 100) if total_count > 0 else 0
        print(f"LEI: {na_count:,} values set to missing ({pct:.1f}%)")
    
    # Apply country code validation
    if 'INVESTMENT_COUNTRY' in df.columns:
        original = df['INVESTMENT_COUNTRY'].copy()
        df['INVESTMENT_COUNTRY'] = df['INVESTMENT_COUNTRY'].apply(validate_country_code)
        originally_not_na = original.notna()
        newly_na = originally_not_na & df['INVESTMENT_COUNTRY'].isna()
        na_count = newly_na.sum()
        total_count = originally_not_na.sum()
        pct = (na_count / total_count * 100) if total_count > 0 else 0
        print(f"INVESTMENT_COUNTRY: {na_count:,} values set to missing ({pct:.1f}%)")
    
    # Apply currency code validation
    if 'CURRENCY_CODE' in df.columns:
        original = df['CURRENCY_CODE'].copy()
        df['CURRENCY_CODE'] = df['CURRENCY_CODE'].apply(validate_currency_code)
        originally_not_na = original.notna()
        newly_na = originally_not_na & df['CURRENCY_CODE'].isna()
        na_count = newly_na.sum()
        total_count = originally_not_na.sum()
        pct = (na_count / total_count * 100) if total_count > 0 else 0
        print(f"CURRENCY_CODE: {na_count:,} values set to missing ({pct:.1f}%)")
    
    # Apply issuer name normalization (these don't set to NA, just normalize)
    if 'ISSUER_NAME' in df.columns:
        df['ISSUER_NAME'] = df['ISSUER_NAME'].apply(normalize_issuer_name)
        print(f"ISSUER_NAME: normalized (no values set to missing)")
    
    if 'ISSUER_TITLE' in df.columns:
        df['ISSUER_TITLE'] = df['ISSUER_TITLE'].apply(normalize_issuer_name)
        print(f"ISSUER_TITLE: normalized (no values set to missing)")
    
    print("="*60)
    
    return df
