# RDT-C — Destination of China's UST outflow: PRE-REGISTERED DESIGN + PREDICTION

**Timestamp: 2026-07-02 (committed BEFORE any RDT-C build — the class-level panel, the SAFE totals fetch,
the ledger, and the verdict do not yet exist).**

Pre-registration, committed first. Symmetric: **(b) WITHIN-US-ROTATION demotes the object's one live signal
to instrument rotation — a fully valid landing; (c) LEFT-US-SECURITIES sustains the exit reading one step,
with the destination currency UNDETERMINED by the k1 wall (RDT-B) — the verdict says which, and never
guesses the currency.** Read-only on prior artifacts (one tasked exception: the Part-3 insert-only
amendment of the object's k3 annotation, mechanics per the RDT-B precedent). DP2–DP6 untouched. No date,
no probability.

## The three branches, and the status of (a)

China's UST-active outflow (RDT-B, recent-3y verdict axis: −0.1092/yr on holdings ≈ −284.8 $bn cumulative
over 36 months, China-alone) went somewhere. Three destinations:
- **(a) Reserve drawdown** — the task states this is CLOSED by grounded search (SAFE totals ≈ +$230bn
  2022→2025 while UST-active ≈ −$280bn; valuation caveat carried). **Per this pre-registration, (a) is
  closed only pending Part 1's own fetch of the official SAFE monthly series — the search summary is not
  trusted.** The closure is tested on the SAFE **foreign-exchange-reserves line (ex-gold)** (cleaner: it
  excludes the gold-price valuation leg); the remaining non-USD/bond valuation inside FX reserves is
  stated as an unquantified caveat, bounded where possible. **If the fetched series contradicts the
  closure (FX reserves fell roughly in step with the UST outflow over the verdict window), branch (a)
  REOPENS and the verdict says DRAWDOWN-REOPENED** — surfaced, not smoothed over.
- **(b) WITHIN-US-ROTATION** — the outflow stayed in US LT securities, rotating into agencies /
  corporates / equities.
- **(c) LEFT-US-SECURITIES** — total US LT securities fell roughly in step with the UST leg; the money
  left US securities. Destination currency: **UNDETERMINED** (the RDT-B k1 wall) — never guessed.

## Mechanical rules (fixed here)

Let X = China's UST active flow over the window (expected negative), and A = the sum of active flows into
the NON-UST US LT classes (agencies + corporate debt + equities), same window, same holder variant, all on
the transactions (active) basis.
- **WITHIN-US-ROTATION** iff A ≥ 0.5·|X| — the non-UST classes absorb at least ~half the UST outflow.
- **LEFT-US-SECURITIES** iff A ≤ 0.1·|X| (including A < 0: selling the other classes too is stronger
  (c)) — total US LT falls roughly in step with (or faster than) UST.
- **MIXED** iff 0.1·|X| < A < 0.5·|X| — the verdict states the ledger (the absorbed fraction A/|X| and the
  residual).
- Computed on **both custody variants** (China-alone; China+Belgium+Luxembourg) — if the two variants land
  on different branches, the verdict is **MIXED-BY-CUSTODY**, stating both. The band is carried through
  every term, never collapsed.
- **Windows (all fixed here; none added later):** the VERDICT AXIS is the RDT-B recent-3y window verbatim
  (the last 36 published months, 2023-05..2026-04 as of the on-disk data). Shown beside it, never the
  verdict: the full window (2013-01→latest) and a labelled freeze-era context window (2022-03→latest).
- **Active basis only** for the ledger: transactions per class; per-class valuation = Δholdings − active,
  a residual whose DIRECTION is stated per class (the 2022 rates selloff cuts agency/corporate bond values
  — the false-exit confound, per class this time; equity valuation moves with the equity market). A
  class-level valuation loss is never read as selling.

## The ledger (Part 2, fixed form)

Per window and per custody variant:
`UST-active (−X) = Δagencies-active + Δ(corporates+equities)-active + residual (left US securities)`
— every term from the transactions data; the residual is what the mechanical rule classifies. The 2023-02
Form S → SLT transactions basis break is carried row-by-row (RDT-B precedent); where a class series does
not exist on one basis, that gap is stated, not interpolated.

## The flipped guard (verbatim; BOTH directions are violations)

**DRAMATIZE:** reading class-level valuation losses as selling to force (c) — the ledger is active-basis
only, and every valuation residual carries its direction statement.
**ZERO:** stretching the window to dilute the rotation — the verdict axis is fixed above at the RDT-B
recent-3y window; the full and freeze-era windows are pre-registered context, and no other window is
introduced.

## Falsifiable expectation (symmetric; any landing promotable)

> **Primary expectation: MIXED** — agencies (and possibly equities) absorb a material but sub-half share
> of the UST outflow. I do not favor it: **REFUTED toward (b)** if A ≥ 0.5·|X| — the object's live signal
> is then DEMOTED to instrument rotation, a fully valid landing stated plainly; **REFUTED toward (c)** if
> A ≤ 0.1·|X| — the exit reading is sustained one step, destination currency UNDETERMINED. If the SAFE
> fetch contradicts the (a)-closure, DRAWDOWN-REOPENED is reported regardless of the ledger. No branch is
> privileged; the ledger decides.

## Part 3 — amendment mechanics (the RDT-B precedent)

The object's k3 annotation is amended **insert-only** with the destination verdict — DEMOTED (b) /
EXIT-CONSISTENT-CURRENCY-UNDETERMINED (c) / MIXED (with the ledger) / DRAWDOWN-REOPENED — via a
deterministic `RDTC_recompute.py` that regenerates the amended object (strip-and-reinsert reproduces the
pre-RDT-C object byte-for-byte against its sha as committed after RDT-B); `RDT_recompute.py`,
`RDTB_recompute.py`, and all prior artifacts are NOT modified; `RDTC_verify.json` carries the
byte-reproduction flags for the class flows, the result/ledger, and the amended object. Numbers computed,
never hardcoded. No date, no probability, no currency guess.

## Anti-planting commitments

- The class schema (which classes exist by country, on which basis, over which spans) is READ from the
  real on-disk SLT/Form-S files and quoted — a finding, not an assumption.
- The SAFE totals leg is FETCHED from the publisher (the on-disk safe_ora files are the cross-check), and
  the valuation caveat on totals is quantified where possible (gold leg from on-disk tonnes × price),
  stated where not.
- Thresholds (0.5 / 0.1), windows, and the custody-disagreement rule are fixed here, before any data;
  applied mechanically.
- Both custody variants and all three windows reported; the verdict axis fixed ex ante.

## Scope

Writes ONLY `build/reserve/RDTC_*` and `build/reserve/rdtc_evidence/*`, plus the tasked insert-only
amendment of `build/reserve/RDT_breaking_point_object.md` via `RDTC_recompute.py`. DP2–DP6, RD1, RD2, RDT,
RDT-B artifacts otherwise untouched. No date, no probability, no destination-currency guess. What follows
RDT-C, if anything, is decided at the gate.
