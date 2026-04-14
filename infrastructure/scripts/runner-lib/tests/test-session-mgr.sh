#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# TEST: session-mgr.sh — session_start, session_end, session_cleanup
# ═══════════════════════════════════════════════════════════════════════════════
# Story: 101.14 AC8

set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_LIB_DIR="$(cd "$TESTS_DIR/.." && pwd)"
export REPO_ROOT
REPO_ROOT="$(cd "$RUNNER_LIB_DIR/../../.." && pwd)"

# ── Setup ──
TEST_DIR=$(mktemp -d)
export RUNNER_STATE_DIR="$TEST_DIR/sessions"
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

# ── Source module ──
source "$RUNNER_LIB_DIR/session-mgr.sh"

# ══════════════════════════════════════════
# Test 1: session_start creates session
# ══════════════════════════════════════════
session_id=$(session_start "test-squad" "phase_1" "test-agent" "sonnet" "claude" "$TEST_DIR/test.log")
assert_true "session_start returns session ID" '[[ -n "$session_id" ]]'

# Verify session file exists
session_file="$RUNNER_STATE_DIR/${session_id}.json"
assert_true "session file created" '[[ -f "$session_file" ]]'

# Verify valid JSON with required fields
status=$(python3 -c "import json; print(json.load(open('$session_file')).get('status',''))")
assert_eq "session initial status is running" "running" "$status"

squad=$(python3 -c "import json; print(json.load(open('$session_file')).get('squad',''))")
assert_eq "session squad field" "test-squad" "$squad"

# ══════════════════════════════════════════
# Test 2: session_end marks completion
# ══════════════════════════════════════════
session_end "$session_id" "0" "500"

end_status=$(python3 -c "import json; print(json.load(open('$session_file')).get('status',''))")
assert_eq "session_end marks completed" "completed" "$end_status"

end_exit=$(python3 -c "import json; print(json.load(open('$session_file')).get('exit_code',''))")
assert_eq "session_end records exit code" "0" "$end_exit"

end_tokens=$(python3 -c "import json; print(json.load(open('$session_file')).get('tokens_estimated',''))")
assert_eq "session_end records tokens" "500" "$end_tokens"

assert_true "session_end sets ended_at" '[[ $(python3 -c "import json; print(json.load(open(\"$session_file\")).get(\"ended_at\",\"null\"))") != "null" ]]'

# ══════════════════════════════════════════
# Test 3: session_end with failure
# ══════════════════════════════════════════
session_id2=$(session_start "test-squad" "phase_2" "agent2" "haiku" "claude" "$TEST_DIR/test2.log")
session_end "$session_id2" "1"

fail_status=$(python3 -c "import json; print(json.load(open('$RUNNER_STATE_DIR/${session_id2}.json')).get('status',''))")
assert_eq "session_end with error marks failed" "failed" "$fail_status"

# ══════════════════════════════════════════
# Test 4: session_cleanup archives old sessions
# ══════════════════════════════════════════
# Set archive threshold to 0 minutes (archive immediately)
export RUNNER_ARCHIVE_AFTER=0

session_cleanup 2>/dev/null

# Both completed/failed sessions should be archived
archived_count=$(find "$RUNNER_STATE_DIR/archive" -name "sess-*.json" 2>/dev/null | wc -l | tr -d ' ')
assert_true "session_cleanup archives completed sessions" '[[ "$archived_count" -ge 1 ]]'

# Active dir should be empty (both sessions ended)
active_count=$(find "$RUNNER_STATE_DIR" -maxdepth 1 -name "sess-*.json" 2>/dev/null | wc -l | tr -d ' ')
assert_eq "no active sessions after cleanup" "0" "$active_count"

# ══════════════════════════════════════════
# Summary
# ══════════════════════════════════════════
if [[ $_TESTS_PASSED -eq $_TESTS_RUN ]]; then
  echo "test-session-mgr: $_TESTS_PASSED/$_TESTS_RUN passed"
  exit 0
else
  echo "test-session-mgr: $_TESTS_PASSED/$_TESTS_RUN passed" >&2
  exit 1
fi
