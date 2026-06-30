# Construct-the-Crosswalk Part 2 — Tagged-Panel Provenance

SOURCE: Composed entirely from Part-1 on-disk artifacts (no network):
`build/contracts/crosswalk_sources.json`, `build/data/crosswalk/hfcaa/hfcaa_conclusive.json`,
`build/data/crosswalk/hfcaa/company_tickers.json`,
`build/data/crosswalk/edgar/edgar_jurisdiction_provenance.json`,
`build/data/crosswalk/qcc/lei-qcc-20250901T000000.csv`, and the panel
`build/data/nport/us_china_nationality_panel.parquet` (haven subset, `is_haven_resident==True`,
663,325 rows, value 3,422,538,903,582.47 converted units).

Generator (canonical, re-runnable offline): `build/data/nport/panel_crosswalk_tagged_recompute.py`.
Outputs: `build/data/nport/panel_crosswalk_tagged.parquet`,
`build/results/panel_crosswalk_tagged_verify.json`,
`build/data/crosswalk/hfcaa/hfcaa_panel_match_fixed.json` (re-derived resolved-identifier set).
Recompute = **PASS**.

## Part-4 LEAK FIX (HTML-entity decode in the HFCAA name join)

**Diagnosed defect.** The prior R1 join consumed pre-resolved identifiers from
`hfcaa_panel_match.json`, whose name-match step compared the SEC HFCAA conclusive-list issuer
name to the panel **without decoding HTML entities**. SEC's conclusive-list HTML table embeds a
non-breaking space as the literal entity `&nbsp;` (U+00A0). Names such as `NetEase,&nbsp;Inc.`,
`ZTO Express (Cayman) Inc.&nbsp;`, `VNET Group,&nbsp;Inc.`, `Youdao,&nbsp;Inc.`,
`MINISO Group Holding Limited&nbsp;`, `Chindata Group Holdings Limited&nbsp;`,
`China Southern Airlines Company Limited&nbsp;` therefore never matched the panel's clean names,
were left `matched:false` with **no resolved identifier**, and R1 never fired for them. NetEase
(CIK 1110646, ~$33B, cusip6 `64110W`/`G6427A`, ISIN `US64110W1027`/`KYG6427A1022`) sat untagged
in the top-20 tail. 8 of the 40 unmatched conclusive-list names carried the undecoded entity.

**Fix (grounded in real SEC data, no name-guess).** R1's HFCAA CIK -> {CUSIP6, ISIN, LEI}
security set is now **re-derived inside the recompute** from real SEC files — `hfcaa_conclusive.json`
(174 CIIs, CIK + name) and `company_tickers.json` (CIK-keyed clean SEC titles) — joined to the
panel by a normalized name that (a) `html.unescape()`-decodes entities, (b) strips U+00A0, suffix
tokens and punctuation. A `company_tickers` title is used as a CIK alias **only when it shares the
HFCAA name's leading stem**, which excludes post-reverse-merger / rebrand drift (CIK 1381074 Fuwei
Films -> current title "Baijiayun"; CIK 1864055 Moxian -> "Abits") so no security is tagged by a
name HFCAA never identified. Every resolved identifier still traces to an HFCAA CIK.

**Measured effect.** HFCAA CIIs matched to the panel: **134 -> 148** (+14 issuers), **+3,918 rows,
+$45.47B** newly R1-eligible, **zero regressions** on the prior 134. Largest recoveries: NetEase
$32.8B, ZTO Express $11.9B, VNET $0.235B, China Southern Air $0.235B, MINISO $0.183B, Chindata
$0.096B, Youdao $0.013B. R2/R3 share no defect (anchored on Alibaba/JD, clean names, now matched by
CIK); R4 is identifier-keyed (QCC LEI) and unaffected.

Tagged panel schema (per holding): `cusip, isin, cusip6, issuer_name, issuer_lei,
residence_iso3, parent_nationality, rules_fired, currency_value`. Residence
(`residence_iso3`) is retained ALONGSIDE the constructed `parent_nationality` so every
reattribution is auditable.

## Rule definitions (a security is CN if ANY fire; the firing rule(s) are recorded per row)

- **R1 SEC HFCAA membership** — matched to the panel by RESOLVED IDENTIFIER (CUSIP6/ISIN/LEI),
  not bare name. The CIK -> identifier set is re-derived from `hfcaa_conclusive.json` +
  `company_tickers.json` joined to the panel by HTML-decoded normalized name (**148 matched CIIs**
  after the Part-4 leak fix, each with its panel ISINs/CUSIP6/LEIs). Name-only HFCAA matches (no
  resolved identifier) = **0** here; none drive the flag.
- **R2 XBRL VIE OpCo jurisdiction = CN** — read from the EDGAR Inline-XBRL filings
  (`edgar_jurisdiction_provenance.json`): Alibaba `baba:ConsolidatedVIEsAndSubsidiariesMember`,
  "The VIEs are incorporated in the PRC ..."; JD.com "consolidated VIEs incorporated in the PRC".
  Applied by resolved identifier (the EDGAR anchor issuers are HFCAA members with resolved IDs).
