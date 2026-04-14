#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR-LIB: reporting.sh — Standardized validation log + score card
# ═══════════════════════════════════════════════════════════════════════════════
# Shared between validate-skill.sh, validate-squad.sh, sinkra-map.sh
# Source: infrastructure/scripts/validator-lib/reporting.sh
#
# Standard artifacts:
#   validation.log  — human-readable text log (append-friendly)
#   score_card.yaml — machine-readable YAML (overwrite per run)

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION LOG — Standardized text format
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   emit_validation_log <output_dir> \
#     --target "roundtable" \
#     --type "skill" \
#     --score "10.0" \
#     --verdict "PASS" \
#     --process "SP-VALIDATE-SKILL" \
#     --script "validate-skill.sh v2.0.0" \
#     --checks "8 PASS, 0 FAIL, 2 WARN, 0 SKIP" \
#     --dims "D1:10.0:PASS D2:10.0:PASS" \
#     --blockers "issue1" "issue2" \
#     --extras "key1=val1" "key2=val2"

emit_validation_log() {
  local output_dir="$1"; shift

  local target="" type="" score="" verdict="" process="" script_id=""
  local checks="" extras=()
  local dims=()
  local blockers=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --target)   target="$2"; shift 2 ;;
      --type)     type="$2"; shift 2 ;;
      --score)    score="$2"; shift 2 ;;
      --verdict)  verdict="$2"; shift 2 ;;
      --process)  process="$2"; shift 2 ;;
      --script)   script_id="$2"; shift 2 ;;
      --checks)   checks="$2"; shift 2 ;;
      --dims)     dims+=($2); shift 2 ;;
      --blockers) shift; while [[ $# -gt 0 && "$1" != --* ]]; do blockers+=("$1"); shift; done ;;
      --extras)   shift; while [[ $# -gt 0 && "$1" != --* ]]; do extras+=("$1"); shift; done ;;
      *) shift ;;
    esac
  done

  mkdir -p "$output_dir"
  local log_file="$output_dir/validation.log"
  local timestamp
  timestamp=$(date +%Y-%m-%dT%H:%M:%S)
  local date_str
  date_str=$(date +%Y-%m-%d)

  {
    echo "═══════════════════════════════════════════"
    echo "VALIDATION LOG"
    echo "═══════════════════════════════════════════"
    echo "Timestamp: $timestamp"
    echo "Target: $target"
    echo "Type: ${type:-unknown}"
    echo "Score: ${score}/10"
    echo "Verdict: $verdict"
    [[ -n "$checks" ]] && echo "Checks: $checks"
    echo ""

    if [[ ${#dims[@]} -gt 0 ]]; then
      echo "Dimensions:"
      for dim_entry in "${dims[@]}"; do
        # Format: "D1:10.0:PASS" or space-separated list
        for d in $dim_entry; do
          local dim_name="${d%%:*}"
          local rest="${d#*:}"
          local dim_score="${rest%%:*}"
          local dim_status="${rest##*:}"
          echo "  $dim_name: $dim_score/10 ($dim_status)"
        done
      done
      echo ""
    fi

    if [[ ${#blockers[@]} -gt 0 ]]; then
      echo "Blocking Issues:"
      for b in "${blockers[@]}"; do
        echo "  - $b"
      done
      echo ""
    fi

    if [[ ${#extras[@]} -gt 0 ]]; then
      for e in "${extras[@]}"; do
        local key="${e%%=*}"
        local val="${e#*=}"
        echo "$key: $val"
      done
      echo ""
    fi

    echo "Process: ${process:-unknown}"
    echo "Script: ${script_id:-unknown}"
    echo "═══════════════════════════════════════════"
  } > "$log_file"
}

# ═══════════════════════════════════════════════════════════════════════════════
# SCORE CARD — Standardized YAML format
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   emit_score_card_yaml <output_dir> \
#     --target "roundtable" \
#     --type "skill" \
#     --score "10.0" \
#     --verdict "PASS" \
#     --process "SP-VALIDATE-SKILL" \
#     --checks "pass:8 fail:0 warn:2 skip:0" \
#     --dims "D1:10.0:PASS:2.0 D2:5.0:WARN:1.0" \
#     --cap "none" \
#     --previous "9.5" \
#     --blockers "issue1" "issue2" \
#     --guardrails "reason1" "reason2"

emit_score_card_yaml() {
  local output_dir="$1"; shift

  local target="" type="" score="" verdict="" process=""
  local checks="" cap="none" previous=""
  local dims=()
  local blockers=()
  local guardrails=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --target)     target="$2"; shift 2 ;;
      --type)       type="$2"; shift 2 ;;
      --score)      score="$2"; shift 2 ;;
      --verdict)    verdict="$2"; shift 2 ;;
      --process)    process="$2"; shift 2 ;;
      --checks)     checks="$2"; shift 2 ;;
      --dims)       dims+=($2); shift 2 ;;
      --cap)        cap="$2"; shift 2 ;;
      --previous)   previous="$2"; shift 2 ;;
      --blockers)   shift; while [[ $# -gt 0 && "$1" != --* ]]; do blockers+=("$1"); shift; done ;;
      --guardrails) shift; while [[ $# -gt 0 && "$1" != --* ]]; do guardrails+=("$1"); shift; done ;;
      *) shift ;;
    esac
  done

  mkdir -p "$output_dir"
  local date_str
  date_str=$(date +%Y-%m-%d)

  {
    echo "# validation score card"
    echo "# Generated: $date_str"
    echo ""
    echo "validation:"
    echo "  target: $target"
    echo "  type: ${type:-unknown}"
    echo "  date: \"$date_str\""
    echo "  process: ${process:-unknown}"
    echo ""

    # Parse checks string "pass:8 fail:0 warn:2 skip:0"
    if [[ -n "$checks" ]]; then
      echo "checks:"
      for pair in $checks; do
        local k="${pair%%:*}"
        local v="${pair#*:}"
        echo "  $k: $v"
      done
      echo ""
    fi

    if [[ ${#dims[@]} -gt 0 ]]; then
      echo "dimensions:"
      for dim_entry in "${dims[@]}"; do
        for d in $dim_entry; do
          local dim_name="${d%%:*}"
          local rest="${d#*:}"
          local dim_score="${rest%%:*}"
          rest="${rest#*:}"
          local dim_status="${rest%%:*}"
          local dim_weight="${rest#*:}"
          [[ "$dim_weight" == "$dim_status" ]] && dim_weight=""
          if [[ -n "$dim_weight" ]]; then
            echo "  $dim_name: { score: $dim_score, status: $dim_status, weight: $dim_weight }"
          else
            echo "  $dim_name: { score: $dim_score, status: $dim_status }"
          fi
        done
      done
      echo ""
    fi

    echo "scores:"
    echo "  weighted: $score"
    echo "  final: $score"
    echo "  verdict: $verdict"
    echo "  cap: $cap"
    [[ -n "$previous" ]] && echo "  previous: $previous"
    echo ""

    echo "blocking_issues:"
    if [[ ${#blockers[@]} -gt 0 ]]; then
      for b in "${blockers[@]}"; do
        echo "  - \"$b\""
      done
    else
      echo "  []"
    fi
    echo ""

    echo "guardrails:"
    if [[ ${#guardrails[@]} -gt 0 ]]; then
      for g in "${guardrails[@]}"; do
        echo "  - \"$g\""
      done
    else
      echo "  []"
    fi
  } > "$output_dir/score_card.yaml"
}

VALIDATOR_LIB_REPORTING=true
