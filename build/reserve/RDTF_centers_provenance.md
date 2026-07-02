# RDT-F custody-center set — grounding provenance (Phase 1, grounding only; no estimation, no verdict)

Date grounded: 2026-07-02.
Governing rule: `build/reserve/RDTF_prediction.md` (committed 6701b5c), "The custody-center set (DERIVED, not chosen)" — a jurisdiction enters IF AND ONLY IF a retained or fetched PUBLISHER document names it as a custodial / ICSD / attribution-bias center, with the grounding line quoted verbatim; beneficial-owner jurisdictions (CYM/HKG/VGB per the DP-era tagging) do NOT enter unless a publisher line independently names them as custodial attribution-bias centers.

Machine-readable companion: `build/reserve/RDTF_centers_manifest.json`.
Fetch/retention log for this stage: `build/reserve/rdtf_evidence/_RDTF_fetch_log.txt`.

## Publisher documents relied on (all on disk)

| Document | Path (raw) | Publisher URL | Fetched |
|---|---|---|---|
| SHL 2025 survey report, "Foreign Portfolio Holdings of U.S. Securities as of June 30, 2025" | `build/reserve/rdtb_evidence/shl2025r.pdf` (extraction `.../shl2025r_extracted.txt`) | https://www.treasury.gov/resource-center/data-chart-center/tic/Documents/shl2025r.pdf | 2026-07-02 |
| TIC FAQ part 2 ("Frequently Asked Questions Regarding the TIC System and TIC Data") | `build/reserve/rdtd_evidence/tic_faq2.html` (reading aid `build/reserve/rdtf_evidence/tic_faq2_extracted.txt`) | https://home.treasury.gov/data/treasury-international-capital-tic-system-home-page/frequently-asked-questions-regarding-the/ticfaq2 | 2026-07-02 |
| MFH methodology note ("New Methodology for Estimating Major Foreign Holders of Treasury Securities", 2/29/2012, with 5/15/2006 archive) | `build/reserve/rdte_evidence/method_mfh_legacy.html` (reading aid `build/reserve/rdtf_evidence/method_mfh_legacy_extracted.txt`) | http://www.treasury.gov/resource-center/data-chart-center/tic/Pages/method-mfh.aspx | 2026-07-02 |
| MFH history table (group-membership footnote) | `build/reserve/rdt_evidence/tic/mfhhis01.txt` | https://treasury.gov/resource-center/data-chart-center/tic/Documents/mfhhis01.txt | 2026-07-01 |

No new fetch was needed for Deliverable 1 — the on-disk record carried every grounding line. (The one new fetch this stage, the H.4.1 release, belongs to Deliverable 2; see `RDTF_basis_quotes.md`.)

## Centers that ENTER (5 entries: 4 jurisdictions + 1 publisher grouping)

### 1. Belgium (BEL), 2. Luxembourg (LUX), 3. Switzerland (CHE), 4. United Kingdom (GBR)

Primary grounding line — SHL 2025, Section 4.3.4 "Reporting Basis: Country of Residence" (`shl2025r_extracted.txt` lines 2016-2019), verbatim:

> "Third, chains of foreign financial intermediaries are often involved in the custody or management of securities. This “custodial bias” tends to overstate the amounts of holdings by residents of countries with major custodial activities such as Belgium, Luxembourg, Switzerland, and the United Kingdom. For example, a resident of Germany may buy a U.S. security and place it in the custody of a Swiss bank."

ICSD line for Belgium and Luxembourg — SHL 2025, same section (lines 2010-2015; the extraction interleaves the page-break string "54 Foreign Portfolio Holdings of U.S. Securities as of June 30, 2025" mid-sentence), verbatim:

> "Second, many registered U.S. securities are issued abroad, and these securities typically trade in book-entry form, with settlement and custody occurring at international central securities depositories (ICSDs). Prominent ICSDs are Euroclear in Belgium and Clearstream in Luxembourg. U.S. survey reporters typically report only the country where the ICSD is located and thus large foreign holdings are attributed to these countries."

Concurring TIC lines — TIC FAQ 7 (`tic_faq2.html`; extraction line ~390):

> "For example, a German investor may buy a U.S. security and place it in the custody of a Swiss bank. In the surveys of foreign holdings of U.S. securities, such a holding is recorded against Switzerland rather than Germany. This \"custodial bias\" contributes to the large recorded foreign holdings of U.S. securities in major financial centers, such as Belgium, the Caribbean banking centers, Luxembourg, Switzerland, and the United Kingdom."

and, for the United Kingdom specifically, the FAQ 7 worked example:

> "This relatively high level of U.K. holdings primarily reflects the custodial bias of the United Kingdom: at $135.7 billion, the United Kingdom was the eighth largest recorded foreign holder of U.S. Treasuries."

and the MFH methodology note (`method_mfh_legacy.html`; extraction line 339):

> "This “custodial bias” contributes to the large recorded holdings in major custodial centers including Belgium, the Caribbean banking centers, Luxembourg, Switzerland, and the United Kingdom."

