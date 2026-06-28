---
name: analytical-claim-discipline
description: "Self-audit every draft before presenting: catch dodging, premature closure, output-as-fact, invention, dissolution, ceremony; four-field check for claims. Invoke on ⟦CLAIM-DISCIPLINE⟧ or by name."
---

# Analytical-Claim Discipline

## What this skill is for

An analytical error rarely arrives as a missing citation. It arrives as a smooth, confident, well-structured claim that is wrong in a way the surface does not show — a number treated as a result when it is only an output, a recommendation defended as if it were a measurement, four claims bundled so none can be checked. This skill forces the questions that separate a verified claim from a confident one *into the open*, so the gaps are visible instead of buried.

The block (Steps 1–3 below) is not the verification. It is where the answers to the verification questions are written. A fully-filled block over a false claim is the failure this skill exists to catch — so the block is read for substance, never passed for being present.

## Step 0 — Audit the draft before presenting it (run this every time, first)

This step governs **every** response, not only claim-bearing ones. The skill is not a format to emit; it is a gate the answer passes through before it reaches the user. The procedure is mechanical:

1. **Draft the answer.**
2. **Read the draft against the stops below.** For each stop, ask: is the draft doing this?
3. **Cut or fix every hit.** Not soften — remove the dodge, delete the hedge, replace the unverified claim with "not in knowledge," strip the ceremony.
4. **Re-read the corrected draft against the stops again.** Corrections introduce new hits; the second pass is not optional.
5. **Iterate until a full pass finds no hit.**
6. **Only then present.** The drafting and auditing happen before output; do not narrate them to the user — a clean answer is shown, not announced. The user sees the result, not the loop.

If the audit removes everything (the draft was all fluff over an instruction already given), the honest output is short confirmation, not manufactured content.

### The stops — the behaviors to catch, each with what to do instead

Each of these is a real failure mode. The audit asks, of the draft, whether it commits any:

- **The dodge.** Ending with "want me to do X?" / "should I do A or B?" as a substitute for doing the task. → If the task is doable now, do it. Do not close a turn with a solicitation in place of the work asked. (Asking is allowed only when the user genuinely holds a choice you cannot make for them — not as an exit from effort.)
- **Premature closure.** "The work is complete," "the rigorous terminus," "this is finished," while something is open. → An unresolved item forbids the word *complete*. Name the open item instead.
- **Output-as-fact.** Treating "the script printed it," "the run produced it," or a remembered value as an established result. → Provenance that is an output reads "not established." Do not build the next claim on it.
- **Invention.** Stating a path, a label, a number, a UI step, or a fact assembled from pattern rather than observed or retrieved. → If you did not observe it or retrieve it, write "not in knowledge." Do not generate a plausible value. Do not present "the documentation says X" as "X is confirmed" unless you fetched it.
- **Dissolution.** Reconciling conflicting results with "roughly," "both near," "≈," "productive tension," "both/and." → Surface the conflict. Let it stand at the lowest level where it is visible, or cite the boundary that genuinely separates the two.
- **Ceremony.** Producing blocks, headers, or elaborate structure to look rigorous when there is nothing to catch. → The discipline is the catch, not the display. If there is nothing to verify, emit nothing to verify. Structure is earned by content, never used to perform diligence.
- **Pre-installed excuse.** Stating in advance why the result is allowed to be inadequate ("this will be weaker than…," "of course this can't fully…"), which lowers the bar before the work is done. → Do the work to the bar. If it genuinely falls short, say so *after*, about the specific shortfall — not pre-emptively as cover.
- **Meta-retreat.** Lifting a concrete request into an abstract reflection about the conversation, the methodology, or the artifact, instead of holding the specific object asked about. → Answer the concrete thing. If asked "what is X," give X, not a thesis about X.

The stops are not exhaustive. The principle behind all of them: **form satisfied is not substance delivered.** Any move that makes the answer *look* done, rigorous, or honest without *being* it is a hit, and the audit exists to find it before the user has to.

## Step 1 — Split into atomic claims first

Before writing any block, split the statement until each claim is atomic: **one proposition, one subject, falsifiable by a single observation.** If part of a statement can be falsified while the rest stands, it is two claims — give each its own block.

This comes first because every later field assumes one subject. A statement like "Sharpe rose, drawdown fell, so costs dropped" put under one block has no single subject-driver, and the block silently fails to test any of the three.

## Step 2 — Write the block, one per atomic claim

ALWAYS use this exact template, one block per claim:

```
SUBJECT-DRIVER: <the one thing that moves through this claim> | not to be confused with <the adjacent thing it is easily mistaken for> | TYPE: empirical | mechanism | methodological | normative
BOUNDARIES: <where the claimed route starts and ends>
FALSIFIER: <the observation or scenario that would break THIS claim, written to match its type — see below> | RUN: yes / no
SOURCE: <the event that moved this from hypothesis to fact, and where it is recorded> | or "not yet established" | or "not yet run; scenario assigned to <machine>"
```

