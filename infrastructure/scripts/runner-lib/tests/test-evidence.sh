#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# TEST: evidence.sh + state_reconcile — Story 115.12
# ═══════════════════════════════════════════════════════════════════════════════
# Scenarios: state clean/drift/corrupt, evidence report generation,
#            OUTPUT_DIR non-writable fallback

set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_LIB_DIR="$(cd "$TESTS_DIR/.." && pwd)"
export REPO_ROOT
REPO_ROOT="$(cd "$RUNNER_LIB_DIR/../../.." && pwd)"

# ── Setup ──
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

assert_false() {
  local label="$1" condition="$2"
  _TESTS_RUN=$((_TESTS_RUN + 1))
  if ! eval "$condition"; then
    _TESTS_PASSED=$((_TESTS_PASSED + 1))
  else
    echo "FAIL: $label — expected false: $condition" >&2
  fi
}

# ── Source modules ──
source "$RUNNER_LIB_DIR/state-manager.sh"
source "$RUNNER_LIB_DIR/evidence.sh"

# ═══════════════════════════════════════════════════════════════
# Test 1: state_reconcile — CLEAN state (no artifacts, valid JSON)
# ═══════════════════════════════════════════════════════════════
STATE_FILE="$TEST_DIR/clean-state.json"
state_init "$STATE_FILE" "test-runner" "pipeline"
result=$(state_reconcile "$STATE_FILE" 2>/dev/null)
assert_eq "state_reconcile CLEAN on valid empty state" "CLEAN" "$result"

# ═══════════════════════════════════════════════════════════════
# Test 2: state_reconcile — CORRUPT (missing file)
# ═══════════════════════════════════════════════════════════════
result=$(state_reconcile "$TEST_DIR/nonexistent.json" 2>/dev/null || true)
assert_eq "state_reconcile CORRUPT on missing file" "CORRUPT" "$result"

# ═══════════════════════════════════════════════════════════════
# Test 3: state_reconcile — CORRUPT (invalid JSON)
# ═══════════════════════════════════════════════════════════════
echo "not json {{{" > "$TEST_DIR/bad.json"
result=$(state_reconcile "$TEST_DIR/bad.json" 2>/dev/null || true)
assert_eq "state_reconcile CORRUPT on invalid JSON" "CORRUPT" "$result"

# ═══════════════════════════════════════════════════════════════
# Test 4: state_reconcile — CORRUPT (missing required fields)
# ═══════════════════════════════════════════════════════════════
echo '{"target":"x"}' > "$TEST_DIR/incomplete.json"
result=$(state_reconcile "$TEST_DIR/incomplete.json" 2>/dev/null || true)
assert_eq "state_reconcile CORRUPT on incomplete state" "CORRUPT" "$result"

# ═══════════════════════════════════════════════════════════════
# Test 5: state_reconcile — DRIFT (missing artifact)
# ═══════════════════════════════════════════════════════════════
DRIFT_STATE="$TEST_DIR/drift-state.json"
state_init "$DRIFT_STATE" "drift-runner" "pipeline"
state_add_artifact "$DRIFT_STATE" "$TEST_DIR/nonexistent-artifact.txt"
result=$(state_reconcile "$DRIFT_STATE" 2>/dev/null || true)
assert_eq "state_reconcile DRIFT on missing artifact" "DRIFT" "$result"

# ═══════════════════════════════════════════════════════════════
# Test 6: state_reconcile — CLEAN with existing artifact
# ═══════════════════════════════════════════════════════════════
CLEAN_ART_STATE="$TEST_DIR/clean-art-state.json"
state_init "$CLEAN_ART_STATE" "clean-art-runner" "pipeline"
echo "hello world" > "$TEST_DIR/real-artifact.txt"
state_add_artifact "$CLEAN_ART_STATE" "$TEST_DIR/real-artifact.txt"
result=$(state_reconcile "$CLEAN_ART_STATE" 2>/dev/null)
assert_eq "state_reconcile CLEAN with existing artifact" "CLEAN" "$result"

# ═══════════════════════════════════════════════════════════════
# Test 7: evidence_record + evidence_report generates valid JSON
# ═══════════════════════════════════════════════════════════════
export OUTPUT_DIR="$TEST_DIR/output"
mkdir -p "$OUTPUT_DIR"

evidence_init
evidence_record "phase_1" "model loaded" "model loaded successfully" "PASS"
evidence_record "phase_2" "output generated" "output file created" "PASS"
evidence_deviation "phase_2" "inline" "minor format issue corrected"
evidence_report

assert_true "evidence report file exists" '[[ -f "$OUTPUT_DIR/execution-evidence.json" ]]'
assert_true "evidence report is valid JSON" 'python3 -m json.tool "$OUTPUT_DIR/execution-evidence.json" >/dev/null 2>&1'

