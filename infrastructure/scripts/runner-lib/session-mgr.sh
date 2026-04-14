#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER-LIB — Session Manager
# ═══════════════════════════════════════════════════════════════
# Tracks, lists, monitors and cancels LLM sessions in execution.
# Replaces fire-and-forget with full session lifecycle visibility.
#
# Functions:
#   session_start  — Register a new session (returns session_id)
#   session_end    — Mark session as completed/failed
#   session_list   — List all sessions with formatted table
#   session_kill   — SIGTERM a running session
#   session_log    — Tail session log file
#   session_info   — Show full session metadata
#   session_cleanup — Archive old completed/killed sessions
#
# Usage:
#   SESSION_ID=$(session_start "mmos" "phase_3" "tim" "haiku" "claude" "/tmp/log.txt")
#   # ... do work ...
#   session_end "$SESSION_ID" 0  # exit_code=0
#
# Story: RUNNER-1.2 (Session Manager)

# ═══════════════════════════════════════════════════════════════
# Configuration (overridable by caller)
# ═══════════════════════════════════════════════════════════════
# Paths are resolved dynamically so env changes take effect.
# ARCHIVE_AFTER_MINUTES and MAX_CONCURRENT are read dynamically from env vars
# RUNNER_ARCHIVE_AFTER (default: 60), RUNNER_MAX_CONCURRENT (default: 0 = unlimited)

_session_dir()         { echo "${RUNNER_STATE_DIR:-${TMPDIR:-/tmp}/runner-sessions}"; }
_session_log_dir()     { echo "$(_session_dir)/logs"; }
_session_archive_dir() { echo "$(_session_dir)/archive"; }

# Ensure directories exist
_session_init_dirs() {
  mkdir -p "$(_session_dir)" "$(_session_log_dir)" "$(_session_archive_dir)"
}

