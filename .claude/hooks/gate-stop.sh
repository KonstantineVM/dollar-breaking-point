#!/bin/bash
# .claude/hooks/gate-stop.sh
# Deterministic end-of-turn gate.
#
# ENFORCES (real): a "done" step must have its verifier artifact on disk. This runs
# in BOTH local CLI and remote/web environments.
#
# HUMAN GATE: in the local CLI, a "human"-gated step also requires its approval
# marker on disk (the human touches it). In remote/web environments
# ($CLAUDE_CODE_REMOTE=true) the human cannot write into the ephemeral sandbox, so
# the human gate is the PULL-REQUEST boundary instead — run one gated stage per
# task/PR. The marker check is therefore SKIPPED when remote; do not let that read
# as "no human gate", it has moved to the PR review.
#
# CANNOT do: detect substitution or planting. A pass here is not a soundness claim.

set -uo pipefail
input="$(cat)"

# Self-evidencing: append exactly one line to build/gate-stop.log BEFORE emitting any
# block decision. The line is authored by the hook (a real turn-end block leaves a
# durable record the assistant cannot fabricate or suppress). Does not touch the
# decision, the stop_hook_active guard, or the verifier/approval checks.
log_block() {
  local reason="$1" sid ts remote flat
  sid="$(printf '%s' "$input" | jq -r '.session_id // "unknown"' 2>/dev/null || echo unknown)"
  ts="$(date -u +%FT%TZ)"
  remote="${CLAUDE_CODE_REMOTE:-false}"
  flat="$(printf '%s' "$reason" | tr '\n' ' ')"
  mkdir -p "${PROJECT_DIR:-$(pwd)}/build"
  printf 'STOP-BLOCK\t%s\tsession=%s\tremote=%s\treason=%s\n' \
    "$ts" "$sid" "$remote" "$flat" >> "${PROJECT_DIR:-$(pwd)}/build/gate-stop.log"
}

active="$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null || echo true)"
[ "$active" = "true" ] && exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
LEDGER="$PROJECT_DIR/build/ledger.json"
[ -f "$LEDGER" ] || exit 0

if ! jq -e . "$LEDGER" >/dev/null 2>&1; then
  log_block "build/ledger.json is not valid JSON; cannot verify build state. Fix the ledger before closing the turn."
  jq -n '{decision: "block", reason: "build/ledger.json is not valid JSON; cannot verify build state. Fix the ledger before closing the turn."}'
  exit 0
fi

REMOTE="${CLAUDE_CODE_REMOTE:-false}"
problems=()
while IFS=$'\t' read -r id status verifier gate approved; do
  [ "$status" = "done" ] || continue
  if [ -n "$verifier" ] && [ ! -e "$PROJECT_DIR/$verifier" ]; then
    problems+=("step ${id}: marked done but verifier artifact '${verifier}' is missing — the result is NOT ESTABLISHED")
  fi
  if [ "$gate" = "human" ] && [ "$REMOTE" != "true" ] && [ ! -e "$PROJECT_DIR/$approved" ]; then
    problems+=("step ${id}: human gate, but approval marker '${approved}' is absent — needs sign-off before proceeding")
  fi
done < <(jq -r '.steps[]? | [.id, (.status // ""), (.verifier // ""), (.gate // ""), (.approved_marker // "")] | @tsv' "$LEDGER")

if [ "${#problems[@]}" -gt 0 ]; then
  reason="Build cannot close yet:"
  for p in "${problems[@]}"; do reason="${reason}"$'\n'"  - ${p}"; done
  log_block "$reason"
  jq -n --arg r "$reason" '{decision: "block", reason: $r}'
  exit 0
fi
exit 0
