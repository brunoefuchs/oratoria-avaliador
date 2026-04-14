#!/bin/bash
# Hook: check-quality-gate — Runs evaluator on phase output if configured
# Hook point: post_phase
# Exit: 0=pass, 1=halt (critical failure), 2=retry (below threshold)
# Story: RUNNER-2.2
# Dependencies: evaluator.sh (RUNNER-2.1)

# Guard: evaluator must be available
if ! declare -f evaluate_phase_output >/dev/null 2>&1; then
  exit 0
fi

# Guard: output file must exist
if [[ -z "$HOOK_OUTPUT_FILE" || ! -f "$HOOK_OUTPUT_FILE" ]]; then
  exit 0
fi

# Guard: phase must be configured for evaluation
if declare -f phase_has_evaluator >/dev/null 2>&1; then
  if ! phase_has_evaluator "$HOOK_PHASE"; then
    exit 0
  fi
fi

echo "  [hook:check-quality-gate] Running evaluator for phase=$HOOK_PHASE" >&2

eval_result=$(evaluate_phase_output "$HOOK_OUTPUT_FILE" "$HOOK_PHASE" "${HOOK_LOG_FILE:-/dev/null}" 2>/dev/null)
eval_exit=$?

# Map evaluator exit codes to hook exit codes
case $eval_exit in
  0) exit 0 ;;    # PASS → continue
  1) exit 2 ;;    # RETRY → retry
  2) exit 2 ;;    # REMEDIATE → retry
  3) exit 1 ;;    # HALT → halt
  *) exit 0 ;;    # Unknown → continue
esac
