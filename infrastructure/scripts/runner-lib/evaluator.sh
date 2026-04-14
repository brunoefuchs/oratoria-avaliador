#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER-LIB — 3-Tier Evaluator Phase
# ═══════════════════════════════════════════════════════════════
# Evaluates LLM phase output using a 3-tier pipeline:
#   Tier 1: Deterministic — schema, format, fields ($0, <1s)
#   Tier 2: LLM Rubrics   — Haiku-based scoring ($0.009, ~15s)
#   Tier 3: Human Review   — flags for manual review
#
# Fail-fast: Tier 1 failure skips Tier 2 (cost saving).
# Backward compatible: squads without evaluator config are unaffected.
#
# Story: RUNNER-2.1 (Evaluator Phase)
# Dependencies: assertions.sh (Tier 1), runtime.sh + models.sh (Tier 2)

# ═══════════════════════════════════════════════════════════════
# Configuration defaults
# ═══════════════════════════════════════════════════════════════

# Default rubrics directory (runner-lib generic rubrics)
EVALUATOR_DEFAULT_RUBRICS_DIR=""

# Per-squad rubrics override (set by squad before calling)
EVALUATOR_RUBRICS_DIR=""

# Tier 2 model (defaults to "fast" = Haiku)
EVALUATOR_MODEL="${EVALUATOR_MODEL:-fast}"

# Tier 2 max tokens per rubric call
EVALUATOR_MAX_TOKENS="${EVALUATOR_MAX_TOKENS:-200}"

# Human review output directory
EVALUATOR_REVIEW_DIR=""

EVALUATOR_GUARDRAIL_NOTICE_EMITTED="${EVALUATOR_GUARDRAIL_NOTICE_EMITTED:-false}"

_evaluator_init() {
  local lib_dir
  lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  EVALUATOR_DEFAULT_RUBRICS_DIR="$lib_dir/rubrics"

  # Ensure dependencies are loaded
  if ! declare -f assert_yaml_schema >/dev/null 2>&1; then
    if [[ -f "$lib_dir/assertions.sh" ]]; then
      source "$lib_dir/assertions.sh"
    fi
  fi
  if ! declare -f run_llm_prompt >/dev/null 2>&1; then
    if [[ -f "$lib_dir/runtime.sh" ]]; then
      source "$lib_dir/runtime.sh"
    fi
  fi
}
_evaluator_init

_configure_evaluator_guardrails() {
  local eval_runtime="${1:-${SELECTED_RUNTIME:-claude}}"
  local best_effort=false

  PHASE_MAX_TURNS=""
  PHASE_ALLOWED_TOOLS=""

  if declare -f runtime_supports_flag >/dev/null 2>&1; then
    if runtime_supports_flag "$eval_runtime" "max-turns"; then
      PHASE_MAX_TURNS="1"
    else
      best_effort=true
    fi

    if runtime_supports_flag "$eval_runtime" "allowed-tools"; then
      PHASE_ALLOWED_TOOLS="Read,Glob,Grep"
    else
      best_effort=true
    fi
  else
    PHASE_MAX_TURNS="1"
    PHASE_ALLOWED_TOOLS="Read,Glob,Grep"
  fi

  if [[ "$best_effort" == true && "$EVALUATOR_GUARDRAIL_NOTICE_EMITTED" != "true" ]]; then
    echo "  [INFO] Evaluator guardrails unavailable in ${eval_runtime}; rubric calls seguem em best-effort." >&2
    EVALUATOR_GUARDRAIL_NOTICE_EMITTED="true"
  fi
}

# ═══════════════════════════════════════════════════════════════
# Tier 1: Deterministic checks
# ═══════════════════════════════════════════════════════════════
# Delegates to assertions.sh functions. $0 cost, <1s.
# Args:
#   $1=output_file  — the file to validate
#   $2=schema_spec  — "field:type,field:type,..." (optional, for YAML)
#   $3=min_bytes    — minimum file size (optional, default 50)
# Returns: JSON string with tier 1 result

