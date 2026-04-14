#!/bin/bash
# SINKRA Pipeline — Metrics & Cost Estimation
# Tracks tokens, duration, and estimated cost per LLM call.

if ! declare -f get_runtime_model >/dev/null 2>&1; then
  _runner_lib_metrics_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "$_runner_lib_metrics_dir/models.sh" ]]; then
    source "$_runner_lib_metrics_dir/models.sh"
  fi
  unset _runner_lib_metrics_dir
fi

# Cumulative metrics (reset per pipeline run)
METRICS_TOTAL_INPUT_TOKENS=0
METRICS_TOTAL_OUTPUT_TOKENS=0
METRICS_TOTAL_COST_USD=0
METRICS_TOTAL_DURATION=0
METRICS_CALL_COUNT=0
METRICS_FILE=""  # Set by caller (e.g., $OUTPUT_DIR/metrics.jsonl)

# Pricing per 1M tokens (USD).
# Canonical pricing table lives in models.sh via _runner_lib_model_pricing().
# get_pricing() remains as a backward-compatible wrapper for existing callers.
get_pricing() {
  local model="$1"
  local runtime="${2:-${SELECTED_RUNTIME:-}}"

  if declare -f _runner_lib_model_pricing >/dev/null 2>&1; then
    local pricing
    pricing="$(_runner_lib_model_pricing "$model" "$runtime")"
    if [[ "$pricing" == *:* ]]; then
      printf '%s\n' "$pricing"
    else
      local input_price output_price
      input_price="${pricing%% *}"
      output_price="${pricing##* }"
      printf '%s:%s\n' "$input_price" "$output_price"
    fi
    return 0
  fi

  # Fallback table for older runner-lib versions without models pricing.
  case "$model" in
    opus|claude-opus-4-6)           echo "5.00:25.00" ;;
    sonnet|claude-sonnet-4-6)       echo "3.00:15.00" ;;
    haiku|claude-haiku-4-5)         echo "1.00:5.00" ;;
    gpt-5-codex|gpt-5.4)            echo "2.50:15.00" ;;
    gpt-5.4-mini)                   echo "0.75:4.50" ;;
    o3)                             echo "10.00:40.00" ;;
    o4-mini)                        echo "2.00:8.00" ;;
    gpt-5.3-codex)                  echo "1.75:14.00" ;;
    gpt-5.3-codex-spark)            echo "1.00:4.00" ;;
    gemini-3.1-pro-preview)         echo "3.00:15.00" ;;  # midpoint of $2-4/$12-18
    gemini-3.1-flash)               echo "0.15:0.60" ;;
    gemini-2.5-pro)                 echo "1.88:12.50" ;;  # midpoint of $1.25-2.50/$10-15
    gemini-2.5-flash)               echo "0.30:2.50" ;;
    *)                              echo "3.00:15.00" ;;
  esac
}

# Estimate tokens from byte count (rough: 1 token ≈ 4 bytes for English/PT-BR)
bytes_to_tokens() {
  local bytes="$1"
  echo $(( bytes / 4 ))
}

# Calculate cost in USD for a given token count and model.
# Args: $1=input_tokens, $2=output_tokens, $3=model
# Prints: cost in USD (6 decimal places)
calculate_cost() {
  local input_tokens="$1"
  local output_tokens="$2"
  local model="$3"
  model="$(resolve_model_alias "$model" "${SELECTED_RUNTIME:-}")"

  local pricing
  pricing="$(get_pricing "$model")"
  local input_price_per_1m="${pricing%%:*}"
  local output_price_per_1m="${pricing##*:}"

  # cost = (input_tokens / 1_000_000 * input_price) + (output_tokens / 1_000_000 * output_price)
  python3 -c "
i = $input_tokens * $input_price_per_1m / 1_000_000
o = $output_tokens * $output_price_per_1m / 1_000_000
print(f'{i + o:.6f}')
" 2>/dev/null || echo "0.000000"
}

