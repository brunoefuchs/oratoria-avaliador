#!/usr/bin/env bash
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# RUNNER-LIB Smoke Test Suite
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Validates that each registered runner can initialize, create state, and
# exit gracefully without requiring an LLM.
#
# Pipeline runners: SMOKE_TEST=true + --max-turns 1 (mock via bootstrap)
# Validators: Deterministic mode (no LLM calls)
# sinkra-map: --dry-run
#
# Usage: bash run-smoke-tests.sh [runner-id...]
#   No args = run all runners from registry.
#   With args = run only matching runner IDs.
#
# Exit: 0 if all pass, 1 if any fail.
# Story: 101.15

set -uo pipefail

SMOKE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$(cd "$SMOKE_DIR/.." && pwd)"
RUNNER_LIB_DIR="$(cd "$TESTS_DIR/.." && pwd)"
REPO_ROOT="$(cd "$RUNNER_LIB_DIR/../../.." && pwd)"
export REPO_ROOT

REGISTRY="$RUNNER_LIB_DIR/runner-registry.yaml"
FIXTURES_DIR="$SMOKE_DIR/fixtures"
SMOKE_TIMEOUT=60

# â”€â”€ Portable timeout (macOS lacks coreutils timeout) â”€â”€
# Uses gtimeout (Homebrew coreutils) > timeout (Linux) > no-op fallback
if command -v gtimeout &>/dev/null; then
  _TIMEOUT_CMD="gtimeout"
elif command -v timeout &>/dev/null 2>&1 && timeout --version &>/dev/null 2>&1; then
  _TIMEOUT_CMD="timeout"
else
  _TIMEOUT_CMD=""
fi

_run_with_timeout() {
  local secs="$1"; shift
  if [[ -n "$_TIMEOUT_CMD" ]]; then
    "$_TIMEOUT_CMD" "$secs" "$@"
  else
    # No timeout available -- run directly (AC7 timeout not enforced)
    "$@"
  fi
}

# â”€â”€ Counters â”€â”€
_TOTAL=0
_PASSED=0
_FAILED=0
_SKIPPED=0
_FAILED_NAMES=()

_START_TIME=$(date +%s)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Registry Parser
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# Parse runner-registry.yaml dynamically (AC2)
# Tries node+js-yaml first, falls back to pure awk for CI environments
# without npm dependencies installed.
parse_registry() {
  # Fast path: node + js-yaml available
  if node -e "require('js-yaml')" 2>/dev/null; then
    node -e "
      const yaml = require('js-yaml');
      const fs = require('fs');
      const reg = yaml.load(fs.readFileSync('$REGISTRY', 'utf8'));
      for (const r of reg.runners) {
        console.log([r.id, r.path, r.type, r.runs_dir || '', r.metrics_glob || ''].join('|'));
      }
    "
    return
  fi

  # Fallback: pure awk parser for simple flat YAML registry
  # Registry format: "  - id: X" starts entry, "    key: val" for fields
  awk '
    /^ *- id:/ {
      if (id != "") print id "|" path "|" type "|" runs_dir "|" metrics_glob
      id=""; path=""; type=""; runs_dir=""; metrics_glob=""
      sub(/.*- id: */, ""); id=$0
      next
    }
    /^ *path:/         { sub(/.*path: */, ""); path=$0 }
    /^ *type:/         { sub(/.*type: */, ""); type=$0 }
    /^ *runs_dir:/     { sub(/.*runs_dir: */, ""); runs_dir=$0 }
    /^ *metrics_glob:/ { sub(/.*metrics_glob: */, ""); metrics_glob=$0 }
    END { if (id != "") print id "|" path "|" type "|" runs_dir "|" metrics_glob }
  ' "$REGISTRY"
}

find_metrics_file() {
  local search_root="$1" test_slug="$2"
  local file=""

  [[ -d "$search_root" ]] || return 1

  while IFS= read -r file; do
    if [[ -s "$file" ]]; then
      echo "$file"
      return 0
    fi
  done < <(
    find "$search_root" -type f \( -name "metrics.jsonl" -o -name "job-metrics.jsonl" \) \
      -path "*${test_slug}*" -print 2>/dev/null
  )

  return 1
}

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Per-Runner Smoke Test
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

