#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER-LIB — Cross-Run Memory (JSONL History)
# ═══════════════════════════════════════════════════════════════
# Append-only JSONL log of run results per squad.
# Enables: which model works best for which phase? recurring failures?
#
# Usage:
#   record_run "phase_5" "true" "45000" "0.180" "timeout" "Phase exceeded 60s"
#   warn_recurring_failures "phase_5" "opus"
#   get_best_model_for_phase "phase_5" "sonnet"
#
# Story: RUNNER-2.3 (Cross-Run Memory + Context Compression)

# Config — overridable by caller
HISTORY_MAX_AGE_DAYS="${HISTORY_MAX_AGE_DAYS:-90}"
HISTORY_MAX_ENTRIES="${HISTORY_MAX_ENTRIES:-1000}"

# Resolve history file path.
# Uses $OUTPUT_DIR/run-history.jsonl if OUTPUT_DIR is set, else /tmp.
_resolve_history_file() {
  if [[ -n "${HISTORY_FILE:-}" ]]; then
    echo "$HISTORY_FILE"
  elif [[ -n "${OUTPUT_DIR:-}" ]]; then
    echo "$OUTPUT_DIR/run-history.jsonl"
  else
    echo "/tmp/runner-run-history.jsonl"
  fi
}

# Record a single phase execution result.
# Args: $1=phase, $2=success(true/false), $3=duration_ms, $4=cost_usd,
#       $5=error_type(optional), $6=error_msg(optional),
#       $7=doc_source(optional: context7|gitmcp|websearch|none)
record_run() {
  local phase="$1"
  local success="$2"
  local duration="${3:-0}"
  local cost="${4:-0}"
  local error_type="${5:-null}"
  local error_msg="${6:-null}"
  local doc_source="${7:-none}"
  local history_file
  history_file="$(_resolve_history_file)"

  # Ensure parent dir exists
  mkdir -p "$(dirname "$history_file")"

  local entry
  entry=$(jq -nc \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg run_id "${RUN_ID:-$(date +%Y%m%d-%H%M%S)-unknown}" \
    --arg squad "${SQUAD_SLUG:-${SQUAD_NAME:-unknown}}" \
    --arg phase "$phase" \
    --arg runtime "${SELECTED_RUNTIME:-unknown}" \
    --arg model "${MODEL:-${LAST_LLM_MODEL:-unknown}}" \
    --argjson success "$success" \
    --argjson duration "$duration" \
    --argjson cost "$cost" \
    --arg error_type "$error_type" \
    --arg error_msg "$error_msg" \
    --arg doc_source "$doc_source" \
    '{timestamp:$ts, run_id:$run_id, squad:$squad, phase:$phase,
      runtime:$runtime, model:$model, success:$success,
      duration_ms:$duration, cost_usd:$cost,
      error_type:$error_type, error_msg:$error_msg,
      doc_source:$doc_source}' 2>/dev/null)

  if [[ -n "$entry" ]]; then
    echo "$entry" >> "$history_file"
  fi
}

# Warn if a phase has failed N+ consecutive times with the same model.
# Args: $1=phase, $2=model, $3=threshold(default:3)
# Returns: 0=ok, 1=recurring failures detected (warning printed)
warn_recurring_failures() {
  local phase="$1"
  local model="$2"
  local threshold="${3:-3}"
  local history_file
  history_file="$(_resolve_history_file)"

  [[ ! -f "$history_file" ]] && return 0

  local consecutive_fails
  consecutive_fails=$(jq -rs "
    [.[] | select(.phase == \"$phase\" and .model == \"$model\")]
    | reverse | [limit($threshold; .[])]
    | map(select(.success == false)) | length
  " "$history_file" 2>/dev/null || echo "0")

  if [[ "${consecutive_fails:-0}" -ge "$threshold" ]]; then
    echo "  ⚠️  Phase $phase failed ${consecutive_fails}/${threshold} recent times with $model" >&2
    local suggested
    suggested=$(get_best_model_for_phase "$phase" "sonnet")
    if [[ "$suggested" != "$model" ]]; then
      echo "     Consider: --model $suggested" >&2
    fi
    return 1
  fi
  return 0
}

# Get the model with highest success rate for a given phase.
# Filters by current runtime to avoid cross-runtime suggestions.
# Args: $1=phase, $2=default_model
# Prints: model name
get_best_model_for_phase() {
  local phase="$1"
  local default_model="$2"
  local runtime="${SELECTED_RUNTIME:-claude}"
  local history_file
  history_file="$(_resolve_history_file)"

  [[ ! -f "$history_file" ]] && echo "$default_model" && return

  local best
  best=$(jq -rs "
    [.[] | select(.phase == \"$phase\" and .success == true and .runtime == \"$runtime\")]
    | group_by(.model)
    | map({model: .[0].model, count: length, avg_cost: ([.[].cost_usd] | add / length)})
    | sort_by(-.count, .avg_cost)
    | .[0].model // \"$default_model\"
  " "$history_file" 2>/dev/null)

  echo "${best:-$default_model}"
}

# Rotate history: archive entries older than HISTORY_MAX_AGE_DAYS.
# Called automatically if history exceeds HISTORY_MAX_ENTRIES.
rotate_history() {
  local history_file
  history_file="$(_resolve_history_file)"

  [[ ! -f "$history_file" ]] && return 0

  local count
  count=$(wc -l < "$history_file" | tr -d ' ')
  [[ "$count" -lt "$HISTORY_MAX_ENTRIES" ]] && return 0

  local cutoff_date
  cutoff_date=$(date -u -v-${HISTORY_MAX_AGE_DAYS}d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || \
                date -u -d "${HISTORY_MAX_AGE_DAYS} days ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || \
                echo "")

  if [[ -z "$cutoff_date" ]]; then
    echo "[memory] WARNING: Cannot compute cutoff date, skipping rotation" >&2
    return 0
  fi

  local archive_file="${history_file%.jsonl}-archive-$(date +%Y-%m).jsonl"

  # Move old entries to archive
  jq -r "select(.timestamp < \"$cutoff_date\")" "$history_file" >> "$archive_file" 2>/dev/null
  local kept
  kept=$(jq -c "select(.timestamp >= \"$cutoff_date\")" "$history_file" 2>/dev/null)

  if [[ -n "$kept" ]]; then
    echo "$kept" > "$history_file"
    echo "[memory] Rotated: kept $(echo "$kept" | wc -l | tr -d ' ') entries, archived to $(basename "$archive_file")" >&2
  fi
}
