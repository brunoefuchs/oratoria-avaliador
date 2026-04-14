#!/usr/bin/env bash
# ===============================================================================
# TEST: lifecycle hooks (programmatic API) & evaluate_with_threshold
# ===============================================================================
# Story: 115.11 — Lifecycle Hooks & Quality Gates
# Tests: hook registration, execution, graceful failure, exit-1 resilience,
#        evaluate_with_threshold PASS/WARNING/VETO + boundary

set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_LIB_DIR="$(cd "$TESTS_DIR/.." && pwd)"

TEST_DIR=$(mktemp -d)
teardown() { rm -rf "$TEST_DIR"; }
trap teardown EXIT

_TESTS_RUN=0
_TESTS_PASSED=0

assert_eq() {
  local label="$1" expected="$2" actual="$3"
  _TESTS_RUN=$((_TESTS_RUN + 1))
  if [[ "$expected" == "$actual" ]]; then
    _TESTS_PASSED=$((_TESTS_PASSED + 1))
  else
    echo "FAIL: $label -- expected '$expected', got '$actual'" >&2
  fi
}

assert_true() {
  local label="$1" condition="$2"
  _TESTS_RUN=$((_TESTS_RUN + 1))
  if eval "$condition"; then
    _TESTS_PASSED=$((_TESTS_PASSED + 1))
  else
    echo "FAIL: $label -- condition false: $condition" >&2
  fi
}

# Source hooks.sh (contains both YAML-declarative and programmatic API)
source "$RUNNER_LIB_DIR/hooks.sh"

# Source evaluator.sh for evaluate_with_threshold
# Need models.sh and runtime.sh as deps
source "$RUNNER_LIB_DIR/models.sh"
record_metrics() { :; }
METRICS_FILE="$TEST_DIR/metrics.jsonl"
SELECTED_RUNTIME="claude"
LLM_TIMEOUT_SECONDS="5"
RETRY_MAX_ATTEMPTS=1
RETRY_BASE_DELAY_SECONDS=0
SESSION_TRACKING="false"
source "$RUNNER_LIB_DIR/runtime.sh"
source "$RUNNER_LIB_DIR/evaluator.sh"

# ======================================================
# PART 1: Lifecycle Hook Registration & Execution
# ======================================================

# Tracking file for hook invocations
HOOK_LOG="$TEST_DIR/hook-invocations.log"
: > "$HOOK_LOG"

# Define test callback functions
my_session_start_hook() {
  echo "session_start:$1" >> "$HOOK_LOG"
}

my_turn_start_hook() {
  echo "turn_start:$1:$2" >> "$HOOK_LOG"
}

my_turn_end_hook() {
  echo "turn_end:$1:$2:$3" >> "$HOOK_LOG"
}

my_pre_compress_hook() {
  echo "pre_compress:$1" >> "$HOOK_LOG"
}

my_error_hook() {
  echo "error:$1:$2:$3" >> "$HOOK_LOG"
}

my_session_end_hook() {
  echo "session_end:$1:$2" >> "$HOOK_LOG"
}

# ======================================================
# Test 1: Register all 6 hooks
# ======================================================
lifecycle_hook_clear
reg_exit=0
lifecycle_hook_register "on_session_start" "my_session_start_hook" || reg_exit=$?
assert_eq "register on_session_start" "0" "$reg_exit"

reg_exit=0
lifecycle_hook_register "on_turn_start" "my_turn_start_hook" || reg_exit=$?
assert_eq "register on_turn_start" "0" "$reg_exit"

reg_exit=0
lifecycle_hook_register "on_turn_end" "my_turn_end_hook" || reg_exit=$?
assert_eq "register on_turn_end" "0" "$reg_exit"

reg_exit=0
lifecycle_hook_register "on_pre_compress" "my_pre_compress_hook" || reg_exit=$?
assert_eq "register on_pre_compress" "0" "$reg_exit"

reg_exit=0
lifecycle_hook_register "on_error" "my_error_hook" || reg_exit=$?
assert_eq "register on_error" "0" "$reg_exit"

reg_exit=0
lifecycle_hook_register "on_session_end" "my_session_end_hook" || reg_exit=$?
assert_eq "register on_session_end" "0" "$reg_exit"

# ======================================================
# Test 2: Register invalid hook name fails
# ======================================================
reg_exit=0
lifecycle_hook_register "on_invalid" "my_session_start_hook" 2>/dev/null || reg_exit=$?
assert_eq "invalid hook name returns 1" "1" "$reg_exit"

# ======================================================
# Test 3: Register non-function callback fails
# ======================================================
reg_exit=0
lifecycle_hook_register "on_session_start" "nonexistent_function_xyz" 2>/dev/null || reg_exit=$?
assert_eq "non-function callback returns 1" "1" "$reg_exit"

# ======================================================
# Test 4: Fire all 6 hooks and verify invocations
# ======================================================
: > "$HOOK_LOG"

lifecycle_fire_on_session_start "sess-001"
lifecycle_fire_on_turn_start "1" "research"
lifecycle_fire_on_turn_end "1" "research" "PASS"
lifecycle_fire_on_pre_compress "50000"
lifecycle_fire_on_error "transient" "429" "rate limit exceeded"
lifecycle_fire_on_session_end "sess-001" "completed"

assert_true "on_session_start fired" "grep -q 'session_start:sess-001' '$HOOK_LOG'"
assert_true "on_turn_start fired" "grep -q 'turn_start:1:research' '$HOOK_LOG'"
assert_true "on_turn_end fired" "grep -q 'turn_end:1:research:PASS' '$HOOK_LOG'"
assert_true "on_pre_compress fired" "grep -q 'pre_compress:50000' '$HOOK_LOG'"
assert_true "on_error fired" "grep -q 'error:transient:429:rate limit exceeded' '$HOOK_LOG'"
assert_true "on_session_end fired" "grep -q 'session_end:sess-001:completed' '$HOOK_LOG'"

