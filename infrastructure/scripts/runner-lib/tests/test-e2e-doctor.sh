#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# TEST: E2E Doctor — end-to-end validation pipeline integration test
# ═══════════════════════════════════════════════════════════════════════════════
# Validates the entire validation pipeline works end-to-end:
#   1. doctor.js exits 0 (or reports correctly)
#   2. validate-yaml-incremental.js catches invalid YAML (exit 1)
#   3. validate-artifact-placement.js catches misplaced artifacts (exit 1)
#
# Each test creates temp fixtures, runs the real validator, and cleans up.
# Exit: 0 if all pass, 1 if any fail.

set -uo pipefail
# Note: -e intentionally omitted — individual assertions handle failures.
# With -e, a single git command failure in a shallow clone kills the entire test silently.

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_LIB_DIR="$(cd "$TESTS_DIR/.." && pwd)"
REPO_ROOT="$(cd "$RUNNER_LIB_DIR/../../.." && pwd)"

# ── Skip recursive invocation (doctor.js → run-tests.sh → this test) ─────────
# The recursive run pollutes git staging state, causing false negatives in Tests 2-5.
if [[ "${E2E_DOCTOR_RUNNING:-}" == "1" ]]; then
  echo "test-e2e-doctor: SKIP (recursive invocation from doctor.js)"
  exit 0
fi

# ── Skip in shallow clones (CI uses fetch-depth: 2) ─────────────────────────
# Tests 2-5 require git add/reset which can fail in shallow clones.
if git -C "$REPO_ROOT" rev-parse --is-shallow-repository 2>/dev/null | grep -q true; then
  echo "test-e2e-doctor: SKIP (shallow clone detected — git staging tests unreliable)"
  exit 0
fi

# ── Remove stale index.lock (common in concurrent CI / hook environments) ─────
LOCK_FILE="$REPO_ROOT/.git/index.lock"
if [[ -f "$LOCK_FILE" ]]; then
  # Only remove if no git process holds it (lsof returns 1 if no process found)
  if ! lsof "$LOCK_FILE" >/dev/null 2>&1; then
    rm -f "$LOCK_FILE"
  fi
fi

# ── Cleanup tracking ──────────────────────────────────────────────────────────
_TEMP_FILES=()

cleanup() {
  for f in "${_TEMP_FILES[@]+"${_TEMP_FILES[@]}"}"; do
    # Force-remove from git index (handles gitignored files added with -f)
    git -C "$REPO_ROOT" rm --cached -f "$f" >/dev/null 2>&1 || true
    if [[ -f "$f" ]]; then
      rm -f "$f"
    elif [[ -d "$f" ]]; then
      rm -rf "$f"
    fi
  done
  # Unstage any remaining files we may have staged during tests
  git -C "$REPO_ROOT" reset HEAD -- . >/dev/null 2>&1 || true
}
trap cleanup EXIT

# ── Assertion helpers (match existing pattern) ─────────────────────────────────
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