# ═══════════════════════════════════════════════════════════════
# session_start — Register a new LLM session
# ═══════════════════════════════════════════════════════════════
# Args: $1=squad $2=phase $3=agent $4=model $5=runtime $6=log_file [metadata_json]
# Returns: session_id on stdout, 0=ok, 1=policy blocked
session_start() {
  local squad="${1:?session_start: squad required}"
  local phase="${2:?session_start: phase required}"
  local agent="${3:-unknown}"
  local model="${4:-unknown}"
  local runtime="${5:-unknown}"
  local log_file="${6:-}"
  local _empty_json='{}'
  local metadata="${7:-$_empty_json}"

  _session_init_dirs

  # Policy: max_concurrent
  local _max_concurrent="${RUNNER_MAX_CONCURRENT:-0}"
  if [[ "$_max_concurrent" -gt 0 ]]; then
    local active_count
    active_count=$(_session_count_active)
    if [[ "$active_count" -ge "$_max_concurrent" ]]; then
      echo "[POLICY] max_concurrent=$_max_concurrent reached ($active_count active). Retry later or increase limit." >&2
      return 1
    fi
  fi

  # Generate session ID
  local ts
  ts=$(date +%Y%m%d-%H%M%S)
  local session_id="sess-${ts}-$$-${squad}-${agent}"

  # Default log file if not provided
  if [[ -z "$log_file" ]]; then
    log_file="$(_session_log_dir)/${session_id}.log"
  fi

  # Create session file
  local session_file="$(_session_dir)/${session_id}.json"
  local now
  now=$(date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')

  cat > "$session_file" << SESSIONEOF
{
  "id": "${session_id}",
  "pid": $$,
  "squad": "${squad}",
  "phase": "${phase}",
  "agent": "${agent}",
  "model": "${model}",
  "runtime": "${runtime}",
  "log_file": "${log_file}",
  "started_at": "${now}",
  "ended_at": null,
  "status": "running",
  "exit_code": null,
  "tokens_estimated": null,
  "metadata": ${metadata}
}
SESSIONEOF

  echo "$session_id"
  return 0
}

# ═══════════════════════════════════════════════════════════════
# session_end — Mark session as completed/failed
# ═══════════════════════════════════════════════════════════════
# Args: $1=session_id $2=exit_code [tokens_estimated]
session_end() {
  local session_id="${1:?session_end: session_id required}"
  local exit_code="${2:-0}"
  local tokens_est="${3:-null}"

  local session_file="$(_session_dir)/${session_id}.json"
  if [[ ! -f "$session_file" ]]; then
    echo "[session] Session not found: $session_id" >&2
    return 1
  fi

  local status="completed"
  [[ "$exit_code" -ne 0 ]] && status="failed"

  local now
  now=$(date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')

  # Update session file via python (safe JSON manipulation)
  python3 - "$session_file" "$status" "$exit_code" "$tokens_est" "$now" << 'PYEOF'
import json, sys
path, status, exit_code, tokens, ended_at = sys.argv[1:6]
with open(path) as f:
    data = json.load(f)
data["status"] = status
data["exit_code"] = int(exit_code)
data["ended_at"] = ended_at
data["tokens_estimated"] = int(tokens) if tokens != "null" else None
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
PYEOF
}

# ═══════════════════════════════════════════════════════════════
# session_list — Show all sessions as formatted table
# ═══════════════════════════════════════════════════════════════
# Args: [--all] (include archived, default: active + recent only)
session_list() {
  local show_all="${1:-}"
  _session_init_dirs

  local search_dirs=("$(_session_dir)")
  [[ "$show_all" == "--all" ]] && search_dirs+=("$(_session_archive_dir)")

  # Collect session files
  local files=()
  for dir in "${search_dirs[@]}"; do
    while IFS= read -r -d '' f; do
      files+=("$f")
    done < <(find "$dir" -maxdepth 1 -name "sess-*.json" -print0 2>/dev/null)
  done

  if [[ ${#files[@]} -eq 0 ]]; then
    echo "No sessions found." >&2
    return 0
  fi

  # Header
  printf "%-42s %-12s %-14s %-8s %-8s %-10s %-10s\n" \
    "ID" "Squad" "Phase" "Agent" "Model" "Duration" "Status"
  printf "%-42s %-12s %-14s %-8s %-8s %-10s %-10s\n" \
    "$(printf '%0.s─' {1..42})" "$(printf '%0.s─' {1..12})" "$(printf '%0.s─' {1..14})" \
    "$(printf '%0.s─' {1..8})" "$(printf '%0.s─' {1..8})" "$(printf '%0.s─' {1..10})" "$(printf '%0.s─' {1..10})"

  # Rows
  for f in "${files[@]}"; do
    python3 - "$f" << 'PYEOF'
import json, sys
from datetime import datetime, timezone

path = sys.argv[1]
try:
    with open(path) as f:
        d = json.load(f)
except:
    sys.exit(0)

# Calculate duration
started = d.get("started_at", "")
ended = d.get("ended_at")
duration = "—"
try:
    start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
    if ended and ended != "null":
        end_dt = datetime.fromisoformat(ended.replace("Z", "+00:00"))
    else:
        end_dt = datetime.now(timezone.utc)
    delta = end_dt - start_dt
    secs = int(delta.total_seconds())
    if secs < 60:
        duration = f"{secs}s"
    elif secs < 3600:
        duration = f"{secs // 60}m {secs % 60}s"
    else:
        duration = f"{secs // 3600}h {(secs % 3600) // 60}m"
except:
    pass

# Status with indicator
status = d.get("status", "unknown")
indicator = {"running": "▶", "completed": "✓", "failed": "✗", "killed": "☠", "archived": "📦"}.get(status, "?")

print(f'{d.get("id","?"):<42} {d.get("squad","?"):<12} {d.get("phase","?"):<14} {d.get("agent","?"):<8} {d.get("model","?"):<8} {duration:<10} {indicator} {status}')
PYEOF
  done
}

# ═══════════════════════════════════════════════════════════════
# session_kill — Send SIGTERM to a running session
# ═══════════════════════════════════════════════════════════════
# Args: $1=session_id
session_kill() {
  local session_id="${1:?session_kill: session_id required}"
  local session_file="$(_session_dir)/${session_id}.json"

  if [[ ! -f "$session_file" ]]; then
    echo "[session] Session not found: $session_id" >&2
    return 1
  fi

  local pid status
  pid=$(python3 -c "import json; d=json.load(open('$session_file')); print(d.get('pid',0))")
  status=$(python3 -c "import json; d=json.load(open('$session_file')); print(d.get('status','unknown'))")

  if [[ "$status" != "running" ]]; then
    echo "[session] Session $session_id is not running (status: $status)" >&2
    return 1
  fi

  # Send SIGTERM
  if kill -0 "$pid" 2>/dev/null; then
    kill -TERM "$pid" 2>/dev/null
    echo "[session] SIGTERM sent to PID $pid (session: $session_id)" >&2
  else
    echo "[session] PID $pid not found (process already ended)" >&2
  fi

  # Update status
  local now
  now=$(date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')
  python3 - "$session_file" "$now" << 'PYEOF'
import json, sys
path, ended_at = sys.argv[1:3]
with open(path) as f:
    data = json.load(f)
data["status"] = "killed"
data["ended_at"] = ended_at
data["exit_code"] = 143  # SIGTERM
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
PYEOF

  return 0
}

# ═══════════════════════════════════════════════════════════════
# session_log — Tail the log file of a session
# ═══════════════════════════════════════════════════════════════
# Args: $1=session_id [--follow|-f]
session_log() {
  local session_id="${1:?session_log: session_id required}"
  local follow="${2:-}"
  local session_file="$(_session_dir)/${session_id}.json"

  if [[ ! -f "$session_file" ]]; then
    echo "[session] Session not found: $session_id" >&2
    return 1
  fi

  local log_file
  log_file=$(python3 -c "import json; print(json.load(open('$session_file')).get('log_file',''))")

  if [[ -z "$log_file" || ! -f "$log_file" ]]; then
    echo "[session] Log file not found: $log_file" >&2
    return 1
  fi

  if [[ "$follow" == "--follow" || "$follow" == "-f" ]]; then
    tail -f "$log_file"
  else
    tail -50 "$log_file"
  fi
}

# ═══════════════════════════════════════════════════════════════
# session_info — Show full metadata for a session
# ═══════════════════════════════════════════════════════════════
# Args: $1=session_id
session_info() {
  local session_id="${1:?session_info: session_id required}"

  # Search both active and archive
  local session_file="$(_session_dir)/${session_id}.json"
  [[ ! -f "$session_file" ]] && session_file="$(_session_archive_dir)/${session_id}.json"

  if [[ ! -f "$session_file" ]]; then
    echo "[session] Session not found: $session_id" >&2
    return 1
  fi

  python3 - "$session_file" << 'PYEOF'
import json, sys
from datetime import datetime, timezone

path = sys.argv[1]
with open(path) as f:
    d = json.load(f)

# Duration
started = d.get("started_at", "")
ended = d.get("ended_at")
duration = "—"
try:
    start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
    if ended and ended != "null":
        end_dt = datetime.fromisoformat(ended.replace("Z", "+00:00"))
    else:
        end_dt = datetime.now(timezone.utc)
    delta = end_dt - start_dt
    secs = int(delta.total_seconds())
    if secs < 60:
        duration = f"{secs}s"
    elif secs < 3600:
        duration = f"{secs // 60}m {secs % 60}s"
    else:
        duration = f"{secs // 3600}h {(secs % 3600) // 60}m"
except:
    pass

status = d.get("status", "unknown")
indicator = {"running": "▶", "completed": "✓", "failed": "✗", "killed": "☠", "archived": "📦"}.get(status, "?")

print(f'══════════════════════════════════════════')
print(f'  Session: {d.get("id")}')
print(f'══════════════════════════════════════════')
print(f'  Status:     {indicator} {status}')
print(f'  PID:        {d.get("pid")}')
print(f'  Squad:      {d.get("squad")}')
print(f'  Phase:      {d.get("phase")}')
print(f'  Agent:      {d.get("agent")}')
print(f'  Model:      {d.get("model")}')
print(f'  Runtime:    {d.get("runtime")}')
print(f'  Started:    {started}')
print(f'  Ended:      {ended or "—"}')
print(f'  Duration:   {duration}')
print(f'  Exit Code:  {d.get("exit_code", "—")}')
print(f'  Tokens Est: {d.get("tokens_estimated", "—")}')
print(f'  Log File:   {d.get("log_file", "—")}')
meta = d.get("metadata", {})
if meta and meta != {}:
    print(f'  Metadata:   {json.dumps(meta)}')
print(f'══════════════════════════════════════════')
PYEOF
}

# ═══════════════════════════════════════════════════════════════
# session_cleanup — Archive completed/killed sessions
# ═══════════════════════════════════════════════════════════════
# Archives sessions older than ARCHIVE_AFTER_MINUTES.
# Called automatically via trap or manually.
session_cleanup() {
  _session_init_dirs

  local now_epoch
  now_epoch=$(date +%s)
  local _archive_after="${RUNNER_ARCHIVE_AFTER:-60}"
  local threshold=$((_archive_after * 60))
  local archived=0

  for f in "$(_session_dir)"/sess-*.json; do
    [[ -f "$f" ]] || continue

    local status ended_at
    status=$(python3 -c "import json; print(json.load(open('$f')).get('status',''))" 2>/dev/null)

    # Only archive completed, failed, or killed sessions
    case "$status" in
      completed|failed|killed) ;;
      *) continue ;;
    esac

    ended_at=$(python3 -c "
import json
from datetime import datetime, timezone
d = json.load(open('$f'))
ea = d.get('ended_at')
if ea and ea != 'null':
    dt = datetime.fromisoformat(ea.replace('Z', '+00:00'))
    print(int(dt.timestamp()))
else:
    print(0)
" 2>/dev/null)

    if [[ -n "$ended_at" && "$ended_at" != "0" ]]; then
      local age=$((now_epoch - ended_at))
      if [[ "$age" -ge "$threshold" ]]; then
        mv "$f" "$(_session_archive_dir)/"
        archived=$((archived + 1))
      fi
    fi
  done

  [[ "$archived" -gt 0 ]] && echo "[session] Archived $archived session(s)" >&2
}

# ═══════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════

# Count active (running) sessions
_session_count_active() {
  local count=0
  for f in "$(_session_dir)"/sess-*.json; do
    [[ -f "$f" ]] || continue
    local s
    s=$(python3 -c "import json; print(json.load(open('$f')).get('status',''))" 2>/dev/null)
    [[ "$s" == "running" ]] && count=$((count + 1))
  done
  echo "$count"
}
