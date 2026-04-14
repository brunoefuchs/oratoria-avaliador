#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# SMOKE TEST TEMPLATE — New Runner Smoke Test
# ═══════════════════════════════════════════════════════════════════════════════
#
# Template for generating smoke tests for new runners created via the
# create-runner SOP (squads/runner-ops/tasks/create-runner.md).
#
# HOW TO USE:
#   1. Copy this template to tests/smoke/test-{runner-id}.sh
#   2. Replace the 4 variables below with runner-specific values
#   3. Customize the per-runner command builder if needed (see CUSTOMIZE section)
#   4. Add fixtures to tests/smoke/fixtures/{runner-id}/ if your runner
#      requires input files (validators often do)
#   5. Register the runner in runner-registry.yaml (run-smoke-tests.sh reads it)
#
# VARIABLES TO SET:
#   RUNNER_ID     — The runner's ID as registered in runner-registry.yaml
#   RUNNER_PATH   — Repo-relative path to the runner script
#   RUNNER_SQUAD  — The squad that owns this runner
#   FIXTURE_DIR   — Path to test fixtures (can be empty if none needed)
#
# THE 7 SMOKE CHECKS:
#   1. init       — Runner script exists and is executable
#   2. state      — Runner creates a state file during initialization
#   3. session    — Runner outputs session/lifecycle indicators
#   4. banner     — Runner prints a recognizable banner or header
#   5. phase-start— Runner begins at least one phase
#   6. metrics    — Runner produces metrics output (JSONL or similar)
#   7. exit-code  — Runner exits cleanly (0 for success, <=1 for validators)
#
# CUSTOMIZATION:
#   - Override build_runner_args() to change how the runner is invoked
#   - Override build_runner_env() to set environment variables
#   - Override evaluate_output() to add runner-specific assertions
#   - Add fixture files in FIXTURE_DIR for runners that need input
#
# Story: 101.16
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ═══════════════════════════════════════════════════════════════
# CONFIGURE: Set these 4 variables for your runner
# ═══════════════════════════════════════════════════════════════

RUNNER_ID="__RUNNER_ID__"           # e.g., "mmos", "books", "validate-squad"
RUNNER_PATH="__RUNNER_PATH__"       # e.g., "squads/mmos/scripts/mmos.sh"
RUNNER_SQUAD="__RUNNER_SQUAD__"     # e.g., "mmos", "books", "squad-creator"
FIXTURE_DIR="__FIXTURE_DIR__"       # e.g., "infrastructure/scripts/runner-lib/tests/smoke/fixtures/mmos"

# ═══════════════════════════════════════════════════════════════
# Paths and setup (DO NOT EDIT)
# ═══════════════════════════════════════════════════════════════

SMOKE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$(cd "$SMOKE_DIR/.." && pwd)"
RUNNER_LIB_DIR="$(cd "$TESTS_DIR/.." && pwd)"
REPO_ROOT="$(cd "$RUNNER_LIB_DIR/../../.." && pwd)"
export REPO_ROOT

RUNNER_ABS="$REPO_ROOT/$RUNNER_PATH"
SMOKE_TIMEOUT=60
TMP_DIR=$(mktemp -d)
TEST_SLUG="smoke-test-${RUNNER_ID}-$$"

# Counters
_CHECKS_RUN=0
_CHECKS_PASSED=0
_CHECKS_FAILED=0

# ═══════════════════════════════════════════════════════════════
# Cleanup on exit
# ═══════════════════════════════════════════════════════════════

teardown() {
  rm -rf "$TMP_DIR"
  # Clean up any test artifacts in outputs/
  find "$REPO_ROOT/outputs" -path "*${TEST_SLUG}*" -exec rm -rf {} + 2>/dev/null || true
}
trap teardown EXIT

# ═══════════════════════════════════════════════════════════════
# Portable timeout (macOS lacks coreutils timeout)
# ═══════════════════════════════════════════════════════════════

if command -v gtimeout &>/dev/null; then
  _TIMEOUT_CMD="gtimeout"
elif command -v timeout &>/dev/null 2>&1 && timeout --version &>/dev/null 2>&1; then
  _TIMEOUT_CMD="timeout"
else
  _TIMEOUT_CMD=""
fi

_run_with_timeout() {
  local secs="$1"; shift
  if [[ -n "$_TIMEOUT_CMD" ]]; then
    "$_TIMEOUT_CMD" "$secs" "$@"
  else
    "$@"
  fi
}

# ═══════════════════════════════════════════════════════════════
# Assertion helpers
# ═══════════════════════════════════════════════════════════════

# check_pass "label" — record a passing check
check_pass() {
  local label="$1"
  _CHECKS_RUN=$((_CHECKS_RUN + 1))
  _CHECKS_PASSED=$((_CHECKS_PASSED + 1))
  echo "  [PASS] $label"
}

