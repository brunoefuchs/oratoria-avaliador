#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# BOOTSTRAP-RUNNER — Template for creating new squad runners
# ═══════════════════════════════════════════════════════════════
#
# This is NOT a generator script. It IS the template.
# Copy this file to your squad's scripts/ directory and customize.
#
# What you get for free by sourcing runner-lib:
#   - Multi-runtime (Claude/Codex/Gemini) with --claude/--codex/--gemini flags
#   - Fallback chain (primary fails → try alternatives automatically)
#   - Cost tracking (metrics.jsonl + show_cost_summary)
#   - Token estimation + LLM pricing
#   - Timeout + retry with exponential backoff
#   - Circuit breaker (N consecutive failures → abort)
#   - Fatal billing limit detection (exit 99)
#   - JSON output mode (--output-format json for Claude)
#   - --max-turns per phase (Claude only)
#   - --allowedTools per phase (Claude only)
#   - Generic assertions (YAML valid, keys exist, file size, markdown valid)
#
# Usage: cp bootstrap-runner.sh squads/{your-squad}/scripts/{your-runner}.sh
#        Then edit the CUSTOMIZE sections below.
#
# Pattern: Same as sinkra-map.sh, sinkra-validate.sh, validate-squad.sh

set -e

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQUAD_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SQUAD_DIR/../.." && pwd)"

# ─── CUSTOMIZE: Your squad identity ───────────────────────────
SQUAD_NAME="$(basename "$SQUAD_DIR")"
RUNNER_NAME="$(basename "$0" .sh)"
RUNNER_VERSION="1.0.0"
# ──────────────────────────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════
# LOAD SHARED INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════

RUNNER_LIB_DIR="$REPO_ROOT/infrastructure/scripts/runner-lib"
if [[ -f "$RUNNER_LIB_DIR/loader.sh" ]]; then
  source "$RUNNER_LIB_DIR/loader.sh"
else
  echo "❌ runner-lib not found at $RUNNER_LIB_DIR"
  echo "   Expected: infrastructure/scripts/runner-lib/loader.sh"
  exit 1
fi

# Pre-flight: verify dependencies before any LLM calls
# ─── CUSTOMIZE: Add squad-specific bins/env vars ─────────────
REQUIRED_BINS="jq,python3"
REQUIRED_ENV=""
# ──────────────────────────────────────────────────────────────
if declare -f preflight_check >/dev/null 2>&1; then
  preflight_check "$REQUIRED_BINS" "$REQUIRED_ENV" || exit 1
fi

# ═══════════════════════════════════════════════════════════════
# ARGUMENT PARSING
# ═══════════════════════════════════════════════════════════════

REQUESTED_RUNTIME="${SINKRA_LLM_RUNTIME:-auto}"
MODEL=""
DRY_RUN="false"
MAX_ITERATIONS=5
POSITIONAL_ARGS=()

show_help() {
  echo "🔄 $RUNNER_NAME v$RUNNER_VERSION ($SQUAD_NAME)"
  echo ""
  echo "Usage: $0 [flags] <target>"
  echo ""
  echo "Runtime flags:"
  echo "  --claude           Use Claude (default)"
  echo "  --codex            Use Codex"
  echo "  --gemini           Use Gemini"
  echo "  --model <name>     Override model"
  echo "  --timeout <secs>   LLM timeout (default: per runtime)"
  echo ""
  echo "Pipeline flags:"
  echo "  --dry-run          Show plan without running"
  echo "  --phase <N>        Start from specific phase"
  echo "  --max-iters <N>    Max iterations per phase (default: 5)"
  echo "  --max-cost <USD>   Cost cap per run (e.g., 2.00). Stops before next phase if exceeded"
  echo ""
  # ─── CUSTOMIZE: Add your specific flags ─────────────────────
  echo "Squad-specific flags:"
  echo "  (add your flags here)"
  # ────────────────────────────────────────────────────────────
  exit 0
}

