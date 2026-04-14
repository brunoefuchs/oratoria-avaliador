#!/bin/bash
# SINKRA Pipeline " LLM Runtime (multi-runtime: claude, codex, gemini)
# Handles prompt execution with retry, timeout, fallback chain, and fatal error detection.
#
# Features:
#   - Multi-runtime: claude, codex, gemini (auto-detect or explicit)
#   - Optional guardrails per phase when the selected runtime supports them
#   - --output-format json with jq parsing (Claude only)
#   - Fallback chain: primary fails ' try next runtime
#   - Retry with exponential backoff for transient errors
#   - Circuit breaker for fatal errors (billing/quota)

if ! declare -f get_runtime_model >/dev/null 2>&1; then
  _runner_lib_runtime_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "$_runner_lib_runtime_dir/models.sh" ]]; then
    source "$_runner_lib_runtime_dir/models.sh"
  fi
  unset _runner_lib_runtime_dir
fi

# Source credential pool if available (L5-Advanced, optional)
if ! declare -f pool_get_credential >/dev/null 2>&1; then
  _runner_lib_cpool_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "$_runner_lib_cpool_dir/credential-pool.sh" ]]; then
    source "$_runner_lib_cpool_dir/credential-pool.sh"
  fi
  unset _runner_lib_cpool_dir
fi

# Track last model used for metrics
LAST_LLM_MODEL=""

# 
# Error Classification -- classify errors as transient/permanent/unknown
# 
# Story: 115.7 (Error Classification & Circuit Breaker)
# Design ref: OpenClaw retry.ts (transient vs permanent, shouldRetry predicate)
#
# classify_error(output_file, exit_code)
#   Returns: "transient" | "permanent" | "unknown"
#   Transient: 429, timeout, connection reset, 5xx -> retry with backoff
#   Permanent: 401 auth, 400 validation, 404 not found -> fail immediately
#   Unknown:   default -> retry up to 3x, then fail
#
# Used by:
#   - run_llm_prompt() POST-LLM guard to feed circuit breaker with error type
#   - replan_on_error() in replan.sh to decide retry vs replan vs abort

classify_error() {
  local output_file="${1:-}"
  local exit_code="${2:-1}"

  # Timeout exit code from run_with_timeout
  if [[ "$exit_code" -eq 124 ]]; then
    echo "transient"
    return 0
  fi

  # If no output file or file does not exist, classify as unknown
  if [[ -z "$output_file" || ! -f "$output_file" ]]; then
    echo "unknown"
    return 0
  fi

  # Permanent errors -- fail immediately, no retry
  if grep -Eiq "401|unauthorized|authentication failed|invalid.*api.*key|invalid.*token" "$output_file" 2>/dev/null; then
    echo "permanent"
    return 0
  fi
  if grep -Eiq "400|bad request|validation error|invalid request|malformed" "$output_file" 2>/dev/null; then
    echo "permanent"
    return 0
  fi
  if grep -Eiq "404|not found|resource.*not.*found|endpoint.*not.*found" "$output_file" 2>/dev/null; then
    echo "permanent"
    return 0
  fi
  if grep -Eiq "403|forbidden|access denied|permission denied" "$output_file" 2>/dev/null; then
    echo "permanent"
    return 0
  fi

  # Transient errors -- retry with backoff
  if grep -Eiq "429|rate limit|too many requests" "$output_file" 2>/dev/null; then
    echo "transient"
    return 0
  fi
  if grep -Eiq "timeout|timed out|deadline exceeded" "$output_file" 2>/dev/null; then
    echo "transient"
    return 0
  fi
  if grep -Eiq "connection reset|connection refused|connection closed|stream disconnected|network error|ECONNRESET|ECONNREFUSED" "$output_file" 2>/dev/null; then
    echo "transient"
    return 0
  fi
  if grep -Eiq "5[0-9][0-9]|server error|service unavailable|internal server error|bad gateway|gateway timeout|overloaded|temporarily unavailable" "$output_file" 2>/dev/null; then
    echo "transient"
    return 0
  fi

  # Default: unknown
  echo "unknown"
  return 0
}

