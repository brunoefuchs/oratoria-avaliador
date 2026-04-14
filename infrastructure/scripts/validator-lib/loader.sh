#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR-LIB: loader.sh — Entry point for shared validation modules
# ═══════════════════════════════════════════════════════════════════════════════
# Usage:
#   source "$WORKSPACE_ROOT/infrastructure/scripts/validator-lib/loader.sh"
#
# After sourcing, check availability flags:
#   VALIDATOR_LIB_COLORS    — colors.sh loaded (ANSI codes, log helpers, box drawing)
#   VALIDATOR_LIB_SCORING   — scoring.sh loaded (dimensional scoring, guardrails)
#   VALIDATOR_LIB_SECURITY  — security.sh loaded (grep-based security scanner)
#   VALIDATOR_LIB_REPORTING — reporting.sh loaded (validation.log + score_card.yaml)

_VLIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Initialize flags
VALIDATOR_LIB_COLORS=false
VALIDATOR_LIB_SCORING=false
VALIDATOR_LIB_SECURITY=false
VALIDATOR_LIB_REPORTING=false

# Load modules (each sets its own flag to true on success)
[[ -f "$_VLIB_DIR/colors.sh" ]]    && source "$_VLIB_DIR/colors.sh"
[[ -f "$_VLIB_DIR/scoring.sh" ]]   && source "$_VLIB_DIR/scoring.sh"
[[ -f "$_VLIB_DIR/security.sh" ]]  && source "$_VLIB_DIR/security.sh"
[[ -f "$_VLIB_DIR/reporting.sh" ]] && source "$_VLIB_DIR/reporting.sh"
