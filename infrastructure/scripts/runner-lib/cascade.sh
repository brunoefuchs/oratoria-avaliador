#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER-LIB — Cascade Model Routing
# ═══════════════════════════════════════════════════════════════
# Starts with cheap model, escalates on low confidence.
# Uses _exec_runtime() from runtime.sh (file-based I/O).
# Integrates with RUNNER-2.3 run-history to skip tiers that always fail.
#
# Usage:
#   PHASE_CASCADE="haiku:0.7,sonnet:0.8,opus"
#   cascade_run "$prompt_file" "$output_file" "phase_3"
#
# Story: RUNNER-3.3 (Cascade Model Routing + Replan-on-Failure)
# Dependencies: runtime.sh (_exec_runtime), metrics.sh (record_metrics),
#               memory.sh (run-history for skip-tier optimization)

# ═══════════════════════════════════════════════════════════════
# Smart Model Routing — classify_turn() (Story 115.9)
# ═══════════════════════════════════════════════════════════════
# Keyword-based turn classification for cheap model routing.
# Simple turns route to RUNNER_CHEAP_MODEL, complex to primary.
# Precedence: classify_turn() only when RUNNER_SMART_ROUTING=true
#             AND no PHASE_CASCADE active.

RUNNER_SMART_ROUTING="${RUNNER_SMART_ROUTING:-true}"
RUNNER_CHEAP_MODEL="${RUNNER_CHEAP_MODEL:-haiku}"

