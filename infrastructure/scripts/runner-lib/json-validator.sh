#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER-LIB: json-validator.sh — Extract and validate JSON from LLM output
# ═══════════════════════════════════════════════════════════════════════════════
# LLMs often return JSON wrapped in markdown, with trailing text, or truncated.
# This module provides safe extraction + validation + field access.
#
# Pattern: Template → LLM → json_extract → json_validate → json_get
#
# Used by: validate-skill.sh, validate-squad.sh, sinkra-validate.sh

# Extract the first valid JSON object from LLM output.
# Strips: markdown code blocks, leading/trailing text, BOM.
# Usage: json_extract <raw_text>
# Returns: clean JSON string (or empty if no JSON found)
json_extract() {
  local raw="$1"
  local candidate validated

  # Try 1: Extract from ```json ... ``` code block
  candidate=$(printf '%s\n' "$raw" | sed -n '/```json/,/```/{/```/d;p}' 2>/dev/null)
  if [[ -n "$candidate" ]]; then
    validated=$(printf '%s' "$candidate" | jq -c . 2>/dev/null)
    if [[ -n "$validated" ]]; then printf '%s' "$(head -1 <<< "$validated")"; return 0; fi
  fi

  # Try 2: Extract from ``` ... ``` (no language tag)
  candidate=$(printf '%s\n' "$raw" | sed -n '/^```$/,/^```$/{/^```$/d;p}' 2>/dev/null)
  if [[ -n "$candidate" ]]; then
    validated=$(printf '%s' "$candidate" | jq -c . 2>/dev/null)
    if [[ -n "$validated" ]]; then printf '%s' "$validated"; return 0; fi
  fi

  # Try 3: Find first { ... } block
  candidate=$(printf '%s\n' "$raw" | sed -n '/^[[:space:]]*{/,/^[[:space:]]*}/p' 2>/dev/null)
  if [[ -n "$candidate" ]]; then
    validated=$(printf '%s' "$candidate" | jq -c . 2>/dev/null)
    if [[ -n "$validated" ]]; then printf '%s' "$validated"; return 0; fi
  fi

  # Try 4: Python fallback — find first balanced JSON object
  if command -v python3 >/dev/null 2>&1; then
    validated=$(printf '%s' "$raw" | python3 -c "
import sys, json
text = sys.stdin.read()
idx = text.find('{')
if idx == -1: sys.exit(1)
text = text[idx:]
for end in range(len(text), 0, -1):
    try:
        obj = json.loads(text[:end])
        print(json.dumps(obj, ensure_ascii=False))
        sys.exit(0)
    except: continue
sys.exit(1)
" 2>/dev/null)
    if [[ -n "$validated" ]]; then printf '%s' "$(head -1 <<< "$validated")"; return 0; fi
  fi

  return 1
}

# Validate that a string is valid JSON.
# Usage: json_validate <json_string>
# Returns: 0=valid, 1=invalid
json_validate() {
  local json="$1"
  if [[ -z "$json" ]]; then
    return 1
  fi
  printf '%s' "$json" | jq empty 2>/dev/null
}

# Get a field from JSON with a default value.
# Usage: json_get <json_string> <jq_path> [default]
# Example: json_get "$response" '.score' '0'
json_get() {
  local json="$1"
  local path="$2"
  local default="${3:-}"

  if [[ -z "$json" ]]; then
    printf '%s' "$default"
    return
  fi

  local val
  val=$(printf '%s' "$json" | jq -r "$path // empty" 2>/dev/null)
  if [[ -n "$val" && "$val" != "null" ]]; then
    printf '%s' "$val"
  else
    printf '%s' "$default"
  fi
}

# Extract JSON from LLM output with retry support.
# Calls json_extract, and if it fails, invokes a retry callback.
# Usage: json_extract_or_retry <raw_text> <retry_callback> [max_retries]
# retry_callback receives no args and should print new LLM output to stdout.
# Returns: extracted JSON (or empty + return 1 if all retries fail)
json_extract_or_retry() {
  local raw="$1"
  local retry_fn="$2"
  local max_retries="${3:-1}"

  # First attempt
  local json
  json=$(json_extract "$raw")
  if [[ -n "$json" ]]; then
    printf '%s' "$json"
    return 0
  fi

  # Retry loop
  local attempt=0
  while [[ "$attempt" -lt "$max_retries" ]]; do
    attempt=$((attempt + 1))
    if declare -f "$retry_fn" >/dev/null 2>&1; then
      local new_raw
      new_raw=$("$retry_fn" 2>/dev/null)
      json=$(json_extract "$new_raw")
      if [[ -n "$json" ]]; then
        printf '%s' "$json"
        return 0
      fi
    fi
  done

  return 1
}

# Validate JSON against required fields.
# Usage: json_has_fields <json_string> <field1> [field2] ...
# Returns: 0=all present, 1=missing (prints missing fields to stderr)
json_has_fields() {
  local json="$1"; shift
  local missing=()

  for field in "$@"; do
    local val
    val=$(printf '%s' "$json" | jq -r ".$field // empty" 2>/dev/null)
    if [[ -z "$val" ]]; then
      missing+=("$field")
    fi
  done

  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "[json-validator] missing fields: ${missing[*]}" >&2
    return 1
  fi
  return 0
}

# ── JSON Auto-Repair (delegates to json-repair.py) ──────────────────
# Usage: json_repair_file <path>    — repair single file in-place
# Usage: json_repair_dir <dir>      — repair all .json files in dir
# Returns: 0 always (repair is best-effort, never blocks pipeline)

json_repair_file() {
  local file="$1"
  if [[ "${RUNNER_LIB_JSON_REPAIR:-false}" == "true" && -f "${RUNNER_LIB_JSON_REPAIR_PATH:-}" ]]; then
    "${RUNNER_PYTHON_BIN:-python3}" "$RUNNER_LIB_JSON_REPAIR_PATH" --file "$file" 2>&1 || true
  fi
}

json_repair_dir() {
  local dir="$1"
  if [[ "${RUNNER_LIB_JSON_REPAIR:-false}" == "true" && -f "${RUNNER_LIB_JSON_REPAIR_PATH:-}" ]]; then
    "${RUNNER_PYTHON_BIN:-python3}" "$RUNNER_LIB_JSON_REPAIR_PATH" --dir "$dir" 2>&1 || true
  fi
}

RUNNER_LIB_JSON_VALIDATOR=true
