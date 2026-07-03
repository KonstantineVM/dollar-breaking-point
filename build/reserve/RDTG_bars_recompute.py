#!/usr/bin/env python3
"""RDT-G Phase 0c -- MAGNITUDE BARS.

Deterministic recompute. Regenerates build/reserve/RDTG_bars.json byte-for-byte
from committed inputs only:

  - build/reserve/RDTG_denominators.json  (market outstandings, COFER 2021-Q4 raw
    shares, H.10 Dec-30-2021 FX set)
  - build/reserve/RDTD_result.json        (upper mass endpoint, field path recorded)
  - build/reserve/RDTE_result.json        (cross-flow sensitivity, field path recorded)
  - build/reserve/RDTF_result.json        (fork interval, CONTEXT ONLY)
  - build/reserve/RDTG_prediction.md      (the pre-registered bar constructions; sha pinned)

Contract: build/reserve/RDTG_prediction.md (committed 7ad70d2). The bars are
computed BEFORE any discriminator series is read (sequencing rule, git-order
gate check): no SAFE SDDS template contents, no destination-country holdings /
b.o.p.-by-counterpart / nonresident-share series are inputs here.

Every number is read from the committed artifacts or computed here at run time --
mass endpoints, outstandings, FX rates and COFER shares are never typed in
(permitted literals: file paths, unit-string guards, marker strings, and pin
assertions that fail loud if a committed input changes). DISK-ONLY: no network.
No date, no probability, no currency guess.
"""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

DENOM_PATH = ROOT / "build/reserve/RDTG_denominators.json"
RDTD_PATH = ROOT / "build/reserve/RDTD_result.json"
RDTE_PATH = ROOT / "build/reserve/RDTE_result.json"
RDTF_PATH = ROOT / "build/reserve/RDTF_result.json"
PRED_PATH = ROOT / "build/reserve/RDTG_prediction.md"
OUT_PATH = ROOT / "build/reserve/RDTG_bars.json"

RDTE_SENS_KEY = "cross_flow_sensitivity_detail (labelled; not caps)"

NOT_YET_COMPUTABLE = (
    "NOT-YET-COMPUTABLE -- no receiving-leg series has been read (pre-registered "
    "sequencing rule: bars precede every discriminator); Part 3 computes this "
    "column against each grounded leg's own published nonresident denominator"
)


def r3(x):
    return round(float(x), 3)


def r4(x):
    return round(float(x), 4)


