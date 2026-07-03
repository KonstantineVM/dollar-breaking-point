#!/usr/bin/env python3
"""
FWTW-RECONSTRUCTION Part 2 -- recompute script (NO NETWORK).

Regenerates TWO US-holder x issuer-nationality bilateral INTERIORS from three
on-disk inputs alone:
  1) build/data/nport/us_china_nationality_panel.parquet   (ROW marginal source)
  2) build/data/bis_ids/ids_cn_nationality.json            (COLUMN fraction source)
  3) build/model/matrix_assembled.json (+ ras_inputs.json) (DP2 RESIDENCY seed)

It writes:
  build/audit/fwtw_recon_interiors.parquet                  (both methods, long form)
  build/audit/fwtw_recon_interiors_provenance.json          (provenance + caveats)
  build/results/fwtw_recon_interiors_verify.json            (verifier: shape, checksums,
                                                             marginal-satisfaction)

It does NOT compute F3 statistics (that is Part 3). It does NOT read or compare to the
pre-registered prediction. It does NOT re-tag the operator or touch the ledger.

------------------------------------------------------------------------------------
DESIGN (documented, not assumed)
------------------------------------------------------------------------------------
HOLDER KEY: cik|series_id. The panel has 7461 distinct cik|series_id vs 7460 distinct
  series_id, i.e. one series_id is shared across two ciks; cik|series_id is the unique
  fund-share-class holder identity and is chosen as the holder axis. Documented.

ROW MARGINAL (holder side): for each fiscal_quarter, each holder's TOTAL USD-equivalent
  holdings of HAVEN-RESIDENT issuers (is_haven_resident=True => residence in
  {CYM,HKG,VGB}). USD-equivalent uses the SAME conversion as the prior freemap pass:
  USD x1; HKD /7.80 (HKMA peg midpoint); minor currencies at fixed representative rates;
  unknown codes 1:1. Non-positive (<=0) and null currency_value rows are DROPPED (a
  marginal must be a non-negative mass vector; short/negative positions cannot seed a
  transport interior). Holders with zero positive haven mass in a quarter are dropped
  for that quarter. This is the EQUITY-HEAVY panel haven pool (asset_cat is ~70% EC).

COLUMN MARGINAL (issuer-nationality {China, non-China}):
  The BIS IDS marginal is DEBT SECURITIES ONLY. We do NOT have a Chinese-nationality
  EQUITY marginal (equity nationality gap; see caveat). To make the BIS debt marginal
  commensurate with the panel haven pool we derive a per-quarter CHINA COLUMN FRACTION
  and apply it to the (equity-heavy) panel haven row total:

    china_col_fraction(q) = (nationality_basis(q) - residence_basis(q)) / nationality_basis(q)

  Interpretation: BIS nationality-basis China debt reattributes haven/offshore-resident
  issuance (Cayman/BVI/HK SPVs etc.) back to the Chinese parent; residence-basis counts
  only debt issued by China-RESIDENT entities. The difference (nationality - residence)
  is exactly the China-nationality debt that is OFFSHORE/HAVEN-resident -- i.e. the part
  of Chinese nationality that hides inside haven residence. As a fraction of the total
  China-nationality pool it is the share of Chinese exposure that a residence-basis view
  MISSES and a nationality-basis view RECOVERS from the haven pool. That is the cleanest
  BIS-internal analogue of "of the haven-resident pool, what share is China by
  nationality," so it is used as the China column fraction for the haven panel.

  china_col_total(q)     = china_col_fraction(q) * row_total(q)
  nonchina_col_total(q)  = row_total(q) - china_col_total(q)

  CAVEAT (equity gap, STATED): this fraction is a DEBT-basis nationality split applied to
  an EQUITY-HEAVY panel haven pool. The haven equity VIEs/ADRs (Alibaba/Tencent/PDD/...)
  are NOT in BIS IDS, so their Chinese nationality is NOT measured by this fraction. The
  fraction is NOT assumed to equal the (unknown) equity China-nationality share and is
  NOT silently equated to it; it is a flagged basis bridge. Equity China nationality
  remains a HOLE.

METHOD 1 -- MAX-ENTROPY (no prior): the entropy-maximising joint subject only to the
  row marginal and the China-nationality column marginal is the INDEPENDENCE table
    p_ij = row_i * col_j / total
  computed EXPLICITLY here (col in {China,non-China}). Every holder receives the same
  China fraction = the aggregate split; that is an OUTPUT of the computation, not an
  assumption, and its F3 behaviour is NOT asserted here.

METHOD 2 -- RAS / Sinkhorn with INFORMATIVE prior (DP2 residency seed): the DP2 CPIS
  residency matrix is mapped onto the {China, non-China} column space to give each
  haven RESIDENCY destination a residency->China-nationality PROPENSITY, then each US
  holder's OWN haven-residency composition (from the panel) carries that propensity:

    DP2 residency->China propensity per haven hub d in {CYM,HKG,VGB}:
        pi_d = (DP2 reporter-row d -> CHN counterpart) / (DP2 reporter-row d total)
      e.g. CYM pi ~ 283663/6199241 ~ 0.0458 ; HKG pi ~ 520855/2166609 ~ 0.2404.
      VGB has no DP2 reporter row (BVI files no CPIS); we assign VGB the CYM propensity
      (both pure offshore-SPV incorporation hubs), documented as a stated proxy.
    For each holder i, panel gives its USD-equiv mass by haven residency hub:
        m_{i,CYM}, m_{i,HKG}, m_{i,VGB}  (sum = row_mass_i)
    Seed China weight for holder i:
        seed_china_i = m_{i,CYM}*pi_CYM + m_{i,HKG}*pi_HKG + m_{i,VGB}*pi_VGB
        seed_nonchina_i = row_mass_i - seed_china_i
    This seed is HOLDER-HETEROGENEOUS: a HKG-heavy fund gets a higher seed China share
    than a CYM-heavy fund, because DP2 residency structure says HKG residency carries
    more China-nationality counterpart than CYM residency. RAS then rescales this
    holder x {China,non-China} seed to satisfy the SAME two marginals as Method 1. The
    RAS preserves the seed's holder-specific China/non-China cross-structure while
    forcing the aggregate China column to the BIS-derived total; Method 2 therefore
    DIFFERS from Method 1 holder-by-holder (Method 1 gives every holder the identical
    aggregate fraction; Method 2 tilts toward each holder's residency mix).

  CAVEAT (RAS residency-proxy, STATED): this interior's credibility equals the
  credibility of the assumption that residency-interaction structure (which hub a fund
  holds through) proxies nationality-interaction structure (which fund actually holds
  Chinese-by-nationality issuers) -- the assumption this project distrusts. Stated as a
  caveat, not a disqualification.
"""

