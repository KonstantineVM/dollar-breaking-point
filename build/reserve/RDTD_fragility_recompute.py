#!/usr/bin/env python3
"""RDT-D Part 1 -- fragility of the 446.5 $bn active-outflow figure.

Deterministic recompute: regenerates build/reserve/RDTD_fragility.json from the
on-disk inputs alone. Pre-registered contract: build/reserve/RDTD_prediction.md
(Part 1): per class and per custody variant over the verdict axis, compute
G = dH - V_stated - active; if |G_total| > 0.25 x |active_total| for the
China-alone variant, flag 446.5-UNRELIABLE, else RELIABLE-WITHIN-GAP.

Every number is computed here from the inputs; nothing is hardcoded. The 0.25
threshold fraction and the window definitions are pre-registered rule constants
(RDTD_prediction.md / RDTC_class_flows.json windows) and are asserted against
the contract text below. No date, no probability.

NOT ESTABLISHED: the output JSON is an estimation output pending its verifier
scenario (orchestrator re-run of this script reproducing the JSON byte-for-byte).
"""

import hashlib
import html as htmlmod
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "build" / "reserve"

PANEL_PATH = RES / "RDTC_class_panel.parquet"
FLOWS_PATH = RES / "RDTC_class_flows.json"
PREDICTION_PATH = RES / "RDTD_prediction.md"
OUT_PATH = RES / "RDTD_fragility.json"

# Retained publisher files carrying the attribution-mechanism language.
MECH_FILES = {
    "mfh": RES / "rdt_evidence" / "tic" / "mfh.txt",
    "seca": RES / "rdt_evidence" / "tic" / "tic_seca_page.html",
    "shl2025": RES / "rdtb_evidence" / "shl2025r_extracted.txt",
}

CLASSES = ["treasury_lt", "agency_lt", "corp_other_bonds_lt", "equity_lt"]
TOTAL = "total_lt"
CLASS_ALIAS = {"corp_lt": "corp_other_bonds_lt"}  # task-name -> panel-name

VARIANTS = {
    "china_alone": ["China, Mainland"],
    "china_belgium_luxembourg": ["China, Mainland", "Belgium", "Luxembourg"],
}

# Pre-registered windows (verbatim from RDTC_class_flows.json "windows" block;
# asserted against that committed ledger at runtime, not restated by hand).
WINDOW_IDS = ["recent_3y_verdict_axis", "freeze_era_2022_03", "full_2013"]

THRESHOLD_FRAC = 0.25  # pre-registered in RDTD_prediction.md; asserted below.

# SLT stated-valuation column exists only from this month (publisher property,
# carried in the committed panel: valchg_musd is non-missing 2023-02 onward only;
# verified from the data below, not assumed).
VSTATED_FIRST_EXPECTED = "2023-02"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def busd(musd):
    return round(musd / 1000.0, 3) if musd is not None else None


def month_range(start: str, end: str):
    out = []
    y, m = int(start[:4]), int(start[5:7])
    ye, me = int(end[:4]), int(end[5:7])
    while (y, m) <= (ye, me):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def prev_month(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    m -= 1
    if m == 0:
        y, m = y - 1, 12
    return f"{y:04d}-{m:02d}"


def strip_html(raw: str) -> str:
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S | re.I)
    txt = htmlmod.unescape(re.sub(r"<[^>]+>", " ", txt))
    return re.sub(r"\s+", " ", txt).strip()


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def quote_on_disk(path: Path, quote: str) -> bool:
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = strip_html(raw) if path.suffix.lower() in (".html", ".htm") else norm_ws(raw)
    return norm_ws(quote) in text