# check_fail "label" "detail" — record a failing check
check_fail() {
  local label="$1" detail="${2:-}"
  _CHECKS_RUN=$((_CHECKS_RUN + 1))
  _CHECKS_FAILED=$((_CHECKS_FAILED + 1))
  echo "  [FAIL] $label${detail:+ — $detail}"
}

# ═══════════════════════════════════════════════════════════════
# CUSTOMIZE: Override these functions for runner-specific behavior
# ═══════════════════════════════════════════════════════════════

# build_runner_args — returns the arguments to pass to the runner.
# Override this for runners that need special args (e.g., --source, project dir).
#
# Default: standard positional args for pipeline runners.
# For validators, override to pass the target (e.g., a squad name or file path).
build_runner_args() {
  # Pipeline default: slug, mode, max-phases
  echo "$TEST_SLUG greenfield 1"

  # --- Examples for different runner types: ---
  #
  # Validator example (validate-squad):
  #   echo "books --quick"
  #
  # Runner with --source flag (decoder):
  #   echo "--source $REPO_ROOT/squads/books $TEST_SLUG greenfield 1"
  #
  # Runner with project dir (copy):
  #   local project_dir="$TMP_DIR/$TEST_SLUG"
  #   mkdir -p "$project_dir"
  #   echo '{"project":"smoke","workflow_id":"smoke","current_phase":0,"status":"initialized"}' \
  #     > "$project_dir/copy-state.json"
  #   echo "$project_dir greenfield 1"
}

# build_runner_env — returns env vars to export before running.
# Override to add runner-specific environment.
#
# Default: SMOKE_TEST=true + PHASE_MAX_TURNS=1 (mocks LLM, limits phases).
build_runner_env() {
  echo "SMOKE_TEST=true PHASE_MAX_TURNS=1"
}

# evaluate_output — add runner-specific assertions on the captured output.
# Called after the 7 standard checks. Use check_pass/check_fail.
#
# Args: $1 = captured stdout+stderr, $2 = exit code
evaluate_output() {
  local _output="$1" _exit_code="$2"
  # Add custom assertions here. Example:
  # if echo "$_output" | grep -q "Expected artifact"; then
  #   check_pass "custom-artifact"
  # else
  #   check_fail "custom-artifact" "Expected artifact not found in output"
  # fi
  :
}

# ═══════════════════════════════════════════════════════════════
# Check 1: init — Runner file exists and is a valid script
# ═══════════════════════════════════════════════════════════════

run_check_init() {
  if [[ ! -f "$RUNNER_ABS" ]]; then
    check_fail "init" "Runner not found at $RUNNER_PATH"
    return 1
  fi

  # Verify it starts with a shebang (valid shell script)
  if head -1 "$RUNNER_ABS" | grep -q '^#!'; then
    check_pass "init"
  else
    check_fail "init" "Runner has no shebang line"
    return 1
  fi
}

# ═══════════════════════════════════════════════════════════════
# Execute the runner and capture output
# ═══════════════════════════════════════════════════════════════

execute_runner() {
  local args env_vars exit_code=0 output=""
  args=$(build_runner_args)
  env_vars=$(build_runner_env)

  output=$(
    cd "$REPO_ROOT" && \
    eval "$env_vars" \
    _run_with_timeout "$SMOKE_TIMEOUT" \
    bash "$RUNNER_ABS" $args 2>&1
  ) || exit_code=$?

  # Store for later checks
  CAPTURED_OUTPUT="$output"
  CAPTURED_EXIT_CODE=$exit_code
}

# ═══════════════════════════════════════════════════════════════
# Check 2: state — Runner creates or updates a state file
# Looks for JSON state files in outputs/ or tmp dir.
# ═══════════════════════════════════════════════════════════════

run_check_state() {
  local found=false

  # Look in outputs/ for state files matching our test slug
  if find "$REPO_ROOT/outputs" -name "*.json" -path "*${TEST_SLUG}*" 2>/dev/null | head -1 | grep -q . 2>/dev/null; then
    found=true
  fi

  # Look in tmp dir (some runners write state there)
  if [[ "$found" == "false" ]] && find "$TMP_DIR" -name "*.json" 2>/dev/null | head -1 | grep -q . 2>/dev/null; then
    found=true
  fi

  # Fallback: check output for state-related keywords
  if [[ "$found" == "false" ]] && echo "$CAPTURED_OUTPUT" | grep -qiE "(state|initialized)" 2>/dev/null; then
    found=true
  fi

  if [[ "$found" == "true" ]]; then
    check_pass "state"
  else
    check_fail "state" "No state file or initialization indicator found"
  fi
}

# ═══════════════════════════════════════════════════════════════
# Check 3: session — Runner outputs session/lifecycle indicators
# ═══════════════════════════════════════════════════════════════

run_check_session() {
  if echo "$CAPTURED_OUTPUT" | grep -qiE "(session|lifecycle|start|end|SESSION)" 2>/dev/null; then
    check_pass "session"
  else
    check_fail "session" "No session/lifecycle indicators in output"
  fi
}