def r6(x):
    return round(float(x), 6)


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    denom = load(DENOM_PATH)
    rdtd = load(RDTD_PATH)
    rdte = load(RDTE_PATH)
    rdtf = load(RDTF_PATH)

    # ------------------------------------------------------------------ masses
    upper = float(rdtd["identity"]["china_alone"]["delta_non_us_busd"])
    sens = float(rdte[RDTE_SENS_KEY]["positive_months_proxy_variant"]["total_busd"])
    lower = round(upper - sens, 3)
    fork = [float(v) for v in
            rdtf["part1_route_robust_ceiling"]["route_robust_interval"]["interval_busd"]]

    # Pin assertions: fail loud if any committed input changes under this script.
    assert upper == 494.977, f"upper mass endpoint changed: {upper}"
    assert sens == 354.028, f"cross-flow sensitivity changed: {sens}"
    assert lower == 140.949, f"derived lower endpoint changed: {lower}"
    assert fork == [48.484, 494.977], f"fork interval changed: {fork}"
    assert fork[1] == upper, "fork upper endpoint no longer equals the mass upper endpoint"
    assert lower > fork[0], (
        "generous-to-the-null direction violated: bars lower endpoint must exceed "
        "the fork's own lower endpoint")

    # ---------------------------------------------------------------- FX set
    fx = denom["fx_set"]
    assert fx["rate_date"] == "2021-12-30", "FX rate date changed"
    usd_per_eur = float(fx["rates"]["usd_per_eur"])
    usd_per_gbp = float(fx["rates"]["usd_per_gbp"])
    usd_per_aud = float(fx["rates"]["usd_per_aud"])
    jpy_per_usd = float(fx["rates"]["jpy_per_usd"])
    cad_per_usd = float(fx["rates"]["cad_per_usd"])
    chf_per_usd = float(fx["rates"]["chf_per_usd"])

    # ------------------------------------------------ outstandings, local bn
    mo = denom["market_outstandings"]

    jp = mo["JGB_JP"]
    assert jp["status"] == "GROUNDED-PRIMARY" and jp["unit"].startswith("100 million yen")
    jp_local_bn = float(jp["value"]) / 10.0  # oku-yen (1e8 JPY) -> JPY bn (1e9)

    de = mo["Bund_DE"]
    assert de["status"] == "GROUNDED-PRIMARY" and de["unit"].startswith("EUR;")
    de_incl_bn = float(de["value"]) / 1e9
    m = re.search(r"row 'Own holdings' same column = (-\d+)", de["quoted_cell"])
    assert m, "DE own-holdings figure not found in the committed quoted_cell"
    de_own_eur = float(m.group(1))  # negative
    de_ff_bn = (float(de["value"]) + de_own_eur) / 1e9  # free float
    assert abs(de_ff_bn - 1427.237742544) < 1e-6, f"DE free float changed: {de_ff_bn}"

    fr = mo["OAT_FR"]
    assert fr["status"] == "GROUNDED-ALTERNATE-OFFICIAL" and fr["unit"].startswith("EUR million")
    assert fr["confidence"] == "MEDIUM", "FR confidence tag changed"
    fr_local_bn = float(fr["value"]) / 1000.0

    uk = mo["gilt_UK"]
    assert uk["status"] == "GROUNDED-PRIMARY" and uk["unit"].startswith("GBP billion")
    uk_local_bn = float(uk["value"])

    au = mo["AGS_AU"]
    assert au["status"] == "NOT-GROUNDED" and au["value"] is None, "AU grounding status changed"

    ca = mo["GoC_CA"]
    assert ca["status"] == "GROUNDED-PRIMARY" and ca["unit"].startswith("CAD million")
    ca_local_bn = float(ca["value"]) / 1000.0

    # local bn -> USD bn at the grounded FX set
    to_usd = {
        "JGB_JP": lambda v: v / jpy_per_usd,
        "Bund_DE": lambda v: v * usd_per_eur,
        "OAT_FR": lambda v: v * usd_per_eur,
        "gilt_UK": lambda v: v * usd_per_gbp,
        "GoC_CA": lambda v: v / cad_per_usd,
    }
    to_local = {
        "JGB_JP": lambda u: u * jpy_per_usd,
        "Bund_DE": lambda u: u / usd_per_eur,
        "OAT_FR": lambda u: u / usd_per_eur,
        "gilt_UK": lambda u: u / usd_per_gbp,
        "GoC_CA": lambda u: u * cad_per_usd,
    }
    local_ccy = {"JGB_JP": "JPY", "Bund_DE": "EUR", "OAT_FR": "EUR",
                 "gilt_UK": "GBP", "GoC_CA": "CAD"}
    confidence = {
        "JGB_JP": "HIGH (GROUNDED-PRIMARY, MoF Japan)",
        "Bund_DE": "HIGH (GROUNDED-PRIMARY, Finanzagentur)",
        "OAT_FR": ("MEDIUM (GROUNDED-ALTERNATE-OFFICIAL: INSEE BDM official-statistics "
                   "republication of the AFT series; AFT primary unreachable -- tag "
                   "carried from RDTG_denominators.json onto this bar)"),
        "gilt_UK": "HIGH (GROUNDED-PRIMARY, UK DMO)",
        "GoC_CA": "HIGH (GROUNDED-PRIMARY, StatCan table 10-10-0002-01)",
    }

    # ------------------------------------------------------------- Scheme 1
    def scheme1_table(de_basis_bn, de_basis_label):
        local_bn = {"JGB_JP": jp_local_bn, "Bund_DE": de_basis_bn,
                    "OAT_FR": fr_local_bn, "gilt_UK": uk_local_bn,
                    "GoC_CA": ca_local_bn}
        usd_bn = {k: to_usd[k](v) for k, v in local_bn.items()}
        total_usd = sum(usd_bn.values())
        shares = {k: v / total_usd for k, v in usd_bn.items()}
        assert abs(sum(shares.values()) - 1.0) < 1e-12, "Scheme-1 shares do not sum to 1"
        markets = {}
        for k in local_bn:
            blo_usd = shares[k] * lower
            bhi_usd = shares[k] * upper
            blo_loc = to_local[k](blo_usd)
            bhi_loc = to_local[k](bhi_usd)
            entry = {
                "local_currency": local_ccy[k],
                "outstanding_local_bn": r3(local_bn[k]),
                "outstanding_usd_bn": r3(usd_bn[k]),
                "share_of_grounded_usd_total": r6(shares[k]),
                "bar_low_usd_bn": r3(blo_usd),
                "bar_high_usd_bn": r3(bhi_usd),
                "bar_low_local_bn": r3(blo_loc),
                "bar_high_local_bn": r3(bhi_loc),
                "pct_of_nonresident_holdings": NOT_YET_COMPUTABLE,
                "confidence": confidence[k],
            }
            if k == "Bund_DE":
                entry["basis_in_this_table"] = de_basis_label
                entry["bar_low_pct_of_outstanding_incl_own_holdings"] = r4(
                    100.0 * blo_loc / de_incl_bn)
                entry["bar_high_pct_of_outstanding_incl_own_holdings"] = r4(
                    100.0 * bhi_loc / de_incl_bn)
                entry["bar_low_pct_of_outstanding_free_float"] = r4(
                    100.0 * blo_loc / de_ff_bn)
                entry["bar_high_pct_of_outstanding_free_float"] = r4(
                    100.0 * bhi_loc / de_ff_bn)
            else:
                entry["bar_low_pct_of_outstanding"] = r4(100.0 * blo_loc / local_bn[k])
                entry["bar_high_pct_of_outstanding"] = r4(100.0 * bhi_loc / local_bn[k])
            markets[k] = entry
        sanity = {
            "grounded_usd_total_bn": r3(total_usd),
            "shares_sum": r6(sum(shares.values())),
            "bar_low_allocations_sum_usd_bn": r3(sum(shares[k] * lower for k in shares)),
            "bar_high_allocations_sum_usd_bn": r3(sum(shares[k] * upper for k in shares)),
            "uniform_pct_note": (
                "Under proportional allocation the %-of-outstanding is identical across "
                "markets by construction (= mass / grounded USD total): "
                f"bar_low {r4(100.0 * lower / total_usd)}%, "
                f"bar_high {r4(100.0 * upper / total_usd)}% -- except where a market's "
                "% is also expressed on a second basis (DE free float)."),
        }
        return markets, sanity

    s1_markets, s1_sanity = scheme1_table(de_incl_bn, "incl-own-holdings (HEADLINE basis)")
    s1ff_markets, s1ff_sanity = scheme1_table(
        de_ff_bn, "free-float (variant basis: outstanding minus own holdings)")

    scheme1 = {
        "rule": ("Market-size-proportional (pre-registered Scheme 1): the mass "
                 f"[{lower}, {upper}] $bn is allocated across the GROUNDED candidate "
                 "sovereign markets {JGB_JP, Bund_DE, OAT_FR, gilt_UK, GoC_CA} in "
                 "proportion to end-2021 outstanding stock converted to USD at the "
                 "grounded H.10 Dec-30-2021 FX set; each bar is then expressed in "
                 "local currency at the same FX set and as % of outstanding."),
        "au_drop": ("AGS_AU DROPS OUT of Scheme 1: its outstanding is NOT-GROUNDED in "
                    "RDTG_denominators.json (AOFM unreachable from this egress; archive "
                    "fallback blocked; nothing substituted from memory), per the "
                    "pre-registered rule in the denominators artifact."),
        "de_basis": ("Germany is computed on BOTH bases quoted in the denominators: "
                     f"incl-own-holdings EUR {r3(de_incl_bn)}bn (HEADLINE) and free-float "
                     f"EUR {r3(de_ff_bn)}bn (= outstanding {r3(de_incl_bn)}bn minus own "
                     f"holdings {r3(-de_own_eur / 1e9)}bn, both read from the committed "
                     "quoted_cell). The Part-3 leg test uses whichever basis the leg's "
                     "own series matches."),
        "fr_medium": ("OAT_FR carries its MEDIUM confidence tag from RDTG_denominators.json "
                      "through to its bar (GROUNDED-ALTERNATE-OFFICIAL, not the tasked "
                      "primary publisher)."),
        "markets_headline_de_incl_own_holdings": s1_markets,
        "sanity_headline": s1_sanity,
        "variant_de_free_float": {
            "note": ("Full re-allocation with Germany entering the proportional pool at "
                     "its free-float outstanding; carried alongside, never the headline."),
            "markets": s1ff_markets,
            "sanity": s1ff_sanity,
        },
    }

    # ------------------------------------------------------------- Scheme 2
    raw = denom["cofer_shares"]["shares_pct"]
    included = ["EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "other"]
    excluded = ["USD", "CNY"]
    assert sorted(included + excluded) == sorted(raw.keys()), "COFER currency list changed"
    inc_sum = sum(float(raw[c]) for c in included)
    check_100 = 100.0 - float(raw["USD"]) - float(raw["CNY"])
    assert abs(inc_sum - check_100) < 1e-9, "COFER shares no longer sum to 100"
    renorm = {c: float(raw[c]) / inc_sum for c in included}
    assert abs(sum(renorm.values()) - 1.0) < 1e-12, "renormalized shares do not sum to 1"

    renorm_arithmetic = (
        f"included_sum_pct = EUR {raw['EUR']} + JPY {raw['JPY']} + GBP {raw['GBP']} + "
        f"AUD {raw['AUD']} + CAD {raw['CAD']} + CHF {raw['CHF']} + other {raw['other']} "
        f"= {inc_sum!r}; cross-check 100 - USD {raw['USD']} - CNY {raw['CNY']} = "
        f"{check_100!r} (agrees to <1e-9); renormalized_share_c = raw_share_c / "
        f"included_sum_pct; renormalized shares sum to {sum(renorm.values())!r}.")

    # EUR mass -> DE + FR split by relative grounded outstanding (same currency,
    # so the split is taken directly on the EUR outstandings).
    w_de = de_incl_bn / (de_incl_bn + fr_local_bn)
    w_fr = fr_local_bn / (de_incl_bn + fr_local_bn)
    w_de_ff = de_ff_bn / (de_ff_bn + fr_local_bn)
    w_fr_ff = fr_local_bn / (de_ff_bn + fr_local_bn)

    def s2_market(ccy, market, weight=1.0, split_note=None):
        frac = renorm[ccy] * weight
        blo_usd, bhi_usd = frac * lower, frac * upper
        blo_loc, bhi_loc = to_local[market](blo_usd), to_local[market](bhi_usd)
        out_bn = {"JGB_JP": jp_local_bn, "Bund_DE": de_incl_bn, "OAT_FR": fr_local_bn,
                  "gilt_UK": uk_local_bn, "GoC_CA": ca_local_bn}[market]
        entry = {
            "cofer_currency": ccy,
            "renormalized_currency_share": r6(renorm[ccy]),
            "market_fraction_of_mass": r6(frac),
            "local_currency": local_ccy[market],
            "bar_low_usd_bn": r3(blo_usd),
            "bar_high_usd_bn": r3(bhi_usd),
            "bar_low_local_bn": r3(blo_loc),
            "bar_high_local_bn": r3(bhi_loc),
            "pct_of_nonresident_holdings": NOT_YET_COMPUTABLE,
            "confidence": confidence[market],
        }
        if split_note:
            entry["eur_split"] = split_note
        if market == "Bund_DE":
            entry["bar_low_pct_of_outstanding_incl_own_holdings"] = r4(
                100.0 * blo_loc / de_incl_bn)
            entry["bar_high_pct_of_outstanding_incl_own_holdings"] = r4(
                100.0 * bhi_loc / de_incl_bn)
            entry["bar_low_pct_of_outstanding_free_float"] = r4(100.0 * blo_loc / de_ff_bn)
            entry["bar_high_pct_of_outstanding_free_float"] = r4(100.0 * bhi_loc / de_ff_bn)
        else:
            entry["bar_low_pct_of_outstanding"] = r4(100.0 * blo_loc / out_bn)
            entry["bar_high_pct_of_outstanding"] = r4(100.0 * bhi_loc / out_bn)
        return entry, frac

    alloc = {}
    fracs = []
    e, f_ = s2_market("JPY", "JGB_JP")
    alloc["JPY__JGB_JP"] = e
    fracs.append(f_)
    e, f_ = s2_market("EUR", "Bund_DE", w_de,
                      f"EUR mass split DE/FR by relative grounded outstanding "
                      f"(headline incl-own basis): w_DE = {r3(de_incl_bn)} / "
                      f"({r3(de_incl_bn)} + {r3(fr_local_bn)}) = {r6(w_de)}")
    alloc["EUR__Bund_DE"] = e
    fracs.append(f_)
    e, f_ = s2_market("EUR", "OAT_FR", w_fr,
                      f"w_FR = {r3(fr_local_bn)} / ({r3(de_incl_bn)} + "
                      f"{r3(fr_local_bn)}) = {r6(w_fr)}")
    alloc["EUR__OAT_FR"] = e
    fracs.append(f_)
    e, f_ = s2_market("GBP", "gilt_UK")
    alloc["GBP__gilt_UK"] = e
    fracs.append(f_)
    e, f_ = s2_market("CAD", "GoC_CA")
    alloc["CAD__GoC_CA"] = e
    fracs.append(f_)

    # AUD -> AGS_AU: mass stated in USD and AUD; % of outstanding NOT-COMPUTABLE.
    aud_frac = renorm["AUD"]
    alloc["AUD__AGS_AU"] = {
        "cofer_currency": "AUD",
        "renormalized_currency_share": r6(aud_frac),
        "market_fraction_of_mass": r6(aud_frac),
        "local_currency": "AUD",
        "bar_low_usd_bn": r3(aud_frac * lower),
        "bar_high_usd_bn": r3(aud_frac * upper),
        "bar_low_local_bn": r3(aud_frac * lower / usd_per_aud),
        "bar_high_local_bn": r3(aud_frac * upper / usd_per_aud),
        "pct_of_outstanding": ("NOT-COMPUTABLE -- the AGS outstanding is NOT-GROUNDED "
                               "in RDTG_denominators.json (AOFM unreachable); the AUD "
                               "mass is stated in USD and AUD but no %-of-outstanding "
                               "denominator exists"),
        "pct_of_nonresident_holdings": NOT_YET_COMPUTABLE,
        "confidence": "LOW (denominator NOT-GROUNDED)",
    }
    fracs.append(aud_frac)

    chf_frac = renorm["CHF"]
    alloc["CHF__remainder_no_candidate_leg"] = {
        "cofer_currency": "CHF",
        "renormalized_currency_share": r6(chf_frac),
        "statement": ("STATED REMAINDER: CHF has no candidate sovereign-market leg in "
                      "the pre-registered set; its mass is carried, never allocated."),
        "bar_low_usd_bn": r3(chf_frac * lower),
        "bar_high_usd_bn": r3(chf_frac * upper),
        "bar_low_chf_bn": r3(chf_frac * lower * chf_per_usd),
        "bar_high_chf_bn": r3(chf_frac * upper * chf_per_usd),
    }
    other_frac = renorm["other"]
    alloc["other__remainder_unallocated"] = {
        "cofer_currency": "other",
        "renormalized_currency_share": r6(other_frac),
        "statement": ("STATED REMAINDER: COFER 'other currencies' map to no candidate "
                      "market; their mass is carried unallocated."),
        "bar_low_usd_bn": r3(other_frac * lower),
        "bar_high_usd_bn": r3(other_frac * upper),
    }

    market_frac_sum = sum(fracs)
    full_frac_sum = market_frac_sum + chf_frac + other_frac
    assert abs(full_frac_sum - 1.0) < 1e-12, "Scheme-2 fractions do not sum to 1"

    scheme2 = {
        "rule": ("COFER-currency-share-proportional (pre-registered Scheme 2): the raw "
                 "IMF COFER 2021-Q4 shares of allocated reserves are restricted to "
                 "non-USD currencies with CNY EXCLUDED (China's own currency is not a "
                 "reserve asset for itself) and renormalized to 1; each currency's mass "
                 "maps to its candidate sovereign market (EUR split DE/FR by relative "
                 "grounded outstanding; CHF and 'other' carried as stated remainders)."),
        "raw_shares_pct_2021Q4": {k: float(v) for k, v in raw.items()},
        "renormalization": {
            "excluded": {c: float(raw[c]) for c in excluded},
            "included_sum_pct": r6(inc_sum),
            "arithmetic": renorm_arithmetic,
            "renormalized_shares": {c: r6(renorm[c]) for c in included},
            "shares_sum_check": r6(sum(renorm.values())),
        },
        "eur_split_weights": {
            "headline_incl_own_holdings": {"w_DE": r6(w_de), "w_FR": r6(w_fr)},
            "variant_de_free_float": {"w_DE": r6(w_de_ff), "w_FR": r6(w_fr_ff)},
            "variant_note": ("Under the DE free-float basis the EUR mass splits "
                             f"DE {r6(w_de_ff)} / FR {r6(w_fr_ff)}; DE bars scale by "
                             f"{r6(w_de_ff / w_de)} and FR bars by {r6(w_fr_ff / w_fr)} "
                             "relative to the headline split -- headline remains "
                             "incl-own-holdings."),
        },
        "allocations": alloc,
        "sanity": {
            "market_allocations_fraction_sum": r6(market_frac_sum),
            "market_allocations_bar_high_sum_usd_bn": r3(market_frac_sum * upper),
            "market_allocations_bar_low_sum_usd_bn": r3(market_frac_sum * lower),
            "chf_plus_other_remainder_fraction": r6(chf_frac + other_frac),
            "full_sum_check": ("market allocations + CHF remainder + other remainder = "
                               f"{r6(full_frac_sum)} of the mass "
                               f"(bar_high: {r3(market_frac_sum * upper)} + "
                               f"{r3(chf_frac * upper)} + {r3(other_frac * upper)} = "
                               f"{r3(full_frac_sum * upper)} vs {upper})"),
            "cofer_methodology_caveat": denom["cofer_shares"]["vintage"],
        },
    }

    # ------------------------------------------------------------- assemble
    payload = {
        "artifact": "RDTG_bars",
        "task": ("RDT-G Phase 0c MAGNITUDE BARS (pre-registration: "
                 "build/reserve/RDTG_prediction.md, commit 7ad70d2; denominators: "
                 "build/reserve/RDTG_denominators.json)"),
        "establishment": ("NOT ESTABLISHED -- output of RDTG_bars_recompute.py; every "
                          "number below is an OUTPUT, not established, until the RDT-G "
                          "verifier scenario runs (build/reserve/RDTG_verify.json with "
                          "all_pass=true, byte-reproducing this file from the committed "
                          "inputs) AND the human gate reviews this stage. Bars are "
                          "yardsticks for the Part-3 leg tests, never findings."),
        "built_utc_date": "2026-07-02",
        "windows": ("Baseline 2015->2021, verdict 2022->2025 (RDT-G freeze-era windows "
                    "per the pre-registration); the bars state what the mass arriving "
                    "over the verdict window implies per candidate market."),
        "mass_endpoints_busd": {
            "upper": r3(upper),
            "upper_source_field": ("build/reserve/RDTD_result.json :: "
                                   "identity.china_alone.delta_non_us_busd"),
            "cross_flow_sensitivity": r3(sens),
            "sensitivity_source_field": ("build/reserve/RDTE_result.json :: "
                                         "\"cross_flow_sensitivity_detail (labelled; "
                                         "not caps)\".positive_months_proxy_variant"
                                         ".total_busd"),
            "lower": r3(lower),
            "lower_derivation": (f"lower = upper - sensitivity = {upper} - {sens} = "
                                 f"{lower} (computed at run time; both endpoints READ "
                                 "from the committed artifacts, never hardcoded)"),
            "fork_interval_context_busd": [r3(fork[0]), r3(fork[1])],
            "fork_source_field": ("build/reserve/RDTF_result.json :: "
                                  "part1_route_robust_ceiling.route_robust_interval"
                                  ".interval_busd (CONTEXT ONLY -- bars use "
                                  f"[{lower}, {upper}] per the pre-registration)"),
            "generous_to_the_null": (f"Bars are built on [{lower}, {upper}] $bn per the "
                                     f"pre-registration; the fork's own lower endpoint "
                                     f"({fork[0]}, RDT-F route-robust) is smaller, so "
                                     f"bars at {lower} are GENEROUS to the null -- a leg "
                                     f"that fails to see {lower} would see {fork[0]} "
                                     "even less. Direction stated; the object's fork "
                                     "interval is unchanged by this choice."),
        },
        "fx_set": {
            "publisher": fx["publisher"],
            "rate_date": fx["rate_date"],
            "rates": {k: float(v) for k, v in fx["rates"].items()},
            "source": fx["url"],
            "retained": fx["retained"],
        },
        "scheme1_market_size_proportional": scheme1,
        "scheme2_cofer_currency_share_proportional": scheme2,
        "stated_limitation": ("Pre-committed direction: the candidate set is not the "
                              "universe of non-US destinations (corporates, equities, "
                              "deposits, non-candidate sovereigns absorb too), so "
                              "per-market bars OVERSTATE what any one market should "
                              "show -- which makes a null WEAKER, never stronger."),
        "sequencing_attestation": (
            "No discriminator series was read, fetched, or opened in this task: no SAFE "
            "SDDS template contents (Section I.B or any other), no destination-country "
            "bond-holdings, balance-of-payments-by-counterpart, or nonresident-share "
            "series. DISK-ONLY: no network access was used. The only data inputs were "
            "the committed denominator artifact (build/reserve/RDTG_denominators.json), "
            "the three committed mass-endpoint fields named in mass_endpoints_busd "
            "(RDTD/RDTE/RDTF result JSONs, read at those field paths only), and the "
            "committed pre-registration RDTG_prediction.md. The bars therefore precede "
            "every discriminator in git order, as the pre-registration requires; no bar "
            "is revised after a discriminator series is seen. The denominators "
            "artifact's own sequencing attestation and co-presence register carry "
            "forward unchanged."),
        "inputs_sha256": {
            "build/reserve/RDTG_denominators.json": sha256_of(DENOM_PATH),
            "build/reserve/RDTD_result.json": sha256_of(RDTD_PATH),
            "build/reserve/RDTE_result.json": sha256_of(RDTE_PATH),
            "build/reserve/RDTF_result.json": sha256_of(RDTF_PATH),
            "build/reserve/RDTG_prediction.md": sha256_of(PRED_PATH),
        },
        "SOURCE": [
            ("build/reserve/RDTG_denominators.json | committed Phase-0b artifact | "
             "market outstandings (JP/DE/UK/CA GROUNDED-PRIMARY; FR "
             "GROUNDED-ALTERNATE-OFFICIAL MEDIUM; AU NOT-GROUNDED), COFER 2021-Q4 raw "
             "shares, H.10 Dec-30-2021 FX set; upstream publisher SOURCE lines are "
             "carried inside that artifact | read 2026-07-02"),
            ("build/reserve/RDTD_result.json :: identity.china_alone.delta_non_us_busd "
             f"= {upper} | committed RDT-D artifact | upper mass endpoint | read "
             "2026-07-02"),
            ("build/reserve/RDTE_result.json :: \"cross_flow_sensitivity_detail "
             "(labelled; not caps)\".positive_months_proxy_variant.total_busd = "
             f"{sens} | committed RDT-E artifact | cross-flow sensitivity subtracted "
             "to form the lower endpoint | read 2026-07-02"),
            ("build/reserve/RDTF_result.json :: part1_route_robust_ceiling."
             f"route_robust_interval.interval_busd = {fork} | committed RDT-F artifact "
             "| fork interval, CONTEXT ONLY | read 2026-07-02"),
            ("build/reserve/RDTG_prediction.md (commit 7ad70d2) | committed "
             "pre-registration | bar constructions implemented exactly as "
             "pre-registered | read 2026-07-02"),
        ],
        "recompute": ("build/reserve/RDTG_bars_recompute.py regenerates this file "
                      "byte-for-byte from the committed inputs (sorted keys, indent=1, "
                      "3-decimal $bn / local-bn amounts, 4-decimal percentages, "
                      "6-decimal shares); every pin assertion fails loud if a committed "
                      "input changes."),
    }

    text = json.dumps(payload, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    OUT_PATH.write_text(text, encoding="utf-8")
    print(json.dumps({
        "written": str(OUT_PATH.relative_to(ROOT)),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "mass_busd": [lower, upper],
    }, indent=1))


if __name__ == "__main__":
    main()
