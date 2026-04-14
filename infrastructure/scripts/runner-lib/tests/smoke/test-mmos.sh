#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Smoke test for mmos runner (Story 115.5)
# ═══════════════════════════════════════════════════════════════
# Validates that mmos.sh can bootstrap, create state, and exit
# gracefully without requiring a live LLM.
#
# Exit: 0 = PASS, 1 = FAIL, 77 = SKIP (no runtime)

set -uo pipefail

SMOKE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_LIB_DIR="$(cd "$SMOKE_DIR/../.." && pwd)"
REPO_ROOT="$(cd "$RUNNER_LIB_DIR/../../.." && pwd)"

RUNNER="$REPO_ROOT/squads/mmos/scripts/mmos.sh"
TEST_SLUG="smoke-test-mmos-$$"

if [[ ! -f "$RUNNER" ]]; then
  echo "SKIP: mmos.sh not found"
  exit 77
fi

# Portable timeout
if command -v gtimeout &>/dev/null; then
  TIMEOUT_CMD="gtimeout"
elif command -v timeout &>/dev/null 2>&1 && timeout --version &>/dev/null 2>&1; then
  TIMEOUT_CMD="timeout"
else
  TIMEOUT_CMD=""
fi

run_with_timeout() {
  local secs="$1"; shift
  if [[ -n "$TIMEOUT_CMD" ]]; then
    "$TIMEOUT_CMD" "$secs" "$@"
  else
    "$@"
  fi
}

# Run mmos in smoke mode: SMOKE_TEST=true limits to 1 turn, no real LLM calls
output=""
exit_code=0
output=$(
  cd "$REPO_ROOT" && \
  SMOKE_TEST=true \
  PHASE_MAX_TURNS=1 \
  run_with_timeout 60 \
  bash "$RUNNER" "$TEST_SLUG" greenfield 1 2>&1
) || exit_code=$?

# CI environments without LLM runtime: skip gracefully
if echo "$output" | grep -q "No supported runtime found"; then
  # Cleanup any partial state
  rm -rf "$REPO_ROOT/outputs/minds/$TEST_SLUG" 2>/dev/null || true
  echo "SKIP: no LLM runtime available"
  exit 77
fi

# Success criteria: runner initialized (state file created or banner printed)
init_ok=false

# Check 1: State file created
if [[ -f "$REPO_ROOT/outputs/minds/$TEST_SLUG/mmos-state.json" ]]; then
  init_ok=true
fi

# Check 2: Output shows initialization indicators
if [[ "$init_ok" == "false" ]]; then
  if echo "$output" | grep -qiE "(state|initialized|session|Pipeline|Phase)" 2>/dev/null; then
    init_ok=true
  fi
fi

# Check 3: exit 0 always means success
if [[ $exit_code -eq 0 ]]; then
  init_ok=true
fi

# Cleanup
rm -rf "$REPO_ROOT/outputs/minds/$TEST_SLUG" 2>/dev/null || true

if [[ "$init_ok" == "true" ]]; then
  echo "PASS: mmos runner initialized successfully"
  exit 0
else
  echo "FAIL: mmos runner did not initialize (exit $exit_code)"
  echo "--- last 10 lines ---"
  echo "$output" | tail -10
  echo "--- end ---"
  exit 1
fi
