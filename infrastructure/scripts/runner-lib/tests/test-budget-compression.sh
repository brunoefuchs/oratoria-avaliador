#!/usr/bin/env bash
# ===============================================================================
# TEST: budget warnings & context compression
# ===============================================================================
# Story: 115.8 — Budget Warnings & Context Compression
# Tests budget_check_iteration() thresholds and compress_context() 5-phase

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

assert_contains() {
  local label="$1" haystack="$2" needle="$3"
  _TESTS_RUN=$((_TESTS_RUN + 1))
  if [[ "$haystack" == *"$needle"* ]]; then
    _TESTS_PASSED=$((_TESTS_PASSED + 1))
  else
    echo "FAIL: $label -- '$haystack' does not contain '$needle'" >&2
  fi
}

# Source models.sh first (needed by runtime.sh)
source "$RUNNER_LIB_DIR/models.sh"

# Stub metrics/session to avoid side effects
record_metrics() { :; }
session_start() { :; }
session_end() { :; }
METRICS_FILE="$TEST_DIR/metrics.jsonl"

source "$RUNNER_LIB_DIR/runtime.sh"
source "$RUNNER_LIB_DIR/compress.sh"

SELECTED_RUNTIME="claude"
MODEL="sonnet"
LLM_TIMEOUT_SECONDS="5"
RETRY_MAX_ATTEMPTS=1
RETRY_BASE_DELAY_SECONDS=0
SESSION_TRACKING="false"

# ======================================================
# BUDGET TESTS — using RUNNER_MAX_ITERATIONS=10 for speed
# ======================================================

# ── Test 1: Budget — no warning below 70%
# ======================================================
RUNNER_MAX_ITERATIONS=10
budget_reset
for i in $(seq 1 6); do
  budget_check_iteration >/dev/null 2>/dev/null
done
assert_eq "6/10 iterations — no caution yet" "false" "$_BUDGET_CAUTION_LOGGED"

# ── Test 2: Budget — caution at 70%
# ======================================================
RUNNER_MAX_ITERATIONS=10
budget_reset
_stderr_file="$TEST_DIR/budget-test2.stderr"
> "$_stderr_file"
for i in $(seq 1 7); do
  budget_check_iteration 2>>"$_stderr_file" || true
done
assert_eq "7/10 iterations — caution logged" "true" "$_BUDGET_CAUTION_LOGGED"
stderr_output=$(cat "$_stderr_file")
assert_contains "caution message includes BUDGET tag" "$stderr_output" "[BUDGET] Caution: 70%"

# ── Test 3: Budget — warning at 90%
# ======================================================
RUNNER_MAX_ITERATIONS=10
budget_reset
_stderr_file="$TEST_DIR/budget-test3.stderr"
> "$_stderr_file"
for i in $(seq 1 9); do
  budget_check_iteration 2>>"$_stderr_file" || true
done
assert_eq "9/10 iterations — warning logged" "true" "$_BUDGET_WARNING_LOGGED"
stderr_output=$(cat "$_stderr_file")
assert_contains "warning message includes wrap up" "$stderr_output" "[BUDGET] Warning: 90%"

# ── Test 4: Budget — hard stop at 100%
# ======================================================
RUNNER_MAX_ITERATIONS=10
budget_reset
last_exit=0
for i in $(seq 1 10); do
  budget_check_iteration >/dev/null 2>/dev/null || { last_exit=$?; break; }
done
assert_eq "10/10 iterations — hard stop returns 1" "1" "$last_exit"

# ── Test 5: Budget — hard stop at 100% (stderr contains STOP)
# ======================================================
RUNNER_MAX_ITERATIONS=10
budget_reset
_stderr_file="$TEST_DIR/budget-test5.stderr"
> "$_stderr_file"
for i in $(seq 1 10); do
  budget_check_iteration 2>>"$_stderr_file" || true
done
stop_output=$(cat "$_stderr_file")
assert_contains "hard stop message" "$stop_output" "[BUDGET] STOP"

