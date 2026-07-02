# RDT-E Part 1(v) — Methodology determination for Cap C (the official-classification premise)

**Question (pre-registered, RDTE_prediction.md Cap C, condition (a)):** do the TIC methodology
documents establish that official money custodied at Euroclear/Clearstream (held via
Belgian/Luxembourg custodians) classifies as PRIVATE — or simply as Belgium/Luxembourg-resident
with no official attribution — in the TIC by-country and foreign-official-aggregate series?

**Determination: ESTABLISHED** (with the publisher's hedge words carried verbatim — see
"Exact scope and residual hedges" below).

Date of determination: 2026-07-02. All quotes below are verbatim from retained files on disk or
files fetched today into `build/reserve/rdte_evidence/`; file and URL given per quote.

---

## Leg 1 — Residency: Euroclear/Clearstream-custodied holdings are recorded as Belgium/Luxembourg-resident, not against the beneficial owner

**Q1.** Treasury, *Foreign Portfolio Holdings of U.S. Securities as of June 30, 2025* (SHL 2025
report), Section 4.3.4 (report p. 54). File: `build/reserve/rdtb_evidence/shl2025r_extracted.txt`
(extraction of `shl2025r.pdf`, fetched 2026-07-02 per `rdtb_evidence/_RDTB_fetch_log.txt`); text
around extracted-file lines 2010–2015:

> "Second, many registered U.S. securities are issued abroad, and these securities typically trade
> in book-entry form, with settlement and custody occurring at international central securities
> depositories (ICSDs). Prominent ICSDs are Euroclear in Belgium and Clearstream in Luxembourg.
> U.S. survey reporters typically report only the country where the ICSD is located and thus large
> foreign holdings are attributed to these countries."

**Q2.** Same report, Glossary entry "Foreign country based on residence" (extracted-file lines
1682–1688):

> "In this report, holdings are reported by U.S. issuers and custodians based on the legal
> residence of the foreign holder. Thus, as discussed in more detail in the section on custodial
> bias in Section 3, if a foreign custodian holds securities on behalf of a third country, the TIC
> system records the holder country as the custodian's residence, not the country of residence of
> the custodian's customer."

**Q3.** Same report, Section 4.3.4, the custody-chain mechanism (extracted-file lines 2016–2028):

> "Third, chains of foreign financial intermediaries are often involved in the custody or
> management of securities. This 'custodial bias' tends to overstate the amounts of holdings by
> residents of countries with major custodial activities such as Belgium, Luxembourg, Switzerland,
> and the United Kingdom. For example, a resident of Germany may buy a U.S. security and place it
> in the custody of a Swiss bank. Normally the Swiss bank will then employ a U.S.-resident
> custodian bank to act as its sub-custodian to hold the security to facilitate settlement and
> custody operations in the United States. When portfolio surveys are conducted, information is
> collected only from U.S.-resident entities. Thus, the U.S.-resident bank, acting as the
> sub-custodian of the Swiss bank, will report this security on the survey. Because the U.S. bank
> will typically know only that it is holding the security on behalf of a Swiss bank, it will
> report the security as Swiss-held."

**Q4.** TIC FAQ #7 ("What are the problems of geographic attribution for securities holdings and
transactions in the TIC system?"). File: `build/reserve/rdtd_evidence/tic_faq2.html` (fetched 2026-07-02 from
https://home.treasury.gov/data/treasury-international-capital-tic-system-home-page/frequently-asked-questions-regarding-the/ticfaq2
per `rdtd_evidence/_RDTD_fetch_log.txt`):

> "For example, if a U.S. Treasury security purchased by a foreign resident is held in a custodial
> account in a third country, the true country of ownership of the security will not be reflected
> in the data."

and, same FAQ:

> "The country attribution of foreign holdings of U.S. securities as reported in the position
> surveys and in the SLT is imperfect because some foreign owners entrust the safekeeping of their
> securities to institutions that are neither in the United States nor in the owner's country of
> residence. For example, a German investor may buy a U.S. security and place it in the custody of
> a Swiss bank. In the surveys of foreign holdings of U.S. securities, such a holding is recorded
> against Switzerland rather than Germany. This 'custodial bias' contributes to the large recorded
> foreign holdings of U.S. securities in major financial centers, such as Belgium, the Caribbean
> banking centers, Luxembourg, Switzerland, and the United Kingdom."

**Q5.** Treasury, "Estimating Holdings of Treasury Securities" (the MFH methodology note). Fetched
2026-07-02 from https://www.treasury.gov/resource-center/data-chart-center/tic/Pages/method-mfh.aspx
(redirects to the live home.treasury.gov page); file:
`build/reserve/rdte_evidence/method_mfh_legacy.html`:

> "Imperfections caused by 'custodial bias' remain in the current MFH table. Some foreign owners
> entrust the safekeeping of their securities to institutions that are neither in the United States
> nor in the owner's country of residence. ... In both the SLT and the periodic surveys of holdings
> of long-term securities, such a holding will typically be recorded vis-a-vis Switzerland rather
> than Germany. This 'custodial bias' contributes to the large recorded holdings in major custodial
> centers including Belgium, the Caribbean banking centers, Luxembourg, Switzerland, and the
> United Kingdom."