# Track unknown error retries per phase (max 3 for unknown errors)
_RLP_UNKNOWN_ERROR_RETRIES=0
_RLP_UNKNOWN_ERROR_MAX=3

# 
# Budget Tracking -- warn at 70%, urgent at 90%, hard stop at 100%
# 
# Story: 115.8 (Budget Warnings & Context Compression)
# Design ref: Hermes run_agent.py (budget_caution 70%, budget_warning 90%)
#
# Usage:
#   RUNNER_MAX_ITERATIONS=50   (default, configurable per runner)
#   Call budget_check_iteration() at the start of each iteration/turn.
#   Returns: 0=continue, 1=hard stop (budget exhausted)
#
# Thresholds:
#   70% -> [BUDGET] Caution log
#   90% -> [BUDGET] Warning log (urgent)
#  100% -> [BUDGET] Hard stop with graceful exit

RUNNER_MAX_ITERATIONS="${RUNNER_MAX_ITERATIONS:-50}"
_BUDGET_CURRENT_ITERATION=0
_BUDGET_CAUTION_LOGGED=false
_BUDGET_WARNING_LOGGED=false

# Increment iteration counter and check budget thresholds.
# Returns: 0=continue, 1=budget exhausted (hard stop)
budget_check_iteration() {
  _BUDGET_CURRENT_ITERATION=$((_BUDGET_CURRENT_ITERATION + 1))
  local current="$_BUDGET_CURRENT_ITERATION"
  local max="${RUNNER_MAX_ITERATIONS:-50}"

  # Guard: max must be positive
  if [[ "$max" -le 0 ]]; then
    max=50
  fi

  local pct=0
  if [[ "$max" -gt 0 ]]; then
    pct=$(( (current * 100) / max ))
  fi

  # 100% -- hard stop
  if [[ "$current" -ge "$max" ]]; then
    echo "  [BUDGET] STOP: ${current}/${max} iterations (100%) -- budget exhausted, graceful exit" >&2
    return 1
  fi

  # 90% -- urgent warning (log once)
  if [[ "$pct" -ge 90 && "$_BUDGET_WARNING_LOGGED" != "true" ]]; then
    echo "  [BUDGET] Warning: 90% -- wrap up (${current}/${max} iterations)" >&2
    _BUDGET_WARNING_LOGGED=true
    return 0
  fi

  # 70% -- caution (log once)
  if [[ "$pct" -ge 70 && "$_BUDGET_CAUTION_LOGGED" != "true" ]]; then
    echo "  [BUDGET] Caution: 70% iterations consumed (${current}/${max})" >&2
    _BUDGET_CAUTION_LOGGED=true
    return 0
  fi

  return 0
}

# Reset budget counters (call at session start or when re-entering a loop).
budget_reset() {
  _BUDGET_CURRENT_ITERATION=0
  _BUDGET_CAUTION_LOGGED=false
  _BUDGET_WARNING_LOGGED=false
}

# Get current budget status as a string (for logging/metrics).
# Returns: "N/M (P%)" e.g. "35/50 (70%)"
budget_status() {
  local max="${RUNNER_MAX_ITERATIONS:-50}"
  [[ "$max" -le 0 ]] && max=50
  local pct=0
  if [[ "$max" -gt 0 ]]; then
    pct=$(( (_BUDGET_CURRENT_ITERATION * 100) / max ))
  fi
  echo "${_BUDGET_CURRENT_ITERATION}/${max} (${pct}%)"
}

# Phase-specific overrides (set by caller before run_llm_prompt)
# These are optional " if empty, not passed to CLI.
PHASE_MAX_TURNS=""
PHASE_ALLOWED_TOOLS=""

# Runtime selection (set by main scripts)
# SELECTED_RUNTIME: claude | codex | gemini
# MODEL: model name passed to runtime

# Strip control characters (U+0000-U+001F except tab/newline/cr) from a file.
# LLM outputs sometimes contain these, breaking jq parsing.
_sanitize_llm_output() {
  local file="$1"
  if [[ -f "$file" ]]; then
    LC_ALL=C tr -d '\000-\010\013\014\016-\037' < "$file" > "${file}.clean" 2>/dev/null \
      && mv "${file}.clean" "$file"
  fi
}

