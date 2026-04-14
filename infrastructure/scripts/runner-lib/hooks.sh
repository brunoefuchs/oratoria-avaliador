#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER-LIB — Declarative Hook System
# ═══════════════════════════════════════════════════════════════
# 4 hook points: pre_phase, post_phase, on_failure, on_complete
# Hooks are defined in runner-hooks.yaml per squad.
# Exit codes: 0=continue, 1=halt, 2=retry
# Backward compatible: no hooks file = no-op.
#
# Story: RUNNER-2.2 (Hook System Declarativo)
# Dependencies: session-mgr.sh (SESSION_ID), runtime.sh (run_with_timeout)

# ═══════════════════════════════════════════════════════════════
# State
# ═══════════════════════════════════════════════════════════════

# Loaded hooks config (empty = not loaded or no hooks file)
_HOOKS_LOADED=""
_HOOKS_FILE=""
_HOOKS_SQUAD_DIR=""

# Default timeout per hook (seconds)
HOOKS_DEFAULT_TIMEOUT="${HOOKS_DEFAULT_TIMEOUT:-30}"

# ═══════════════════════════════════════════════════════════════
# hooks_load — Parse runner-hooks.yaml from squad directory
# ═══════════════════════════════════════════════════════════════
# Args: $1=squad_dir (directory containing runner-hooks.yaml)
# Returns: 0=loaded, 1=no hooks file (no-op)

hooks_load() {
  local squad_dir="$1"

  _HOOKS_SQUAD_DIR="$squad_dir"
  _HOOKS_FILE="$squad_dir/runner-hooks.yaml"

  if [[ ! -f "$_HOOKS_FILE" ]]; then
    _HOOKS_LOADED=""
    return 1
  fi

  # Validate YAML syntax — reuse assertions.sh if loaded, else inline
  if declare -f assert_yaml_valid >/dev/null 2>&1; then
    if ! assert_yaml_valid "$_HOOKS_FILE" 2>/dev/null; then
      echo "  ⚠️  hooks: invalid runner-hooks.yaml, hooks disabled" >&2
      _HOOKS_LOADED=""
      return 1
    fi
  fi

  _HOOKS_LOADED="true"
  return 0
}

# ═══════════════════════════════════════════════════════════════
# _hooks_get_scripts — Get hook scripts for a hook point + phase
# ═══════════════════════════════════════════════════════════════
# Returns lines of "script_path:timeout" pairs.
# First checks phase_hooks.{phase}.{hook_point}, then hooks.{hook_point}.
# Args: $1=hook_point, $2=phase_label

_hooks_get_scripts() {
  local hook_point="$1"
  local phase_label="$2"

  python3 - "$_HOOKS_FILE" "$hook_point" "$phase_label" "$HOOKS_DEFAULT_TIMEOUT" <<'PYEOF'
import yaml, sys

hooks_file = sys.argv[1]
hook_point = sys.argv[2]
phase_label = sys.argv[3]
default_timeout = sys.argv[4]

with open(hooks_file) as f:
    data = yaml.safe_load(f) or {}

# Check phase-specific hooks first
hooks = []
phase_hooks = data.get('phase_hooks', {}).get(phase_label, {}).get(hook_point, [])
if phase_hooks:
    hooks = phase_hooks
else:
    hooks = data.get('hooks', {}).get(hook_point, [])

for h in hooks:
    if isinstance(h, dict):
        script = h.get('script', '')
        timeout = h.get('timeout', default_timeout)
    elif isinstance(h, str):
        script = h
        timeout = default_timeout
    else:
        continue
    if script:
        print(f'{script}:{timeout}')
PYEOF
}

# ═══════════════════════════════════════════════════════════════
# hooks_run — Execute hooks for a given hook point
# ═══════════════════════════════════════════════════════════════
# Args:
#   $1=hook_point   — pre_phase|post_phase|on_failure|on_complete
#   $2=phase_label  — current phase name
# Env vars exported to hook scripts:
#   HOOK_SQUAD, HOOK_PHASE, HOOK_AGENT, HOOK_SESSION_ID,
#   HOOK_OUTPUT_FILE, HOOK_EXIT_CODE, HOOK_LOG_FILE
# Returns: 0=continue, 1=halt, 2=retry