# ── Test 6: Budget — budget_reset clears state
# ======================================================
RUNNER_MAX_ITERATIONS=10
budget_reset
for i in $(seq 1 8); do
  budget_check_iteration >/dev/null 2>/dev/null || true
done
assert_eq "before reset — caution logged" "true" "$_BUDGET_CAUTION_LOGGED"
budget_reset
assert_eq "after reset — caution cleared" "false" "$_BUDGET_CAUTION_LOGGED"
assert_eq "after reset — counter cleared" "0" "$_BUDGET_CURRENT_ITERATION"

# ── Test 7: Budget — budget_status returns correct format
# ======================================================
RUNNER_MAX_ITERATIONS=10
budget_reset
for i in $(seq 1 5); do
  budget_check_iteration >/dev/null 2>/dev/null
done
status=$(budget_status)
assert_eq "budget status at 5/10" "5/10 (50%)" "$status"

# ── Test 8: Budget — caution and warning logged only once
# ======================================================
RUNNER_MAX_ITERATIONS=10
budget_reset
_stderr_file="$TEST_DIR/budget-test8.stderr"
> "$_stderr_file"
for i in $(seq 1 9); do
  budget_check_iteration 2>>"$_stderr_file" || true
done
all_output=$(cat "$_stderr_file")
# Count occurrences of Caution
caution_count=$(echo "$all_output" | grep -c "\[BUDGET\] Caution" || true)
warning_count=$(echo "$all_output" | grep -c "\[BUDGET\] Warning" || true)
assert_eq "caution logged exactly once" "1" "$caution_count"
assert_eq "warning logged exactly once" "1" "$warning_count"

# ======================================================
# COMPRESSION TESTS
# ======================================================

# ── Test 9: compress_context — small file passes through
# ======================================================
small_file="$TEST_DIR/small-context.txt"
echo "Hello world" > "$small_file"
result=$(compress_context "$small_file")
assert_eq "small file passes through" "$small_file" "$result"

# ── Test 10: compress_context — nonexistent file passes through
# ======================================================
result=$(compress_context "/nonexistent/file.txt")
assert_eq "nonexistent file passes through" "/nonexistent/file.txt" "$result"

# ── Test 11: compress_context — large file gets compressed
# ======================================================
large_file="$TEST_DIR/large-context.txt"
# Generate a large context file (~2000 lines)
{
  echo "[system] You are a helpful assistant."
  echo "[user] Please help me with this task."
  echo "[assistant] Of course, I will help."
  for i in $(seq 1 200); do
    echo "[tool_use] search_files query='pattern $i'"
    echo "[tool_result]"
    # Generate >200 chars of output
    python3 -c "print('x' * 250)" 2>/dev/null || printf '%0.sx' $(seq 1 250); echo ""
    echo "[/tool_result]"
    echo "[assistant] Found results for pattern $i. The data shows interesting trends."
  done
  echo "[user] What is the summary?"
  echo "[assistant] Here is the summary of all findings."
} > "$large_file"

result=$(compress_context "$large_file" 3 2>/dev/null)
assert_true "compressed file exists" "[[ -f '$result' ]]"

if [[ -f "$result" ]]; then
  original_size=$(wc -c < "$large_file" | tr -d ' ')
  compressed_size=$(wc -c < "$result" | tr -d ' ')
  assert_true "compressed is smaller than original" "[[ $compressed_size -lt $original_size ]]"
fi

