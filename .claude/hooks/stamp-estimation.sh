#!/bin/bash
# .claude/hooks/stamp-estimation.sh
# Runs after Bash. Self-filters to estimation/test runs. PostToolUse cannot undo
# the run; it records the result as an OUTPUT (not a verified fact) and reminds
# via additionalContext. Non-blocking by nature; exits quietly on any parse issue.
set -uo pipefail
input="$(cat)"

command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)"
[ -n "$command" ] || exit 0
printf '%s' "$command" | grep -Eiq 'estimat|identif|gate|backtest|sinkhorn|ras_balance|fit_model' || exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
mkdir -p "$PROJECT_DIR/build"
printf '%s\tOUTPUT (not established until verifier runs)\t%s\n' "$(date -u +%FT%TZ)" "$command" >> "$PROJECT_DIR/build/run-ledger.log"

jq -n '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: "An estimation/test command just ran. Its result is an OUTPUT — NOT ESTABLISHED until its verifier scenario runs and its verifier artifact exists. Record the verifier path in build/ledger.json before marking the step done."}}'
exit 0