hooks_run() {
  local hook_point="$1"
  local phase_label="${2:-unknown}"

  # No-op if hooks not loaded
  [[ -n "$_HOOKS_LOADED" ]] || return 0

  local scripts
  scripts=$(_hooks_get_scripts "$hook_point" "$phase_label")
  [[ -n "$scripts" ]] || return 0

  # Export context for hook scripts
  export HOOK_SQUAD="${SQUAD_SLUG:-unknown}"
  export HOOK_PHASE="$phase_label"
  export HOOK_AGENT="${AGENT_SLUG:-unknown}"
  export HOOK_SESSION_ID="${HOOK_SESSION_ID:-${_ACTIVE_SESSION_ID:-}}"
  export HOOK_OUTPUT_FILE="${HOOK_OUTPUT_FILE:-}"
  export HOOK_EXIT_CODE="${HOOK_EXIT_CODE:-0}"
  export HOOK_LOG_FILE="${HOOK_LOG_FILE:-/dev/null}"

  while IFS= read -r entry; do
    [[ -n "$entry" ]] || continue

    local script="${entry%%:*}"
    local timeout="${entry##*:}"

    # Resolve script path (relative to squad dir or absolute)
    local script_path
    if [[ "$script" == /* ]]; then
      script_path="$script"
    else
      script_path="$_HOOKS_SQUAD_DIR/$script"
    fi

    # Check script exists
    if [[ ! -f "$script_path" ]]; then
      # Check runner-lib hooks/ as fallback for generic hooks
      local lib_dir
      lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
      if [[ -f "$lib_dir/$script" ]]; then
        script_path="$lib_dir/$script"
      else
        echo "  ⚠️  hook: script not found: $script" >&2
        continue
      fi
    fi

    # Make executable if needed
    [[ -x "$script_path" ]] || chmod +x "$script_path" 2>/dev/null

    # Execute with timeout
    local exit_code=0
    if declare -f run_with_timeout >/dev/null 2>&1; then
      run_with_timeout "$timeout" bash "$script_path" 2>&1 || exit_code=$?
    elif command -v gtimeout &>/dev/null; then
      gtimeout "$timeout" bash "$script_path" 2>&1 || exit_code=$?
    elif command -v timeout &>/dev/null; then
      timeout "$timeout" bash "$script_path" 2>&1 || exit_code=$?
    else
      bash "$script_path" 2>&1 || exit_code=$?
    fi

    case $exit_code in
      0)
        # OK, continue to next hook
        ;;
      1)
        echo "  🛑 [HOOK] $script → HALT" >&2
        return 1
        ;;
      2)
        echo "  🔄 [HOOK] $script → RETRY" >&2
        return 2
        ;;
      124)
        echo "  ⏰ [HOOK] $script → TIMEOUT after ${timeout}s" >&2
        # Timeout is non-fatal, continue to next hook
        ;;
      *)
        echo "  ⚠️  [HOOK] $script → exit $exit_code (ignored)" >&2
        ;;
    esac
  done <<< "$scripts"

  return 0
}

# ═══════════════════════════════════════════════════════════════
# Convenience wrappers for each hook point
# ═══════════════════════════════════════════════════════════════

hooks_run_pre() {
  hooks_run "pre_phase" "${1:-unknown}"
}

hooks_run_post() {
  hooks_run "post_phase" "${1:-unknown}"
}

hooks_run_on_failure() {
  hooks_run "on_failure" "${1:-unknown}"
}

hooks_run_on_complete() {
  hooks_run "on_complete" "${1:-unknown}"
}

# ═══════════════════════════════════════════════════════════════
# Programmatic Lifecycle Hooks API (Story 115.11)
# ═══════════════════════════════════════════════════════════════
# 6 formal hooks for framework-internal lifecycle events.
# Design: separate from YAML-declarative model which serves
# squad-configurable external scripts. Programmatic hooks are
# in-process function callbacks registered at runtime.
#
# DECISION: Programmatic API (not YAML-extended).
# Justification:
#   1. YAML model executes external scripts via subprocess — adds
#      latency inappropriate for hot-path hooks (on_turn_start/end
#      fire every turn).
#   2. Programmatic hooks are in-process bash functions — zero
#      fork overhead.
#   3. The two paradigms serve different purposes: YAML = squad-
#      configurable external scripts, Programmatic = framework-
#      internal lifecycle events.
#   4. Mixing both in one YAML schema would create confusing dual
#      semantics for hook consumers.
#
# Each hook is wrapped in error handling: hook failure does NOT
# block execution (logs warning, continues).
#
# Dependencies: classify_error() from runtime.sh (for on_error)

# Registry: associative-array-like flat vars (_LIFECYCLE_HOOK_{NAME}_{N})
# Using flat vars for bash 3.x compat (no declare -A).
_LIFECYCLE_HOOK_COUNT_on_session_start=0
_LIFECYCLE_HOOK_COUNT_on_turn_start=0
_LIFECYCLE_HOOK_COUNT_on_turn_end=0
_LIFECYCLE_HOOK_COUNT_on_pre_compress=0
_LIFECYCLE_HOOK_COUNT_on_error=0
_LIFECYCLE_HOOK_COUNT_on_session_end=0

# ═══════════════════════════════════════════════════════════════
# lifecycle_hook_register — Register a callback for a lifecycle event
# ═══════════════════════════════════════════════════════════════
# Args: $1=hook_name, $2=callback_function_name
# Valid hook names: on_session_start, on_turn_start, on_turn_end,
#                   on_pre_compress, on_error, on_session_end
# Returns: 0=registered, 1=invalid hook name

lifecycle_hook_register() {
  local hook_name="$1"
  local callback="$2"

  # Validate hook name
  case "$hook_name" in
    on_session_start|on_turn_start|on_turn_end|on_pre_compress|on_error|on_session_end)
      ;;
    *)
      echo "  [WARN] lifecycle_hook_register: unknown hook '$hook_name'" >&2
      return 1
      ;;
  esac

  # Validate callback is a function
  if ! declare -f "$callback" >/dev/null 2>&1; then
    echo "  [WARN] lifecycle_hook_register: '$callback' is not a function" >&2
    return 1
  fi

  local count_var="_LIFECYCLE_HOOK_COUNT_${hook_name}"
  local count="${!count_var}"
  local entry_var="_LIFECYCLE_HOOK_${hook_name}_${count}"
  eval "$entry_var='$callback'"
  eval "$count_var=$((count + 1))"
  return 0
}

# ═══════════════════════════════════════════════════════════════
# lifecycle_hook_clear — Clear all callbacks for a hook (or all hooks)
# ═══════════════════════════════════════════════════════════════
# Args: $1=hook_name (optional; if empty, clears all)

lifecycle_hook_clear() {
  local hook_name="${1:-}"

  if [[ -z "$hook_name" ]]; then
    for hn in on_session_start on_turn_start on_turn_end on_pre_compress on_error on_session_end; do
      lifecycle_hook_clear "$hn"
    done
    return 0
  fi

  local count_var="_LIFECYCLE_HOOK_COUNT_${hook_name}"
  local count="${!count_var:-0}"
  local i=0
  while [[ "$i" -lt "$count" ]]; do
    unset "_LIFECYCLE_HOOK_${hook_name}_${i}" 2>/dev/null || true
    i=$((i + 1))
  done
  eval "$count_var=0"
}

# ═══════════════════════════════════════════════════════════════
# _lifecycle_hook_fire — Internal: execute all callbacks for a hook
# ═══════════════════════════════════════════════════════════════
# Each callback is invoked inside a subshell-like trap so that
# exit/return/error in the callback does NOT propagate.
# Args: $1=hook_name, $2..N=arguments passed to callbacks

_lifecycle_hook_fire() {
  local hook_name="$1"
  shift

  local count_var="_LIFECYCLE_HOOK_COUNT_${hook_name}"
  local count="${!count_var:-0}"

  [[ "$count" -gt 0 ]] || return 0

  local i=0
  while [[ "$i" -lt "$count" ]]; do
    local entry_var="_LIFECYCLE_HOOK_${hook_name}_${i}"
    local callback="${!entry_var:-}"
    i=$((i + 1))

    [[ -n "$callback" ]] || continue

    # Execute in error-safe wrapper: failure logs warning, never blocks
    (
      set +e
      "$callback" "$@" 2>&1 || true
    ) 2>/dev/null || {
      echo "  [WARN] lifecycle hook '$hook_name' callback '$callback' failed (ignored)" >&2
    }
  done
  return 0
}

# ═══════════════════════════════════════════════════════════════
# Public firing functions — called by runner framework
# ═══════════════════════════════════════════════════════════════

# on_session_start(session_id) — before the first turn
lifecycle_fire_on_session_start() {
  local session_id="${1:-}"
  _lifecycle_hook_fire "on_session_start" "$session_id"
}

# on_turn_start(turn_number, phase_name) — before each turn
lifecycle_fire_on_turn_start() {
  local turn_number="${1:-0}"
  local phase_name="${2:-unknown}"
  _lifecycle_hook_fire "on_turn_start" "$turn_number" "$phase_name"
}

# on_turn_end(turn_number, phase_name, result) — after each turn
lifecycle_fire_on_turn_end() {
  local turn_number="${1:-0}"
  local phase_name="${2:-unknown}"
  local result="${3:-unknown}"
  _lifecycle_hook_fire "on_turn_end" "$turn_number" "$phase_name" "$result"
}

# on_pre_compress(context_size) — before context compression
lifecycle_fire_on_pre_compress() {
  local context_size="${1:-0}"
  _lifecycle_hook_fire "on_pre_compress" "$context_size"
}

# on_error(error_type, error_code, message) — on any error
# References classify_error() from runtime.sh (Story 115.7)
lifecycle_fire_on_error() {
  local error_type="${1:-unknown}"
  local error_code="${2:-1}"
  local message="${3:-}"
  _lifecycle_hook_fire "on_error" "$error_type" "$error_code" "$message"
}

# on_session_end(session_id, exit_reason) — after last turn
lifecycle_fire_on_session_end() {
  local session_id="${1:-}"
  local exit_reason="${2:-normal}"
  _lifecycle_hook_fire "on_session_end" "$session_id" "$exit_reason"
}