assert_contains() {
  local label="$1" haystack="$2" needle="$3"
  _TESTS_RUN=$((_TESTS_RUN + 1))
  if [[ "$haystack" == *"$needle"* ]]; then
    _TESTS_PASSED=$((_TESTS_PASSED + 1))
  else
    echo "FAIL: $label — output does not contain '$needle'" >&2
    echo "  got: $(echo "$haystack" | head -5)" >&2
  fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: doctor.js runs successfully (exit 0 or known non-zero)
# ═══════════════════════════════════════════════════════════════════════════════
# Set guard to prevent doctor.js → run-tests.sh → test-e2e-doctor.sh recursion,
# which pollutes git staging state and causes false negatives in Tests 2-5.
export E2E_DOCTOR_RUNNING=1
doctor_exit=0
doctor_output=""
doctor_output=$(node "$REPO_ROOT/scripts/doctor.js" 2>&1) || doctor_exit=$?
unset E2E_DOCTOR_RUNNING

# doctor.js exit 0 means healthy; exit 1 means it found issues but ran correctly.
# Either is acceptable — the key is it does NOT crash (exit 2+ or signal).
if [[ $doctor_exit -le 1 ]]; then
  assert_eq "doctor.js runs without crash" "true" "true"
else
  assert_eq "doctor.js runs without crash (exit=$doctor_exit)" "0" "$doctor_exit"
fi

# doctor.js must produce recognizable output
assert_contains "doctor.js produces diagnostic output" "$doctor_output" "Doctor"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: validate-yaml-incremental.js catches invalid YAML
# ═══════════════════════════════════════════════════════════════════════════════
INVALID_YAML_FILE="$REPO_ROOT/_e2e-test-invalid-syntax-$$.yaml"
cat > "$INVALID_YAML_FILE" <<'YAMLERR'
valid_key: true
broken:
  - item1
  - item2
  bad_indent: [unclosed
    nested: "missing quote
YAMLERR
_TEMP_FILES+=("$INVALID_YAML_FILE")

# Stage it so git diff --staged picks it up (remove lock if stale)
rm -f "$REPO_ROOT/.git/index.lock" 2>/dev/null || true
git -C "$REPO_ROOT" add -f "$INVALID_YAML_FILE" 2>/dev/null || echo "WARNING: git add failed for invalid YAML fixture" >&2

yaml_exit=0
yaml_output=""
yaml_output=$(node "$REPO_ROOT/scripts/validate-yaml-incremental.js" 2>&1) || yaml_exit=$?

# Check the test file appears in error output (exit code may vary if repo has other changed YAMLs)
assert_contains "invalid YAML file named in output" "$yaml_output" "_e2e-test-invalid-syntax-$$.yaml"

# Unstage and remove
git -C "$REPO_ROOT" rm --cached -f "$INVALID_YAML_FILE" >/dev/null 2>&1 || true
rm -f "$INVALID_YAML_FILE"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: validate-yaml-incremental.js passes valid YAML
# ═══════════════════════════════════════════════════════════════════════════════
VALID_YAML_FILE="$REPO_ROOT/_e2e-test-valid-syntax-$$.yaml"
cat > "$VALID_YAML_FILE" <<'YAMLOK'
name: e2e-test
description: Valid YAML for E2E testing
items:
  - one
  - two
YAMLOK
_TEMP_FILES+=("$VALID_YAML_FILE")

rm -f "$REPO_ROOT/.git/index.lock" 2>/dev/null || true
git -C "$REPO_ROOT" add -f "$VALID_YAML_FILE" 2>/dev/null || echo "WARNING: git add failed for valid YAML fixture" >&2

valid_yaml_exit=0
valid_yaml_output=""
valid_yaml_output=$(node "$REPO_ROOT/scripts/validate-yaml-incremental.js" 2>&1) || valid_yaml_exit=$?

# Our valid file must NOT appear in error output (repo may have other changed YAMLs affecting exit code)
if [[ "$valid_yaml_output" == *"_e2e-test-valid-syntax-$$.yaml"* ]]; then
  assert_eq "valid YAML not flagged as error" "not-found" "found"
else
  assert_eq "valid YAML not flagged as error" "not-found" "not-found"
fi

git -C "$REPO_ROOT" rm --cached -f "$VALID_YAML_FILE" >/dev/null 2>&1 || true
rm -f "$VALID_YAML_FILE"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: validate-artifact-placement.js catches misplaced squad output
# ═══════════════════════════════════════════════════════════════════════════════
# Create a file with squad-output indicator inside workspace/ (violation)
MISPLACED_DIR="$REPO_ROOT/workspace/businesses/aiox/L4-operational"
MISPLACED_FILE="$MISPLACED_DIR/_e2e-test-score-card-$$.jsonl"
mkdir -p "$MISPLACED_DIR"
echo '{"score":100}' > "$MISPLACED_FILE"
_TEMP_FILES+=("$MISPLACED_FILE")

rm -f "$REPO_ROOT/.git/index.lock" 2>/dev/null || true
git -C "$REPO_ROOT" add -f "$MISPLACED_FILE" 2>/dev/null || echo "WARNING: git add failed for misplaced artifact fixture" >&2

artifact_exit=0
artifact_output=""
artifact_output=$(node "$REPO_ROOT/scripts/validate-artifact-placement.js" 2>&1) || artifact_exit=$?

# Check our misplaced file appears in violation output (exit code may vary with other repo state)
assert_contains "violation mentions score-card" "$artifact_output" "_e2e-test-score-card-$$"

git -C "$REPO_ROOT" rm --cached -f "$MISPLACED_FILE" >/dev/null 2>&1 || true
rm -f "$MISPLACED_FILE"

# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: validate-artifact-placement.js passes correctly placed file
# ═══════════════════════════════════════════════════════════════════════════════
CORRECT_DIR="$REPO_ROOT/outputs/e2e-test-squad-$$"
CORRECT_FILE="$CORRECT_DIR/_e2e-test-result-$$.yaml"
mkdir -p "$CORRECT_DIR"
echo 'result: pass' > "$CORRECT_FILE"
_TEMP_FILES+=("$CORRECT_FILE" "$CORRECT_DIR")

rm -f "$REPO_ROOT/.git/index.lock" 2>/dev/null || true
git -C "$REPO_ROOT" add -f "$CORRECT_FILE" 2>/dev/null || echo "WARNING: git add failed for correct artifact fixture" >&2

correct_exit=0
correct_output=""
correct_output=$(node "$REPO_ROOT/scripts/validate-artifact-placement.js" 2>&1) || correct_exit=$?

# Our correctly placed file must NOT appear in violations (repo may have other violations affecting exit code)
if [[ "$correct_output" == *"_e2e-test-result-$$"* ]]; then
  assert_eq "correctly placed artifact not flagged" "not-found" "found"
else
  assert_eq "correctly placed artifact not flagged" "not-found" "not-found"
fi

git -C "$REPO_ROOT" rm --cached -f "$CORRECT_FILE" >/dev/null 2>&1 || true
rm -f "$CORRECT_FILE"
rmdir "$CORRECT_DIR" 2>/dev/null || true

# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════
if [[ $_TESTS_PASSED -eq $_TESTS_RUN ]]; then
  echo "test-e2e-doctor: $_TESTS_PASSED/$_TESTS_RUN passed"
  exit 0
else
  echo "test-e2e-doctor: $_TESTS_PASSED/$_TESTS_RUN passed" >&2
  exit 1
fi