# Validate JSON string; return fallback if invalid.
_validate_json_or_fallback() {
  local json="$1" fallback="$2"
  if [[ -n "$json" ]] && echo "$json" | jq . >/dev/null 2>&1; then echo "$json"; else echo "$fallback"; fi
}

# Detect and validate runtime CLI.
detect_runtime() {
  local requested="${1:-auto}"
  case "$requested" in
    auto)
      if command -v claude >/dev/null 2>&1; then echo "claude"
      elif command -v codex >/dev/null 2>&1; then echo "codex"
      elif command -v gemini >/dev/null 2>&1; then echo "gemini"
      else echo "none"
      fi
      ;;
    claude|codex|gemini) echo "$requested" ;;
    *) echo "invalid" ;;
  esac
}

# Validate that the selected runtime CLI exists.
validate_runtime() {
  local runtime="$1"
  if ! command -v "$runtime" >/dev/null 2>&1; then
    echo "[x] '$runtime' CLI not found in PATH."
    exit 1
  fi
}

# Get fallback runtimes (excluding current).
# Limited to MAX 1 fallback to avoid cascade latency.
# Previous bug: Claude'Gemini'Codex cascade added 30-60s latency per phase
# when each runtime failed sequentially. 1 fallback is sufficient.
_get_fallback_runtimes() {
  local current="$1"
  local max_fallbacks="${RUNNER_MAX_FALLBACKS:-1}"
  local fallbacks=""
  local count=0
  for rt in claude gemini codex; do
    if [[ "$rt" != "$current" ]] && command -v "$rt" >/dev/null 2>&1; then
      fallbacks="$fallbacks $rt"
      count=$((count + 1))
      [[ "$count" -ge "$max_fallbacks" ]] && break
    fi
  done
  echo "$fallbacks"
}

# Get default model for a runtime (used when falling back).
_get_default_model() {
  local runtime="$1"
  get_quality_model "$runtime"
}

# Run command with timeout (returns 124 on timeout).
run_with_timeout() {
  local timeout_seconds="$1"
  shift

  if [[ -z "$timeout_seconds" || "$timeout_seconds" -le 0 ]]; then
    "$@"
    return $?
  fi

  # Cross-platform timeout: gtimeout (macOS Homebrew) > timeout (GNU/macOS 10.15+) > perl fallback
  local timeout_cmd=""
  if command -v gtimeout &>/dev/null; then
    timeout_cmd="gtimeout"
  elif command -v timeout &>/dev/null 2>&1; then
    timeout_cmd="timeout"
  fi

  if [[ -n "$timeout_cmd" ]]; then
    $timeout_cmd "$timeout_seconds" "$@"
    return $?
  fi

  # Fallback: perl (works on macOS/Linux, not on Windows/Git Bash)
  if command -v perl &>/dev/null; then
    perl -e '
      use strict;
      use warnings;
      my $timeout = shift @ARGV;
      my $pid = fork();
      die "fork failed\n" unless defined $pid;
      if ($pid == 0) { exec @ARGV or exit 127; }
      my $timed_out = 0;
      eval {
        local $SIG{ALRM} = sub { die "TIMEOUT\n" };
        alarm($timeout);
        waitpid($pid, 0);
        alarm(0);
      };
      if ($@) {
        $timed_out = 1;
        kill 15, $pid; sleep 2; kill 9, $pid;
        waitpid($pid, 0);
      }
      exit($timed_out ? 124 : ($? >> 8));
    ' "$timeout_seconds" "$@"
    return $?
  fi

  # Last resort: run without timeout
  echo "WARNING: No timeout command available (install coreutils). Running without timeout." >&2
  "$@"
  return $?
}

# Detect fatal errors that should abort the pipeline immediately (no retry, no fallback).
is_fatal_error() {
  local output_file="$1"
  grep -Eiq "You've hit your usage limit|usage limit|purchase more credits|billing|quota exceeded|account suspended|exceeded retry limit" "$output_file"
}

