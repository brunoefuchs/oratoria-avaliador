#!/usr/bin/env bash
# ===============================================================================
# TEST: error classification & circuit breaker integration
# ===============================================================================
# Story: 115.7 — Error Classification & Circuit Breaker
# Tests classify_error(), circuit breaker type-aware increment, and replan_on_error()

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

# Source only models.sh (for resolve_model_alias) and runtime.sh (for classify_error)
source "$RUNNER_LIB_DIR/models.sh"

# Stub metrics to avoid side effects
record_metrics() { :; }
METRICS_FILE="$TEST_DIR/metrics.jsonl"

source "$RUNNER_LIB_DIR/runtime.sh"

SELECTED_RUNTIME="claude"
MODEL="sonnet"
LLM_TIMEOUT_SECONDS="5"
RETRY_MAX_ATTEMPTS=1
RETRY_BASE_DELAY_SECONDS=0
SESSION_TRACKING="false"

# ======================================================
# Test 1: classify_error — transient (429 rate limit)
# ======================================================
err_file="$TEST_DIR/err-429.txt"
echo "Error: 429 Too Many Requests - rate limit exceeded" > "$err_file"
result=$(classify_error "$err_file" 1)
assert_eq "429 classified as transient" "transient" "$result"

# ======================================================
# Test 2: classify_error — transient (timeout)
# ======================================================
err_file="$TEST_DIR/err-timeout.txt"
echo "ERROR: LLM call timed out after 300s" > "$err_file"
result=$(classify_error "$err_file" 124)
assert_eq "timeout exit 124 classified as transient" "transient" "$result"

# ======================================================
# Test 3: classify_error — transient (connection reset)
# ======================================================
err_file="$TEST_DIR/err-connreset.txt"
echo "Error: connection reset by peer ECONNRESET" > "$err_file"
result=$(classify_error "$err_file" 1)
assert_eq "connection reset classified as transient" "transient" "$result"

# ======================================================
# Test 4: classify_error — transient (5xx server error)
# ======================================================
err_file="$TEST_DIR/err-500.txt"
echo "HTTP 503 Service Unavailable - server error" > "$err_file"
result=$(classify_error "$err_file" 1)
assert_eq "503 classified as transient" "transient" "$result"

# ======================================================
# Test 5: classify_error — permanent (401 auth)
# ======================================================
err_file="$TEST_DIR/err-401.txt"
echo "Error: 401 Unauthorized - invalid api key" > "$err_file"
result=$(classify_error "$err_file" 1)
assert_eq "401 classified as permanent" "permanent" "$result"

# ======================================================
# Test 6: classify_error — permanent (400 validation)
# ======================================================
err_file="$TEST_DIR/err-400.txt"
echo "Error: 400 Bad Request - validation error in request body" > "$err_file"
result=$(classify_error "$err_file" 1)
assert_eq "400 classified as permanent" "permanent" "$result"

# ======================================================
# Test 7: classify_error — permanent (404 not found)
# ======================================================
err_file="$TEST_DIR/err-404.txt"
echo "Error: 404 Not Found - resource not found" > "$err_file"
result=$(classify_error "$err_file" 1)
assert_eq "404 classified as permanent" "permanent" "$result"

# ======================================================
# Test 8: classify_error — unknown (generic error)
# ======================================================
err_file="$TEST_DIR/err-unknown.txt"
echo "Something went wrong in an unexpected way" > "$err_file"
result=$(classify_error "$err_file" 1)
assert_eq "generic error classified as unknown" "unknown" "$result"

# ======================================================
# Test 9: classify_error — no file (missing output)
# ======================================================
result=$(classify_error "" 1)
assert_eq "empty file path classified as unknown" "unknown" "$result"

result=$(classify_error "/nonexistent/path/file.txt" 1)
assert_eq "nonexistent file classified as unknown" "unknown" "$result"

# ======================================================
# Test 10: replan_on_error — permanent error aborts
# ======================================================
source "$RUNNER_LIB_DIR/replan.sh"

# Override _get_fallback_runtimes for test isolation
_get_fallback_runtimes() { echo ""; }
_get_default_model() { echo "sonnet"; }

err_file="$TEST_DIR/err-perm-replan.txt"
echo "Error: 401 Unauthorized" > "$err_file"
replan_exit=0
replan_on_error "$err_file" 1 "test-phase" "" "$TEST_DIR/replan.log" > /dev/null 2>/dev/null || replan_exit=$?
assert_eq "replan_on_error aborts on permanent error" "1" "$replan_exit"

# ======================================================
# Test 11: replan_on_error — transient returns 2 (retry signal)
# ======================================================
err_file="$TEST_DIR/err-trans-replan.txt"
echo "Error: 429 rate limit" > "$err_file"
replan_exit=0
replan_on_error "$err_file" 1 "test-phase" "" "$TEST_DIR/replan.log" > /dev/null 2>/dev/null || replan_exit=$?
assert_eq "replan_on_error signals retry on transient" "2" "$replan_exit"

# ======================================================
# Test 12: Circuit breaker — permanent error increments by 3
# ======================================================
_RLP_CONSECUTIVE_FAILURES=0
CIRCUIT_BREAKER_THRESHOLD=10

# Simulate what the POST-LLM guard does with a permanent error
tmp_perm="$TEST_DIR/cb-perm.txt"
echo "Error: 401 Unauthorized" > "$tmp_perm"
_error_type=$(classify_error "$tmp_perm" 1)
case "$_error_type" in
  permanent) _RLP_CONSECUTIVE_FAILURES=$((_RLP_CONSECUTIVE_FAILURES + 3)) ;;
  *) _RLP_CONSECUTIVE_FAILURES=$((_RLP_CONSECUTIVE_FAILURES + 1)) ;;
esac
assert_eq "permanent error increments breaker by 3" "3" "$_RLP_CONSECUTIVE_FAILURES"

# ======================================================
# Test 13: Circuit breaker — transient error increments by 1
# ======================================================
_RLP_CONSECUTIVE_FAILURES=0
tmp_trans="$TEST_DIR/cb-trans.txt"
echo "Error: 429 rate limit" > "$tmp_trans"
_error_type=$(classify_error "$tmp_trans" 1)
case "$_error_type" in
  permanent) _RLP_CONSECUTIVE_FAILURES=$((_RLP_CONSECUTIVE_FAILURES + 3)) ;;
  *) _RLP_CONSECUTIVE_FAILURES=$((_RLP_CONSECUTIVE_FAILURES + 1)) ;;
esac
assert_eq "transient error increments breaker by 1" "1" "$_RLP_CONSECUTIVE_FAILURES"

# ======================================================
# Summary
# ======================================================
if [[ $_TESTS_PASSED -eq $_TESTS_RUN ]]; then
  echo "test-error-classification: $_TESTS_PASSED/$_TESTS_RUN passed"
  exit 0
else
  echo "test-error-classification: $_TESTS_PASSED/$_TESTS_RUN passed" >&2
  exit 1
fi
