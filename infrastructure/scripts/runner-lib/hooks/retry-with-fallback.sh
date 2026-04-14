#!/bin/bash
# Hook: retry-with-fallback — Signals retry when phase fails with transient error
# Hook point: on_failure
# Exit: 0=no retry needed, 2=retry with fallback
# Story: RUNNER-2.2

# Only retry on specific exit codes (transient errors)
case "$HOOK_EXIT_CODE" in
  124)
    # Timeout — worth retrying
    echo "  [hook:retry-with-fallback] Phase timed out, signaling retry" >&2
    exit 2
    ;;
  99)
    # Fatal (billing/quota) — do NOT retry
    echo "  [hook:retry-with-fallback] Fatal error (billing/quota), no retry" >&2
    exit 0
    ;;
  *)
    # Check if output suggests transient error
    if [[ -n "$HOOK_OUTPUT_FILE" && -f "$HOOK_OUTPUT_FILE" ]]; then
      if grep -Eiq "stream disconnected|connection reset|timed out|temporarily unavailable|rate limit|503" "$HOOK_OUTPUT_FILE" 2>/dev/null; then
        echo "  [hook:retry-with-fallback] Transient error detected, signaling retry" >&2
        exit 2
      fi
    fi
    # Non-transient failure — don't retry
    exit 0
    ;;
esac
