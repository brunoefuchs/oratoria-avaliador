#!/bin/bash
# Hook: archive-session — Archives session log and cleanup temp files
# Hook point: on_complete
# Exit: 0 (always continue)
# Story: RUNNER-2.2

echo "  [hook:archive-session] Archiving session=$HOOK_SESSION_ID phase=$HOOK_PHASE" >&2

# End session tracking if available
if [[ -n "$HOOK_SESSION_ID" ]] && declare -f session_end >/dev/null 2>&1; then
  session_end "$HOOK_SESSION_ID" "0" "0" 2>/dev/null || true
fi

exit 0