_evaluate_deterministic() {
  local output_file="$1"
  local schema_spec="${2:-}"
  local min_bytes="${3:-50}"

  if [[ ! -f "$output_file" ]]; then
    echo '{"passed":false,"checks":{"file_exists":false},"score":0}'
    return 1
  fi

  # Run all checks, collect boolean results
  local all_passed=true
  local chk_file_exists=true
  local chk_min_size=true
  local chk_format_valid="skipped"
  local chk_schema_valid=""

  local size
  size=$(wc -c < "$output_file" | tr -d ' ')
  if [[ "$size" -lt "$min_bytes" ]]; then
    chk_min_size=false; all_passed=false
  fi

  local ext="${output_file##*.}"
  case "$ext" in
    yaml|yml)
      if assert_yaml_valid "$output_file" 2>/dev/null; then
        chk_format_valid=true
      else
        chk_format_valid=false; all_passed=false
      fi
      if [[ -n "$schema_spec" ]]; then
        if assert_yaml_schema "$output_file" "$schema_spec" 2>/dev/null; then
          chk_schema_valid=true
        else
          chk_schema_valid=false; all_passed=false
        fi
      fi
      ;;
    json)
      if assert_json_valid "$output_file" 2>/dev/null; then chk_format_valid=true
      else chk_format_valid=false; all_passed=false; fi
      ;;
    md)
      if assert_markdown_valid "$output_file" 2>/dev/null; then chk_format_valid=true
      else chk_format_valid=false; all_passed=false; fi
      ;;
  esac

  local score=100
  [[ "$all_passed" != true ]] && score=0

  # Build JSON in a single jq call
  local schema_arg=""
  [[ -n "$chk_schema_valid" ]] && schema_arg="--argjson schema_valid $chk_schema_valid"

  jq -n \
    --argjson passed "$all_passed" \
    --argjson file_exists "$chk_file_exists" \
    --argjson min_size "$chk_min_size" \
    --arg format_valid "$chk_format_valid" \
    --argjson score "$score" \
    $schema_arg \
    '{passed: $passed, checks: {file_exists: $file_exists, min_size: $min_size, format_valid: (if $format_valid == "true" then true elif $format_valid == "false" then false else $format_valid end)} + (if $ARGS.named.schema_valid then {schema_valid: $ARGS.named.schema_valid} else {} end), score: $score}'
}

# ═══════════════════════════════════════════════════════════════
# Tier 2: LLM Rubric Evaluation
# ═══════════════════════════════════════════════════════════════
# Runs N configurable Haiku rubrics against the output.
# Each rubric is a YAML file with a prompt template.
# Cost target: <= $0.01 per run (3 Haiku calls).
# Args:
#   $1=output_file      — the file to evaluate
#   $2=rubrics_dir      — directory containing rubric YAML files (optional)
#   $3=log_file         — log file for LLM calls
#   $4=task_description — description of what the agent was supposed to do
#   $5=expected_fields  — expected output fields/structure description
# Returns: JSON string with tier 2 result

