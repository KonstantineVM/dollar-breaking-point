# N-PORT Dataset Processing Pipeline

## I. INTRODUCTION

This repository contains a full pipeline to download, parse, clean, and assemble SEC N-PORT filings into research-ready datasets. N-PORT forms are quarterly filings from registered investment companies and include detailed portfolio holdings.

The pipeline uses a mix of Bash, Python, and Stata. The directory contains the following files:

- README.md (this file)
- A_download_nport.sh -- Bash script to download and unzip SEC N‑PORT quarterly data zips.
- B_processing_functions_nport.py -- Library of Python helpers for processing TSVs.
- C_nport_build.py -- Python script that orchestrates a single‑quarter build.
- D_clean_quarters.do -- Stata script that cleans a single-quarter processed data.
- E_unique_report_holding_ids.do -- Stata script that standardizes holding IDs
- F_masterfile_quarters.do -- Stata script that builds standardized and cleaned masterfile
- NPORT_Master.do -- Stata controller

## II. ONE-TIME SETUP

You must set your paths so outputs are created in the right place.

### Edit NPORT_Master.do

The base path refers to the folder containing NPORT_Master.do. Data created by the pipeline are automatically saved under that path in new subfolders (i.e., raw, processed, cleaned, extra, and masterfile).

Set a contact email (used in the SEC request headers) before downloading N-PORT TSV files:

global sec_email "your_email@institution.edu"

You can specify which quarters to include in NPORT_Master.do using:

local startq = "2019q4"

local endq   = "2024q4"

If your Stata environment requires user-contributed packages (egenmore, mmerge, ftools, gtools), simply un-comment the corresponding ssc install lines near the top of NPORT_Master.do

If you are missing python packages, for example pandas, run the following command to install them:

pip3 install pandas

## Running the pipeline

stata-mp -b do NPORT_Master.do
