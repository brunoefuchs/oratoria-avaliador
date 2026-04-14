#!/bin/bash
# SINKRA Context Engine — Smart context management for pipeline runners.
# Applies deepH/PAI insights with KISS principle.
#
# Features:
#   1. Phase-aware context boost (Context Moments)
#   2. Cumulative handoff chain (not just last phase)
#   3. Error signature dedup (block same failing call)
#   4. Content-addressable artifacts (SHA dedup)
#   5. Inline vs artifact decision by size

# ═══════════════════════════════════════════════════════════════
# 1. CONTEXT MOMENTS — What matters changes by phase
# ═══════════════════════════════════════════════════════════════
# Instead of sending everything to every phase, send what matters.
# Pedro Valerio: "Cada fase depende do output da anterior como input.
# Mandar tudo é preguiça, não eficiência."

# Get which squad files to actually READ (not just list) per validate phase.
# Returns newline-separated file paths relative to squad dir.
get_phase_focus_files() {
  local phase_num="$1"
  local squad_path="$2"

  case "$phase_num" in
    1) # Inventory: config + directory structure only
      echo "config.yaml"
      ;;
    2) # Executors & Hierarchy: config + agent defs + composition
      echo "config.yaml"
      ls "$squad_path/agents/"*.md 2>/dev/null | head -5 | while IFS= read -r f; do basename "$f"; done | sed 's/^/agents\//'
      ;;
    3) # Task Anatomy & Tokens: task files + data
      ls "$squad_path/tasks/"*.md 2>/dev/null | head -8 | while IFS= read -r f; do basename "$f"; done | sed 's/^/tasks\//'
      echo "data/process-token-map.yaml" 2>/dev/null
      ;;
    4) # Domains, Gates, Mandamentos: workflows + quality + config
      ls "$squad_path/workflows/"*.yaml 2>/dev/null | head -5 | while IFS= read -r f; do basename "$f"; done | sed 's/^/workflows\//'
      echo "config.yaml"
      ls "$squad_path/data/"*gate* "$squad_path/data/"*quality* "$squad_path/data/"*veto* 2>/dev/null | head -3 | while IFS= read -r f; do basename "$f"; done | sed 's/^/data\//'
      ;;
    5) # Axiomas, Infra, Extensions: data + templates
      ls "$squad_path/data/"*.yaml 2>/dev/null | head -5 | while IFS= read -r f; do basename "$f"; done | sed 's/^/data\//'
      ls "$squad_path/templates/"*.yaml 2>/dev/null | head -3 | while IFS= read -r f; do basename "$f"; done | sed 's/^/templates\//'
      ;;
    6) # Consolidation: dim-*.yaml only (already handled separately)
      ;;
  esac
}

# Read focused squad files for a phase (instead of sending 145KB of everything).
# Returns concatenated content with file headers.
# Alan Nicolas: "Manda o que precisa, não o que tem."
read_focused_context() {
  local phase_num="$1"
  local squad_path="$2"
  local max_bytes="${3:-30000}"  # Budget per phase

  local total_bytes=0
  local result=""

  while IFS= read -r rel_path; do
    [[ -z "$rel_path" ]] && continue
    local full_path="$squad_path/$rel_path"
    [[ ! -f "$full_path" ]] && continue

    local file_size
    file_size=$(wc -c < "$full_path" | tr -d ' ')

    # Budget check
    if [[ $((total_bytes + file_size)) -gt $max_bytes ]]; then
      result+="--- $rel_path (TRUNCATED — ${file_size}B exceeds budget) ---"$'\n'
      # Send first 2000 bytes only
      result+="$(head -c 2000 "$full_path")"$'\n'
      result+="... [truncated at 2000B of ${file_size}B]"$'\n'$'\n'
      total_bytes=$((total_bytes + 2000))
    else
      result+="--- $rel_path (${file_size}B) ---"$'\n'
      result+="$(cat "$full_path")"$'\n'$'\n'
      total_bytes=$((total_bytes + file_size))
    fi
  done <<< "$(get_phase_focus_files "$phase_num" "$squad_path")"

  echo "$result"
}

# ═══════════════════════════════════════════════════════════════
# 2. CUMULATIVE HANDOFF CHAIN — Carry decisions, not just last phase
# ═══════════════════════════════════════════════════════════════
# Pedro Valerio: "O pipeline é uma cadeia. Cada elo precisa saber
# o que os anteriores decidiram, não só o último."

