#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER-LIB Integration Test Runner
# ═══════════════════════════════════════════════════════════════════════════════
# Discovers and executes all test-*.sh files in this directory.
# Uses assertions.sh from runner-lib for validations.
#
# Usage: bash run-tests.sh [--smoke-only] [--skip-smoke] [--coverage] [--coverage-output file] [--update-coverage-baseline] [test-name...]
#   No args = run all integration tests + smoke tests.
#   --smoke-only = run only smoke tests (skip integration tests).
#   With args = run only matching test-*.sh files.
#
# Exit: 0 if all tests pass, 1 if any fail.
# Story: 101.14, 101.15

set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_LIB_DIR="$(cd "$TESTS_DIR/.." && pwd)"
export REPO_ROOT
REPO_ROOT="$(cd "$RUNNER_LIB_DIR/../../.." && pwd)"

SMOKE_DIR="$TESTS_DIR/smoke"
SMOKE_ONLY=false
SKIP_SMOKE=false
COVERAGE=false
COVERAGE_OUTPUT=""
UPDATE_COVERAGE_BASELINE=false
TRACE_FILE=""

# ── Parse flags ──
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --smoke-only)
      SMOKE_ONLY=true
      shift
      ;;
    --skip-smoke)
      SKIP_SMOKE=true
      shift
      ;;
    --coverage)
      COVERAGE=true
      shift
      ;;
    --coverage-output)
      COVERAGE_OUTPUT="${2:-}"
      shift 2
      ;;
    --update-coverage-baseline)
      UPDATE_COVERAGE_BASELINE=true
      shift
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done
set -- "${POSITIONAL[@]+"${POSITIONAL[@]}"}"

# ── Source assertions from runner-lib ──
if [[ -f "$RUNNER_LIB_DIR/assertions.sh" ]]; then
  source "$RUNNER_LIB_DIR/assertions.sh"
fi

# ── Test counters ──
_TOTAL=0
_PASSED=0
_FAILED=0
_SKIPPED=0
_FAILED_NAMES=()
_SMOKE_PASSED=0
_SMOKE_FAILED=0
_SMOKE_SKIPPED=0

run_bash_with_optional_coverage() {
  local script_path="$1"
  shift

  if [[ "$COVERAGE" == "true" ]]; then
    env \
      BASH_XTRACEFD=9 \
      PS4='+${BASH_SOURCE:-$0}:${LINENO}:' \
      SHELLOPTS=xtrace \
      bash "$script_path" "$@" 9>>"$TRACE_FILE"
  else
    bash "$script_path" "$@"
  fi
}

parse_smoke_summary() {
  local output="$1"
  local summary_line=""

  summary_line="$(printf '%s\n' "$output" | grep -E '^[[:space:]]+[0-9]+/[0-9]+ (runners smoke OK|passed, [0-9]+ failed)' | tail -1)"
  [[ -n "$summary_line" ]] || return 1

  if [[ "$summary_line" =~ ([0-9]+)/([0-9]+)[[:space:]]+runners[[:space:]]+smoke[[:space:]]+OK ]]; then
    _SMOKE_PASSED="${BASH_REMATCH[1]}"
    _SMOKE_FAILED=0
  elif [[ "$summary_line" =~ ([0-9]+)/([0-9]+)[[:space:]]+passed,[[:space:]]+([0-9]+)[[:space:]]+failed ]]; then
    _SMOKE_PASSED="${BASH_REMATCH[1]}"
    _SMOKE_FAILED="${BASH_REMATCH[3]}"
  else
    return 1
  fi

  if [[ "$summary_line" =~ ,[[:space:]]+([0-9]+)[[:space:]]+skipped ]]; then
    _SMOKE_SKIPPED="${BASH_REMATCH[1]}"
  else
    _SMOKE_SKIPPED=0
  fi

  return 0
}

# ── Timer ──
_START_TIME=$(date +%s)

if [[ "$COVERAGE" == "true" ]]; then
  TRACE_FILE="$(mktemp)"
  trap 'rm -f "$TRACE_FILE"' EXIT
fi

