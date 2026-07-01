#!/usr/bin/env python3
"""
FULL-PANEL POWER REBUILD, Part 1 -- tagging step.

REUSES the R1-R4 rule logic from panel_crosswalk_tagged_recompute.py VERBATIM and the
SAME crosswalk source files. The rule IDENTIFIER SETS (R1 HFCAA resolved CUSIP6/ISIN/LEI,
R2 XBRL VIE CN ids, R3 F-6/20-F CN ids, R4 QCC CN-segment LEIs) are derived EXACTLY as in
the recompute, and -- critically -- R1's HFCAA-name -> panel-identifier RESOLUTION is done
against the SAME 8-quarter panel (us_china_nationality_panel.parquet) the recompute used.
The frozen sets are then applied, issuer-keyed, to EVERY quarter of the full haven panel.

This is why the rules are NOT re-derived: the resolved-identifier sets are identical to the
ones that produced panel_crosswalk_tagged.parquet, so overlapping quarters tag identically
(checked) and the new quarters are tagged by the same issuer keys.

Carries fiscal_quarter + cik + series_id through (Part 2's fund x quarter panel needs them).
"""
import json, os, collections, html, re
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc

ROOT = "/home/user/dollar-breaking-point"
CW = os.path.join(ROOT, "build/data/crosswalk")
RESOLVE_PANEL = os.path.join(ROOT, "build/data/nport/us_china_nationality_panel.parquet")
PARTS_DIR = os.path.join(ROOT, "build/data/nport/haven_parts")
PRIOR_TAGGED = os.path.join(ROOT, "build/data/nport/panel_crosswalk_tagged.parquet")
OUT_PARQUET = os.path.join(ROOT, "build/data/nport/panel_crosswalk_tagged_full.parquet")

HFCAA_CONCLUSIVE = os.path.join(CW, "hfcaa/hfcaa_conclusive.json")
COMPANY_TICKERS = os.path.join(CW, "hfcaa/company_tickers.json")
EDGAR_PROV = os.path.join(CW, "edgar/edgar_jurisdiction_provenance.json")
QCC_CSV = os.path.join(CW, "qcc/lei-qcc-20250901T000000.csv")

# ----------------------------------------------------------------- VERBATIM helpers (recompute)
def norm6(c):
    if c is None:
        return None
    c = str(c).strip()
    return c[:6] if len(c) >= 6 else None

_SUFFIX = re.compile(r"\b(INCORPORATED|INC|CORPORATION|CORP|LIMITED|LTD|LLC|LP|PLC|CO|"
                     r"COMPANY|GROUP|HOLDINGS|HOLDING|GMBH|AG|SA|NV|ADR|ADS|SPONSORED|"
                     r"UNSPONSORED|THE)\b")
def norm_name(s):
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


