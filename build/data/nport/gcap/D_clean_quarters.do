*-----------------------------------------------------------
* Load processed data
*-----------------------------------------------------------
* Accept arguments from NPORT_Master.do: quarter, processed_quarters_dir, cleaned_quarters_dir
args quarter processed_quarters_dir cleaned_quarters_dir
global quarter = "`quarter'"

* Parse year and quarter number from the string (e.g., 2020q3)
local year = substr("$quarter", 1, 4)
local qnum = substr("$quarter", 6, 1)
if `qnum' == 1 {
    local previous_qnum = 4
    local previous_year = `year' - 1
}
else {
    local previous_qnum = `qnum' - 1
    local previous_year = `year'
}

* Load input data
use "`processed_quarters_dir'/${quarter}.dta", clear
qui rename *, lower

*-----------------------------------------------------------
* Cleaning process: keep last-updated report within quarters
*-----------------------------------------------------------
* Construct fund identifier
qui gen fund_key = cik + "_" + series_id + "_" + series_lei if !missing(series_id) & !missing(series_lei)
qui replace fund_key = cik + "_" + series_id + "_notlei" if !missing(series_id) & missing(series_lei)
qui replace fund_key = cik + "_notid_" + series_lei if missing(series_id) & !missing(series_lei)
qui replace fund_key = cik + "_notid_notlei" if missing(series_id) & missing(series_lei)

* Convert report date to daily
qui gen report_date_day = dofc(report_date)

* Generate a (numeric) fund-report identifier
qui egen fund_report = group(fund_key report_date_day)

* For each fund-report date, find the latest (P/A) filing date
qui gegen pa_filing_date = max(filing_date) if sub_type == "NPORT-P/A", by(fund_report)
qui gegen max_pa_date = max(pa_filing_date), by(fund_report)

* Drop NPORT-P filings if a newer P/A exists for same fund-report date
qui gen drop_flag = sub_type == "NPORT-P" & !missing(max_pa_date) & filing_date <= max_pa_date
qui drop if drop_flag == 1
drop drop_flag report_date_day fund_report pa_filing_date max_pa_date sub_type

* Drop missing and zero values
qui drop if missing(currency_value)
qui destring currency_value, replace force
qui drop if currency_value == 0

* Adjust quarter variables
rename quarter quarter_reference
gen quarter_report = yq(year(dofc(report_date)), quarter(dofc(report_date)))
format quarter_report %tq

* Save output
save "`cleaned_quarters_dir'/`previous_year'q`previous_qnum'.dta", replace

* Confirmation message
display "${quarter} --> `previous_year'q`previous_qnum' cleaned."
