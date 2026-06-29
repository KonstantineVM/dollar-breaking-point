#!/usr/bin/env python3
"""Inject verdict + robustness + episode-simultaneity into panel_test.json."""
import json
P="/home/user/dollar-breaking-point/build/audit/panel_test.json"
r=json.load(open(P))

r["robustness"]={
  "R1_drop_CYM_reclassification_break":{
    "why":"CYM->USA jumps 1.72T->3.86T at 2023-S2 (+124%), a coverage/reclassification break, not a flow. Dropped CYM as a holder.",
    "mean_within_holder_US_vs_offshore_corr":0.485,
    "count_negative_F3_sign":"1 of 11",
    "reading":"In raw first-differences the F3 substitution sign (NEGATIVE US-vs-offshore) is ABSENT; US claims and the offshore-China pool co-move POSITIVELY (common growth/valuation trend)."
  },
  "R2_remove_common_factor":{
    "why":"Every US-column series shares one factor (2022-S1 dip + common uptrend). Demeaned each transition by the cross-holder mean to test whether an IDIOSYNCRATIC F3 substitution or F4 lead/lag survives.",
    "mean_idiosyncratic_US_vs_offshore_corr":-0.137,
    "count_negative_F3_sign":"6 of 11 (BEL,CHN,DEU,FRA,HKG,ITA negative; GBR,IRL,JPN,LUX positive; NLD ~0)",
    "residual_leadlag_mean_pairwise_asymmetry":0.195,
    "residual_footprint_cosine_F4_vs_F3":-0.865,
    "reading":"The sign-flip is MIXED (6 vs 5), incoherent across holders, from <=9 obs each. The footprint cosine of -0.865 is a MECHANICAL artifact of demeaning (residuals are anti-correlated with the factor they were demeaned against), NOT two recovered factors. Removing the cross-holder common factor REMOVES the F4 contagion/common-run direction itself -- so the residual cannot be used to claim it separates F3 from F4 (circular)."
  }
}

r["episode_2022_simultaneity"]={
  "transition":"2021-S2 -> 2022-S1",
  "pct_change_US_column_by_holder":{
    "BEL":-23.6,"CHN":-3.2,"CYM":5.4,"DEU":-17.1,"FRA":-16.2,"GBR":-17.1,
    "HKG":-8.4,"IRL":-16.0,"ITA":-11.3,"JPN":-20.9,"LUX":-18.5,"NLD":-23.2
  },
  "holders_dropping_simultaneously":"11 of 12, all in the SAME semiannual bucket 2022-S1",
  "decisive_reading":"The one episode the lead/lag test needs to order (the 2022 sanctions/repricing event) hits 11 of 12 holders' US-column SIMULTANEOUSLY within a single semiannual period. There is NO temporal ordering to detect at semiannual resolution: the F4 contagion discriminator (does a's drop LEAD b's?) cannot fire when everyone moves at once. A broad simultaneous drop is observationally the SHARED common-run direction -- exactly the f=0 degenerate footprint DP4 identified. Semiannual frequency is too coarse to separate contagion-ordering from a common shock."
}

r["interpretation"]={
  "F3_substitution_signature":"ABSENT / WRONG SIGN in levels. F3 predicts a holder cutting US claims WHILE the offshore-China pool rises (negative within-holder corr). Observed mean is +0.466 (positive co-movement). The substitution footprint is not present in the panel; offshore-China and US claims grow together.",
  "F4_contagion_signature":"NOT ORDERABLE. Contemporaneous cross-holder co-movement is high (+0.633) but that is common-trend, not ordered contagion. Lead/lag asymmetry is small (0.27) and noise-level (<=9 obs/pair). The decisive 2022 episode is SIMULTANEOUS across 11/12 holders -> no lead/lag to detect at semiannual resolution.",
  "footprint_collinearity":"The F4-contemporaneous and F3-within footprints across holders have cosine 0.939 (raw) -- still NEARLY COLLINEAR. The panel does NOT split the USA-column block into two distinct temporal directions. One dominant common factor governs both.",
  "f_dependence_persists":"Even the R2 demeaned negative correlations cannot separate F3 from F4 WITHOUT f: whether a holder's idiosyncratic US-vs-offshore anti-co-movement is F3 substitution-INTO-CHINA vs F4 rebalancing into NON-China offshore depends entirely on the China-nationality fraction f of that holder's offshore pool. The discriminator relocates the f-dependence; it does not remove it."
}

r["verdict"]="CONFIRM"
r["discriminator_separates_F3_F4"]=False
r["reason"]=(
  "CONFIRM the DP5/DP4 'F3/F4 not identified' on data in hand. The 11-period CPIS/PIP "
  "panel was pulled (16 series, 2020-S1..2025-S1) and the temporal lead/lag discriminator "
  "built. It does NOT break the f=0 degeneracy, for three grounded reasons shown on the raw "
  "panel: (1) the F3 substitution footprint is ABSENT/wrong-sign -- US-column holdings and the "
  "offshore-China destination pool co-move POSITIVELY (mean within-holder corr +0.47), not "
  "negatively as substitution requires; (2) the F4 contagion footprint is NOT ORDERABLE -- the "
  "one episode that matters (2022) drops 11 of 12 holders SIMULTANEOUSLY within a single "
  "semiannual bucket, so there is no lead/lag to detect; semiannual frequency is too coarse, "
  "exactly the granularity_caveat path (a) flagged; (3) the F3 and F4 footprints remain "
  "near-collinear across holders (cosine 0.94), so the USA-column block stays a single shared "
  "direction. The only way to get a sign-split (R2 demeaning) is to REMOVE the common F4 "
  "direction first (circular) and yields an incoherent 6-vs-5 split that STILL needs f to be "
  "read as F3-into-China vs F4-into-non-China-offshore. The time dimension the build already "
  "had does NOT separate F3 from F4 without pinning the China-nationality fraction f. "
  "'not identified' stands -- it was NOT false on data in hand. (No separation is fabricated; "
  "the raw 11-period panel is shown in raw_panel.)"
)
r["caveat_on_scope"]=(
  "This tests path (a) -- the temporal panel -- ONLY, against DP4's actual rank-1-at-f=0 "
  "operator. It does NOT re-open or modify DP4/DP5 artifacts and does NOT start DP6. The DP5 "
  "resolution_path.json claimed path (a) would 'break the degeneracy without pinning a hole'; "
  "executing it shows that claim was OPTIMISTIC: at CPIS's actual semiannual residency-basis "
  "granularity the panel cannot order the 2022 episode and carries no F3 substitution sign, so "
  "it does not deliver f-free separation. This is a finding ABOUT path (a)'s grounded "
  "granularity_caveat (semiannual; residency basis), now executed rather than asserted."
)

json.dump(r,open(P,"w"),indent=2)
print("verdict:",r["verdict"])
print("separates_F3_F4:",r["discriminator_separates_F3_F4"])
print("panel_periods_pulled:",r["panel_periods_pulled"])
print("series:",r["cells_pulled"]["n_series"])
EOF_GUARD=1
print("written",P)