Every one of BE/LU/CH/UK is named in an unambiguous publisher custodial-bias line in the current-vintage SHL report AND in two TIC methodology documents. They enter.

### 5. Caribbean banking centers (CARIB-BC) — a TIC publisher GROUPING, not a single jurisdiction

Grounding lines: the MFH methodology note calls the group one of the "major custodial centers" (quote above), and TIC FAQ 7 names it inside the custodial-bias sentence (quote above). Under the mechanical rule the group is named as a custodial attribution-bias center by the publisher, so it enters — at the grouping level, exactly as named.

Publisher-defined membership:
- `mfhhis01.txt` footnote 4 (lines 1287-1288), verbatim: "Caribbean Banking Centers include Bahamas, Bermuda, Cayman Islands, Netherlands Antilles, and Panama. Beginning with new series for June 2006, also includes British Virgin Islands. This aggregate of countries was discontinued after data for February 2016."
- SHL 2025 Section 3.3 (lines 1739-1740), the closely related SHL grouping, verbatim: "Caribbean financial centers are Bermuda; Bonaire, Sint Eustatius, and Saba; British Virgin Islands; Cayman Islands; Curacao; and Panama."

**Plainly stated assembly caveat:** the custodial naming exists ONLY at group level. No member jurisdiction is individually named as a custodial center by any publisher line found, and two members (Cayman Islands, British Virgin Islands) are exactly the jurisdictions the pre-registration's zero-guard tags as beneficial-owner. The TIC aggregate line for the group was discontinued after February 2016 data, so it has no direct country line on the RDT-F verdict axis (2023-05..2026-04). How (and whether) the group-level naming can be operationalized without individually admitting beneficial-owner members is an assembly-stage decision that must be reported, not a grounding fact; this file records the quotes only.

## Candidates recorded as AMBIGUOUS (not entered; listed for the assembly to report)

### Cayman Islands (CYM), as an individual jurisdiction
No publisher line names Cayman individually and unambiguously as a custodial/ICSD/attribution-bias center. The nearest lines, verbatim:

- SHL 2025 lines 1814-1816 (conjunctive — does not separate custody from offshore issuance): "Differences are concentrated in countries that are hubs for offshore debt issuance and securities custody businesses: the United Kingdom, Cayman Islands, Luxembourg, and Belgium."
- SHL 2025 lines 678-683 (disjunctive, and the publisher's own follow-on sentence classifies Cayman in the fund/beneficial-owner subset): "Among the top foreign holders are financial centers — such as the Cayman Islands, the United Kingdom, Luxembourg, Ireland, and Switzerland — in which substantial amounts of securities owned by residents of other countries are managed or held in custody. Moreover, three of these financial centers — the Cayman Islands, Luxembourg, and Ireland — have large financial industries with many international investment funds whose holders need not be, and often are not, residents of those countries."
- SHL 2025 lines 1686-1688 (beneficial-owner characterization): "In addition, funds with legal residence outside the United States (for example, in the Cayman Islands) can and do hold securities on behalf of residents of other countries, including the United States."

Cayman is a member of the CARIB-BC group named in the custodial-bias lines; a group mention is not the independent individual naming the zero-guard requires. AMBIGUOUS; not entered.

### Ireland (IRL)
Named only in disjunctive "financial centers" lines and explicitly classified by the publisher in the investment-fund subset. Verbatim (SHL 2025 lines 1670-1674): "Financial centers: These countries manage or hold in custody substantial amounts of securities owned by residents of other countries or have a large financial industry with many international investment funds whose holders need not be, and often are not, residents of those countries. These countries include the Cayman Islands, Ireland, Luxembourg, Switzerland, and the United Kingdom." Neither the SHL custodial-bias passage, nor TIC FAQ 7, nor the MFH methodology note names Ireland. AMBIGUOUS; not entered.

## Candidates REJECTED

### Hong Kong (HKG)
No custodial/ICSD/attribution-bias line names Hong Kong in any retained or fetched publisher document (searched: SHL 2025 full text; TIC FAQ part 2; MFH methodology note; MFH history footnotes; TIC securities(b) page). Its only classificatory mention in SHL 2025 is geographic-group membership (lines 1735-1738): "Advanced foreign economies (AFE) include ... Hong Kong; ...". The DP-era offshore-hub tagging of HKG is beneficial-owner taxonomy. Rejected.

### British Virgin Islands (VGB), as an individual jurisdiction
No individual custodial line. Appears only as a member of the publisher-defined Caribbean groupings (SHL 2025 lines 1739-1740; mfhhis01.txt footnote 4, member from June 2006). Group membership is recorded under CARIB-BC and is not an individual naming. Rejected individually.

## Result

The grounded custody-center set is: **Belgium, Luxembourg, Switzerland, United Kingdom, plus the publisher grouping "Caribbean banking centers" (group level only, with the assembly caveat above)**. Ireland and Cayman Islands (individually) are AMBIGUOUS and excluded; Hong Kong and British Virgin Islands (individually) are rejected. No center entered or exited by choice; every entry and exclusion above carries its verbatim publisher line and on-disk path.
