#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# TEST: replan.sh — run_llm_prompt_with_replan bridge
# ═══════════════════════════════════════════════════════════════════════════════
# Story: 101.14 AC10

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

# Track calls via file (immune to subshell)
CALL_LOG="$TEST_DIR/call-log.txt"
METRICS_LOG="$TEST_DIR/replan-metrics.log"
: > "$CALL_LOG"
: > "$METRICS_LOG"

record_metrics() {
  local model="$1" _input="$2" _output="$3" _duration="$4" phase="$5"
  printf '%s|%s\n' "$model" "$phase" >> "$METRICS_LOG"
}

source "$RUNNER_LIB_DIR/models.sh"
source "$RUNNER_LIB_DIR/replan.sh"

_get_fallback_runtimes() { echo "gemini"; }
_get_default_model() {
  if [[ "$1" == "gemini" ]]; then echo "gemini-3.1-pro-preview"; else echo "sonnet"; fi
}

# Mock run_llm_prompt using a scenario variable
run_llm_prompt() {
  local model="$1" _prompt="$2" _log_file="$3" phase_label="${4:-unknown}"
  echo "${SELECTED_RUNTIME}:${model}:${phase_label}" >> "$CALL_LOG"
  record_metrics "$model" 0 0 0 "$phase_label"

  case "${REPLAN_TEST_SCENARIO:-}" in
    disabled-no-retry)  printf 'primary failure'; return 1 ;;
    primary-success)    printf 'primary success'; return 0 ;;
    model-switch-success)
      if [[ "$model" == "opus" ]]; then printf 'primary failure'; return 1; fi
      printf 'model switch recovered'; return 0
      ;;
    all-fail-skip)   printf 'still failing'; return 1 ;;
    max-one-strategy) printf 'still failing'; return 1 ;;
  esac
  printf 'unexpected'; return 1
}

SELECTED_RUNTIME="claude"
LOG_FILE="$TEST_DIR/replan.log"

# ══════════════════════════════════════════
# Test 1: PHASE_REPLAN=false — delegates once, no retry
# ══════════════════════════════════════════
REPLAN_TEST_SCENARIO="disabled-no-retry"
PHASE_REPLAN=false
REPLAN_MAX_ATTEMPTS=3
: > "$CALL_LOG"

output_file="$TEST_DIR/test1.out"
exit_code=0
run_llm_prompt_with_replan "opus" "prompt" "$LOG_FILE" "phase-a" > "$output_file" 2>/dev/null || exit_code=$?

call_count=$(wc -l < "$CALL_LOG" | tr -d ' ')
first_call=$(head -1 "$CALL_LOG" 2>/dev/null || echo "")
output=$(cat "$output_file")

assert_eq "replan disabled preserves failure exit" "1" "$exit_code"
assert_eq "replan disabled calls only once" "1" "$call_count"
assert_eq "replan disabled keeps phase label" "claude:opus:phase-a" "$first_call"
assert_eq "replan disabled returns primary output" "primary failure" "$output"

# ══════════════════════════════════════════
# Test 2: PHASE_REPLAN=true + primary success — no strategies tried
# ══════════════════════════════════════════
REPLAN_TEST_SCENARIO="primary-success"
PHASE_REPLAN=true
: > "$CALL_LOG"

output=$(run_llm_prompt_with_replan "opus" "prompt" "$LOG_FILE" "phase-b" 2>/dev/null)
call_count=$(wc -l < "$CALL_LOG" | tr -d ' ')

assert_eq "primary success output" "primary success" "$output"
assert_eq "primary success has one call" "1" "$call_count"

# ══════════════════════════════════════════
# Test 3: model_switch success recovers
# ══════════════════════════════════════════
REPLAN_TEST_SCENARIO="model-switch-success"
: > "$CALL_LOG"

output=$(run_llm_prompt_with_replan "opus" "prompt" "$LOG_FILE" "phase-c" 2>/dev/null)
call_count=$(wc -l < "$CALL_LOG" | tr -d ' ')
second_call=$(sed -n '2p' "$CALL_LOG" 2>/dev/null || echo "")

assert_eq "model switch recovered" "model switch recovered" "$output"
assert_eq "model switch has two calls" "2" "$call_count"
assert_eq "second call uses fallback model" "claude:sonnet:replan-phase-c-model_switch" "$second_call"

# ══════════════════════════════════════════
# Test 4: all fail → skip_degraded returns 0 with PHASES_DEGRADED
# ══════════════════════════════════════════
REPLAN_TEST_SCENARIO="all-fail-skip"
REPLAN_MAX_ATTEMPTS=3
PHASES_DEGRADED=""
export PHASES_DEGRADED
: > "$CALL_LOG"
: > "$METRICS_LOG"

output_file="$TEST_DIR/test4.out"
run_llm_prompt_with_replan "opus" "prompt" "$LOG_FILE" "phase-d" > "$output_file" 2>/dev/null
output=$(cat "$output_file")

assert_true "all fail returns DEGRADED marker" '[[ "$output" == DEGRADED:* ]]'
assert_eq "degraded phase tracked" "phase-d" "$PHASES_DEGRADED"
assert_true "skip_degraded metric recorded" 'grep -q "opus|replan-phase-d-skip_degraded" "$METRICS_LOG"'

# ══════════════════════════════════════════
# Test 5: REPLAN_MAX_ATTEMPTS=1 — max 1 strategy after primary
# ══════════════════════════════════════════
REPLAN_TEST_SCENARIO="max-one-strategy"
REPLAN_MAX_ATTEMPTS=1
: > "$CALL_LOG"

exit_code=0
run_llm_prompt_with_replan "opus" "prompt" "$LOG_FILE" "phase-e" > /dev/null 2>/dev/null || exit_code=$?
call_count=$(wc -l < "$CALL_LOG" | tr -d ' ')

assert_eq "max attempts 1 returns failure" "1" "$exit_code"
assert_eq "max attempts 1: primary + 1 strategy = 2 calls" "2" "$call_count"

# ══════════════════════════════════════════
# Test 6: Replan attempts record metrics with replan- label
# ══════════════════════════════════════════
REPLAN_TEST_SCENARIO="all-fail-skip"
REPLAN_MAX_ATTEMPTS=3
PHASES_DEGRADED=""
export PHASES_DEGRADED
: > "$METRICS_LOG"

run_llm_prompt_with_replan "opus" "prompt" "$LOG_FILE" "metrics-test" > /dev/null 2>/dev/null
assert_true "metrics contain replan- label" 'grep -q "replan-" "$METRICS_LOG"'

# ══════════════════════════════════════════
# Summary
# ══════════════════════════════════════════
if [[ $_TESTS_PASSED -eq $_TESTS_RUN ]]; then
  echo "test-replan: $_TESTS_PASSED/$_TESTS_RUN passed"
  exit 0
else
  echo "test-replan: $_TESTS_PASSED/$_TESTS_RUN passed" >&2
  exit 1
fi
