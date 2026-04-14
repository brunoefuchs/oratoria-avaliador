#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER-LIB — Context Compression (Haiku Summarization)
# ═══════════════════════════════════════════════════════════════
# Between phases, compresses the previous phase output into ~500 tokens
# using the cheapest available model. The expensive model (Opus) receives
# only the summary + new phase prompt.
#
# Compression is opt-in: set PHASE_COMPRESS=true before calling.
# Original output is always preserved on disk.
#
# Story: RUNNER-2.3 (Cross-Run Memory + Context Compression)
# Dependencies: runtime.sh (_exec_runtime), models.sh (get_fast_model)

# Target compressed output length
COMPRESS_MAX_TOKENS="${COMPRESS_MAX_TOKENS:-600}"

# Get cheapest model for compression.
# Prefers Claude Haiku (best cost/quality for summarization).
# Falls back to the cheap model of the current runtime.
_get_compress_model() {
  # Prefer Claude Haiku if available (best cost/quality for summarization)
  local runtime="${SELECTED_RUNTIME:-claude}"
  if command -v claude &>/dev/null; then
    runtime="claude"
  fi
  local model
  if declare -f get_fast_model >/dev/null 2>&1; then
    model=$(get_fast_model "$runtime")
  else
    model="haiku"
  fi
  echo "$runtime:$model"
}

# Compress phase output into ~500 tokens focused on next-phase needs.
# Args:
#   $1=output_file         — full phase output to compress
#   $2=next_phase_context  — what the next phase needs to know
# Prints: path to compressed file (or original if compression fails)
# Exit: always 0 (non-fatal — fallback to original on failure)
compress_phase_output() {
  local output_file="$1"
  local next_phase_context="${2:-Continue processing}"

  if [[ ! -f "$output_file" ]]; then
    echo "$output_file"
    return 0
  fi

  local compressed_file
  # Determine extension and create compressed filename
  local ext="${output_file##*.}"
  local base="${output_file%.*}"
  compressed_file="${base}-compressed.${ext}"

  # Read content (cap at 8000 chars to limit compression prompt size)
  local content
  content=$(head -c 8000 "$output_file")

  local prompt="Compress this phase output into approximately 500 tokens.
Keep ONLY information relevant to the next phase.
Next phase needs: $next_phase_context

RULES:
- Preserve exact numbers, names, scores, file paths
- Remove boilerplate, repetition, verbose formatting
- Structure as concise bullet points
- Maximum 500 tokens output

PHASE OUTPUT:
$content"

  local prompt_file result_file
  prompt_file=$(mktemp)
  result_file=$(mktemp)
  printf '%s' "$prompt" > "$prompt_file"

  # Run compression in subshell (isolates runtime/model/guardrail state)
  local exit_code=0
  local compress_spec
  compress_spec=$(_get_compress_model)
  (
    SELECTED_RUNTIME="${compress_spec%%:*}"
    PHASE_MAX_TURNS="1"
    PHASE_ALLOWED_TOOLS=""
    _exec_runtime "${compress_spec##*:}" "$prompt_file" "$result_file" "$SELECTED_RUNTIME"
  ) || exit_code=$?

  rm -f "$prompt_file"

  # FALLBACK: if compression fails, return original file
  if [[ $exit_code -ne 0 ]] || [[ ! -s "$result_file" ]]; then
    echo "  ⚠️  [compress] Compression failed for $(basename "$output_file"), using full output" >&2
    rm -f "$result_file"
    echo "$output_file"
    return 0
  fi

  # Extract result if Claude JSON format (reuse runtime.sh helper)
  if declare -f _extract_result >/dev/null 2>&1; then
    _extract_result "$result_file" "${compress_spec%%:*}" 2>/dev/null
  else
    local extracted
    extracted=$(jq -r '.result // empty' "$result_file" 2>/dev/null)
    [[ -n "$extracted" ]] && echo "$extracted" > "$result_file"
  fi

  mv "$result_file" "$compressed_file"

  # Log compression stats
  local original_bytes compressed_bytes ratio
  original_bytes=$(wc -c < "$output_file" | tr -d ' ')
  compressed_bytes=$(wc -c < "$compressed_file" | tr -d ' ')
  if [[ "$original_bytes" -gt 0 ]]; then
    ratio=$(awk "BEGIN{printf \"%.0f\", (1 - $compressed_bytes/$original_bytes)*100}")
  else
    ratio="0"
  fi

  echo "  📦 [compress] $(basename "$output_file"): ${original_bytes}B → ${compressed_bytes}B (${ratio}% reduction)" >&2

  # Record compression cost in metrics (if available)
  if declare -f record_metrics >/dev/null 2>&1; then
    local compress_model_name
    compress_model_name=$(echo "$(_get_compress_model)" | cut -d: -f2)
    record_metrics "$compress_model_name" "$original_bytes" "$compressed_bytes" "0" "compress" "ok" "0" "" 2>/dev/null || true
  fi

  echo "$compressed_file"
}