# Detect transient runtime errors that should trigger retry.
is_transient_runtime_error() {
  local output_file="$1"
  if is_fatal_error "$output_file"; then return 1; fi

  if grep -Eiq "stream disconnected|connection reset|timed out|timeout|temporarily unavailable|service unavailable|network error|rate limit|429|503|5.. Server Error|overloaded" "$output_file"; then
    return 0
  fi

  if [[ "$SELECTED_RUNTIME" == "codex" ]]; then
    grep -Eiq "failed to queue rollout|failed to shutdown rollout|Reconnecting" "$output_file"
    return $?
  fi

  return 1
}

# Return 0 when the runtime supports a flag, 1 otherwise.
_supports_flag() {
  local runtime="$1"
  local flag="$2"

  case "$runtime:$flag" in
    claude:json-output|claude:max-turns|claude:allowed-tools) return 0 ;;
    *) return 1 ;;
  esac
}

runtime_supports_flag() {
  local runtime="${1:-$SELECTED_RUNTIME}"
  local flag="$2"
  _supports_flag "$runtime" "$flag"
}

_warn_unsupported_flag() {
  local runtime="$1"
  local flag="$2"
  echo "  [WARN] Flag --${flag} not supported by ${runtime}, skipping" >&2
}

# Build the runtime-specific command to execute a prompt.
# Args:
#   $1=model, $2=prompt_file, $3=output_file, $4=runtime_override(optional)
#   $5=json_output(optional: auto|true), $6=max_turns(optional), $7=allowed_tools(optional)
_exec_runtime() {
  local model="$1"
  local prompt_file="$2"
  local output_file="$3"
  local runtime="${4:-$SELECTED_RUNTIME}"
  local json_output="${5:-auto}"
  local max_turns="${6:-$PHASE_MAX_TURNS}"
  local allowed_tools="${7:-$PHASE_ALLOWED_TOOLS}"

  case "$runtime" in
    claude)
      # Build optional flags
      local claude_opts=""
      local claude_output_flag=""

      if [[ "$json_output" == "true" || "$json_output" == "auto" ]]; then
        claude_output_flag=" --output-format json"
      fi

      if [[ -n "$max_turns" ]]; then
        claude_opts="$claude_opts --max-turns $max_turns"
      fi
      if [[ -n "$allowed_tools" ]]; then
        claude_opts="$claude_opts --allowedTools \"$allowed_tools\""
      fi

      run_with_timeout "$LLM_TIMEOUT_SECONDS" bash -c \
        "claude -p --model \"$model\"$claude_output_flag --dangerously-skip-permissions$claude_opts < \"$prompt_file\"" \
        >"$output_file" 2>&1
      ;;
    codex)
      # Codex only supports: --model, --full-auto. Other flags silently skipped.
      run_with_timeout "$LLM_TIMEOUT_SECONDS" codex exec \
        --model "$model" \
        --full-auto \
        - <"$prompt_file" >"$output_file" 2>&1
      ;;
    gemini)
      # Gemini only supports: --model, --yolo. Other flags silently skipped.
      run_with_timeout "$LLM_TIMEOUT_SECONDS" bash -c \
        "cat \"$prompt_file\" | gemini -p 'Follow the instructions provided via stdin exactly.' --model \"$model\" --yolo" \
        >"$output_file" 2>&1
      ;;
    *)
      echo " Unknown runtime: $runtime" >"$output_file"
      return 1
      ;;
  esac
}