# Build cumulative decisions from all phase-handoff.yaml files.
# Returns compact summary of all previous phases' key decisions.
build_handoff_chain() {
  local output_dir="$1"
  local current_phase="$2"

  local chain=""
  local handoff_count=0

  # Read all previous handoffs (stored as phase-N-handoff.yaml)
  for i in $(seq 1 $((current_phase - 1))); do
    local hf="$output_dir/phase-${i}-handoff.yaml"
    if [[ -f "$hf" ]]; then
      handoff_count=$((handoff_count + 1))
      # Extract only decisions and warnings (compact)
      local decisions
      decisions=$(python3 -c "
import yaml
with open('$hf') as f:
    d = yaml.safe_load(f) or {}
h = d.get('handoff', d)
phase = h.get('from_phase', $i)
agent = h.get('from_agent', '?')
decs = h.get('decisions', [])
warns = h.get('warnings', [])
focus = h.get('next_agent_focus', [])
print(f'Phase {phase} (@{agent}):')
for d in decs[:3]: print(f'  - {d}')
for w in warns[:2]: print(f'  ⚠️ {w}')
" 2>/dev/null)
      chain+="$decisions"$'\n'
    fi
  done

  # Also check the generic phase-handoff.yaml (current/last)
  if [[ -f "$output_dir/phase-handoff.yaml" && "$handoff_count" -eq 0 ]]; then
    chain+="$(cat "$output_dir/phase-handoff.yaml")"$'\n'
  fi

  echo "$chain"
}

# Rename phase-handoff.yaml to phase-N-handoff.yaml after each phase completes.
# Preserves chain for future phases.
archive_phase_handoff() {
  local output_dir="$1"
  local phase_num="$2"

  if [[ -f "$output_dir/phase-handoff.yaml" ]]; then
    cp "$output_dir/phase-handoff.yaml" "$output_dir/phase-${phase_num}-handoff.yaml"
  fi
}

# ═══════════════════════════════════════════════════════════════
# 3. ERROR SIGNATURE DEDUP — Don't repeat the same failing call
# ═══════════════════════════════════════════════════════════════
# deepH H-11: "Block by repetition, not count."

# Error signatures tracked via file (bash 3.2 compatible — no associative arrays)
_ERROR_SIG_FILE=""

_init_error_tracking() {
  if [[ -z "$_ERROR_SIG_FILE" ]]; then
    _ERROR_SIG_FILE="$(mktemp)"
  fi
}

# Record a failed call signature.
record_error_signature() {
  _init_error_tracking
  local sig="${1}:${2}:${3}"
  echo "$sig" >> "$_ERROR_SIG_FILE"
}

# Check if a call has failed too many times (same signature).
# Returns: 0=ok to proceed, 1=blocked
check_error_signature() {
  _init_error_tracking
  local sig="${1}:${2}:${3}"
  local max="${4:-3}"
  local count
  count=$(grep -c "^${sig}$" "$_ERROR_SIG_FILE" 2>/dev/null || echo 0)

  if [[ "$count" -ge "$max" ]]; then
    echo "  🔴 Blocked: same call failed ${count}x (signature: ${sig:0:30}...)" >&2
    return 1
  fi
  return 0
}

# ═══════════════════════════════════════════════════════════════
# 4. CONTENT-ADDRESSABLE ARTIFACTS — SHA dedup
# ═══════════════════════════════════════════════════════════════
# deepH H-16: "Same content = same ID = no duplicate storage."

# Check if an artifact with identical content already exists.
# Args: $1=file_path
# Returns: 0=new, 1=duplicate (prints existing path)
check_artifact_dedup() {
  local file="$1"
  local output_dir="$2"

  [[ ! -f "$file" ]] && return 0

  local hash
  hash=$(sha256sum "$file" 2>/dev/null || shasum -a 256 "$file")
  hash=$(echo "$hash" | cut -d' ' -f1 | cut -c1-12)

  # Check if any file in output_dir has same hash
  for existing in "$output_dir"/*.yaml "$output_dir"/*.md; do
    [[ ! -f "$existing" ]] && continue
    [[ "$existing" == "$file" ]] && continue

    local existing_hash
    existing_hash=$(shasum -a 256 "$existing" | cut -d' ' -f1 | cut -c1-12)

    if [[ "$hash" == "$existing_hash" ]]; then
      echo "  ♻️  Dedup: $(basename "$file") identical to $(basename "$existing")" >&2
      return 1
    fi
  done

  return 0
}


# (No prompt trimming — send full context. The phase-focused loading in
# read_focused_context already keeps prompts reasonable. Cutting content
# from a prompt that was built intentionally degrades output quality.)