# ── Discover integration tests ──
TEST_FILES=()
if [[ "$SMOKE_ONLY" == "false" ]]; then
  if [[ $# -gt 0 ]]; then
    for name in "$@"; do
      local_file="$TESTS_DIR/test-${name}.sh"
      full_file="$TESTS_DIR/${name}"
      if [[ -f "$local_file" ]]; then
        TEST_FILES+=("$local_file")
      elif [[ -f "$full_file" ]]; then
        TEST_FILES+=("$full_file")
      else
        echo "WARN: Test not found: $name" >&2
      fi
    done
  else
    for f in "$TESTS_DIR"/test-*.sh; do
      [[ -f "$f" ]] && TEST_FILES+=("$f")
    done
  fi
fi

# ── Run integration tests (if any) ──
if [[ ${#TEST_FILES[@]} -gt 0 ]]; then
  echo "═══════════════════════════════════════════════════════════════"
  echo "  RUNNER-LIB Integration Tests"
  echo "  Tests: ${#TEST_FILES[@]}"
  echo "═══════════════════════════════════════════════════════════════"
  echo ""

  for test_file in "${TEST_FILES[@]}"; do
    test_name="$(basename "$test_file" .sh)"
    _TOTAL=$((_TOTAL + 1))

    printf "  %-40s " "$test_name"

    # Run test in subshell, capture exit code
    test_output=""
    test_exit=0
    test_output=$(run_bash_with_optional_coverage "$test_file" 2>&1) || test_exit=$?

    if [[ $test_exit -eq 0 ]]; then
      echo "PASS"
      _PASSED=$((_PASSED + 1))
    elif [[ $test_exit -eq 77 ]]; then
      echo "SKIP"
      _SKIPPED=$((_SKIPPED + 1))
    else
      echo "FAIL (exit $test_exit)"
      _FAILED=$((_FAILED + 1))
      _FAILED_NAMES+=("$test_name")
      # Show output on failure
      echo "--- output ---"
      echo "$test_output" | head -30
      echo "--- end ---"
      echo ""
    fi
  done

  echo ""
elif [[ "$SMOKE_ONLY" == "false" ]]; then
  echo "No integration tests found."
fi

# ── Run smoke tests (AC16: always included as separate suite) ──
_SMOKE_EXIT=0
if [[ "$SKIP_SMOKE" != "true" && -f "$SMOKE_DIR/run-smoke-tests.sh" ]]; then
  echo ""
  _SMOKE_OUTPUT=""
  _SMOKE_OUTPUT=$(run_bash_with_optional_coverage "$SMOKE_DIR/run-smoke-tests.sh" 2>&1) || _SMOKE_EXIT=$?
  printf '%s\n' "$_SMOKE_OUTPUT"

  parse_smoke_summary "$_SMOKE_OUTPUT" || true
  _PASSED=$((_PASSED + _SMOKE_PASSED))
  _FAILED=$((_FAILED + _SMOKE_FAILED))
  _SKIPPED=$((_SKIPPED + _SMOKE_SKIPPED))

  if [[ $_SMOKE_EXIT -ne 0 ]]; then
    _FAILED_NAMES+=("smoke-tests")
  fi
fi

# ── Summary ──
_END_TIME=$(date +%s)
_DURATION=$((_END_TIME - _START_TIME))

echo ""
echo "═══════════════════════════════════════════════════════════════"
printf "  Summary: %d passed, %d failed, %d skipped (%ds)\n" \
  "$_PASSED" "$_FAILED" "$_SKIPPED" "$_DURATION"
if [[ $_SMOKE_EXIT -ne 0 ]]; then
  echo "  (smoke tests also failed)"
fi
echo "═══════════════════════════════════════════════════════════════"

if [[ "$COVERAGE" == "true" ]]; then
  if [[ -z "$COVERAGE_OUTPUT" ]]; then
    COVERAGE_OUTPUT="$(mktemp)"
  fi

  coverage_args=(
    --trace-file "$TRACE_FILE"
    --runner-lib-dir "$RUNNER_LIB_DIR"
    --output "$COVERAGE_OUTPUT"
  )
  if [[ "$UPDATE_COVERAGE_BASELINE" == "true" ]]; then
    coverage_args+=(--update-baseline "$REPO_ROOT/outputs/qa/coverage-baseline.json")
  fi

  node "$TESTS_DIR/coverage-report.js" "${coverage_args[@]}"

  coverage_pct=$(node -e "const fs=require('fs'); const c=JSON.parse(fs.readFileSync(process.argv[1],'utf8')); console.log(c.runner_lib.coverage_pct);" "$COVERAGE_OUTPUT")
  executed_lines=$(node -e "const fs=require('fs'); const c=JSON.parse(fs.readFileSync(process.argv[1],'utf8')); console.log(c.runner_lib.executed_lines);" "$COVERAGE_OUTPUT")
  total_lines=$(node -e "const fs=require('fs'); const c=JSON.parse(fs.readFileSync(process.argv[1],'utf8')); console.log(c.runner_lib.total_coverable_lines);" "$COVERAGE_OUTPUT")
  modules_covered=$(node -e "const fs=require('fs'); const c=JSON.parse(fs.readFileSync(process.argv[1],'utf8')); console.log(c.runner_lib.modules_covered);" "$COVERAGE_OUTPUT")
  total_modules=$(node -e "const fs=require('fs'); const c=JSON.parse(fs.readFileSync(process.argv[1],'utf8')); console.log(c.runner_lib.total_modules);" "$COVERAGE_OUTPUT")

  echo ""
  printf "  Coverage: %s%% (%s/%s executable lines, %s/%s modules)\n" \
    "$coverage_pct" "$executed_lines" "$total_lines" "$modules_covered" "$total_modules"
fi

if [[ ${#_FAILED_NAMES[@]} -gt 0 || $_SMOKE_EXIT -ne 0 ]]; then
  echo ""
  echo "  Failed:"
  for name in "${_FAILED_NAMES[@]}"; do
    echo "    - $name"
  done
  exit 1
fi

exit 0
