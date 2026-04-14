#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER-LIB — Replan-on-Failure
# ═══════════════════════════════════════════════════════════════
# Tries alternative strategies before aborting a failed phase.
# NEVER truncates prompts — a complete prompt > a mangled one.
#
# Strategies (in order):
#   1. model_switch — retry with alternative model (same runtime)
#   2. runtime_switch — retry with alternative runtime entirely
#   3. skip_degraded — mark phase as degraded, continue pipeline
#
# Usage:
#   PHASE_REPLAN=true
#   run_with_replan "$prompt_file" "$output_file" "phase_5"
#
# Story: RUNNER-3.3 (Cascade Model Routing + Replan-on-Failure)
# Dependencies: runtime.sh (_exec_runtime, _get_fallback_runtimes, _get_default_model)

REPLAN_MAX_ATTEMPTS="${REPLAN_MAX_ATTEMPTS:-2}"

# Track degraded phases for downstream awareness
PHASES_DEGRADED="${PHASES_DEGRADED:-}"

# Run a phase with replan-on-failure support.
# Args: $1=prompt_file, $2=output_file, $3=phase_label
# Env: PHASE_REPLAN=true to enable
# Returns: 0=success (or degraded), 1=all strategies failed
run_with_replan() {
  local prompt_file="$1"
  local output_file="$2"
  local phase="${3:-unknown}"
  local replan_enabled="${PHASE_REPLAN:-false}"

  # Primary attempt
  local exit_code=0
  _exec_runtime "$MODEL" "$prompt_file" "$output_file" || exit_code=$?

  [[ $exit_code -eq 0 ]] && return 0
  [[ "$replan_enabled" != "true" ]] && return $exit_code

  # Replan loop
  local attempt=0
  local strategies=("model_switch" "runtime_switch" "skip_degraded")
  local tried=""

  while [[ $attempt -lt $REPLAN_MAX_ATTEMPTS && $attempt -lt ${#strategies[@]} ]]; do
    local strategy="${strategies[$attempt]}"
    attempt=$((attempt + 1))
    tried="${tried:+$tried, }$strategy"

    echo "  🔄 [replan] Phase $phase attempt $attempt/$REPLAN_MAX_ATTEMPTS: strategy=$strategy" >&2

    case "$strategy" in
      model_switch)
        local alt_model
        alt_model=$(_get_replan_fallback_model "$SELECTED_RUNTIME" "$MODEL")
        if [[ -z "$alt_model" ]]; then
          echo "  [replan] No alternative model for $SELECTED_RUNTIME/$MODEL" >&2
          continue
        fi
        echo "  [replan] Switching model: $MODEL → $alt_model" >&2
        exit_code=0
        _exec_runtime "$alt_model" "$prompt_file" "$output_file" "$SELECTED_RUNTIME" || exit_code=$?
        ;;

      runtime_switch)
        local fallback_runtimes
        fallback_runtimes=$(_get_fallback_runtimes "$SELECTED_RUNTIME")
        local success=false
        for fb_runtime in $fallback_runtimes; do
          local fb_model
          fb_model=$(_get_default_model "$fb_runtime")
          echo "  [replan] Switching runtime: $SELECTED_RUNTIME/$MODEL → $fb_runtime/$fb_model" >&2
          exit_code=0
          _exec_runtime "$fb_model" "$prompt_file" "$output_file" "$fb_runtime" || exit_code=$?
          if [[ $exit_code -eq 0 ]]; then
            success=true
            break
          fi
        done
        $success || continue
        ;;

      skip_degraded)
        echo "  ⚠️  [replan] Skipping phase $phase with degraded output" >&2
        echo "DEGRADED: Phase $phase skipped after $attempt replan attempts. Strategies tried: $tried" > "$output_file"
        PHASES_DEGRADED="${PHASES_DEGRADED:+$PHASES_DEGRADED,}$phase"
        export PHASES_DEGRADED
        return 0
        ;;
    esac

    # Record replan attempt in metrics
    if declare -f record_metrics >/dev/null 2>&1; then
      local out_bytes in_bytes
      out_bytes=$(wc -c < "$output_file" 2>/dev/null | tr -d ' ' || echo 0)
      in_bytes=$(wc -c < "$prompt_file" 2>/dev/null | tr -d ' ' || echo 0)
      record_metrics "$MODEL" "$in_bytes" "$out_bytes" "0" "replan-$phase-$strategy" \
        "$([ $exit_code -eq 0 ] && echo ok || echo error)" 2>/dev/null || true
    fi

    [[ $exit_code -eq 0 ]] && return 0
  done

  echo "  ❌ [replan] Phase $phase failed after $REPLAN_MAX_ATTEMPTS replans. Strategies tried: $tried" >&2
  return 1
}

