#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# TEST: cascade.sh — classify_turn() smart model routing
# ═══════════════════════════════════════════════════════════════════════════════
# Story: 115.9 — Smart Model Routing Enhancement
# Tests: classify_turn() classification logic, smart_route() integration,
#        RUNNER_SMART_ROUTING toggle, PHASE_CASCADE precedence.

set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_LIB_DIR="$(cd "$TESTS_DIR/.." && pwd)"

TEST_DIR=$(mktemp -d)
teardown() { rm -rf "$TEST_DIR"; }
trap 'echo "test-smart-routing: CRASHED at line $LINENO (exit $?)" >&2; teardown' ERR
trap teardown EXIT

export LC_ALL=C

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

# ── Source only classify_turn (no runtime dependency needed) ──
# We source cascade.sh but stub _exec_runtime for smart_route tests
source "$RUNNER_LIB_DIR/cascade.sh"
_EXEC_RUNTIME_CALLED=""
_EXEC_RUNTIME_MODEL=""
_exec_runtime() {
  _EXEC_RUNTIME_MODEL="$1"
  _EXEC_RUNTIME_CALLED="true"
  # Write dummy output
  echo "ok" > "$3"
  return 0
}

# ═══════════════════════════════════════════════════════════════
# classify_turn() tests
# ═══════════════════════════════════════════════════════════════

# T1: Simple greeting → simple
echo "oi" > "$TEST_DIR/t1.txt"
result=$(classify_turn "$TEST_DIR/t1.txt")
assert_eq "T1: 'oi' is simple" "simple" "$result"

# T2: Simple question → simple
echo "como vai?" > "$TEST_DIR/t2.txt"
result=$(classify_turn "$TEST_DIR/t2.txt")
assert_eq "T2: 'como vai?' is simple" "simple" "$result"

# T3: Complex keyword 'implement' → complex
echo "implemente auth" > "$TEST_DIR/t3.txt"
result=$(classify_turn "$TEST_DIR/t3.txt")
assert_eq "T3: 'implemente auth' is complex (implement keyword)" "complex" "$result"

# T4: Complex keyword 'debug' → complex
echo "debug this function" > "$TEST_DIR/t4.txt"
result=$(classify_turn "$TEST_DIR/t4.txt")
assert_eq "T4: 'debug this function' is complex" "complex" "$result"

# T5: Complex keyword 'test' → complex
echo "test the api endpoint" > "$TEST_DIR/t5.txt"
result=$(classify_turn "$TEST_DIR/t5.txt")
assert_eq "T5: 'test the api' is complex" "complex" "$result"

# T6: Complex keyword 'refactor' → complex
echo "refactor this code" > "$TEST_DIR/t6.txt"
result=$(classify_turn "$TEST_DIR/t6.txt")
assert_eq "T6: 'refactor this code' is complex" "complex" "$result"

# T7: Complex keyword 'architecture' → complex
echo "explain the architecture" > "$TEST_DIR/t7.txt"
result=$(classify_turn "$TEST_DIR/t7.txt")
assert_eq "T7: 'architecture' keyword is complex" "complex" "$result"

# T8: Complex keyword 'analyze' → complex
echo "analyze the logs" > "$TEST_DIR/t8.txt"
result=$(classify_turn "$TEST_DIR/t8.txt")
assert_eq "T8: 'analyze' keyword is complex" "complex" "$result"

# T9: Complex keyword 'create' → complex
echo "create a new module" > "$TEST_DIR/t9.txt"
result=$(classify_turn "$TEST_DIR/t9.txt")
assert_eq "T9: 'create' keyword is complex" "complex" "$result"

# T10: Complex keyword 'design' → complex
echo "design the database schema" > "$TEST_DIR/t10.txt"
result=$(classify_turn "$TEST_DIR/t10.txt")
assert_eq "T10: 'design' keyword is complex" "complex" "$result"

