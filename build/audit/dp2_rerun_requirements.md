# DP2 re-run requirements — carry-forward from the DP2 audit

The next DP2 re-run (on the CPIS-augmented, multi-country bilateral matrix) MUST do the
three things below. Each is traceable to a specific DP2-audit finding; none is optional.
This file records the requirements only — it does not perform the re-run and does not modify
any DP2 artifact (the audit and this reopening are read-only with respect to `build/model/*`
and `build/results/*`).

## (a) FIX the claims/liabilities label swap in the residual artifact
**Traceable to:** `build/audit/residual_recompute.json` → `bis_asymmetry` (audit fact #1).

`build/results/dp2_residual.json`'s `bis_marginal_asymmetry` block has the **claims and
liabilities labels reversed**:
- it labels `usd_claims = 10,240,580.6` and `usd_liabilities = 9,529,422.9`;
- but the raw BIS LBS data shows **position C (CLAIMS) = 9,529,422.9** and **position L
  (LIABILITIES) = 10,240,580.6**.

The **magnitude reproduces exactly** (|asymmetry| = $711,157.7mn) and `matrix_assembled.json`
is itself correctly labeled — only the residual artifact's asymmetry block is inverted. The
re-run MUST emit `usd_claims = 9,529,422.9` and `usd_liabilities = 10,240,580.6`.

Secondary defect, same finding: the reported **`asymmetry_pct = 7.19%` matches no reproducible
denominator** (claims-base = 7.463%, liab-base = 6.945%, mean-base = 7.194%). The re-run MUST
either state the denominator basis explicitly or drop the percentage in favor of the
unambiguous absolute figure.

## (b) WRITE the RAS column-target vector (and the exact RAS set/seed rule) to disk
**Traceable to:** `build/audit/residual_recompute.json` → `ras_residuals` (audit fact #1).

The headline **$3,962,793mn ($3.96tn) row residual is currently UNRECONSTRUCTABLE**: the
column-target vector is absent from every on-disk artifact, so a clean from-scratch Sinkhorn
gave **last-pass row_resid_L2 ≈ $5,489,628mn ($5.49tn)** instead — the gap is driven entirely
by the unknown column targets. **The number is not established at any value until it is
reproducible.** The qualitative result (non-convergence after 200 passes, column residual
driven to ~machine-zero, large stalled row residual) does reproduce; the exact figure does not.

The re-run MUST persist, alongside the assembled matrix, the inputs needed to reproduce the
residual blind:
1. the **column-target (column-marginal) vector** actually used;
2. the **exact area set** for the RAS (the audit could only infer "US + 18 BIS areas = 19";
   `matrix_spec.json`'s `area_set` lists 22 labels — the discrepancy must be resolved on disk);
3. the **seed rule**: the prior constant (eps) and the placement rule for the prior-seeded
   cells (the original states 17 TIC seed cells + 38 prior cells; the recompute found 18 TIC
   counterparties present — reconcile and record).

A residual figure whose inputs are not on disk is an output, not an established result.

## (c) DO NOT assume the residual collapses when CPIS cells populate
**Traceable to:** the BIS asymmetry finding (audit #1) + `build/audit/cpis_probe.json`.

CPIS adds **portfolio-investment (securities) bilateral cells**. It does **not** touch the
**BIS banking-marginal floor**: the **~$711bn (711,157.7 USD mn) claims/liabilities asymmetry
exists BEFORE any RAS** — same source (BIS LBS), same area set, marginals that do not net to
zero. Any balanced matrix sits at least this far from internal consistency regardless of how
many CPIS cells populate.

The re-run MUST therefore **report whatever the residual actually is** after the real bilateral
cells are assembled — it must NOT presuppose that populating CPIS collapses the residual to
zero or near-zero. The structural-sparsity non-convergence DP2 found was about the *banking*
column support; CPIS densifies the *portfolio* layer, a different instrument block. The two
must be balanced and their residuals reported on their own terms, with the irreducible BIS
banking-marginal asymmetry stated as a floor.

---

**Summary:** the re-run inherits (a) a label-correction, (b) a reproducibility obligation for
the RAS residual, and (c) a prohibition on assuming the residual vanishes. Together these keep
the next DP2 from re-importing the three defects this audit established.
