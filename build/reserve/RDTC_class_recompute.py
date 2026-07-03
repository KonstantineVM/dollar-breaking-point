#!/usr/bin/env python3
"""
RDT-C Part 1 (class-level leg) — China's US LT securities holdings AND active flows BY ASSET CLASS,
from the on-disk TIC files. Deterministic: re-running regenerates byte-identical
build/reserve/RDTC_class_flows.json and the same panel content (content-hash recorded in the JSON).

Pre-registered contract: build/reserve/RDTC_prediction.md (committed 2026-07-02, before this build).
  - Verdict axis  = the RDT-B recent-3y window VERBATIM (read from RDTB_k3_distribution.json, not typed in).
  - Context windows: full (2013-01 -> latest published) and freeze-era (2022-03 -> latest published).
  - Ledger is ACTIVE (transactions) basis only; per-class valuation residual = dHoldings - active,
    direction stated per class; a valuation loss is NEVER counted as selling.
  - Mechanical rule: A >= 0.5|X| -> WITHIN-US-ROTATION ; A <= 0.1|X| -> LEFT-US-SECURITIES ; else MIXED;
    variants disagreeing on the verdict axis -> MIXED-BY-CUSTODY.
  - 2023-02 Form S -> SLT transactions basis break carried row-by-row (rdt_k3_provenance.md precedent).

Writes ONLY:
  build/reserve/RDTC_class_flows.json
  build/reserve/RDTC_class_panel.parquet
No network. No date, no probability. Every number computed from the on-disk inputs below.
"""

import csv
import hashlib
import io
import json
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # -> build/
REPO = os.path.dirname(ROOT)

SLT1_PATH = os.path.join(ROOT, "data", "treasury_tic", "current", "slt_tables", "slt_table1.txt")
SLT3_PATH = os.path.join(ROOT, "reserve", "rdt_evidence", "tic", "slt_table3.txt")
S1_PATH = os.path.join(ROOT, "reserve", "rdt_evidence", "tic", "s1_globl.txt")
SLT3D_PATH = os.path.join(ROOT, "reserve", "rdt_evidence", "tic", "slt3d_globl.csv")
MFH_PATH = os.path.join(ROOT, "reserve", "rdt_evidence", "tic", "mfhhis01.csv")
RDTB_DIST_PATH = os.path.join(ROOT, "reserve", "RDTB_k3_distribution.json")
RDTB_PANEL_PATH = os.path.join(ROOT, "reserve", "RDTB_k3_panel.parquet")

OUT_JSON = os.path.join(ROOT, "reserve", "RDTC_class_flows.json")
OUT_PARQUET = os.path.join(ROOT, "reserve", "RDTC_class_panel.parquet")

COUNTRIES = ["China, Mainland", "Belgium", "Luxembourg"]
CLASSES = ["treasury_lt", "agency_lt", "corp_other_bonds_lt", "equity_lt"]
ALL_CLASSES = CLASSES + ["total_lt"]

# Form S (s1_globl.txt) numeric columns [1]..[12] follow country, code, month.
# Net foreign purchases per DOMESTIC class = gross purchases by foreigners - gross sales by foreigners:
#   treasury_lt            = [1] - [7]
#   agency_lt              = [2] - [8]
#   corp_other_bonds_lt    = [3] - [9]
#   equity_lt              = [4] - [10]
# ([5],[6],[11],[12] are FOREIGN securities -- out of scope.)
FORM_S_NET = {"treasury_lt": (1, 7), "agency_lt": (2, 8), "corp_other_bonds_lt": (3, 9), "equity_lt": (4, 10)}

BREAK_MONTH = "2023-02"  # publisher basis break: Form S before, expanded Form SLT from this month
FULL_START = "2013-01"
FREEZE_START = "2022-03"

