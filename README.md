# Dollar Breaking-Point Build Harness (Claude Code)

A Claude Code harness that runs the dollar breaking-point build through a fixed
pipeline, with an orchestrator delegating to six specialized subagents and an
integrity gate at every decision point. Requires **Claude Code** (hooks and subagents
do not exist on claude.ai).

## What it enforces — and what it does not (read this first)

The hooks deterministically block on the **checkable shell**: a step marked done
without its verifier artifact, a human gate without its approval marker, a deliverable
containing deferral/planting language or missing a SOURCE field, an estimation result
not recorded as "not established," and any attempt by the agent to write its own human
approval. These are real, tested gates.

They **cannot** detect **substitution** (reasoning to a result and presenting it as the
target) or **planting** (building the model so the conclusion is forced). The
integrity-critic — both the Stop prompt hook and the read-only critic subagent — flags
suspected instances, but it is a model, not a proof, and cannot certify their absence.
Those two failures rest on the **human gates**. A green build is not a certificate that
the reasoning was sound. This boundary is the point of the design, not a caveat to it.

## Layout

```
CLAUDE.md                      orchestrator instructions + non-negotiables + protocols
.claude/
  settings.json                hooks (4 command + 1 prompt) and the approvals deny-rule
  hooks/
    setup-web.sh               SessionStart (web only): ensure jq in the sandbox
    inject-context.sh          SessionStart/SubagentStart: inject guardrails into context
    gate-write-claims.sh       PreToolUse(Write|Edit): block deferral language / missing SOURCE; fails closed
    gate-stop.sh               Stop: block turn-end on unmet verifier (both) / approval (CLI only)
    stamp-estimation.sh        PostToolUse(Bash): record estimation runs as "not established"
  agents/                      the six specialists (data-source, matrix-assembly,
                               structural-model, estimation, identification-gate, integrity-critic)
  skills/
    answer-integrity-audit/        included
    analytical-claim-discipline/   included (snapshot, with references/)
```

## Install

1. Copy this `CLAUDE.md` and `.claude/` into your project repo root.
2. Make the hook scripts executable: `chmod +x .claude/hooks/*.sh`
3. Ensure `jq` is installed (the hooks use it): `jq --version`
4. Both skills are bundled under `.claude/skills/` — `answer-integrity-audit` and a
   snapshot of `analytical-claim-discipline` (with its `references/`). If you maintain a
   newer version of the latter, replace the bundled copy with yours.
5. Start Claude Code in the repo: `claude`
6. Confirm the pieces loaded: run `/hooks` (all five should appear under their events),
   `/agents` (the six specialists), and `/skills` (both skills).

## Verify the gates actually bite (do not skip)

A hook that silently does nothing is indistinguishable from a working one until it
matters. Before trusting the harness, confirm each gate blocks:

- Ask the orchestrator to write a file under `build/claims/` with no `SOURCE:` line —
  the PreToolUse gate should deny it.
- Put a step `"status":"done"` in `build/ledger.json` with a `verifier` path that does
  not exist, then let the turn try to end — the Stop gate should block and name it.
- Ask it to `touch build/approvals/DP5.approved` — the deny rule should refuse.

These mirror the tests this harness was validated against. If any does not block, fix
the hook before relying on it.

## Run

Tell the orchestrator to execute the pipeline DP0 → DP6 (defined in `CLAUDE.md`). It
plans in plan mode, delegates each step to a specialist by name, the critic gates each
handoff, estimation outputs are stamped "not established," and the build pauses at each
★ human gate. Your job at a ★ is to read the artifact and, if it holds, create the
approval marker yourself (e.g. `touch build/approvals/DP1.approved`). The deepest two
failures are caught here, by your reading — so read, do not rubber-stamp.

## Running on Claude Code on the web

The harness runs on the web (it detects `$CLAUDE_CODE_REMOTE` and adapts). Differences:

- **Install** = commit `CLAUDE.md` and `.claude/` to the GitHub repo you point the web
  session at. The cloud sandbox clones the repo and runs the hooks from it. (`chmod` is
  unnecessary — the hooks are invoked as `bash <script>`.)
- **Internet access**: limited by default. DP1 grounding (the data-source-agent reaching
  publishers) needs it. In the environment settings, set network access to trusted or
  full before starting; with trusted, allowlist the publisher domains you need.
- **`jq`**: ensured automatically by `setup-web.sh` (a SessionStart hook), which runs
  `apt-get install -y jq` only in the remote sandbox.
- **Human gates = pull requests.** You cannot write into the sandbox mid-task, so the
  approval-marker mechanism is off on the web and the Stop gate does not require it.
  Instead, **run one gated stage per task**: each task does a stage, opens a PR, and
  stops; you review and merge the PR (that is the gate), then launch the next stage as a
  new task. The deterministic gates (verifier artifact present, SOURCE field, no
  deferral language, "not established" stamps) still run inside every task.
- Everything else — the six agents, the critic prompt hook, the write and stop gates —
  works unchanged.

The verify-the-gates-bite checks above still apply; run them in a throwaway task first.
