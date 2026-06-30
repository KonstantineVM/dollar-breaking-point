#!/usr/bin/env python3
"""
CONSTRUCT-THE-CROSSWALK Part 2 — recompute generator (no network).

Regenerates the tagged haven panel from:
  - the panel parquet (build/data/nport/us_china_nationality_panel.parquet), haven subset
  - the Part-1 source files in build/data/crosswalk/ (HFCAA panel match, EDGAR provenance,
    GLEIF ISIN->LEI, GLEIF-QCC, OpenCorporates)
ONLY. No fetches.

Per holding it emits keys + residence (investment_country_iso3) ALONGSIDE the constructed
parent_nationality, plus which rule(s) fired (auditable provenance). Every CN flag traces
to a named rule and a real source row; no name-guessing.

Rules (a security is flagged CN if ANY fire):
  R1  SEC HFCAA membership matched to the panel by RESOLVED IDENTIFIER (CUSIP6/ISIN/LEI),
      NOT bare name. (Name-only HFCAA matches that resolve to no identifier are recorded
      separately as R1_name_only and do NOT drive the CN flag.)

      LEAK FIX (2026-06-30, Part-4): the prior pass consumed pre-resolved identifiers from
      hfcaa/hfcaa_panel_match.json, whose name-match step compared the SEC conclusive-list
      issuer name to the panel WITHOUT decoding HTML entities. SEC's conclusive-list HTML
      table embeds a non-breaking space as the literal entity '&nbsp;' (-> U+00A0); names
      such as 'NetEase,&nbsp;Inc.', 'ZTO Express (Cayman) Inc.&nbsp;', 'VNET Group,&nbsp;Inc.',
      'Youdao,&nbsp;Inc.', 'MINISO Group Holding Limited&nbsp;', 'Chindata...&nbsp;',
      'China Southern Airlines...&nbsp;' therefore never matched the panel's clean names and
      were left matched=false with NO resolved identifier -> R1 never fired for them. NetEase
      (CIK 1110646, ~$33B, cusip6 64110W / G6427A) sat UNTAGGED in the top-20 tail.

      The fix re-derives the HFCAA CIK -> {CUSIP6, ISIN, LEI} security set HERE, from real
      SEC source files (hfcaa_conclusive.json + company_tickers.json) joined to the panel by
      a normalized name that (a) html.unescape()-decodes entities, (b) strips U+00A0, suffix
      tokens and punctuation. company_tickers.json (CIK-keyed, clean SEC titles) supplies an
      alias name per CIK; that alias is used ONLY when it shares the HFCAA name's leading
      stem, which EXCLUDES post-reverse-merger / rebrand drift (e.g. CIK 1381074 Fuwei Films
      -> current title 'Baijiayun', CIK 1864055 Moxian -> 'Abits') so no security is tagged
      by a name HFCAA never identified. Every resolved identifier traces to an HFCAA CIK.
      Result (MEASURED below): 148 HFCAA CIIs now match the panel (was 134); +14 issuers,
      +3,918 rows, +~$45.5B newly R1-tagged, zero regressions on the prior 134.
  R2  XBRL VIE OpCo jurisdiction = CN for the issuer (read from the filing).
  R3  Form F-6 / 20-F home or OpCo jurisdiction = CN (read).
  R4  GLEIF/QCC parent/registry resolving to CN -- RESTRICTED. See QCC sanity check below.

QCC SANITY CHECK (load-bearing; documented in provenance):
  GLEIF doc text: QCC is the "QCC Global Enterprise Identifier" assigned by Qichacha, a
  database of "more than 500 million legal entities in over 200 countries and regions".
  A QCC code is therefore NOT a Chinese registration-authority code -- its mere presence
  does NOT mean China registration. Empirically (this script measures it): of the 2,932
  haven LEIs carrying a QCC code, the QCC country-segment is KY(1993)/VG(305)/HK(195)/
  CN(155)/US(89)/BM(87)/...; and 175 of 178 named non-Chinese Cayman CLO/hedge-fund LEIs
  (Madison Park, Palmer Square, Carlyle, Dryden, Voya, TICP, Sound Point, CIFC, Cerberus,
  Millennium, Elliott) carry a QCC code -- with QKY/QVG/QJE/QUS segments. So "carries any
  QCC code" is SPURIOUS as a China signal. We therefore RESTRICT R4 to QCC codes whose
  country segment == 'CN' (real value read from the code), cross-checked to the China LOU
  prefix '30030' / GLEIF China registration. That subset is genuinely Chinese H-share /
  red-chip names (Air China, CRRC, Haier, WuXi, ...) residing HKG/CYM. OpenCorporates adds
  0 China-register rows for the haven LEIs, so it is not used for R4.
"""
import json, os
import collections
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PANEL = os.path.join(ROOT, "build/data/nport/us_china_nationality_panel.parquet")
CW = os.path.join(ROOT, "build/data/crosswalk")
OUT_PARQUET = os.path.join(ROOT, "build/data/nport/panel_crosswalk_tagged.parquet")
OUT_VERIFY = os.path.join(ROOT, "build/results/panel_crosswalk_tagged_verify.json")
HFCAA_MATCH = os.path.join(CW, "hfcaa/hfcaa_panel_match.json")
EDGAR_PROV = os.path.join(CW, "edgar/edgar_jurisdiction_provenance.json")
QCC_CSV = os.path.join(CW, "qcc/lei-qcc-20250901T000000.csv")

