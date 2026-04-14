#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# TEST: git-context.sh — generate_git_context integration tests
# ═══════════════════════════════════════════════════════════════
# Story: STORY-118.1

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

# ── Source module ──
source "$RUNNER_LIB_DIR/git-context.sh"

# ── Create a temporary git repo with multiple commits ──
ORIG_DIR="$(pwd)"
TEMP_REPO="$TEST_DIR/test-repo"
mkdir -p "$TEMP_REPO"
cd "$TEMP_REPO"

git init --quiet
git config user.email "test@test.com"
git config user.name "Test User"

# Create a file and make 6 commits
TEST_FILE="sample.txt"
for i in 1 2 3 4 5 6; do
  echo "Line added in commit $i" >> "$TEST_FILE"
  git add "$TEST_FILE"
  git commit --quiet -m "commit $i: add line $i to sample"
done

# ═══════════════════════════════════════════════════════════════
# Test 1: File with multiple commits produces output with diff and log
# ═══════════════════════════════════════════════════════════════
output=$(generate_git_context "$TEST_FILE")

assert_true "output is non-empty for file with history" '[[ -n "$output" ]]'
assert_true "output contains diff section header" 'echo "$output" | grep -q "Recent Diff"'
assert_true "output contains log section header" 'echo "$output" | grep -q "Commit Log"'

# ═══════════════════════════════════════════════════════════════
# Test 2: New file with no history returns empty
# ═══════════════════════════════════════════════════════════════
UNTRACKED_FILE="brand-new.txt"
echo "I am new" > "$UNTRACKED_FILE"
# Do NOT git add — this file has zero history

output_new=$(generate_git_context "$UNTRACKED_FILE")
assert_eq "new file returns empty" "" "$output_new"

# ═══════════════════════════════════════════════════════════════
# Test 3: Budget respected — output <= maxBytes
# ═══════════════════════════════════════════════════════════════
BUDGET=512
output_budget=$(generate_git_context "$TEST_FILE" "$BUDGET")
output_bytes=$(printf '%s' "$output_budget" | wc -c | tr -d '[:space:]')

assert_true "output respects budget ($output_bytes <= $BUDGET)" '[[ "$output_bytes" -le "$BUDGET" ]]'

# ═══════════════════════════════════════════════════════════════
# Test 4: Diff appears before log in output
# ═══════════════════════════════════════════════════════════════
diff_pos=$(echo "$output" | grep -n "Recent Diff" | head -1 | cut -d: -f1)
log_pos=$(echo "$output" | grep -n "Commit Log" | head -1 | cut -d: -f1)

# Both must exist (already tested), now check order
assert_true "diff appears before log" '[[ "$diff_pos" -lt "$log_pos" ]]'

# ═══════════════════════════════════════════════════════════════
# Test 5: No file path returns empty
# ═══════════════════════════════════════════════════════════════
output_empty=$(generate_git_context "")
assert_eq "empty file path returns empty" "" "$output_empty"

# ═══════════════════════════════════════════════════════════════
# Test 6: Output contains summary line with commit count
# ═══════════════════════════════════════════════════════════════
assert_true "output contains commit count summary" 'echo "$output" | grep -q "6 commits"'

# ═══════════════════════════════════════════════════════════════
# Test 7: Shallow repo (1 commit) still works
# ═══════════════════════════════════════════════════════════════
SHALLOW_REPO="$TEST_DIR/shallow-repo"
mkdir -p "$SHALLOW_REPO"
cd "$SHALLOW_REPO"
git init --quiet
git config user.email "test@test.com"
git config user.name "Test User"
echo "single line" > "only.txt"
git add "only.txt"
git commit --quiet -m "only commit"

output_shallow=$(generate_git_context "only.txt")
assert_true "shallow repo produces output" '[[ -n "$output_shallow" ]]'
assert_true "shallow repo output has log" 'echo "$output_shallow" | grep -q "Commit Log"'

cd "$ORIG_DIR"

# ═══════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════
if [[ $_TESTS_PASSED -eq $_TESTS_RUN ]]; then
  echo "test-git-context: $_TESTS_PASSED/$_TESTS_RUN passed"
  exit 0
else
  echo "test-git-context: $_TESTS_PASSED/$_TESTS_RUN passed" >&2
  exit 1
fi
