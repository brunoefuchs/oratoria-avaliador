#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER-LIB: evidence.sh — Execution evidence audit trail (L3-Quality)
# ═══════════════════════════════════════════════════════════════════════════════
# Records evidence entries and deviations during pipeline execution.
# Generates execution-evidence.json as audit artifact.
#
# Layer: L3-Quality (audit/observability)
# Design ref: GSD execution_evidence.json + deviation_log
#
# Requires: jq or python3 (for JSON generation)

# ── Internal storage (bash arrays) ──
_EVIDENCE_ENTRIES=()
_EVIDENCE_DEVIATIONS=()
_EVIDENCE_INITIALIZED=false

# ── Writability check ──
_evidence_can_write() {
  local output_dir="${OUTPUT_DIR:-}"
  if [[ -z "$output_dir" ]]; then
    return 1
  fi
  if [[ ! -d "$output_dir" ]]; then
    mkdir -p "$output_dir" 2>/dev/null || return 1
  fi
  if [[ ! -w "$output_dir" ]]; then
    return 1
  fi
  return 0
}

# Initialize evidence collection.
# Usage: evidence_init
evidence_init() {
  _EVIDENCE_ENTRIES=()
  _EVIDENCE_DEVIATIONS=()
  _EVIDENCE_INITIALIZED=true
}

# Record an evidence entry for a pipeline phase.
# Usage: evidence_record <phase> <claim> <actual> <status>
#   phase:  phase name/number (e.g., "phase_1", "bootstrap")
#   claim:  what was expected (e.g., "state file created")
#   actual: what actually happened (e.g., "state file created at /tmp/state.json")
#   status: PASS | FAIL | SKIP
evidence_record() {
  local phase="${1:?evidence_record requires phase}"
  local claim="${2:?evidence_record requires claim}"
  local actual="${3:?evidence_record requires actual}"
  local status="${4:?evidence_record requires status}"

  if [[ "$_EVIDENCE_INITIALIZED" != "true" ]]; then
    evidence_init
  fi

  local ts
  ts=$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S)

  # Store as pipe-delimited string (avoids nested quoting issues)
  _EVIDENCE_ENTRIES+=("${ts}|${phase}|${claim}|${actual}|${status}")
}

# Record a deviation (unexpected divergence from plan).
# Usage: evidence_deviation <phase> <severity> <description>
#   severity: inline (quick fix, no replan) | architectural (replan needed)
evidence_deviation() {
  local phase="${1:?evidence_deviation requires phase}"
  local severity="${2:?evidence_deviation requires severity}"
  local description="${3:?evidence_deviation requires description}"

  if [[ "$_EVIDENCE_INITIALIZED" != "true" ]]; then
    evidence_init
  fi

  local ts
  ts=$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S)

  _EVIDENCE_DEVIATIONS+=("${ts}|${phase}|${severity}|${description}")
}

# Generate execution-evidence.json from accumulated entries.
# Usage: evidence_report
# Output: ${OUTPUT_DIR}/execution-evidence.json
# Returns: 0 on success, 1 if OUTPUT_DIR not writable (warning, non-blocking)
evidence_report() {
  if ! _evidence_can_write; then
    echo "[evidence] WARNING: OUTPUT_DIR not writable or unset, skipping evidence report" >&2
    return 1
  fi

  local output_file="${OUTPUT_DIR}/execution-evidence.json"
  local tmp_file="${output_file}.tmp"

  # Build JSON via jq or python3
  if command -v jq >/dev/null 2>&1; then
    _evidence_report_jq "$tmp_file"
  else
    _evidence_report_python "$tmp_file"
  fi

  if [[ -f "$tmp_file" ]]; then
    mv "$tmp_file" "$output_file"
    return 0
  fi
  return 1
}

_evidence_report_jq() {
  local tmp_file="$1"
  local entries_json="[]"
  local deviations_json="[]"

  for entry in "${_EVIDENCE_ENTRIES[@]}"; do
    IFS='|' read -r ts phase claim actual status <<< "$entry"
    entries_json=$(echo "$entries_json" | jq \
      --arg ts "$ts" --arg phase "$phase" \
      --arg claim "$claim" --arg actual "$actual" --arg status "$status" \
      '. += [{"timestamp": $ts, "phase": $phase, "claim": $claim, "actual": $actual, "status": $status}]')
  done

  for dev in "${_EVIDENCE_DEVIATIONS[@]}"; do
    IFS='|' read -r ts phase severity description <<< "$dev"
    deviations_json=$(echo "$deviations_json" | jq \
      --arg ts "$ts" --arg phase "$phase" \
      --arg severity "$severity" --arg desc "$description" \
      '. += [{"timestamp": $ts, "phase": $phase, "severity": $severity, "description": $desc}]')
  done

  local report_ts
  report_ts=$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S)

  jq -n \
    --arg ts "$report_ts" \
    --argjson entries "$entries_json" \
    --argjson deviations "$deviations_json" \
    --argjson entry_count "${#_EVIDENCE_ENTRIES[@]}" \
    --argjson deviation_count "${#_EVIDENCE_DEVIATIONS[@]}" \
    '{
      generated_at: $ts,
      summary: {
        total_entries: $entry_count,
        total_deviations: $deviation_count
      },
      entries: $entries,
      deviations: $deviations
    }' > "$tmp_file"
}

_evidence_report_python() {
  local tmp_file="$1"
  # Pass entries and deviations via temp files to avoid arg length limits
  local entries_tmp
  entries_tmp=$(mktemp)
  local deviations_tmp
  deviations_tmp=$(mktemp)
  printf '%s\n' "${_EVIDENCE_ENTRIES[@]}" > "$entries_tmp"
  printf '%s\n' "${_EVIDENCE_DEVIATIONS[@]}" > "$deviations_tmp"

  python3 - "$tmp_file" "$entries_tmp" "$deviations_tmp" <<'PYEOF'
import json, sys
from datetime import datetime

out_file, entries_file, deviations_file = sys.argv[1:4]

entries = []
with open(entries_file, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        parts = line.split('|', 4)
        if len(parts) == 5:
            entries.append({
                "timestamp": parts[0],
                "phase": parts[1],
                "claim": parts[2],
                "actual": parts[3],
                "status": parts[4],
            })

deviations = []
with open(deviations_file, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        parts = line.split('|', 3)
        if len(parts) == 4:
            deviations.append({
                "timestamp": parts[0],
                "phase": parts[1],
                "severity": parts[2],
                "description": parts[3],
            })

report = {
    "generated_at": datetime.now().isoformat(),
    "summary": {
        "total_entries": len(entries),
        "total_deviations": len(deviations),
    },
    "entries": entries,
    "deviations": deviations,
}

with open(out_file, 'w', encoding='utf-8', newline='\n') as fh:
    json.dump(report, fh, ensure_ascii=False, indent=2)
    fh.write('\n')
PYEOF

  rm -f "$entries_tmp" "$deviations_tmp"
}

RUNNER_LIB_EVIDENCE=true
