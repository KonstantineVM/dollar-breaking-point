*-----------------------------------------------------------
* Housekeeping and loading unique portfolio holdings data
*-----------------------------------------------------------
* Accept arguments from NPORT_Master.do
args quarter cleaned_quarters_dir extra_data_dir masterfile_data_dir
global quarter = "`quarter'"

* Set paths
local input_folder "`cleaned_quarters_dir'"
local output_folder "`masterfile_data_dir'"

* Create output folder if it does not exist
cap mkdir "`output_folder'"

* Load master holding ID file
use "`extra_data_dir'/nport_unique_portfolio_holdings.dta", clear

* Filter to current quarter report
keep if quarter_report == yq(real(substr("$quarter",1,4)), real(substr("$quarter",6,1)))

* Collect all quarter-reference values needed
glevelsof quarter_reference, local(ref_quarters) clean
display "Quarter references needed: `ref_quarters'"

* Loop over each quarter reference to get portfolio info
foreach qref of local ref_quarters {
    display "Merging with quarter_reference: `qref'"
    
    * Check if the cleaned quarter file exists
    capture confirm file "`input_folder'/`qref'.dta"
    if _rc != 0 {
        display as error "Warning: File `qref'.dta not found, skipping..."
        continue
    }
    
    * Load the relevant cleaned quarter file (data is unique on holding_id)
    qui mmerge accession_number holding_id using "`input_folder'/`qref'.dta", ///
        type(1:1) udrop(quarter_reference quarter_report) unmatch(master) update
    
    * Validate merge results
    qui count if _merge == 1
    local unmatched_master = r(N)
    qui count if _merge == 3  
    local matched = r(N)
    
    display "  - Matched: `matched', Unmatched from master: `unmatched_master'"
    
    * Check for critical missing data in matched observations
    qui count if _merge == 3 & missing(cik)
    if r(N) > 0 {
        display as error "Warning: `r(N)' matched observations missing CIK for quarter `qref'"
    }
    
    drop _merge
}

* Adjust quarter_reference to date format
rename quarter_reference quarter_reference_temp
gen quarter_reference = yq(real(substr(quarter_reference_temp,1,4)), real(substr(quarter_reference_temp,6,1)))
format quarter_reference %tq
drop quarter_reference_temp

* Compress file
compress

* Save masterfile for each quarter
save "`output_folder'/${quarter}.dta", replace