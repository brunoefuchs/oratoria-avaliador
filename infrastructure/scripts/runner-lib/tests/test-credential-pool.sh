#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# TEST: credential-pool.sh — rotation, cooldown, pool empty scenarios
# ═══════════════════════════════════════════════════════════════════════════════
# Story: 115.10

set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_LIB_DIR="$(cd "$TESTS_DIR/.." && pwd)"

TEST_DIR=$(mktemp -d)
teardown() { rm -rf "$TEST_DIR" "${TMPDIR:-/tmp}"/runner-credential-pool-test-*.json 2>/dev/null; }
trap 'echo "test-credential-pool: CRASHED at line $LINENO (exit $?)" >&2; teardown' ERR
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

assert_neq() {
  local label="$1" unexpected="$2" actual="$3"
  _TESTS_RUN=$((_TESTS_RUN + 1))
  if [[ "$unexpected" != "$actual" ]]; then
    _TESTS_PASSED=$((_TESTS_PASSED + 1))
  else
    echo "FAIL: $label — expected NOT '$unexpected', got '$actual'" >&2
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

# ══════════════════════════════════════════════════════════════════════════════
# Scenario 1: Round-robin rotation
# ══════════════════════════════════════════════════════════════════════════════

# Reset pool state between scenarios
_reset_pool() {
  _POOL_KEYS=()
  _POOL_STATE_FILE=""
  _POOL_INITIALIZED=false
  _POOL_LAST_INDEX=0
  _POOL_LAST_KEY=""
  unset RUNNER_API_KEYS RUNNER_API_KEYS_FILE RUNNER_CREDENTIAL_STRATEGY 2>/dev/null || true
  rm -f "${TMPDIR:-/tmp}"/runner-credential-pool-test-*.json 2>/dev/null || true
}

_reset_pool
export RUNNER_API_KEYS="key-alpha,key-beta,key-gamma"
export RUNNER_NAME="test-rotation"
export RUNNER_CREDENTIAL_STRATEGY="round_robin"

source "$RUNNER_LIB_DIR/credential-pool.sh"

# First call should return key-alpha (index 0)
key1=$(pool_get_credential 2>/dev/null)
assert_eq "round_robin: first key is key-alpha" "key-alpha" "$key1"

# Second call should return key-beta (index 1)
key2=$(pool_get_credential 2>/dev/null)
assert_eq "round_robin: second key is key-beta" "key-beta" "$key2"

# Third call should return key-gamma (index 2)
key3=$(pool_get_credential 2>/dev/null)
assert_eq "round_robin: third key is key-gamma" "key-gamma" "$key3"

# Fourth call wraps around to key-alpha
key4=$(pool_get_credential 2>/dev/null)
assert_eq "round_robin: fourth key wraps to key-alpha" "key-alpha" "$key4"

# State file should exist
assert_true "state file exists" '[[ -f "${TMPDIR:-/tmp}/runner-credential-pool-test-rotation.json" ]]'

# ══════════════════════════════════════════════════════════════════════════════
# Scenario 1b: Least-used strategy
# ══════════════════════════════════════════════════════════════════════════════

_reset_pool
export RUNNER_API_KEYS="key-one,key-two,key-three"
export RUNNER_NAME="test-least-used"
export RUNNER_CREDENTIAL_STRATEGY="least_used"

# Re-source to reset internal state
source "$RUNNER_LIB_DIR/credential-pool.sh"

# All start at request_count=0, so first available wins
lu_key1=$(pool_get_credential 2>/dev/null)
assert_neq "least_used: returns a key" "" "$lu_key1"

# Report success to increment request_count on first key
pool_report_success "$lu_key1" 2>/dev/null
lu_key2=$(pool_get_credential 2>/dev/null)
# Second call should prefer a different key (lower count)
# (key-one has count=1, others have count=0)
assert_neq "least_used: second call prefers different key" "$lu_key1" "$lu_key2"

# ══════════════════════════════════════════════════════════════════════════════
# Scenario 1c: Load from file
# ══════════════════════════════════════════════════════════════════════════════

_reset_pool
local_keys_file="$TEST_DIR/api-keys.txt"
printf "file-key-1\n# comment line\nfile-key-2\n" > "$local_keys_file"
export RUNNER_API_KEYS_FILE="$local_keys_file"
export RUNNER_NAME="test-file-load"

source "$RUNNER_LIB_DIR/credential-pool.sh"

fk1=$(pool_get_credential 2>/dev/null)
assert_eq "file load: first key" "file-key-1" "$fk1"

fk2=$(pool_get_credential 2>/dev/null)
assert_eq "file load: second key" "file-key-2" "$fk2"

# ══════════════════════════════════════════════════════════════════════════════
# Scenario 2: Cooldown (429/401/402)
# ══════════════════════════════════════════════════════════════════════════════

_reset_pool
export RUNNER_API_KEYS="cool-key-1,cool-key-2,cool-key-3"
export RUNNER_NAME="test-cooldown"
export RUNNER_CREDENTIAL_STRATEGY="round_robin"
# Short cooldowns for testing
export RUNNER_COOLDOWN_429=3600
export RUNNER_COOLDOWN_401=86400
export RUNNER_COOLDOWN_402=86400

source "$RUNNER_LIB_DIR/credential-pool.sh"

# Get first key and report 429
cd1=$(pool_get_credential 2>/dev/null)
assert_eq "cooldown: get first key" "cool-key-1" "$cd1"
pool_report_error "cool-key-1" 429 2>/dev/null

# Next call should skip cool-key-1 (in cooldown) and return cool-key-2
cd2=$(pool_get_credential 2>/dev/null)
assert_eq "cooldown 429: skip to cool-key-2" "cool-key-2" "$cd2"

# Report 401 on cool-key-2
pool_report_error "cool-key-2" 401 2>/dev/null

# Next should return cool-key-3
cd3=$(pool_get_credential 2>/dev/null)
assert_eq "cooldown 401: skip to cool-key-3" "cool-key-3" "$cd3"

# Report 402 on cool-key-3
pool_report_error "cool-key-3" 402 2>/dev/null

# Verify state file has cooldown info
if command -v jq >/dev/null 2>&1; then
  state_file="${TMPDIR:-/tmp}/runner-credential-pool-test-cooldown.json"
  k1_status=$(jq -r '.keys[0].last_status' "$state_file" 2>/dev/null)
  k2_status=$(jq -r '.keys[1].last_status' "$state_file" 2>/dev/null)
  k3_status=$(jq -r '.keys[2].last_status' "$state_file" 2>/dev/null)
  assert_eq "state: key1 last_status=429" "429" "$k1_status"
  assert_eq "state: key2 last_status=401" "401" "$k2_status"
  assert_eq "state: key3 last_status=402" "402" "$k3_status"

  k1_cooldown=$(jq -r '.keys[0].cooldown_until' "$state_file" 2>/dev/null)
  assert_true "state: key1 has future cooldown" '[[ "$k1_cooldown" -gt 0 ]]'
fi

# Report success resets error counter
pool_report_success "cool-key-1" 2>/dev/null
if command -v jq >/dev/null 2>&1; then
  state_file="${TMPDIR:-/tmp}/runner-credential-pool-test-cooldown.json"
  k1_err=$(jq -r '.keys[0].error_count' "$state_file" 2>/dev/null)
  k1_cd=$(jq -r '.keys[0].cooldown_until' "$state_file" 2>/dev/null)
  assert_eq "success resets error_count" "0" "$k1_err"
  assert_eq "success resets cooldown" "0" "$k1_cd"
fi

# ══════════════════════════════════════════════════════════════════════════════
# Scenario 3: Pool empty / all keys in cooldown
# ══════════════════════════════════════════════════════════════════════════════

_reset_pool
export RUNNER_API_KEYS="exhaust-1,exhaust-2"
export RUNNER_NAME="test-exhausted"
export RUNNER_CREDENTIAL_STRATEGY="round_robin"

source "$RUNNER_LIB_DIR/credential-pool.sh"

# Exhaust both keys
pool_get_credential >/dev/null 2>&1
pool_report_error "exhaust-1" 429 2>/dev/null
pool_get_credential >/dev/null 2>&1
pool_report_error "exhaust-2" 401 2>/dev/null

# All keys in cooldown — should still return a key (fallback) with warning
fallback_key=$(pool_get_credential 2>"$TEST_DIR/fallback-stderr.txt")
assert_neq "fallback: returns a key even when all in cooldown" "" "$fallback_key"

# Check that warning was emitted
assert_true "fallback: warning message emitted" 'grep -q "All keys in cooldown" "$TEST_DIR/fallback-stderr.txt"'

# ══════════════════════════════════════════════════════════════════════════════
# Scenario 3b: No keys configured — pool_get_credential returns 1
# ══════════════════════════════════════════════════════════════════════════════

_reset_pool
export RUNNER_NAME="test-nokeys"

source "$RUNNER_LIB_DIR/credential-pool.sh"

no_key_exit=0
pool_get_credential >/dev/null 2>&1 || no_key_exit=$?
assert_eq "no keys: returns exit code 1" "1" "$no_key_exit"

# ══════════════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════════════

echo "test-credential-pool: $_TESTS_PASSED/$_TESTS_RUN passed"
[[ "$_TESTS_PASSED" -eq "$_TESTS_RUN" ]] || exit 1
