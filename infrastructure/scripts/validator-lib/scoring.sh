#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR-LIB: scoring.sh — Dimensional weighted scoring + guardrails
# ═══════════════════════════════════════════════════════════════════════════════
# Shared between validate-skill.sh and validate-squad.sh
# Source: infrastructure/scripts/validator-lib/scoring.sh

export LC_NUMERIC=C

# State — consumers must reset via scoring_reset() before each validation
_SCORING_TOTAL_WEIGHTED=0
_SCORING_TOTAL_WEIGHT=0
_SCORING_GUARDRAIL_REASONS=()
_SCORING_SCORE_CAP=""

# Per-dimension tracking (parallel arrays — Bash 3.2 compatible, no declare -A)
_SCORING_DIM_NAMES=()
_SCORING_DIM_SCORES_VALUES=()
_SCORING_DIM_STATUS_VALUES=()

# Internal: find index for a dimension name, or -1
_scoring_dim_index() {
  local needle="$1"
  local i
  for i in "${!_SCORING_DIM_NAMES[@]}"; do
    if [[ "${_SCORING_DIM_NAMES[$i]}" == "$needle" ]]; then
      echo "$i"; return 0
    fi
  done
  echo "-1"; return 1
}

# Internal: set score/status for a dimension (insert or update)
_scoring_dim_set() {
  local dim="$1" score="$2" status="$3"
  local idx
  idx=$(_scoring_dim_index "$dim") || true
  if [[ "$idx" -ge 0 ]]; then
    _SCORING_DIM_SCORES_VALUES[$idx]="$score"
    _SCORING_DIM_STATUS_VALUES[$idx]="$status"
  else
    _SCORING_DIM_NAMES+=("$dim")
    _SCORING_DIM_SCORES_VALUES+=("$score")
    _SCORING_DIM_STATUS_VALUES+=("$status")
  fi
}

scoring_reset() {
  _SCORING_TOTAL_WEIGHTED=0
  _SCORING_TOTAL_WEIGHT=0
  _SCORING_GUARDRAIL_REASONS=()
  _SCORING_SCORE_CAP=""
  _SCORING_DIM_NAMES=()
  _SCORING_DIM_SCORES_VALUES=()
  _SCORING_DIM_STATUS_VALUES=()
}

# Register a dimension score
# Usage: scoring_add "D1" passed_count total_count weight
scoring_add() {
  local dim="$1" passed="$2" total="$3" weight="$4"
  if [[ "$total" -eq 0 ]]; then return; fi

  local dim_score
  dim_score=$(awk "BEGIN { printf \"%.1f\", ($passed / $total) * 10 }")
  local weighted
  weighted=$(awk "BEGIN { printf \"%.4f\", $dim_score * $weight }")
  _SCORING_TOTAL_WEIGHTED=$(awk "BEGIN { printf \"%.4f\", $_SCORING_TOTAL_WEIGHTED + $weighted }")
  _SCORING_TOTAL_WEIGHT=$(awk "BEGIN { printf \"%.4f\", $_SCORING_TOTAL_WEIGHT + $weight }")

  local _status="FAIL"
  if awk "BEGIN { exit ($dim_score >= 7.0) ? 0 : 1 }" 2>/dev/null; then
    _status="PASS"
  elif awk "BEGIN { exit ($dim_score >= 5.0) ? 0 : 1 }" 2>/dev/null; then
    _status="WARN"
  fi
  _scoring_dim_set "$dim" "$dim_score" "$_status"
}

# Get the raw weighted average (before guardrails)
scoring_raw_score() {
  if awk "BEGIN { exit ($_SCORING_TOTAL_WEIGHT > 0) ? 0 : 1 }" 2>/dev/null; then
    awk "BEGIN { printf \"%.1f\", $_SCORING_TOTAL_WEIGHTED / $_SCORING_TOTAL_WEIGHT }"
  else
    echo "0.0"
  fi
}

