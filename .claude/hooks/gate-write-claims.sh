#!/bin/bash
# .claude/hooks/gate-write-claims.sh
# Deterministic PreToolUse gate on deliverable writes. FAILS CLOSED: if the tool
# input cannot be parsed, the write is denied rather than silently allowed — an
# integrity gate that cannot read its input must not wave the write through.
#
# HONEST SCOPE: these are HEURISTICS, not detectors of the reasoning failure.
# A regex catches the phrase "treat as identified"; it cannot catch a model that
# planted the conclusion in its factor structure. The reasoning versions are the
# critic's and the human's job.

set -uo pipefail
input="$(cat)"

deny() {
  jq -n --arg r "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $r}}'
  exit 0
}

# Fail closed on unparseable input.
if ! printf '%s' "$input" | jq -e . >/dev/null 2>&1; then
  deny "Integrity gate could not parse the tool input as JSON; refusing the write (gate-write-claims)."
fi

file_path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"
content="$(printf '%s' "$input" | jq -r '.tool_input.content // .tool_input.new_string // (.tool_input.edits // [] | map(.new_string) | join("\n")) // empty' 2>/dev/null)"

[ -n "$file_path" ] || exit 0

# Only gate deliverables under build/.
case "$file_path" in
  *"/build/claims/"*|*"/build/results/"*|*"/build/model/"*) : ;;
  *) exit 0 ;;
esac

# 1. High-signal deferral / planting tells.
if printf '%s' "$content" | grep -Eiq 'phase[ -]?two|phase[ -]?2|for now,?[[:space:]]+(we|i)\b|assume[d]?[[:space:]]+identified|treat(ed)?[[:space:]]+as[[:space:]]+identified|TODO:?[[:space:]]*identif'; then
  deny "Deferral/planting language found in a deliverable. State the open item plainly (UNDETERMINED / NOT IDENTIFIED) or do the work — do not defer the hard part and present the deferral as method."
fi

# 2. A claims artifact must carry the four-field SOURCE line (claim-discipline).
case "$file_path" in
  *"/build/claims/"*)
    if ! printf '%s' "$content" | grep -q 'SOURCE:'; then
      deny "A claims artifact must include a SOURCE field. Provide SUBJECT-DRIVER / BOUNDARIES / FALSIFIER / SOURCE, or mark fields UNDETERMINED and keep reasoning — do not ship an unprovenanced claim."
    fi
    ;;
esac

exit 0