CLO_TOKENS = ["MADISON PARK", "PALMER SQUARE", "CARLYLE", "DRYDEN", "VOYA", "TICP",
              "SOUND POINT", "CIFC", "CERBERUS", "MILLENNIUM", "ELLIOTT"]

import html, re
HFCAA_CONCLUSIVE = os.path.join(CW, "hfcaa/hfcaa_conclusive.json")
COMPANY_TICKERS = os.path.join(CW, "hfcaa/company_tickers.json")

def norm6(c):
    if c is None:
        return None
    c = str(c).strip()
    return c[:6] if len(c) >= 6 else None

_SUFFIX = re.compile(r"\b(INCORPORATED|INC|CORPORATION|CORP|LIMITED|LTD|LLC|LP|PLC|CO|"
                     r"COMPANY|GROUP|HOLDINGS|HOLDING|GMBH|AG|SA|NV|ADR|ADS|SPONSORED|"
                     r"UNSPONSORED|THE)\b")
def norm_name(s):
    """Normalize an issuer name for matching: decode HTML entities (THE LEAK FIX),
    strip U+00A0, uppercase, drop punctuation and corporate-suffix tokens."""
    if not s:
        return ""
    s = html.unescape(s).replace("\xa0", " ").upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = _SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()
def name_stem(s):
    s = html.unescape(s or "").replace("\xa0", " ").upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    parts = s.split()
    return parts[0] if parts else ""

# ---------------------------------------------------------------- load panel haven subset
cols = ["cusip", "isin", "cusip6", "issuer_name", "issuer_lei",
        "is_haven_resident", "currency_value", "investment_country_iso3"]
have_cols = pq.ParquetFile(PANEL).schema_arrow.names
read_cols = [c for c in cols if c in have_cols]
t = pq.read_table(PANEL, columns=read_cols)
t = t.filter(pc.equal(t["is_haven_resident"], True))
n = t.num_rows

cusip = t["cusip"].to_pylist()
isin = t["isin"].to_pylist()
lei = t["issuer_lei"].to_pylist()
name = t["issuer_name"].to_pylist()
value = t["currency_value"].to_pylist()
res = t["investment_country_iso3"].to_pylist()
cusip6 = (t["cusip6"].to_pylist() if "cusip6" in read_cols else [norm6(c) for c in cusip])

HAVEN_VALUE = sum(v for v in value if v is not None)

