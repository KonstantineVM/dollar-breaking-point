# RDT-D Part 2 — TIC "China, Mainland" vs the SAFE reserve pool: the perimeter determination

**A documentary determination from public definitions only. No number is fabricated; where the split
is not publicly decomposable it is stated as a BOUND with direction. All sources fetched 2026-07-02
and retained in `build/reserve/rdtd_evidence/` (see `_RDTD_fetch_log.txt`).**

## The two perimeters, as their publishers define them

**Claim 1 — TIC attribution is residence-of-holder as recorded by U.S.-resident reporters.**
- SUBJECT-DRIVER: TIC SHL/SLT/MFH country attribution.
- The SHL survey records "the country of holder ... based on the residence of the security owner",
  collected only from U.S.-resident custodians/issuers/end-investors; where a chain of foreign
  intermediaries intervenes, the security is attributed to the first foreign country in the chain
  visible to the U.S. reporter ("custodial bias", worked German-investor/Swiss-custodian example).
- BOUNDARIES: attribution is legal residence, not nationality and not beneficial ownership through
  chains; MFH monthly estimates ride on TIC SLT (holdings) and BL2.
- FALSIFIER: publisher text stating beneficial-owner look-through for MFH/SLT/SHL. Not found.
- SOURCE: `tic_shl2025r.pdf` §4.3.4 "Reporting Basis: Country of Residence" (fetched 2026-07-02 from
  https://www.treasury.gov/resource-center/data-chart-center/tic/Documents/shl2025r.pdf);
  `tic_faq2.html` FAQ #7 (https://home.treasury.gov/data/treasury-international-capital-tic-system-home-page/frequently-asked-questions-regarding-the/ticfaq2);
  `tic_mfh.txt` footnote 1/ ("U.S. securities held in overseas custody accounts may not be attributed
  to the actual owners"; MFH based on TIC SLT and BL2) (https://ticdata.treasury.gov/Publish/mfh.txt;
  the retained file is the publisher's snapshot dated March 15, 2023 — the footnote, not the data,
  is what is used here).

**Claim 2 — "China, Mainland" in TIC covers ALL mainland-resident holders, official and private,
with no published per-country official/private split.**
- TIC's Foreign Official Institutions "consist primarily of foreign national government institutions
  involved in the formulation of monetary policy, such as central banks, but also include national
  government-owned investment funds, including sovereign wealth funds, and other national government
  institutions" — i.e., in TIC terms both SAFE/PBoC **and CIC** are FOIs, and Chinese-resident banks,
  funds and private investors are additionally inside "China, Mainland".
- The official/private split is published only as **all-country aggregates** (SHL Exhibits 7–8; the
  MFH "Of which: For. Official" grand-total block). The by-country tables carry totals only.
  "Mainland China excludes Hong Kong and Macau, which are reported separately."
- The publisher itself warns the sector split is imperfect: "Distinguishing official from private
  holders can be difficult because chains of financial intermediaries can obscure the true foreign
  holders. As such, some holdings attributed to private intermediaries, especially in major custodial
  centers, may reflect holdings of foreign official institutions."
- FALSIFIER: a published TIC table of China-specific FOI holdings. Not found in the retained
  publisher documents (SHL 2025 report; MFH table; TIC FAQ).
- SOURCE: `tic_shl2025r.pdf` (glossary "Foreign Official Institutions (FOIs)"; Exhibits 7–8; note to
  Exhibit 7; country tables), `tic_mfh.txt`.

**Claim 3 — the SAFE reserve pool is Section I.A "official reserve assets", the assets under the
monetary authorities' control that SAFE manages by statute.**
- Reserve assets are "those external assets that are readily available to and controlled by the
  monetary authorities" (IMF template guideline para. 59, quoting BPM6 6.64); SAFE's stated function
  7 is "to undertake operations and management of foreign exchange reserves, gold reserves, and
  other foreign exchange assets of the state."
- The template's own Section I.B ("other foreign currency assets — securities not included in
  official reserve assets": 1,605.36 亿USD = **160.536 $bn at 2026-05**, read from the retained
  2026-05 file) is the publisher's own line showing official Chinese foreign-currency securities
  that sit **outside** the reserve pool. The publisher does not state which entity holds I.B, so no
  entity attribution is claimed for it.
- BOUNDARIES: I.B covers monetary authorities' and central government's non-reserve FX assets per
  the IMF guideline; whether CIC or state-bank portfolios are inside I.B is **not stated by SAFE**
  and is not asserted here.