import json
import hashlib
import os

import numpy as np
import pandas as pd

ROOT = "/home/user/dollar-breaking-point"
PANEL = f"{ROOT}/build/data/nport/us_china_nationality_panel.parquet"
BIS = f"{ROOT}/build/data/bis_ids/ids_cn_nationality.json"
DP2 = f"{ROOT}/build/model/matrix_assembled.json"

OUT_PARQUET = f"{ROOT}/build/audit/fwtw_recon_interiors.parquet"
OUT_PROV = f"{ROOT}/build/audit/fwtw_recon_interiors_provenance.json"
OUT_VERIFY = f"{ROOT}/build/results/fwtw_recon_interiors_verify.json"

HAVENS = {"CYM", "HKG", "VGB"}

# --- FX to USD-equivalent: IDENTICAL to build/audit/freemap_coverage_recompute.py ---
HKD_PER_USD = 7.80
MINOR_RATES = {
    "TWD": 30.0, "EUR": 0.90, "CAD": 1.30, "GBP": 0.78, "CNY": 7.0, "BRL": 5.0,
    "AUD": 1.45, "JPY": 130.0, "ILS": 3.5, "NOK": 9.5, "ZAR": 16.0, "SGD": 1.35,
    "KRW": 1200.0, "KYD": 0.82, "RUB": 75.0, "IDR": 14500.0, "TRY": 15.0,
    "MXN": 19.0, "AED": 3.67, "INR": 80.0,
}