# T11: Complex keyword 'evaluate' → complex
echo "evaluate the options" > "$TEST_DIR/t11.txt"
result=$(classify_turn "$TEST_DIR/t11.txt")
assert_eq "T11: 'evaluate' keyword is complex" "complex" "$result"

# T12: Complex keyword 'validate' → complex
echo "validate the input" > "$TEST_DIR/t12.txt"
result=$(classify_turn "$TEST_DIR/t12.txt")
assert_eq "T12: 'validate' keyword is complex" "complex" "$result"

# T13: Complex keyword 'deploy' → complex
echo "deploy to production" > "$TEST_DIR/t13.txt"
result=$(classify_turn "$TEST_DIR/t13.txt")
assert_eq "T13: 'deploy' keyword is complex" "complex" "$result"

# T14: Complex keyword 'migrate' → complex
echo "migrate the database" > "$TEST_DIR/t14.txt"
result=$(classify_turn "$TEST_DIR/t14.txt")
assert_eq "T14: 'migrate' keyword is complex" "complex" "$result"

# T15: Backticks → complex
echo 'run `npm install`' > "$TEST_DIR/t15.txt"
result=$(classify_turn "$TEST_DIR/t15.txt")
assert_eq "T15: backticks are complex" "complex" "$result"

# T16: URL → complex
echo "check https://example.com" > "$TEST_DIR/t16.txt"
result=$(classify_turn "$TEST_DIR/t16.txt")
assert_eq "T16: URL is complex" "complex" "$result"

# T17: Long text (> 160 chars) → complex
printf '%0.s-' {1..170} > "$TEST_DIR/t17.txt"
result=$(classify_turn "$TEST_DIR/t17.txt")
assert_eq "T17: >160 chars is complex" "complex" "$result"

# T18: Many words (> 28) → complex
echo "a b c d e f g h i j k l m n o p q r s t u v w x y z aa bb cc" > "$TEST_DIR/t18.txt"
result=$(classify_turn "$TEST_DIR/t18.txt")
assert_eq "T18: >28 words is complex" "complex" "$result"

# T19: Multiple newlines (> 1) → complex
printf "line one\nline two\nline three\n" > "$TEST_DIR/t19.txt"
result=$(classify_turn "$TEST_DIR/t19.txt")
assert_eq "T19: >1 newline is complex" "complex" "$result"

# T20: Non-existent file → complex (safe default)
result=$(classify_turn "$TEST_DIR/nonexistent.txt")
assert_eq "T20: non-existent file is complex" "complex" "$result"

# T21: Empty file → simple
> "$TEST_DIR/t21.txt"
result=$(classify_turn "$TEST_DIR/t21.txt")
assert_eq "T21: empty file is simple" "simple" "$result"

# T22: Short non-keyword sentence → simple
echo "sounds good, thanks" > "$TEST_DIR/t22.txt"
result=$(classify_turn "$TEST_DIR/t22.txt")
assert_eq "T22: 'sounds good, thanks' is simple" "simple" "$result"

# T23: Yes/no → simple
echo "yes" > "$TEST_DIR/t23.txt"
result=$(classify_turn "$TEST_DIR/t23.txt")
assert_eq "T23: 'yes' is simple" "simple" "$result"

# T24: Case-insensitive keyword detection
echo "IMPLEMENT the feature" > "$TEST_DIR/t24.txt"
result=$(classify_turn "$TEST_DIR/t24.txt")
assert_eq "T24: 'IMPLEMENT' (uppercase) is complex" "complex" "$result"

# T25: http:// URL → complex
echo "see http://localhost:3000" > "$TEST_DIR/t25.txt"
result=$(classify_turn "$TEST_DIR/t25.txt")
assert_eq "T25: http:// URL is complex" "complex" "$result"

# ═══════════════════════════════════════════════════════════════
# smart_route() tests
# ═══════════════════════════════════════════════════════════════

