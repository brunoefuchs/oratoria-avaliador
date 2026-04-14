#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# TEST: runtime.sh guards — cost cap, circuit breaker, truncate, filter
# ═══════════════════════════════════════════════════════════════════════════════
# Story: 101.14 AC11

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
    echo "FAIL: $label — expected '$expected', got '$actual'" >&2
  fi
}

assert_true() {
  local label="$1" condition="$2"
  _TESTS_RUN=$((_TESTS_RUN + 1))
  if eval "$condition"; then
    _TESTS_PASSED=$((_TESTS_PASSED + 1))
  else
    echo "FAIL: $label — condition false: $condition" >&2
  fi
}

# Track _exec_runtime calls via file (immune to subshell)
EXEC_LOG="$TEST_DIR/exec-calls.log"
PROMPT_SIZE_LOG="$TEST_DIR/prompt-sizes.log"
: > "$EXEC_LOG"
: > "$PROMPT_SIZE_LOG"

source "$RUNNER_LIB_DIR/models.sh"
source "$RUNNER_LIB_DIR/metrics.sh"
source "$RUNNER_LIB_DIR/headless-guard.sh"
source "$RUNNER_LIB_DIR/runtime.sh"

SELECTED_RUNTIME="claude"
MODEL="sonnet"
LLM_TIMEOUT_SECONDS="5"
RETRY_MAX_ATTEMPTS=1
METRICS_FILE="$TEST_DIR/metrics.jsonl"
SESSION_TRACKING="false"

_exec_runtime() {
  local model="$1" prompt_file="$2" output_file="$3"
  echo "call" >> "$EXEC_LOG"
  wc -c < "$prompt_file" | tr -d ' ' >> "$PROMPT_SIZE_LOG"
  # Write output with some CLI noise for filter tests
  python3 - "$output_file" << 'PYEOF'
import json, sys
payload = "\n".join([
    "Real content line 1",
    "Warning: Skipping extension",
    "Real content line 2",
    "Path not in workspace",
    "YOLO mode is enabled",
    "clean payload",
])
with open(sys.argv[1], "w") as fh:
    json.dump({"result": payload}, fh)
    fh.write("\n")
PYEOF
  return 0
}

LOG="$TEST_DIR/guard.log"

# ══════════════════════════════════════════
# Test 1: COST_CAP_GUARD=true + budget exceeded — returns 3, skips exec
# ══════════════════════════════════════════
check_cost_cap() { return 75; }
COST_CAP_GUARD=true
: > "$EXEC_LOG"

exit_code=0
run_llm_prompt "$MODEL" "prompt" "$LOG" "guard-cost" > /dev/null 2>/dev/null || exit_code=$?
exec_count=$(wc -l < "$EXEC_LOG" | tr -d ' ')

assert_eq "cost cap exceeded returns 3" "3" "$exit_code"
assert_eq "cost cap exceeded skips _exec_runtime" "0" "$exec_count"
unset -f check_cost_cap
unset COST_CAP_GUARD

# ══════════════════════════════════════════
# Test 2: COST_CAP_GUARD=true + budget ok — executes normally
# ══════════════════════════════════════════
check_cost_cap() { return 0; }
COST_CAP_GUARD=true
: > "$EXEC_LOG"
: > "$METRICS_FILE"

run_llm_prompt "$MODEL" "prompt" "$LOG" "guard-ok" > /dev/null 2>/dev/null
exec_count=$(wc -l < "$EXEC_LOG" | tr -d ' ')

assert_true "cost cap ok calls _exec_runtime" '[[ "$exec_count" -ge 1 ]]'
unset -f check_cost_cap
unset COST_CAP_GUARD

# ══════════════════════════════════════════
# Test 3: CIRCUIT_BREAKER_THRESHOLD=3 + 3 failures — returns 2
# ══════════════════════════════════════════
CIRCUIT_BREAKER_THRESHOLD=3
_RLP_CONSECUTIVE_FAILURES=3
: > "$EXEC_LOG"

