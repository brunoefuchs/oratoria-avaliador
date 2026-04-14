#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER-LIB — Git Context Injection
# ═══════════════════════════════════════════════════════════════
# Generates recent git history (diffs + log) for a file, formatted
# as Markdown context suitable for injection into agent prompts.
#
# Usage:
#   result=$(generate_git_context "path/to/file.js")
#   result=$(generate_git_context "path/to/file.js" 4096)
#
# Budget allocation:
#   - 62% for diff (higher signal — shows what changed)
#   - 38% for log  (shows commit history / trajectory)
#
# Story: STORY-118.1 (Code-as-Feedback: Git History Context)

# ── Config (overridable) ──
GIT_CONTEXT_MAX_BYTES="${GIT_CONTEXT_MAX_BYTES:-8192}"
GIT_CONTEXT_DIFF_DEPTH="${GIT_CONTEXT_DIFF_DEPTH:-5}"
GIT_CONTEXT_MAX_COMMITS="${GIT_CONTEXT_MAX_COMMITS:-20}"
GIT_CONTEXT_TIMEOUT="${GIT_CONTEXT_TIMEOUT:-2}"

# ── Internal: portable timeout wrapper ──
# macOS ships without `timeout`; coreutils provides `gtimeout`.
# Falls back to running without timeout if neither is available.
_git_context_run_with_timeout() {
  local secs="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "$secs" "$@" 2>/dev/null
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$secs" "$@" 2>/dev/null
  else
    # No timeout utility — run directly
    "$@" 2>/dev/null
  fi
}

# ── Internal: determine safe diff depth for shallow repos ──
_git_context_safe_depth() {
  local requested="$1"
  local total
  total=$(_git_context_run_with_timeout "$GIT_CONTEXT_TIMEOUT" \
    git rev-list --count HEAD 2>/dev/null) || total=0
  total="${total:-0}"
  # Strip whitespace
  total=$(echo "$total" | tr -d '[:space:]')
  if [[ "$total" -le 0 ]]; then
    echo "0"
  elif [[ "$total" -lt "$requested" ]]; then
    echo "$total"
  else
    echo "$requested"
  fi
}

# ── Internal: get recent diff for a file ──
# Args: $1=file_path, $2=depth
# Prints: diff text (may be empty)
_git_context_diff() {
  local file_path="$1"
  local depth="$2"

  [[ "$depth" -le 0 ]] && return 0

  _git_context_run_with_timeout "$GIT_CONTEXT_TIMEOUT" \
    git diff "HEAD~${depth}" -- "$file_path" 2>/dev/null || true
}

# ── Internal: get commit log for a file ──
# Args: $1=file_path, $2=max_commits
# Prints: oneline log
_git_context_log() {
  local file_path="$1"
  local max_commits="$2"

  _git_context_run_with_timeout "$GIT_CONTEXT_TIMEOUT" \
    git log --oneline "-${max_commits}" -- "$file_path" 2>/dev/null || true
}

# ── Internal: count changed lines for summary ──
_git_context_count_changes() {
  local diff_text="$1"
  local adds=0
  local dels=0

  if [[ -n "$diff_text" ]]; then
    adds=$(echo "$diff_text" | grep -c '^+[^+]' 2>/dev/null || echo "0")
    dels=$(echo "$diff_text" | grep -c '^-[^-]' 2>/dev/null || echo "0")
  fi
  echo "${adds}+/${dels}-"
}

# ── Internal: count commits from log ──
_git_context_count_commits() {
  local log_text="$1"
  if [[ -z "$log_text" ]]; then
    echo "0"
  else
    echo "$log_text" | wc -l | tr -d '[:space:]'
  fi
}

