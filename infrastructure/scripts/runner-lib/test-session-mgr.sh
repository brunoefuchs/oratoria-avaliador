#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER-LIB — Integration Tests for RUNNER-1.2 Session Manager
# ═══════════════════════════════════════════════════════════════
# Tests session lifecycle, policy enforcement, CLI routing.
#
# Usage: bash infrastructure/scripts/runner-lib/test-session-mgr.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_TMP="$(mktemp -d)"
PASS=0
FAIL=0

cleanup() { rm -rf "$TEST_TMP"; }
trap cleanup EXIT

# Override session dir to test temp
export RUNNER_STATE_DIR="$TEST_TMP/sessions"
export RUNNER_MAX_CONCURRENT=0
export RUNNER_ARCHIVE_AFTER=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { PASS=$((PASS + 1)); echo -e "  ${GREEN}✓${NC} $1"; }
fail() { FAIL=$((FAIL + 1)); echo -e "  ${RED}✗${NC} $1"; }

echo "═══════════════════════════════════════════════════════"
echo "  RUNNER-1.2 Session Manager — Integration Tests"
echo "═══════════════════════════════════════════════════════"
echo ""

# Source runner-lib
source "$SCRIPT_DIR/loader.sh"

# ─────────────────────────────────────────────────────────────
# TEST GROUP 1: Session Lifecycle
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}1. Session Lifecycle${NC}"

# 1a. Start a session
SID=$(session_start "mmos" "phase_3" "tim" "haiku" "claude" "$TEST_TMP/test.log" 2>/dev/null)
if [[ -n "$SID" && "$SID" == sess-* ]]; then
  ok "session_start returns valid ID: $SID"
else
  fail "session_start should return sess-* ID (got: $SID)"
fi

# 1b. Session file exists
if [[ -f "$RUNNER_STATE_DIR/$SID.json" ]]; then
  ok "Session file created at $RUNNER_STATE_DIR/$SID.json"
else
  fail "Session file should exist"
fi

# 1c. Session status is running
STATUS=$(python3 -c "import json; print(json.load(open('$RUNNER_STATE_DIR/$SID.json')).get('status'))" 2>/dev/null)
if [[ "$STATUS" == "running" ]]; then
  ok "Session status is 'running'"
else
  fail "Session status should be 'running' (got: $STATUS)"
fi

# 1d. Session fields are correct
SQUAD=$(python3 -c "import json; print(json.load(open('$RUNNER_STATE_DIR/$SID.json')).get('squad'))" 2>/dev/null)
if [[ "$SQUAD" == "mmos" ]]; then
  ok "Session squad is 'mmos'"
else
  fail "Session squad should be 'mmos' (got: $SQUAD)"
fi

# 1e. End session with success
session_end "$SID" 0 5000 2>/dev/null
STATUS=$(python3 -c "import json; print(json.load(open('$RUNNER_STATE_DIR/$SID.json')).get('status'))" 2>/dev/null)
if [[ "$STATUS" == "completed" ]]; then
  ok "session_end marks status 'completed'"
else
  fail "Status should be 'completed' (got: $STATUS)"
fi

# 1f. Exit code recorded
EXIT_CODE=$(python3 -c "import json; print(json.load(open('$RUNNER_STATE_DIR/$SID.json')).get('exit_code'))" 2>/dev/null)
if [[ "$EXIT_CODE" == "0" ]]; then
  ok "Exit code 0 recorded"
else
  fail "Exit code should be 0 (got: $EXIT_CODE)"
fi

# 1g. Tokens estimated recorded
TOKENS=$(python3 -c "import json; print(json.load(open('$RUNNER_STATE_DIR/$SID.json')).get('tokens_estimated'))" 2>/dev/null)
if [[ "$TOKENS" == "5000" ]]; then
  ok "Tokens estimated (5000) recorded"
else
  fail "Tokens should be 5000 (got: $TOKENS)"
fi

# 1h. End session with failure
SID2=$(session_start "books" "phase_5" "orch" "opus" "claude" "$TEST_TMP/test2.log" 2>/dev/null)
session_end "$SID2" 1 2>/dev/null
STATUS2=$(python3 -c "import json; print(json.load(open('$RUNNER_STATE_DIR/$SID2.json')).get('status'))" 2>/dev/null)
if [[ "$STATUS2" == "failed" ]]; then
  ok "session_end with exit_code=1 marks 'failed'"
else
  fail "Status should be 'failed' (got: $STATUS2)"
fi

echo ""

# ─────────────────────────────────────────────────────────────
# TEST GROUP 2: Session List
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}2. Session List${NC}"