def to_usd_vec(values, codes):
    out = np.array(values, dtype="float64")
    codes = np.asarray(codes, dtype=object)
    div = np.ones(len(out), dtype="float64")
    for i, c in enumerate(codes):
        if c == "USD":
            div[i] = 1.0
        elif c == "HKD":
            div[i] = HKD_PER_USD
        elif c in MINOR_RATES:
            div[i] = MINOR_RATES[c]
        else:
            div[i] = 1.0
    return out / div


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------------------
# 1) ROW marginals (holder x quarter): USD-equiv positive haven mass
# ----------------------------------------------------------------------------------
def build_row_marginals():
    df = pd.read_parquet(
        PANEL,
        columns=[
            "cik", "series_id", "fiscal_quarter",
            "is_haven_resident", "currency_value", "currency_code",
        ],
    )
    df = df[df["is_haven_resident"].astype(bool)].copy()
    df = df[df["currency_value"].notna()]
    df["usd"] = to_usd_vec(df["currency_value"].to_numpy(), df["currency_code"].to_numpy())
    df = df[df["usd"] > 0.0]
    df["holder"] = df["cik"].astype(str) + "|" + df["series_id"].astype(str)
    g = df.groupby(["fiscal_quarter", "holder"], as_index=False)["usd"].sum()
    g = g.rename(columns={"usd": "row_mass_usd"})
    # per-hub composition (for the holder-heterogeneous Method-2 seed)
    need = ["cik", "series_id", "fiscal_quarter", "investment_country_iso3",
            "is_haven_resident", "currency_value", "currency_code"]
    df2 = pd.read_parquet(PANEL, columns=need)
    df2 = df2[df2["is_haven_resident"].astype(bool)].copy()
    df2 = df2[df2["currency_value"].notna()]
    df2["usd"] = to_usd_vec(df2["currency_value"].to_numpy(), df2["currency_code"].to_numpy())
    df2 = df2[df2["usd"] > 0.0]
    df2["holder"] = df2["cik"].astype(str) + "|" + df2["series_id"].astype(str)
    hub = (df2.groupby(["fiscal_quarter", "holder", "investment_country_iso3"], as_index=False)["usd"]
              .sum()
              .pivot_table(index=["fiscal_quarter", "holder"],
                           columns="investment_country_iso3", values="usd", fill_value=0.0)
              .reset_index())
    for h in HAVENS:
        if h not in hub.columns:
            hub[h] = 0.0
    return g, hub


# ----------------------------------------------------------------------------------
# 2) COLUMN China fraction (per quarter) from BIS IDS
# ----------------------------------------------------------------------------------
def build_china_fractions():
    bis = json.load(open(BIS))
    pq = bis["panel_quarters"]
    fr = {}
    for qlabel, rec in pq.items():
        nat = float(rec["nationality_basis_usd_millions"])
        res = float(rec["residence_basis_usd_millions"])
        fr[qlabel] = {
            "nationality_basis_usd_millions": nat,
            "residence_basis_usd_millions": res,
            "china_col_fraction": (nat - res) / nat,
        }
    return fr


# Map panel fiscal_quarter (e.g. '2019q3') -> BIS panel_quarters key (e.g. '2019-Q3')
def fq_to_bis(fq):
    y, q = fq[:4], fq[4:]
    return f"{y}-{q.upper()}"