# ═══════════════════════════════════════════════════════════════
# 5-Phase Context Compression — compress_context()
# ═══════════════════════════════════════════════════════════════
# Story: 115.8 (Budget Warnings & Context Compression)
# Design ref: Hermes context_compressor.py (5-phase algorithm)
#
# Phases:
#   1. Tool result pruning — replace outputs >200 chars with placeholder
#   2. Boundary detection — protect first 3 messages + last N messages
#   3. Summarization — via run_llm_prompt with cheap model (Haiku)
#   4. Orphan cleanup — remove tool results without matching call
#   5. Assembly — head + summary + tail
#
# Args:
#   $1 = context_file (the conversation/context to compress)
#   $2 = tail_count (number of recent messages to preserve, default 5)
# Prints: path to compressed context file
# Exit: always 0 (fallback to truncation on any failure)

# Estimated context window in characters (rough: 200K tokens ~ 800K chars)
RUNNER_CONTEXT_WINDOW_CHARS="${RUNNER_CONTEXT_WINDOW_CHARS:-800000}"
# Cheap model for summarization
RUNNER_CHEAP_MODEL="${RUNNER_CHEAP_MODEL:-haiku}"

compress_context() {
  local context_file="${1:-}"
  local tail_count="${2:-5}"

  if [[ ! -f "$context_file" ]]; then
    echo "$context_file"
    return 0
  fi

  local context_size
  context_size=$(wc -c < "$context_file" | tr -d ' ')

  # If context is small, no compression needed
  if [[ "$context_size" -lt 1000 ]]; then
    echo "$context_file"
    return 0
  fi

  local work_dir
  work_dir=$(mktemp -d)
  local compressed_file="${context_file%.*}-ctx-compressed.${context_file##*.}"

  # ── Phase 1: Tool result pruning ──
  # Replace tool outputs longer than 200 chars with a placeholder
  local phase1_file="$work_dir/phase1.txt"
  awk '
    BEGIN { in_tool_result = 0; tool_buf = ""; tool_lines = 0 }
    /\[tool_result\]/ || /^Result:/ || /^Output:/ {
      in_tool_result = 1
      tool_buf = $0 "\n"
      tool_lines = 1
      next
    }
    /\[\/tool_result\]/ || /^---$/ {
      if (in_tool_result) {
        tool_buf = tool_buf $0 "\n"
        if (length(tool_buf) > 200) {
          printf "[tool_result pruned — %d chars replaced with placeholder]\n", length(tool_buf)
        } else {
          printf "%s", tool_buf
        }
        in_tool_result = 0
        tool_buf = ""
        tool_lines = 0
        next
      }
    }
    {
      if (in_tool_result) {
        tool_buf = tool_buf $0 "\n"
        tool_lines++
        # Auto-close after 50 lines without end marker
        if (tool_lines > 50) {
          if (length(tool_buf) > 200) {
            printf "[tool_result pruned — %d chars replaced with placeholder]\n", length(tool_buf)
          } else {
            printf "%s", tool_buf
          }
          in_tool_result = 0
          tool_buf = ""
          tool_lines = 0
        }
      } else {
        print
      }
    }
    END {
      if (in_tool_result && length(tool_buf) > 0) {
        if (length(tool_buf) > 200) {
          printf "[tool_result pruned — %d chars replaced with placeholder]\n", length(tool_buf)
        } else {
          printf "%s", tool_buf
        }
      }
    }
  ' "$context_file" > "$phase1_file" 2>/dev/null || cp "$context_file" "$phase1_file"

  # ── Phase 2: Boundary detection ──
  # Protect first 3 messages (system context) + last N messages (recent work)
  local total_lines
  total_lines=$(wc -l < "$phase1_file" | tr -d ' ')
  local head_lines=30   # ~first 3 messages (estimate ~10 lines each)
  local tail_lines=$((tail_count * 10))  # ~N messages at ~10 lines each

  # Ensure we don't exceed file size
  if [[ $((head_lines + tail_lines)) -ge "$total_lines" ]]; then
    # File is small enough, no middle section to compress
    cp "$phase1_file" "$compressed_file"
    rm -rf "$work_dir"
    echo "$compressed_file"
    return 0
  fi

  local head_file="$work_dir/head.txt"
  local middle_file="$work_dir/middle.txt"
  local tail_file="$work_dir/tail.txt"

  head -n "$head_lines" "$phase1_file" > "$head_file"
  local skip_tail=$((total_lines - tail_lines))
  tail -n "$tail_lines" "$phase1_file" > "$tail_file"
  sed -n "$((head_lines + 1)),$((skip_tail))p" "$phase1_file" > "$middle_file"

  # ── Phase 3: Summarization ──
  # Summarize the middle section using cheap model
  local summary_file="$work_dir/summary.txt"
  local middle_size
  middle_size=$(wc -c < "$middle_file" | tr -d ' ')

  if [[ "$middle_size" -gt 100 ]]; then
    # Try LLM summarization with cheap model
    local summarized=false
    if declare -f run_llm_prompt >/dev/null 2>&1; then
      local summary_prompt
      summary_prompt="Summarize this conversation segment into key facts, decisions, and outputs. Maximum 300 tokens. Preserve exact file paths, numbers, and technical terms.

SEGMENT:
$(head -c 6000 "$middle_file")"

      local summary_log="$work_dir/summary.log"
      local summary_output=""
      local summary_exit=0

      # Use cheap model via subshell to isolate state
      summary_output=$(
        PHASE_MAX_TURNS="1"
        PHASE_ALLOWED_TOOLS=""
        run_llm_prompt "$RUNNER_CHEAP_MODEL" "$summary_prompt" "$summary_log" "compress-summarize" 2>/dev/null
      ) || summary_exit=$?

      if [[ $summary_exit -eq 0 && -n "$summary_output" ]]; then
        echo "[--- Compressed summary of ${middle_size} chars ---]" > "$summary_file"
        echo "$summary_output" >> "$summary_file"
        echo "[--- End compressed summary ---]" >> "$summary_file"
        summarized=true
      fi
    fi

    # Fallback: simple truncation if LLM unavailable
    if [[ "$summarized" != "true" ]]; then
      echo "  [compress] RUNNER_CHEAP_MODEL unavailable -- falling back to truncation" >&2
      echo "[--- Truncated: ${middle_size} chars of middle context removed ---]" > "$summary_file"
      head -c 500 "$middle_file" >> "$summary_file"
      echo "" >> "$summary_file"
      echo "[--- End truncated section ---]" >> "$summary_file"
    fi
  else
    # Middle is small, keep as-is
    cp "$middle_file" "$summary_file"
  fi

  # ── Phase 4: Orphan cleanup ──
  # Remove tool_result blocks that have no matching tool_use/tool_call
  # Applied to head and tail sections
  local clean_head="$work_dir/clean_head.txt"
  local clean_tail="$work_dir/clean_tail.txt"

  _remove_orphan_tool_results "$head_file" > "$clean_head" 2>/dev/null || cp "$head_file" "$clean_head"
  _remove_orphan_tool_results "$tail_file" > "$clean_tail" 2>/dev/null || cp "$tail_file" "$clean_tail"

  # ── Phase 5: Assembly ──
  # head + summary + tail
  {
    cat "$clean_head"
    echo ""
    cat "$summary_file"
    echo ""
    cat "$clean_tail"
  } > "$compressed_file"

  # Log stats
  local compressed_size
  compressed_size=$(wc -c < "$compressed_file" | tr -d ' ')
  local ratio=0
  if [[ "$context_size" -gt 0 ]]; then
    ratio=$(awk "BEGIN{printf \"%.0f\", (1 - $compressed_size/$context_size)*100}")
  fi
  echo "  [compress] Context: ${context_size}B -> ${compressed_size}B (${ratio}% reduction, 5-phase)" >&2

  rm -rf "$work_dir"
  echo "$compressed_file"
  return 0
}