- SOURCE: `imf_reserves_template_guide2013.pdf` para. 59 (fetched 2026-07-02 from
  https://www.imf.org/external/np/sta/ir/IRProcessWeb/pdf/guide2013.pdf);
  `safe_en_major_functions.html` (https://www.safe.gov.cn/en/MajorFunctions/index.html);
  `raw_004_8f67a8316b9e4b10a4d489601dc8bb04.xls` (SAFE 2026-05 template, Sections I.A/I.B).

**Claim 4 — CIC is a mainland-resident holder of U.S. securities OUTSIDE the reserve pool.**
- CIC's own FAQ: "CIC was initially capitalized with $200 billion in reserves **purchased from** the
  People's Bank of China **in exchange for** RMB1,550 billion in sovereign bonds issued by the
  Ministry of Finance" — the FX was bought out of the reserve pool against MoF bonds, which is the
  publicly groundable form of CIC's "not reserves" characterization (a literal sentence "CIC's assets
  are not reserves" does not appear on the retained CIC pages; the exchange-capitalization statement
  is what is asserted). CIC describes itself as "a vehicle to diversify China's foreign exchange
  holdings", headquartered in Beijing (mainland-resident), whose portfolio includes public equities,
  bonds, and "cash products and others include cash, overnight deposits, **US Treasury bills**, etc."
- Consequence: CIC's U.S. securities, where visible to U.S. custodians as China-resident, sit inside
  TIC "China, Mainland" (and inside TIC's FOI aggregate) but outside SAFE's I.A reserve pool.
- CIC does not publish its U.S.-securities holdings; no figure is available to size this wedge.
- SOURCE: `cic_faqs.html` (http://www.china-inv.cn/chinainven/home/FAQs.shtml),
  `cic_who_we_are.html` (http://www.china-inv.cn/en/About_CIC/Who_We_Are.shtml).

**Claim 5 — state banks' own FX portfolios are mainland-resident holdings outside I.A.**
- Under the IMF control criterion (Claim 3), commercial banks' own FX portfolios are not "readily
  available to and controlled by the monetary authorities" and so are outside reserve assets, while
  the banks are mainland-resident and hence inside TIC "China, Mainland" where U.S.-custodied.
- The recurrent claim that PBoC/SAFE places **entrusted reserve funds** with state banks (which
  would blur this line) is **NOT-AVAILABLE from primary sources**: neither SAFE nor the banks
  publish such a decomposition; treatments of it exist only in secondary literature (tier:
  SECONDARY, not fetched, not used, not quantified here).
- SOURCE: `imf_reserves_template_guide2013.pdf` para. 59 (definition); absence-of-disclosure checked
  on `safe_en_major_functions.html` and the retained SAFE template files.

## DETERMINATION

1. **Containment.** TIC "China, Mainland" ⊇ {SAFE reserve-pool holdings of U.S. securities **that
   are held through custody chains recording a mainland-China-resident holder to the U.S.
   reporter**}. It is **not** a superset of the reserve pool's total U.S. holdings: reserve
   securities custodied at third-country custodians/ICSDs (Euroclear/Belgium, Clearstream/Luxembourg,
   UK, Switzerland — the publisher's own named custodial-bias centers) are attributed to those
   countries, not to China (Claim 1). Symmetrically, TIC-China is not contained in the reserve pool,
   because it includes CIC, state banks, and private mainland residents (Claims 2, 4, 5). **Neither
   perimeter contains the other.**
2. **Quantifiability of the excess.** The non-reserve mainland share of TIC-China is **not publicly
   quantifiable**: TIC publishes no per-country official/private split (Claim 2); SAFE publishes no
   custody-geography or counterpart-country detail for the reserve pool (the SDDS template's only
   geography is the deposits counterpart-bank headquarters split, and deposits are 0.06%–1.36% of
   the FX line — see `rdtd_sdds_manifest.json`); CIC publishes no U.S.-securities figure (Claim 4).
   No secondary estimate is promoted to fill this.
3. **The BOUND on the identity, with direction of each bias.** As pre-registered
   (`RDTD_prediction.md`, pool caveat): (i) **non-reserve mainland holders make TIC-China OVERSTATE
   the reserve pool's U.S. holdings** — ΔH_us_LT and the 446.5 active-flow leg attribute to "China"
   movements that may belong to CIC/state-bank/private portfolios outside the pool; (ii) **custody
   masking cuts the other way** — reserve holdings custodied via Belgium/Luxembourg/UK are invisible
   to TIC-China, so TIC-China UNDERSTATES the pool's total U.S. holdings, and shifts between direct
   and third-country custody masquerade as Chinese sales/purchases. The two wedges have opposite
   signs and unknown magnitudes; the identity therefore carries them as a stated bound, with the
   pre-registered CN+BE+LU custody variant (RDT-C, active flow 326.323 vs 446.493 $bn China-alone)
   as the on-ledger mitigation of wedge (ii). Wedge (i) has **no** on-ledger mitigation — it is an
   unquantified, direction-known overstatement and must be carried as such in every downstream use.
4. **What this forbids downstream.** Reading ΔH_us_LT (TIC-China) as "SAFE reserve sales/purchases
   of U.S. securities" without both wedges stated; using the SDDS securities line and TIC-China as
   if they had the same perimeter; promoting any secondary-source split of the wedges into the
   identity.

Files: all cited raw files in `build/reserve/rdtd_evidence/`; fetch log
`build/reserve/rdtd_evidence/_RDTD_fetch_log.txt` (all fetches 2026-07-02).