# ---------------------------------------------------------------------------
# The mechanism quotes (verbatim from the retained publisher files; each one is
# substring-verified against its file at runtime -- a failed match flips the
# self-check flag rather than silently passing).
# ---------------------------------------------------------------------------
MECH_QUOTES = [
    {
        "file": "build/reserve/rdt_evidence/tic/tic_seca_page.html",
        "role": "transactions side -- the discontinued Form S attributed transactions to the country TRANSACTING with the U.S. (publisher's own contrast, written when the SLT replaced Form S)",
        "quote": ("Note that the new data on purchases and sales of foreign securities show the "
                  "country that issued the securities, in contrast to the previous data that showed "
                  "the country doing the transactions with the U.S."),
    },
    {
        "file": "build/reserve/rdtb_evidence/shl2025r_extracted.txt",
        "role": "reporting basis -- TIC data attributed to the counterparty's country of legal residence; holdings surveys to the residence of the owner",
        "quote": ("TIC data are reported based on the counterparty’s country of legal residence. In the "
                  "case of the SHL, the country of holder is recorded based on the residence of the "
                  "security owner."),
    },
    {
        "file": "build/reserve/rdtb_evidence/shl2025r_extracted.txt",
        "role": "intermediary / financial-center (custodial) bias, naming Belgium, Luxembourg, Switzerland and the United Kingdom",
        "quote": ("Third, chains of foreign financial intermediaries are often involved in the custody or "
                  "management of securities. This “custodial bias” tends to overstate the amounts of "
                  "holdings by residents of countries with major custodial activities such as Belgium, "
                  "Luxembourg, Switzerland, and the United Kingdom."),
    },
    {
        "file": "build/reserve/rdtb_evidence/shl2025r_extracted.txt",
        "role": "ICSD attribution -- Euroclear (Belgium) / Clearstream (Luxembourg): large foreign holdings attributed to the ICSD country",
        "quote": ("Prominent ICSDs are Euroclear in "
                  "Belgium and Clearstream in Luxembourg. U.S. survey reporters typically report only "
                  "the country where the ICSD is located and thus large foreign holdings are attributed to "
                  "these countries."),
    },
    {
        "file": "build/reserve/rdtb_evidence/shl2025r_extracted.txt",
        "role": "the transactions-vs-positions gap itself, from the publisher: a non-zero G is a documented property of the system",
        "quote": ("Finally, securities lending and short sales can introduce a difference between "
                  "reported securities transactions and changes in reported positions."),
    },
    {
        "file": "build/reserve/rdtb_evidence/shl2025r_extracted.txt",
        "role": "the transactions-vs-positions gap, continued -- survives valuation adjustment",
        "quote": ("Thus, there will be a "
                  "difference between reported net transactions and the change in reported positions, "
                  "even after adjusting for valuation changes."),
    },
    {
        "file": "build/reserve/rdt_evidence/tic/mfh.txt",
        "role": "holdings side -- custody-based collection may not attribute to actual owners (MFH footnote 1/)",
        "quote": ("The data in this table are collected primarily from U.S.-based custodians and broker-dealers. "
                  "Since U.S. securities held in overseas custody accounts may not be attributed to the actual owners, "
                  "the data may not provide a precise accounting of individual country ownership of Treasury securities"),
    },
]

# The TIC FAQ page was NOT retained when Part 1 was first built; RDT-D Part 2 subsequently
# fetched it (cited in rdtd_pool_determination.md). It is NOT an input to any Part-1
# computation and no language from it is quoted here; the retention statement below is
# assertion-guarded so regeneration fails loudly rather than misdescribing the disk state.
TIC_FAQ_PATH = RES / "rdtd_evidence" / "tic_faq2.html"


def tic_faq_note():
    assert TIC_FAQ_PATH.exists(), (
        "TEMPLATE GUARD FAILED: build/reserve/rdtd_evidence/tic_faq2.html not on disk -- "
        "the Part-2 retention statement would misdescribe; refusing to emit it"
    )
    return {
        "note": (
            "The MFH footnote points to TIC FAQ #7 for the full attribution discussion; the FAQ page was "
            "not retained at Part-1 build time and was subsequently fetched by Part 2 as "
            "build/reserve/rdtd_evidence/tic_faq2.html (cited in rdtd_pool_determination.md). No language "
            "from it is quoted in this Part-1 mechanism composite, which is grounded entirely in the "
            "retained files listed (publisher's SECA release-notes page, the publisher's SHL 2025 survey "
            "report sections 4.2.4/4.3.4, and the MFH footnote); no sentence is paraphrased from memory."
        ),
        "tic_faq_file": "build/reserve/rdtd_evidence/tic_faq2.html",
        "tic_faq_sha256": sha256(TIC_FAQ_PATH),
        "role": ("NOT an input to any Part-1 computation (hence not in inputs_sha256); existence and sha "
                 "recorded only to keep the retention statement accurate"),
    }


