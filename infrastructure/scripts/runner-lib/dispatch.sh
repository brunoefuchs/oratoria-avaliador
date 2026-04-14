#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER-LIB — Cross-Squad Dispatch
# ═══════════════════════════════════════════════════════════════
# Enables squads to invoke other squads mid-pipeline.
# Routing table defines available squads and their entry points.
#
# Usage:
#   dispatch_to_squad "mmos" "extract-voice-dna" "/tmp/input.json" "hooks/callback.sh"
#   dispatch_to_squad "mmos" "extract-voice-dna" "/tmp/input.json" "" "true"  # sync
#
# Story: RUNNER-4.1 (Cross-Squad Dispatch + Worktree Isolation)
# Dependencies: session-mgr.sh (session tracking), hooks.sh (callbacks)

_dispatch_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DISPATCH_ROUTING_TABLE="${DISPATCH_ROUTING_TABLE:-$_dispatch_lib_dir/squad-routing.yaml}"

# Dispatch a task to another squad.
# Args:
#   $1=target_squad  — squad name from routing table
#   $2=task_name     — task/capability to invoke
#   $3=input_file    — path to input data (optional)
#   $4=callback      — script to invoke on completion (optional)
#   $5=wait_mode     — "true" for sync, "false" for async (default)
# Returns: session_id (printed to stdout)
# Exit: 0=dispatched, 1=error
dispatch_to_squad() {
  local target_squad="$1"
  local task="${2:-default}"
  local input_file="${3:-}"
  local callback="${4:-}"
  local wait_mode="${5:-false}"

  if [[ ! -f "$DISPATCH_ROUTING_TABLE" ]]; then
    echo "  ❌ [dispatch] Routing table not found: $DISPATCH_ROUTING_TABLE" >&2
    return 1
  fi

  # Resolve entry point and dispatch status from routing table (single parse)
  local entry accepts
  local _dispatch_parsed
  _dispatch_parsed=$(python3 - "$DISPATCH_ROUTING_TABLE" "$target_squad" <<'PYEOF'
import yaml, sys
with open(sys.argv[1]) as f:
    data = yaml.safe_load(f)
sq = data.get('squads', {}).get(sys.argv[2], {})
entry = sq.get('entry', '')
accepts = 'true' if sq.get('accepts_dispatch', False) else 'false'
print(f'{entry}\n{accepts}')
PYEOF
  ) 2>/dev/null
  entry=$(echo "$_dispatch_parsed" | head -1)
  accepts=$(echo "$_dispatch_parsed" | tail -1)

  if [[ -z "$entry" ]]; then
    echo "  ❌ [dispatch] Squad '$target_squad' not found in routing table" >&2
    return 1
  fi

  if [[ "$accepts" != "true" ]]; then
    echo "  ❌ [dispatch] Squad '$target_squad' does not accept dispatch" >&2
    return 1
  fi

  # Resolve repo root for relative paths
  local repo_root
  repo_root=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
  local entry_path="$repo_root/$entry"

  if [[ ! -f "$entry_path" ]]; then
    echo "  ❌ [dispatch] Entry script not found: $entry_path" >&2
    return 1
  fi

  # Create session for dispatched task
  local session_id="dispatch-${target_squad}-${task}-$(date +%s)"
  if declare -f session_start >/dev/null 2>&1; then
    session_id=$(session_start "$target_squad" "dispatch-$task" "$task" "" "" "" 2>/dev/null) || true
  fi

  echo "  📤 [dispatch] $target_squad/$task (session: $session_id, mode: $([ "$wait_mode" == "true" ] && echo "sync" || echo "async"))" >&2

  # Build env for dispatched task
  local dispatch_env=""
  dispatch_env="DISPATCH_FROM=${SQUAD_SLUG:-unknown}"
  dispatch_env="$dispatch_env DISPATCH_TASK=$task"
  dispatch_env="$dispatch_env DISPATCH_SESSION=$session_id"
  [[ -n "$input_file" ]] && dispatch_env="$dispatch_env DISPATCH_INPUT=$input_file"

  if [[ "$wait_mode" == "true" ]]; then
    # Sync: wait for completion
    local exit_code=0
    env $dispatch_env bash "$entry_path" 2>&1 || exit_code=$?

    if declare -f session_end >/dev/null 2>&1; then
      session_end "$session_id" "$exit_code" "0" 2>/dev/null || true
    fi

    if [[ -n "$callback" && -f "$callback" ]]; then
      HOOK_SESSION_ID="$session_id" HOOK_EXIT_CODE="$exit_code" bash "$callback" 2>&1 || true
    fi

    echo "$session_id"
    return $exit_code
  else
    # Async: fire in background
    {
      local exit_code=0
      env $dispatch_env bash "$entry_path" 2>&1 || exit_code=$?

      if declare -f session_end >/dev/null 2>&1; then
        session_end "$session_id" "$exit_code" "0" 2>/dev/null || true
      fi

      if [[ -n "$callback" && -f "$callback" ]]; then
        HOOK_SESSION_ID="$session_id" HOOK_EXIT_CODE="$exit_code" bash "$callback" 2>&1 || true
      fi
    } &

    echo "$session_id"
    return 0
  fi
}

# List available squads from routing table.
dispatch_list_squads() {
  if [[ ! -f "$DISPATCH_ROUTING_TABLE" ]]; then
    echo "No routing table found."
    return 1
  fi

  python3 -c "
import yaml
with open('$DISPATCH_ROUTING_TABLE') as f:
    data = yaml.safe_load(f)
for name, info in data.get('squads', {}).items():
    status = '✅' if info.get('accepts_dispatch') else '❌'
    caps = ', '.join(info.get('capabilities', []))
    print(f'{status} {name:<20} {caps}')
" 2>/dev/null
}