# ----------------------------------------------------------------------------------
# 3) DP2 residency seed -> {China, non-China} aggregate split
# ----------------------------------------------------------------------------------
def build_seed_propensities():
    """DP2 residency->China-nationality propensity pi_d per haven hub d in {CYM,HKG,VGB}.
    pi_d = (DP2 reporter-row d -> CHN counterpart) / (DP2 reporter-row d total)."""
    dp2 = json.load(open(DP2))
    rows = dp2["layers"]["portfolio_investment_bilateral_CPIS"][
        "balanced_matrix_after_consistency_pass"]["rows"]
    pi = {}
    detail = {}
    for hub in ["CYM", "HKG"]:
        r = rows[hub]
        tot = sum(float(v) for v in r.values())
        chn = float(r.get("CHN", 0.0))
        pi[hub] = chn / tot if tot > 0 else 0.0
        detail[hub] = {"row_total_usd_mn": tot, "to_CHN_usd_mn": chn, "pi": pi[hub]}
    # VGB has no DP2 reporter row (BVI files no CPIS); proxy with CYM propensity.
    pi["VGB"] = pi["CYM"]
    detail["VGB"] = {"row_total_usd_mn": 0.0, "to_CHN_usd_mn": None,
                     "pi": pi["VGB"], "note": "no DP2 reporter row; assigned CYM propensity (proxy)"}
    return pi, detail


# ----------------------------------------------------------------------------------
# RAS / Sinkhorn for a 2-column table (holder x {China, non-China})
# ----------------------------------------------------------------------------------
def ras_two_col(seed, row_targets, col_targets, n_passes=200, tol=1e-9):
    """seed: (n,2) >0; row_targets: (n,); col_targets: (2,). Returns matrix + resid log."""
    M = seed.astype("float64").copy()
    log = []
    for p in range(1, n_passes + 1):
        rs = M.sum(axis=1)
        rs[rs == 0] = 1.0
        M = M * (row_targets / rs)[:, None]
        cs = M.sum(axis=0)
        cs[cs == 0] = 1.0
        M = M * (col_targets / cs)[None, :]
        row_resid = M.sum(axis=1) - row_targets
        col_resid = M.sum(axis=0) - col_targets
        rl2 = float(np.sqrt(np.sum(row_resid ** 2)))
        cl2 = float(np.sqrt(np.sum(col_resid ** 2)))
        if p <= 10 or p % 25 == 0:
            log.append({"pass": p, "row_resid_L2": rl2, "col_resid_L2": cl2,
                        "row_resid_Linf": float(np.max(np.abs(row_resid))),
                        "col_resid_Linf": float(np.max(np.abs(col_resid)))})
        if rl2 < tol and cl2 < tol:
            log.append({"pass": p, "row_resid_L2": rl2, "col_resid_L2": cl2,
                        "row_resid_Linf": float(np.max(np.abs(row_resid))),
                        "col_resid_Linf": float(np.max(np.abs(col_resid))),
                        "converged": True})
            break
    return M, log