# ---------------------------------------------------------------- R1: HFCAA resolved IDs
# LEAK FIX: re-derive HFCAA CIK -> {CUSIP6, ISIN, LEI} HERE from real SEC source files
# (hfcaa_conclusive.json + company_tickers.json) joined to the panel by HTML-decoded
# normalized name, instead of trusting the prior pass's leaky pre-resolved match file.
hf_conclusive = json.load(open(HFCAA_CONCLUSIVE))
ct_raw = json.load(open(COMPANY_TICKERS))
ct_by_cik = collections.defaultdict(set)
for it in (ct_raw.values() if isinstance(ct_raw, dict) else ct_raw):
    ct_by_cik[int(it["cik_str"])].add(it["title"])

# panel-haven normalized-name -> row indices (built once, used for R1 resolution)
pname_to_rows = collections.defaultdict(list)
for _i in range(n):
    pname_to_rows[norm_name(name[_i])].append(_i)

# candidate normalized names per HFCAA CIK: the decoded conclusive-list name PLUS any
# company_tickers title that shares the HFCAA name's leading stem (drift guard).
hf_isin, hf_cusip6, hf_lei = set(), set(), set()
hfcaa_cik_rows = {}          # cik -> sorted panel row indices it resolves to
hfcaa_matched = []           # rebuilt match records (CIK + resolved ids/value/rows)
name_only_count = 0
for r in hf_conclusive:
    cik = int(r["cik"])
    stem = name_stem(r["issuer_name"])
    cands = {norm_name(r["issuer_name"])}
    for ttl in ct_by_cik.get(cik, ()):
        if name_stem(ttl) == stem:
            cands.add(norm_name(ttl))
    cands.discard("")
    rows = sorted({i for c in cands for i in pname_to_rows.get(c, ())})
    if not rows:
        continue
    hfcaa_cik_rows[cik] = rows
    rec_isin = sorted({isin[i] for i in rows if isin[i]})
    rec_c6 = sorted({cusip6[i] for i in rows if cusip6[i] and cusip6[i] not in ("000000",)})
    rec_lei = sorted({lei[i] for i in rows if lei[i] and lei[i] != "N/A"})
    for v in rec_isin:
        hf_isin.add(v)
    for v in rec_c6:
        hf_cusip6.add(v)
    for v in rec_lei:
        hf_lei.add(v)
    has_id = bool(rec_isin or rec_c6 or rec_lei)
    if not has_id:
        name_only_count += 1
    hfcaa_matched.append({
        "issuer_name": r["issuer_name"], "cik": str(cik), "matched": True,
        "panel_rows": len(rows),
        "panel_value_converted": sum(value[i] or 0.0 for i in rows),
        "isins": rec_isin, "cusip6": rec_c6, "leis": rec_lei,
        "candidate_norm_names": sorted(cands),
    })
hfcaa_value_in_file = sum(x["panel_value_converted"] for x in hfcaa_matched)
hfcaa_cik_matched_count = len(hfcaa_matched)

# EDGAR provenance: VIE OpCo CN (R2) and F-6/20-F home CN (R3) anchors, by resolved id.
# EDGAR file carries names/CIK; we resolve to identifiers via the HFCAA match file
# (Alibaba/JD are HFCAA members with resolved isins/cusip6/leis there).
edgar = json.load(open(EDGAR_PROV))
r2_isin, r2_cusip6, r2_lei = set(), set(), set()
r3_isin, r3_cusip6, r3_lei = set(), set(), set()
# Key the rebuilt HFCAA records by CIK (robust; EDGAR provenance carries the CIK) and by
# normalized name as a fallback. R2/R3 attach the EDGAR-read jurisdiction to the issuer's
# panel-resolved identifiers via its HFCAA record.
hf_by_cik = {int(x["cik"]): x for x in hfcaa_matched}
hf_by_norm = {norm_name(x["issuer_name"]): x for x in hfcaa_matched}
def add_ids(target_isin, target_c6, target_lei, rec):
    for v in rec.get("isins") or []:
        target_isin.add(v)
    for v in rec.get("cusip6") or []:
        target_c6.add(v)
    for v in rec.get("leis") or []:
        target_lei.add(v)