# Create a few more sessions
SID3=$(session_start "copy" "phase_1" "writer" "sonnet" "claude" "$TEST_TMP/test3.log" 2>/dev/null)

LIST_OUTPUT=$(session_list 2>/dev/null)
if echo "$LIST_OUTPUT" | grep -q "mmos"; then
  ok "session_list shows mmos session"
else
  fail "session_list should show mmos session"
fi

if echo "$LIST_OUTPUT" | grep -q "copy"; then
  ok "session_list shows copy session"
else
  fail "session_list should show copy session"
fi

LINE_COUNT=$(echo "$LIST_OUTPUT" | wc -l | tr -d ' ')
if [[ "$LINE_COUNT" -ge 4 ]]; then  # header + separator + at least 2 rows
  ok "session_list has header + rows ($LINE_COUNT lines)"
else
  fail "session_list should have >= 4 lines (got: $LINE_COUNT)"
fi

session_end "$SID3" 0 2>/dev/null

echo ""

# ─────────────────────────────────────────────────────────────
# TEST GROUP 3: Session Info
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}3. Session Info${NC}"

INFO_OUTPUT=$(session_info "$SID" 2>/dev/null)
if echo "$INFO_OUTPUT" | grep -q "mmos"; then
  ok "session_info shows squad name"
else
  fail "session_info should show squad name"
fi

if echo "$INFO_OUTPUT" | grep -q "phase_3"; then
  ok "session_info shows phase"
else
  fail "session_info should show phase"
fi

if echo "$INFO_OUTPUT" | grep -q "completed"; then
  ok "session_info shows status"
else
  fail "session_info should show status"
fi

echo ""

# ─────────────────────────────────────────────────────────────
# TEST GROUP 4: Session Kill
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}4. Session Kill${NC}"

# Start a background process to simulate a real session
sleep 300 &
SLEEP_PID=$!

SID4=$(session_start "sinkra" "phase_7" "qa" "haiku" "claude" "$TEST_TMP/test4.log" 2>/dev/null)
# Patch the PID in the session file to point to our sleep process
python3 -c "
import json
f = '$RUNNER_STATE_DIR/$SID4.json'
d = json.load(open(f))
d['pid'] = $SLEEP_PID
json.dump(d, open(f, 'w'), indent=2)
" 2>/dev/null

session_kill "$SID4" 2>/dev/null
STATUS4=$(python3 -c "import json; print(json.load(open('$RUNNER_STATE_DIR/$SID4.json')).get('status'))" 2>/dev/null)
if [[ "$STATUS4" == "killed" ]]; then
  ok "session_kill marks status 'killed'"
else
  fail "Status should be 'killed' (got: $STATUS4)"
fi

EXIT4=$(python3 -c "import json; print(json.load(open('$RUNNER_STATE_DIR/$SID4.json')).get('exit_code'))" 2>/dev/null)
if [[ "$EXIT4" == "143" ]]; then
  ok "session_kill records exit_code 143 (SIGTERM)"
else
  fail "Exit code should be 143 (got: $EXIT4)"
fi

# Verify the sleep process was actually killed
sleep 0.1
if kill -0 "$SLEEP_PID" 2>/dev/null; then
  fail "Sleep process should have been killed"
  kill "$SLEEP_PID" 2>/dev/null  # cleanup
else
  ok "Background process actually terminated by SIGTERM"
fi

# Kill already non-running session should fail
if session_kill "$SID4" 2>/dev/null; then
  fail "Killing non-running session should return 1"
else
  ok "session_kill rejects non-running session"
fi

echo ""

# ─────────────────────────────────────────────────────────────
# TEST GROUP 5: Policy — max_concurrent
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}5. Policy: max_concurrent${NC}"

# Set max_concurrent to 2
export RUNNER_MAX_CONCURRENT=2

# Start 2 sessions (one already running from SID — wait, SID was ended)
# Clean up and start fresh
rm -rf "$RUNNER_STATE_DIR"
export RUNNER_STATE_DIR="$TEST_TMP/sessions-policy"

SID_P1=$(session_start "sq1" "p1" "a1" "h" "c" "$TEST_TMP/p1.log" 2>/dev/null)
SID_P2=$(session_start "sq2" "p2" "a2" "h" "c" "$TEST_TMP/p2.log" 2>/dev/null)

if [[ -n "$SID_P1" && -n "$SID_P2" ]]; then
  ok "2 sessions started within max_concurrent=2"
else
  fail "Should allow 2 sessions (got: P1=$SID_P1, P2=$SID_P2)"
fi