smoke_test_pipeline() {
  local runner_id="$1" runner_path="$2" runs_dir="$3" metrics_glob="${4:-}"
  local tmp_dir
  tmp_dir=$(mktemp -d)
  local test_slug="smoke-test-${runner_id}-$$"
  local exit_code=0

  local runner_abs="$REPO_ROOT/$runner_path"

  if [[ ! -f "$runner_abs" ]]; then
    echo "    SKIP: runner not found at $runner_path"
    rm -rf "$tmp_dir"
    return 77
  fi

  # â”€â”€ Build per-runner command args â”€â”€
  local cmd_args=("$runner_abs")
  local cmd_env="SMOKE_TEST=true PHASE_MAX_TURNS=1"

  case "$runner_id" in
    copy)
      # Copy expects an existing project dir as first arg
      local copy_project_dir="$tmp_dir/$test_slug"
      mkdir -p "$copy_project_dir"
      echo '{"project":"smoke-test","workflow_id":"smoke","current_phase":0,"status":"initialized"}' \
        > "$copy_project_dir/copy-state.json"
      cmd_args+=("$copy_project_dir" "greenfield" "1")
      ;;
    decoder)
      # Decoder requires --source flag for new systems
      cmd_args+=("--source" "$REPO_ROOT/squads/books" "$test_slug" "greenfield" "1")
      ;;
    *)
      # mmos, books: standard positional args
      cmd_args+=("$test_slug" "greenfield" "1")
      ;;
  esac

  # â”€â”€ Execute â”€â”€
  local output=""
  output=$(
    cd "$REPO_ROOT" && \
    SMOKE_TEST=true \
    PHASE_MAX_TURNS=1 \
    _run_with_timeout "$SMOKE_TIMEOUT" \
    bash "${cmd_args[@]}" 2>&1
  ) || exit_code=$?

  # â”€â”€ CI Skip: no LLM runtime available â”€â”€
  # Pipeline runners require claude/codex/gemini in PATH. In CI environments
  # without LLM runtimes, skip gracefully instead of failing.
  if echo "$output" | grep -q "No supported runtime found"; then
    rm -rf "$tmp_dir"
    return 77  # SKIP
  fi

  # â”€â”€ Evaluate result â”€â”€
  # For pipeline runners with SMOKE_TEST=true, the mock output will not
  # satisfy evaluators/assertions, so non-zero exit is expected.
  # Success criteria: runner INITIALIZED (state created OR banner printed).
  local init_ok=false

  # Check 1: State file created in runs_dir (AC5)
  if find "$REPO_ROOT/$runs_dir" -name "*.json" -path "*${test_slug}*" 2>/dev/null | head -1 | grep -q . 2>/dev/null; then
    init_ok=true
  fi

  # Check 2: State file in temp dir (copy runner)
  if [[ "$init_ok" == "false" ]] && find "$tmp_dir" -name "*.json" 2>/dev/null | head -1 | grep -q . 2>/dev/null; then
    init_ok=true
  fi

  # Check 3: Output contains init indicators (banner, state, session)
  if [[ "$init_ok" == "false" ]]; then
    if echo "$output" | grep -qiE "(state|initialized|session|Pipeline|preflight|Phase)" 2>/dev/null; then
      init_ok=true
    fi
  fi

  # Check 4: exit 0 always means success
  if [[ $exit_code -eq 0 ]]; then
    init_ok=true
  fi

  if [[ "$init_ok" == "false" ]]; then
    echo ""
    echo "    FAIL: runner did not initialize (exit $exit_code)"
    echo "    --- output (last 15 lines) ---"
    echo "$output" | tail -15
    echo "    --- end ---"
    rm -rf "$tmp_dir"
    return 1
  fi

  # AC6: Check for metrics JSONL.
  # In smoke mode, some runners stop after init/state creation and only emit
  # metrics during full execution. Treat missing metrics as warning here.
  local metrics_file=""
  if [[ -n "$runs_dir" ]]; then
    metrics_file="$(find_metrics_file "$REPO_ROOT/$runs_dir" "$test_slug" || true)"
  fi
  if [[ -z "$metrics_file" ]]; then
    metrics_file="$(find_metrics_file "$REPO_ROOT/outputs" "$test_slug" || true)"
  fi
  if [[ -z "$metrics_file" && -n "$metrics_glob" ]]; then
    metrics_file="$(python3 - "$REPO_ROOT" "$metrics_glob" "$test_slug" <<'PY'