LLM_TIMEOUT_SECONDS=""
RETRY_MAX_ATTEMPTS=""
RETRY_BASE_DELAY_SECONDS=3
START_PHASE=""
MAX_COST=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)       show_help ;;
    --claude)        REQUESTED_RUNTIME="claude"; shift ;;
    --codex)         REQUESTED_RUNTIME="codex"; shift ;;
    --gemini)        REQUESTED_RUNTIME="gemini"; shift ;;
    --model)         MODEL="$2"; shift 2 ;;
    --timeout)       LLM_TIMEOUT_SECONDS="$2"; shift 2 ;;
    --dry-run)       DRY_RUN="true"; shift ;;
    --phase)         START_PHASE="$2"; shift 2 ;;
    --max-iters)     MAX_ITERATIONS="$2"; shift 2 ;;
    --max-cost)      MAX_COST="$2"; shift 2 ;;
    # ─── CUSTOMIZE: Add your specific flag handlers ───────────
    # --your-flag)   YOUR_VAR="$2"; shift 2 ;;
    # ──────────────────────────────────────────────────────────
    -*)              echo "❌ Unknown flag: $1"; exit 1 ;;
    *)               POSITIONAL_ARGS+=("$1"); shift ;;
  esac
done

# ═══════════════════════════════════════════════════════════════
# RESOLVE RUNTIME
# ═══════════════════════════════════════════════════════════════

SELECTED_RUNTIME="$(detect_runtime "$REQUESTED_RUNTIME")"
if [[ "$SELECTED_RUNTIME" == "none" || "$SELECTED_RUNTIME" == "invalid" ]]; then
  echo "❌ No supported runtime found (claude, codex, or gemini)"
  exit 1
fi
validate_runtime "$SELECTED_RUNTIME"

# Per-runtime defaults
case "$SELECTED_RUNTIME" in
  claude) MODEL="${MODEL:-$(get_quality_model "$SELECTED_RUNTIME")}"; RETRY_MAX_ATTEMPTS="${RETRY_MAX_ATTEMPTS:-2}"; LLM_TIMEOUT_SECONDS="${LLM_TIMEOUT_SECONDS:-3600}" ;;
  codex)  MODEL="${MODEL:-$(get_quality_model "$SELECTED_RUNTIME")}"; RETRY_MAX_ATTEMPTS="${RETRY_MAX_ATTEMPTS:-3}"; LLM_TIMEOUT_SECONDS="${LLM_TIMEOUT_SECONDS:-5400}" ;;
  gemini) MODEL="${MODEL:-$(get_quality_model "$SELECTED_RUNTIME")}"; RETRY_MAX_ATTEMPTS="${RETRY_MAX_ATTEMPTS:-2}"; LLM_TIMEOUT_SECONDS="${LLM_TIMEOUT_SECONDS:-3600}" ;;
esac
export SELECTED_RUNTIME MODEL LLM_TIMEOUT_SECONDS RETRY_MAX_ATTEMPTS RETRY_BASE_DELAY_SECONDS

# ═══════════════════════════════════════════════════════════════
# SETUP OUTPUT (versioned runs)
# ═══════════════════════════════════════════════════════════════

TARGET="${POSITIONAL_ARGS[0]:-default}"
RUN_TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
RUN_ID="${RUN_TIMESTAMP}-${SELECTED_RUNTIME}-${MODEL}"
OUTPUT_DIR="$REPO_ROOT/outputs/$SQUAD_NAME/$TARGET/$RUNNER_NAME/$RUN_ID"
LOG_DIR="$OUTPUT_DIR/logs"
METRICS_FILE="$OUTPUT_DIR/metrics.jsonl"

mkdir -p "$OUTPUT_DIR" "$LOG_DIR"
ln -sfn "$RUN_ID" "$(dirname "$OUTPUT_DIR")/latest"

