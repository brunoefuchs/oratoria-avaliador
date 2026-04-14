#!/usr/bin/env bash
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# RUNNER-LIB: state-manager.sh â€” Pipeline state file management via jq
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Atomic state updates with .tmp staging (safe against crashes).
# Used by: sinkra-map.sh, mmos.sh, copy.sh, ralph-7d.sh, swipe.sh
#
# Requires: jq

# Atomic jq update â€” writes to .tmp, validates JSON, then moves.
# Usage: state_update [jq_args...] <jq_filter> <state_file>
# Example: state_update --arg status "running" '.status = $status' "$STATE_FILE"
_state_has_jq() {
  command -v jq >/dev/null 2>&1
}

_state_json_validate() {
  local state_file="$1"
  if _state_has_jq; then
    jq empty "$state_file" >/dev/null 2>&1
  else
    python3 - "$state_file" <<'PYEOF' >/dev/null 2>&1
import json, sys
with open(sys.argv[1], encoding='utf-8') as fh:
    json.load(fh)
PYEOF
  fi
}

_state_json_get() {
  local state_file="$1"
  local path="$2"
  if _state_has_jq; then
    jq -r "$path // empty" "$state_file" 2>/dev/null
  else
    python3 - "$state_file" "$path" <<'PYEOF' 2>/dev/null
import json, sys
with open(sys.argv[1], encoding='utf-8') as fh:
    data = json.load(fh)
path = sys.argv[2]
if path.endswith('// empty'):
    path = path[:-8].strip()
if path.startswith('.'):
    path = path[1:]
value = data
for part in [p for p in path.split('.') if p]:
    if isinstance(value, dict):
        value = value.get(part, '')
    else:
        value = ''
        break
if value in ('', None):
    print('', end='')
elif isinstance(value, bool):
    print('true' if value else 'false', end='')
else:
    print(value, end='')
PYEOF
  fi
}

_state_python_update() {
  local state_file="$1"
  local filter="$2"
  shift 2
  python3 - "$state_file" "$filter" "$@" <<'PYEOF'
import json, sys
state_file = sys.argv[1]
filter_expr = sys.argv[2]
args = sys.argv[3:]
named = {}
i = 0
while i < len(args):
    kind = args[i]
    if kind in ('--arg', '--argjson') and i + 2 < len(args):
        key = args[i + 1]
        raw = args[i + 2]
        named[key] = json.loads(raw) if kind == '--argjson' else raw
        i += 3
    else:
        i += 1
with open(state_file, encoding='utf-8') as fh:
    data = json.load(fh)
if filter_expr == '.':
    pass
elif filter_expr == '.status = $status':
    data['status'] = named['status']
elif filter_expr == '.phases[$key].status = $status':
    phase = data.setdefault('phases', {}).setdefault(named['key'], {})
    phase['status'] = named['status']
elif filter_expr == '.phases[$key].status = $status | .phases[$key].agent = $agent':
    phase = data.setdefault('phases', {}).setdefault(named['key'], {})
    phase['status'] = named['status']
    phase['agent'] = named['agent']
elif '.target //= $slug' in filter_expr and '.checkpoints //= {}' in filter_expr:
    data.setdefault('target', named['slug'])
    data.setdefault('type', 'sinkra-process')
    data.setdefault('process_slug', named['slug'])
    data.setdefault('process_name', named['name'])
    data.setdefault('mode', named['mode'])
    data.setdefault('status', 'initialized')
    data.setdefault('current_phase', named['phase'])
    data.setdefault('current_agent', named['agent'])
    data.setdefault('model', named['model'])
    data.setdefault('phases', named['phases'])
    data.setdefault('artifacts', [])
    data.setdefault('checkpoints', {})
elif filter_expr == '.status = "complete" | .completed_at = $ts | .total_duration_seconds = $dur':
    data['status'] = 'complete'
    data['completed_at'] = named['ts']
    data['total_duration_seconds'] = named['dur']
elif filter_expr == '.artifacts += [$art]':
    data.setdefault('artifacts', []).append(named['art'])
else:
    raise SystemExit(f'unsupported state_update filter without jq: {filter_expr}')
with open(state_file + '.tmp', 'w', encoding='utf-8', newline='\n') as fh:
    json.dump(data, fh, ensure_ascii=False, indent=2)
    fh.write('\n')
PYEOF
}

