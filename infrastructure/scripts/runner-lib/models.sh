#!/bin/bash
# SINKRA Pipeline — Canonical Model Catalog
# Single source of truth for runtime model defaults and pricing used by runner-lib consumers.

_runner_lib_model_catalog() {
  local runtime="$1"
  case "$runtime" in
    claude)
      echo "quality=opus"
      echo "balanced=sonnet"
      echo "fast=haiku"
      ;;
    codex)
      echo "quality=gpt-5.4"
      echo "balanced=gpt-5.4"
      echo "fast=gpt-5.4-mini"
      ;;
    gemini)
      echo "quality=gemini-3.1-pro-preview"
      echo "balanced=gemini-3.1-pro-preview"
      echo "fast=gemini-3.1-pro-preview"
      ;;
    *)
      return 1
      ;;
  esac
}

_runner_lib_model_override() {
  local runtime="$1"
  local profile="$2"

  local runtime_token profile_token runtime_var profile_var
  runtime_token=$(printf '%s' "$runtime" | tr '[:lower:]-' '[:upper:]_')
  profile_token=$(printf '%s' "$profile" | tr '[:lower:]-' '[:upper:]_')
  runtime_var="SINKRA_MODEL_${runtime_token}_${profile_token}"
  profile_var="SINKRA_MODEL_${profile_token}"

  if [[ -n "${!runtime_var:-}" ]]; then
    printf '%s\n' "${!runtime_var}"
    return 0
  fi

  if [[ -n "${!profile_var:-}" ]]; then
    printf '%s\n' "${!profile_var}"
    return 0
  fi

  return 1
}

_runner_lib_model_from_catalog() {
  local runtime="$1"
  local profile="$2"

  local line
  while IFS= read -r line; do
    [[ "$line" == "$profile="* ]] || continue
    printf '%s\n' "${line#*=}"
    return 0
  done < <(_runner_lib_model_catalog "$runtime")

  return 1
}

get_runtime_model() {
  local runtime="$1"
  local profile="${2:-balanced}"
  local override=""

  override="$(_runner_lib_model_override "$runtime" "$profile" 2>/dev/null || true)"
  if [[ -n "$override" ]]; then
    printf '%s\n' "$override"
    return 0
  fi

  if _runner_lib_model_from_catalog "$runtime" "$profile"; then
    return 0
  fi

  return 1
}

get_quality_model() {
  get_runtime_model "$1" "quality"
}

get_balanced_model() {
  get_runtime_model "$1" "balanced"
}

get_fast_model() {
  get_runtime_model "$1" "fast"
}

resolve_model_alias() {
  local model="$1"
  local runtime="${2:-${SELECTED_RUNTIME:-}}"

  if [[ -z "$runtime" ]]; then
    printf '%s\n' "$model"
    return 0
  fi

  case "$model" in
    gpt-5-codex)
      get_quality_model "codex"
      ;;
    gpt-5.3-codex-spark)
      get_fast_model "codex"
      ;;
    quality|opus|high)
      get_quality_model "$runtime"
      ;;
    balanced|default|sonnet)
      get_balanced_model "$runtime"
      ;;
    fast|haiku|low)
      get_fast_model "$runtime"
      ;;
    *)
      printf '%s\n' "$model"
      ;;
  esac
}

describe_runtime_models() {
  local runtime="$1"
  printf 'quality=%s balanced=%s fast=%s\n' \
    "$(get_quality_model "$runtime")" \
    "$(get_balanced_model "$runtime")" \
    "$(get_fast_model "$runtime")"
}

# ═══════════════════════════════════════════════════════════════
# Model Pricing — Single Source of Truth
# ═══════════════════════════════════════════════════════════════
# Prices per 1M tokens (USD): input output
# Updated: 2026-03-28
# Sources: anthropic.com/pricing, openai.com/api/pricing, ai.google.dev/pricing
# Story: RUNNER-3.2 (Unified Cost Tracking)
#
# NOTE: metrics.sh wraps this function via get_pricing(), normalizing the
# output format for legacy callers. models.sh remains the canonical registry
# for both capabilities and pricing.

_runner_lib_model_pricing() {
  local model="$1"
  local resolved
  resolved="$(resolve_model_alias "$model" "${2:-${SELECTED_RUNTIME:-}}")"

  # Returns: "input_per_1m output_per_1m"
  case "$resolved" in
    # Anthropic
    opus|claude-opus-4-6)              echo "5.00 25.00" ;;
    sonnet|claude-sonnet-4-6)          echo "3.00 15.00" ;;
    haiku|claude-haiku-4-5)            echo "1.00 5.00" ;;

    # OpenAI
    gpt-5.4|gpt-5-codex)              echo "2.50 15.00" ;;
    gpt-5.4-mini)                      echo "0.75 4.50" ;;
    o3)                                echo "10.00 40.00" ;;
    o4-mini)                           echo "2.00 8.00" ;;

    # Gemini
    gemini-3.1-pro-preview)            echo "3.00 15.00" ;;
    gemini-3.1-flash)                  echo "0.15 0.60" ;;
    gemini-2.5-pro)                    echo "1.88 12.50" ;;
    gemini-2.5-flash)                  echo "0.30 2.50" ;;

    # Fallback (conservative)
    *)                                 echo "3.00 15.00" ;;
  esac
}

# Get cost for a given token count.
# Args: $1=model, $2=input_tokens, $3=output_tokens, $4=runtime(optional)
# Prints: cost in USD (6 decimal places)
get_model_cost() {
  local model="$1"
  local input_tokens="$2"
  local output_tokens="$3"
  local runtime="${4:-${SELECTED_RUNTIME:-}}"

  local pricing
  pricing="$(_runner_lib_model_pricing "$model" "$runtime")"
  local input_price="${pricing%% *}"
  local output_price="${pricing##* }"

  python3 -c "
i = $input_tokens * $input_price / 1_000_000
o = $output_tokens * $output_price / 1_000_000
print(f'{i + o:.6f}')
" 2>/dev/null || echo "0.000000"
}