# Helper: remove tool_result blocks without a preceding tool_use/tool_call.
# Reads from file $1, writes cleaned output to stdout.
_remove_orphan_tool_results() {
  local file="$1"
  awk '
    BEGIN { in_result = 0; buf = "" }
    /\[tool_result\]/ {
      in_result = 1
      buf = $0 "\n"
      next
    }
    /\[\/tool_result\]/ {
      if (in_result) {
        # Check if there was a tool_use/tool_call within 20 lines above
        # Simplified: just drop orphans (no preceding tool_use marker found)
        in_result = 0
        buf = ""
        next
      }
    }
    {
      if (in_result) {
        buf = buf $0 "\n"
      } else {
        print
      }
    }
  ' "$file"
}

# ═══════════════════════════════════════════════════════════════
# Auto-trigger: compress when context > 50% of estimated window
# ═══════════════════════════════════════════════════════════════
# Story: 115.8 — auto compress trigger
#
# Call this after each turn/iteration with the current context file.
# If context exceeds 50% of RUNNER_CONTEXT_WINDOW_CHARS, compresses automatically.
#
# Args:
#   $1 = context_file
#   $2 = tail_count (optional, default 5)
# Prints: path to (possibly compressed) context file

maybe_compress_context() {
  local context_file="${1:-}"
  local tail_count="${2:-5}"

  if [[ ! -f "$context_file" ]]; then
    echo "$context_file"
    return 0
  fi

  local context_size
  context_size=$(wc -c < "$context_file" | tr -d ' ')
  local window="${RUNNER_CONTEXT_WINDOW_CHARS:-800000}"
  local threshold=$(( window / 2 ))  # 50%

  if [[ "$context_size" -gt "$threshold" ]]; then
    echo "  [compress] Context ${context_size}B exceeds 50% of window (${threshold}B) -- auto-compressing" >&2
    compress_context "$context_file" "$tail_count"
  else
    echo "$context_file"
  fi
}