state_update() {
  local state_file="${!#}"  # last argument is the file
  if [[ ! -f "$state_file" ]]; then
    echo "  [state-manager] state file not found: $state_file" >&2
    return 1
  fi
  if _state_has_jq; then
    jq "$@" > "${state_file}.tmp" 2>/dev/null
  else
    local filter_index=$(($# - 1))
    local filter="${!filter_index}"
    _state_python_update "$state_file" "$filter" "${@:1:$(($# - 2))}" 2>/dev/null || {
      rm -f "${state_file}.tmp"
      return 1
    }
  fi
  if _state_json_validate "${state_file}.tmp"; then
    mv "${state_file}.tmp" "$state_file"
  else
    echo "  [state-manager] jq validation failed, state preserved" >&2
    rm -f "${state_file}.tmp"
    return 1
  fi
}

# Initialize a pipeline state file with standard fields.
# Usage: state_init <state_file> <target_slug> <target_type> [extra_json_fields]
# Example: state_init "$STATE" "copy" "pipeline" '{"mode":"greenfield","model":"opus"}'
state_init() {
  local state_file="$1"
  local target_slug="$2"
  local target_type="${3:-pipeline}"
  local _default_extra='{}'
  local extra_json="${4:-$_default_extra}"

  if [[ -f "$state_file" ]]; then
    return 0  # already exists, don't overwrite
  fi

  local dir
  dir=$(dirname "$state_file")
  mkdir -p "$dir"

  local ts
  ts=$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S)
  local tmp_file="${state_file}.tmp"

  if _state_has_jq; then
    if ! jq -n \
      --arg slug "$target_slug" \
      --arg type "$target_type" \
      --arg ts "$ts" \
      --argjson extra "$extra_json" \
      '{
        target: $slug,
        type: $type,
        status: "initialized",
        started_at: $ts,
        current_phase: 1,
        phases: {},
        artifacts: [],
        checkpoints: {}
      } + $extra' > "$tmp_file"; then
      rm -f "$tmp_file"
      return 1
    fi
  else
    python3 - "$tmp_file" "$target_slug" "$target_type" "$ts" "$extra_json" <<'PYEOF' || {
import json, sys
out_file, slug, target_type, ts, extra_json = sys.argv[1:]
data = {
    "target": slug,
    "type": target_type,
    "status": "initialized",
    "started_at": ts,
    "current_phase": 1,
    "phases": {},
    "artifacts": [],
    "checkpoints": {},
}
data.update(json.loads(extra_json))
with open(out_file, 'w', encoding='utf-8', newline='\n') as fh:
    json.dump(data, fh, ensure_ascii=False, indent=2)
    fh.write('\n')
PYEOF
      rm -f "$tmp_file"
      return 1
    }
  fi

  if _state_json_validate "$tmp_file"; then
    mv "$tmp_file" "$state_file"
  else
    rm -f "$tmp_file"
    return 1
  fi
}

# Get a field from state file.
# Usage: state_get <state_file> <jq_path> [default]
# Example: state_get "$STATE" '.current_phase' '1'
state_get() {
  local state_file="$1"
  local path="$2"
  local default="${3:-}"
  local val
  val=$(_state_json_get "$state_file" "$path")
  echo "${val:-$default}"
}