- **R3 Form F-6 / 20-F home or OpCo jurisdiction = CN** — read, not name-guessed. Alibaba F-6EF
  acc 0001193805-22-000150 cover jurisdiction + 20-F OpCo CN.
- **R4 GLEIF/QCC parent/registry resolving to CN — RESTRICTED** (see QCC check below).

## QCC sanity check (load-bearing — performed BEFORE trusting R4)

**What a QCC code denotes (from GLEIF documentation, read on disk** —
`build/data/crosswalk/qcc/qcc_page.html`): the QCC code is the *"QCC Global Enterprise
Identifier"* assigned by Qichacha, whose database holds *"more than 500 million legal entities
in over 200 countries and regions."* It is therefore **NOT a Chinese registration-authority
code**. Its mere presence does NOT mean the entity is China-registered. The QCC code's country
segment (chars 2-3, e.g. `Q**KY**...`) encodes the **registration jurisdiction of the LEI-bearing
entity** — i.e. the residency entity, not the parent nationality.

**Measured over the 3,434 panel haven LEIs:** 2,932 (85%) carry a QCC code. Their country-segment
distribution is KY 1,993 / VG 305 / HK 195 / **CN 155** / US 89 / BM 87 / GB 25 / JE 22 / ... .
The Cayman segment alone is 13x the China segment. So **"carries any QCC code" is SPURIOUS** as a
China-nationality signal — it would paint ~1,993 Cayman + 305 BVI + 195 HK entities as Chinese.

**CLO cross-check (shown):** of the 178 distinct haven LEIs whose issuer name contains a named
non-Chinese Cayman CLO / hedge-fund token (Madison Park, Palmer Square, Carlyle, Dryden, Voya,
TICP, Sound Point, CIFC, Cerberus, Millennium, Elliott), **175 carry a QCC code** — confirming
"any QCC" would spuriously China-tag them. Their QCC country segments are KY 166 / IE 4 / US 3 /
VG 1 / JE 1 — **zero `QCN`**. Alibaba's own QCC-carrying secondary LEIs read `QBM` (Bermuda), not
China.

**Decision (documented):** R4 is **restricted to QCC codes whose country segment == `CN`** (a real
value read from the code), which is the only QCC subset that is genuine independent China-registration
evidence. That subset is 155 haven LEIs, all on the China LOU prefix `30030...` and all genuine
Chinese H-share / red-chip names (Air China, China Eastern, CRRC, Haier, WuXi AppTec, Midea, Great
Wall Motor, ...). **Spurious CLO China-tags under the restricted R4 = 0.** OpenCorporates adds 0
China-register rows for the haven LEIs and is not used.

## HFCAA-in-panel reconciliation (verifiable check)

- HFCAA CIIs matched to the panel after the leak fix: **148** (was 134); resolved value
  **623,076,735,599** = **18.21%** of haven.
- R1 fired (by resolved identifier) on **56,041** panel rows, value **661,063,837,960 = 19.32%** of
  haven (was 51,870 rows / 17.97% pre-fix). The leak fix adds the 14 entity-decoded issuers
  (+3,918 newly-matched rows, +$45.47B); the R1 row delta (+4,171) slightly exceeds the
  newly-matched-row count because some recovered identifiers also resolve panel rows previously
  reached only by R2/R3.

## Per-rule tagged counts and value shares (of haven value) — POST leak fix

| Rule | Rows | Value (conv. units) | Value share |
|------|------|---------------------|-------------|
| R1 HFCAA (resolved id) | 56,041 | 661,063,837,960 | 19.32% |
| R2 XBRL VIE OpCo CN | 12,861 | 353,365,687,790 | 10.32% |
| R3 F-6/20-F CN | 9,347 | 299,864,516,177 | 8.76% |
| R4 QCC CN-segment | 8,805 | 111,667,034,179 | 3.26% |
| **Any CN (union)** | **64,057** | **760,982,259,508** | **22.23%** |

(Rules overlap: R1/R2/R3 co-fire on the VIE/ADR names; the union is the CN flag.)

## Caveats (carried, not smoothed)

- **Equity / LEI reach:** R4's reach is capped by LEI presence — only 79% of haven value carries an
  LEI; the 21% LEI-less value is unreachable by QCC. R2/R3 are anchored on the two read filings
  (Alibaba, JD) applied via their resolved identifiers; broader per-name VIE/F-6 reading is the
  licensed-crosswalk frontier, not claimed here.
- **No name-guessing:** holdings with no resolvable identifier tying to a source row are left
  `UNDETERMINED-NON-CN-OR-UNREACHED`. Example: a small Alibaba-Group-Holding CYM row with null
  ISIN/CUSIP6 and LEI `N/A` cannot be sourced and is left untagged; "Alibaba Pictures / Alibaba
  Health" are distinct Bermuda-incorporated HK-listed subsidiaries, not the HFCAA parent, so they
  are not tagged by R1. This is the honest reach limit, not a deflation.
- **Residence retained:** `residence_iso3` sits beside `parent_nationality` on every row (Alibaba:
  residence CYM/HKG -> nationality CN via R1|R2|R3).

Coverage B (Part 3) is NOT computed here.
