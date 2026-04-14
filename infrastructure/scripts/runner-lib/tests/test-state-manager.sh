#!/usr/bin/env bash
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# TEST: state-manager.sh â€” state_init, state_update, state_phase_update
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Story: 101.14 AC6

set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_LIB_DIR="$(cd "$TESTS_DIR/.." && pwd)"
export REPO_ROOT
REPO_ROOT="$(cd "$RUNNER_LIB_DIR/../../.." && pwd)"

# â”€â”€ Setup â”€â”€
TEST_DIR=$(mktemp -d)
teardown() { rm -rf "$TEST_DIR"; }
trap teardown EXIT

_TESTS_RUN=0
_TESTS_PASSED=0

json_read_file() {
  local expr="$1" file="$2"
  if command -v jq >/dev/null 2>&1; then
    jq -r "$expr" "$file" 2>/dev/null
  else
    python3 - "$file" "$expr" <<'PYEOF' 2>/dev/null
import json, sys
with open(sys.argv[1], encoding='utf-8') as fh:
    data = json.load(fh)
expr = sys.argv[2]
paths = {
    '.target': data.get('target', ''),
    '.status': data.get('status', ''),
    '.current_phase': data.get('current_phase', ''),
    '.started_at': data.get('started_at', ''),
    '.phases.phase_1.status': data.get('phases', {}).get('phase_1', {}).get('status', ''),
    '.phases.phase_1.agent': data.get('phases', {}).get('phase_1', {}).get('agent', ''),
}
value = paths.get(expr, '')
if value is None:
    value = ''
print(value, end='')
PYEOF
  fi
}

assert_eq() {
  local label="$1" expected="$2" actual="$3"
  _TESTS_RUN=$((_TESTS_RUN + 1))
  if [[ "$expected" == "$actual" ]]; then
    _TESTS_PASSED=$((_TESTS_PASSED + 1))
  else
    echo "FAIL: $label â€” expected '$expected', got '$actual'" >&2
  fi
}

assert_true() {
  local label="$1" condition="$2"
  _TESTS_RUN=$((_TESTS_RUN + 1))
  if eval "$condition"; then
    _TESTS_PASSED=$((_TESTS_PASSED + 1))
  else
    echo "FAIL: $label â€” condition false: $condition" >&2
  fi
}

# â”€â”€ Source module â”€â”€
source "$RUNNER_LIB_DIR/state-manager.sh"

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Test 1: state_init creates valid JSON state file
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
STATE_FILE="$TEST_DIR/state.json"

state_init "$STATE_FILE" "test-runner" "pipeline"
assert_true "state_init creates file" '[[ -f "$STATE_FILE" ]]'

# Verify it's valid JSON
assert_true "state file is valid JSON" 'python3 -m json.tool "$STATE_FILE" >/dev/null 2>&1'

# Check required fields
target=$(json_read_file '.target' "$STATE_FILE")
assert_eq "state target field" "test-runner" "$target"

status=$(json_read_file '.status' "$STATE_FILE")
assert_eq "state initial status" "initialized" "$status"

phase=$(json_read_file '.current_phase' "$STATE_FILE")
assert_eq "state initial current_phase" "1" "$phase"

assert_true "state has started_at" '[[ -n $(json_read_file ".started_at" "$STATE_FILE") ]]'

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Test 2: state_update persists a field
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
state_update --arg status "running" '.status = $status' "$STATE_FILE"
updated_status=$(json_read_file '.status' "$STATE_FILE")
assert_eq "state_update persists field" "running" "$updated_status"

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Test 3: state_phase_update updates phase
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
state_phase_update "$STATE_FILE" "phase_1" "complete" "agent-x"
phase_status=$(json_read_file '.phases.phase_1.status' "$STATE_FILE")
assert_eq "phase_update sets status" "complete" "$phase_status"

phase_agent=$(json_read_file '.phases.phase_1.agent' "$STATE_FILE")
assert_eq "phase_update sets agent" "agent-x" "$phase_agent"

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Test 4: Idempotency â€” updating same field 2x = last value
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
state_update --arg status "paused" '.status = $status' "$STATE_FILE"
state_update --arg status "resumed" '.status = $status' "$STATE_FILE"
final_status=$(json_read_file '.status' "$STATE_FILE")
assert_eq "idempotent update keeps last value" "resumed" "$final_status"

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Test 5: state_init does not overwrite existing file
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
state_init "$STATE_FILE" "new-runner" "pipeline"
target_after=$(json_read_file '.target' "$STATE_FILE")
assert_eq "state_init does not overwrite existing" "test-runner" "$target_after"

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Test 6: state_validate checks required fields
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
state_validate "$STATE_FILE"
assert_eq "state_validate passes on valid state" "0" "$?"

# Create an invalid state file
echo '{"target":"x"}' > "$TEST_DIR/bad-state.json"
if state_validate "$TEST_DIR/bad-state.json" 2>/dev/null; then
  echo "FAIL: state_validate should fail on missing fields" >&2
  _TESTS_RUN=$((_TESTS_RUN + 1))
else
  _TESTS_RUN=$((_TESTS_RUN + 1))
  _TESTS_PASSED=$((_TESTS_PASSED + 1))
fi

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Summary
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
if [[ $_TESTS_PASSED -eq $_TESTS_RUN ]]; then
  echo "test-state-manager: $_TESTS_PASSED/$_TESTS_RUN passed"
  exit 0
else
  echo "test-state-manager: $_TESTS_PASSED/$_TESTS_RUN passed" >&2
  exit 1
fi