# T26: smart_route routes simple turn to cheap model
echo "oi" > "$TEST_DIR/t26.txt"
export RUNNER_SMART_ROUTING="true"
export RUNNER_CHEAP_MODEL="haiku"
unset PHASE_CASCADE 2>/dev/null || true
_EXEC_RUNTIME_CALLED=""
_EXEC_RUNTIME_MODEL=""
smart_route "$TEST_DIR/t26.txt" "$TEST_DIR/t26_out.txt" "test_phase" 2>/dev/null
assert_eq "T26: smart_route calls _exec_runtime for simple" "true" "$_EXEC_RUNTIME_CALLED"
assert_eq "T26: smart_route uses cheap model" "haiku" "$_EXEC_RUNTIME_MODEL"

# T27: smart_route returns 1 for complex turn (not routed)
echo "implement auth system" > "$TEST_DIR/t27.txt"
_EXEC_RUNTIME_CALLED=""
exit_code=0
smart_route "$TEST_DIR/t27.txt" "$TEST_DIR/t27_out.txt" "test_phase" 2>/dev/null || exit_code=$?
assert_eq "T27: smart_route returns 1 for complex" "1" "$exit_code"
assert_eq "T27: _exec_runtime NOT called for complex" "" "$_EXEC_RUNTIME_CALLED"

# T28: RUNNER_SMART_ROUTING=false bypasses routing
echo "oi" > "$TEST_DIR/t28.txt"
export RUNNER_SMART_ROUTING="false"
_EXEC_RUNTIME_CALLED=""
exit_code=0
smart_route "$TEST_DIR/t28.txt" "$TEST_DIR/t28_out.txt" "test_phase" 2>/dev/null || exit_code=$?
assert_eq "T28: smart routing disabled returns 1" "1" "$exit_code"
assert_eq "T28: _exec_runtime NOT called when disabled" "" "$_EXEC_RUNTIME_CALLED"
export RUNNER_SMART_ROUTING="true"

# T29: PHASE_CASCADE active → smart routing bypassed (cascade precedence)
echo "oi" > "$TEST_DIR/t29.txt"
export PHASE_CASCADE="haiku:0.7,sonnet:0.8,opus"
_EXEC_RUNTIME_CALLED=""
exit_code=0
smart_route "$TEST_DIR/t29.txt" "$TEST_DIR/t29_out.txt" "test_phase" 2>/dev/null || exit_code=$?
assert_eq "T29: cascade active returns 1 (bypassed)" "1" "$exit_code"
assert_eq "T29: _exec_runtime NOT called when cascade active" "" "$_EXEC_RUNTIME_CALLED"
unset PHASE_CASCADE

# T30: Default RUNNER_CHEAP_MODEL is haiku
echo "hello" > "$TEST_DIR/t30.txt"
unset RUNNER_CHEAP_MODEL 2>/dev/null || true
_EXEC_RUNTIME_MODEL=""
smart_route "$TEST_DIR/t30.txt" "$TEST_DIR/t30_out.txt" "test_phase" 2>/dev/null
assert_eq "T30: default cheap model is haiku" "haiku" "$_EXEC_RUNTIME_MODEL"
export RUNNER_CHEAP_MODEL="haiku"

# T31: Custom RUNNER_CHEAP_MODEL respected
echo "hi" > "$TEST_DIR/t31.txt"
export RUNNER_CHEAP_MODEL="flash"
_EXEC_RUNTIME_MODEL=""
smart_route "$TEST_DIR/t31.txt" "$TEST_DIR/t31_out.txt" "test_phase" 2>/dev/null
assert_eq "T31: custom cheap model respected" "flash" "$_EXEC_RUNTIME_MODEL"
export RUNNER_CHEAP_MODEL="haiku"

# ═══════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════

echo ""
echo "test-smart-routing: $_TESTS_PASSED / $_TESTS_RUN passed"
[[ $_TESTS_PASSED -eq $_TESTS_RUN ]] || exit 1
