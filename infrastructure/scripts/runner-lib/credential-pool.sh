#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# SINKRA Pipeline — Credential Pool (L5-Advanced)
# Multi-key rotation with cooldown for API key management.
#
# Features:
#   - Multiple API keys via RUNNER_API_KEYS or RUNNER_API_KEYS_FILE
#   - Strategies: round_robin (default), least_used
#   - Per-key cooldown: 429 → 1h, 401 → 24h, 402 → 24h
#   - State tracking in /tmp (ephemeral — resets on reboot)
#   - Fallback: all keys in cooldown → use last available key with warning
#
# Design Reference: Hermes credential_pool.py (PooledCredential, 4 strategies)
# Story: 115.10
# ═══════════════════════════════════════════════════════════════════════════════

# ── Configuration ──
# RUNNER_API_KEYS="key1,key2,key3"       — comma-separated keys
# RUNNER_API_KEYS_FILE=/path/to/file     — one key per line
# RUNNER_CREDENTIAL_STRATEGY=round_robin — round_robin | least_used
# RUNNER_NAME=my-runner                  — used for state file naming

# ── Cooldown durations (seconds) ──
_POOL_COOLDOWN_429="${RUNNER_COOLDOWN_429:-3600}"    # 1 hour
_POOL_COOLDOWN_401="${RUNNER_COOLDOWN_401:-86400}"   # 24 hours
_POOL_COOLDOWN_402="${RUNNER_COOLDOWN_402:-86400}"   # 24 hours

# ── Internal state ──
_POOL_KEYS=()
_POOL_STATE_FILE=""
_POOL_INITIALIZED=false
_POOL_LAST_INDEX=0
_POOL_LAST_KEY=""

# ── JSON helpers (jq with python3 fallback) ──

_pool_json_get() {
  local file="$1" expr="$2"
  if command -v jq >/dev/null 2>&1; then
    jq -r "$expr" "$file" 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c "
import json, sys
with open('$file') as f: data = json.load(f)
expr = '''$expr'''
if expr.startswith('.keys'):
    import re
    m = re.match(r'\.keys\[(\d+)\]\.(\w+)', expr)
    if m:
        idx, field = int(m.group(1)), m.group(2)
        keys = data.get('keys', [])
        if idx < len(keys):
            print(keys[idx].get(field, ''), end='')
        else:
            print('', end='')
    else:
        print(json.dumps(data.get('keys', [])), end='')
elif expr == '.last_index':
    print(data.get('last_index', 0), end='')
elif expr == '.keys | length':
    print(len(data.get('keys', [])), end='')
else:
    print('', end='')
" 2>/dev/null
  else
    echo ""
  fi
}

_pool_json_write() {
  local file="$1" content="$2"
  local tmp="${file}.tmp.$$"
  printf '%s\n' "$content" > "$tmp" && mv "$tmp" "$file"
}

# ── Initialize pool ──

