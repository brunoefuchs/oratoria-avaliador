#!/usr/bin/env bash

set -euo pipefail

# === CUSTOMIZE ===
RUNNER_NAME="__RUNNER_NAME__"
SQUAD_SLUG="__SQUAD_SLUG__"
OUTPUT_KIND="__OUTPUT_KIND__"
DEFAULT_MODEL="${RUNNER_MODEL:-opus}"
DEFAULT_MODE="${RUNNER_MODE:-greenfield}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
RUNNER_LIB_DIR="$REPO_ROOT/infrastructure/scripts/runner-lib"
OUTPUT_ROOT="${RUNNER_OUTPUT_ROOT:-$REPO_ROOT/outputs/$SQUAD_SLUG/$OUTPUT_KIND}"

source "$RUNNER_LIB_DIR/pipeline-bootstrap.sh"

RUNNER_LIB_RUNTIME=true
SESSION_TRACKING=true

TARGET_SLUG=""
MODE="$DEFAULT_MODE"
DRY_RUN="false"
MAX_COST="${RUNNER_MAX_COST:-}"
STATE_FILE=""
RUN_DIR=""
METRICS_FILE=""
LOG_DIR=""

cleanup() {
  local exit_code=$?
  if [[ -n "${STATE_FILE:-}" && -f "${STATE_FILE:-}" && $exit_code -ne 0 ]]; then
    state_update --arg status "failed" '.status = $status' "$STATE_FILE" || true
  fi
}
trap cleanup EXIT

show_help() {
  cat <<EOF
$RUNNER_NAME runner

Usage:
  $(basename "$0") <target-slug> [greenfield|brownfield] [--dry-run] [--max-cost USD]

Flags:
  --dry-run         Skips LLM call and writes fixture output
  --max-cost <usd>  Stops after phase if accumulated cost exceeds cap
EOF
}

parse_args() {
  local positional=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        show_help
        exit 0
        ;;
      --dry-run)
        DRY_RUN="true"
        shift
        ;;
      --max-cost)
        MAX_COST="${2:?Missing value for --max-cost}"
        shift 2
        ;;
      *)
        positional+=("$1")
        shift
        ;;
    esac
  done

  if [[ ${#positional[@]} -lt 1 ]]; then
    show_help
    exit 1
  fi

  TARGET_SLUG="${positional[0]}"
  MODE="${positional[1]:-$DEFAULT_MODE}"
}

build_phase_prompt() {
  local phase_id="$1"
  local target_slug="$2"

  cat <<EOF
# ${RUNNER_NAME} — ${phase_id}

Read source files FIRST, then write artifacts.

Target: ${target_slug}
Mode: ${MODE}
Phase: ${phase_id}

Deliver only the artifact content required for this phase.
EOF
}

init_run() {
  local timestamp
  timestamp="$(date +%Y%m%d-%H%M%S)"
  RUN_DIR="$OUTPUT_ROOT/${timestamp}-${TARGET_SLUG}"
  LOG_DIR="$RUN_DIR/logs"
  STATE_FILE="$RUN_DIR/state.json"
  METRICS_FILE="$RUN_DIR/metrics.jsonl"

  mkdir -p "$RUN_DIR" "$LOG_DIR"
  state_init "$STATE_FILE" "$TARGET_SLUG" "runner" "{\"mode\":\"$MODE\",\"runner\":\"$RUNNER_NAME\"}"
  state_update --arg status "running" '.status = $status' "$STATE_FILE"
}

run_phase() {
  local phase_id="$1"
  local phase_num="$2"
  local prompt
  local log_file="$LOG_DIR/${phase_id}.log"
  local output_file="$RUN_DIR/${phase_id}.md"
  local raw_output=""

  prompt="$(build_phase_prompt "$phase_id" "$TARGET_SLUG")"
  prompt="$(truncate_prior_context "$prompt" 6000)"

  state_phase_update "$STATE_FILE" "$phase_id" "running" "$RUNNER_NAME"
  state_update --argjson phase "$phase_num" '.current_phase = $phase' "$STATE_FILE"

  if [[ "$DRY_RUN" == "true" ]]; then
    raw_output="# ${phase_id}\n\nDry-run output for ${TARGET_SLUG}."
  else
    raw_output="$(run_llm_prompt "$DEFAULT_MODEL" "$prompt" "$log_file" "$phase_id")"
  fi

  raw_output="$(filter_llm_output "$raw_output" "$log_file")"
  printf '%s\n' "$raw_output" > "$output_file"

  check_cost_cap "$MAX_COST" || return 75

  state_phase_update "$STATE_FILE" "$phase_id" "complete" "$RUNNER_NAME"
  state_add_artifact "$STATE_FILE" "$output_file"
}

main() {
  parse_args "$@"
  init_run

  # === CUSTOMIZE ===
  run_phase "phase-1-discovery" 1
  run_phase "phase-2-delivery" 2

  state_complete "$STATE_FILE" 0
  echo "Artifacts written to: $RUN_DIR"
}

main "$@"
