#!/bin/bash
# .claude/hooks/setup-web.sh  (SessionStart)
# In remote/web environments only, ensure jq is present (the gates need it). Output
# goes to a log, never to stdout (SessionStart stdout is injected into context).
# No-op in the local CLI: installing system packages on someone's machine unbidden
# would be presumptuous; ensure jq yourself there.
set -uo pipefail
[ "${CLAUDE_CODE_REMOTE:-false}" = "true" ] || exit 0
if ! command -v jq >/dev/null 2>&1; then
  { sudo apt-get update && sudo apt-get install -y jq; } >/tmp/harness-setup.log 2>&1 \
    || { apt-get update && apt-get install -y jq; } >>/tmp/harness-setup.log 2>&1 \
    || true
fi
exit 0