# Verify content
if command -v jq >/dev/null 2>&1; then
  entry_count=$(jq '.summary.total_entries' "$OUTPUT_DIR/execution-evidence.json")
  dev_count=$(jq '.summary.total_deviations' "$OUTPUT_DIR/execution-evidence.json")
  assert_eq "evidence report has 2 entries" "2" "$entry_count"
  assert_eq "evidence report has 1 deviation" "1" "$dev_count"
else
  entry_count=$(python3 -c "import json; d=json.load(open('$OUTPUT_DIR/execution-evidence.json')); print(d['summary']['total_entries'])")
  dev_count=$(python3 -c "import json; d=json.load(open('$OUTPUT_DIR/execution-evidence.json')); print(d['summary']['total_deviations'])")
  assert_eq "evidence report has 2 entries" "2" "$entry_count"
  assert_eq "evidence report has 1 deviation" "1" "$dev_count"
fi

# ═══════════════════════════════════════════════════════════════
# Test 8: evidence_report — OUTPUT_DIR non-writable fallback
# ═══════════════════════════════════════════════════════════════
export OUTPUT_DIR="$TEST_DIR/readonly-dir"
mkdir -p "$OUTPUT_DIR"
chmod 444 "$OUTPUT_DIR"

evidence_init
evidence_record "phase_1" "test" "test" "PASS"

# Should return 1 (warning) but NOT exit the script (non-blocking)
if evidence_report 2>/dev/null; then
  _TESTS_RUN=$((_TESTS_RUN + 1))
  echo "FAIL: evidence_report should return 1 on non-writable dir" >&2
else
  _TESTS_RUN=$((_TESTS_RUN + 1))
  _TESTS_PASSED=$((_TESTS_PASSED + 1))
fi

# Restore permissions for cleanup
chmod 755 "$OUTPUT_DIR"

# ═══════════════════════════════════════════════════════════════
# Test 9: evidence_report — OUTPUT_DIR unset fallback
# ═══════════════════════════════════════════════════════════════
unset OUTPUT_DIR
evidence_init
evidence_record "phase_1" "test" "test" "PASS"
if evidence_report 2>/dev/null; then
  _TESTS_RUN=$((_TESTS_RUN + 1))
  echo "FAIL: evidence_report should return 1 when OUTPUT_DIR unset" >&2
else
  _TESTS_RUN=$((_TESTS_RUN + 1))
  _TESTS_PASSED=$((_TESTS_PASSED + 1))
fi

# ═══════════════════════════════════════════════════════════════
# Test 10: evidence_deviation records architectural severity
# ═══════════════════════════════════════════════════════════════
export OUTPUT_DIR="$TEST_DIR/output2"
mkdir -p "$OUTPUT_DIR"

evidence_init
evidence_deviation "phase_3" "architectural" "schema migration required"
evidence_report

assert_true "evidence report with deviation exists" '[[ -f "$OUTPUT_DIR/execution-evidence.json" ]]'
if command -v jq >/dev/null 2>&1; then
  severity=$(jq -r '.deviations[0].severity' "$OUTPUT_DIR/execution-evidence.json")
  assert_eq "deviation severity is architectural" "architectural" "$severity"
else
  severity=$(python3 -c "import json; d=json.load(open('$OUTPUT_DIR/execution-evidence.json')); print(d['deviations'][0]['severity'])")
  assert_eq "deviation severity is architectural" "architectural" "$severity"
fi

# ═══════════════════════════════════════════════════════════════
# Test 11: bootstrap phase helpers (integration)
# ═══════════════════════════════════════════════════════════════
export OUTPUT_DIR="$TEST_DIR/output3"
mkdir -p "$OUTPUT_DIR"
RUNNER_LIB_EVIDENCE=true

source "$RUNNER_LIB_DIR/pipeline-bootstrap.sh"

evidence_init
bootstrap_phase_start "build" "compiling assets"
bootstrap_phase_end "build" "PASS" "all assets compiled"
evidence_report

assert_true "bootstrap phase evidence file exists" '[[ -f "$OUTPUT_DIR/execution-evidence.json" ]]'
if command -v jq >/dev/null 2>&1; then
  count=$(jq '.summary.total_entries' "$OUTPUT_DIR/execution-evidence.json")
  assert_eq "bootstrap generated 2 evidence entries" "2" "$count"
else
  count=$(python3 -c "import json; d=json.load(open('$OUTPUT_DIR/execution-evidence.json')); print(d['summary']['total_entries'])")
  assert_eq "bootstrap generated 2 evidence entries" "2" "$count"
fi

# ═══════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════
if [[ $_TESTS_PASSED -eq $_TESTS_RUN ]]; then
  echo "test-evidence: $_TESTS_PASSED/$_TESTS_RUN passed"
  exit 0
else
  echo "test-evidence: $_TESTS_PASSED/$_TESTS_RUN passed" >&2
  exit 1
fi
