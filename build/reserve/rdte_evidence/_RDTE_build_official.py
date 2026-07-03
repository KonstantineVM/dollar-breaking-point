#!/usr/bin/env python3
"""RDT-E Part 1(iv): build the aggregate foreign-official UST series (TIC MFH/SLT5)
and the FRBNY H.4.1 custody series (via FRED mirror), monthly, 2013-01..latest.

Inputs (all retained on disk; no numbers hardcoded):
  - build/reserve/rdt_evidence/tic/mfhhis01.csv        (TIC MFH history, fetched 2026-07-01)
  - build/reserve/rdt_evidence/tic/slt_table5.txt      (TIC SLT Table 5, fetched 2026-07-01;
      byte-identical live refetch retained as rdte_evidence/slt_table5_live.txt, 2026-07-02)
  - build/reserve/rdte_evidence/fred_wmtsecl1.csv      (FRED WMTSECL1, fetched 2026-07-02)

Output: build/reserve/rdte_official_series.csv and a JSON blob (stdout) with the
coverage, cross-checks, and axis changes for the manifest.
"""
import csv, json, re, sys
from pathlib import Path

BASE = Path("/home/user/dollar-breaking-point/build/reserve")
MON = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}

# ---------- 1. TIC MFH history: "For. Official" row per year block ----------
mfh_path = BASE / "rdt_evidence/tic/mfhhis01.csv"
rows = list(csv.reader(mfh_path.open()))
tic = {}          # "YYYY-MM" -> (value_busd, source)
cur_months = None  # list of "YYYY-MM" for the current block, column-aligned
for r in rows:
    cells = [c.strip() for c in r]
    if not any(cells):
        continue
    if cells and cells[0] == "" and cells[1] in MON:
        month_names = [c for c in cells[1:] if c in MON]
        cur_month_names = month_names
        cur_months = None  # wait for the year row
        continue
    if cells and cells[0] == "Country" and re.match(r"^(19|20)\d\d$", cells[1] or ""):
        years = [c for c in cells[1:] if re.match(r"^(19|20)\d\d$", c)]
        if len(years) == len(cur_month_names):
            cur_months = [f"{y}-{MON[m]:02d}" for y, m in zip(years, cur_month_names)]
        else:
            cur_months = None
        continue
    if cells[0].lstrip() .startswith("For. Official") and cur_months:
        vals = cells[1:1 + len(cur_months)]
        for ym, v in zip(cur_months, vals):
            if v not in ("", "n/a"):
                yr = int(ym[:4])
                if 2013 <= yr <= 2025 and ym not in tic:
                    # blocks are newest-first; duplicated columns (pre-2012 double-June)
                    # never reach here because of the year filter
                    tic[ym] = (float(v), "rdt_evidence/tic/mfhhis01.csv")

# ---------- 2. SLT Table 5: "Of Which: Foreign Official" ----------
slt5_path = BASE / "rdt_evidence/tic/slt_table5.txt"
slt5 = {}
header_months = None
for line in slt5_path.open():
    parts = [p.strip() for p in line.rstrip("\n").split("\t")]
    if parts and parts[0] == "Country":
        header_months = [p for p in parts[1:] if re.match(r"^\d{4}-\d{2}$", p)]
    if parts and parts[0] == "Of Which: Foreign Official" and header_months:
        vals = parts[1:1 + len(header_months)]
        for ym, v in zip(header_months, vals):
            if v:
                slt5[ym] = float(v)

# cross-check: overlap between mfhhis01 and slt_table5
overlap = sorted(set(tic) & set(slt5))
overlap_check = {ym: {"mfhhis01": tic[ym][0], "slt_table5": slt5[ym],
                      "diff": round(tic[ym][0] - slt5[ym], 3)} for ym in overlap}
max_overlap_diff = max((abs(d["diff"]) for d in overlap_check.values()), default=None)

# extend TIC series with slt_table5 months not in mfhhis01 (2026 months)
for ym, v in slt5.items():
    if ym not in tic:
        tic[ym] = (v, "rdt_evidence/tic/slt_table5.txt")

# ---------- 3. FRED WMTSECL1 weekly -> month-end (last Wednesday obs per month) ----------
fred_path = BASE / "rdte_evidence/fred_wmtsecl1.csv"
frbny = {}  # "YYYY-MM" -> (busd, obs_date)
with fred_path.open() as f:
    rd = csv.DictReader(f)
    for row in rd:
        d = row["observation_date"]
        v = row["WMTSECL1"]
        if not v or v == ".":
            continue
        ym = d[:7]
        # rows are chronological; keep the last (latest Wednesday) per month
        frbny[ym] = (round(float(v) / 1000.0, 3), d)

# ---------- 4. assemble monthly CSV 2013-01..latest ----------
all_months = sorted(set(list(tic) + [m for m in frbny if m >= "2013-01"]))
all_months = [m for m in all_months if m >= "2013-01"]
out_path = BASE / "rdte_official_series.csv"
with out_path.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["month", "tic_official_ust_busd", "tic_source",
                "frbny_custody_ust_busd", "frbny_obs_date", "frbny_source"])
    for ym in all_months:
        t = tic.get(ym)
        h = frbny.get(ym)
        w.writerow([ym,
                    t[0] if t else "", t[1] if t else "",
                    h[0] if h else "", h[1] if h else "",
                    "rdte_evidence/fred_wmtsecl1.csv" if h else ""])

# ---------- 5. axis changes (context; the cap is applied at assembly) ----------
def delta(series, a, b):
    if a in series and b in series:
        va = series[a][0] if isinstance(series[a], tuple) else series[a]
        vb = series[b][0] if isinstance(series[b], tuple) else series[b]
        return {"start_month": a, "end_month": b, "start": va, "end": vb,
                "change_busd": round(vb - va, 3),
                "direction": "DECLINED" if vb < va else ("ROSE" if vb > va else "FLAT")}
    return {"start_month": a, "end_month": b, "error": "endpoint missing"}

tic_last = max(m for m in tic)
frb_last = max(frbny)
frb_series = {m: v for m, v in frbny.items()}
summary = {
    "tic": {
        "coverage": [min(tic), tic_last],
        "n_months": len([m for m in tic if m >= "2013-01"]),
        "verdict_axis_refmonth": delta(tic, "2023-04", "2026-04"),
        "verdict_axis_startmonth": delta(tic, "2023-05", "2026-04"),
        "full_window": delta(tic, "2013-01", tic_last),
        "overlap_months_mfhhis01_vs_slt5": len(overlap),
        "max_abs_overlap_diff_busd": max_overlap_diff,
    },
    "frbny": {
        "coverage": ["2013-01", frb_last],
        "verdict_axis_refmonth": delta(frb_series, "2023-04", "2026-04"),
        "verdict_axis_startmonth": delta(frb_series, "2023-05", "2026-04"),
        "full_window": delta(frb_series, "2013-01", frb_last),
        "full_window_to_tic_last": delta(frb_series, "2013-01", tic_last),
    },
    "cross_check_tic_minus_frbny": {
        ym: round((tic[ym][0] if isinstance(tic[ym], tuple) else tic[ym]) - frb_series[ym][0], 3)
        for ym in ["2013-01", "2023-04", "2026-04"] if ym in tic and ym in frb_series
    },
}
print(json.dumps(summary, indent=2))
