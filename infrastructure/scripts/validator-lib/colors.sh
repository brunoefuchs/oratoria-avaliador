#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR-LIB: colors.sh — ANSI colors + terminal formatting helpers
# ═══════════════════════════════════════════════════════════════════════════════
# Shared between validate-skill.sh, validate-squad.sh, sinkra-map.sh
# Source: infrastructure/scripts/validator-lib/colors.sh

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Log helpers — require VERBOSE variable from consumer
# Usage: vlog_pass "CHECK_ID" "message"

vlog_pass() {
  local check="$1" msg="$2"
  if [[ "${VERBOSE:-false}" == true ]]; then
    printf "  ${GREEN}PASS${NC} %-8s %s\n" "$check" "$msg"
  fi
}

vlog_fail() {
  local check="$1" msg="$2"
  if [[ "${VERBOSE:-false}" == true ]]; then
    printf "  ${RED}FAIL${NC} %-8s %s\n" "$check" "$msg"
  fi
}

vlog_warn() {
  local check="$1" msg="$2"
  if [[ "${VERBOSE:-false}" == true ]]; then
    printf "  ${YELLOW}WARN${NC} %-8s %s\n" "$check" "$msg"
  fi
}

vlog_skip() {
  local check="$1" msg="$2"
  if [[ "${VERBOSE:-false}" == true ]]; then
    printf "  ${CYAN}SKIP${NC} %-8s %s\n" "$check" "$msg"
  fi
}

vlog_score() {
  local dim="$1" score="$2" weight="$3"
  if [[ "${VERBOSE:-false}" == true ]]; then
    printf "  ${BLUE}SCORE${NC} %-8s %s/10 (weight: %.1f)\n" "$dim" "$score" "$weight"
  fi
}

# Box drawing helpers
box_header() {
  local title="$1"
  printf "\n${BOLD}${CYAN}"
  printf "  ╔═══════════════════════════════════════════╗\n"
  printf "  ║  %-41s ║\n" "$title"
  printf "  ╚═══════════════════════════════════════════╝${NC}\n"
}

box_section() {
  local title="$1"
  printf "\n  ${BOLD}┌─── %s ───${NC}\n" "$title"
}

# Dimensional score table
# Usage: emit_dim_table "D1:10.0:PASS" "D2:5.0:WARN" ...
emit_dim_table() {
  if [[ $# -eq 0 ]]; then return; fi
  printf "\n  ${BOLD}┌──────────┬────────┬────────┐${NC}\n"
  printf "  ${BOLD}│ Dimension│ Score  │ Status │${NC}\n"
  printf "  ${BOLD}├──────────┼────────┼────────┤${NC}\n"
  for entry in "$@"; do
    local dim="${entry%%:*}"
    local rest="${entry#*:}"
    local score="${rest%%:*}"
    local status="${rest##*:}"
    local color="$GREEN"
    [[ "$status" == "WARN" ]] && color="$YELLOW"
    [[ "$status" == "FAIL" ]] && color="$RED"
    printf "  │ %-8s │ %s/10 │ ${color}%-6s${NC} │\n" "$dim" "$score" "$status"
  done
  printf "  ${BOLD}└──────────┴────────┴────────┘${NC}\n"
}

VALIDATOR_LIB_COLORS=true