# Bridge wrapper: run_llm_prompt() with replan-on-failure.
# Same signature as run_llm_prompt(): (model, prompt_string, log_file, phase_label)
# Returns string output like run_llm_prompt(). Delegates to run_llm_prompt() for
# each attempt (primary + replan strategies), preserving metrics and session tracking.
#
# Env: PHASE_REPLAN=true to enable replan (otherwise just delegates once)
#      REPLAN_MAX_ATTEMPTS (default 2)
#
# Story: 101.10 AC1
run_llm_prompt_with_replan() {
  local model="$1"
  local prompt="$2"
  local log_file="$3"
  local phase_label="${4:-unknown}"
  local replan_enabled="${PHASE_REPLAN:-false}"

  # Primary attempt via run_llm_prompt
  local output=""
  local exit_code=0
  output=$(run_llm_prompt "$model" "$prompt" "$log_file" "$phase_label") || exit_code=$?

  if [[ $exit_code -eq 0 && -n "$output" ]]; then
    printf '%s' "$output"
    return 0
  fi

  # If replan disabled, pass through the failure
  if [[ "$replan_enabled" != "true" ]]; then
    [[ -n "$output" ]] && printf '%s' "$output"
    return $exit_code
  fi

  # Replan loop — same strategies as run_with_replan, but using run_llm_prompt
  local attempt=0
  local strategies=("model_switch" "runtime_switch" "skip_degraded")
  local tried=""
  local max_attempts="${REPLAN_MAX_ATTEMPTS:-2}"

  while [[ $attempt -lt $max_attempts && $attempt -lt ${#strategies[@]} ]]; do
    local strategy="${strategies[$attempt]}"
    attempt=$((attempt + 1))
    tried="${tried:+$tried, }$strategy"

    echo "  🔄 [replan] Phase $phase_label attempt $attempt/$max_attempts: strategy=$strategy" >&2

    case "$strategy" in
      model_switch)
        local alt_model
        alt_model=$(_get_replan_fallback_model "$SELECTED_RUNTIME" "$model")
        if [[ -z "$alt_model" ]]; then
          echo "  [replan] No alternative model for $SELECTED_RUNTIME/$model" >&2
          continue
        fi
        echo "  [replan] Switching model: $model → $alt_model" >&2
        exit_code=0
        output=$(run_llm_prompt "$alt_model" "$prompt" "$log_file" "replan-$phase_label-model_switch") || exit_code=$?
        ;;

      runtime_switch)
        local fallback_runtimes
        fallback_runtimes=$(_get_fallback_runtimes "$SELECTED_RUNTIME")
        local found_success=false
        for fb_runtime in $fallback_runtimes; do
          local fb_model
          fb_model=$(_get_default_model "$fb_runtime")
          echo "  [replan] Switching runtime: $SELECTED_RUNTIME/$model → $fb_runtime/$fb_model" >&2
          local saved_runtime="$SELECTED_RUNTIME"
          SELECTED_RUNTIME="$fb_runtime"
          exit_code=0
          output=$(run_llm_prompt "$fb_model" "$prompt" "$log_file" "replan-$phase_label-runtime_switch") || exit_code=$?
          SELECTED_RUNTIME="$saved_runtime"
          if [[ $exit_code -eq 0 && -n "$output" ]]; then
            found_success=true
            break
          fi
        done
        $found_success || continue
        ;;

      skip_degraded)
        echo "  ⚠️  [replan] Skipping phase $phase_label with degraded output" >&2
        output="DEGRADED: Phase $phase_label skipped after $attempt replan attempts. Strategies tried: $tried"
        PHASES_DEGRADED="${PHASES_DEGRADED:+$PHASES_DEGRADED,}$phase_label"
        export PHASES_DEGRADED
        printf '%s' "$output"
        # Record degraded metric
        if declare -f record_metrics >/dev/null 2>&1; then
          record_metrics "$model" "${#prompt}" "${#output}" "0" "replan-$phase_label-skip_degraded" "degraded" 2>/dev/null || true
        fi
        return 0
        ;;
    esac

    if [[ $exit_code -eq 0 && -n "$output" ]]; then
      printf '%s' "$output"
      return 0
    fi
  done

  echo "  ❌ [replan] Phase $phase_label failed after $max_attempts replans. Strategies tried: $tried" >&2
  [[ -n "$output" ]] && printf '%s' "$output"
  return 1
}

# Get alternative model for a runtime (different tier).
# Args: $1=runtime, $2=current_model
_get_replan_fallback_model() {
  local runtime="$1"
  local current_model="$2"
  local resolved
  resolved=$(resolve_model_alias "$current_model" "$runtime" 2>/dev/null || echo "$current_model")

  case "$runtime" in
    claude)
      case "$resolved" in
        opus|claude-opus-4-6)     echo "sonnet" ;;
        sonnet|claude-sonnet-4-6) echo "haiku" ;;
        *)                        echo "" ;;
      esac
      ;;
    codex)
      case "$resolved" in
        gpt-5.4)      echo "gpt-5.4-mini" ;;
        gpt-5.4-mini) echo "" ;;
        *)            echo "gpt-5.4-mini" ;;
      esac
      ;;
    gemini)
      case "$resolved" in
        gemini-3.1-pro-preview) echo "" ;;  # No cheaper gemini allowed (flash banned)
        *)                      echo "" ;;
      esac
      ;;
  esac
}

# replan_on_error(output_file, exit_code, phase_label)
# Routes errors to retry/replan/abort based on classify_error() classification.
# Returns: 0=continue (retry), 1=abort (permanent), 2=retry (transient)
#
# Story: 115.7 AC4
replan_on_error() {
  local output_file="${1:-}"
  local exit_code="${2:-1}"
  local phase_label="${3:-unknown}"

  # Classify the error
  local error_type
  if declare -f classify_error >/dev/null 2>&1; then
    error_type=$(classify_error "$output_file" "$exit_code")
  else
    error_type="unknown"
  fi

  case "$error_type" in
    permanent)
      echo "  [REPLAN] Permanent error in phase $phase_label — aborting (no retry)" >&2
      return 1
      ;;
    transient)
      echo "  [REPLAN] Transient error in phase $phase_label — signaling retry" >&2
      return 2
      ;;
    *)
      echo "  [REPLAN] Unknown error in phase $phase_label — signaling retry (cautious)" >&2
      return 2
      ;;
  esac
}
