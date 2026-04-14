#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER CLI — Unified command-line interface for runner-lib
# ═══════════════════════════════════════════════════════════════
# Entry point for all runner-lib operations.
#
# Usage:
#   runner sessions list [--all]
#   runner sessions kill <session-id>
#   runner sessions log <session-id> [--follow|-f]
#   runner sessions info <session-id>
#   runner sessions cleanup
#   runner cost summary
#   runner cost detail <metrics-file>
#
# Install: symlink to PATH or alias:
#   ln -s $(git rev-parse --show-toplevel)/infrastructure/scripts/runner-lib/runner-cli.sh /usr/local/bin/runner
#   # or
#   alias runner="$(git rev-parse --show-toplevel)/infrastructure/scripts/runner-lib/runner-cli.sh"
#
# Story: RUNNER-1.2 (Session Manager)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load runner-lib
source "$SCRIPT_DIR/loader.sh"

# ═══════════════════════════════════════════════════════════════
# Subcommand routing
# ═══════════════════════════════════════════════════════════════

_runner_usage() {
  cat << 'EOF'
runner — Unified CLI for runner-lib

USAGE:
  runner <command> <subcommand> [args]

COMMANDS:
  sessions list [--all]              List sessions (active + recent, or all)
  sessions kill <session-id>         Kill a running session (SIGTERM)
  sessions log <session-id> [-f]     Show session log (optionally follow)
  sessions info <session-id>         Show full session metadata
  sessions cleanup                   Archive old completed sessions

  cost summary                       Show cost summary (requires METRICS_FILE)
  cost detail <metrics-file>         Show cost details from a specific file

  version                            Show runner-lib version

EOF
}

_runner_sessions() {
  local subcmd="${1:-}"
  shift 2>/dev/null || true

  case "$subcmd" in
    list)
      session_list "$@"
      ;;
    kill)
      local id="${1:?Usage: runner sessions kill <session-id>}"
      session_kill "$id"
      ;;
    log)
      local id="${1:?Usage: runner sessions log <session-id> [--follow|-f]}"
      shift
      session_log "$id" "$@"
      ;;
    info)
      local id="${1:?Usage: runner sessions info <session-id>}"
      session_info "$id"
      ;;
    cleanup)
      session_cleanup
      ;;
    *)
      echo "Unknown sessions subcommand: $subcmd" >&2
      echo "Available: list, kill, log, info, cleanup" >&2
      return 1
      ;;
  esac
}

_runner_cost() {
  local subcmd="${1:-}"
  shift 2>/dev/null || true

  case "$subcmd" in
    summary)
      if [[ -z "${METRICS_FILE:-}" ]]; then
        echo "METRICS_FILE not set. Use: METRICS_FILE=path/to/metrics.jsonl runner cost summary" >&2
        return 1
      fi
      show_cost_summary
      ;;
    detail)
      local file="${1:?Usage: runner cost detail <metrics-file>}"
      METRICS_FILE="$file"
      show_cost_summary
      ;;
    *)
      echo "Unknown cost subcommand: $subcmd" >&2
      echo "Available: summary, detail" >&2
      return 1
      ;;
  esac
}

# ═══════════════════════════════════════════════════════════════
# Main dispatch
# ═══════════════════════════════════════════════════════════════

main() {
  local cmd="${1:-}"
  shift 2>/dev/null || true

  case "$cmd" in
    sessions)
      _runner_sessions "$@"
      ;;
    cost)
      _runner_cost "$@"
      ;;
    version)
      echo "runner-cli 1.0.0 (runner-lib)"
      ;;
    help|--help|-h|"")
      _runner_usage
      ;;
    *)
      echo "Unknown command: $cmd" >&2
      _runner_usage
      return 1
      ;;
  esac
}

main "$@"
