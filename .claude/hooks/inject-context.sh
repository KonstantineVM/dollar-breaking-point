#!/bin/bash
# .claude/hooks/inject-context.sh
# Runs at SessionStart and SubagentStart. stdout is added to context.
# This GUARANTEES the guardrails are present in every context; it does NOT
# guarantee they are followed. Presence is deterministic; compliance is not.

set -euo pipefail
cat <<'EOF'
[HARNESS — integrity gates active]
Before any handoff and before ending any turn, apply both skills:
  - answer-integrity-audit  (⟦INTEGRITY⟧)
  - analytical-claim-discipline  (⟦CLAIM-DISCIPLINE⟧)

Non-negotiables for this build:
  1. The breaking point is reported as three objects — frontier (manifold),
     distance-to-frontier (signed scalar), hazard (with binding mode). NEVER a date.
  2. Estimation/test results are NOT ESTABLISHED until their verifier artifact
     exists on disk. Do not build the next claim on an unverified output.
  3. "hazard not identified" is a permitted, expected output. Do NOT fabricate a
     hazard, and do NOT define a factor so the conclusion is forced.
  4. Ground every present-day fact (data structure, access, methodology) against
     the publisher. Do not assert it from memory.
  5. Maintain build/ledger.json. Do not mark a step "done" without its verifier
     artifact. Human-gate steps require build/approvals/<DP>.approved, which only
     a human creates (the harness denies the agent write access to that folder).

Enforcement reality: the Stop and PreToolUse hooks block on the CHECKABLE shell
(missing verifier, missing approval, deferral language, missing SOURCE). The
integrity-critic prompt hook runs every turn-end but is a model, not a proof.
NONE of these can detect substitution-by-inference or planting-by-construction.
Those are caught, if at all, at the human gates. That is why the human gates exist.
EOF
exit 0