# Classify a turn as simple or complex based on content heuristics.
# Args: $1=prompt_file (path to file containing the turn text)
# Prints: "simple" or "complex"
classify_turn() {
  local prompt_file="$1"

  [[ ! -f "$prompt_file" ]] && echo "complex" && return 0

  local content
  content=$(cat "$prompt_file" 2>/dev/null || echo "")

  # Empty file → simple. Ausência do arquivo continua no safe default acima.
  [[ -z "$content" ]] && echo "simple" && return 0

  local char_count=${#content}
  local word_count newline_count

  word_count=$(echo "$content" | wc -w | tr -d ' ')
  newline_count=$(echo "$content" | wc -l | tr -d ' ')
  newline_count=$((newline_count - 1))  # wc -l counts terminated lines

  # Length gates: > 160 chars OR > 28 words OR > 1 newline → complex
  [[ $char_count -gt 160 ]] && echo "complex" && return 0
  [[ $word_count -gt 28 ]] && echo "complex" && return 0
  [[ $newline_count -gt 1 ]] && echo "complex" && return 0

  # Code signals: backticks or URLs → complex
  if echo "$content" | grep -qE '`|https?://' 2>/dev/null; then
    echo "complex" && return 0
  fi

  # Complex keywords (case-insensitive)
  local keywords="debug|implement|implemente|test|refactor|architecture|analyze|create|design|evaluate|validate|deploy|migrate"
  if echo "$content" | grep -qiE "\b($keywords)\b" 2>/dev/null; then
    echo "complex" && return 0
  fi

  echo "simple"
}

# Route a turn through smart routing if enabled and no cascade active.
# Args: $1=prompt_file, $2=output_file, $3=phase_label
# Returns: 0 if handled by smart routing, 1 if should use normal path
smart_route() {
  local prompt_file="$1"
  local output_file="$2"
  local phase="${3:-unknown}"
  local cheap_model="${RUNNER_CHEAP_MODEL:-haiku}"

  # Disabled → skip
  [[ "$RUNNER_SMART_ROUTING" != "true" ]] && return 1

  # Cascade active → skip (cascade has precedence)
  [[ -n "${PHASE_CASCADE:-}" ]] && return 1

  local classification
  classification=$(classify_turn "$prompt_file")

  if [[ "$classification" == "simple" ]]; then
    echo "  [ROUTING] Simple turn detected → routing to ${cheap_model}" >&2
    _exec_runtime "$cheap_model" "$prompt_file" "$output_file"
    return $?
  fi

  return 1  # Complex → use normal path
}

# Run a phase with cascade model routing.
# Args: $1=prompt_file, $2=output_file, $3=phase_label
# Env: PHASE_CASCADE="model:threshold,model:threshold,model"
# Returns: 0=success, 1=all tiers exhausted
cascade_run() {
  local prompt_file="$1"
  local output_file="$2"
  local phase="${3:-unknown}"
  local cascade_spec="${PHASE_CASCADE:-}"

  # No cascade: use default model
  if [[ -z "$cascade_spec" ]]; then
    _exec_runtime "$MODEL" "$prompt_file" "$output_file"
    return $?
  fi

  local level=0
  local tier_output_file
  tier_output_file=$(mktemp)

  IFS=',' read -ra tiers <<< "$cascade_spec"

  for tier in "${tiers[@]}"; do
    level=$((level + 1))
    local tier_model="${tier%%:*}"
    local threshold="${tier#*:}"
    [[ "$tier_model" == "$threshold" ]] && threshold="0"  # Last tier: no threshold

    # Skip tier if run-history shows 0% success (memory.sh integration from RUNNER-2.3)
    if declare -f get_best_model_for_phase >/dev/null 2>&1 && [[ -n "${HISTORY_FILE:-}" && -f "${HISTORY_FILE:-}" ]]; then
      local tier_success_rate
      tier_success_rate=$(jq -rs "
        [.[] | select(.phase == \"$phase\" and .model == \"$tier_model\" and .runtime == \"$SELECTED_RUNTIME\")]
        | if length > 5 then (map(select(.success)) | length) / length else 1 end
      " "$HISTORY_FILE" 2>/dev/null || echo "1")
      if awk "BEGIN{exit($tier_success_rate == 0 ? 0 : 1)}" 2>/dev/null; then
        echo "  [cascade] Skipping $tier_model for $phase (0% success in history)" >&2
        continue
      fi
    fi

    # Execute with tier model
    local exit_code=0
    _exec_runtime "$tier_model" "$prompt_file" "$tier_output_file" "$SELECTED_RUNTIME" || exit_code=$?

    # Record attempt in metrics
    if declare -f record_metrics >/dev/null 2>&1; then
      local out_bytes in_bytes
      out_bytes=$(wc -c < "$tier_output_file" 2>/dev/null | tr -d ' ' || echo 0)
      in_bytes=$(wc -c < "$prompt_file" 2>/dev/null | tr -d ' ' || echo 0)
      record_metrics "$tier_model" "$in_bytes" "$out_bytes" "0" "cascade-$phase-L$level" \
        "$([ $exit_code -eq 0 ] && echo ok || echo error)" 2>/dev/null || true
    fi

    # If failed, try next tier
    [[ $exit_code -ne 0 ]] && continue

    # Calculate confidence
    local confidence
    confidence=$(calculate_confidence "$tier_output_file" "$phase")

    # Accept if meets threshold or is last tier
    if [[ "$threshold" == "0" ]] || \
       awk "BEGIN{exit($confidence >= $threshold ? 0 : 1)}" 2>/dev/null; then
      cp "$tier_output_file" "$output_file"
      rm -f "$tier_output_file"
      echo "  ✅ [cascade] $phase: accepted $tier_model (confidence=$confidence, level=$level)" >&2
      return 0
    fi

    echo "  ⬆️  [cascade] $phase: $tier_model confidence=$confidence < threshold=$threshold, escalating..." >&2
  done

  rm -f "$tier_output_file"
  echo "  ❌ [cascade] All tiers exhausted for $phase" >&2
  return 1
}

# Composable confidence scoring — combines structural + format-specific checks.
# NEVER uses LLM to judge its own output (circular).
# Args: $1=output_file, $2=phase_label
# Prints: confidence score 0.00-1.00
calculate_confidence() {
  local output_file="$1"
  local phase="${2:-}"

  python3 - "$output_file" "${PHASE_OUTPUT_SCHEMA:-}" <<'PYEOF'
import sys, os

output_file = sys.argv[1]
schema_spec = sys.argv[2] if len(sys.argv) > 2 else ""

try:
    with open(output_file) as f:
        content = f.read()
except Exception:
    print("0.00")
    sys.exit(0)

if not content.strip():
    print("0.00")
    sys.exit(0)

score = 0.3  # base: file exists and is non-empty
length = len(content)

# Length signals substantive response
if length > 500: score += 0.15
if length > 2000: score += 0.10

# Structure signals (headers, lists)
lines = content.split('\n')
if any(line.startswith('#') for line in lines): score += 0.10
if any(line.strip().startswith('- ') for line in lines): score += 0.05

# Format-specific validation
if schema_spec:
    try:
        import yaml
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            score += 0.15
            fields = [f.split(':')[0].strip() for f in schema_spec.split(',') if ':' in f]
            present = sum(1 for f in fields if f in data)
            score += 0.15 * (present / max(len(fields), 1))
    except Exception:
        pass
else:
    try:
        import yaml
        data = yaml.safe_load(content)
        if isinstance(data, dict): score += 0.10
    except Exception:
        pass
    try:
        import json
        json.loads(content)
        score += 0.10
    except Exception:
        pass

print(f"{min(score, 1.0):.2f}")
PYEOF
}