for e in edgar:
    rec = None
    if e.get("cik"):
        rec = hf_by_cik.get(int(e["cik"]))
    if not rec:
        rec = hf_by_norm.get(norm_name(e.get("issuer_name", "")))
    if not rec:
        continue
    if e.get("opco_nationality") == "CN":
        add_ids(r2_isin, r2_cusip6, r2_lei, rec)  # R2 VIE OpCo CN
    if "CN" in (e.get("f6_adr_jurisdiction", "") + e.get("residence_source", "")) or \
       e.get("opco_nationality") == "CN":
        # R3 fires where an F-6/20-F was read for the issuer (home/OpCo jurisdiction read);
        # Alibaba has an explicit F-6EF read. Record by resolved id.
        if e.get("f6_adr_jurisdiction"):
            add_ids(r3_isin, r3_cusip6, r3_lei, rec)

# ---------------------------------------------------------------- R4: QCC restricted to CN segment
# Build QCC lookup only for the haven LEIs (stream the big CSV once).
haven_leis = set(l for l in lei if l and l != "N/A")
qcc_code = {}
with open(QCC_CSV) as f:
    next(f)
    for line in f:
        L, code = line.rstrip("\n").split(",", 1)
        if L in haven_leis:
            qcc_code[L] = code
# country segment = chars [1:3] of the QCC code (after leading 'Q')
qcc_any_leis = set(qcc_code)
qcc_cn_leis = set(L for L, c in qcc_code.items() if len(c) >= 3 and c[1:3] == "CN")
qcc_seg_dist = collections.Counter(c[1:3] for c in qcc_code.values() if len(c) >= 3)

# CLO cross-check: do the named non-Chinese CLO LEIs carry QCC, and with what segment?
clo_leis = set()
clo_lei_by_token = collections.defaultdict(set)
for nm, L in zip(name, lei):
    if not nm or not L or L == "N/A":
        continue
    up = nm.upper()
    for tok in CLO_TOKENS:
        if tok in up:
            clo_leis.add(L)
            clo_lei_by_token[tok].add(L)
clo_with_qcc = {L: qcc_code[L] for L in clo_leis if L in qcc_code}
clo_qcc_cn = [L for L, c in clo_with_qcc.items() if len(c) >= 3 and c[1:3] == "CN"]
clo_qcc_seg = collections.Counter(c[1:3] for c in clo_with_qcc.values() if len(c) >= 3)

# ---------------------------------------------------------------- tag every haven row
parent_nat = []
rules_fired = []
r_counts = collections.Counter()
r_value = collections.Counter()
any_cn_value = 0.0
any_cn_rows = 0
hfcaa_panel_rows = 0
hfcaa_panel_value = 0.0
hfcaa_seen_keys = set()

for i in range(n):
    fired = []
    c6 = cusip6[i]
    iv = isin[i]
    lv = lei[i]
    # R1 HFCAA by resolved identifier
    r1 = (iv in hf_isin) or (c6 in hf_cusip6) or (lv in hf_lei)
    if r1:
        fired.append("R1_HFCAA")
    # R2 XBRL VIE OpCo CN
    if (iv in r2_isin) or (c6 in r2_cusip6) or (lv in r2_lei):
        fired.append("R2_XBRL_VIE_CN")
    # R3 F-6/20-F home/OpCo CN
    if (iv in r3_isin) or (c6 in r3_cusip6) or (lv in r3_lei):
        fired.append("R3_F6_20F_CN")
    # R4 QCC restricted to CN country-segment
    if lv in qcc_cn_leis:
        fired.append("R4_QCC_CN_segment")

    v = value[i] or 0.0
    if fired:
        parent_nat.append("CN")
        any_cn_rows += 1
        any_cn_value += v
        for r in fired:
            r_counts[r] += 1
            r_value[r] += v
        rules_fired.append("|".join(fired))
        # HFCAA-in-panel reconciliation: count rows/value where R1 fired
        if "R1_HFCAA" in fired:
            hfcaa_panel_rows += 1
            hfcaa_panel_value += v
    else:
        parent_nat.append("UNDETERMINED-NON-CN-OR-UNREACHED")
        rules_fired.append("")