# ======================================================
# Test 5: Multiple callbacks on same hook
# ======================================================
my_second_session_start() {
  echo "second_session_start:$1" >> "$HOOK_LOG"
}

lifecycle_hook_register "on_session_start" "my_second_session_start"

: > "$HOOK_LOG"
lifecycle_fire_on_session_start "sess-002"

count=$(grep -c "sess-002" "$HOOK_LOG")
assert_eq "two callbacks both fired" "2" "$count"

# ======================================================
# Test 6: Graceful failure — hook that does exit 1
# ======================================================
# This is the explicit AC test: hook with exit 1 must NOT crash runner
my_crashing_hook() {
  exit 1
}

lifecycle_hook_clear "on_turn_start"
lifecycle_hook_register "on_turn_start" "my_crashing_hook"

fire_exit=0
lifecycle_fire_on_turn_start "99" "crash-test" 2>/dev/null || fire_exit=$?
assert_eq "exit-1 hook does not block execution" "0" "$fire_exit"

# ======================================================
# Test 7: Hook after crashing hook still fires
# ======================================================
# Register a good hook after the crashing one
my_post_crash_hook() {
  echo "post_crash:$1:$2" >> "$HOOK_LOG"
}

lifecycle_hook_register "on_turn_start" "my_post_crash_hook"

: > "$HOOK_LOG"
lifecycle_fire_on_turn_start "100" "resilience" 2>/dev/null
assert_true "post-crash hook still fires" "grep -q 'post_crash:100:resilience' '$HOOK_LOG'"

# ======================================================
# Test 8: lifecycle_hook_clear removes hooks
# ======================================================
lifecycle_hook_clear "on_turn_start"
: > "$HOOK_LOG"
lifecycle_fire_on_turn_start "101" "cleared"
line_count=$(wc -l < "$HOOK_LOG" | tr -d ' ')
assert_eq "cleared hooks produce no output" "0" "$line_count"

# ======================================================
# Test 9: lifecycle_hook_clear with no arg clears all
# ======================================================
lifecycle_hook_register "on_session_start" "my_session_start_hook"
lifecycle_hook_register "on_error" "my_error_hook"
lifecycle_hook_clear
: > "$HOOK_LOG"
lifecycle_fire_on_session_start "sess-003"
lifecycle_fire_on_error "unknown" "1" "test"
line_count=$(wc -l < "$HOOK_LOG" | tr -d ' ')
assert_eq "clear-all removes all hooks" "0" "$line_count"

# ======================================================
# PART 2: evaluate_with_threshold
# ======================================================

# ======================================================
# Test 10: score > threshold → PASS
# ======================================================
result=$(evaluate_with_threshold "completeness" 85 70 "false" 2>/dev/null)
assert_eq "85 >= 70 is PASS" "PASS" "$result"

# ======================================================
# Test 11: score == threshold → PASS (boundary)
# ======================================================
result=$(evaluate_with_threshold "accuracy" 70 70 "true" 2>/dev/null)
assert_eq "70 == 70 is PASS (boundary)" "PASS" "$result"

# ======================================================
# Test 12: score < threshold, no veto → WARNING
# ======================================================
ewt_exit=0
result=$(evaluate_with_threshold "relevance" 60 70 "false" 2>/dev/null) || ewt_exit=$?
assert_eq "60 < 70 no-veto is WARNING" "WARNING" "$result"
assert_eq "WARNING exit code is 1" "1" "$ewt_exit"

# ======================================================
# Test 13: score < threshold, veto → VETO
# ======================================================
ewt_exit=0
result=$(evaluate_with_threshold "safety" 40 70 "true" 2>/dev/null) || ewt_exit=$?
assert_eq "40 < 70 veto is VETO" "VETO" "$result"
assert_eq "VETO exit code is 2" "2" "$ewt_exit"

# ======================================================
# Test 14: score == threshold with float → PASS (boundary float)
# ======================================================
result=$(evaluate_with_threshold "precision" 72.5 72.5 "true" 2>/dev/null)
assert_eq "72.5 == 72.5 is PASS (float boundary)" "PASS" "$result"

# ======================================================
# Test 15: score just below threshold with float → VETO
# ======================================================
ewt_exit=0
result=$(evaluate_with_threshold "recall" 69.9 70 "true" 2>/dev/null) || ewt_exit=$?
assert_eq "69.9 < 70 veto is VETO" "VETO" "$result"

# ======================================================
# Test 16: score 0, threshold 0 → PASS
# ======================================================
result=$(evaluate_with_threshold "edge" 0 0 "true" 2>/dev/null)
assert_eq "0 == 0 is PASS" "PASS" "$result"

# ======================================================
# Test 17: score 100, threshold 100 → PASS
# ======================================================
result=$(evaluate_with_threshold "max" 100 100 "false" 2>/dev/null)
assert_eq "100 == 100 is PASS" "PASS" "$result"

# ======================================================
# Test 18: PASS exit code is 0
# ======================================================
ewt_exit=0
evaluate_with_threshold "pass-check" 90 50 "true" >/dev/null 2>/dev/null || ewt_exit=$?
assert_eq "PASS exit code is 0" "0" "$ewt_exit"

# ======================================================
# Summary
# ======================================================
if [[ $_TESTS_PASSED -eq $_TESTS_RUN ]]; then
  echo "test-lifecycle-hooks: $_TESTS_PASSED/$_TESTS_RUN passed"
  exit 0
else
  echo "test-lifecycle-hooks: $_TESTS_PASSED/$_TESTS_RUN passed" >&2
  exit 1
fi