# Record metrics for one LLM call.
# Args: $1=model, $2=input_bytes, $3=output_bytes, $4=duration_secs, $5=phase(optional),
#       $6=status(optional), $7=expected_duration(optional), $8=runtime(optional)
record_metrics() {
  local model="$1"
  local input_bytes="$2"
  local output_bytes="$3"
  local duration="$4"
  local phase="${5:-unknown}"
  local status="${6:-ok}"
  local expected_duration="${7:-0}"
  local runtime_override="${8:-$SELECTED_RUNTIME}"

  local input_tokens
  input_tokens=$(bytes_to_tokens "$input_bytes")
  local output_tokens
  output_tokens=$(bytes_to_tokens "$output_bytes")
  local cost
  cost=$(calculate_cost "$input_tokens" "$output_tokens" "$model")

  # Update cumulative counters (in-memory — may be lost in subshells)
  METRICS_TOTAL_INPUT_TOKENS=$((METRICS_TOTAL_INPUT_TOKENS + input_tokens))
  METRICS_TOTAL_OUTPUT_TOKENS=$((METRICS_TOTAL_OUTPUT_TOKENS + output_tokens))
  METRICS_TOTAL_DURATION=$((METRICS_TOTAL_DURATION + duration))
  METRICS_CALL_COUNT=$((METRICS_CALL_COUNT + 1))

  # Calculate cumulative cost from JSONL (immune to subshell variable loss)
  # Must happen BEFORE appending current entry to JSONL
  if [[ -n "$METRICS_FILE" && -f "$METRICS_FILE" ]]; then
    METRICS_TOTAL_COST_USD=$(python3 -c "
import json
total = sum(json.loads(l).get('cost_usd',0) for l in open('$METRICS_FILE') if l.strip())
print(f'{total + $cost:.6f}')
" 2>/dev/null || echo "0.000000")
  else
    METRICS_TOTAL_COST_USD=$(python3 -c "print(f'{$cost:.6f}')" 2>/dev/null || echo "$cost")
  fi

  # Display inline
  echo "  📊 Tokens: ~${input_tokens} in / ~${output_tokens} out | Cost: \$${cost} | Total: \$${METRICS_TOTAL_COST_USD}" >&2

  # Calculate efficiency metrics
  local solve_rate="null"
  local tokens_per_useful_byte="null"

  if [[ "$expected_duration" -gt 0 && "$duration" -gt 0 ]]; then
    solve_rate=$(python3 -c "print(f'{min($expected_duration / $duration, 1.0):.3f}')" 2>/dev/null || echo "null")
  fi
  if [[ "$output_bytes" -gt 0 ]]; then
    tokens_per_useful_byte=$(python3 -c "print(f'{($input_tokens + $output_tokens) / $output_bytes:.2f}')" 2>/dev/null || echo "null")
  fi

  # Append to metrics file (JSONL) — AFTER cumulative calculation
  if [[ -n "$METRICS_FILE" ]]; then
    local squad_slug="${SQUAD_SLUG:-${SQUAD_NAME:-unknown}}"
    local agent_slug="${AGENT_SLUG:-unknown}"
    cat >> "$METRICS_FILE" << EOF
{"ts":"$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S)","squad":"$squad_slug","agent":"$agent_slug","phase":"$phase","model":"$model","runtime":"$runtime_override","input_tokens":$input_tokens,"output_tokens":$output_tokens,"input_bytes":$input_bytes,"output_bytes":$output_bytes,"cost_usd":$cost,"duration_s":$duration,"status":"$status","cumulative_cost_usd":$METRICS_TOTAL_COST_USD,"solve_rate":$solve_rate,"tokens_per_useful_byte":$tokens_per_useful_byte}
EOF
  fi
}

# Emit cost for a completed phase (convenience wrapper).
# Calculates cost from bytes + model and records to JSONL.
# Args: $1=model, $2=input_bytes, $3=output_bytes, $4=duration, $5=phase
# Story: RUNNER-3.2
emit_cost() {
  local model="$1"
  local input_bytes="$2"
  local output_bytes="$3"
  local duration="${4:-0}"
  local phase="${5:-unknown}"

  local input_tokens output_tokens cost
  input_tokens=$(bytes_to_tokens "$input_bytes")
  output_tokens=$(bytes_to_tokens "$output_bytes")
  cost=$(calculate_cost "$input_tokens" "$output_tokens" "$model")

  echo "$cost"
}

# Cross-squad cost summary from all metrics.jsonl files.
# Scans outputs/*/metrics.jsonl and outputs/*/logs/job-metrics.jsonl
# Args: $1=outputs_base_dir (optional, defaults to outputs/)
# Story: RUNNER-3.2
cost_summary() {
  local base_dir="${1:-outputs}"

  python3 - "$base_dir" <<'PYEOF'
import json, os, sys, glob

base = sys.argv[1]
patterns = [
    f"{base}/**/metrics.jsonl",
    f"{base}/**/job-metrics.jsonl",
]

squads = {}
for pattern in patterns:
    for f in glob.glob(pattern, recursive=True):
        for line in open(f):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            squad = d.get("squad", os.path.basename(os.path.dirname(os.path.dirname(f))))
            if squad not in squads:
                squads[squad] = {"runs": 0, "tokens": 0, "cost": 0.0}
            squads[squad]["runs"] += 1
            squads[squad]["tokens"] += d.get("input_tokens", 0) + d.get("output_tokens", 0)
            squads[squad]["cost"] += d.get("cost_usd", 0)

if not squads:
    print("No metrics found.")
    sys.exit(0)

print(f"{'Squad':<20} {'Runs':>6} {'Tokens':>10} {'Cost (USD)':>12} {'Avg/Run':>10}")
print("-" * 62)
total_runs = total_tokens = 0
total_cost = 0.0
for sq in sorted(squads):
    s = squads[sq]
    avg = s["cost"] / max(s["runs"], 1)
    print(f"{sq:<20} {s['runs']:>6} {s['tokens']:>10,} ${s['cost']:>10.2f} ${avg:>9.4f}")
    total_runs += s["runs"]
    total_tokens += s["tokens"]
    total_cost += s["cost"]
print("-" * 62)
avg_total = total_cost / max(total_runs, 1)
print(f"{'TOTAL':<20} {total_runs:>6} {total_tokens:>10,} ${total_cost:>10.2f} ${avg_total:>9.4f}")
PYEOF
}

# Check if accumulated cost exceeds a cap. Call after each phase.
# Args: $1=max_cost (USD string, e.g. "2.00"). Empty = no cap.
# Returns: 0=under cap (or no cap), 75=exceeded (TEMPFAIL)
# Story: RUNNER-1.3 (Runner Hardening)
check_cost_cap() {
  local max_cost="${1:-}"
  [[ -z "$max_cost" ]] && return 0  # No cap set — backward compatible

  # Read cumulative cost from JSONL (source of truth, immune to subshell loss)
  local current="0"
  if [[ -n "$METRICS_FILE" && -f "$METRICS_FILE" ]]; then
    current=$(python3 -c "
import json
total = sum(json.loads(l).get('cost_usd',0) for l in open('$METRICS_FILE') if l.strip())
print(f'{total:.6f}')
" 2>/dev/null || echo "$METRICS_TOTAL_COST_USD")
  else
    current="${METRICS_TOTAL_COST_USD:-0}"
  fi

  local exceeded
  exceeded=$(python3 -c "print(1 if float('$current') > float('$max_cost') else 0)" 2>/dev/null || echo "0")

  if [[ "$exceeded" == "1" ]]; then
    echo "══════════════════════════════════════════" >&2
    echo "  COST CAP EXCEEDED" >&2
    echo "  Current: \$$current / Cap: \$$max_cost" >&2
    echo "  Run stopped. State saved for resume." >&2
    echo "══════════════════════════════════════════" >&2
    return 75  # TEMPFAIL — caller should save_state then exit
  fi
  return 0
}

# Print final cost summary (reads from metrics.jsonl — immune to subshell issues).
show_cost_summary() {
  if [[ -z "$METRICS_FILE" || ! -f "$METRICS_FILE" ]]; then
    echo ""
    echo "  💰 No metrics recorded."
    return
  fi

  # Aggregate from JSONL (subshell globals are lost, file is the source of truth)
  local agg
  agg=$(python3 -c "
import json
total_in = 0; total_out = 0; total_cost = 0.0; total_dur = 0; calls = 0
solve_rates = []; tpub = []
models = set()
runtimes = set()
for line in open('$METRICS_FILE'):
    line = line.strip()
    if not line: continue
    d = json.loads(line)
    total_in += d.get('input_tokens', 0)
    total_out += d.get('output_tokens', 0)
    total_cost += d.get('cost_usd', 0)
    total_dur += d.get('duration_s', 0)
    calls += 1
    models.add(d.get('model', ''))
    runtimes.add(d.get('runtime', ''))
    sr = d.get('solve_rate')
    if sr is not None and sr != 'null': solve_rates.append(float(sr))
    tp = d.get('tokens_per_useful_byte')
    if tp is not None and tp != 'null': tpub.append(float(tp))
avg_sr = f'{sum(solve_rates)/len(solve_rates):.3f}' if solve_rates else 'n/a'
avg_tp = f'{sum(tpub)/len(tpub):.1f}' if tpub else 'n/a'
print(f'{total_in}|{total_out}|{total_cost:.6f}|{total_dur}|{calls}|{\",\".join(models)}|{\",\".join(runtimes)}|{avg_sr}|{avg_tp}')
" 2>/dev/null)

  if [[ -z "$agg" ]]; then
    echo "  💰 Could not parse metrics."
    return
  fi

  IFS='|' read -r m_in m_out m_cost m_dur m_calls m_models m_runtimes m_solve_rate m_tpub <<< "$agg"
  local m_total=$((m_in + m_out))

  # Derive pricing from the most-used model in the JSONL (not global $MODEL which may be unset)
  local _primary_model="${m_models%%,*}"
  local pricing
  pricing="$(get_pricing "$(resolve_model_alias "${_primary_model:-${MODEL:-sonnet}}" "${SELECTED_RUNTIME:-}")")"
  local input_price="${pricing%%:*}"
  local output_price="${pricing##*:}"

  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║                 💰 Cost & Efficiency Summary                ║"
  echo "╠══════════════════════════════════════════════════════════════╣"
  echo "║  Runtime(s):    $m_runtimes"
  echo "║  Model(s):      $m_models"
  echo "║  Pricing:       \$${input_price}/M in, \$${output_price}/M out"
  echo "║                                                              ║"
  printf "║  Input tokens:  ~%d\n" "$m_in"
  printf "║  Output tokens: ~%d\n" "$m_out"
  printf "║  Total tokens:  ~%d\n" "$m_total"
  echo "║  LLM calls:     $m_calls"
  echo "║  Total time:    ${m_dur}s"
  echo "║                                                              ║"
  echo "║  💰 Estimated cost: \$${m_cost}"
  echo "║                                                              ║"
  echo "║  ⚡ Efficiency:"
  echo "║     Solve rate:           $m_solve_rate (1.0 = ideal speed)"
  echo "║     Tokens/useful byte:   $m_tpub (lower = more efficient)"
  echo "║                                                              ║"
  echo "║  📊 Details: $(basename "$METRICS_FILE")"
  echo "╚══════════════════════════════════════════════════════════════╝"
}