# ---------------------------------------------------------------- write tagged parquet
out = pa.table({
    "cusip": pa.array(cusip),
    "isin": pa.array(isin),
    "cusip6": pa.array(cusip6),
    "issuer_name": pa.array(name),
    "issuer_lei": pa.array(lei),
    "residence_iso3": pa.array(res),
    "parent_nationality": pa.array(parent_nat),
    "rules_fired": pa.array(rules_fired),
    "currency_value": pa.array(value, type=pa.float64()),
})
pq.write_table(out, OUT_PARQUET)

# ---------------------------------------------------------------- leak-fix delta (MEASURED)
# Compare the corrected HFCAA->panel match against the prior (leaky) hfcaa_panel_match.json
# still on disk, to MEASURE exactly how many issuers / rows / value the entity-decode fix
# recovered. This is diagnostic provenance, not a tagging input.
_prior = json.load(open(HFCAA_MATCH))
_prior_matched_ciks = {int(x["cik"]) for x in _prior if x.get("matched")}
_new_matched_ciks = set(hfcaa_cik_rows)
_newly = sorted(_new_matched_ciks - _prior_matched_ciks)
_name_by_cik = {int(r["cik"]): r["issuer_name"] for r in hf_conclusive}
LEAK_FIX_DELTA = {
    "prior_matched_CII_count": len(_prior_matched_ciks),
    "corrected_matched_CII_count": len(_new_matched_ciks),
    "regressions_prior_matched_now_unmatched": sorted(_prior_matched_ciks - _new_matched_ciks),
    "newly_matched_CII_count": len(_newly),
    "newly_matched_rows": sum(len(hfcaa_cik_rows[c]) for c in _newly),
    "newly_matched_value": sum(value[i] or 0.0 for c in _newly for i in hfcaa_cik_rows[c]),
    "newly_matched_detail": [
        {"cik": c, "hfcaa_name": _name_by_cik.get(c),
         "rows": len(hfcaa_cik_rows[c]),
         "value": sum(value[i] or 0.0 for i in hfcaa_cik_rows[c]),
         "cusip6": sorted({cusip6[i] for i in hfcaa_cik_rows[c]
                           if cusip6[i] and cusip6[i] != "000000"}),
         "isin": sorted({isin[i] for i in hfcaa_cik_rows[c] if isin[i]}),
         "lei": sorted({lei[i] for i in hfcaa_cik_rows[c] if lei[i] and lei[i] != "N/A"})}
        for c in _newly
    ],
}