**Leg-1 conclusion:** ESTABLISHED outright. The publisher states the rule (Q2: holder country =
custodian's residence, not the customer's), names Euroclear/Clearstream explicitly (Q1: holdings
"are attributed to these countries" — Belgium and Luxembourg), and repeats it across the SHL
report, the FAQ, and the MFH methodology note. Official money held via Euroclear/Clearstream is
therefore recorded on the Belgium/Luxembourg country lines with no attribution to the owner.

## Leg 2 — Sector: such holdings sit in the PRIVATE attribution, not the foreign-official aggregate

**Q6.** SHL 2025 report, note to Exhibit 7 ("U.S. Long-Term Securities by Foreign Holder Sector",
report p. 19–20). File: `build/reserve/rdtb_evidence/shl2025r_extracted.txt`, line 794:

> "Distinguishing official from private holders can be difficult because chains of financial
> intermediaries can obscure the true foreign holders. As such, some holdings attributed to
> private intermediaries, especially in major custodial centers, may reflect holdings of foreign
> official institutions."

This is the publisher stating, in its own sector-of-holder exhibit, that foreign-official money
held through intermediary chains in the major custodial centers (Belgium and Luxembourg are the
named ICSD hosts, Q1) is *attributed to private intermediaries* — i.e., it is counted in the
private sector, outside the foreign-official aggregate.

**Q7.** Mechanism consistency — TIC FAQ #10a ("How do the TIC data on Major Foreign Holders of
U.S. Treasury Securities compare with FRBNY custody holdings?"), file
`build/reserve/rdtd_evidence/tic_faq2.html`:

> "First, not all foreign official holdings of Treasury securities as reported by the TIC system
> are held at FRBNY. In particular, Treasury securities held by private custodians on behalf of
> foreign official institutions are included in the TIC but not in the FRBNY figures."

FAQ #10a shows the TIC official designation is what U.S. reporters can see: U.S. private custodians
who know their client is a foreign official institution report it as official. Under the custody
chain of Q3, the U.S. reporter for an Euroclear/Clearstream position sees only the ICSD (a private
foreign entity in Belgium/Luxembourg) — per Q2/Q3 it reports the position against the custodian it
sees; the official character of a beneficial owner behind the ICSD is not visible to the reporter.
Q6 states the resulting classification outcome explicitly.

**Leg-2 conclusion:** ESTABLISHED via Q6 (the publisher's own statement that FOI holdings behind
custodial-center intermediary chains land in the private attribution) combined with the reporting
rule Q2/Q3. No retained or fetched TIC document states or implies the contrary (that TIC sees
through Euroclear/Clearstream to an official owner); none was found in the SHL 2025 report, TIC
FAQ, or the MFH methodology note.

---

## Exact scope and residual hedges (stated, not smoothed over)

1. **No single sentence** in the retained documents names Euroclear/Clearstream + official +
   private in one breath. The determination is the joint reading of Q1 (Euroclear/Clearstream
   holdings attributed to Belgium/Luxembourg), Q2 (rule: custodian's residence, not the customer's),
   and Q6 (holdings attributed to private intermediaries in major custodial centers may in fact be
   foreign-official money). Each passage is the publisher's own, verbatim.
2. **Publisher hedge words carried:** Q1 "typically report only the country where the ICSD is
   located"; Q3 "will typically know only"; Q6 "some holdings ... may reflect". The hedges concern
   *which and how many* holdings are affected (unknowable to the publisher itself), not the
   direction of the classification rule. The rule as stated never runs the other way: no passage
   describes a channel by which an Euroclear/Clearstream-custodied position is recorded as
   foreign-official.
3. Consequence for Cap C condition (a): the premise is established — a foreign official institution
   relocating custody of U.S. Treasuries to Euroclear/Clearstream drops off its own country line
   and out of the TIC foreign-official aggregate, reappearing as Belgium/Luxembourg-resident
   private-attributed holdings. (Whether Cap C *grounds* also requires condition (b), the actual
   decline of the official aggregates over the window — computed in `rdte_official_manifest.json`;
   on the verdict axis the TIC official aggregate ROSE while the FRBNY custody series DECLINED.
   The cap is applied at the assembly stage, not here.)

## Sources checked (fetch dates)

- `build/reserve/rdtb_evidence/shl2025r_extracted.txt` (from `shl2025r.pdf`,
  https://www.treasury.gov/resource-center/data-chart-center/tic/Documents/shl2025r.pdf, fetched 2026-07-02T02:59:34Z per rdtb_evidence/_RDTB_fetch_log.txt, RDT-B stage).
- `build/reserve/rdtd_evidence/tic_faq2.html` (https://home.treasury.gov/data/treasury-international-capital-tic-system-home-page/frequently-asked-questions-regarding-the/ticfaq2, HTTP 200, fetched 2026-07-02 per rdtd_evidence/_RDTD_fetch_log.txt, RDT-D stage).
- `build/reserve/rdte_evidence/method_mfh_legacy.html` — Treasury "Estimating Holdings of Treasury
  Securities", https://www.treasury.gov/resource-center/data-chart-center/tic/Pages/method-mfh.aspx
  (200, resolves to the live page), fetched 2026-07-02 (this stage).
- Attempted (404, recorded in `rdte_evidence/_RDTE_fetch_log.txt`): a guessed home.treasury.gov
  path for the same methodology note; the legacy URL above succeeded instead.
