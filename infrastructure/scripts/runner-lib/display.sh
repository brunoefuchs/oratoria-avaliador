#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER-LIB: display.sh — Unicode box drawing for pipeline display
# ═══════════════════════════════════════════════════════════════════════════════
# Standardized 62-char wide boxes used by all autonomous runners.
# Used by: sinkra-map.sh, mmos.sh, copy.sh, books.sh, ralph-7d.sh, swipe.sh

# Phase header — displayed before each pipeline phase.
# Usage: display_phase_header <phase_num> <label> [agent_name] [emoji]
display_phase_header() {
  local phase_num="$1"
  local label="$2"
  local agent="${3:-}"
  local emoji="${4:-📌}"

  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  if [[ -n "$agent" ]]; then
    printf "║  %s PHASE %s: %s (@%s)\n" "$emoji" "$phase_num" "$label" "$agent"
  else
    printf "║  %s PHASE %s: %s\n" "$emoji" "$phase_num" "$label"
  fi
  echo "╚══════════════════════════════════════════════════════════════╝"
}

# Pipeline status banner — displayed at pipeline start.
# Usage: display_pipeline_banner <title> <kv_pairs...>
# Example: display_pipeline_banner "SINKRA Pipeline" "Process:Casting" "Mode:greenfield" "Runtime:claude"
display_pipeline_banner() {
  local title="$1"; shift

  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  printf "║        %s\n" "$title"
  echo "╠══════════════════════════════════════════════════════════════╣"
  echo "║                                                              ║"

  for kv in "$@"; do
    local key="${kv%%:*}"
    local val="${kv#*:}"
    printf "║  %-12s %s\n" "$key:" "$val"
  done

  echo "║                                                              ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo ""
}

# Completion banner — displayed when pipeline finishes.
# Usage: display_completion <title> <kv_pairs...>
display_completion() {
  local title="$1"; shift

  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║                                                              ║"
  printf "║        🎉 %s\n" "$title"
  echo "║                                                              ║"

  for kv in "$@"; do
    local key="${kv%%:*}"
    local val="${kv#*:}"
    printf "║  %-12s %s\n" "$key:" "$val"
  done

  echo "║                                                              ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
}

# Section separator — lighter than phase header.
# Usage: display_section <title>
display_section() {
  local title="$1"
  echo ""
  echo "═══ $title ═══"
}

RUNNER_LIB_DISPLAY=true
