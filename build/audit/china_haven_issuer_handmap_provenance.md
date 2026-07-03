# China haven-issuer hand-map — provenance and sourcing standard

Artifact: `build/audit/china_haven_issuer_handmap.csv`
Built: 2026-06-29. Part of COVERAGE-MEASUREMENT Part 1, Deliverable B.
This is a SOURCED lookup only. It does NOT re-tag any holding and does NOT compute
coverage (Part 2, separate agent). The panel was not modified.

## Selection rule (targeted at the panel's largest haven issuers)
1. Profiled the panel's haven-resident subset (`is_haven_resident==True`, residence in
   CYM/HKG/VGB) of `build/data/nport/us_china_nationality_panel.parquet`, grouping by
   issuer_name and pooling `currency_value` (USD) across all 8 fiscal quarters. Ranked
   the top ~70 haven issuers by pooled value.
2. Among those large haven issuers, kept only the ones that are **Chinese by ultimate
   parent / operations** AND can be sourced to a public filing. The map is targeted at
   actual large holdings so it is neither padded nor thin.

## Sourcing standard (every row sourced; no guesses)
Each entry is a U.S.-SEC **foreign-private-issuer** that files **Form 20-F** and is a
China-concept stock: a Cayman/BVI holding company (matching N-PORT residence = haven)
whose 20-F discloses operations conducted in the PRC, in the standard China-concept
structure (consolidated affiliated entities / VIEs / PRC subsidiaries). The China-parent
(nationality = CN) claim is sourced to the issuer's SEC EDGAR registrant record and its
most recent 20-F. CIKs, registrant names, incorporation codes, and the latest 20-F
accession numbers were read live from the SEC submissions API
(`https://data.sec.gov/submissions/CIK<CIK>.json`) and EDGAR browse on 2026-06-29.

Verified registrants (CIK | SEC stateOfIncorporation | latest 20-F):
- Alibaba Group Holding Ltd — CIK 1577552 | K3 Cayman | 0001193125-26-231755 (2026-05-20)
- JD.com, Inc. — CIK 1549802 | E9 Cayman | 0001193125-26-157870 (2026-04-16)
- Baidu, Inc. — CIK 1329099 | Cayman | 0001193125-26-109289 (2026-03-17)
- NetEase, Inc. — CIK 1110646 | Cayman | 0001104659-26-043468 (2026-04-15)
- Trip.com Group Ltd — CIK 1269238 | Cayman | 0001193125-26-183379 (2026-04-28)
- PDD Holdings Inc. (fka Pinduoduo Inc.) — CIK 1737806 | E9 Cayman | 0001104659-26-050727 (2026-04-29)
- TAL Education Group — CIK 1499620 | Cayman | 0001104659-26-073410 (2026-06-12)
- ZTO Express (Cayman) Inc. — CIK 1677250 | Cayman | 0001104659-26-044613 (2026-04-17)
- H World Group Ltd (fka Huazhu Group Ltd) — CIK 1483994 | Cayman | 0001104659-26-048058 (2026-04-24)

The SEC submissions API confirmed business-address country = F4 (China) for JD.com, TAL,
ZTO, H World; the others report no business country but disclose PRC operations in the
20-F. The residence-vs-nationality gap is explicit in the SEC record: e.g. Alibaba's
stateOfIncorporation = K3 (Cayman, = N-PORT residence KY) while its operations and
ultimate parent are Chinese.

## Why a hand-map is needed (GLEIF cannot do this)
Deliverable A showed that ALL of these large VIE/ADR names resolve in GLEIF as
**SELF = KY** (Cayman): they have NO GLEIF Level-2 parent relationship and their own
GLEIF legal jurisdiction is Cayman. GLEIF therefore cannot tag them CN. The China
nationality of these names lives in their SEC 20-F (PRC-operations / VIE disclosure),
not in GLEIF. This hand-map is genuinely additive to the GLEIF lookup, not redundant.

## Match keys
One row per distinct ISIN that the named issuer carries in the panel haven subset
(match_key_type = isin). Multiple ISINs per issuer reflect ordinary shares (KYG... HK
lines), ADRs (US0... / US...144A lines), and USD bonds — all attributable to the same
SEC registrant. 70 rows across 9 issuers. Using ISIN (not cusip6) as the key avoids the
many `000000` placeholder cusip6 values seen in the panel.

## Deliberately OMITTED as unsourceable in this environment (NOT assumed CN)
Several large haven issuers in the panel top-list are Chinese-operating but are
**not SEC registrants**, so no SEC 20-F exists to source the claim, and their primary
HK-Exchange listing documents could not be fetched as primary filings in this
environment. Per the do-not-guess rule they are OMITTED rather than tagged:
- Tencent Holdings Ltd (KYG875721634), Meituan (KYG596691041), Xiaomi Corp (KYG9830T1067),
  Li Ning Co Ltd, ANTA Sports Products Ltd, Shenzhou International, WuXi Biologics (Cayman),
  China Mengniu Dairy, China Resources Land, WH Group, Sea Ltd (NYSE-listed but Singapore
  ultimate parent — NOT China; correctly omitted).
These are large untagged haven issuers a future pass could add if a primary public
filing (HKEX listing prospectus / annual report) is fetched and read.

## Deliberately OMITTED because NOT China by ultimate parent (honest in both directions)
Large haven-resident issuers in the top list that are NOT Chinese-parent and must NOT be
tagged CN:
- AIA Group Ltd (HK-domiciled pan-Asian insurer; not a Chinese-parent),
  Hong Kong Exchanges & Clearing, Galaxy Entertainment Group, Sands China (US Las Vegas
  Sands parent), Sun Hung Kai Properties, CK Hutchison / CK Asset Holdings, CLP Holdings,
  Power Assets, Link REIT, BOC Hong Kong Holdings, Techtronic Industries, Fabrinet
  (Thailand operations, NYSE), Avolon Holdings (Irish aircraft lessor), and the CLO/ABS
  shells (Madison Park Funding, Sound Point CLO, CIFC Funding, Dryden Senior Loan, Voya
  CLO) — Cayman securitization vehicles, not Chinese operating companies.
Note: H-share banks/insurers such as China Construction Bank, ICBC, Bank of China, Ping An
appear with N-PORT residence HKG but are CN by GLEIF legal jurisdiction (captured in the
Deliverable A SELF-CN set), so they are handled by the GLEIF lookup, not duplicated here.

## Integrity
Every row's China-parent claim is sourced to a real, fetched SEC EDGAR record (CIK +
20-F accession verified live 2026-06-29). No entry is from memory. No fabricated coverage
figure appears here. The omission lists make the map honest in both directions: nothing
sourceable-and-large is dropped to keep it thin, and nothing unsourceable is added to pad it.