# Extract text result from Claude JSON output.
# Claude --output-format json returns: {"type":"result","result":"...text..."}
# For other runtimes, returns raw output.
_extract_result() {
  local output_file="$1"
  local runtime="${2:-$SELECTED_RUNTIME}"

  # Sanitize control chars before any jq parsing
  _sanitize_llm_output "$output_file"

  if [[ "$runtime" == "claude" ]]; then
    # Try to extract .result from JSON
    local extracted
    if command -v jq >/dev/null 2>&1; then
      extracted=$(jq -r '.result // empty' "$output_file" 2>/dev/null)
    else
      extracted=$(python3 - "$output_file" <<'PYEOF' 2>/dev/null || true
import json, sys
try:
    with open(sys.argv[1], encoding='utf-8') as fh:
        data = json.load(fh)
    value = data.get('result', '')
    if value is None:
        value = ''
    print(value, end='')
except Exception:
    pass
PYEOF
      )
    fi
    if [[ -n "$extracted" ]]; then
      echo "$extracted" > "$output_file"
      return 0
    fi
    # If jq fails, the output might not be JSON (error message, etc.) " keep as-is
  fi
  return 0
}

# Runtime display name for logs.
_runtime_label() {
  case "${1:-$SELECTED_RUNTIME}" in
    claude) echo "Claude" ;;
    codex)  echo "Codex" ;;
    gemini) echo "Gemini" ;;
    *)      echo "${1:-$SELECTED_RUNTIME}" ;;
  esac
}