BOND_DIRECTION = (
    "bond class: the valuation residual is a price effect (rates/credit). The 2022 rates selloff CUT "
    "bond values -- a negative residual is a valuation loss, NEVER counted as selling (the false-exit "
    "confound, per class)."
)
EQUITY_DIRECTION = (
    "equity class: the valuation residual moves with the US equity market -- a positive residual is "
    "market appreciation (not buying); a negative residual is a market fall (not selling)."
)
DIRECTION_RULE = {
    "treasury_lt": BOND_DIRECTION,
    "agency_lt": BOND_DIRECTION,
    "corp_other_bonds_lt": BOND_DIRECTION,
    "equity_lt": EQUITY_DIRECTION,
    "total_lt": "total: mixture of the bond and equity direction rules above; not separately interpreted.",
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def month_range(a, b):
    """Inclusive list of YYYY-MM strings a..b."""
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    out = []
    while (ya, ma) <= (yb, mb):
        out.append(f"{ya:04d}-{ma:02d}")
        ma += 1
        if ma == 13:
            ma, ya = 1, ya + 1
    return out


def prev_month(m):
    y, mm = int(m[:4]), int(m[5:7])
    mm -= 1
    if mm == 0:
        mm, y = 12, y - 1
    return f"{y:04d}-{mm:02d}"


def num(tok):
    """Parse a TIC token: strip quotes/commas/CR; 'n.a.' -> None."""
    t = tok.strip().strip('"').replace(",", "").strip()
    if t in ("n.a.", "na", "", "n.a"):
        return None
    return float(t)


# ---------------------------------------------------------------- SLT Table 1 (by-country, by-class)
def parse_slt_table1():
    """Return (rows, quoted_header_lines). rows: dict[(country, month)] -> dict of 15 floats/None.
    Column order per the file's own machine-name line (line 9)."""
    with open(SLT1_PATH, encoding="utf-8", errors="replace") as f:
        lines = [ln.rstrip("\r\n") for ln in f]
    header_quote = [ln.rstrip() for ln in lines[0:9]]
    machine = lines[8].split("\t")
    expected = [
        "country", "country_code", "date",
        "for_lt_total_pos", "for_lt_total_net", "for_lt_total_valchg",
        "for_lt_treas_pos", "for_lt_treas_net", "for_lt_treas_valchg",
        "for_lt_agcy_pos", "for_lt_agcy_net", "for_lt_agcy_valchg",
        "for_lt_corp_pos", "for_lt_corp_net", "for_lt_corp_valchg",
        "for_lt_eqty_pos", "for_lt_eqty_net", "for_lt_eqty_valchg",
    ]
    assert [m.strip() for m in machine] == expected, f"slt_table1 machine header changed: {machine}"
    rows = {}
    for ln in lines[9:]:
        parts = ln.split("\t")
        if len(parts) != 18 or not re.match(r"^\d{4}-\d{2}$", parts[2].strip()):
            continue
        country = parts[0].strip()
        if country not in COUNTRIES:
            continue
        month = parts[2].strip()
        rows[(country, month)] = {expected[i]: num(parts[i]) for i in range(3, 18)}
    return rows, header_quote


# ---------------------------------------------------------------- SLT Table 3 (Treasury-only, cross-check)
def parse_slt_table3():
    with open(SLT3_PATH, encoding="utf-8", errors="replace") as f:
        lines = [ln.rstrip("\r\n") for ln in f]
    header_quote = [ln.rstrip() for ln in lines[0:9]]
    machine = [m.strip() for m in lines[8].split("\t")]
    assert machine[:3] == ["country", "country_code", "date"], f"slt_table3 header changed: {machine}"
    i_net = machine.index("for_lt_treas_net")
    rows = {}
    for ln in lines[9:]:
        parts = ln.split("\t")
        if len(parts) <= i_net or not re.match(r"^\d{4}-\d{2}$", parts[2].strip()):
            continue
        country = parts[0].strip()
        if country not in COUNTRIES:
            continue
        rows[(country, parts[2].strip())] = num(parts[i_net])
    return rows, header_quote


# ---------------------------------------------------------------- Form S (s1_globl.txt)
def parse_form_s():
    with open(S1_PATH, encoding="utf-8", errors="replace") as f:
        lines = [ln.rstrip("\r\n").rstrip("\r") for ln in f]
    header_quote = [ln.rstrip() for ln in lines[0:17]]
    rows = {}
    for ln in lines:
        parts = next(csv.reader([ln], delimiter="\t"))
        if len(parts) < 15:
            continue
        country = parts[0].strip().strip('"')
        if country not in COUNTRIES:
            continue
        month = parts[2].strip()
        if not re.match(r"^\d{4}-\d{2}$", month):
            continue
        vals = [num(p) for p in parts[3:15]]  # [1]..[12]
        net = {}
        for cls, (b, s) in FORM_S_NET.items():
            gb, gs = vals[b - 1], vals[s - 1]
            net[cls] = None if (gb is None or gs is None) else gb - gs
        rows[(country, month)] = net
    return rows, header_quote


# ---------------------------------------------------------------- panel
def build_panel(slt1, form_s, latest_month):
    months = month_range(FULL_START, latest_month)
    recs = []
    for country in COUNTRIES:
        for m in months:
            slt_row = slt1.get((country, m))
            fs_row = form_s.get((country, m))
            for cls in ALL_CLASSES:
                key = {
                    "treasury_lt": "treas", "agency_lt": "agcy",
                    "corp_other_bonds_lt": "corp", "equity_lt": "eqty", "total_lt": "total",
                }[cls]
                pos = slt_row.get(f"for_lt_{key}_pos") if slt_row else None
                valchg = slt_row.get(f"for_lt_{key}_valchg") if slt_row else None
                pos_source = "slt_table1.txt" if pos is not None else None
                if m < BREAK_MONTH:
                    basis = "FORM_S"
                    if cls == "total_lt":
                        act = None
                        if fs_row and all(fs_row.get(c) is not None for c in CLASSES):
                            act = sum(fs_row[c] for c in CLASSES)
                    else:
                        act = fs_row.get(cls) if fs_row else None
                    tx_source = "s1_globl.txt" if act is not None else None
                    valchg = None  # publisher: no by-country valuation change before 2023-02
                else:
                    basis = "SLT"
                    act = slt_row.get(f"for_lt_{key}_net") if slt_row else None
                    tx_source = "slt_table1.txt" if act is not None else None
                recs.append({
                    "country": country, "month": m, "asset_class": cls,
                    "pos_musd": pos, "active_musd": act, "valchg_musd": valchg,
                    "basis": basis, "pos_source": pos_source, "tx_source": tx_source,
                })
    df = pd.DataFrame.from_records(recs)
    return df


def panel_content_sha(df):
    buf = io.StringIO()
    df.to_csv(buf, index=False, float_format="%.6f")
    return hashlib.sha256(buf.getvalue().encode()).hexdigest()


# ---------------------------------------------------------------- window machinery
def get_series(df, countries, cls, col):
    """Sum a column across the given countries, month-indexed; None if any country missing that month."""
    sub = df[(df["country"].isin(countries)) & (df["asset_class"] == cls)]
    piv = sub.pivot(index="month", columns="country", values=col)
    return piv


def window_sum(piv, months):
    """Sum over window months x countries. Returns (sum, n_nonmissing_months, n_window_months).
    A month counts non-missing only if ALL countries in the variant have a value."""
    got = piv.reindex(months)
    row_ok = got.notna().all(axis=1)
    total = got[row_ok].sum().sum()
    return (float(total), int(row_ok.sum()), len(months))


def holdings_delta(piv, ref_month, end_month):
    ref = piv.reindex([ref_month]).iloc[0]
    end = piv.reindex([end_month]).iloc[0]
    if ref.isna().any() or end.isna().any():
        return None
    return float(end.sum() - ref.sum())


def classify(X, A):
    """Pre-registered mechanical rule. X = UST active flow (expected negative), A = non-UST active sum."""
    if X >= 0:
        return "RULE-NOT-APPLICABLE (X >= 0: no UST active outflow over this window)"
    absX = abs(X)
    if A >= 0.5 * absX:
        return "WITHIN-US-ROTATION"
    if A <= 0.1 * absX:
        return "LEFT-US-SECURITIES"
    return "MIXED"


def build_ledger(df, variant_name, countries, window_name, start, end, role):
    months = month_range(start, end)
    ref_month = prev_month(start)
    per_class = {}
    for cls in CLASSES:
        act_piv = get_series(df, countries, cls, "active_musd")
        pos_piv = get_series(df, countries, cls, "pos_musd")
        val_piv = get_series(df, countries, cls, "valchg_musd")
        a_sum, a_n, a_tot = window_sum(act_piv, months)
        dh = holdings_delta(pos_piv, ref_month, end)
        # published cumulative valuation change over the SLT-covered part of the window
        slt_months = [m for m in months if m >= BREAK_MONTH]
        v_sum, v_n, v_tot = window_sum(val_piv, slt_months) if slt_months else (0.0, 0, 0)
        val_resid = None if dh is None else dh - a_sum
        window_fully_slt = (len(slt_months) == len(months))
        if val_resid is not None and window_fully_slt and v_n == v_tot:
            other_changes = ("other_changes_busd (survey benchmark / coverage reattribution; "
                             "NOT selling and NOT price): %.3f" % ((val_resid - v_sum) / 1000.0))
        elif val_resid is not None:
            other_changes = ("other-changes decomposition PARTIAL -- window includes pre-2023-02 months "
                             "with no published by-country valuation change; not decomposed, not interpolated")
        else:
            other_changes = "NOT AVAILABLE (delta holdings unavailable)"
        entry = {
            "active_cum_busd": round(a_sum / 1000.0, 3),
            "active_months_nonmissing": f"{a_n}/{a_tot}",
            "delta_holdings_busd": (round(dh / 1000.0, 3) if dh is not None else
                                    "NOT AVAILABLE -- by-class SLT positions begin 2020-01; "
                                    f"reference month {ref_month} precedes coverage"),
            "valuation_residual_busd": (round(val_resid / 1000.0, 3) if val_resid is not None else
                                        "NOT AVAILABLE (delta holdings unavailable)"),
            "residual_decomposition": other_changes,
            "valuation_residual_direction": (
                ("valuation GAIN over window" if val_resid > 0 else
                 "valuation LOSS over window" if val_resid < 0 else "flat")
                if val_resid is not None else "UNDETERMINED over this window"),
            "direction_rule": DIRECTION_RULE[cls],
            "published_valchg_cum_busd_slt_part": round(v_sum / 1000.0, 3),
            "published_valchg_months": f"{v_n}/{v_tot} (SLT-covered months only; none exist pre-2023-02)",
        }
        per_class[cls] = entry
    X = per_class["treasury_lt"]["active_cum_busd"]
    a_parts = {c: per_class[c]["active_cum_busd"] for c in ("agency_lt", "corp_other_bonds_lt", "equity_lt")}
    A = round(sum(a_parts.values()), 3)
    n_form_s = len([m for m in months if m < BREAK_MONTH])
    n_slt = len(months) - n_form_s
    ledger = {
        "window": window_name, "role": role, "start": start, "end": end,
        "holdings_reference_month": ref_month,
        "variant": variant_name, "countries": countries,
        "basis_composition": {"form_s_months": n_form_s, "slt_months": n_slt,
                              "break_at": BREAK_MONTH if (n_form_s and n_slt) else
                              ("none inside window -- uniform SLT basis" if n_form_s == 0 else
                               "none inside window -- uniform Form S basis")},
        "X_ust_active_busd": X,
        "A_nonust_active_busd": {**{k: v for k, v in a_parts.items()}, "total": A},
        "A_over_absX": (round(A / abs(X), 4) if X != 0 else None),
        "residual_left_us_busd": (round(abs(X) - A, 3) if X < 0 else
                                  "not defined (X >= 0)"),
        "ledger_identity": ("|UST-active| = A(absorbed within US LT) + residual(left US securities): "
                            f"{abs(X):.3f} = {A:.3f} + {abs(X) - A:.3f} $bn" if X < 0 else
                            "X >= 0: no outflow to decompose"),
        "branch": classify(X, A),
        "per_class": per_class,
    }
    return ledger


# ---------------------------------------------------------------- main build (pure; run twice for determinism)
def build_payload():
    slt1, slt1_hdr = parse_slt_table1()
    slt3, slt3_hdr = parse_slt_table3()
    form_s, s1_hdr = parse_form_s()

    latest_month = max(m for (_, m) in slt1.keys())
    df = build_panel(slt1, form_s, latest_month)

    # ---- RDT-B verdict axis, read verbatim from the RDT-B artifact (not typed in)
    with open(RDTB_DIST_PATH) as f:
        rdtb = json.load(f)
    r3 = rdtb["payload"]["recent_3y_window"]
    china_row = next(r for r in r3["distribution_r_all_countries"] if r["country"] == "China, Mainland")
    v_start, v_end = china_row["window_start"], china_row["window_end"]
    rdtb_china_3y = china_row["sum_net_purchases_busd"]

    windows = [
        ("recent_3y_verdict_axis", v_start, v_end, "VERDICT AXIS (RDT-B recent-3y window verbatim)"),
        ("full_2013", FULL_START, latest_month, "context (pre-registered)"),
        ("freeze_era_2022_03", FREEZE_START, latest_month, "context (pre-registered, labelled freeze-era)"),
    ]
    variants = [("china_alone", ["China, Mainland"]),
                ("china_belgium_luxembourg", COUNTRIES)]

    ledgers = {}
    for wname, ws, we, role in windows:
        ledgers[wname] = {}
        for vname, clist in variants:
            ledgers[wname][vname] = build_ledger(df, vname, clist, wname, ws, we, role)

    # verdict-axis custody-band branch
    b1 = ledgers["recent_3y_verdict_axis"]["china_alone"]["branch"]
    b2 = ledgers["recent_3y_verdict_axis"]["china_belgium_luxembourg"]["branch"]
    headline = b1 if b1 == b2 else f"MIXED-BY-CUSTODY (china_alone: {b1}; china_belgium_luxembourg: {b2})"

    # ---- RDT-B reconciliation
    rdtb_panel = pd.read_parquet(RDTB_PANEL_PATH)
    my_ust = df[(df["asset_class"] == "treasury_lt")][["country", "month", "active_musd"]].copy()
    my_ust["mine_busd"] = my_ust["active_musd"] / 1000.0
    mrg = my_ust.merge(
        rdtb_panel[rdtb_panel["country"].isin(COUNTRIES)][["country", "month", "net_lt_purchases_busd"]],
        on=["country", "month"], how="inner")
    both = mrg.dropna(subset=["mine_busd", "net_lt_purchases_busd"])
    monthly_diff = (both["mine_busd"] - both["net_lt_purchases_busd"]).abs()
    max_monthly = float(monthly_diff.max())
    max_row = both.loc[monthly_diff.idxmax()]
    v_months = month_range(v_start, v_end)
    my_china_3y = float(both[(both["country"] == "China, Mainland") & (both["month"].isin(v_months))]["mine_busd"].sum())
    # table1 vs table3 LT-Treasury net (post-break, both published)
    t3_diffs = []
    for (c, m), v3 in slt3.items():
        if v3 is None or m < BREAK_MONTH:
            continue
        v1 = slt1.get((c, m), {}).get("for_lt_treas_net")
        if v1 is not None:
            t3_diffs.append(abs(v1 - v3))
    recon = {
        "verdict_axis_china_ust_active_busd_mine": round(my_china_3y, 3),
        "verdict_axis_china_ust_active_busd_rdtb": rdtb_china_3y,
        "verdict_axis_abs_diff_busd": round(abs(my_china_3y - rdtb_china_3y), 6),
        "monthly_vs_rdtb_panel": {
            "countries": COUNTRIES,
            "overlapping_nonmissing_months": int(len(both)),
            "max_abs_diff_busd": round(max_monthly, 6),
            "max_diff_at": {"country": str(max_row["country"]), "month": str(max_row["month"])},
        },
        "slt_table1_vs_slt_table3_lt_treas_net": {
            "cells_compared": len(t3_diffs),
            "max_abs_diff_musd": (round(max(t3_diffs), 3) if t3_diffs else None),
        },
    }

    # ---- SLT identity diagnostic: dPos - (net + valchg) on the SLT span (should be ~0 by construction)
    gaps = []
    for country in COUNTRIES:
        for cls in ALL_CLASSES:
            sub = df[(df["country"] == country) & (df["asset_class"] == cls)].set_index("month").sort_index()
            for m in sub.index:
                if m < BREAK_MONTH:
                    continue
                pm = prev_month(m)
                if pm not in sub.index:
                    continue
                p0, p1 = sub.at[pm, "pos_musd"], sub.at[m, "pos_musd"]
                a, v = sub.at[m, "active_musd"], sub.at[m, "valchg_musd"]
                if None in (p0, p1, a, v) or any(pd.isna(x) for x in (p0, p1, a, v)):
                    continue
                gaps.append(abs((p1 - p0) - (a + v)))
    identity_max_musd = round(max(gaps), 3) if gaps else None

    # ---- series summaries
    summaries = {}
    for country in COUNTRIES:
        summaries[country] = {}
        for cls in ALL_CLASSES:
            sub = df[(df["country"] == country) & (df["asset_class"] == cls)].set_index("month").sort_index()
            pos = sub["pos_musd"].dropna()
            act = sub["active_musd"].dropna()
            summaries[country][cls] = {
                "positions_span": (f"{pos.index.min()}..{pos.index.max()}" if len(pos) else "none"),
                "positions_first_last_busd": ([round(pos.iloc[0] / 1000, 3), round(pos.iloc[-1] / 1000, 3)]
                                              if len(pos) else None),
                "active_span": (f"{act.index.min()}..{act.index.max()}" if len(act) else "none"),
                "active_months": int(len(act)),
                "active_form_s_months": int(len(sub[(sub.index < BREAK_MONTH) & sub["active_musd"].notna()])),
                "active_slt_months": int(len(sub[(sub.index >= BREAK_MONTH) & sub["active_musd"].notna()])),
                "active_cum_full_busd": round(float(act.sum()) / 1000, 3),
            }

    schema = {
        "slt_table1.txt": {
            "path": os.path.relpath(SLT1_PATH, REPO),
            "quoted_header_lines_1_to_9": slt1_hdr,
            "reading": ("By-country U.S. LONG-TERM securities: five class blocks -- Total U.S. Securities; "
                        "U.S. Treasuries; U.S. Agency Bonds; U.S. Corp. & Other Bonds; U.S. Corp. Equity -- "
                        "each with Holdings / Net U.S. Sales / Valuation Change, millions USD. "
                        "Observed spans for China, Belgium, Luxembourg: Holdings 2020-01..{L}; "
                        "Net U.S. Sales and Valuation Change n.a. before 2023-02 (expanded-SLT basis "
                        "2023-02..{L}).").replace("{L}", latest_month),
        },
        "s1_globl.txt (Form S)": {
            "path": os.path.relpath(S1_PATH, REPO),
            "quoted_header_lines_1_to_17": s1_hdr,
            "reading": ("Gross purchases/sales by foreigners, by country, monthly to 2023-01 (discontinued "
                        "Form S). Domestic classes: [1]/[7] Marketable U.S. Treasury & FFB bonds+notes; "
                        "[2]/[8] Bonds of U.S. Gov't corps & federally sponsored agencies; [3]/[9] U.S. "
                        "corporate & other bonds; [4]/[10] U.S. corporate stocks ([5],[6],[11],[12] are "
                        "foreign securities -- out of scope). Net per class = purchases - sales. "
                        "China/Belgium/Luxembourg: complete 2013-01..2023-01 (121 months each)."),
        },
        "slt_table3.txt": {
            "path": os.path.relpath(SLT3_PATH, REPO),
            "quoted_header_lines_1_to_9": slt3_hdr,
            "reading": ("TREASURY-ONLY by country (total/long-term/short-term Treasuries; holdings, Net U.S. "
                        "Sales, Valuation Change). No agency/corporate/equity classes. Used only to "
                        "cross-check the LT-Treasury net column of slt_table1.txt (RDT-B's post-break source)."),
        },
        "slt3d_globl.csv": {
            "path": os.path.relpath(SLT3D_PATH, REPO),
            "quoted_title_lines": ['"TABLE 3D:  U.S",". Treasury Secu","rities Held by","Foreign Residen","ts 1/"',
                                   '"","Millio","ns of dollars"',
                                   '"","","","Total U.S.","Long-term","Short-term" / "Treasury Securities"'],
            "reading": ("Frozen all-countries TREASURY-ONLY holdings 2011-09..2023-01. NO class detail beyond "
                        "Treasury LT/ST -- carries no agency/corporate/equity columns. Not used for the class "
                        "panel (no by-class positions exist on disk before 2020-01; gap stated, not interpolated)."),
        },
        "mfhhis01.csv": {
            "path": os.path.relpath(MFH_PATH, REPO),
            "quoted_title_lines": ["MAJOR FOREIGN HOLDERS OF TREASURY SECURITIES", "(in billions of dollars)",
                                   "HOLDINGS 1/ AT END OF PERIOD"],
            "reading": ("MFH history: TOTAL Treasury holdings only (no asset-class split). Not usable for the "
                        "class panel; it is RDT-B's holdings source and enters here only via the RDT-B "
                        "reconciliation."),
        },
    }

    checks = {
        "window_end_equals_latest_published_month": v_end == latest_month,
        "latest_published_month": latest_month,
        "verdict_window_entirely_on_slt_basis": v_start >= BREAK_MONTH,
        "form_s_121_months_each_country": all(
            summaries[c]["treasury_lt"]["active_form_s_months"] == 121 for c in COUNTRIES),
        "slt_identity_max_abs_gap_musd_dPos_minus_net_minus_valchg": identity_max_musd,
        "slt_identity_gap_reading": (
            "dHoldings - (Net U.S. Sales + Valuation Change) is NOT zero in the published SLT data: the "
            "holdings level incorporates annual survey benchmarks and coverage/custody reattribution that "
            "the monthly net+valchg columns do not. Largest single-month gaps sit in the custody centers "
            "(Belgium, Luxembourg). This 'other changes' leg is quantified per class per window in each "
            "ledger's residual_decomposition where the window is fully SLT-covered; it is neither selling "
            "nor a price move and is never read as either."),
        "rdtb_verdict_axis_recon_abs_diff_busd": recon["verdict_axis_abs_diff_busd"],
        "rdtb_monthly_recon_max_abs_diff_busd": recon["monthly_vs_rdtb_panel"]["max_abs_diff_busd"],
        "no_date_no_probability": "no breaking-point date and no probability appear in this artifact",
    }

    payload = {
        "artifact": "RDTC_class_flows (RDT-C Part 1, class-level leg)",
        "establishment": ("NOT ESTABLISHED -- output of RDTC_class_recompute.py; every number below is an "
                          "OUTPUT pending its verifier scenario (orchestrator re-run of this script and the "
                          "RDT-C Part 2/3 assembly). The SAFE leg is NOT integrated here."),
        "contract": "build/reserve/RDTC_prediction.md (pre-registered before this build)",
        "inputs_sha256": {
            os.path.relpath(p, REPO): sha256_file(p)
            for p in [SLT1_PATH, SLT3_PATH, S1_PATH, SLT3D_PATH, MFH_PATH, RDTB_DIST_PATH, RDTB_PANEL_PATH]
        },
        "class_schema_quoted": schema,
        "basis_break": ("Publisher basis break at 2023-02 carried row-by-row in the panel ('basis' column): "
                        "active flows 2013-01..2023-01 = Form S (s1_globl.txt); 2023-02..%s = expanded Form "
                        "SLT (slt_table1.txt Net U.S. Sales). By-country valuation change does not exist "
                        "before 2023-02 (publisher statement, rdt_k3_provenance.md); by-class positions do "
                        "not exist on disk before 2020-01 -- both gaps stated, not interpolated." % latest_month),
        "windows": {w[0]: {"start": w[1], "end": w[2], "role": w[3]} for w in windows},
        "mechanical_rule": ("X = UST active flow; A = agencies+corporates+equities active, same window/variant. "
                            "WITHIN-US-ROTATION iff A >= 0.5|X|; LEFT-US-SECURITIES iff A <= 0.1|X| (incl. A<0); "
                            "MIXED otherwise; variants disagreeing on the verdict axis -> MIXED-BY-CUSTODY. "
                            "Thresholds fixed in RDTC_prediction.md before any data."),
        "series_summaries": summaries,
        "ledgers": ledgers,
        "verdict_axis_branch_headline": {
            "window": "recent_3y_verdict_axis",
            "china_alone": b1,
            "china_belgium_luxembourg": b2,
            "headline_branch": headline,
            "note": ("BRANCH VERDICT on the verdict axis only; other windows are pre-registered context. "
                     "SAFE leg not integrated here (Part 2/3 assembly does that)."),
        },
        "valuation_direction_statements": {c: DIRECTION_RULE[c] for c in ALL_CLASSES},
        "rdtb_reconciliation": recon,
        "self_check": checks,
        "panel": {
            "path": os.path.relpath(OUT_PARQUET, REPO),
            "rows": int(len(df)),
            "columns": list(df.columns),
            "countries": COUNTRIES,
            "classes": ALL_CLASSES,
            "months": f"{FULL_START}..{latest_month}",
            "content_sha256_of_canonical_csv": panel_content_sha(df),
        },
    }
    return payload, df


def main():
    payload1, df = build_payload()
    payload2, _ = build_payload()
    s1 = json.dumps(payload1, indent=1, sort_keys=False)
    s2 = json.dumps(payload2, indent=1, sort_keys=False)
    payload1["self_check"]["double_build_identical"] = (s1 == s2)
    with open(OUT_JSON, "w") as f:
        json.dump(payload1, f, indent=1, sort_keys=False)
        f.write("\n")
    df.to_parquet(OUT_PARQUET, index=False)
    print("wrote", OUT_JSON)
    print("wrote", OUT_PARQUET, len(df), "rows")
    print("double_build_identical:", s1 == s2)
    v = payload1["verdict_axis_branch_headline"]
    print("verdict-axis branch:", v["headline_branch"])
    for var in ("china_alone", "china_belgium_luxembourg"):
        L = payload1["ledgers"]["recent_3y_verdict_axis"][var]
        print(f"  {var}: X={L['X_ust_active_busd']} A={L['A_nonust_active_busd']['total']} "
              f"A/|X|={L['A_over_absX']} residual={L['residual_left_us_busd']} -> {L['branch']}")
    print("recon:", payload1["rdtb_reconciliation"]["verdict_axis_abs_diff_busd"],
          payload1["rdtb_reconciliation"]["monthly_vs_rdtb_panel"]["max_abs_diff_busd"])


if __name__ == "__main__":
    main()