_pool_init() {
  [[ "$_POOL_INITIALIZED" == true ]] && return 0

  # Load keys from env or file
  if [[ -n "${RUNNER_API_KEYS:-}" ]]; then
    IFS=',' read -ra _POOL_KEYS <<< "$RUNNER_API_KEYS"
  elif [[ -n "${RUNNER_API_KEYS_FILE:-}" && -f "${RUNNER_API_KEYS_FILE}" ]]; then
    local line
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ -z "$line" || "$line" == \#* ]] && continue
      _POOL_KEYS+=("$line")
    done < "$RUNNER_API_KEYS_FILE"
  fi

  if [[ ${#_POOL_KEYS[@]} -eq 0 ]]; then
    _POOL_INITIALIZED=true
    return 0
  fi

  # State file
  local runner_name="${RUNNER_NAME:-default}"
  _POOL_STATE_FILE="${TMPDIR:-/tmp}/runner-credential-pool-${runner_name}.json"

  # Load or create state
  if [[ -f "$_POOL_STATE_FILE" ]]; then
    _POOL_LAST_INDEX=$(_pool_json_get "$_POOL_STATE_FILE" '.last_index')
    _POOL_LAST_INDEX="${_POOL_LAST_INDEX:-0}"
  else
    _pool_write_initial_state
  fi

  _POOL_INITIALIZED=true
}

_pool_write_initial_state() {
  local keys_json="["
  local i=0
  for key in "${_POOL_KEYS[@]}"; do
    [[ $i -gt 0 ]] && keys_json+=","
    local key_id
    key_id=$(_pool_key_id "$key")
    keys_json+="{\"key_id\":\"${key_id}\",\"request_count\":0,\"last_status\":0,\"last_status_at\":0,\"error_count\":0,\"cooldown_until\":0}"
    i=$((i + 1))
  done
  keys_json+="]"
  _pool_json_write "$_POOL_STATE_FILE" "{\"last_index\":0,\"keys\":${keys_json}}"
}

_pool_key_id() {
  local key="$1"
  local len=${#key}
  if [[ $len -le 8 ]]; then
    echo "$key"
  else
    echo "${key:0:4}...${key:$((len-4)):4}"
  fi
}

_pool_now() {
  date +%s
}

# ── Core functions ──

# pool_get_credential()
# Returns the next available API key based on strategy.
# Outputs the key to stdout. Returns 0 on success, 1 if no keys configured.
pool_get_credential() {
  _pool_init

  if [[ ${#_POOL_KEYS[@]} -eq 0 ]]; then
    return 1
  fi

  local strategy="${RUNNER_CREDENTIAL_STRATEGY:-round_robin}"
  local now
  now=$(_pool_now)
  local key_count=${#_POOL_KEYS[@]}

  case "$strategy" in
    round_robin)
      _pool_get_round_robin "$now" "$key_count"
      ;;
    least_used)
      _pool_get_least_used "$now" "$key_count"
      ;;
    *)
      _pool_get_round_robin "$now" "$key_count"
      ;;
  esac
}

_pool_get_round_robin() {
  local now="$1" key_count="$2"
  # Re-read from state file to handle subshell state loss (BUG-1 fix, Story 115.10)
  local start_idx="$_POOL_LAST_INDEX"
  if [[ -f "$_POOL_STATE_FILE" ]]; then
    local disk_idx
    disk_idx=$(_pool_json_get "$_POOL_STATE_FILE" '.last_index')
    start_idx="${disk_idx:-$start_idx}"
  fi
  local checked=0
  local idx="$start_idx"

  while [[ $checked -lt $key_count ]]; do
    local cooldown_until
    cooldown_until=$(_pool_json_get "$_POOL_STATE_FILE" ".keys[${idx}].cooldown_until")
    cooldown_until="${cooldown_until:-0}"

    if [[ "$cooldown_until" -le "$now" ]]; then
      _POOL_LAST_INDEX=$(( (idx + 1) % key_count ))
      _POOL_LAST_KEY="${_POOL_KEYS[$idx]}"
      _pool_update_last_index
      echo "${_POOL_KEYS[$idx]}"
      return 0
    fi

    idx=$(( (idx + 1) % key_count ))
    checked=$((checked + 1))
  done

  # All keys in cooldown — fallback to last used or first key
  _pool_fallback_key
}

_pool_get_least_used() {
  local now="$1" key_count="$2"
  local min_count=999999999
  local min_idx=-1

  local i=0
  while [[ $i -lt $key_count ]]; do
    local cooldown_until
    cooldown_until=$(_pool_json_get "$_POOL_STATE_FILE" ".keys[${i}].cooldown_until")
    cooldown_until="${cooldown_until:-0}"

    if [[ "$cooldown_until" -le "$now" ]]; then
      local req_count
      req_count=$(_pool_json_get "$_POOL_STATE_FILE" ".keys[${i}].request_count")
      req_count="${req_count:-0}"

      if [[ "$req_count" -lt "$min_count" ]]; then
        min_count="$req_count"
        min_idx=$i
      fi
    fi
    i=$((i + 1))
  done

  if [[ $min_idx -ge 0 ]]; then
    _POOL_LAST_KEY="${_POOL_KEYS[$min_idx]}"
    _pool_update_state_field "$min_idx" "request_count" "$((min_count + 1))"
    echo "${_POOL_KEYS[$min_idx]}"
    return 0
  fi

  # All in cooldown
  _pool_fallback_key
}

_pool_fallback_key() {
  echo "  [CREDENTIAL-POOL] WARNING: All keys in cooldown — using last available key" >&2
  if [[ -n "$_POOL_LAST_KEY" ]]; then
    echo "$_POOL_LAST_KEY"
  else
    echo "${_POOL_KEYS[0]}"
  fi
  return 0
}

_pool_update_last_index() {
  if [[ -f "$_POOL_STATE_FILE" ]] && command -v jq >/dev/null 2>&1; then
    local tmp="${_POOL_STATE_FILE}.tmp.$$"
    jq ".last_index = $_POOL_LAST_INDEX" "$_POOL_STATE_FILE" > "$tmp" 2>/dev/null && mv "$tmp" "$_POOL_STATE_FILE"
  elif [[ -f "$_POOL_STATE_FILE" ]] && command -v python3 >/dev/null 2>&1; then
    python3 -c "
import json
with open('$_POOL_STATE_FILE') as f: data = json.load(f)
data['last_index'] = $_POOL_LAST_INDEX
with open('$_POOL_STATE_FILE', 'w') as f: json.dump(data, f)
" 2>/dev/null
  fi
}

_pool_update_state_field() {
  local idx="$1" field="$2" value="$3"
  if [[ -f "$_POOL_STATE_FILE" ]] && command -v jq >/dev/null 2>&1; then
    local tmp="${_POOL_STATE_FILE}.tmp.$$"
    jq ".keys[${idx}].${field} = ${value}" "$_POOL_STATE_FILE" > "$tmp" 2>/dev/null && mv "$tmp" "$_POOL_STATE_FILE"
  elif [[ -f "$_POOL_STATE_FILE" ]] && command -v python3 >/dev/null 2>&1; then
    python3 -c "
import json
with open('$_POOL_STATE_FILE') as f: data = json.load(f)
data['keys'][${idx}]['${field}'] = ${value}
with open('$_POOL_STATE_FILE', 'w') as f: json.dump(data, f)
" 2>/dev/null
  fi
}

# pool_report_error(key_id_or_key, http_status)
# Marks a key with cooldown based on HTTP status code.
pool_report_error() {
  _pool_init
  local key_ref="$1"
  local http_status="$2"

  [[ ${#_POOL_KEYS[@]} -eq 0 ]] && return 0

  local idx
  idx=$(_pool_find_key_index "$key_ref")
  [[ "$idx" == "-1" ]] && return 0

  local now
  now=$(_pool_now)

  local cooldown_secs=0
  case "$http_status" in
    429) cooldown_secs="$_POOL_COOLDOWN_429" ;;
    401) cooldown_secs="$_POOL_COOLDOWN_401" ;;
    402) cooldown_secs="$_POOL_COOLDOWN_402" ;;
    *)   cooldown_secs=0 ;;
  esac

  local cooldown_until=$((now + cooldown_secs))
  local key_id
  key_id=$(_pool_key_id "${_POOL_KEYS[$idx]}")

  if [[ "$cooldown_secs" -gt 0 ]]; then
    echo "  [CREDENTIAL-POOL] Key ${key_id} got HTTP ${http_status} — cooldown ${cooldown_secs}s" >&2
  fi

  # Update state: increment error_count, set last_status, cooldown_until
  if [[ -f "$_POOL_STATE_FILE" ]] && command -v jq >/dev/null 2>&1; then
    local tmp="${_POOL_STATE_FILE}.tmp.$$"
    jq ".keys[${idx}].last_status = ${http_status} | .keys[${idx}].last_status_at = ${now} | .keys[${idx}].error_count = (.keys[${idx}].error_count + 1) | .keys[${idx}].cooldown_until = ${cooldown_until}" \
      "$_POOL_STATE_FILE" > "$tmp" 2>/dev/null && mv "$tmp" "$_POOL_STATE_FILE"
  elif [[ -f "$_POOL_STATE_FILE" ]] && command -v python3 >/dev/null 2>&1; then
    python3 -c "
import json
with open('$_POOL_STATE_FILE') as f: data = json.load(f)
k = data['keys'][${idx}]
k['last_status'] = ${http_status}
k['last_status_at'] = ${now}
k['error_count'] = k.get('error_count', 0) + 1
k['cooldown_until'] = ${cooldown_until}
with open('$_POOL_STATE_FILE', 'w') as f: json.dump(data, f)
" 2>/dev/null
  fi
}

# pool_report_success(key_id_or_key)
# Resets error counter for a key.
pool_report_success() {
  _pool_init
  local key_ref="$1"

  [[ ${#_POOL_KEYS[@]} -eq 0 ]] && return 0

  local idx
  idx=$(_pool_find_key_index "$key_ref")
  [[ "$idx" == "-1" ]] && return 0

  local now
  now=$(_pool_now)

  # Update state: reset error_count, set last_status=200, increment request_count
  if [[ -f "$_POOL_STATE_FILE" ]] && command -v jq >/dev/null 2>&1; then
    local tmp="${_POOL_STATE_FILE}.tmp.$$"
    jq ".keys[${idx}].last_status = 200 | .keys[${idx}].last_status_at = ${now} | .keys[${idx}].error_count = 0 | .keys[${idx}].cooldown_until = 0 | .keys[${idx}].request_count = (.keys[${idx}].request_count + 1)" \
      "$_POOL_STATE_FILE" > "$tmp" 2>/dev/null && mv "$tmp" "$_POOL_STATE_FILE"
  elif [[ -f "$_POOL_STATE_FILE" ]] && command -v python3 >/dev/null 2>&1; then
    python3 -c "
import json
with open('$_POOL_STATE_FILE') as f: data = json.load(f)
k = data['keys'][${idx}]
k['last_status'] = 200
k['last_status_at'] = ${now}
k['error_count'] = 0
k['cooldown_until'] = 0
k['request_count'] = k.get('request_count', 0) + 1
with open('$_POOL_STATE_FILE', 'w') as f: json.dump(data, f)
" 2>/dev/null
  fi
}

_pool_find_key_index() {
  local ref="$1"
  local i=0
  for key in "${_POOL_KEYS[@]}"; do
    if [[ "$key" == "$ref" ]]; then
      echo "$i"
      return 0
    fi
    local kid
    kid=$(_pool_key_id "$key")
    if [[ "$kid" == "$ref" ]]; then
      echo "$i"
      return 0
    fi
    i=$((i + 1))
  done
  echo "-1"
}
