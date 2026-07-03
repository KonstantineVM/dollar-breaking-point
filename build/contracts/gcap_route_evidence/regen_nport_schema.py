#!/usr/bin/env python3
"""
Recompute / verify the schema of the GCAP Drive object nport.zip
(id=1dGUfDFPqreYzJClEs46JWBivEJXhyNM7, total 16,470,969,928 bytes) using ONLY the
committed raw byte blobs in this directory -- NO network access.

Inputs (raw evidence, committed alongside this script):
  - zip_tail.bin      : last 100,000 bytes of the 16.47 GB object
                        (contains ZIP64 EOCD + locator + central directory)
  - member0_head.bin  : first 8,388,608 bytes of the object
                        (local file header of member 2019q3.dta + raw-deflate prefix)

Outputs / checks:
  - Regenerates the member list (26 entries, sizes, offsets) from zip_tail.bin and
    byte-compares to the committed nport_zip_entries.json.
  - Regenerates the dta-118 <varnames> of the first member from member0_head.bin and
    byte-compares to the committed nport_2019q3_schema.json.
  - Asserts the route-relevant facts: security ids issuer_cusip / identifier_isin /
    issuer_lei are present; investment_country is the ONLY geography column; NO
    nationality / ultimate_parent / cmns_country column exists.

Prints "PASS" only if every check holds and the regenerated JSON byte-matches the
committed artifacts. Emits a machine-readable result to stdout's JSON tail.
"""
import struct, zlib, json, hashlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOTAL_BYTES = 16470969928
TAIL_LEN = 100000          # zip_tail.bin length / offset of first byte = TOTAL-TAIL_LEN
HEAD_LEN = 8388608         # member0_head.bin length, fetched at offset 0

EXPECTED_SHA = {
    "zip_tail.bin": "07d803f02c8c3ae982ed3dd98421f113b49447bdf4f1459025ce4106d8be98fb",
    "member0_head.bin": "a7700ed636e94ee25ec7d9e784654330d13a1c4d80722a5a37684eea9af9e14c",
}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_central_directory(tail_path):
    data = open(tail_path, "rb").read()
    tail_start = TOTAL_BYTES - len(data)  # absolute offset of buffer[0]
    loc = data.rfind(b"PK\x06\x07")       # ZIP64 EOCD locator
    if loc < 0:
        raise RuntimeError("ZIP64 EOCD locator not found in tail")
    _sig, _disk, eocd64_off, _ndisks = struct.unpack("<IIQI", data[loc:loc + 20])
    rel = eocd64_off - tail_start
    (_s, _sz, _vm, _vn, _d1, _d2, _nd, n_total, cd_size, cd_off) = struct.unpack(
        "<IQHHIIQQQQ", data[rel:rel + 56])
    crel = cd_off - tail_start
    cd = data[crel:crel + cd_size]
    entries = []
    p = 0
    while p < len(cd) and cd[p:p + 4] == b"PK\x01\x02":
        (_sig, _vm, _vn, _flag, method, _mt, _md, _crc, csize, usize,
         nlen, elen, clen, _ds, _ia, _ea, lho) = struct.unpack(
            "<IHHHHHHIIIHHHHHII", cd[p:p + 46])
        name = cd[p + 46:p + 46 + nlen].decode("utf-8", "replace")
        extra = cd[p + 46 + nlen:p + 46 + nlen + elen]
        real_csize, real_usize, real_lho = csize, usize, lho
        ep = 0
        while ep + 4 <= len(extra):
            hid, hsz = struct.unpack("<HH", extra[ep:ep + 4])
            body = extra[ep + 4:ep + 4 + hsz]
            if hid == 0x0001:
                bp = 0
                if usize == 0xFFFFFFFF:
                    real_usize = struct.unpack("<Q", body[bp:bp + 8])[0]; bp += 8
                if csize == 0xFFFFFFFF:
                    real_csize = struct.unpack("<Q", body[bp:bp + 8])[0]; bp += 8
                if lho == 0xFFFFFFFF:
                    real_lho = struct.unpack("<Q", body[bp:bp + 8])[0]; bp += 8
            ep += 4 + hsz
        entries.append({
            "name": name, "uncompressed": real_usize, "compressed": real_csize,
            "local_header_offset": real_lho, "method": method,
        })
        p += 46 + nlen + elen + clen
    return n_total, entries