# Third should be blocked
SID_P3=$(session_start "sq3" "p3" "a3" "h" "c" "$TEST_TMP/p3.log" 2>/dev/null)
rc=$?
if [[ "$rc" -ne 0 || -z "$SID_P3" ]]; then
  ok "3rd session blocked by max_concurrent=2"
else
  fail "3rd session should be blocked (got: $SID_P3)"
fi

# End one, then 3rd should work
session_end "$SID_P1" 0 2>/dev/null
SID_P3=$(session_start "sq3" "p3" "a3" "h" "c" "$TEST_TMP/p3.log" 2>/dev/null)
if [[ -n "$SID_P3" ]]; then
  ok "After ending 1 session, new session allowed"
else
  fail "Should allow new session after ending one"
fi

# Reset
export RUNNER_MAX_CONCURRENT=0
session_end "$SID_P2" 0 2>/dev/null
session_end "$SID_P3" 0 2>/dev/null

echo ""

# ─────────────────────────────────────────────────────────────
# TEST GROUP 6: Cleanup / Archive
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}6. Cleanup / Archive${NC}"

export RUNNER_STATE_DIR="$TEST_TMP/sessions-cleanup"
export RUNNER_ARCHIVE_AFTER=0  # archive immediately

SID_C1=$(session_start "cq1" "p1" "a" "h" "c" "$TEST_TMP/c1.log" 2>/dev/null)
session_end "$SID_C1" 0 2>/dev/null

# Sleep 1s to ensure the session is "old enough" (archive_after=0)
sleep 1

session_cleanup 2>/dev/null

if [[ -f "$RUNNER_STATE_DIR/archive/$SID_C1.json" ]]; then
  ok "Completed session archived"
else
  fail "Session should be moved to archive dir"
fi

if [[ ! -f "$RUNNER_STATE_DIR/$SID_C1.json" ]]; then
  ok "Session removed from active dir"
else
  fail "Session should not remain in active dir after archive"
fi

echo ""

# ─────────────────────────────────────────────────────────────
# TEST GROUP 7: CLI (runner-cli.sh)
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}7. CLI Interface${NC}"

CLI="$SCRIPT_DIR/runner-cli.sh"

VERSION=$(bash "$CLI" version 2>/dev/null)
if [[ "$VERSION" == *"1.0.0"* ]]; then
  ok "runner version shows 1.0.0"
else
  fail "runner version should show 1.0.0 (got: $VERSION)"
fi

HELP=$(bash "$CLI" help 2>/dev/null)
if echo "$HELP" | grep -q "sessions"; then
  ok "runner help mentions sessions"
else
  fail "runner help should mention sessions"
fi

if echo "$HELP" | grep -q "cost"; then
  ok "runner help mentions cost"
else
  fail "runner help should mention cost"
fi

echo ""

# ─────────────────────────────────────────────────────────────
# TEST GROUP 8: Loader Integration
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}8. Loader Integration${NC}"

if [[ "$RUNNER_LIB_SESSION" == "true" ]]; then
  ok "loader.sh sets RUNNER_LIB_SESSION=true"
else
  fail "loader.sh should set RUNNER_LIB_SESSION=true"
fi

for fn in session_start session_end session_list session_kill session_log session_info session_cleanup; do
  if declare -f "$fn" >/dev/null 2>&1; then
    ok "Function $fn() available"
  else
    fail "Function $fn() should be available"
  fi
done

echo ""

# ─────────────────────────────────────────────────────────────
# TEST GROUP 9: Edge Cases
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}9. Edge Cases${NC}"

# Non-existent session
if session_info "sess-nonexistent" 2>/dev/null; then
  fail "session_info on nonexistent should fail"
else
  ok "session_info rejects nonexistent session"
fi

if session_kill "sess-nonexistent" 2>/dev/null; then
  fail "session_kill on nonexistent should fail"
else
  ok "session_kill rejects nonexistent session"
fi

if session_log "sess-nonexistent" 2>/dev/null; then
  fail "session_log on nonexistent should fail"
else
  ok "session_log rejects nonexistent session"
fi

if session_end "sess-nonexistent" 0 2>/dev/null; then
  fail "session_end on nonexistent should fail"
else
  ok "session_end rejects nonexistent session"
fi

echo ""

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
TOTAL=$((PASS + FAIL))
echo "═══════════════════════════════════════════════════════"
if [[ "$FAIL" -eq 0 ]]; then
  echo -e "  ${GREEN}${BOLD}ALL $TOTAL TESTS PASSED${NC}"
else
  echo -e "  ${RED}${BOLD}$FAIL/$TOTAL TESTS FAILED${NC}"
fi
echo "═══════════════════════════════════════════════════════"

exit "$FAIL"