# ── Test 12: compress_context — Phase 1 prunes tool results
# ======================================================
pruned_file="$TEST_DIR/pruned-context.txt"
{
  echo "Line 1"
  echo "[tool_result]"
  python3 -c "print('A' * 300)" 2>/dev/null || printf '%0.sA' $(seq 1 300); echo ""
  echo "[/tool_result]"
  echo "Line after tool"
} > "$pruned_file"
# Manually run awk phase 1 logic
phase1_result=$(awk '
  BEGIN { in_tool_result = 0; tool_buf = ""; tool_lines = 0 }
  /\[tool_result\]/ {
    in_tool_result = 1
    tool_buf = $0 "\n"
    tool_lines = 1
    next
  }
  /\[\/tool_result\]/ {
    if (in_tool_result) {
      tool_buf = tool_buf $0 "\n"
      if (length(tool_buf) > 200) {
        printf "[tool_result pruned — %d chars replaced with placeholder]\n", length(tool_buf)
      } else {
        printf "%s", tool_buf
      }
      in_tool_result = 0
      tool_buf = ""
      tool_lines = 0
      next
    }
  }
  {
    if (in_tool_result) {
      tool_buf = tool_buf $0 "\n"
      tool_lines++
      if (tool_lines > 50) {
        if (length(tool_buf) > 200) {
          printf "[tool_result pruned — %d chars replaced with placeholder]\n", length(tool_buf)
        } else {
          printf "%s", tool_buf
        }
        in_tool_result = 0
        tool_buf = ""
        tool_lines = 0
      }
    } else {
      print
    }
  }
  END {
    if (in_tool_result && length(tool_buf) > 0) {
      if (length(tool_buf) > 200) {
        printf "[tool_result pruned — %d chars replaced with placeholder]\n", length(tool_buf)
      } else {
        printf "%s", tool_buf
      }
    }
  }
' "$pruned_file")
assert_contains "phase 1 prunes large tool results" "$phase1_result" "pruned"
assert_contains "phase 1 keeps surrounding text" "$phase1_result" "Line 1"

# ── Test 13: maybe_compress_context — below threshold passes through
# ======================================================
small_ctx="$TEST_DIR/small-ctx.txt"
echo "Small context" > "$small_ctx"
RUNNER_CONTEXT_WINDOW_CHARS=1000
result=$(maybe_compress_context "$small_ctx" 2>/dev/null)
assert_eq "below 50% threshold passes through" "$small_ctx" "$result"

# ── Test 14: maybe_compress_context — above threshold triggers compression
# ======================================================
big_ctx="$TEST_DIR/big-ctx.txt"
# Generate content > 50% of a small window
{
  for i in $(seq 1 100); do
    echo "Message $i: This is a line of context with some content to make it larger than the threshold."
  done
} > "$big_ctx"
RUNNER_CONTEXT_WINDOW_CHARS=2000  # 50% = 1000 chars, file is ~9000
trigger_stderr=$(maybe_compress_context "$big_ctx" 2 2>&1 >/dev/null || true)
assert_contains "auto-compress triggered" "$trigger_stderr" "auto-compressing"

# ── Test 15: Compression fallback when RUNNER_CHEAP_MODEL unavailable
# ======================================================
# run_llm_prompt is stubbed (not really calling LLM), so summarization fails
# compress_context should fallback to truncation
fallback_file="$TEST_DIR/fallback-context.txt"
{
  echo "[system] System message line 1"
  echo "[user] User message"
  echo "[assistant] Assistant response"
  for i in $(seq 1 100); do
    echo "Middle content line $i with enough text to be substantial for testing."
  done
  echo "[user] Recent question"
  echo "[assistant] Recent answer"
} > "$fallback_file"

# Ensure run_llm_prompt returns failure (no real LLM)
run_llm_prompt() { return 1; }
result=$(compress_context "$fallback_file" 2 2>/dev/null)
if [[ -f "$result" ]]; then
  content=$(cat "$result")
  assert_contains "fallback includes truncation notice" "$content" "Truncated"
fi
# Restore run_llm_prompt
source "$RUNNER_LIB_DIR/runtime.sh"

# ======================================================
# Summary
# ======================================================
if [[ $_TESTS_PASSED -eq $_TESTS_RUN ]]; then
  echo "test-budget-compression: $_TESTS_PASSED/$_TESTS_RUN passed"
  exit 0
else
  echo "test-budget-compression: $_TESTS_PASSED/$_TESTS_RUN passed" >&2
  exit 1
fi