# ── Internal: truncate text to byte limit ──
_git_context_truncate() {
  local text="$1"
  local max_bytes="$2"

  if [[ -z "$text" ]]; then
    echo ""
    return
  fi

  local actual_bytes
  actual_bytes=$(printf '%s' "$text" | wc -c | tr -d '[:space:]')

  if [[ "$actual_bytes" -le "$max_bytes" ]]; then
    echo "$text"
  else
    local marker="
[...truncated to ${max_bytes} bytes]"
    local marker_len
    marker_len=$(printf '%s' "$marker" | wc -c | tr -d '[:space:]')
    local content_budget=$(( max_bytes - marker_len ))
    if [[ "$content_budget" -lt 0 ]]; then
      content_budget=0
    fi
    printf '%s' "$text" | head -c "$content_budget"
    printf '%s\n' "$marker"
  fi
}

# ═══════════════════════════════════════════════════════════════
# generate_git_context — Main entry point
# ═══════════════════════════════════════════════════════════════
# Args: $1=file_path, $2=max_bytes (optional, default 8192)
# Prints: formatted Markdown context (or empty string on failure)
# Returns: 0 always (graceful — never fails the caller)
generate_git_context() {
  local file_path="${1:-}"
  local max_bytes="${2:-$GIT_CONTEXT_MAX_BYTES}"

  # Guard: no file path
  if [[ -z "$file_path" ]]; then
    return 0
  fi

  # Guard: git not available
  if ! command -v git >/dev/null 2>&1; then
    return 0
  fi

  # Guard: not in a git repo
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    return 0
  fi

  # Guard: file has no git history (new/untracked)
  local file_commits
  file_commits=$(_git_context_run_with_timeout "$GIT_CONTEXT_TIMEOUT" \
    git log --oneline -1 -- "$file_path" 2>/dev/null) || file_commits=""
  if [[ -z "$file_commits" ]]; then
    return 0
  fi

  # Determine safe depth
  local safe_depth
  safe_depth=$(_git_context_safe_depth "$GIT_CONTEXT_DIFF_DEPTH")

  # Budget: 62% diff, 38% log
  local diff_budget=$(( (max_bytes * 62) / 100 ))
  local log_budget=$(( (max_bytes * 38) / 100 ))

  # Fetch diff (FIRST — higher signal)
  local raw_diff=""
  if [[ "$safe_depth" -gt 0 ]]; then
    raw_diff=$(_git_context_diff "$file_path" "$safe_depth")
  fi
  local trimmed_diff
  trimmed_diff=$(_git_context_truncate "$raw_diff" "$diff_budget")

  # Fetch log (SECOND)
  local raw_log
  raw_log=$(_git_context_log "$file_path" "$GIT_CONTEXT_MAX_COMMITS")
  local trimmed_log
  trimmed_log=$(_git_context_truncate "$raw_log" "$log_budget")

  # Build summary
  local change_stats
  change_stats=$(_git_context_count_changes "$raw_diff")
  local commit_count
  commit_count=$(_git_context_count_commits "$raw_log")

  local summary="Git context for ${file_path}: ${commit_count} commits, ${change_stats} in last ${safe_depth} commits"

  # Format as Markdown
  local formatted=""
  formatted="### Git Context: ${file_path}"
  formatted="${formatted}
${summary}
"

  if [[ -n "$trimmed_diff" ]]; then
    formatted="${formatted}
#### Recent Diff (last ${safe_depth} commits)
\`\`\`diff
${trimmed_diff}
\`\`\`
"
  fi

  if [[ -n "$trimmed_log" ]]; then
    formatted="${formatted}
#### Commit Log (last ${commit_count} commits)
\`\`\`
${trimmed_log}
\`\`\`
"
  fi

  # Final byte check — trim entire output if needed
  local total_bytes
  total_bytes=$(printf '%s' "$formatted" | wc -c | tr -d '[:space:]')
  if [[ "$total_bytes" -gt "$max_bytes" ]]; then
    local marker="
[...git context truncated to ${max_bytes} bytes]"
    local marker_len
    marker_len=$(printf '%s' "$marker" | wc -c | tr -d '[:space:]')
    local content_budget=$(( max_bytes - marker_len ))
    if [[ "$content_budget" -lt 0 ]]; then
      content_budget=0
    fi
    printf '%s' "$formatted" | head -c "$content_budget"
    printf '%s\n' "$marker"
  else
    echo "$formatted"
  fi

  return 0
}