# Update phase status in state file.
# Usage: state_phase_update <state_file> <phase_key> <status> [agent]
state_phase_update() {
  local state_file="$1"
  local phase_key="$2"
  local status="$3"
  local agent="${4:-}"

  if [[ -n "$agent" ]]; then
    state_update \
      --arg key "$phase_key" \
      --arg status "$status" \
      --arg agent "$agent" \
      '.phases[$key].status = $status | .phases[$key].agent = $agent' \
      "$state_file"
  else
    state_update \
      --arg key "$phase_key" \
      --arg status "$status" \
      '.phases[$key].status = $status' \
      "$state_file"
  fi
}

# Mark pipeline complete with duration.
# Usage: state_complete <state_file> <duration_seconds>
state_complete() {
  local state_file="$1"
  local duration="${2:-0}"
  local ts
  ts=$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S)

  state_update \
    --arg ts "$ts" \
    --argjson dur "$duration" \
    '.status = "complete" | .completed_at = $ts | .total_duration_seconds = $dur' \
    "$state_file"
}

# Register an artifact in state file.
# Usage: state_add_artifact <state_file> <artifact_path>
state_add_artifact() {
  local state_file="$1"
  local artifact="$2"
  state_update \
    --arg art "$artifact" \
    '.artifacts += [$art]' \
    "$state_file"
}

# Validate that a state file has required schema fields.
# Usage: state_validate <state_file>
# Returns: 0=valid, 1=missing fields (prints which ones)
state_validate() {
  local state_file="$1"
  if [[ ! -f "$state_file" ]]; then
    echo "[state-manager] file not found: $state_file" >&2
    return 1
  fi

  local required=("target" "type" "status" "started_at" "current_phase")
  local missing=()
  for field in "${required[@]}"; do
    local val
    val=$(_state_json_get "$state_file" ".$field")
    if [[ -z "$val" ]]; then
      missing+=("$field")
    fi
  done

  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "[state-manager] missing required fields: ${missing[*]}" >&2
    return 1
  fi
  return 0
}

# Reconcile state file against filesystem-tracked artifacts.
# Usage: state_reconcile <state_file>
# Returns/prints:
#   CLEAN   -> state válido e artifacts presentes
#   DRIFT   -> state válido, mas artifacts ausentes no filesystem
#   CORRUPT -> state ausente/inválido/schema incompleto
#
# Nota: esta implementação cobre a reconciliação essencial exigida pelos
# runners atuais e pelos testes do runner-lib. Checagens adicionais de hash/git
# podem ser acopladas depois sem quebrar o contrato CLEAN/DRIFT/CORRUPT.
state_reconcile() {
  local state_file="$1"

  if [[ ! -f "$state_file" ]]; then
    echo "CORRUPT"
    return 0
  fi

  if ! _state_json_validate "$state_file"; then
    echo "CORRUPT"
    return 0
  fi

  if ! state_validate "$state_file" >/dev/null 2>&1; then
    echo "CORRUPT"
    return 0
  fi

  local artifacts=()
  if _state_has_jq; then
    while IFS= read -r artifact; do
      [[ -n "$artifact" ]] && artifacts+=("$artifact")
    done < <(jq -r '.artifacts[]? // empty' "$state_file" 2>/dev/null)
  else
    while IFS= read -r artifact; do
      [[ -n "$artifact" ]] && artifacts+=("$artifact")
    done < <(
      python3 - "$state_file" <<'PYEOF' 2>/dev/null
import json, sys
with open(sys.argv[1], encoding='utf-8') as fh:
    data = json.load(fh)
for item in data.get("artifacts", []) or []:
    if item:
        print(item)
PYEOF
    )
  fi

  local drift=false
  local artifact=""
  for artifact in "${artifacts[@]}"; do
    if [[ ! -e "$artifact" ]]; then
      drift=true
      break
    fi
  done

  if [[ "$drift" == "true" ]]; then
    echo "DRIFT"
    return 0
  fi

  echo "CLEAN"
  return 0
}

RUNNER_LIB_STATE_MANAGER=true
