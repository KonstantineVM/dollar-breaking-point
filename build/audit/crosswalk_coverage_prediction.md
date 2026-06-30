# Construct-the-Crosswalk Coverage — PRE-REGISTERED FALSIFIABLE PREDICTION

**Timestamp: 2026-06-30 (written and committed BEFORE Parts 1–4 — before any source is fetched, before the crosswalk is built, before B is recomputed).**

This file is a pre-registration, committed to the branch *before* the SEC-HFCAA / XBRL-VIE / GLEIF-QCC
crosswalk is constructed and applied. The prediction below **may be REFUTED by the result**, and either
outcome is the finding to report. Do not tune toward this prediction; do not suppress a refutation. Ground
every join rate from the real files; report the measured B whatever it is.

## What this build does

The prior coverage pass measured discriminating coverage **B = 0.287** (share of US-held haven VALUE whose
parent-nationality differs from residence — the part that could break the uniform aggregate reweighting). It
was thin because it relied on GLEIF Level-2 alone, where Chinese VIEs dead-end at `SELF=KY` (the Cayman
shell's ultimate parent often has no LEI). This build constructs a free, official route around that exact
failure — the SEC HFCAA Commission-Identified-Issuer list + Form F-6 ADR jurisdiction + the mandatory
VIE-look-through Inline-XBRL tags naming the consolidated Chinese OpCo's jurisdiction directly — joins it to
the panel, and **re-measures B for direct comparability**.

## The prediction (verbatim, falsifiable)

> Prediction: the SEC-HFCAA + XBRL-VIE route raises discriminating coverage **B** from the prior **0.287**
> toward roughly **0.45–0.65**, by directly tagging the large Chinese VIE/ADR equity names (Alibaba, PDD,
> Baidu, JD, NetEase, Trip.com, and the broader HFCAA universe) that resolve KY/HK by residence but CN by
> consolidated operating entity — value GLEIF Level-2 missed. **B is expected to materially exceed 0.287 but
> is NOT expected to clear the ~0.80 RECOMMEND-PROCEED bar**, because the prior pass measured the uncovered
> tail to be large, diffuse, and dominated by genuinely non-Chinese Cayman structured-credit / hedge-fund
> vehicles (CLOs, etc.) that no Chinese-nationality crosswalk will tag.
>
> Refutation / outcomes:
> - If **B does not materially exceed 0.287** (say, fails to reach ~0.35), the construction failed to add the
>   tagging a licensed per-security crosswalk would — the SEC/XBRL route is not a sufficient free substitute.
>   REFUTES the "this route adds real discriminating coverage" expectation.
> - If **B clears ~0.80** with a bounded/characterized tail, that EXCEEDS this prediction — the free route is
>   sufficient and a re-tag + separability re-test becomes worth running.
> - The expected middle outcome (B materially above 0.287 but short of 0.80) means the free route adds real
>   per-security CN nationality yet still leaves the identification-relevant residual to the licensed crosswalk.

## Decision bar (pre-registered, applied in Part 4)

- **RECOMMEND-PROCEED** iff B clears ~0.80 by value with a bounded/characterized uncovered tail.
- **RECOMMEND-NOT-PROCEED** if B remains well short of 0.80; report how far the construction moved B from
  0.287 and what residual untagged value remains for the licensed CMNS crosswalk.
- **OPEN** if sources are unfetchable or coverage is ambiguous.

## Anti-planting commitments

- Every CN flag must trace to **HFCAA membership OR an XBRL VIE-OpCo jurisdiction tag OR an F-6 home
  jurisdiction OR a GLEIF/QCC parent** resolving to CN — never a name-guess. A name that cannot be sourced is
  left untagged, not assumed CN.
- No large, obviously-Chinese issuer is to be left untagged to deflate B; if one appears in the untagged
  tail, that means the construction is incomplete (to be reported), not that the tail is non-Chinese.
- Every join/match rate is MEASURED from the real fetched files and recomputable from the tagged panel; none
  is asserted. The new B is recomputed from the tagged panel by a committed script.

## Scope

This pass STOPS after the prediction, the sources contract, the tagged panel, the coverage artifact, the
recompute script, and the recommendation. It does NOT re-tag the operator, does NOT rebuild the operator,
does NOT re-run separability, does NOT touch DP2–DP5, and does NOT begin DP6. No date, no bare probability,
no hazard claim.
