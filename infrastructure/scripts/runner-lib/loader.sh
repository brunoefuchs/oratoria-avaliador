#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER-LIB LOADER — Shared infrastructure for all LLM runners
# ═══════════════════════════════════════════════════════════════
#
# Source this file from any bash runner script to get:
#   - runtime.sh:  Multi-runtime LLM execution (Claude/Codex/Gemini)
#   - metrics.sh:  Cost tracking, token estimation, JSONL recording
#   - context-engine.sh: Error dedup, context management
#
# Usage:
#   RUNNER_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../infrastructure/scripts/runner-lib" && pwd)"
#   source "$RUNNER_LIB_DIR/loader.sh"
#
# Or shorter, from repo root:
#   source "$(git rev-parse --show-toplevel)/infrastructure/scripts/runner-lib/loader.sh"
#
# What gets loaded:
#   - runtime.sh:  _exec_runtime(), run_llm_prompt(), detect_runtime(),
#                  validate_runtime(), is_fatal_error(), fallback chain
#   - metrics.sh:  record_metrics(), show_cost_summary(), calculate_cost(),
#                  get_pricing(), bytes_to_tokens(), check_cost_cap()
#   - context-engine.sh: error dedup, context budget management
#   - assertions.sh: assert_yaml_valid(), assert_yaml_schema(), assert_yaml_has_keys()
#   - preflight.sh: preflight_check() — verify bins/env before run
#   - state-manager.sh: state_init(), state_update(), state_get(), state_phase_update()
#   - progress-logger.sh: progress_init(), progress_phase_start/complete(), progress_checkpoint()
#   - display.sh: display_phase_header(), display_pipeline_banner(), display_completion()
#   - arg-parser.sh: parse_common_args(), parse_extra_flags()
#   - python-resolver.sh: resolve_python(), require_python()
#   - memory.sh:    record_run(), get_best_model_for_phase(), warn_recurring_failures()
#   - json-validator.sh: json_extract(), json_validate(), json_get(), json_has_fields()
#
# All libs are safe to source multiple times (idempotent).

RUNNER_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Canonical model catalog (required)
if [[ -f "$RUNNER_LIB_DIR/models.sh" ]]; then
  source "$RUNNER_LIB_DIR/models.sh"
  RUNNER_LIB_MODELS="true"
else
  echo "⚠️  runner-lib: models.sh not found at $RUNNER_LIB_DIR" >&2
  RUNNER_LIB_MODELS="false"
fi

# Core: LLM runtime execution (required)
if [[ -f "$RUNNER_LIB_DIR/runtime.sh" ]]; then
  source "$RUNNER_LIB_DIR/runtime.sh"
  RUNNER_LIB_RUNTIME="true"
else
  echo "⚠️  runner-lib: runtime.sh not found at $RUNNER_LIB_DIR" >&2
  RUNNER_LIB_RUNTIME="false"
fi

# Cost tracking (required)
if [[ -f "$RUNNER_LIB_DIR/metrics.sh" ]]; then
  source "$RUNNER_LIB_DIR/metrics.sh"
  RUNNER_LIB_METRICS="true"
else
  RUNNER_LIB_METRICS="false"
fi

# Context engine (optional)
if [[ -f "$RUNNER_LIB_DIR/context-engine.sh" ]]; then
  source "$RUNNER_LIB_DIR/context-engine.sh"
  RUNNER_LIB_CONTEXT="true"
else
  RUNNER_LIB_CONTEXT="false"
fi

# Generic assertions (optional)
if [[ -f "$RUNNER_LIB_DIR/assertions.sh" ]]; then
  source "$RUNNER_LIB_DIR/assertions.sh"
  RUNNER_LIB_ASSERTIONS="true"
else
  RUNNER_LIB_ASSERTIONS="false"
fi