exit_code=0
run_llm_prompt "$MODEL" "prompt" "$LOG" "guard-cb" > /dev/null 2>/dev/null || exit_code=$?
exec_count=$(wc -l < "$EXEC_LOG" | tr -d ' ')

assert_eq "circuit breaker returns 2" "2" "$exit_code"
assert_eq "circuit breaker skips _exec_runtime" "0" "$exec_count"

# ══════════════════════════════════════════
# Test 4: CIRCUIT_BREAKER + success → resets _RLP_CONSECUTIVE_FAILURES to 0
# ══════════════════════════════════════════
_RLP_CONSECUTIVE_FAILURES=2
: > "$METRICS_FILE"

run_llm_prompt "$MODEL" "prompt" "$LOG" "guard-reset" > /dev/null 2>/dev/null
assert_eq "success resets consecutive failures" "0" "$_RLP_CONSECUTIVE_FAILURES"

unset CIRCUIT_BREAKER_THRESHOLD

# ══════════════════════════════════════════
# Test 5: HEADLESS_TRUNCATE_BYTES=100 — prompt truncated before _exec_runtime
# ══════════════════════════════════════════
HEADLESS_TRUNCATE_BYTES=100
: > "$PROMPT_SIZE_LOG"
: > "$METRICS_FILE"

long_prompt=$(printf 'A%.0s' {1..250})
run_llm_prompt "$MODEL" "$long_prompt" "$LOG" "guard-truncate" > /dev/null 2>/dev/null

prompt_bytes=$(head -1 "$PROMPT_SIZE_LOG" 2>/dev/null || echo 999)
assert_true "truncate reduces prompt below 250 bytes" '[[ "$prompt_bytes" -lt 250 ]]'

unset HEADLESS_TRUNCATE_BYTES

# ══════════════════════════════════════════
# Test 6: HEADLESS_FILTER=true — CLI noise filtered from output
# ══════════════════════════════════════════
HEADLESS_FILTER=true
: > "$METRICS_FILE"

filtered_file="$TEST_DIR/filtered.out"
run_llm_prompt "$MODEL" "prompt" "$LOG" "guard-filter" > "$filtered_file" 2>/dev/null
filtered_output=$(cat "$filtered_file")

assert_true "filter removes Warning: Skipping extension" '! grep -q "Warning: Skipping extension" "$filtered_file"'
assert_true "filter removes YOLO banner" '! grep -q "YOLO mode is enabled" "$filtered_file"'
assert_true "filter preserves clean payload" 'grep -q "clean payload" "$filtered_file"'

unset HEADLESS_FILTER

# ══════════════════════════════════════════
# Test 7: No env vars — no guards activate (backward compat)
# ══════════════════════════════════════════
unset COST_CAP_GUARD CIRCUIT_BREAKER_THRESHOLD HEADLESS_TRUNCATE_BYTES HEADLESS_FILTER
_RLP_CONSECUTIVE_FAILURES=0
: > "$EXEC_LOG"
: > "$METRICS_FILE"

plain_file="$TEST_DIR/plain.out"
run_llm_prompt "$MODEL" "plain prompt" "$LOG" "guard-plain" > "$plain_file" 2>/dev/null
exec_count=$(wc -l < "$EXEC_LOG" | tr -d ' ')

assert_eq "no-guard path executes _exec_runtime" "1" "$exec_count"
# Without HEADLESS_FILTER, raw output including noise is returned
assert_true "no-guard keeps raw output (noise present)" 'grep -q "Warning: Skipping extension" "$plain_file"'

# ══════════════════════════════════════════
# Summary
# ══════════════════════════════════════════
if [[ $_TESTS_PASSED -eq $_TESTS_RUN ]]; then
  echo "test-guards: $_TESTS_PASSED/$_TESTS_RUN passed"
  exit 0
else
  echo "test-guards: $_TESTS_PASSED/$_TESTS_RUN passed" >&2
  exit 1
fi