# Execute one LLM call with retry + fallback chain.
# Args:
#   $1=model, $2=prompt, $3=log_file, $4=phase_label(optional)
#   Optional flags after arg 4:
#     --json-output
#     --max-turns N
#     --allowed-tools CSV
# Returns: 0=success, 99=fatal, other=error
run_llm_prompt() {
  local model="$1"
  local prompt="$2"
  local log_file="$3"
  local phase_label="${4:-unknown}"
  local requested_json_output="auto"
  local requested_max_turns="${PHASE_MAX_TURNS:-}"
  local requested_allowed_tools="${PHASE_ALLOWED_TOOLS:-}"

  if [[ "$#" -ge 4 ]]; then
    shift 4
  else
    shift "$#"
  fi

  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --json-output)
        requested_json_output="true"
        shift
        ;;
      --max-turns)
        requested_max_turns="${2:-}"
        shift 2
        ;;
      --allowed-tools)
        requested_allowed_tools="${2:-}"
        shift 2
        ;;
      *)
        echo "  [WARN] Unknown run_llm_prompt option: $1" >&2
        shift
        ;;
    esac
  done

  model="$(resolve_model_alias "$model" "$SELECTED_RUNTIME")"
  LAST_LLM_MODEL="$model"

  # -- PRE-LLM Guard: Cost cap (AC1 -- Story 101.12) --
  if [[ "${COST_CAP_GUARD:-}" == "true" ]] && declare -f check_cost_cap >/dev/null 2>&1; then
    if ! check_cost_cap "${MAX_COST:-}"; then
      echo "  [!] COST CAP: Budget exceeded -- LLM call skipped." >&2
      return 3
    fi
  fi

  # -- PRE-LLM Guard: Circuit breaker (AC2 -- Story 101.12) --
  if [[ -n "${CIRCUIT_BREAKER_THRESHOLD:-}" ]]; then
    : "${_RLP_CONSECUTIVE_FAILURES:=0}"
    if [[ "$_RLP_CONSECUTIVE_FAILURES" -ge "$CIRCUIT_BREAKER_THRESHOLD" ]]; then
      echo "  [!] CIRCUIT BREAKER: $_RLP_CONSECUTIVE_FAILURES consecutive LLM failures (threshold: $CIRCUIT_BREAKER_THRESHOLD) -- skipping." >&2
      return 2
    fi
  fi

  local tmp_output
  tmp_output="$(mktemp)"
  local prompt_input
  prompt_input="$(mktemp)"

  # -- PRE-LLM Guard: Truncate (AC3 -- Story 101.12) --
  if [[ -n "${HEADLESS_TRUNCATE_BYTES:-}" ]] && declare -f truncate_prior_context >/dev/null 2>&1; then
    prompt="$(truncate_prior_context "$prompt" "$HEADLESS_TRUNCATE_BYTES")"
  fi

  printf '%s' "$prompt" > "$prompt_input"

  # Some squad artifacts may contain invalid byte sequences. Normalize once so
  # strict CLIs like Codex do not reject the prompt before the request is sent.
  if command -v iconv >/dev/null 2>&1; then
    local prompt_utf8
    prompt_utf8="$(mktemp)"
    if iconv -f UTF-8 -t UTF-8//IGNORE "$prompt_input" > "$prompt_utf8" 2>/dev/null; then
      mv "$prompt_utf8" "$prompt_input"
    else
      rm -f "$prompt_utf8"
    fi
  fi

  local prompt_size
  prompt_size=$(wc -c < "$prompt_input" | tr -d ' ')
  local label
  label="$(_runtime_label)"
  echo "  - Sending to $label ($model) -- ${prompt_size} bytes prompt..." >&2

  # Session tracking (opt-in: set SESSION_TRACKING=true to enable)
  local _session_id=""
  if [[ "${SESSION_TRACKING:-false}" == "true" ]] && declare -f session_start >/dev/null 2>&1; then
    _session_id=$(session_start \
      "${SQUAD_SLUG:-unknown}" \
      "$phase_label" \
      "${AGENT_SLUG:-unknown}" \
      "$model" \
      "$SELECTED_RUNTIME" \
      "$log_file" 2>/dev/null) || true
  fi

  local call_start
  call_start=$(date +%s)
  local exit_code=0
  local attempt=1
  local active_runtime="$SELECTED_RUNTIME"
  local active_model="$model"

  # Credential pool integration (Story 115.10)
  local _pool_key=""
  if declare -f pool_get_credential >/dev/null 2>&1; then
    _pool_key=$(pool_get_credential 2>/dev/null) || true
    if [[ -n "$_pool_key" ]]; then
      export ANTHROPIC_API_KEY="$_pool_key"
    fi
  fi

  while true; do
    exit_code=0
    : > "$tmp_output"

    _exec_runtime \
      "$active_model" \
      "$prompt_input" \
      "$tmp_output" \
      "$active_runtime" \
      "$requested_json_output" \
      "$requested_max_turns" \
      "$requested_allowed_tools" || exit_code=$?

    if [[ "$exit_code" -eq 124 ]]; then
      echo "ERROR: LLM call timed out after ${LLM_TIMEOUT_SECONDS}s" >> "$tmp_output"
    fi

    {
      echo "----- attempt:$attempt runtime:$active_runtime model:$active_model exit:$exit_code ts:$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S) -----"
      cat "$tmp_output"
      echo "----- end-attempt:$attempt -----"
    } >> "$log_file"

    # Success " extract result and break
    if [[ "$exit_code" -eq 0 ]]; then
      _extract_result "$tmp_output" "$active_runtime"
      break
    fi

    # Billing/quota limit on THIS runtime " skip to fallback (don't abort pipeline)
    local is_billing_error=false
    if is_fatal_error "$tmp_output"; then
      is_billing_error=true
      local dead_label
      dead_label="$(_runtime_label "$active_runtime")"
      echo "  [!] $dead_label billing/quota limit reached -- trying fallback..." >&2
    fi

    # Retry transient errors on same runtime (but NOT billing errors)
    if [[ "$is_billing_error" != true && "$attempt" -lt "$RETRY_MAX_ATTEMPTS" ]]; then
      if is_transient_runtime_error "$tmp_output"; then
        local delay=$(( RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)) ))
        echo "    Transient error (attempt $attempt/$RETRY_MAX_ATTEMPTS). Retrying in ${delay}s..." >&2
        sleep "$delay"
        attempt=$((attempt + 1))
        continue
      fi
    fi

    # Primary runtime failed (billing, transient exhausted, or other) " try fallback chain
    local tried_fallback=false
    for fb_runtime in $(_get_fallback_runtimes "$active_runtime"); do
      # Skip runtimes that aren't installed
      command -v "$fb_runtime" >/dev/null 2>&1 || continue

      local fb_model
      fb_model="$(_get_default_model "$fb_runtime")"
      local fb_label
      fb_label="$(_runtime_label "$fb_runtime")"
      echo "   Fallback: trying $fb_label ($fb_model)..." >&2

      exit_code=0
      : > "$tmp_output"
      _exec_runtime \
        "$fb_model" \
        "$prompt_input" \
        "$tmp_output" \
        "$fb_runtime" \
        "$requested_json_output" \
        "$requested_max_turns" \
        "$requested_allowed_tools" || exit_code=$?

      {
        echo "----- fallback runtime:$fb_runtime model:$fb_model exit:$exit_code ts:$(date -Iseconds) -----"
        cat "$tmp_output"
        echo "----- end-fallback -----"
      } >> "$log_file"

      # Fallback also hit billing limit -- try next
      if [[ "$exit_code" -ne 0 ]] && is_fatal_error "$tmp_output"; then
        echo "  [!] $fb_label also hit billing limit -- trying next..." >&2
        continue
      fi

      if [[ "$exit_code" -eq 0 ]]; then
        _extract_result "$tmp_output" "$fb_runtime"
        active_runtime="$fb_runtime"
        active_model="$fb_model"
        tried_fallback=true
        echo "   Fallback to $fb_label succeeded" >&2
        break
      fi
    done

    if [[ "$tried_fallback" == true && "$exit_code" -eq 0 ]]; then
      break
    fi

    # ALL runtimes failed " only NOW return fatal
    if [[ "$is_billing_error" == true ]]; then
      echo "   ALL runtimes exhausted (billing/quota). Pipeline cannot continue." >&2
      rm -f "$tmp_output" "$prompt_input"
      return 99
    fi

    # Non-billing failure, all fallbacks failed
    break
  done

  # Record metrics
  local call_end
  call_end=$(date +%s)
  local call_duration=$((call_end - call_start))
  local output_size
  output_size=$(wc -c < "$tmp_output" | tr -d ' ')

  if type record_metrics &>/dev/null; then
    local status="ok"
    [[ "$exit_code" -ne 0 ]] && status="error"
    record_metrics "$active_model" "$prompt_size" "$output_size" "$call_duration" "$phase_label" "$status" "0" "$active_runtime"
  fi

  # End session tracking
  if [[ -n "$_session_id" ]] && declare -f session_end >/dev/null 2>&1; then
    local tokens_est=$((prompt_size / 4 + output_size / 4))
    session_end "$_session_id" "$exit_code" "$tokens_est" 2>/dev/null || true
  fi

  # -- POS-LLM Guard: Circuit breaker update (AC5 -- Story 101.12) --
  if [[ -n "${CIRCUIT_BREAKER_THRESHOLD:-}" ]]; then
    if [[ "$exit_code" -ne 0 ]]; then
      # Story 115.7: classify error to feed breaker with type-aware increment
      local _error_type="unknown"
      if [[ -f "$tmp_output" ]]; then
        _error_type=$(classify_error "$tmp_output" "$exit_code")
      fi
      case "$_error_type" in
        permanent)
          # Permanent errors fast-trip the breaker (increment by 3)
          _RLP_CONSECUTIVE_FAILURES=$((_RLP_CONSECUTIVE_FAILURES + 3))
          echo "  [CIRCUIT-BREAKER] Permanent error detected -- fast-trip (+3, total: $_RLP_CONSECUTIVE_FAILURES)" >&2
          ;;
        transient)
          # Transient errors increment normally (increment by 1)
          _RLP_CONSECUTIVE_FAILURES=$((_RLP_CONSECUTIVE_FAILURES + 1))
          ;;
        *)
          # Unknown errors increment normally
          _RLP_CONSECUTIVE_FAILURES=$((_RLP_CONSECUTIVE_FAILURES + 1))
          ;;
      esac
    else
      _RLP_CONSECUTIVE_FAILURES=0
      _RLP_UNKNOWN_ERROR_RETRIES=0
    fi
  fi

  # Credential pool feedback (Story 115.10)
  if [[ -n "${_pool_key:-}" ]] && declare -f pool_report_success >/dev/null 2>&1; then
    if [[ "$exit_code" -eq 0 ]]; then
      pool_report_success "$_pool_key" 2>/dev/null || true
    else
      pool_report_error "$_pool_key" "${exit_code}" 2>/dev/null || true
    fi
  fi

  # "" P"S-LLM Guard: Filter (AC4 " Story 101.12) ""
  if [[ "${HEADLESS_FILTER:-}" == "true" && "$exit_code" -eq 0 ]] && declare -f filter_llm_output >/dev/null 2>&1; then
    local filtered_output
    filtered_output="$(filter_llm_output "$(cat "$tmp_output")")"
    printf '%s' "$filtered_output" > "$tmp_output"
  fi

  cat "$tmp_output"
  rm -f "$tmp_output" "$prompt_input"
  return $exit_code
}

