#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER-LIB — Worktree Isolation
# ═══════════════════════════════════════════════════════════════
# Git worktree isolation for parallel job execution.
# Each parallel job gets an isolated worktree — no race conditions.
# Fallback to temp directory if git worktree is unavailable.
#
# Story: RUNNER-4.1 (Cross-Squad Dispatch + Worktree Isolation)

WORKTREE_BASE="${WORKTREE_BASE:-${TMPDIR:-/tmp}/runner-worktrees}"

# Create an isolated worktree for a session.
# Args: $1=session_id
# Prints: worktree path
# Returns: 0=created
worktree_create() {
  local session_id="$1"
  local worktree_path="$WORKTREE_BASE/${session_id}"

  mkdir -p "$WORKTREE_BASE"

  if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
    if git worktree add "$worktree_path" HEAD --detach 2>/dev/null; then
      echo "  🌳 [worktree] Created: $worktree_path" >&2
      echo "$worktree_path"
      return 0
    fi
  fi

  # Fallback: plain directory (no git isolation)
  echo "  ⚠️  [worktree] Git worktree not available, using temp directory" >&2
  mkdir -p "$worktree_path"
  echo "$worktree_path"
  return 0
}

# Merge outputs from worktree back to main directory.
# Only copies output artifacts (not code).
# Args: $1=worktree_path, $2=output_dir
# Returns: 0=merged
worktree_merge() {
  local worktree_path="$1"
  local output_dir="$2"

  if [[ ! -d "$worktree_path" ]]; then
    echo "  ⚠️  [worktree] Path not found: $worktree_path" >&2
    return 1
  fi

  mkdir -p "$output_dir"

  # Copy outputs — rsync preferred but not required
  if command -v rsync &>/dev/null; then
    rsync -a "${worktree_path}/outputs/" "${output_dir}/" 2>/dev/null || \
      cp -R "${worktree_path}/outputs/." "${output_dir}/" 2>/dev/null || true
  else
    cp -R "${worktree_path}/outputs/." "${output_dir}/" 2>/dev/null || true
  fi

  echo "  📦 [worktree] Merged outputs to $output_dir" >&2
  return 0
}

# Remove a worktree and clean up.
# Args: $1=session_id
# Returns: 0=cleaned
worktree_cleanup() {
  local session_id="$1"
  local worktree_path="$WORKTREE_BASE/${session_id}"

  if [[ ! -d "$worktree_path" ]]; then
    return 0
  fi

  # Try git worktree remove first
  if command -v git >/dev/null 2>&1; then
    git worktree remove "$worktree_path" --force 2>/dev/null || true
  fi

  # Ensure directory is gone
  rm -rf "$worktree_path" 2>/dev/null || true

  echo "  🧹 [worktree] Cleaned up: $session_id" >&2
  return 0
}

# List active worktrees.
worktree_list() {
  if [[ ! -d "$WORKTREE_BASE" ]]; then
    echo "No active worktrees."
    return 0
  fi

  local count=0
  for d in "$WORKTREE_BASE"/*/; do
    [[ -d "$d" ]] || continue
    local name
    name=$(basename "$d")
    local size
    size=$(du -sh "$d" 2>/dev/null | cut -f1)
    echo "  🌳 $name ($size)"
    count=$((count + 1))
  done

  [[ $count -eq 0 ]] && echo "No active worktrees."
  return 0
}
