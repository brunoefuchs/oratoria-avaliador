#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER-LIB: progress-logger.sh — Standardized markdown progress logging
# ═══════════════════════════════════════════════════════════════════════════════
# Appends structured markdown entries to a progress file (progress.txt).
# Used by: sinkra-map.sh, mmos.sh, copy.sh, books.sh, swipe.sh

# Set the progress file path. Call once before other functions.
# Usage: progress_init <file_path> <pipeline_name> [target_name]
progress_init() {
  PROGRESS_FILE="$1"
  local pipeline_name="$2"
  local target_name="${3:-}"
  _ensure_jsonl

  if [[ ! -f "$PROGRESS_FILE" ]]; then
    local dir
    dir=$(dirname "$PROGRESS_FILE")
    mkdir -p "$dir"
    {
      echo "# $pipeline_name Progress Log"
      [[ -n "$target_name" ]] && echo "**Target:** $target_name"
      echo "**Started:** $(date +%Y-%m-%d\ %H:%M:%S)"
      echo ""
      echo "---"
      echo ""
      echo "## Session Log"
      echo ""
    } > "$PROGRESS_FILE"
  fi

  if [[ -n "$_PROGRESS_JSONL_FILE" ]]; then
    mkdir -p "$(dirname "$_PROGRESS_JSONL_FILE")"
    touch "$_PROGRESS_JSONL_FILE"
    progress_log_jsonl "pipeline_init" "" "initialized" "{}"
  fi
}

# Log phase start.
# Usage: progress_phase_start <phase_num> <phase_label> [agent_name]
progress_phase_start() {
  local phase_num="$1"
  local phase_label="$2"
  local agent="${3:-}"
  [[ -z "$PROGRESS_FILE" ]] && return
  local extra_json="{}"
  if command -v jq >/dev/null 2>&1; then
    extra_json=$(jq -cn --arg label "$phase_label" --arg agent "$agent" '{label:$label,agent:$agent}')
  fi

  {
    echo ""
    echo "### Phase $phase_num: $phase_label"
    [[ -n "$agent" ]] && echo "**Agent:** @$agent"
    echo "**Started:** $(date +%H:%M:%S)"
  } >> "$PROGRESS_FILE"
  progress_log_jsonl "phase_start" "$phase_num" "running" "$extra_json"
}

# Log phase complete with optional notes.
# Usage: progress_phase_complete <phase_num> [status] [notes]
progress_phase_complete() {
  local phase_num="$1"
  local status="${2:-complete}"
  local notes="${3:-}"
  [[ -z "$PROGRESS_FILE" ]] && return

  {
    echo "**Completed:** $(date +%H:%M:%S) — $status"
    [[ -n "$notes" ]] && echo "$notes"
  } >> "$PROGRESS_FILE"
  progress_log_jsonl "phase_complete" "$phase_num" "$status" "{}"
}

# Log a checkpoint.
# Usage: progress_checkpoint <checkpoint_name> [details]
progress_checkpoint() {
  local name="$1"
  local details="${2:-}"
  [[ -z "$PROGRESS_FILE" ]] && return
  local extra_json="{}"
  if command -v jq >/dev/null 2>&1; then
    extra_json=$(jq -cn --arg details "$details" '{details:$details}')
  fi

  {
    echo ""
    echo "#### Checkpoint: $name — $(date +%H:%M:%S)"
    [[ -n "$details" ]] && echo "$details"
  } >> "$PROGRESS_FILE"
  progress_log_jsonl "checkpoint" "" "$name" "$extra_json"
}

# Log pipeline complete with duration.
# Usage: progress_pipeline_complete <duration_seconds> [artifact_count]
progress_pipeline_complete() {
  local duration="$1"
  local artifacts="${2:-0}"
  local minutes=$((duration / 60))
  [[ -z "$PROGRESS_FILE" ]] && return

  {
    echo ""
    echo "---"
    echo ""
    echo "## Pipeline Complete: $(date +%Y-%m-%d)"
    echo "- Total duration: ${minutes}m (${duration}s)"
    [[ "$artifacts" -gt 0 ]] && echo "- Artifacts: $artifacts files"
  } >> "$PROGRESS_FILE"
  progress_log_jsonl "pipeline_complete" "" "complete" "{\"duration_seconds\":$duration,\"artifacts\":$artifacts}"
}

# Log a freeform entry.
# Usage: progress_log <message>
progress_log() {
  [[ -z "$PROGRESS_FILE" ]] && return
  echo "$1" >> "$PROGRESS_FILE"
}

# ── JSONL Structured Logging (machine-readable) ──
# Companion to the markdown log. One JSON line per event.
# File: same dir as PROGRESS_FILE, named events.jsonl

# Initialize JSONL log path (auto-called by progress_init if available)
_PROGRESS_JSONL_FILE=""

_ensure_jsonl() {
  if [[ -z "$_PROGRESS_JSONL_FILE" && -n "${PROGRESS_FILE:-}" ]]; then
    _PROGRESS_JSONL_FILE="$(dirname "$PROGRESS_FILE")/events.jsonl"
  fi
}

# Log a structured event as JSONL.
# Usage: progress_log_jsonl <event_type> <phase> [status] [extra_json]
# Example: progress_log_jsonl "phase_start" "3" "running" '{"agent":"executor-classifier"}'
progress_log_jsonl() {
  _ensure_jsonl
  [[ -z "$_PROGRESS_JSONL_FILE" ]] && return

  local event_type="$1"
  local phase="${2:-}"
  local status="${3:-}"
  local _empty_json='{}'
  local extra="${4:-$_empty_json}"
  local ts
  ts=$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S)

  printf '{"ts":"%s","event":"%s","phase":"%s","status":"%s","data":%s}\n' \
    "$ts" "$event_type" "$phase" "$status" "$extra" >> "$_PROGRESS_JSONL_FILE"
}

RUNNER_LIB_PROGRESS_LOGGER=true
