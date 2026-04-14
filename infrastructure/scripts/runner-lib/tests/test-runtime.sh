#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# TEST: runtime.sh — detect_runtime, run_llm_prompt with mock _exec_runtime
# ═══════════════════════════════════════════════════════════════════════════════
# Story: 101.14 AC5

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

# Source modules
source "$RUNNER_LIB_DIR/models.sh"
source "$RUNNER_LIB_DIR/metrics.sh"
source "$RUNNER_LIB_DIR/runtime.sh"

# Set after sourcing (metrics.sh resets METRICS_FILE)
METRICS_FILE="$TEST_DIR/metrics.jsonl"
SELECTED_RUNTIME="claude"
MODEL="sonnet"
LLM_TIMEOUT_SECONDS="5"
RETRY_MAX_ATTEMPTS=1
SESSION_TRACKING="false"

# ══════════════════════════════════════════
# Test 1: detect_runtime returns valid runtime
# ══════════════════════════════════════════
assert_eq "detect_runtime claude" "claude" "$(detect_runtime claude)"
assert_eq "detect_runtime codex" "codex" "$(detect_runtime codex)"
assert_eq "detect_runtime gemini" "gemini" "$(detect_runtime gemini)"
assert_eq "detect_runtime invalid" "invalid" "$(detect_runtime invalid-rt)"

result=$(detect_runtime auto)
assert_true "detect_runtime auto is valid" '[[ "$result" == "claude" || "$result" == "codex" || "$result" == "gemini" || "$result" == "none" ]]'

# ══════════════════════════════════════════
# Test 2: run_llm_prompt with mock returns output, writes log and metrics
# ══════════════════════════════════════════
_exec_runtime() {
  local model="$1" prompt_file="$2" output_file="$3"
  printf '{"result":"Mock output from %s"}\n' "$model" > "$output_file"
  return 0
}

LOG_FILE="$TEST_DIR/llm.log"
touch "$LOG_FILE"
: > "$METRICS_FILE"

output_file="$TEST_DIR/rlp-output.txt"
exit_code=0
run_llm_prompt "$MODEL" "test prompt" "$LOG_FILE" "test-phase" > "$output_file" 2>/dev/null || exit_code=$?

assert_eq "run_llm_prompt success exit code" "0" "$exit_code"
assert_true "run_llm_prompt writes output" '[[ -s "$output_file" ]]'
assert_true "run_llm_prompt writes log" '[[ -s "$LOG_FILE" ]]'
assert_true "run_llm_prompt writes metrics" '[[ -s "$METRICS_FILE" ]]'

# Verify metrics JSONL is valid JSON
assert_true "metrics JSONL is valid JSON" 'head -1 "$METRICS_FILE" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null'

# ══════════════════════════════════════════
# Test 3: Circuit breaker resets on success
# (run_llm_prompt updates _RLP_CONSECUTIVE_FAILURES in main shell only if not in subshell)
# ══════════════════════════════════════════
CIRCUIT_BREAKER_THRESHOLD=3
_RLP_CONSECUTIVE_FAILURES=2

_exec_runtime() {
  local model="$1" prompt_file="$2" output_file="$3"
  printf '{"result":"Success"}\n' > "$output_file"
  return 0
}

# Run in the main shell via redirect (not subshell) to preserve variable changes
run_llm_prompt "$MODEL" "test" "$LOG_FILE" "cb-test" > "$TEST_DIR/cb.out" 2>/dev/null || true
assert_eq "circuit breaker resets on success" "0" "$_RLP_CONSECUTIVE_FAILURES"

unset CIRCUIT_BREAKER_THRESHOLD

# ══════════════════════════════════════════
# Summary
# ══════════════════════════════════════════
if [[ $_TESTS_PASSED -eq $_TESTS_RUN ]]; then
  echo "test-runtime: $_TESTS_PASSED/$_TESTS_RUN passed"
  exit 0
else
  echo "test-runtime: $_TESTS_PASSED/$_TESTS_RUN passed" >&2
  exit 1
fi