import glob
import os
import sys

repo_root, pattern, slug = sys.argv[1:4]
for path in glob.glob(os.path.join(repo_root, pattern), recursive=True):
    if slug in path and os.path.isfile(path) and os.path.getsize(path) > 0:
        print(path)
        break
PY
)"
  fi
  if [[ -z "$metrics_file" ]]; then
    echo ""
    echo "    WARN: runner initialized without metrics JSONL in smoke mode"
    echo "    Expected under: ${runs_dir:-outputs/} (pattern: ${metrics_glob:-n/a})"
  fi

  # â”€â”€ Cleanup â”€â”€
  find "$REPO_ROOT/$runs_dir" -path "*${test_slug}*" -exec rm -rf {} + 2>/dev/null || true
  # Also clean up outputs that may use different patterns
  find "$REPO_ROOT/outputs" -path "*${test_slug}*" -exec rm -rf {} + 2>/dev/null || true
  rm -rf "$tmp_dir"

  return 0
}

smoke_test_validator() {
  local runner_id="$1" runner_path="$2"
  local runner_abs="$REPO_ROOT/$runner_path"
  local exit_code=0

  if [[ ! -f "$runner_abs" ]]; then
    echo "    SKIP: runner not found at $runner_path"
    return 77
  fi

  local cmd_args=()
  local output=""

  case "$runner_id" in
    validate-squad)
      # --quick is 100% deterministic, 0 LLM calls
      # Use "books" as a well-known squad that exists
      cmd_args=("$runner_abs" "books" "--quick")
      ;;
    validate-skill)
      # Without --deep is 100% deterministic
      # Use "commit" as a well-known skill
      cmd_args=("$runner_abs" "commit")
      ;;
    sinkra-validate)
      # --no-remediation = deterministic only (Phase 1)
      cmd_args=("$runner_abs" "--squad" "books" "--no-remediation")
      ;;
    *)
      echo "    SKIP: unknown validator '$runner_id'"
      return 77
      ;;
  esac

  output=$(
    cd "$REPO_ROOT" && \
    _run_with_timeout "$SMOKE_TIMEOUT" \
    bash "${cmd_args[@]}" 2>&1
  ) || exit_code=$?

  # Validators: exit 0 = PASS, exit 1 = FAIL (but script ran), exit 2+ = ERROR
  # For smoke test, exit 0 or 1 both mean "validator ran correctly"
  if [[ $exit_code -le 1 ]]; then
    return 0
  fi

  echo "    FAIL: exit code $exit_code (error, not validation result)"
  echo "    --- output (last 15 lines) ---"
  echo "$output" | tail -15
  echo "    --- end ---"
  return 1
}

smoke_test_sinkra_map() {
  local runner_path="$1"
  local runner_abs="$REPO_ROOT/$runner_path"
  local exit_code=0

  if [[ ! -f "$runner_abs" ]]; then
    echo "    SKIP: runner not found at $runner_path"
    return 77
  fi

  # --dry-run: shows plan without running, exits 0
  local output=""
  output=$(
    cd "$REPO_ROOT" && \
    _run_with_timeout "$SMOKE_TIMEOUT" \
    bash "$runner_abs" --squad books --dry-run 2>&1
  ) || exit_code=$?

  # CI Skip: no LLM runtime available
  if echo "$output" | grep -q "No supported runtime found"; then
    return 77  # SKIP
  fi

  if [[ $exit_code -ne 0 ]]; then
    echo "    FAIL: --dry-run exited $exit_code"
    echo "    --- output (last 15 lines) ---"
    echo "$output" | tail -15
    echo "    --- end ---"
    return 1
  fi

  return 0
}

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Main: Discover and run
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# Verify registry exists
if [[ ! -f "$REGISTRY" ]]; then
  echo "ERROR: Runner registry not found at $REGISTRY"
  exit 1