def build_rule_sets():
    """Reproduce the recompute's rule-set construction EXACTLY, resolving R1 against the
    SAME 8-quarter panel the recompute used. Returns the frozen identifier sets."""
    cols = ["cusip", "isin", "issuer_name", "issuer_lei",
            "is_haven_resident", "currency_value", "investment_country_iso3"]
    have = pq.ParquetFile(RESOLVE_PANEL).schema_arrow.names
    rc = [c for c in cols if c in have]
    t = pq.read_table(RESOLVE_PANEL, columns=rc)
    t = t.filter(pc.equal(t["is_haven_resident"], True))
    n = t.num_rows
    cusip = t["cusip"].to_pylist()
    isin = t["isin"].to_pylist()
    lei = t["issuer_lei"].to_pylist()
    name = t["issuer_name"].to_pylist()
    value = t["currency_value"].to_pylist()
    cusip6 = [norm6(c) for c in cusip]

    # R1: HFCAA CIK -> {CUSIP6, ISIN, LEI} re-derived from real SEC files joined to panel
    hf_conclusive = json.load(open(HFCAA_CONCLUSIVE))
    ct_raw = json.load(open(COMPANY_TICKERS))
    ct_by_cik = collections.defaultdict(set)
    for it in (ct_raw.values() if isinstance(ct_raw, dict) else ct_raw):
        ct_by_cik[int(it["cik_str"])].add(it["title"])
    pname_to_rows = collections.defaultdict(list)
    for _i in range(n):
        pname_to_rows[norm_name(name[_i])].append(_i)
    hf_isin, hf_cusip6, hf_lei = set(), set(), set()
    hfcaa_matched = []
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
        rec_isin = sorted({isin[i] for i in rows if isin[i]})
        rec_c6 = sorted({cusip6[i] for i in rows if cusip6[i] and cusip6[i] not in ("000000",)})
        rec_lei = sorted({lei[i] for i in rows if lei[i] and lei[i] != "N/A"})
        hf_isin.update(rec_isin); hf_cusip6.update(rec_c6); hf_lei.update(rec_lei)
        hfcaa_matched.append({"issuer_name": r["issuer_name"], "cik": str(cik),
                              "isins": rec_isin, "cusip6": rec_c6, "leis": rec_lei})

    # R2 / R3: EDGAR-read CN jurisdictions attached via HFCAA resolved ids
    edgar = json.load(open(EDGAR_PROV))
    r2_isin, r2_cusip6, r2_lei = set(), set(), set()
    r3_isin, r3_cusip6, r3_lei = set(), set(), set()
    hf_by_cik = {int(x["cik"]): x for x in hfcaa_matched}
    hf_by_norm = {norm_name(x["issuer_name"]): x for x in hfcaa_matched}
    def add_ids(ti, tc, tl, rec):
        for v in rec.get("isins") or []:
            ti.add(v)
        for v in rec.get("cusip6") or []:
            tc.add(v)
        for v in rec.get("leis") or []:
            tl.add(v)
    for e in edgar:
        rec = None
        if e.get("cik"):
            rec = hf_by_cik.get(int(e["cik"]))
        if not rec:
            rec = hf_by_norm.get(norm_name(e.get("issuer_name", "")))
        if not rec:
            continue
        if e.get("opco_nationality") == "CN":
            add_ids(r2_isin, r2_cusip6, r2_lei, rec)
        if "CN" in (e.get("f6_adr_jurisdiction", "") + e.get("residence_source", "")) or \
           e.get("opco_nationality") == "CN":
            if e.get("f6_adr_jurisdiction"):
                add_ids(r3_isin, r3_cusip6, r3_lei, rec)

    # R4: QCC restricted to CN segment, built over the RESOLVE panel haven LEIs (the recompute
    # streamed the QCC csv filtered to haven LEIs; the QCC csv is the rule source, LEI-keyed --
    # applied to any quarter's LEIs identically).
    haven_leis_resolve = set(l for l in lei if l and l != "N/A")
    qcc_code = {}
    with open(QCC_CSV) as f:
        next(f)
        for line in f:
            L, code = line.rstrip("\n").split(",", 1)
            if L in haven_leis_resolve:
                qcc_code[L] = code
    qcc_cn_leis = set(L for L, c in qcc_code.items() if len(c) >= 3 and c[1:3] == "CN")

    return dict(hf_isin=hf_isin, hf_cusip6=hf_cusip6, hf_lei=hf_lei,
                r2_isin=r2_isin, r2_cusip6=r2_cusip6, r2_lei=r2_lei,
                r3_isin=r3_isin, r3_cusip6=r3_cusip6, r3_lei=r3_lei,
                qcc_cn_leis=qcc_cn_leis,
                hfcaa_matched_count=len(hfcaa_matched))


def tag_rows(isin, cusip6, lei, S):
    """VERBATIM rule firing from the recompute."""
    fired = []
    if (isin in S["hf_isin"]) or (cusip6 in S["hf_cusip6"]) or (lei in S["hf_lei"]):
        fired.append("R1_HFCAA")
    if (isin in S["r2_isin"]) or (cusip6 in S["r2_cusip6"]) or (lei in S["r2_lei"]):
        fired.append("R2_XBRL_VIE_CN")
    if (isin in S["r3_isin"]) or (cusip6 in S["r3_cusip6"]) or (lei in S["r3_lei"]):
        fired.append("R3_F6_20F_CN")
    if lei in S["qcc_cn_leis"]:
        fired.append("R4_QCC_CN_segment")
    return fired


