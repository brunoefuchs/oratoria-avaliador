#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER-LIB: arg-parser.sh — Common flag parsing for autonomous runners
# ═══════════════════════════════════════════════════════════════════════════════
# Parses the standard flags shared across all runners. Script-specific flags
# and remaining positional args are preserved in POSITIONAL_ARGS, in original
# order, for the consumer to re-parse.
#
# Standard flags parsed:
#   --claude / --codex / --gemini   → REQUESTED_RUNTIME
#   --model <model>                 → RUNNER_MODEL
#   --force-model <model>           → RUNNER_FORCE_MODEL + RUNNER_MODEL
#   --timeout <seconds>             → LLM_TIMEOUT_SECONDS
#   --max-cost <usd>                → MAX_COST
#   --phase <num>                   → START_PHASE
#   --dry-run                       → DRY_RUN=true
#   --verbose                       → VERBOSE=true
#   --quick                         → QUICK=true
#   --help / -h                     → calls show_help (must be defined by consumer)
#
# Usage:
#   parse_common_args "$@"
#   set -- "${POSITIONAL_ARGS[@]}"  # remaining args for consumer
#   # or: parse_extra_flags "${POSITIONAL_ARGS[@]}"

# Defaults (consumer can override before calling parse_common_args)
REQUESTED_RUNTIME="${REQUESTED_RUNTIME:-auto}"
RUNNER_MODEL="${RUNNER_MODEL:-}"
RUNNER_FORCE_MODEL="${RUNNER_FORCE_MODEL:-}"
LLM_TIMEOUT_SECONDS="${LLM_TIMEOUT_SECONDS:-3600}"
MAX_COST="${MAX_COST:-}"
START_PHASE="${START_PHASE:-}"
DRY_RUN="${DRY_RUN:-false}"
VERBOSE="${VERBOSE:-false}"
QUICK="${QUICK:-false}"
JSON_OUTPUT="${JSON_OUTPUT:-false}"
EVAL_DISABLED="${EVAL_DISABLED:-false}"
EVAL_TIER1_ONLY="${EVAL_TIER1_ONLY:-false}"
if ! declare -p POSITIONAL_ARGS >/dev/null 2>&1; then
  POSITIONAL_ARGS=()
fi
if ! declare -p _UNKNOWN_FLAGS >/dev/null 2>&1; then
  _UNKNOWN_FLAGS=()
fi
if ! declare -p REMAINING_ARGS >/dev/null 2>&1; then
  REMAINING_ARGS=()
fi
PARSE_EXTRA_FLAGS_CONSUMED="${PARSE_EXTRA_FLAGS_CONSUMED:-1}"

_arg_parser_require_value() {
  local flag="$1"
  if [[ $# -lt 2 || -z "${2:-}" ]]; then
    echo "❌ Missing value for $flag" >&2
    echo "   Use --help for usage." >&2
    exit 1
  fi
}

parse_common_args() {
  POSITIONAL_ARGS=()
  REMAINING_ARGS=()
  _UNKNOWN_FLAGS=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        if declare -f show_help >/dev/null 2>&1; then
          show_help
        else
          echo "No help available. Define show_help() before parse_common_args."
          exit 0
        fi
        ;;
      --claude)       REQUESTED_RUNTIME="claude"; shift ;;
      --codex)        REQUESTED_RUNTIME="codex"; shift ;;
      --gemini)       REQUESTED_RUNTIME="gemini"; shift ;;
      --model)
        _arg_parser_require_value "$1" "${2:-}"
        RUNNER_MODEL="$2"
        shift 2
        ;;
      --force-model)
        _arg_parser_require_value "$1" "${2:-}"
        RUNNER_FORCE_MODEL="$2"
        RUNNER_MODEL="$2"
        shift 2
        ;;
      --timeout)
        _arg_parser_require_value "$1" "${2:-}"
        LLM_TIMEOUT_SECONDS="$2"
        shift 2
        ;;
      --max-cost)
        _arg_parser_require_value "$1" "${2:-}"
        MAX_COST="$2"
        shift 2
        ;;
      --phase)
        _arg_parser_require_value "$1" "${2:-}"
        START_PHASE="$2"
        shift 2
        ;;
      --dry-run)      DRY_RUN="true"; shift ;;
      --verbose|-v)   VERBOSE="true"; shift ;;
      --quick|-q)     QUICK="true"; shift ;;
      --json|-j)      JSON_OUTPUT="true"; shift ;;
      --no-eval)      EVAL_DISABLED="true"; shift ;;
      --eval-tier1-only) EVAL_TIER1_ONLY="true"; shift ;;
      -*)
        # Unknown flag — preserve exact token order for consumer-side parsing.
        _UNKNOWN_FLAGS+=("$1")
        POSITIONAL_ARGS+=("$1")
        REMAINING_ARGS+=("$1")
        shift
        ;;
      *)
        POSITIONAL_ARGS+=("$1")
        REMAINING_ARGS+=("$1")
        shift
        ;;
    esac
  done
}

# Re-process script-specific args with a consumer-defined parser.
# Preferred:
#   - define handle_extra_args() and parse the full "$@" stream yourself
# Backwards compatible:
#   - define handle_extra_flag()
#   - inspect "$@" from inside the handler
#   - set PARSE_EXTRA_FLAGS_CONSUMED to the number of tokens consumed
# Usage: parse_extra_flags "${POSITIONAL_ARGS[@]}"
parse_extra_flags() {
  if declare -f handle_extra_args >/dev/null 2>&1; then
    handle_extra_args "$@"
    return $?
  fi

  local extra_args=("$@")
  while [[ ${#extra_args[@]} -gt 0 ]]; do
    if ! declare -f handle_extra_flag >/dev/null 2>&1; then
      echo "❌ Unknown extra argument: ${extra_args[0]}" >&2
      echo "   Define handle_extra_args() or handle_extra_flag() to parse script-specific args." >&2
      exit 1
    fi

    PARSE_EXTRA_FLAGS_CONSUMED=1
    handle_extra_flag "${extra_args[@]}"

    local consumed="${PARSE_EXTRA_FLAGS_CONSUMED:-1}"
    if ! [[ "$consumed" =~ ^[0-9]+$ ]] || (( consumed < 1 )); then
      echo "❌ handle_extra_flag() must set PARSE_EXTRA_FLAGS_CONSUMED to >= 1" >&2
      exit 1
    fi

    extra_args=("${extra_args[@]:$consumed}")
  done
}

RUNNER_LIB_ARG_PARSER=true