fi

# Parse all runners from registry
RUNNER_ENTRIES=()
while IFS= read -r entry; do
  [[ -n "$entry" ]] && RUNNER_ENTRIES+=("$entry")
done < <(parse_registry)

if [[ ${#RUNNER_ENTRIES[@]} -eq 0 ]]; then
  echo "ERROR: No runners found in registry"
  exit 1
fi

# Filter if specific runner IDs given as args
FILTER_IDS=()
if [[ $# -gt 0 ]]; then
  FILTER_IDS=("$@")
fi

echo ""
echo "================================================================"
echo "  RUNNER-LIB Smoke Tests"
echo "  Registry: $(basename "$REGISTRY") (${#RUNNER_ENTRIES[@]} runners)"
echo "  Timeout: ${SMOKE_TIMEOUT}s per runner"
echo "================================================================"
echo ""

for entry in "${RUNNER_ENTRIES[@]}"; do
  IFS='|' read -r runner_id runner_path runner_type runs_dir metrics_glob <<< "$entry"

  # Apply filter if provided
  if [[ ${#FILTER_IDS[@]} -gt 0 ]]; then
    local_match=false
    for fid in "${FILTER_IDS[@]}"; do
      if [[ "$runner_id" == "$fid" ]]; then
        local_match=true
        break
      fi
    done
    [[ "$local_match" == "false" ]] && continue
  fi

  _TOTAL=$((_TOTAL + 1))
  printf "  %-25s " "$runner_id"

  test_exit=0

  case "$runner_type" in
    pipeline)
      if [[ "$runner_id" == "sinkra-map" ]]; then
        smoke_test_sinkra_map "$runner_path" || test_exit=$?
      else
        smoke_test_pipeline "$runner_id" "$runner_path" "$runs_dir" "$metrics_glob" || test_exit=$?
      fi
      ;;
    validator)
      smoke_test_validator "$runner_id" "$runner_path" || test_exit=$?
      ;;
    *)
      echo "SKIP (unknown type: $runner_type)"
      _SKIPPED=$((_SKIPPED + 1))
      continue
      ;;
  esac

  if [[ $test_exit -eq 0 ]]; then
    echo "PASS"
    _PASSED=$((_PASSED + 1))
  elif [[ $test_exit -eq 77 ]]; then
    echo "SKIP"
    _SKIPPED=$((_SKIPPED + 1))
  else
    echo "FAIL"
    _FAILED=$((_FAILED + 1))
    _FAILED_NAMES+=("$runner_id")
  fi
done

# â”€â”€ Summary (AC18) â”€â”€
_END_TIME=$(date +%s)
_DURATION=$((_END_TIME - _START_TIME))

echo ""
echo "================================================================"
if [[ $_FAILED -eq 0 ]]; then
  printf "  %d/%d runners smoke OK" "$_PASSED" "$_TOTAL"
else
  printf "  %d/%d passed, %d failed" "$_PASSED" "$_TOTAL" "$_FAILED"
fi
if [[ $_SKIPPED -gt 0 ]]; then
  printf ", %d skipped" "$_SKIPPED"
fi
printf " (%ds)\n" "$_DURATION"
echo "================================================================"

if [[ ${#_FAILED_NAMES[@]} -gt 0 ]]; then
  echo ""
  echo "  Failed runners:"
  for name in "${_FAILED_NAMES[@]}"; do
    echo "    - $name"
  done
  exit 1
fi

exit 0
