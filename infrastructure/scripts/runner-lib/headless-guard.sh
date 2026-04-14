#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# HEADLESS GUARD — Protection for Headless LLM Execution
# ═══════════════════════════════════════════════════════════════

# Filter stdout JSON/Markdown safely from CLI noise
filter_llm_output() {
  local output_text="$1"
  local log_file="${2:-/dev/null}"
  local metadata_log="${log_file%.log}.metadata.log"

  if [[ "$log_file" != "/dev/null" ]]; then
    echo "$output_text" | grep -E '^\s*\{"type":"result"|^\s*\{"error":|^\s*\{"type":"session|MODEL_CAPACITY_EXHAUSTED|GaxiosError:' >> "$metadata_log" 2>/dev/null || true
  fi

  echo "$output_text" \
    | grep -v '^\s*{"type":"result"' \
    | grep -v '^\s*{"error":' \
    | grep -v '^\s*{"type":"session' \
    | grep -v 'MODEL_CAPACITY_EXHAUSTED' \
    | grep -v 'Warning: Skipping extension' \
    | grep -v '^\s*at .*node_modules/' \
    | grep -v 'Path not in workspace' \
    | grep -v 'GaxiosError:' \
    | grep -v 'YOLO mode is enabled'
}

# Truncate context for the prompt to prevent overflow (~3KB limit)
truncate_prior_context() {
  local context_content="$1"
  local max_bytes="${2:-3072}"
  
  local current_bytes=${#context_content}
  if (( current_bytes > max_bytes )); then
    echo "${context_content:0:max_bytes}...[TRUNCATED: Exceeded ${max_bytes} bytes]"
  else
    echo "$context_content"
  fi
}

# Guard prompts against dangerous/protected paths
validate_no_protected_paths() {
  local prompt_file="$1"
  if [[ ! -f "$prompt_file" ]]; then return 0; fi

  if grep -qEo "(\.claude/agents|\.aiox-core/constitution)" "$prompt_file"; then
     echo "❌ [Headless Guard] Error: Prompt references protected paths." >&2
     return 1
  fi
  return 0
}

# Helper to build raw Claude CLI commands with safe boundaries
build_headless_cmd() {
  local prompt_file="$1"
  local timeout="${2:-120}"
  echo "claude -p \"\$(cat \"$prompt_file\")\""
}

# Count turns in a generic LLM run log stderr
count_bash_turns() {
  local log_file="$1"
  if [[ ! -f "$log_file" ]]; then
    echo 0
    return 0
  fi
  
  # Basic turn counting logic based on classic outputs
  grep -c -E "(^\[Turn|^API Request)" "$log_file" || echo 0
}