def main():
    rows, hub = build_row_marginals()
    fr = build_china_fractions()
    pi, pi_detail = build_seed_propensities()

    quarters = sorted(rows["fiscal_quarter"].unique())
    records = []
    per_quarter_meta = {}
    ras_logs = {}

    for q in quarters:
        bkey = fq_to_bis(q)
        if bkey not in fr:
            # No BIS commensurate marginal for this quarter -> cannot build column. Flag.
            per_quarter_meta[q] = {"bis_key": bkey, "status": "NO_BIS_MARGINAL_skipped"}
            continue
        cf = fr[bkey]["china_col_fraction"]
        sub = rows[rows["fiscal_quarter"] == q].sort_values("holder").reset_index(drop=True)
        r = sub["row_mass_usd"].to_numpy(dtype="float64")
        total = float(r.sum())
        holders = sub["holder"].tolist()
        col_china = cf * total
        col_nonchina = total - col_china
        col_targets = np.array([col_china, col_nonchina], dtype="float64")

        # METHOD 1 -- independence table p_ij = row_i * col_j / total (EXPLICIT)
        m1 = np.outer(r, col_targets) / total  # (n,2): [China, non-China]

        # METHOD 2 -- holder-heterogeneous DP2-residency seed, then RAS to same marginals.
        hsub = (hub[hub["fiscal_quarter"] == q]
                .set_index("holder").reindex(holders).fillna(0.0))
        m_cym = hsub["CYM"].to_numpy(dtype="float64")
        m_hkg = hsub["HKG"].to_numpy(dtype="float64")
        m_vgb = hsub["VGB"].to_numpy(dtype="float64")
        seed_china = m_cym * pi["CYM"] + m_hkg * pi["HKG"] + m_vgb * pi["VGB"]
        seed_china = np.clip(seed_china, 0.0, r)  # cannot exceed the holder's row mass
        seed = np.empty((len(r), 2), dtype="float64")
        seed[:, 0] = seed_china
        seed[:, 1] = r - seed_china
        seed = np.where(seed <= 0, 1e-12, seed)  # guard zeros for RAS
        m2, log = ras_two_col(seed, r, col_targets)
        ras_logs[q] = log

        per_quarter_meta[q] = {
            "bis_key": bkey,
            "n_holders": len(holders),
            "row_total_usd": total,
            "china_col_fraction_bis": cf,
            "china_col_total_usd": col_china,
            "nonchina_col_total_usd": col_nonchina,
            "nationality_basis_usd_millions": fr[bkey]["nationality_basis_usd_millions"],
            "residence_basis_usd_millions": fr[bkey]["residence_basis_usd_millions"],
            "seed_china_share_aggregate": float(seed_china.sum() / total),
            "status": "BUILT",
        }

        for i, h in enumerate(holders):
            records.append({
                "fiscal_quarter": q, "holder": h, "nationality": "China",
                "method1_maxent_usd": float(m1[i, 0]),
                "method2_ras_usd": float(m2[i, 0]),
                "row_mass_usd": float(r[i]),
            })
            records.append({
                "fiscal_quarter": q, "holder": h, "nationality": "non-China",
                "method1_maxent_usd": float(m1[i, 1]),
                "method2_ras_usd": float(m2[i, 1]),
                "row_mass_usd": float(r[i]),
            })

    out = pd.DataFrame.from_records(records)
    out = out[["fiscal_quarter", "holder", "nationality",
               "method1_maxent_usd", "method2_ras_usd", "row_mass_usd"]]
    out.to_parquet(OUT_PARQUET, index=False)

    # ---- marginal-satisfaction checks (both methods, both axes) ----
    checks = {}
    for q, meta in per_quarter_meta.items():
        if meta.get("status") != "BUILT":
            continue
        sub = out[out["fiscal_quarter"] == q]
        # row sums (sum over the 2 nationality cells per holder) vs row_mass
        for method, col in [("method1", "method1_maxent_usd"), ("method2", "method2_ras_usd")]:
            piv = sub.pivot_table(index="holder", columns="nationality", values=col, aggfunc="sum")
            rowsum = piv.sum(axis=1).to_numpy()
            rmass = sub.groupby("holder")["row_mass_usd"].first().reindex(piv.index).to_numpy()
            row_resid = np.max(np.abs(rowsum - rmass))
            china_sum = piv["China"].sum()
            nonchina_sum = piv["non-China"].sum()
            col_resid_china = abs(china_sum - meta["china_col_total_usd"])
            col_resid_nonchina = abs(nonchina_sum - meta["nonchina_col_total_usd"])
            checks.setdefault(q, {})[method] = {
                "row_marginal_max_abs_resid_usd": float(row_resid),
                "row_marginal_max_rel_resid": float(row_resid / max(rmass.max(), 1.0)),
                "col_china_abs_resid_usd": float(col_resid_china),
                "col_nonchina_abs_resid_usd": float(col_resid_nonchina),
                "col_china_rel_resid": float(col_resid_china / max(meta["china_col_total_usd"], 1.0)),
            }

    # write provenance
    provenance = {
        "artifact": "fwtw_recon_interiors_provenance.json",
        "step": "FWTW-RECONSTRUCTION Part 2 (compute two interiors; NOT F3 stats; NOT prediction compare)",
        "generated_by": "build/audit/fwtw_recon_interiors_recompute.py",
        "no_network": True,
        "inputs": {
            "row_marginal_source": PANEL,
            "column_fraction_source": BIS,
            "dp2_residency_seed_source": DP2,
        },
        "holder_axis": {
            "key": "cik|series_id",
            "rationale": "7461 distinct cik|series_id vs 7460 distinct series_id (one series_id "
                         "shared across two ciks); cik|series_id is the unique fund-share-class "
                         "holder identity.",
        },
        "row_marginal_definition": {
            "scope": "per fiscal_quarter, each holder's total USD-equivalent holdings of "
                     "HAVEN-RESIDENT issuers (is_haven_resident=True => residence in {CYM,HKG,VGB}).",
            "fx_conversion": {
                "USD": "x1",
                "HKD": f"/{HKD_PER_USD} (HKMA Linked Exchange Rate System peg midpoint)",
                "minor_currencies": "fixed representative rates (units/USD); identical dict to "
                                    "build/audit/freemap_coverage_recompute.py",
                "unknown_codes": "treated 1:1 (negligible tail, e.g. 'N/A')",
            },
            "sign_filter": "non-positive (<=0) and null currency_value rows DROPPED; a marginal "
                           "must be a non-negative mass vector.",
            "equity_heavy_note": "panel haven pool is ~70% equity (asset_cat EC); this is the "
                                 "equity-heavy pool the debt-basis column fraction is applied to.",
        },
        "column_fraction_derivation": {
            "column_space": ["China", "non-China"],
            "formula": "china_col_fraction(q) = (nationality_basis(q) - residence_basis(q)) / nationality_basis(q)",
            "interpretation": "BIS-internal share of China-nationality DEBT that is offshore/haven-"
                              "resident (recovered by nationality reattribution, missed by residence). "
                              "Used as the China column fraction for the haven panel pool.",
            "china_col_total": "china_col_fraction(q) * panel_haven_row_total(q)",
            "per_quarter": {q: fr[fq_to_bis(q)] for q in quarters if fq_to_bis(q) in fr},
        },
        "dp2_seed_mapping": {
            "seed_construction": "holder-heterogeneous. Each haven RESIDENCY hub d in {CYM,HKG,VGB} "
                                 "gets a DP2 residency->China propensity pi_d = (DP2 reporter-row d -> "
                                 "CHN) / (DP2 reporter-row d total). Each US holder's panel mass by hub "
                                 "(m_CYM,m_HKG,m_VGB) carries that propensity: seed_china_i = "
                                 "sum_d m_{i,d}*pi_d. RAS rescales holder x {China,non-China} seed to "
                                 "the row + China-nationality column marginals.",
            "dp2_residency_to_china_propensity_per_hub": pi_detail,
            "vgb_proxy_note": "VGB has no DP2 reporter row (BVI files no CPIS); assigned CYM propensity.",
        },
        "methods": {
            "method1_maxent": "independence table p_ij = row_i * col_j / total; max-entropy, no prior; "
                              "every holder gets the aggregate China fraction (an OUTPUT, not assumed).",
            "method2_ras": "RAS/Sinkhorn from the DP2 residency seed split, rescaled to the SAME two "
                           "marginals as Method 1.",
        },
        "caveats": {
            "equity_gap": "The China column fraction is a DEBT-basis nationality split (BIS IDS = debt "
                          "securities only) applied to an EQUITY-HEAVY panel haven pool. Haven equity "
                          "VIEs/ADRs (Alibaba/Tencent/PDD/Baidu) are NOT in BIS IDS; their Chinese "
                          "nationality is NOT measured by this fraction. The debt fraction is NOT "
                          "assumed equal to the (unknown) equity China-nationality share and NOT "
                          "silently equated to it. Equity China nationality remains a HOLE.",
            "ras_residency_proxy": "Method 2's credibility equals the credibility of the assumption "
                                   "that residency-interaction structure proxies nationality-interaction "
                                   "structure -- the assumption this project distrusts. Stated as a "
                                   "caveat, not a disqualification.",
        },
        "per_quarter_meta": per_quarter_meta,
        "SOURCE": "Panel: SEC Form N-PORT (build_us_china_panel.py provenance). BIS: WS_DEBT_SEC2_PUB "
                  "nationality vs residence (ids_cn_nationality.json). DP2 seed: matrix_assembled.json "
                  "CPIS residency USA row.",
    }
    json.dump(provenance, open(OUT_PROV, "w"), indent=2)

    # verifier
    n_holders_total = out["holder"].nunique()
    verify = {
        "artifact": "fwtw_recon_interiors_verify.json",
        "recompute_script": "build/audit/fwtw_recon_interiors_recompute.py",
        "interiors_parquet": OUT_PARQUET,
        "parquet_sha256": sha256_file(OUT_PARQUET),
        "shape_rows": int(out.shape[0]),
        "shape_cols": int(out.shape[1]),
        "columns": list(out.columns),
        "n_quarters_built": int(sum(1 for m in per_quarter_meta.values() if m.get("status") == "BUILT")),
        "n_distinct_holders_over_panel": int(n_holders_total),
        "per_quarter_china_col_fraction": {
            q: per_quarter_meta[q]["china_col_fraction_bis"]
            for q in quarters if per_quarter_meta.get(q, {}).get("status") == "BUILT"
        },
        "per_quarter_n_holders": {
            q: per_quarter_meta[q]["n_holders"]
            for q in quarters if per_quarter_meta.get(q, {}).get("status") == "BUILT"
        },
        "marginal_satisfaction_checks": checks,
        "ras_residual_logs_tail": {q: ras_logs[q][-1] for q in ras_logs},
        "method1_is_independence_table": "p_ij = row_i * col_j / total, computed via numpy.outer; "
                                         "verified row+col marginals satisfied to tolerance below.",
        "method2_is_ras_of_dp2_residency_seed": "Sinkhorn from DP2 USA residency split, rescaled to "
                                                "the same two marginals; verified to tolerance.",
        "tolerance_rel": 1e-6,
    }
    # overall PASS/FAIL: all built quarters, both methods, row & col rel resid < 1e-6
    ok = True
    for q, md in checks.items():
        for method, c in md.items():
            if c["row_marginal_max_rel_resid"] > 1e-6:
                ok = False
            if c["col_china_rel_resid"] > 1e-6:
                ok = False
    verify["PASS"] = bool(ok)
    json.dump(verify, open(OUT_VERIFY, "w"), indent=2)

    print("PASS" if ok else "FAIL")
    print("parquet:", OUT_PARQUET, "shape", out.shape)
    print("distinct holders over panel:", n_holders_total)
    for q in quarters:
        m = per_quarter_meta.get(q, {})
        if m.get("status") == "BUILT":
            print(f"  {q} (BIS {m['bis_key']}): n_holders={m['n_holders']} "
                  f"china_col_fraction={m['china_col_fraction_bis']:.6f} "
                  f"row_total_usd={m['row_total_usd']:.3e}")
            print(f"      M2 seed china share (aggregate): {m['seed_china_share_aggregate']:.6f}")
        else:
            print(f"  {q}: {m.get('status')}")
    print("DP2 residency->China propensities per hub:",
          {k: round(v, 6) for k, v in pi.items()})


if __name__ == "__main__":
    main()