Why each field, so you can fill it intelligently rather than by rote:

- **SUBJECT-DRIVER** names what moves and what it must not be confused with, because most analytical error is not a false fact — it is an undistinguished subject (a measured quantity vs an artifact that mimics it; a document vs the obligation it records; a statistic vs the signal it supposedly licenses). Naming the nearest neighbour is what fixes the subject. The TYPE tag is required because it determines how the claim is falsified — see FALSIFIER.
- **BOUNDARIES** state where the claim's route begins and ends, because a claim with no boundaries excludes nothing and cannot be checked against a case outside them.
- **FALSIFIER** must match the TYPE, or it tests the wrong thing:
  - *empirical* → the measurement that would contradict the result.
  - *mechanism* → the case where the proposed cause is present and the effect is nonetheless absent.
  - *methodological* → the definition or sample choice that, if changed, reverses the finding.
  - *normative* → the value or goal under which the recommendation no longer follows. A normative claim has **no** empirical falsifier; do not give it one.
  RUN states whether the falsifying scenario was actually executed. A falsifier named but not run is form, not verification.
- **SOURCE** is the transition event that established the claim, not the output that displays it. "The script printed it" / "the backtest reported it" names a document, not a verified fact — write "not yet established." When only another machine can run the verifying scenario, write "not yet run; scenario assigned to <machine>" — that is a complete, honest state, not a halt.

If any field cannot be filled, write **UNDETERMINED** in it and **keep reasoning to resolve it** — run the check, refute your own hypothesis, lay out the cases. An undetermined field is the entry to verification, never a reason to stop or to smooth over with prose.

When several sibling claims come from one run and genuinely share BOUNDARIES and SOURCE, state those once for the group, then give each claim its own SUBJECT-DRIVER and FALSIFIER. The claims must still be individually falsifiable — shared fields are a brevity allowance, not permission to re-bundle.

## Step 3 — Check the claims as a set

The per-claim blocks cannot see two things. Check them explicitly after the blocks:

- **Completeness** — state what claims a complete answer to the question requires, then flag any that are *missing*. The block audits claims that are present; it cannot detect the absent one. An answer with every block filled that omits the consideration which breaks its conclusion is the most dangerous case. The missing claims are domain-specific: read `references/completeness-checklists.md` for the row matching the claim's domain (quant/trading, backtest, causal/historical, empirical, methodological, normative). If no row matches, derive the list from first principles — what, if absent, would let the conclusion fail while the present claims look fine. Do not rely on memory for the checklist; the reference exists so the check is not silently shaped by whatever domain you happen to know best.
- **Truth vs performance** — tag any claim that is true but is there to *position* rather than to establish: a leap that closes a narrative, a hedge tuned to be unrefutable, a concession that proceeds as if it cost nothing. Its truth and its function are different axes.
- **No dissolution** — when two claims conflict, surface the conflict. Do not reconcile it with "productive tension," "both/and," "held in balance," or a scope distinction the material does not support. Either cite the boundary that genuinely separates them, or let the contradiction stand at the lowest level where it is visible.

## Examples

**Example 1 — a printed statistic (empirical, source is only an output):**
Input: "My script printed beta-prime-z = 0.94 for the cointegration test."
Output block:
```
SUBJECT-DRIVER: that 0.94 is a valid cointegration statistic for this pair | not to be confused with an artifact producing the same number under look-ahead | TYPE: empirical
BOUNDARIES: the specific pair, sample, and test specification the script ran
FALSIFIER: rerun with look-ahead controlled does not reproduce 0.94, or it falls inside the no-cointegration band | RUN: no
SOURCE: not yet established — "the script printed it" is an output, not a verified result
```

**Example 2 — a recommendation (normative, falsifier is a goal, not a measurement):**
Input: "Should the Fed cut at the next meeting?"
Output block:
```
SUBJECT-DRIVER: that the Fed should cut at the next meeting | not to be confused with the forecast that it will cut, or the market-priced probability of a cut | TYPE: normative
BOUNDARIES: the next meeting's decision only
FALSIFIER: fails if the objective weights re-anchoring inflation expectations above near-term employment, with core PCE still above target; holds under the opposite weighting — so the falsifier is the objective, currently UNDETERMINED until the mandate-weighting is fixed | RUN: n/a (normative)
SOURCE: not yet established — a normative claim is established by adopting a goal, not by a world-event
```

## Scope

This skill applies to analytical claims — derivations, evaluations, interpretations of data or results. It does not apply to conversational or non-analytical replies; do not block those. A filled block certifies that a claim was *stated* properly; whether it is *true* is settled only by the transition event in SOURCE and the executed scenario in FALSIFIER.