# 
# Evaluator Integration " Optional hook between phases
# 
# Call after run_llm_prompt to evaluate output quality.
# Backward compatible: no-ops if evaluator.sh not loaded or phase not configured.
# Story: RUNNER-2.1
#
# Args:
#   $1=output_file   " the file produced by the phase
#   $2=phase_label   " phase name (e.g., "1_research")
#   $3=log_file      " log file for evaluator LLM calls
# Returns: verdict string (PASS|RETRY|REMEDIATE|HALT) to stdout
#          Exit code: 0=PASS, 1=RETRY, 2=REMEDIATE, 3=HALT
# If evaluator is not loaded or phase has no evaluator: returns PASS (exit 0)

run_phase_evaluator() {
  local output_file="$1"
  local phase_label="${2:-unknown}"
  local log_file="${3:-/dev/null}"
  local _saved_eval_tier1_only="${EVALUATOR_TIER1_ONLY:-false}"

  # Guard: --no-eval flag disables evaluator completely (Story 101.11 AC14)
  if [[ "${EVAL_DISABLED:-false}" == "true" ]]; then
    echo "PASS"
    return 0
  fi

  # Guard: evaluator not loaded
  if ! declare -f evaluate_phase_output >/dev/null 2>&1; then
    echo "PASS"
    return 0
  fi

  # Guard: phase not configured for evaluation
  if ! declare -f phase_has_evaluator >/dev/null 2>&1 || ! phase_has_evaluator "$phase_label"; then
    echo "PASS"
    return 0
  fi

  # Guard: --eval-tier1-only skips Tier 2 LLM rubrics (Story 101.11 AC13)
  if [[ "${EVAL_TIER1_ONLY:-false}" == "true" ]]; then
    export EVALUATOR_TIER1_ONLY="true"
  fi

  # Run evaluation
  local eval_result
  local eval_exit=0
  eval_result=$(evaluate_phase_output "$output_file" "$phase_label" "$log_file" 2>/dev/null) || eval_exit=$?
  export EVALUATOR_TIER1_ONLY="$_saved_eval_tier1_only"

  # Guard: empty result means evaluator crashed -- treat as PASS (fail-open)
  if [[ -z "$eval_result" ]]; then
    echo "    Evaluator: evaluate_phase_output returned empty for $phase_label -- fail-open to PASS" >&2
    echo "PASS"
    return 0
  fi

  # Save eval result to file alongside the output
  local eval_result_file="${output_file%.*}-eval-result.json"
  echo "$eval_result" > "$eval_result_file" 2>/dev/null || true

  # Extract verdict
  local verdict
  if command -v jq >/dev/null 2>&1; then
    verdict=$(echo "$eval_result" | jq -r '.verdict // "PASS"' 2>/dev/null || echo "PASS")
  else
    verdict=$(python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('verdict','PASS'))" <<< "$eval_result" 2>/dev/null || echo "PASS")
  fi

  # RETRY limiter: max 1 retry per phase, second RETRY ' REMEDIATE (Story 101.11 AC11)
  if [[ "$verdict" == "RETRY" ]]; then
    local retry_key="_EVAL_RETRY_${phase_label//[^a-zA-Z0-9_]/_}"
    local retry_count="${!retry_key:-0}"
    if [[ "$retry_count" -ge 1 ]]; then
      echo "    Evaluator: max 1 RETRY reached for $phase_label -- downgrading to REMEDIATE" >&2
      verdict="REMEDIATE"
      eval_exit=2
    else
      eval "$retry_key=$((retry_count + 1))"
      export "$retry_key"
    fi
  fi

  echo "$verdict"
  return $eval_exit
}
