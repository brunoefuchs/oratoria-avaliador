#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# TEST: arg-parser.sh — parse_common_args with standard flags
# ═══════════════════════════════════════════════════════════════════════════════
# Story: 101.14 AC9

set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_LIB_DIR="$(cd "$TESTS_DIR/.." && pwd)"
export REPO_ROOT
REPO_ROOT="$(cd "$RUNNER_LIB_DIR/../../.." && pwd)"

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

# ══════════════════════════════════════════
# Test 1: --model sets RUNNER_MODEL
# ══════════════════════════════════════════
(
  source "$RUNNER_LIB_DIR/arg-parser.sh"
  parse_common_args --model opus
  [[ "$RUNNER_MODEL" == "opus" ]]
) && { _TESTS_RUN=$((_TESTS_RUN + 1)); _TESTS_PASSED=$((_TESTS_PASSED + 1)); } \
  || { _TESTS_RUN=$((_TESTS_RUN + 1)); echo "FAIL: --model sets RUNNER_MODEL" >&2; }

# ══════════════════════════════════════════
# Test 2: --claude sets REQUESTED_RUNTIME
# ══════════════════════════════════════════
(
  source "$RUNNER_LIB_DIR/arg-parser.sh"
  parse_common_args --claude
  [[ "$REQUESTED_RUNTIME" == "claude" ]]
) && { _TESTS_RUN=$((_TESTS_RUN + 1)); _TESTS_PASSED=$((_TESTS_PASSED + 1)); } \
  || { _TESTS_RUN=$((_TESTS_RUN + 1)); echo "FAIL: --claude sets REQUESTED_RUNTIME" >&2; }

# ══════════════════════════════════════════
# Test 3: --codex sets REQUESTED_RUNTIME
# ══════════════════════════════════════════
(
  source "$RUNNER_LIB_DIR/arg-parser.sh"
  parse_common_args --codex
  [[ "$REQUESTED_RUNTIME" == "codex" ]]
) && { _TESTS_RUN=$((_TESTS_RUN + 1)); _TESTS_PASSED=$((_TESTS_PASSED + 1)); } \
  || { _TESTS_RUN=$((_TESTS_RUN + 1)); echo "FAIL: --codex sets REQUESTED_RUNTIME" >&2; }

# ══════════════════════════════════════════
# Test 4: --max-cost sets MAX_COST
# ══════════════════════════════════════════
(
  source "$RUNNER_LIB_DIR/arg-parser.sh"
  parse_common_args --max-cost 5.00
  [[ "$MAX_COST" == "5.00" ]]
) && { _TESTS_RUN=$((_TESTS_RUN + 1)); _TESTS_PASSED=$((_TESTS_PASSED + 1)); } \
  || { _TESTS_RUN=$((_TESTS_RUN + 1)); echo "FAIL: --max-cost sets MAX_COST" >&2; }

# ══════════════════════════════════════════
# Test 5: --no-eval sets EVAL_DISABLED=true
# ══════════════════════════════════════════
(
  source "$RUNNER_LIB_DIR/arg-parser.sh"
  parse_common_args --no-eval
  [[ "$EVAL_DISABLED" == "true" ]]
) && { _TESTS_RUN=$((_TESTS_RUN + 1)); _TESTS_PASSED=$((_TESTS_PASSED + 1)); } \
  || { _TESTS_RUN=$((_TESTS_RUN + 1)); echo "FAIL: --no-eval sets EVAL_DISABLED" >&2; }

# ══════════════════════════════════════════
# Test 6: --eval-tier1-only sets EVAL_TIER1_ONLY=true
# ══════════════════════════════════════════
(
  source "$RUNNER_LIB_DIR/arg-parser.sh"
  parse_common_args --eval-tier1-only
  [[ "$EVAL_TIER1_ONLY" == "true" ]]
) && { _TESTS_RUN=$((_TESTS_RUN + 1)); _TESTS_PASSED=$((_TESTS_PASSED + 1)); } \
  || { _TESTS_RUN=$((_TESTS_RUN + 1)); echo "FAIL: --eval-tier1-only sets EVAL_TIER1_ONLY" >&2; }

# ══════════════════════════════════════════
# Test 7: Defaults when no args provided
# ══════════════════════════════════════════
(
  source "$RUNNER_LIB_DIR/arg-parser.sh"
  parse_common_args
  [[ "$REQUESTED_RUNTIME" == "auto" ]] && \
  [[ "$RUNNER_MODEL" == "" ]] && \
  [[ "$DRY_RUN" == "false" ]] && \
  [[ "$VERBOSE" == "false" ]] && \
  [[ "$EVAL_DISABLED" == "false" ]] && \
  [[ "$EVAL_TIER1_ONLY" == "false" ]]
) && { _TESTS_RUN=$((_TESTS_RUN + 1)); _TESTS_PASSED=$((_TESTS_PASSED + 1)); } \
  || { _TESTS_RUN=$((_TESTS_RUN + 1)); echo "FAIL: defaults when no args" >&2; }

# ══════════════════════════════════════════
# Test 8: Multiple flags combined
# ══════════════════════════════════════════
(
  source "$RUNNER_LIB_DIR/arg-parser.sh"
  parse_common_args --gemini --model opus --max-cost 2.50 --no-eval --verbose
  [[ "$REQUESTED_RUNTIME" == "gemini" ]] && \
  [[ "$RUNNER_MODEL" == "opus" ]] && \
  [[ "$MAX_COST" == "2.50" ]] && \
  [[ "$EVAL_DISABLED" == "true" ]] && \
  [[ "$VERBOSE" == "true" ]]
) && { _TESTS_RUN=$((_TESTS_RUN + 1)); _TESTS_PASSED=$((_TESTS_PASSED + 1)); } \
  || { _TESTS_RUN=$((_TESTS_RUN + 1)); echo "FAIL: multiple flags combined" >&2; }

# ══════════════════════════════════════════
# Test 9: Positional args preserved
# ══════════════════════════════════════════
(
  source "$RUNNER_LIB_DIR/arg-parser.sh"
  parse_common_args my-slug --model opus extra-arg
  [[ "${POSITIONAL_ARGS[0]}" == "my-slug" ]] && \
  [[ "${POSITIONAL_ARGS[1]}" == "extra-arg" ]]
) && { _TESTS_RUN=$((_TESTS_RUN + 1)); _TESTS_PASSED=$((_TESTS_PASSED + 1)); } \
  || { _TESTS_RUN=$((_TESTS_RUN + 1)); echo "FAIL: positional args preserved" >&2; }

# ══════════════════════════════════════════
# Summary
# ══════════════════════════════════════════
if [[ $_TESTS_PASSED -eq $_TESTS_RUN ]]; then
  echo "test-arg-parser: $_TESTS_PASSED/$_TESTS_RUN passed"
  exit 0
else
  echo "test-arg-parser: $_TESTS_PASSED/$_TESTS_RUN passed" >&2
  exit 1
fi