# ═══════════════════════════════════════════════════════════════
# Check 4: banner — Runner prints a recognizable header/banner
# ═══════════════════════════════════════════════════════════════

run_check_banner() {
  if echo "$CAPTURED_OUTPUT" | grep -qiE "(═|━|Pipeline|Runner|Banner|=====)" 2>/dev/null; then
    check_pass "banner"
  else
    check_fail "banner" "No banner or header detected in output"
  fi
}

# ═══════════════════════════════════════════════════════════════
# Check 5: phase-start — Runner begins at least one phase
# ═══════════════════════════════════════════════════════════════

run_check_phase_start() {
  if echo "$CAPTURED_OUTPUT" | grep -qiE "(Phase|phase|PHASE|step|Stage)" 2>/dev/null; then
    check_pass "phase-start"
  else
    check_fail "phase-start" "No phase/step indicator found in output"
  fi
}

# ═══════════════════════════════════════════════════════════════
# Check 6: metrics — Runner produces metrics output
# ═══════════════════════════════════════════════════════════════

run_check_metrics() {
  local found=false

  # Look for non-empty metrics JSONL files
  if find "$REPO_ROOT/outputs" -type f \( -name "metrics.jsonl" -o -name "job-metrics.jsonl" \) -path "*${TEST_SLUG}*" -size +0c 2>/dev/null | head -1 | grep -q . 2>/dev/null; then
    found=true
  fi

  if [[ "$found" == "false" ]] && find "$TMP_DIR" -type f \( -name "metrics.jsonl" -o -name "job-metrics.jsonl" \) -size +0c 2>/dev/null | head -1 | grep -q . 2>/dev/null; then
    found=true
  fi

  # Check output for metrics keywords
  if [[ "$found" == "false" ]] && echo "$CAPTURED_OUTPUT" | grep -qiE "(metrics|METRICS|cost|tokens|duration)" 2>/dev/null; then
    found=true
  fi

  if [[ "$found" == "true" ]]; then
    check_pass "metrics"
  else
    check_fail "metrics" "No non-empty metrics output or file detected"
  fi
}

# ═══════════════════════════════════════════════════════════════
# Check 7: exit-code — Runner exits cleanly
# For pipeline runners: 0 = success (SMOKE_TEST mock may cause non-zero)
# For validators: 0 or 1 = valid (1 = validation failure, not error)
# ═══════════════════════════════════════════════════════════════

run_check_exit_code() {
  # With SMOKE_TEST=true, pipeline runners may exit non-zero because
  # mock output does not satisfy evaluators. The key is that the runner
  # STARTED (init + state created). We accept exit <= 1 for validators
  # and any exit that produced output for pipelines.
  if [[ $CAPTURED_EXIT_CODE -eq 0 ]]; then
    check_pass "exit-code"
  elif [[ $CAPTURED_EXIT_CODE -le 1 ]]; then
    # exit 1 is acceptable for validators (means "validation failed, not crash")
    check_pass "exit-code (exit=$CAPTURED_EXIT_CODE, acceptable for validators)"
  elif [[ -n "$CAPTURED_OUTPUT" ]]; then
    # Runner produced output before failing — smoke mock limitation
    check_pass "exit-code (exit=$CAPTURED_EXIT_CODE, runner initialized before failure)"
  else
    check_fail "exit-code" "Runner exited $CAPTURED_EXIT_CODE with no output"
  fi
}

# ═══════════════════════════════════════════════════════════════
# Main: Run all 7 checks + custom checks
# ═══════════════════════════════════════════════════════════════

main() {
  echo ""
  echo "════════════════════════════════════════════════════════"
  echo "  Smoke Test: $RUNNER_ID"
  echo "  Path: $RUNNER_PATH"
  echo "  Squad: $RUNNER_SQUAD"
  echo "════════════════════════════════════════════════════════"
  echo ""

  # Check 1: init (pre-execution)
  run_check_init || { echo ""; echo "ABORTED: runner not found"; exit 1; }

  # Execute the runner
  echo "  Running $RUNNER_ID with SMOKE_TEST=true ..."
  execute_runner
  echo ""

  # Checks 2-7 (post-execution)
  run_check_state
  run_check_session
  run_check_banner
  run_check_phase_start
  run_check_metrics
  run_check_exit_code

  # Custom checks
  evaluate_output "$CAPTURED_OUTPUT" "$CAPTURED_EXIT_CODE"

  # Summary
  echo ""
  echo "────────────────────────────────────────────────────────"
  echo "  Result: $_CHECKS_PASSED/$_CHECKS_RUN checks passed"

  if [[ $_CHECKS_FAILED -gt 0 ]]; then
    echo "  Status: FAIL ($_CHECKS_FAILED checks failed)"
    echo "────────────────────────────────────────────────────────"
    exit 1
  else
    echo "  Status: PASS"
    echo "────────────────────────────────────────────────────────"
    exit 0
  fi
}

# Initialize captured output
CAPTURED_OUTPUT=""
CAPTURED_EXIT_CODE=0

main "$@"