def main():
    S = build_rule_sets()

    # assemble full haven panel from parts (sorted by fiscal quarter)
    def fqkey(p):
        b = os.path.basename(p)[len("haven_"):-len(".parquet")]
        return (int(b[:4]), int(b[5]))
    parts = sorted([os.path.join(PARTS_DIR, f) for f in os.listdir(PARTS_DIR)
                    if f.startswith("haven_") and f.endswith(".parquet")], key=fqkey)

    out_cols = collections.defaultdict(list)
    per_q = []
    for p in parts:
        t = pq.read_table(p)
        fq = t["fiscal_quarter"].to_pylist()[0] if t.num_rows else os.path.basename(p)[6:-8]
        cusip = t["cusip"].to_pylist()
        isin = t["isin"].to_pylist()
        lei = t["issuer_lei"].to_pylist()
        name = t["issuer_name"].to_pylist()
        value = t["currency_value"].to_pylist()
        res = t["investment_country_iso3"].to_pylist()
        cik = t["cik"].to_pylist()
        series = t["series_id"].to_pylist()
        fqs = t["fiscal_quarter"].to_pylist()
        c6 = [norm6(c) for c in cusip]

        cn_rows = 0
        usable = 0
        for i in range(t.num_rows):
            fired = tag_rows(isin[i], c6[i], lei[i], S)
            pn = "CN" if fired else "UNDETERMINED-NON-CN-OR-UNREACHED"
            if fired:
                cn_rows += 1
            iv = isin[i]; cv = cusip[i]
            if (iv and len(str(iv)) == 12) or (cv and len(str(cv)) == 9):
                usable += 1
            out_cols["fiscal_quarter"].append(fqs[i])
            out_cols["cik"].append(cik[i])
            out_cols["series_id"].append(series[i])
            out_cols["cusip"].append(cusip[i])
            out_cols["isin"].append(isin[i])
            out_cols["cusip6"].append(c6[i])
            out_cols["issuer_name"].append(name[i])
            out_cols["issuer_lei"].append(lei[i])
            out_cols["residence_iso3"].append(res[i])
            out_cols["parent_nationality"].append(pn)
            out_cols["rules_fired"].append("|".join(fired))
            out_cols["currency_value"].append(value[i])
        per_q.append({"fiscal_quarter": fq, "haven_rows": t.num_rows,
                      "cn_tagged_rows": cn_rows,
                      "identifier_coverage_pct": round(100.0 * usable / t.num_rows, 4) if t.num_rows else 0.0,
                      "identifier_usable_n": usable})

    out = pa.table({
        "fiscal_quarter": pa.array(out_cols["fiscal_quarter"]),
        "cik": pa.array(out_cols["cik"]),
        "series_id": pa.array(out_cols["series_id"]),
        "cusip": pa.array(out_cols["cusip"]),
        "isin": pa.array(out_cols["isin"]),
        "cusip6": pa.array(out_cols["cusip6"]),
        "issuer_name": pa.array(out_cols["issuer_name"]),
        "issuer_lei": pa.array(out_cols["issuer_lei"]),
        "residence_iso3": pa.array(out_cols["residence_iso3"]),
        "parent_nationality": pa.array(out_cols["parent_nationality"]),
        "rules_fired": pa.array(out_cols["rules_fired"]),
        "currency_value": pa.array(out_cols["currency_value"], type=pa.float64()),
    })
    pq.write_table(out, OUT_PARQUET)

    summary = {"rule_sets": {k: len(v) for k, v in S.items() if isinstance(v, set)},
               "hfcaa_matched_count": S["hfcaa_matched_count"],
               "out_path": OUT_PARQUET, "total_rows": out.num_rows,
               "per_quarter": per_q}
    json.dump(summary, open(os.path.join(PARTS_DIR, "_tag_summary.json"), "w"), indent=2)
    print("TAG_DONE")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