def parse_other_changes(s):
    """Parse the trailing float from an RDTC residual_decomposition string, or None."""
    if not isinstance(s, str):
        return None
    m = re.search(r":\s*(-?\d+(?:\.\d+)?)\s*$", s)
    return float(m.group(1)) if m else None


def compute():
    inputs_sha = {
        str(p.relative_to(ROOT)): sha256(p)
        for p in [PANEL_PATH, FLOWS_PATH, PREDICTION_PATH] + sorted(set(MECH_FILES.values()))
    }

    prediction_text = PREDICTION_PATH.read_text(encoding="utf-8")
    threshold_clause_ok = (
        "G = ΔH − V_stated − active" in prediction_text
        and "|G_total| > 0.25 × |active_total|" in prediction_text
        and "China-alone" in prediction_text
    )

    flows = json.loads(FLOWS_PATH.read_text(encoding="utf-8"))
    windows = {
        wid: {
            "start": flows["windows"][wid]["start"],
            "end": flows["windows"][wid]["end"],
            "role": flows["windows"][wid]["role"],
        }
        for wid in WINDOW_IDS
    }
    # holdings reference month = month before window start (as in the RDTC ledgers)
    for wid in windows:
        windows[wid]["holdings_reference_month"] = prev_month(windows[wid]["start"])
        ledg_ref = flows["ledgers"][wid]["china_alone"]["holdings_reference_month"]
        assert windows[wid]["holdings_reference_month"] == ledg_ref, (wid, ledg_ref)

    df = pd.read_parquet(PANEL_PATH)

    # Per-variant series: dict[(class)] -> DataFrame indexed by month with pos/active/valchg.
    def variant_frame(countries, cls):
        frames = []
        for c in countries:
            sub = df[(df.country == c) & (df.asset_class == cls)].set_index("month")[
                ["pos_musd", "active_musd", "valchg_musd"]
            ]
            frames.append(sub)
        out = frames[0].copy()
        for f in frames[1:]:
            out = out.add(f, fill_value=None)  # NaN + x = NaN (skipna not applied)
        return out.sort_index()

    # Verify the publisher property that V_stated begins at 2023-02 (per country).
    vstated_first = {}
    for c in df.country.unique():
        nn = df[(df.country == c) & df.valchg_musd.notna()]
        vstated_first[c] = str(nn.month.min())
    vstated_starts_2023_02 = all(v == VSTATED_FIRST_EXPECTED for v in vstated_first.values())

    all_classes = CLASSES + [TOTAL]
    frames = {
        (vn, cls): variant_frame(countries, cls)
        for vn, countries in VARIANTS.items()
        for cls in all_classes
    }

    def window_table(vn, wid):
        w = windows[wid]
        months = month_range(w["start"], w["end"])
        ref = w["holdings_reference_month"]
        table = {}
        for cls in all_classes:
            fr = frames[(vn, cls)]
            row = {}
            pos_ref = fr["pos_musd"].get(ref)
            pos_end = fr["pos_musd"].get(w["end"])
            dh_ok = pos_ref is not None and pos_end is not None and pd.notna(pos_ref) and pd.notna(pos_end)
            act = fr["active_musd"].reindex(months)
            val = fr["valchg_musd"].reindex(months)
            n_act_missing = int(act.isna().sum())
            n_val = int(val.notna().sum())
            n_val_missing = int(val.isna().sum())
            val_missing_months = [m for m in months if pd.isna(val.get(m))]
            row["active_cum_busd"] = busd(float(act.sum(skipna=True)))
            row["active_months"] = f"{len(months) - n_act_missing}/{len(months)}"
            row["V_stated_cum_busd"] = busd(float(val.sum(skipna=True))) if n_val > 0 else None
            row["V_stated_months_covered"] = f"{n_val}/{len(months)}"
            if n_val_missing:
                row["V_stated_shortfall"] = (
                    f"{n_val_missing} months in window have NO published by-country valuation change "
                    f"({val_missing_months[0]}..{val_missing_months[-1]}; publisher publishes the column from "
                    f"{VSTATED_FIRST_EXPECTED} only). V_stated cumulated on the available span; NOT interpolated."
                )
            if dh_ok:
                dh = float(pos_end - pos_ref)
                row["delta_holdings_busd"] = busd(dh)
                dh_minus_active = dh - float(act.sum(skipna=True))
                row["dH_minus_active_busd"] = busd(dh_minus_active)
                g = dh - float(val.sum(skipna=True)) - float(act.sum(skipna=True))
                row["G_busd"] = busd(g)
                row["G_sign"] = "positive" if g > 0 else ("negative" if g < 0 else "zero")
                if n_val_missing:
                    row["G_label"] = (
                        "CONFLATED: G over this window mixes the true reconciliation gap with UNPUBLISHED "
                        "valuation change for the V_stated-missing months (pre-2023-02); it is NOT a clean gap."
                    )
                else:
                    row["G_label"] = "clean: every window month carries the published SLT valuation-change column"
            else:
                row["delta_holdings_busd"] = (
                    "NOT AVAILABLE -- by-class SLT positions begin 2020-01; reference month "
                    f"{ref} precedes coverage"
                )
                row["dH_minus_active_busd"] = None
                row["G_busd"] = None
                row["G_sign"] = "NOT AVAILABLE"
                row["G_label"] = "NOT AVAILABLE (delta holdings unavailable); components reported, G not computed"
            table[cls] = row
        # class-sum cross-check on G (total_lt column vs sum of the four classes)
        gs = [table[c]["G_busd"] for c in CLASSES]
        if all(isinstance(g, float) for g in gs) and isinstance(table[TOTAL]["G_busd"], float):
            table["_G_sum_of_classes_busd"] = round(sum(gs), 3)
            table["_G_total_minus_sum_busd"] = round(table[TOTAL]["G_busd"] - sum(gs), 3)
        return table

    g_tables = {wid: {vn: window_table(vn, wid) for vn in VARIANTS} for wid in WINDOW_IDS}

    # ------------------------------------------------------------------
    # Mechanical threshold (pre-registered): China-alone, verdict axis.
    # ------------------------------------------------------------------
    va = "recent_3y_verdict_axis"
    g_total_cn = g_tables[va]["china_alone"][TOTAL]["G_busd"]
    active_total_cn = g_tables[va]["china_alone"][TOTAL]["active_cum_busd"]
    threshold_busd = round(THRESHOLD_FRAC * abs(active_total_cn), 3)
    ratio_cn = round(abs(g_total_cn) / abs(active_total_cn), 4)
    flag = "446.5-UNRELIABLE" if abs(g_total_cn) > threshold_busd else "RELIABLE-WITHIN-GAP"

    g_total_cbl = g_tables[va]["china_belgium_luxembourg"][TOTAL]["G_busd"]
    active_total_cbl = g_tables[va]["china_belgium_luxembourg"][TOTAL]["active_cum_busd"]
    ratio_cbl = round(abs(g_total_cbl) / abs(active_total_cbl), 4)

    mechanical_flag = {
        "rule": "pre-registered (RDTD_prediction.md Part 1): flag 446.5-UNRELIABLE iff |G_total| > 0.25 x |active_total|, China-alone variant, verdict axis",
        "rule_clause_found_in_contract": threshold_clause_ok,
        "window": va,
        "variant_headline": "china_alone",
        "G_total_busd": g_total_cn,
        "abs_G_total_busd": round(abs(g_total_cn), 3),
        "active_total_busd": active_total_cn,
        "abs_active_total_busd": round(abs(active_total_cn), 3),
        "threshold_busd": threshold_busd,
        "ratio_absG_over_absActive": ratio_cn,
        "flag": flag,
        "context_variant_cn_be_lu": {
            "G_total_busd": g_total_cbl,
            "active_total_busd": active_total_cbl,
            "threshold_busd_own_active": round(THRESHOLD_FRAC * abs(active_total_cbl), 3),
            "ratio_absG_over_absActive": ratio_cbl,
            "would_trip_own_threshold": bool(abs(g_total_cbl) > THRESHOLD_FRAC * abs(active_total_cbl)),
            "note": "CONTEXT ONLY -- the pre-registered headline flag is the China-alone variant.",
        },
    }

    # ------------------------------------------------------------------
    # Reconciliation against the committed RDTC ledgers (verdict axis).
    # dH - active must equal the RDTC valuation_residual (V_us per class);
    # G must equal the RDTC 'other_changes' where RDTC published it.
    # ------------------------------------------------------------------
    recon = {"window": va, "per_variant": {}, "max_abs_diff_busd": 0.0}
    maxdiff = 0.0
    for vn in VARIANTS:
        ledg = flows["ledgers"][va][vn]
        rows = {}
        # per class
        for cls in CLASSES:
            lc = ledg["per_class"][cls]
            mine = g_tables[va][vn][cls]
            diffs = {
                "active_cum_busd": round(mine["active_cum_busd"] - lc["active_cum_busd"], 3),
                "delta_holdings_busd": round(mine["delta_holdings_busd"] - lc["delta_holdings_busd"], 3),
                "dH_minus_active_vs_valuation_residual_busd": round(
                    mine["dH_minus_active_busd"] - lc["valuation_residual_busd"], 3
                ),
                "V_stated_vs_published_valchg_busd": round(
                    mine["V_stated_cum_busd"] - lc["published_valchg_cum_busd_slt_part"], 3
                ),
            }
            oc = parse_other_changes(lc.get("residual_decomposition"))
            if oc is not None:
                diffs["G_vs_rdtc_other_changes_busd"] = round(mine["G_busd"] - oc, 3)
            rows[cls] = diffs
            maxdiff = max(maxdiff, *(abs(v) for v in diffs.values()))
        # total: RDTC carries X + A_total, and residual_left_us = -(X + A_total)
        x = ledg["X_ust_active_busd"]
        a_tot = ledg["A_nonust_active_busd"]["total"]
        mine_tot = g_tables[va][vn][TOTAL]
        tot_diffs = {
            "active_total_vs_ledger_X_plus_A_busd": round(mine_tot["active_cum_busd"] - (x + a_tot), 3),
            "active_total_vs_minus_residual_left_us_busd": round(
                mine_tot["active_cum_busd"] - (-ledg["residual_left_us_busd"]), 3
            ),
            "dH_minus_active_vs_sum_of_class_valuation_residuals_busd": round(
                mine_tot["dH_minus_active_busd"]
                - sum(ledg["per_class"][c]["valuation_residual_busd"] for c in CLASSES),
                3,
            ),
        }
        rows[TOTAL] = tot_diffs
        maxdiff = max(maxdiff, *(abs(v) for v in tot_diffs.values()))
        rows["_reading"] = (
            "dH - active (mine) is compared to RDTC's committed valuation_residual (the V_us leg of the "
            "identity); V_stated to RDTC's published_valchg; G to RDTC's other_changes. Diffs are "
            "rounding-level or the reconciliation fails."
        )
        recon["per_variant"][vn] = rows
    recon["max_abs_diff_busd"] = round(maxdiff, 3)
    recon["tolerance_busd"] = 0.005
    recon["reconciled"] = bool(maxdiff <= 0.005)

    # ------------------------------------------------------------------
    # Monthly gap rows: gap_m = dPos_m - active_m - valchg_m, computable only
    # on months where the stated-valuation column exists (2023-02..).
    # ------------------------------------------------------------------
    def monthly_gaps(fr):
        pos = fr["pos_musd"]
        months = [
            m
            for m in fr.index
            if pd.notna(fr.at[m, "valchg_musd"])
            and pd.notna(fr.at[m, "active_musd"])
            and pd.notna(pos.get(m))
            and pd.notna(pos.get(prev_month(m)))
        ]
        return pd.Series(
            {
                m: float(pos[m] - pos[prev_month(m)] - fr.at[m, "active_musd"] - fr.at[m, "valchg_musd"])
                for m in months
            }
        ).sort_index()

    def gap_block(fr):
        g = monthly_gaps(fr)
        if len(g) == 0:
            return {"n_months": 0}
        imax = g.abs().idxmax()
        return {
            "n_months": int(len(g)),
            "span": f"{g.index.min()}..{g.index.max()}",
            "mean_busd": busd(float(g.mean())),
            "mean_abs_busd": busd(float(g.abs().mean())),
            "median_abs_busd": busd(float(g.abs().median())),
            "max_abs_busd": busd(float(g.abs().max())),
            "sum_busd": busd(float(g.sum())),
            "n_abs_gt_10busd": int((g.abs() > 10000).sum()),
            "largest_abs_row": {"month": str(imax), "gap_busd": busd(float(g[imax]))},
        }

    monthly = {"definition": "gap_m = dHoldings_m - active_m - V_stated_m (musd; reported busd); computable only on the stated-valuation span", "per_variant": {}, "per_country_total_lt": {}}
    for vn in VARIANTS:
        blocks = {cls: gap_block(frames[(vn, cls)]) for cls in all_classes}
        # single largest |gap| row across all classes for the variant
        best = None
        for cls in all_classes:
            b = blocks[cls]
            if b.get("n_months", 0) and (
                best is None or abs(b["largest_abs_row"]["gap_busd"]) > abs(best["gap_busd"])
            ):
                best = {"asset_class": cls, **b["largest_abs_row"]}
        monthly["per_variant"][vn] = {"largest_abs_row_any_class": best, "by_class": blocks}
    for c in df.country.unique():
        fr = df[(df.country == c) & (df.asset_class == TOTAL)].set_index("month")[
            ["pos_musd", "active_musd", "valchg_musd"]
        ].sort_index()
        monthly["per_country_total_lt"][str(c)] = gap_block(fr)

    lux = monthly["per_country_total_lt"].get("Luxembourg", {})
    lux_row = lux.get("largest_abs_row", {})
    rdtc_max_gap_busd = round(flows["self_check"]["slt_identity_max_abs_gap_musd_dPos_minus_net_minus_valchg"] / 1000.0, 3)
    lux_reproduced = bool(
        lux_row
        and lux_row.get("month") == "2023-12"
        and abs(abs(lux_row.get("gap_busd", 0.0)) - rdtc_max_gap_busd) <= 0.005
    )

    biggest_country_gap = max(
        (abs(b["largest_abs_row"]["gap_busd"]), c)
        for c, b in monthly["per_country_total_lt"].items()
        if b.get("n_months", 0)
    )
    character = (
        "episodic-with-systematic-floor: the single largest monthly |gap| "
        f"({biggest_country_gap[0]:.3f} $bn, {biggest_country_gap[1]} total_lt) dwarfs the median monthly |gap|; "
        "large gaps concentrate in the custody centers (Belgium/Luxembourg), consistent with the publisher's "
        "documented custody/ICSD attribution and survey-benchmark reattribution rather than with a smooth "
        "monthly reporting error. See monthly_gap_distribution for the numbers; this sentence interprets "
        "nothing beyond them."
    )

    # ------------------------------------------------------------------
    # Mechanism quotes -- verify each against its retained file.
    # ------------------------------------------------------------------
    quotes_out = []
    all_found = True
    for q in MECH_QUOTES:
        found = quote_on_disk(ROOT / q["file"], q["quote"])
        all_found &= found
        quotes_out.append({**q, "verbatim_found_in_file": found})
    mechanism = {
        "status": "ON-DISK (verbatim, composite of retained publisher files)" if all_found else "PARTIAL -- at least one quote failed verbatim match; treat as NOT-ON-DISK",
        "statement": (
            "Transactions (the 446.5's substance) are attributed to the country of the counterparty "
            "transacting with the U.S. -- for intermediated trades that is the intermediary's country "
            "(the classic UK/financial-center effect) -- while holdings are attributed to the (custody-"
            "chain-visible) residence of the holder. The publisher states each leg in its own words below; "
            "the composite, not memory, is the ground for the mechanism."
        ),
        "quotes": quotes_out,
        "tic_faq_note": tic_faq_note(),
    }

    result = {
        "artifact": "RDTD_fragility (RDT-D Part 1: fragility of the 446.5 $bn active-outflow figure)",
        "establishment": (
            "NOT ESTABLISHED -- output of RDTD_fragility_recompute.py; every number below is an OUTPUT "
            "pending its verifier scenario (orchestrator re-run of build/reserve/RDTD_fragility_recompute.py "
            "reproducing this file byte-for-byte, and the RDT-D gate)."
        ),
        "contract": "build/reserve/RDTD_prediction.md (pre-registered before this build)",
        "no_date_no_probability": "no breaking-point date and no probability appear in this artifact",
        "inputs_sha256": inputs_sha,
        "units": "all *_busd fields are billions of USD, rounded to 3 decimals; panel native unit is millions",
        "class_alias": CLASS_ALIAS,
        "windows": windows,
        "identity": "G = dH - V_stated - active, per class, per custody variant (pre-registered Part-1 rule)",
        "v_stated_property": {
            "first_published_month_per_country": vstated_first,
            "starts_2023_02_everywhere": vstated_starts_2023_02,
            "reading": (
                "The SLT stated valuation-change column exists from 2023-02 only (publisher property, verified "
                "from the committed panel). The verdict axis (2023-05..2026-04) lies entirely on it; the "
                "freeze-era and full context windows do NOT -- their G conflates valuation and gap and is "
                "labelled so, per the pre-registration."
            ),
        },
        "G_tables": g_tables,
        "mechanical_flag": mechanical_flag,
        "rdtc_reconciliation": recon,
        "monthly_gap_distribution": monthly,
        "monthly_gap_character": character,
        "rdtc_largest_gap_reproduction": {
            "rdtc_committed_max_abs_gap_busd": rdtc_max_gap_busd,
            "rdtc_committed_location": "Luxembourg total_lt 2023-12 (RDTC_class_flows.json self_check)",
            "my_luxembourg_total_lt_largest_row": lux_row,
            "reproduced": lux_reproduced,
        },
        "attribution_mechanism": mechanism,
        "self_check": {
            "threshold_clause_found_in_prediction": threshold_clause_ok,
            "v_stated_starts_2023_02": vstated_starts_2023_02,
            "verdict_axis_v_stated_complete_36_of_36": all(
                g_tables[va][vn][cls]["V_stated_months_covered"] == "36/36"
                for vn in VARIANTS
                for cls in all_classes
            ),
            "rdtc_reconciled_within_tolerance": recon["reconciled"],
            "rdtc_max_abs_recon_diff_busd": recon["max_abs_diff_busd"],
            "luxembourg_2023_12_gap_reproduced": lux_reproduced,
            "mechanism_quotes_all_verbatim_on_disk": all_found,
            "class_additivity_max_abs_diff_busd_verdict_axis": max(
                abs(g_tables[va][vn].get("_G_total_minus_sum_busd", 0.0)) for vn in VARIANTS
            ),
            "no_date_no_probability": True,
        },
    }
    return result


def main():
    r1 = compute()
    r2 = compute()
    s1 = json.dumps(r1, indent=1, ensure_ascii=False, sort_keys=False)
    s2 = json.dumps(r2, indent=1, ensure_ascii=False, sort_keys=False)
    r1["self_check"]["double_build_identical"] = bool(s1 == s2)
    out = json.dumps(r1, indent=1, ensure_ascii=False, sort_keys=False) + "\n"
    OUT_PATH.write_text(out, encoding="utf-8")
    print(f"wrote {OUT_PATH}")
    print(f"double_build_identical: {r1['self_check']['double_build_identical']}")
    print(f"flag: {r1['mechanical_flag']['flag']}  ratio: {r1['mechanical_flag']['ratio_absG_over_absActive']}")
    print(f"reconciled: {r1['rdtc_reconciliation']['reconciled']} (max diff {r1['rdtc_reconciliation']['max_abs_diff_busd']} $bn)")
    print(f"quotes on disk: {r1['self_check']['mechanism_quotes_all_verbatim_on_disk']}")
    print(f"lux 2023-12 reproduced: {r1['self_check']['luxembourg_2023_12_gap_reproduced']}")


if __name__ == "__main__":
    main()
