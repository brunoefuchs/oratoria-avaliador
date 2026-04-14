#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER-LIB: pipeline-bootstrap.sh — One-line bootstrap for autonomous runners
# ═══════════════════════════════════════════════════════════════════════════════
# Sources all runner-lib + validator-lib modules with graceful fallback.
# Sets availability flags for each module family.
#
# Usage (in your runner script):
#   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
#   source "$REPO_ROOT/infrastructure/scripts/runner-lib/pipeline-bootstrap.sh"
#
# After sourcing, check flags:
#   RUNNER_LIB_LOADED        — core runner-lib (runtime, metrics, models)
#   RUNNER_LIB_STATE_MANAGER — state-manager.sh
#   RUNNER_LIB_PROGRESS_LOGGER — progress-logger.sh
#   RUNNER_LIB_DISPLAY       — display.sh
#   RUNNER_LIB_ARG_PARSER    — arg-parser.sh
#   RUNNER_LIB_PYTHON_RESOLVER — python-resolver.sh
#   VALIDATOR_LIB_LOADED     — validator-lib (colors, scoring, security, reporting)

_BOOTSTRAP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_BOOTSTRAP_REPO_ROOT="${REPO_ROOT:-$(cd "$_BOOTSTRAP_DIR/../../.." && pwd)}"

# ── Initialize flags ──
RUNNER_LIB_LOADED=false
RUNNER_LIB_STATE_MANAGER=false
RUNNER_LIB_PROGRESS_LOGGER=false
RUNNER_LIB_DISPLAY=false
RUNNER_LIB_ARG_PARSER=false
RUNNER_LIB_PYTHON_RESOLVER=false
RUNNER_LIB_JSON_VALIDATOR=false
RUNNER_LIB_JSON_REPAIR=false
RUNNER_LIB_EVIDENCE=false
VALIDATOR_LIB_LOADED=false

# ── Load runner-lib core (existing + v2 modules via loader.sh) ──
if [[ -f "$_BOOTSTRAP_DIR/loader.sh" ]]; then
  source "$_BOOTSTRAP_DIR/loader.sh"
  RUNNER_LIB_LOADED=true
fi

# ── Backward-compatible fallback if loader.sh predates v2 modules ──
if [[ "${RUNNER_LIB_STATE_MANAGER:-false}" != "true" && -f "$_BOOTSTRAP_DIR/state-manager.sh" ]]; then
  source "$_BOOTSTRAP_DIR/state-manager.sh"
fi
if [[ "${RUNNER_LIB_PROGRESS_LOGGER:-false}" != "true" && -f "$_BOOTSTRAP_DIR/progress-logger.sh" ]]; then
  source "$_BOOTSTRAP_DIR/progress-logger.sh"
fi
if [[ "${RUNNER_LIB_DISPLAY:-false}" != "true" && -f "$_BOOTSTRAP_DIR/display.sh" ]]; then
  source "$_BOOTSTRAP_DIR/display.sh"
fi
if [[ "${RUNNER_LIB_ARG_PARSER:-false}" != "true" && -f "$_BOOTSTRAP_DIR/arg-parser.sh" ]]; then
  source "$_BOOTSTRAP_DIR/arg-parser.sh"
fi
if [[ "${RUNNER_LIB_PYTHON_RESOLVER:-false}" != "true" && -f "$_BOOTSTRAP_DIR/python-resolver.sh" ]]; then
  source "$_BOOTSTRAP_DIR/python-resolver.sh"
fi
if [[ "${RUNNER_LIB_JSON_VALIDATOR:-false}" != "true" && -f "$_BOOTSTRAP_DIR/json-validator.sh" ]]; then
  source "$_BOOTSTRAP_DIR/json-validator.sh"
fi
if [[ "${RUNNER_LIB_EVIDENCE:-false}" != "true" && -f "$_BOOTSTRAP_DIR/evidence.sh" ]]; then
  source "$_BOOTSTRAP_DIR/evidence.sh"
  RUNNER_LIB_EVIDENCE=true
fi

# ── JSON Repair (Python, not sourced — detected for availability flag) ──
if [[ -f "$_BOOTSTRAP_DIR/json-repair.py" ]]; then
  RUNNER_LIB_JSON_REPAIR=true
  RUNNER_LIB_JSON_REPAIR_PATH="$_BOOTSTRAP_DIR/json-repair.py"
  export RUNNER_LIB_JSON_REPAIR RUNNER_LIB_JSON_REPAIR_PATH
fi

# ── Load validator-lib (if available) ──
_VLIB_DIR="$_BOOTSTRAP_REPO_ROOT/infrastructure/scripts/validator-lib"
if [[ -f "$_VLIB_DIR/loader.sh" ]]; then
  source "$_VLIB_DIR/loader.sh"
  VALIDATOR_LIB_LOADED=true
fi

# ── SMOKE_TEST mock (Story 101.14 AC13) ──
# When SMOKE_TEST=true, override _exec_runtime to return mock output.
# This allows running any runner end-to-end without an LLM:
#   SMOKE_TEST=true bash books.sh test-slug --max-turns 1
if [[ "${SMOKE_TEST:-false}" == "true" ]]; then
  _exec_runtime() {
    local model="$1" prompt_file="$2" output_file="$3"
    cat > /dev/null < "$prompt_file"
    printf 'SMOKE_TEST mock output from %s\n' "$model" > "$output_file"
    return 0
  }
fi

# ── Phase evidence helpers (Story 115.12) ──
bootstrap_phase_start() {
  local phase="$1"
  local actual="${2:-phase started}"

  if declare -f evidence_record >/dev/null 2>&1; then
    evidence_record "$phase" "phase_start" "$actual" "PASS"
  fi
}

bootstrap_phase_end() {
  local phase="$1"
  local status="${2:-PASS}"
  local actual="${3:-phase completed}"

  if declare -f evidence_record >/dev/null 2>&1; then
    evidence_record "$phase" "phase_end" "$actual" "$status"
  fi
}
