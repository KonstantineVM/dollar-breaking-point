# build/data/gleif — GLEIF Level-2 "who owns whom" grounding (COVERAGE-MEASUREMENT Part 1, Deliverable A)

Purpose: resolve the panel's haven-resident issuer LEIs to an ultimate-parent legal
jurisdiction (ISO country), so a later pass can decide whether a free per-security
nationality re-tag is worth attempting. This directory holds the GLEIF inputs and the
derived lookup. NO re-tagging and NO coverage computation are done here.

## Path used
- **Relationships (Level-2 RR):** REAL bulk golden-copy file, downloaded and parsed.
  The full RR golden copy is small (~23 MB zip / ~238 MB CSV / 477,383 records), so the
  bulk path was tractable and used directly.
- **Parent-LEI -> country (Level-1):** resolved via the FREE GLEIF API
  (`api.gleif.org/api/v1/lei-records`), NOT the bulk L1 golden copy. The full L1 golden
  copy is ~468 MB zip (3,356,603 records) — large; resolving only the distinct LEIs we
  actually need (240 distinct parent LEIs + 3,434 haven issuer LEIs = 3,599 distinct,
  fetched in 200-LEI batches via `filter[lei]=`) is far cheaper and is the documented
  reason for the API path. The L1 country field name was confirmed from a real API
  record (see contract), not assumed.

## Files
- `20260629-1600-gleif-goldencopy-rr-golden-copy.csv.zip` — the actual RR golden copy
  bulk file (publish 2026-06-29 16:00 UTC, RR_2.1). Gitignored (large); URL recorded in
  `.gitignore` and in `build/contracts/gleif_source_contract.json` for reproducibility.
- `lei_parent_country.csv` — committed. One row per distinct haven issuer_lei that GLEIF
  could resolve to a country. Columns:
  `issuer_lei, ultimate_parent_lei, parent_country_iso, relationship_type, source`.
  - `relationship_type`: ULTIMATE (IS_ULTIMATELY_CONSOLIDATED_BY parent),
    DIRECT (IS_DIRECTLY_CONSOLIDATED_BY parent, used only when no ULTIMATE exists),
    SELF (no RR parent relationship filed in GLEIF -> the issuer's OWN legal country is
    recorded, with ultimate_parent_lei == issuer_lei). The SELF rows carry RESIDENCE-like
    information for entities with no parent relationship, EXCEPT where GLEIF's legal
    jurisdiction itself differs from N-PORT residence (e.g. HK-listed H-shares whose
    GLEIF legal country is CN). Nationality from a REAL parent relationship is ONLY the
    ULTIMATE/DIRECT rows; SELF is the issuer's own legal jurisdiction.
  - `parent_country_iso`: ISO **alpha-2** (GLEIF `entity.legalAddress.country`).
  - `source`: "GLEIF-RR+API" for every row (RR bulk file for relationships, GLEIF API
    for country).

## Reproduce
1. GET `https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest` -> `data.rr.full_file.csv.url`
2. Download that zip, unzip, read the CSV.
3. Extract distinct non-null 20-char `issuer_lei` from the panel haven subset.
4. Map child->parent on RR rows where `Relationship.RelationshipType` is
   `IS_ULTIMATELY_CONSOLIDATED_BY` (preferred) or `IS_DIRECTLY_CONSOLIDATED_BY`.
5. For each distinct needed LEI, GET `https://api.gleif.org/api/v1/lei-records?filter[lei]=<up to 200 LEIs>`
   -> `data[].attributes.entity.legalAddress.country`.

Checked against the GLEIF publisher on 2026-06-29.
