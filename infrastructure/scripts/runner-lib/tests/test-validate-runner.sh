#!/usr/bin/env bash
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# TEST: validate-runner.sh â€” smoke test warning/error/pass behavior
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Story: 101.16 AC7, AC8, AC9

set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_LIB_DIR="$(cd "$TESTS_DIR/.." && pwd)"
REPO_ROOT="$(cd "$RUNNER_LIB_DIR/../../.." && pwd)"

TEST_DIR=$(mktemp -d)
RUNNER_ID="validate-runner-fixture"
RUNNER_FIXTURE_DIR="$RUNNER_LIB_DIR/tests/smoke/fixtures/$RUNNER_ID"
RUNNER_REL_PATH="infrastructure/scripts/runner-lib/tests/smoke/fixtures/$RUNNER_ID/${RUNNER_ID}.sh"
RUNNER_FILE="$REPO_ROOT/$RUNNER_REL_PATH"
SMOKE_SCRIPT="$RUNNER_LIB_DIR/tests/smoke/test-${RUNNER_ID}.sh"

teardown() {
  rm -rf "$TEST_DIR"
  rm -rf "$RUNNER_FIXTURE_DIR"
  rm -f "$SMOKE_SCRIPT"
}
trap teardown EXIT

export LC_ALL=C

_TESTS_RUN=0
_TESTS_PASSED=0

json_read_file() {
  local file="$1" expr="$2"
  python3 - "$file" "$expr" <<'PYEOF' 2>/dev/null
import json, sys
with open(sys.argv[1], encoding='utf-8') as fh:
    data = json.load(fh)
expr = sys.argv[2]
checks = data[0].get('checks', [])
if expr == 'missing_passed':
    value = next((c.get('passed') for c in checks if c.get('name') == 'smoke_test_exists'), '')
elif expr == 'missing_severity':
    value = next((c.get('severity') for c in checks if c.get('name') == 'smoke_test_exists'), '')
elif expr == 'warning_count':
    value = len(data[0].get('warnings', []))
elif expr == 'error_passed':
    value = next((c.get('passed') for c in checks if c.get('name') == 'smoke_test_passes'), '')
elif expr == 'error_severity':
    value = next((c.get('severity') for c in checks if c.get('name') == 'smoke_test_passes'), '')
elif expr == 'error_count':
    value = len(data[0].get('errors', []))
elif expr == 'pass_value':
    value = next((c.get('passed') for c in checks if c.get('name') == 'smoke_test_passes'), '')
else:
    value = ''
if isinstance(value, bool):
    print('true' if value else 'false', end='')
else:
    print(value, end='')
PYEOF
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

mkdir -p "$RUNNER_FIXTURE_DIR"

cat > "$RUNNER_FILE" <<EOF
#!/usr/bin/env bash
source "$RUNNER_LIB_DIR/pipeline-bootstrap.sh"
RUNNER_LIB_RUNTIME=true
trap 'true' EXIT
state_init "\$STATE_FILE" "fixture" "runner"
state_update "\$STATE_FILE" '.'
state_phase_update "\$STATE_FILE" "0_init" "complete"
METRICS_FILE="/tmp/fixture-metrics.jsonl"
record_metrics "fixture" 0 0 0 0 0 success
SESSION_TRACKING=true
session_start "fixture" "phase" "agent" "model" "runtime" "/tmp/fixture.log"
session_end "fixture" 0
check_cost_cap || true
filter_llm_output "fixture"
cascade_run "fixture prompt" "/tmp/fixture.log" "fixture-phase" || true
hooks_load "$REPO_ROOT/squads/books" || true
evaluate_phase_output "/tmp/fixture.json" "fixture-phase" "/tmp/fixture.log" || true
read_focused_context "$REPO_ROOT" "fixture-phase" || true
EOF
chmod +x "$RUNNER_FILE"

run_validate_runner() {
  local json_file="$1"
  local exit_code=0

  LC_ALL=C bash "$RUNNER_LIB_DIR/validate-runner.sh" "$RUNNER_REL_PATH" --json > "$json_file" 2>/dev/null || exit_code=$?
  echo "$exit_code"
}

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Test 1: Missing smoke test => warning only, exit 0
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
JSON1="$TEST_DIR/result-missing.json"
rm -f "$SMOKE_SCRIPT"
exit_code=$(run_validate_runner "$JSON1")

assert_eq "missing smoke test exit code" "0" "$exit_code"
warning_passed=$(json_read_file "$JSON1" 'missing_passed')
warning_severity=$(json_read_file "$JSON1" 'missing_severity')
warning_count=$(json_read_file "$JSON1" 'warning_count')
assert_eq "missing smoke test check fails" "false" "$warning_passed"
assert_eq "missing smoke test severity warning" "warning" "$warning_severity"
assert_true "missing smoke test recorded as warning" '[[ "$warning_count" -ge 1 ]]'

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Test 2: Failing smoke test => error, exit 1
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
cat > "$SMOKE_SCRIPT" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
chmod +x "$SMOKE_SCRIPT"

JSON2="$TEST_DIR/result-fail.json"
exit_code=$(run_validate_runner "$JSON2")

assert_eq "failing smoke test exit code" "1" "$exit_code"
error_passed=$(json_read_file "$JSON2" 'error_passed')
error_severity=$(json_read_file "$JSON2" 'error_severity')
error_count=$(json_read_file "$JSON2" 'error_count')
assert_eq "failing smoke test check fails" "false" "$error_passed"
assert_eq "failing smoke test severity error" "error" "$error_severity"
assert_true "failing smoke test recorded as error" '[[ "$error_count" -ge 1 ]]'

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Test 3: Passing smoke test => exit 0 and passing check
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
cat > "$SMOKE_SCRIPT" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$SMOKE_SCRIPT"

JSON3="$TEST_DIR/result-pass.json"
exit_code=$(run_validate_runner "$JSON3")

assert_eq "passing smoke test exit code" "0" "$exit_code"
pass_value=$(json_read_file "$JSON3" 'pass_value')
assert_eq "passing smoke test check passes" "true" "$pass_value"

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Summary
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
if [[ $_TESTS_PASSED -eq $_TESTS_RUN ]]; then
  echo "test-validate-runner: $_TESTS_PASSED/$_TESTS_RUN passed"
  exit 0
else
  echo "test-validate-runner: $_TESTS_PASSED/$_TESTS_RUN passed" >&2
  exit 1
fi