# Pre-flight dependency check (optional)
if [[ -f "$RUNNER_LIB_DIR/preflight.sh" ]]; then
  source "$RUNNER_LIB_DIR/preflight.sh"
  RUNNER_LIB_PREFLIGHT="true"
else
  RUNNER_LIB_PREFLIGHT="false"
fi

# Pipeline state management (optional, v2)
if [[ -f "$RUNNER_LIB_DIR/state-manager.sh" ]]; then
  source "$RUNNER_LIB_DIR/state-manager.sh"
  RUNNER_LIB_STATE_MANAGER="true"
else
  RUNNER_LIB_STATE_MANAGER="false"
fi

# Progress logging (optional, v2)
if [[ -f "$RUNNER_LIB_DIR/progress-logger.sh" ]]; then
  source "$RUNNER_LIB_DIR/progress-logger.sh"
  RUNNER_LIB_PROGRESS_LOGGER="true"
else
  RUNNER_LIB_PROGRESS_LOGGER="false"
fi

# Terminal display helpers (optional, v2)
if [[ -f "$RUNNER_LIB_DIR/display.sh" ]]; then
  source "$RUNNER_LIB_DIR/display.sh"
  RUNNER_LIB_DISPLAY="true"
else
  RUNNER_LIB_DISPLAY="false"
fi

# Common argument parser (optional, v2)
if [[ -f "$RUNNER_LIB_DIR/arg-parser.sh" ]]; then
  source "$RUNNER_LIB_DIR/arg-parser.sh"
  RUNNER_LIB_ARG_PARSER="true"
else
  RUNNER_LIB_ARG_PARSER="false"
fi

# Python resolver with PyYAML probe (optional, v2)
if [[ -f "$RUNNER_LIB_DIR/python-resolver.sh" ]]; then
  source "$RUNNER_LIB_DIR/python-resolver.sh"
  RUNNER_LIB_PYTHON_RESOLVER="true"
else
  RUNNER_LIB_PYTHON_RESOLVER="false"
fi

# JSON extraction + validation helpers (optional, v2)
if [[ -f "$RUNNER_LIB_DIR/json-validator.sh" ]]; then
  source "$RUNNER_LIB_DIR/json-validator.sh"
  RUNNER_LIB_JSON_VALIDATOR="true"
else
  RUNNER_LIB_JSON_VALIDATOR="false"
fi

# Cross-run memory (optional)
if [[ -f "$RUNNER_LIB_DIR/memory.sh" ]]; then
  source "$RUNNER_LIB_DIR/memory.sh"
  RUNNER_LIB_MEMORY="true"
else
  RUNNER_LIB_MEMORY="false"
fi

# Session manager (optional)
if [[ -f "$RUNNER_LIB_DIR/session-mgr.sh" ]]; then
  source "$RUNNER_LIB_DIR/session-mgr.sh"
  RUNNER_LIB_SESSION="true"
else
  RUNNER_LIB_SESSION="false"
fi

# Cross-squad dispatch (optional) — Story: RUNNER-4.1
if [[ -f "$RUNNER_LIB_DIR/dispatch.sh" ]]; then
  source "$RUNNER_LIB_DIR/dispatch.sh"
  RUNNER_LIB_DISPATCH="true"
else
  RUNNER_LIB_DISPATCH="false"
fi

# Worktree isolation (optional) — Story: RUNNER-4.1
if [[ -f "$RUNNER_LIB_DIR/worktree.sh" ]]; then
  source "$RUNNER_LIB_DIR/worktree.sh"
  RUNNER_LIB_WORKTREE="true"
else
  RUNNER_LIB_WORKTREE="false"
fi

# Cascade model routing (optional) — Story: RUNNER-3.3
if [[ -f "$RUNNER_LIB_DIR/cascade.sh" ]]; then
  source "$RUNNER_LIB_DIR/cascade.sh"
  RUNNER_LIB_CASCADE="true"
else
  RUNNER_LIB_CASCADE="false"
fi