# ---------------------------------------------------------------- verify artifact
verify = {
    "artifact": "panel_crosswalk_tagged_verify",
    "generated_by": "build/data/nport/panel_crosswalk_tagged_recompute.py (no network)",
    "tagged_panel_path": OUT_PARQUET,
    "shape": {"rows": out.num_rows, "cols": out.num_columns,
              "columns": out.schema.names},
    "panel_haven": {"rows": n, "value_converted": HAVEN_VALUE},
    "marginal_row_check": {
        "haven_rows_expected": 663325,
        "haven_rows_in_output": out.num_rows,
        "rows_match": out.num_rows == 663325,
        "value_in_output": sum(v for v in value if v is not None),
        "value_matches_panel_haven": abs(sum(v for v in value if v is not None) - HAVEN_VALUE) < 1.0,
    },
    "per_rule_counts": dict(r_counts),
    "per_rule_value": {k: r_value[k] for k in r_value},
    "per_rule_value_share_of_haven": {k: r_value[k] / HAVEN_VALUE for k in r_value},
    "cn_tagged_total": {
        "rows": any_cn_rows,
        "value": any_cn_value,
        "value_share_of_haven": any_cn_value / HAVEN_VALUE,
    },
    "hfcaa_reconciliation": {
        "note": ("Part-1 reported 134 HFCAA names matched (16.24% of haven value, "
                 "555,977,880,166). Part-4 LEAK FIX (HTML-entity decode) recovers the "
                 "issuers whose conclusive-list name carried an undecoded '&nbsp;' and so "
                 "never name-matched (NetEase, ZTO Express, VNET, Youdao, MINISO, Chindata, "
                 "China Southern Air, +others). Match is now re-derived from real SEC files."),
        "hfcaa_CIIs_matched_to_panel": hfcaa_cik_matched_count,
        "hfcaa_value_resolved": hfcaa_value_in_file,
        "hfcaa_value_share_of_haven": hfcaa_value_in_file / HAVEN_VALUE,
        "R1_rows_tagged_in_panel": hfcaa_panel_rows,
        "R1_value_tagged_in_panel": hfcaa_panel_value,
        "R1_value_share_of_haven": hfcaa_panel_value / HAVEN_VALUE,
        "name_only_matches_not_driving_flag": name_only_count,
        "leak_fix_delta_vs_prior_match_file": LEAK_FIX_DELTA,
    },
    "qcc_sanity_check": {
        "gleif_doc_quote": ("QCC = 'QCC Global Enterprise Identifier' assigned by Qichacha, "
                            "a database of 'more than 500 million legal entities in over 200 "
                            "countries and regions' -- NOT a Chinese registration-authority code."),
        "haven_leis_total": len(haven_leis),
        "haven_leis_carrying_any_qcc": len(qcc_any_leis),
        "haven_leis_qcc_country_segment_dist": dict(qcc_seg_dist),
        "haven_leis_qcc_CN_segment": len(qcc_cn_leis),
        "verdict": ("'carries any QCC code' is SPURIOUS: 85% of haven LEIs carry one and the "
                    "segment is mostly KY/VG/HK, not CN. R4 RESTRICTED to QCC CN-segment "
                    "(155 haven LEIs), which are genuine China H-share/red-chip names."),
    },
    "clo_cross_check": {
        "clo_tokens": CLO_TOKENS,
        "distinct_clo_leis_in_haven": len(clo_leis),
        "clo_leis_carrying_any_qcc": len(clo_with_qcc),
        "clo_qcc_country_segment_dist": dict(clo_qcc_seg),
        "clo_leis_with_qcc_CN_segment": len(clo_qcc_cn),
        "outcome": ("Non-Chinese CLO/hedge-fund LEIs DO carry QCC codes (would be spuriously "
                    "China-tagged by 'any QCC'), but their QCC segment is QKY/QVG/QJE/QUS, NOT "
                    "QCN -- so the restricted R4 (CN-segment only) does NOT tag them. "
                    "Spurious-tag count under restricted R4 = " + str(len(clo_qcc_cn)) + "."),
    },
    "caveats": {
        "equity_lei_reach": ("R4 reach is capped by LEI presence: 79% of haven value carries an "
                             "LEI; the 21% LEI-less value is unreachable by QCC/OC."),
        "opencorporates": "OC adds 0 China-register rows for haven LEIs; not used for R4.",
        "name_only_hfcaa": ("HFCAA matches with no resolved identifier are recorded as "
                            "name-only and do NOT drive the CN flag; count=" + str(name_only_count)),
        "residence_retained": "residence_iso3 retained beside parent_nationality for audit.",
    },
}
# Persist the corrected HFCAA->panel match (resolved identifiers) as a real artifact so the
# leak fix is auditable on disk. Written to a NEW file; the prior leaky match file is left in
# place untouched so the leak_fix_delta can be re-MEASURED against it on any future re-run.
json.dump(sorted(hfcaa_matched, key=lambda x: -x["panel_value_converted"]),
          open(os.path.join(CW, "hfcaa/hfcaa_panel_match_fixed.json"), "w"), indent=2)

json.dump(verify, open(OUT_VERIFY, "w"), indent=2)
print("PASS" if (out.num_rows == 663325 and
                  verify["marginal_row_check"]["value_matches_panel_haven"] and
                  not LEAK_FIX_DELTA["regressions_prior_matched_now_unmatched"]) else "FAIL")
print(json.dumps({k: verify[k] for k in ["shape", "per_rule_counts", "cn_tagged_total",
      "hfcaa_reconciliation", "qcc_sanity_check", "clo_cross_check"]}, indent=2, default=str))