# ═══════════════════════════════════════════════════════════════
# SHOW STATUS
# ═══════════════════════════════════════════════════════════════

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        🔄 $RUNNER_NAME v$RUNNER_VERSION"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║                                                              ║"
echo "║  Squad:     $SQUAD_NAME"
echo "║  Target:    $TARGET"
echo "║  Runtime:   $SELECTED_RUNTIME"
echo "║  Model:     $MODEL"
echo "║  Output:    $OUTPUT_DIR"
echo "║                                                              ║"
# ─── CUSTOMIZE: Add your execution plan ───────────────────────
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Execution Plan:                                             ║"
echo "║  ┌─────────────────────────────────────────────────────────┐ ║"
echo "║  │ Phase 1: (your first phase)                             │ ║"
echo "║  │    ↓                                                    │ ║"
echo "║  │ Phase 2: (your second phase)                            │ ║"
echo "║  └─────────────────────────────────────────────────────────┘ ║"
# ──────────────────────────────────────────────────────────────
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

if [[ "$DRY_RUN" == "true" ]]; then
  echo "🔍 DRY RUN — would execute pipeline for: $TARGET"
  exit 0
fi

# ═══════════════════════════════════════════════════════════════
# PIPELINE EXECUTION
# ═══════════════════════════════════════════════════════════════

PIPELINE_LOG="$LOG_DIR/pipeline-$(date +%Y%m%d).log"
PIPELINE_START=$(date +%s)

echo "🚀 Started at $(date +%H:%M:%S)" | tee -a "$PIPELINE_LOG"

# ─── CUSTOMIZE: Your pipeline phases ──────────────────────────
#
# For each phase, use this pattern:
#
#   echo ""
#   echo "╔══════════════════════════════════════════════════════════════╗"
#   echo "║  📌 PHASE 1/N: Phase Name — $(date +%H:%M:%S)"
#   echo "╚══════════════════════════════════════════════════════════════╝"
#
#   # Option A: Run LLM call
#   PHASE_MAX_TURNS="5"        # optional: limit turns
#   PHASE_ALLOWED_TOOLS=""     # optional: restrict tools
#   prompt="Your prompt here..."
#   prompt_file=$(mktemp)
#   printf '%s' "$prompt" > "$prompt_file"
#   output=$(run_llm_prompt "$MODEL" "$(cat "$prompt_file")" "$PIPELINE_LOG" "phase1") || exit_code=$?
#   rm -f "$prompt_file"
#
#   # Option B: Run deterministic script
#   python3 "$SQUAD_DIR/scripts/your-check.py" "$TARGET" --output json
#
#   # Option C: Run assertion
#   assert_yaml_valid "$OUTPUT_DIR/result.yaml"
#   assert_yaml_schema "$OUTPUT_DIR/result.yaml" "$SCHEMA_SCORE_CARD"
#
#   # Cost cap check (between phases — stops before next phase if exceeded)
#   check_cost_cap "${MAX_COST:-}" || { echo "💾 Saving state..."; exit 75; }
#
# ──────────────────────────────────────────────────────────────

echo "⚠️  No phases defined yet. Edit the CUSTOMIZE sections in this script."

# ═══════════════════════════════════════════════════════════════
# COMPLETION
# ═══════════════════════════════════════════════════════════════

PIPELINE_END=$(date +%s)
TOTAL_DURATION=$((PIPELINE_END - PIPELINE_START))
TOTAL_MINUTES=$((TOTAL_DURATION / 60))
TOTAL_SECONDS=$((TOTAL_DURATION % 60))

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║        ✅ $RUNNER_NAME COMPLETE                               ║"
echo "║                                                              ║"
echo "║  Target:    $TARGET"
echo "║  Duration:  ${TOTAL_MINUTES}m ${TOTAL_SECONDS}s"
echo "║  Output:    $OUTPUT_DIR"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# Cost summary (from metrics.sh)
show_cost_summary
