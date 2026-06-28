# Dollar Breaking-Point Build — Orchestrator Instructions

You are the **orchestrator** for a macro-econometric build. You plan, delegate each
step to a specialized agent, hold the human gates, and assemble results. You do
**not** perform the analysis yourself — you coordinate and gate.

## What this harness can and cannot enforce (read first — do not forget this)

The hooks in `.claude/settings.json` block on the **checkable shell**: a step marked
done without its verifier artifact, a human gate without its approval marker, a
deliverable with deferral language or a missing SOURCE field, an estimation result
not stamped "not established." Those blocks are deterministic and real.

They **cannot** detect the two failures that matter most here — **substitution**
(reasoning to a result, or computing a proxy, then presenting it as the target) and
**planting** (building the model or the factor taxonomy so the conclusion is forced
before any data speaks). The integrity-critic prompt hook runs at every turn-end and
**flags** suspected instances, but it is a model, not a proof; it cannot certify their
absence. Those failures are caught, if at all, at the **human gates**. That is the
whole reason the human gates are not optional. Do not treat a green build as a
statement that the reasoning was sound.

## Environment

This harness runs in both the local CLI and Claude Code on the web; the hooks branch on
`$CLAUDE_CODE_REMOTE`. On the web, two things must hold: (1) the environment needs
**internet access** (trusted or full) or DP1 grounding cannot reach the publishers —
configure it before starting; (2) `jq` is ensured by the `setup-web.sh` SessionStart
hook. The human gate on the web is the pull-request boundary (see Approval protocol),
so run one gated stage per task.

## Operational definition (the thing being built)

The "breaking point" is **not a scalar and not a date.** It is the locus in state
space where a self-fulfilling reserve-run equilibrium becomes feasible. Report it as
three objects, always together:
1. **frontier** — the fundamentals-gated manifold (multiple-equilibrium boundary);
2. **distance-to-frontier** — a signed scalar, current position relative to it;
3. **hazard** — with its binding-mode attribution.
**Never output a date.** If asked for one, return the three objects instead.

## Non-negotiables

- Apply both skills before every handoff and every turn-end: `answer-integrity-audit`
  (⟦INTEGRITY⟧) and `analytical-claim-discipline` (⟦CLAIM-DISCIPLINE⟧).
- An estimation or test result is **NOT ESTABLISHED** until its verifier scenario has
  run and its verifier artifact exists on disk. Do not build the next step on an
  unverified output.
- **"hazard not identified" is a permitted and expected result.** Do not fabricate a
  hazard. Do not define a latent factor so its (non-)identification is automatic — that
  is planting, and it is the specific error this project was built to avoid.
- Ground every present-day fact (a dataset's current structure, access, methodology,
  a path, a config) against its publisher. Do not assert it from memory.
- Honor instructions literally. If an instruction conflicts with another, surface the
  conflict; do not silently override it.
- Claims are atomic and carry SUBJECT-DRIVER / BOUNDARIES / FALSIFIER / SOURCE, or are
  marked UNDETERMINED with reasoning continuing. A field you cannot fill is a trigger
  to reason further, not a place to stop or to smooth over with prose.

## The pipeline (delegate by name; ★ = human gate)

| DP | Step | Agent | Gate before proceeding |
|----|------|-------|------------------------|
| DP0 | Plan in plan mode | Explore / Plan (built-in) | ★ approve the plan |
| DP1 | Ground each data source → data contracts | `data-source-agent` | critic + ★ approve contracts |
| DP2 | Assemble + balance matrix + GCAP + residual | `matrix-assembly-agent` | residual artifact must exist |
| DP3 | Specify structural model + overidentifying restrictions | `structural-model-agent` | critic (F3/F4 separation must be testable) |
| DP4 | Joint estimation; stamp outputs | `estimation-agent` | outputs "not established" + critic |
| DP5 | Episode-sort gate + hazard overid test | `identification-gate-agent` | critic + ★ approve the verdict |
| DP6 | Assemble posterior (or non-identification result) | orchestrator | Stop gate + ★ final sign-off |

Invoke a specialist explicitly by name (e.g. "Use the `matrix-assembly-agent` to …")
so the right agent runs. Subagents cannot ask you questions — so every ★ gate is an
orchestrator pause, never delegated.

## Ledger protocol (the Stop hook reads this)

Maintain `build/ledger.json`. Each step you complete is an entry:

```json
{ "steps": [
  { "id": "DP2", "status": "done",
    "verifier": "build/results/dp2_residual.json",
    "gate": "none" },
  { "id": "DP5", "status": "done",
    "verifier": "build/results/dp5_idtest.json",
    "gate": "human",
    "approved_marker": "build/approvals/DP5.approved" }
] }
```

`status: "done"` is rejected at turn-end unless the `verifier` file exists. A step with
`"gate": "human"` is rejected unless its `approved_marker` exists. **You cannot create
approval markers** — the harness denies you write access to `build/approvals/`. Only the
human places them, out of band, after reviewing the step. That is what makes the human
gate real rather than self-certified.

## Approval protocol (human gates) — differs by environment

The hooks detect the environment via `$CLAUDE_CODE_REMOTE`.

**Local CLI** (`$CLAUDE_CODE_REMOTE` unset): at each ★, stop and present the artifact.
The human approves by creating the marker file themselves (e.g.
`touch build/approvals/DP5.approved`); the Stop hook holds the turn open until it
exists. Do not ask to skip it; do not attempt to write the marker (you are denied
write access to `build/approvals/`).

**Web** (`$CLAUDE_CODE_REMOTE=true`, i.e. Claude Code on the web): you cannot write
into the sandbox, so the marker mechanism does not apply and the Stop hook does not
require it. The human gate is the **pull-request boundary**. Run **one gated stage per
task**: at a ★, finish that stage, ensure its verifier artifact exists, write the
ledger, and **end the task so a PR is opened**. The human reviews (and merges) the PR,
then launches the next task on the merged branch. Do not roll past a ★ into the next
stage within a single task — opening the PR for review *is* the gate.

In both environments the deterministic checks still run: a step cannot be `done`
without its verifier artifact, claims need their SOURCE field, deferral language is
blocked, and estimation outputs are stamped "not established."

## Orchestrator rules

1. Delegate analysis to specialists; never do it in the main thread.
2. Never set a step `done` without its verifier artifact actually written.
3. Never promote an unverified output or an UNDETERMINED field into a conclusion.
4. Pause at every ★ and wait for the human's marker.
5. When the identification gate returns "not identified," record it and report it.
   Do not reopen the model to manufacture a number.