_evaluate_llm_rubrics() {
  local output_file="$1"
  local rubrics_dir="${2:-${EVALUATOR_RUBRICS_DIR:-$EVALUATOR_DEFAULT_RUBRICS_DIR}}"
  local log_file="${3:-/dev/null}"
  local task_description="${4:-No task description provided}"
  local expected_fields="${5:-No expected fields specified}"

  if [[ "${EVALUATOR_TIER1_ONLY:-false}" == "true" ]]; then
    echo '{"passed":true,"rubrics":[],"overall_score":0,"total_cost":0,"skipped":true,"reason":"Tier 2 disabled by EVAL_TIER1_ONLY"}'
    return 0
  fi

  if [[ ! -d "$rubrics_dir" ]]; then
    echo '{"passed":true,"rubrics":[],"overall_score":0,"total_cost":0,"error":"no rubrics directory"}'
    return 0
  fi

  # Read output preview (first 2000 chars)
  local output_preview
  output_preview=$(head -c 2000 "$output_file")

  local rubrics_json="[]"
  local total_cost=0
  local total_weighted_score=0
  local total_weight=0
  local all_passed=true

  # Resolve model for Tier 2
  local eval_model="$EVALUATOR_MODEL"
  local eval_runtime="${SELECTED_RUNTIME:-claude}"

  # Only claude supports Haiku natively; for other runtimes use their fast model
  if [[ "$eval_runtime" != "claude" ]]; then
    eval_model="fast"
  fi

  for rubric_file in "$rubrics_dir"/*.yaml "$rubrics_dir"/*.yml; do
    [[ -f "$rubric_file" ]] || continue

    # Parse all rubric fields in a single python3 call
    local rubric_name rubric_threshold rubric_weight rubric_max_tokens rubric_prompt
    local _rubric_parsed
    _rubric_parsed=$(python3 - "$rubric_file" "$EVALUATOR_MAX_TOKENS" <<'PYEOF'
import yaml, sys
rubric_file = sys.argv[1]
default_max_tokens = sys.argv[2]
with open(rubric_file) as f:
    d = yaml.safe_load(f) or {}
r = d.get('rubric', {})
import os
name = r.get('name', os.path.splitext(os.path.basename(rubric_file))[0])
threshold = r.get('threshold', 0.7)
weight = r.get('weight', 1)
max_tokens = r.get('max_tokens', default_max_tokens)
prompt = d.get('prompt', 'Score this output 0-100. Respond with JSON: {"score": N, "reason": "one line"}')
# Use ASCII unit separator (0x1f) as delimiter to avoid conflicts with prompt content
sep = '\x1f'
print(f'{name}{sep}{threshold}{sep}{weight}{sep}{max_tokens}{sep}{prompt}', end='')
PYEOF
    ) 2>/dev/null
    IFS=$'\x1f' read -r rubric_name rubric_threshold rubric_weight rubric_max_tokens rubric_prompt <<< "$_rubric_parsed"

    # Template substitution
    rubric_prompt="${rubric_prompt//\{\{expected_fields\}\}/$expected_fields}"
    rubric_prompt="${rubric_prompt//\{\{output_preview\}\}/$output_preview}"
    rubric_prompt="${rubric_prompt//\{\{task_description\}\}/$task_description}"

    # Call LLM (Haiku)
    local call_start call_end
    call_start=$(date +%s)

    local llm_response
    # Save/restore phase overrides to avoid polluting caller state
    local _saved_max_turns="$PHASE_MAX_TURNS"
    local _saved_allowed_tools="$PHASE_ALLOWED_TOOLS"
    _configure_evaluator_guardrails "$eval_runtime"

    llm_response=$(run_llm_prompt "$eval_model" "$rubric_prompt" "$log_file" "evaluator-${rubric_name}" 2>/dev/null) || true

    PHASE_MAX_TURNS="$_saved_max_turns"
    PHASE_ALLOWED_TOOLS="$_saved_allowed_tools"

    call_end=$(date +%s)

    # Parse score from response (may be wrapped in ```json ... ``` code fences)
    local score=0
    local reason="no response"
    if [[ -n "$llm_response" ]]; then
      # Strip markdown code fences, then extract JSON
      local cleaned
      cleaned=$(echo "$llm_response" | sed 's/```json//g; s/```//g' | tr '\n' ' ')
      local json_part
      json_part=$(echo "$cleaned" | python3 -c "
import sys, re, json
text = sys.stdin.read()
m = re.search(r'\{[^{}]*\}', text)
if m:
    try:
        obj = json.loads(m.group())
        print(json.dumps(obj))
    except: print('{}')
else: print('{}')
" 2>/dev/null)
      if [[ -n "$json_part" && "$json_part" != "{}" ]]; then
        score=$(echo "$json_part" | jq -r '.score // 0' 2>/dev/null || echo 0)
        reason=$(echo "$json_part" | jq -r '.reason // "no reason"' 2>/dev/null || echo "parse error")
      fi
    fi

    # Estimate cost using metrics.sh (reuse canonical pricing)
    local prompt_tokens=$(( ${#rubric_prompt} / 4 ))
    local output_tokens=$(( ${#llm_response} / 4 ))
    local cost="0.003000"
    if declare -f calculate_cost >/dev/null 2>&1; then
      cost=$(calculate_cost "$prompt_tokens" "$output_tokens" "$eval_model")
    fi

    # Normalize score and check threshold (threshold is 0-1, score is 0-100)
    [[ "$score" -gt 100 ]] && score=100
    [[ "$score" -lt 0 ]] && score=0
    local threshold_score=$(( ${rubric_threshold%%.*} * 100 + ${rubric_threshold#*.}0 ))
    # Simplified: multiply threshold by 100 (handles 0.7 → 70)
    threshold_score=$(awk "BEGIN{printf \"%d\", $rubric_threshold * 100}")
    local rubric_passed="true"
    if [[ "$score" -lt "$threshold_score" ]]; then
      rubric_passed="false"
      all_passed=false
    fi

    # Accumulate weighted score
    total_weighted_score=$(( total_weighted_score + score * rubric_weight ))
    total_weight=$(( total_weight + rubric_weight ))
    total_cost=$(awk "BEGIN{printf \"%.6f\", $total_cost + $cost}")

    # Append to rubrics array
    rubrics_json=$(echo "$rubrics_json" | jq \
      --arg name "$rubric_name" \
      --argjson score "$score" \
      --argjson passed "$rubric_passed" \
      --arg cost "$cost" \
      --arg reason "$reason" \
      '. + [{"name": $name, "score": $score, "passed": $passed, "cost": ($cost | tonumber), "reason": $reason}]')
  done

  # Calculate overall score
  local overall_score=0
  if [[ "$total_weight" -gt 0 ]]; then
    overall_score=$(python3 -c "print(round($total_weighted_score / $total_weight, 1))" 2>/dev/null || echo 0)
  fi

  local passed_json="true"
  [[ "$all_passed" != true ]] && passed_json="false"

  jq -n \
    --argjson passed "$passed_json" \
    --argjson rubrics "$rubrics_json" \
    --argjson overall_score "$overall_score" \
    --arg total_cost "$total_cost" \
    '{passed: $passed, rubrics: $rubrics, overall_score: $overall_score, total_cost: ($total_cost | tonumber)}'
}

# ═══════════════════════════════════════════════════════════════
# Tier 3: Human Review Flag
# ═══════════════════════════════════════════════════════════════
# Creates a marker file for human review. Does not block pipeline.
# Args:
#   $1=output_file    — the file to flag
#   $2=review_dir     — directory to place review markers
#   $3=reason         — why human review is needed (optional)
# Returns: JSON string with tier 3 result

_flag_human_review() {
  local output_file="$1"
  local review_dir="${2:-${EVALUATOR_REVIEW_DIR:-}}"
  local reason="${3:-Flagged for human review}"

  if [[ -z "$review_dir" ]]; then
    echo '{"flagged":false,"reason":"no review directory configured"}'
    return 0
  fi

  mkdir -p "$review_dir"

  local basename
  basename=$(basename "$output_file")
  local marker_file="$review_dir/review-${basename%.yaml}.json"

  jq -n \
    --arg file "$output_file" \
    --arg reason "$reason" \
    --arg timestamp "$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S)" \
    '{file: $file, reason: $reason, flagged_at: $timestamp, reviewed: false}' \
    > "$marker_file"

  echo '{"flagged":true,"marker":"'"$marker_file"'"}'
}

# ═══════════════════════════════════════════════════════════════
# Main: evaluate_phase_output()
# ═══════════════════════════════════════════════════════════════
# Orchestrates the 3-tier evaluation pipeline with fail-fast.
#
# Args:
#   $1=output_file       — file to evaluate
#   $2=phase_label       — phase name (e.g., "1_research")
#   $3=log_file          — log file for LLM calls
# Optional named args (via env vars or flags after $3):
#   EVAL_SCHEMA          — schema spec for Tier 1 ("field:type,...")
#   EVAL_MIN_BYTES       — minimum file size for Tier 1
#   EVAL_RUBRICS_DIR     — rubrics directory override
#   EVAL_TASK_DESC       — task description for rubric context
#   EVAL_EXPECTED_FIELDS — expected fields for rubric context
#   EVAL_HUMAN_REVIEW    — "true" to flag for human review
#   EVAL_REVIEW_DIR      — directory for human review markers
#
# Returns: eval-result JSON to stdout
# Exit codes: 0=PASS, 1=RETRY, 2=REMEDIATE, 3=HALT

evaluate_phase_output() {
  local output_file="$1"
  local phase_label="${2:-unknown}"
  local log_file="${3:-/dev/null}"

  local schema="${EVAL_SCHEMA:-}"
  local min_bytes="${EVAL_MIN_BYTES:-50}"
  local rubrics_dir="${EVAL_RUBRICS_DIR:-${EVALUATOR_RUBRICS_DIR:-$EVALUATOR_DEFAULT_RUBRICS_DIR}}"
  local task_desc="${EVAL_TASK_DESC:-Phase: $phase_label}"
  local expected_fields="${EVAL_EXPECTED_FIELDS:-}"
  local human_review="${EVAL_HUMAN_REVIEW:-false}"
  local review_dir="${EVAL_REVIEW_DIR:-${EVALUATOR_REVIEW_DIR:-}}"

  local session_id="eval-$(date +%Y%m%d-%H%M%S)-${phase_label}"
  local timestamp
  timestamp="$(date -Iseconds)"

  echo "  🔍 Evaluator: starting 3-tier evaluation for phase '$phase_label'..." >&2

  # ─── Tier 1: Deterministic ───
  echo "  📐 Tier 1: Deterministic checks..." >&2
  local tier1_result
  tier1_result=$(_evaluate_deterministic "$output_file" "$schema" "$min_bytes")
  local tier1_passed
  tier1_passed=$(echo "$tier1_result" | jq -r '.passed')

  if [[ "$tier1_passed" != "true" ]]; then
    echo "  ❌ Tier 1 FAILED — skipping Tier 2 (fail-fast)" >&2

    # Build result with Tier 2 skipped
    local result
    result=$(jq -n \
      --arg sid "$session_id" \
      --arg phase "$phase_label" \
      --arg ts "$timestamp" \
      --argjson tier1 "$tier1_result" \
      '{
        session_id: $sid,
        phase: $phase,
        timestamp: $ts,
        tiers: {
          deterministic: $tier1,
          llm_rubrics: {passed: false, rubrics: [], overall_score: 0, total_cost: 0, skipped: true, reason: "Tier 1 failed"},
          human_review: {flagged: false}
        },
        verdict: "RETRY",
        signal: "tier1_failed"
      }')

    echo "$result"
    return 1
  fi

  echo "  ✅ Tier 1 passed" >&2

  # ─── Tier 2: LLM Rubrics ───
  echo "  🤖 Tier 2: LLM rubric evaluation..." >&2
  local tier2_result
  tier2_result=$(_evaluate_llm_rubrics "$output_file" "$rubrics_dir" "$log_file" "$task_desc" "$expected_fields")
  local tier2_passed
  tier2_passed=$(echo "$tier2_result" | jq -r '.passed')
  local tier2_score
  tier2_score=$(echo "$tier2_result" | jq -r '.overall_score')
  local tier2_cost
  tier2_cost=$(echo "$tier2_result" | jq -r '.total_cost')

  echo "  📊 Tier 2 score: $tier2_score | cost: \$$tier2_cost" >&2

  # ─── Tier 3: Human Review ───
  local tier3_result='{"flagged":false}'
  if [[ "$human_review" == "true" ]]; then
    echo "  👤 Tier 3: Flagging for human review..." >&2
    tier3_result=$(_flag_human_review "$output_file" "$review_dir" "Evaluator flagged: phase=$phase_label score=$tier2_score")
  fi

  # ─── Determine verdict ───
  local verdict="PASS"
  local signal="null"

  if [[ "$tier2_passed" != "true" ]]; then
    # Check how bad the failure is
    local score_int
    score_int=$(python3 -c "print(int(float('$tier2_score')))" 2>/dev/null || echo 0)

    if [[ "$score_int" -lt 30 ]]; then
      verdict="HALT"
      signal="\"critical_quality_failure\""
      echo "  🛑 Verdict: HALT (score $tier2_score < 30)" >&2
    elif [[ "$score_int" -lt 50 ]]; then
      verdict="REMEDIATE"
      signal="\"low_quality\""
      echo "  ⚠️  Verdict: REMEDIATE (score $tier2_score < 50)" >&2
    else
      verdict="RETRY"
      signal="\"below_threshold\""
      echo "  🔄 Verdict: RETRY (score $tier2_score below threshold)" >&2
    fi
  else
    echo "  ✅ Verdict: PASS" >&2
  fi

  # ─── Build final result ───
  local result
  result=$(jq -n \
    --arg sid "$session_id" \
    --arg phase "$phase_label" \
    --arg ts "$timestamp" \
    --argjson tier1 "$tier1_result" \
    --argjson tier2 "$tier2_result" \
    --argjson tier3 "$tier3_result" \
    --arg verdict "$verdict" \
    --argjson signal "$signal" \
    '{
      session_id: $sid,
      phase: $phase,
      timestamp: $ts,
      tiers: {
        deterministic: $tier1,
        llm_rubrics: $tier2,
        human_review: $tier3
      },
      verdict: $verdict,
      signal: $signal
    }')

  echo "$result"

  # Return exit code based on verdict
  case "$verdict" in
    PASS)      return 0 ;;
    RETRY)     return 1 ;;
    REMEDIATE) return 2 ;;
    HALT)      return 3 ;;
  esac
}

# ═══════════════════════════════════════════════════════════════
# Helper: Check if a phase has evaluator configured
# ═══════════════════════════════════════════════════════════════
# Used by runtime.sh to decide whether to run evaluation.
# A phase has evaluator if EVAL_PHASES contains the phase label.
# Args: $1=phase_label
# Returns: 0 if evaluator should run, 1 otherwise

phase_has_evaluator() {
  local phase="$1"
  local eval_phases="${EVAL_PHASES:-}"

  # If EVAL_PHASES is empty, no evaluation for any phase
  [[ -z "$eval_phases" ]] && return 1

  # Check if "all" is set
  [[ "$eval_phases" == "all" ]] && return 0

  # Check if phase is in comma-separated list
  echo ",$eval_phases," | grep -q ",$phase," 2>/dev/null
}

# ═══════════════════════════════════════════════════════════════
# evaluate_with_threshold — Numeric quality gate with veto power
# ═══════════════════════════════════════════════════════════════
# Story: 115.11 (Quality Gates)
# Design ref: GSD phase-7 quality gates (11 dimensions, threshold + veto)
#
# Args:
#   $1=dimension_name  — name of the quality dimension (e.g., "completeness")
#   $2=score           — numeric score (integer or float, 0-100)
#   $3=threshold       — minimum acceptable score (integer or float, 0-100)
#   $4=veto_power      — "true" or "false"
#
# Returns to stdout: "PASS" | "WARNING" | "VETO"
# Exit codes: 0=PASS, 1=WARNING, 2=VETO
#
# Boundary rule: score == threshold → PASS (not WARNING)
# Veto rule: score < threshold AND veto_power=true → VETO (blocks advance)
# Warning rule: score < threshold AND veto_power=false → WARNING (log + continue)

evaluate_with_threshold() {
  local dimension_name="${1:-unknown}"
  local score="${2:-0}"
  local threshold="${3:-0}"
  local veto_power="${4:-false}"

  # Normalize: compare as integers scaled by 100 to handle floats
  # e.g., 72.5 → 7250, 70 → 7000
  local score_scaled threshold_scaled
  score_scaled=$(awk "BEGIN{printf \"%d\", $score * 100}" 2>/dev/null || echo 0)
  threshold_scaled=$(awk "BEGIN{printf \"%d\", $threshold * 100}" 2>/dev/null || echo 0)

  if [[ "$score_scaled" -ge "$threshold_scaled" ]]; then
    echo "PASS"
    return 0
  fi

  # Score is below threshold
  if [[ "$veto_power" == "true" ]]; then
    echo "  [VETO] Quality gate '$dimension_name': score $score < threshold $threshold (veto_power=true)" >&2
    echo "VETO"
    return 2
  else
    echo "  [WARNING] Quality gate '$dimension_name': score $score < threshold $threshold (advisory)" >&2
    echo "WARNING"
    return 1
  fi
}
