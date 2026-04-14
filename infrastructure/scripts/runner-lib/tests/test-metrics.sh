#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# TEST: metrics.sh — record_metrics, check_cost_cap, cost accumulation
# ═══════════════════════════════════════════════════════════════════════════════
# Story: 101.14 AC7

set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_LIB_DIR="$(cd "$TESTS_DIR/.." && pwd)"
export REPO_ROOT
REPO_ROOT="$(cd "$RUNNER_LIB_DIR/../../.." && pwd)"

# ── Setup ──
TEST_DIR=$(mktemp -d)
export SELECTED_RUNTIME="claude"
export SQUAD_SLUG="test-squad"
export AGENT_SLUG="test-agent"
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

# ── Source modules ──
source "$RUNNER_LIB_DIR/models.sh"
source "$RUNNER_LIB_DIR/metrics.sh"

# Set METRICS_FILE after sourcing (metrics.sh resets it to "")
METRICS_FILE="$TEST_DIR/metrics.jsonl"

# ══════════════════════════════════════════
# Test 1: record_metrics generates valid JSONL
# ══════════════════════════════════════════
: > "$METRICS_FILE"

# Reset cumulative counters
METRICS_TOTAL_INPUT_TOKENS=0
METRICS_TOTAL_OUTPUT_TOKENS=0
METRICS_TOTAL_COST_USD=0
METRICS_TOTAL_DURATION=0
METRICS_CALL_COUNT=0

record_metrics "sonnet" "4000" "2000" "5" "phase_1" "ok" "0" "claude" 2>/dev/null

assert_true "record_metrics creates JSONL file" '[[ -s "$METRICS_FILE" ]]'

# Validate JSONL is valid JSON
first_line=$(head -1 "$METRICS_FILE")
assert_true "JSONL line is valid JSON" 'echo "$first_line" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null'

# Check required fields
has_required=$(echo "$first_line" | python3 -c "
import json, sys
d = json.load(sys.stdin)
required = ['ts','squad','agent','phase','model','runtime','input_tokens','output_tokens','cost_usd','duration_s','status']
missing = [k for k in required if k not in d]
print('ok' if not missing else 'missing:' + ','.join(missing))
")
assert_eq "JSONL has required fields" "ok" "$has_required"

# ══════════════════════════════════════════
# Test 2: check_cost_cap returns 0 below cap
# ══════════════════════════════════════════
exit_code=0
check_cost_cap "100.00" 2>/dev/null || exit_code=$?
assert_eq "check_cost_cap below cap returns 0" "0" "$exit_code"

# ══════════════════════════════════════════
# Test 3: check_cost_cap returns 75 above cap
# ══════════════════════════════════════════
exit_code=0
check_cost_cap "0.000001" 2>/dev/null || exit_code=$?
assert_eq "check_cost_cap above cap returns 75" "75" "$exit_code"

# ══════════════════════════════════════════
# Test 4: check_cost_cap with no cap returns 0
# ══════════════════════════════════════════
exit_code=0
check_cost_cap "" 2>/dev/null || exit_code=$?
assert_eq "check_cost_cap no cap returns 0" "0" "$exit_code"

# ══════════════════════════════════════════
# Test 5: Cost accumulation between phases
# ══════════════════════════════════════════
: > "$METRICS_FILE"
METRICS_TOTAL_COST_USD=0

record_metrics "sonnet" "4000" "2000" "5" "phase_1" "ok" "0" "claude" 2>/dev/null
record_metrics "sonnet" "8000" "4000" "10" "phase_2" "ok" "0" "claude" 2>/dev/null

line_count=$(wc -l < "$METRICS_FILE" | tr -d ' ')
assert_eq "two phases produce two JSONL lines" "2" "$line_count"

# Verify cumulative cost increases
cumulative=$(python3 -c "
import json
lines = [json.loads(l) for l in open('$METRICS_FILE') if l.strip()]
print('ok' if len(lines) == 2 and lines[1]['cumulative_cost_usd'] > lines[0]['cost_usd'] else 'fail')
")
assert_eq "cumulative cost increases across phases" "ok" "$cumulative"

# ══════════════════════════════════════════
# Summary
# ══════════════════════════════════════════
if [[ $_TESTS_PASSED -eq $_TESTS_RUN ]]; then
  echo "test-metrics: $_TESTS_PASSED/$_TESTS_RUN passed"
  exit 0
else
  echo "test-metrics: $_TESTS_PASSED/$_TESTS_RUN passed" >&2
  exit 1
fi
