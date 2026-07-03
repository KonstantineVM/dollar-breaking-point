* ---------------------------------------------------------------------------------------------------
* NPORT_Master.do: This file dispatches jobs for NPORT data processing
* Runs sequentially A-F, from downloading to cleaning
* ---------------------------------------------------------------------------------------------------

clear all
version 16
set more off
// qui do ~/profile.do

* ---------------------------------------------------------------------------------------------------
* Core globals: paths and email (to perform SEC download)
* ---------------------------------------------------------------------------------------------------

* Set base bath where code and data reside
global base_path = "`c(pwd)'"

* Other core paths
global raw_data "$base_path/raw"
global output_data "$base_path/output"

* Output directories
global processed_data "$output_data/processed"
global cleaned_data "$output_data/cleaned"
global extra_data "$output_data/extra"
global masterfile_data "$output_data/masterfile"
global logs_dir "$output_data/logs"

* Python environment
global python_path "python3"

* Email for SEC downloads
global sec_email "youremail@institution.edu"

* ---------------------------------------------------------------------------------------------------
* Quarter range
* ---------------------------------------------------------------------------------------------------
local startq = "2019q4"
local endq   = "2020q1"

* Expand start/end into a space-separated list
local y  = real(substr("`startq'",1,4))
local q  = real(substr("`startq'",6,1))
local y2 = real(substr("`endq'",1,4))
local q2 = real(substr("`endq'",6,1))

local qlist ""
while ( `y' < `y2' ) | ( `y' == `y2' & `q' <= `q2' ) {
    local qlist `qlist' `y'q`q'
    local q = `q' + 1
    if `q' == 5 {
        local q = 1
        local y = `y' + 1
    }
}
global quarters_all "`qlist'"
display as text "Will process quarters: $quarters_all"

* ---------------------------------------------------------------------------------------------------
* Create folder structure
* ---------------------------------------------------------------------------------------------------

cap mkdir "$raw_data"
cap mkdir "$output_data"
cap mkdir "$processed_data"
cap mkdir "$cleaned_data" 
cap mkdir "$extra_data"
cap mkdir "$masterfile_data"
cap mkdir "$logs_dir"

* ---------------------------------------------------------------------------------------------------
* Install required Stata packages
* ---------------------------------------------------------------------------------------------------

cap ssc install egenmore
cap ssc install mmerge
cap ssc install ftools
cap ssc install gtools

* ---------------------------------------------------------------------------------------------------
* Sequential pipeline (A-F)
* ---------------------------------------------------------------------------------------------------

* A. Download N-PORT source zips
display as text "A) Downloading N-PORT data for: $quarters_all"
! bash "$base_path/A_download_nport.sh" "$raw_data" "$sec_email" "$quarters_all" > "$logs_dir/download_nport.log" 2>&1

* B. Build processed quarterly data
display as text "B) Building processed quarterly data (Python)"
foreach quarter of global quarters_all {
    display as text "   Building `quarter' ..."
    ! $python_path "$base_path/C_nport_build.py" "`quarter'" "$base_path" "$raw_data" "$processed_data" > "$logs_dir/build_`quarter'.log" 2>&1
    capture confirm file "$processed_data/`quarter'.dta"
    if _rc != 0 {
        display as error "ERROR: Build output missing for `quarter'. See: $logs_dir/build_`quarter'.log"
        exit 198
    }
}

* C. Clean each quarter
display as text "C) Cleaning quarterly files"
foreach quarter of global quarters_all {
    display as text "   Cleaning `quarter' ..."
    do "$base_path/D_clean_quarters.do" "`quarter'" "$processed_data" "$cleaned_data"
}

* D/E. Create unique portfolio holdings once
display as text "D) Creating unique portfolio holdings"
do "$base_path/E_unique_portfolio_holdings.do" "$cleaned_data" "$extra_data"
capture confirm file "$extra_data/nport_unique_portfolio_holdings.dta"
if _rc != 0 {
    display as error "ERROR: Unique portfolio holdings file missing. Expected at $extra_data/nport_unique_portfolio_holdings.dta"
    exit 198
}

* F. Build masterfiles for each quarter
display as text "E) Building masterfiles per quarter"
foreach quarter of global quarters_all {
    display as text "   Masterfile `quarter' ..."
    do "$base_path/F_masterfile_quarters.do" "`quarter'" "$cleaned_data" "$extra_data" "$masterfile_data"
    capture confirm file "$masterfile_data/`quarter'.dta"
    if _rc != 0 {
        display as error "ERROR: Masterfile missing for `quarter'."
        exit 198
    }
}

display as result "N-PORT pipeline completed successfully for: $quarters_all"
exit 0