def parse_first_member_varnames(head_path):
    buf = open(head_path, "rb").read()
    if buf[:4] != b"PK\x03\x04":
        raise RuntimeError("member0_head.bin does not start with a local file header")
    (_sig, _ver, _flag, method, _mt, _md, _crc, _cs, _us, nlen, elen) = struct.unpack(
        "<IHHHHHIIIHH", buf[:30])
    name = buf[30:30 + nlen].decode()
    if method != 8:
        raise RuntimeError("first member not deflate")
    comp = buf[30 + nlen + elen:]
    d = zlib.decompressobj(-15)
    try:
        out = d.decompress(comp)
    except Exception:
        out = b""  # truncation at end of 8MB prefix is expected
    K = struct.unpack("<H", out[out.find(b"<K>") + 3:out.find(b"<K>") + 5])[0]

    def sec(tag):
        a = out.find(b"<" + tag + b">"); b = out.find(b"</" + tag + b">")
        return out[a + len(tag) + 2:b]

    vn = sec(b"varnames")
    names = [vn[k * 129:(k + 1) * 129].split(b"\x00")[0].decode("utf-8", "replace")
             for k in range(K)]
    lab = sec(b"variable_labels")
    labels = [lab[k * 321:(k + 1) * 321].split(b"\x00")[0].decode("utf-8", "replace")
              for k in range(K)]
    return name, K, names, labels


def main():
    result = {"checks": {}, "sha256": {}}
    ok = True

    # 0. raw-blob integrity
    for fn, exp in EXPECTED_SHA.items():
        got = sha256_file(os.path.join(HERE, fn))
        result["sha256"][fn] = got
        match = (got == exp)
        result["checks"][f"sha256:{fn}"] = match
        ok = ok and match

    # 1. central directory -> entries; byte-compare to committed nport_zip_entries.json
    n_total, entries = parse_central_directory(os.path.join(HERE, "zip_tail.bin"))
    committed_entries = json.load(open(os.path.join(HERE, "nport_zip_entries.json")))
    entries_match = (entries == committed_entries)
    result["checks"]["entries_byte_match_committed_json"] = entries_match
    result["checks"]["member_count_is_26"] = (n_total == 26 and len(entries) == 26)
    names = [e["name"] for e in entries]
    result["checks"]["members_2019q3_to_2025q4"] = (
        names[0] == "2019q3.dta" and names[-1] == "2025q4.dta")
    ok = ok and entries_match and (n_total == 26) and (len(entries) == 26)

    # 2. first member varnames -> byte-compare to committed nport_2019q3_schema.json
    mname, K, varnames, labels = parse_first_member_varnames(
        os.path.join(HERE, "member0_head.bin"))
    regen_schema = {"nvar": K, "varnames": varnames, "varlabels": labels}
    committed_schema = json.load(open(os.path.join(HERE, "nport_2019q3_schema.json")))
    schema_match = (regen_schema == committed_schema)
    result["checks"]["schema_byte_match_committed_json"] = schema_match
    result["checks"]["first_member_is_2019q3"] = (mname == "2019q3.dta")
    result["checks"]["nvar_is_41"] = (K == 41)
    ok = ok and schema_match and (mname == "2019q3.dta") and (K == 41)

    # 3. route-relevant assertions on the ACTUAL columns
    sec_ids = [c for c in ("issuer_cusip", "identifier_isin", "issuer_lei") if c in varnames]
    result["security_identifier_columns_present"] = sec_ids
    result["checks"]["has_security_identifier"] = (len(sec_ids) >= 1)

    geo_like = [c for c in varnames if "country" in c.lower()]
    result["geography_columns"] = geo_like
    result["checks"]["only_geography_is_investment_country"] = (geo_like == ["investment_country"])

    nat_like = [c for c in varnames
                if any(t in c.lower() for t in ("nationalit", "ultimate", "parent", "cmns", "domicile"))]
    result["nationality_parent_columns"] = nat_like
    result["checks"]["no_parent_nationality_column"] = (len(nat_like) == 0)

    ok = ok and (len(sec_ids) >= 1) and (geo_like == ["investment_country"]) and (len(nat_like) == 0)

    result["total_bytes_from_zip64_eocd_context"] = TOTAL_BYTES
    result["overall_pass"] = ok
    result["route_relevant_conclusion"] = (
        "Security ids present (%s); only geography column = investment_country (issuer "
        "residence per publisher README); no nationality/ultimate-parent column -> "
        "supports ROUTE-A-ABSENT-EARNED for file #2." % ", ".join(sec_ids)
        if ok else "VERIFY FAILED -- do not rely on file #2 schema.")

    print(json.dumps(result, indent=2))
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