# Get score and status for a dimension
# Usage: scoring_dim_score "D1" → "10.0"
scoring_dim_score() {
  local idx
  idx=$(_scoring_dim_index "$1") || true
  if [[ "$idx" -ge 0 ]]; then echo "${_SCORING_DIM_SCORES_VALUES[$idx]}"; else echo ""; fi
}
scoring_dim_status() {
  local idx
  idx=$(_scoring_dim_index "$1") || true
  if [[ "$idx" -ge 0 ]]; then echo "${_SCORING_DIM_STATUS_VALUES[$idx]}"; else echo ""; fi
}

# Get all guardrail reasons
scoring_guardrail_reasons() {
  for reason in "${_SCORING_GUARDRAIL_REASONS[@]}"; do
    echo "$reason"
  done
}

scoring_score_cap() { echo "${_SCORING_SCORE_CAP:-none}"; }

# Apply standard guardrails and return final score
# Usage: apply_guardrails blocking_count [high_dims...] → prints "score|verdict"
#
# Guardrails:
#   G1: blocking_count > 0 → cap at 6.0
#   G2: any HIGH-weight dim < 3.0 → cap at 6.0
#   G3: 2+ dims < 5.0 → cap at 5.0
#
# Verdict: PASS (>=7.0, no blocks) | WARN (>=5.0) | FAIL (<5.0 or blocks)
apply_guardrails() {
  local blocking_count="$1"
  shift
  local high_dims=("$@")  # dimension names with HIGH weight

  local final_score
  final_score=$(scoring_raw_score)
  _SCORING_GUARDRAIL_REASONS=()
  _SCORING_SCORE_CAP=""

  # G1: Blocking issues cap at 6.0
  if [[ "$blocking_count" -gt 0 ]]; then
    if awk "BEGIN { exit ($final_score > 6.0) ? 0 : 1 }" 2>/dev/null; then
      final_score="6.0"
      _SCORING_SCORE_CAP="6.0"
      _SCORING_GUARDRAIL_REASONS+=("blocking issues force cap at 6.0")
    fi
  fi

  # G2: HIGH dimension debt cap at 6.0
  for dim in "${high_dims[@]}"; do
    local ds
    ds="$(scoring_dim_score "$dim")"
    if [[ -n "$ds" ]] && awk "BEGIN { exit ($ds < 3.0) ? 0 : 1 }" 2>/dev/null; then
      if awk "BEGIN { exit ($final_score > 6.0) ? 0 : 1 }" 2>/dev/null; then
        final_score="6.0"
        _SCORING_SCORE_CAP="6.0"
        _SCORING_GUARDRAIL_REASONS+=("HIGH dimension $dim=$ds < 3.0 forces cap at 6.0")
      fi
    fi
  done

  # G3: Combined critical debt — 2+ dims < 5.0 → cap at 5.0
  local low_dim_count=0
  local _i _dim_name
  for _i in "${!_SCORING_DIM_NAMES[@]}"; do
    _dim_name="${_SCORING_DIM_NAMES[$_i]}"
    local ds="${_SCORING_DIM_SCORES_VALUES[$_i]}"
    if awk "BEGIN { exit ($ds < 5.0) ? 0 : 1 }" 2>/dev/null; then
      low_dim_count=$((low_dim_count + 1))
    fi
  done
  if [[ "$low_dim_count" -ge 2 ]]; then
    if awk "BEGIN { exit ($final_score > 5.0) ? 0 : 1 }" 2>/dev/null; then
      final_score="5.0"
      _SCORING_SCORE_CAP="5.0"
      _SCORING_GUARDRAIL_REASONS+=("$low_dim_count dimensions < 5.0 forces cap at 5.0")
    fi
  fi

  # Verdict
  local verdict="FAIL"
  if [[ "$blocking_count" -gt 0 ]]; then
    verdict="FAIL"
  elif awk "BEGIN { exit ($final_score >= 7.0) ? 0 : 1 }" 2>/dev/null; then
    verdict="PASS"
  elif awk "BEGIN { exit ($final_score >= 5.0) ? 0 : 1 }" 2>/dev/null; then
    verdict="WARN"
  fi

  echo "$final_score|$verdict"
}

VALIDATOR_LIB_SCORING=true
