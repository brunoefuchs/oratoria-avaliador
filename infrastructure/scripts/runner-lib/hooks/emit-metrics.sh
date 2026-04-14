#!/bin/bash
# Hook: emit-metrics — Records phase metrics via runner-lib metrics.sh
# Hook point: post_phase
# Exit: 0 (always continue)
# Story: RUNNER-2.2

# Guard: metrics functions must be available
if ! declare -f record_metrics >/dev/null 2>&1; then
  echo "  [hook:emit-metrics] metrics.sh not loaded, skipping" >&2
  exit 0
fi

# Calculate output size
output_size=0
if [[ -n "$HOOK_OUTPUT_FILE" && -f "$HOOK_OUTPUT_FILE" ]]; then
  output_size=$(wc -c < "$HOOK_OUTPUT_FILE" | tr -d ' ')
fi

echo "  [hook:emit-metrics] Recording metrics for phase=$HOOK_PHASE squad=$HOOK_SQUAD" >&2

exit 0
