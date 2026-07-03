*-----------------------------------------------------------
* Housekeeping and loading cleaned data
*-----------------------------------------------------------
* Accept arguments from NPORT_Master.do
args cleaned_quarters_dir extra_data_dir

clear

* Define paths
local input_folder "`cleaned_quarters_dir'"
local output_folder "`extra_data_dir'"

* Get list of .dta files
local files : dir "`input_folder'" files "*.dta"

* Create output folder if it doesn't exist
cap mkdir "`output_folder'"

* Loop over each file and append to create master dataset
foreach f of local files {
    append using "`input_folder'/`f'"
}

* Display total observations loaded
qui count
display "Total observations loaded: " r(N)

*-----------------------------------------------------------
* Create unique portfolio holdings dataset
*-----------------------------------------------------------
* Generate fund-report identifier for cross-quarter deduplication
qui gen report_date_day = dofc(report_date)
gegen fund_report = group(fund_key report_date_day)

* For each fund-report date, find the most recent filing across all quarters
* Obs.: Handling cases where old portfolio data appears in newer N-PORT filings
preserve
    * Create mapping of most recent filing per fund-report combination
    gcollapse (max) latest_filing_date = filing_date, by(fund_report fund_key report_date_day)

    * Get the accession numbers for these latest filings
    tempfile latest_filings
    save `latest_filings'
    restore

    * Merge back with full data to get accession numbers of latest filings
    mmerge fund_report fund_key report_date_day using `latest_filings', type(n:1) ukeep(latest_filing_date)
    assert _merge == 3
    drop _merge

    * Keep only observations from the most recent filing for each fund-report
    qui gen keep_flag = (filing_date == latest_filing_date)

    * Display summary statistics
    qui count if keep_flag == 1
    local kept = r(N)
    qui count if keep_flag == 0
    local dropped = r(N)
    display "Cross-quarter deduplication: keeping `kept' observations, dropping `dropped' outdated reports"

    * Apply the filter to keep only most recent data
    qui keep if keep_flag == 1

    * Create final mapping file with unique accession numbers
    preserve
    keep accession_number fund_key report_date_day filing_date
    gduplicates drop
    save "`output_folder'/nport_unique_report_fund_map.dta", replace
restore

* Clean up temporary variables
drop report_date_day fund_report latest_filing_date keep_flag

* Drop temporary variables
keep accession_number holding_id currency_value quarter_reference quarter_report

* Save unique portfolio holdings dataset
save "`output_folder'/nport_unique_portfolio_holdings.dta", replace