# Replan-on-failure (optional) — Story: RUNNER-3.3
if [[ -f "$RUNNER_LIB_DIR/replan.sh" ]]; then
  source "$RUNNER_LIB_DIR/replan.sh"
  RUNNER_LIB_REPLAN="true"
else
  RUNNER_LIB_REPLAN="false"
fi

# Context compression (optional) — Story: RUNNER-2.3
if [[ -f "$RUNNER_LIB_DIR/compress.sh" ]]; then
  source "$RUNNER_LIB_DIR/compress.sh"
  RUNNER_LIB_COMPRESS="true"
else
  RUNNER_LIB_COMPRESS="false"
fi

# Declarative hook system (optional) — Story: RUNNER-2.2
if [[ -f "$RUNNER_LIB_DIR/hooks.sh" ]]; then
  source "$RUNNER_LIB_DIR/hooks.sh"
  RUNNER_LIB_HOOKS="true"
else
  RUNNER_LIB_HOOKS="false"
fi

# 3-Tier evaluator (optional) — Story: RUNNER-2.1
if [[ -f "$RUNNER_LIB_DIR/evaluator.sh" ]]; then
  source "$RUNNER_LIB_DIR/evaluator.sh"
  RUNNER_LIB_EVALUATOR="true"
else
  RUNNER_LIB_EVALUATOR="false"
fi

# Headless guard for safe LLM execution (optional) — Story: EPIC-101.1
if [[ -f "$RUNNER_LIB_DIR/headless-guard.sh" ]]; then
  source "$RUNNER_LIB_DIR/headless-guard.sh"
  RUNNER_LIB_HEADLESS_GUARD="true"
else
  RUNNER_LIB_HEADLESS_GUARD="false"
fi

# Git context injection (optional) — Story: STORY-118.1
if [[ -f "$RUNNER_LIB_DIR/git-context.sh" ]]; then
  source "$RUNNER_LIB_DIR/git-context.sh"
  RUNNER_LIB_GIT_CONTEXT="true"
else
  RUNNER_LIB_GIT_CONTEXT="false"
fi

# Execution evidence audit trail (optional) — Story: STORY-115.12
if [[ -f "$RUNNER_LIB_DIR/evidence.sh" ]]; then
  source "$RUNNER_LIB_DIR/evidence.sh"
  RUNNER_LIB_EVIDENCE="true"
else
  RUNNER_LIB_EVIDENCE="false"
fi

# Markdown companion generation (optional) — Story: STORY-118.4
if [[ -f "$RUNNER_LIB_DIR/markdown-companion.sh" ]]; then
  source "$RUNNER_LIB_DIR/markdown-companion.sh"
  RUNNER_LIB_MARKDOWN_COMPANION="true"
else
  RUNNER_LIB_MARKDOWN_COMPANION="false"
fi

# Export availability flags for consumer scripts
export RUNNER_LIB_MODELS RUNNER_LIB_RUNTIME RUNNER_LIB_METRICS RUNNER_LIB_CONTEXT RUNNER_LIB_ASSERTIONS RUNNER_LIB_PREFLIGHT RUNNER_LIB_STATE_MANAGER RUNNER_LIB_PROGRESS_LOGGER RUNNER_LIB_DISPLAY RUNNER_LIB_ARG_PARSER RUNNER_LIB_PYTHON_RESOLVER RUNNER_LIB_MEMORY RUNNER_LIB_SESSION RUNNER_LIB_DISPATCH RUNNER_LIB_WORKTREE RUNNER_LIB_CASCADE RUNNER_LIB_REPLAN RUNNER_LIB_COMPRESS RUNNER_LIB_HOOKS RUNNER_LIB_EVALUATOR RUNNER_LIB_HEADLESS_GUARD RUNNER_LIB_GIT_CONTEXT RUNNER_LIB_EVIDENCE RUNNER_LIB_MARKDOWN_COMPANION
