#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
REGISTRY_FILE="$SCRIPT_DIR/runner-registry.yaml"
COMPARE_RUNS="$SCRIPT_DIR/compare-runs.sh"
VALIDATE_RUNNER="$SCRIPT_DIR/validate-runner.sh"
OUTPUT_JSON="false"

show_help() {
  cat <<EOF
runner-metrics.sh — status e métricas dos runners

Usage:
  $(basename "$0") status [--json]
  $(basename "$0") cost <runner-id> [--json]
  $(basename "$0") runs <runner-id> [--json]
  $(basename "$0") integration [runner-id] [--json]
  $(basename "$0") compare <runner-id> [--json]
EOF
}

registry_entry() {
  local runner_id="$1"
  # Fast path: node + js-yaml
  if node -e "require('js-yaml')" 2>/dev/null; then
    node - "$REGISTRY_FILE" "$runner_id" <<'NODE'
const fs = require("fs");
const yaml = require("js-yaml");
const [file, runnerId] = process.argv.slice(2);
const data = yaml.load(fs.readFileSync(file, "utf8")) || {};
const runner = (data.runners || []).find((item) => item.id === runnerId);
if (!runner) process.exit(1);
console.log(JSON.stringify(runner));
NODE
    return
  fi
  # Fallback: python3 + PyYAML
  if python3 -c "import yaml, json" 2>/dev/null; then
    python3 -c "
import yaml, json, sys
with open(sys.argv[1]) as f:
    data = yaml.safe_load(f) or {}
runner = next((r for r in data.get('runners', []) if r.get('id') == sys.argv[2]), None)
if not runner: sys.exit(1)
print(json.dumps(runner))
" "$REGISTRY_FILE" "$runner_id"
    return
  fi
  echo '{"error":"no yaml parser available (install js-yaml or PyYAML)"}' >&2
  return 1
}

json_flag() {
  if [[ "$OUTPUT_JSON" == "true" ]]; then
    echo "--json"
  fi
}

status_cmd() {
  local output
  if ! output="$("$VALIDATE_RUNNER" --all $(json_flag) 2>&1)"; then
    printf '%s\n' "$output"
    return 0
  fi
  printf '%s\n' "$output"
}

cost_cmd() {
  local runner_id="$1"
  local entry
  entry="$(registry_entry "$runner_id")"
  python3 - "$entry" "$REPO_ROOT" "$OUTPUT_JSON" <<'PY'
import glob
import json
import sys
from pathlib import Path

entry = json.loads(sys.argv[1])
repo_root = Path(sys.argv[2])
as_json = sys.argv[3] == "true"

pattern = entry.get("metrics_glob", "")
files = sorted(glob.glob(str(repo_root / pattern), recursive=True))
total_cost = 0.0
total_tokens = 0
records = 0

for file in files:
    for line in Path(file).read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        total_cost += float(row.get("cost_usd", 0))
        total_tokens += int(row.get("input_tokens", 0)) + int(row.get("output_tokens", 0))
        records += 1

payload = {
    "runner": entry["id"],
    "files": len(files),
    "records": records,
    "total_cost_usd": round(total_cost, 6),
    "total_tokens": total_tokens,
}

if as_json:
    print(json.dumps(payload, indent=2))
else:
    print(f"runner: {payload['runner']}")
    print(f"files: {payload['files']}")
    print(f"records: {payload['records']}")
    print(f"total_cost_usd: {payload['total_cost_usd']}")
    print(f"total_tokens: {payload['total_tokens']}")
PY
}

runs_cmd() {
  local runner_id="$1"
  local entry
  entry="$(registry_entry "$runner_id")"
  python3 - "$entry" "$OUTPUT_JSON" <<'PY'
import json
import os
import sys
from pathlib import Path

entry = json.loads(sys.argv[1])
as_json = sys.argv[2] == "true"
session_dir = Path(os.environ.get("RUNNER_STATE_DIR", f"{os.environ.get('TMPDIR', '/tmp')}/runner-sessions"))
runs = []

for file in sorted(session_dir.glob("sess-*.json")):
    try:
        data = json.loads(file.read_text())
    except Exception:
        continue
    if data.get("squad") != entry.get("squad"):
        continue
    runs.append({
        "id": data.get("id"),
        "phase": data.get("phase"),
        "status": data.get("status"),
        "started_at": data.get("started_at"),
        "model": data.get("model"),
        "runtime": data.get("runtime"),
    })

runs = sorted(runs, key=lambda item: item.get("started_at") or "", reverse=True)[:10]

if as_json:
    print(json.dumps({"runner": entry["id"], "runs": runs}, indent=2))
else:
    print(f"runner: {entry['id']}")
    if not runs:
        print("runs: none")
    for run in runs:
        print(f"- {run['started_at']} {run['status']} {run['phase']} {run['runtime']}/{run['model']}")
PY
}

integration_cmd() {
  local runner_id="${1:-}"
  if [[ -n "$runner_id" ]]; then
    local entry
    entry="$(registry_entry "$runner_id")"
    local path
    path="$(python3 - "$entry" <<'PY'
import json
import sys
print(json.loads(sys.argv[1])["path"])
PY
)"
    "$VALIDATE_RUNNER" "$path" $(json_flag)
    return
  fi

  "$VALIDATE_RUNNER" --all $(json_flag)
}

compare_cmd() {
  local runner_id="$1"
  local entry
  entry="$(registry_entry "$runner_id")"
  local runs_dir
  runs_dir="$(python3 - "$entry" <<'PY'
import json
import sys
print(json.loads(sys.argv[1]).get("runs_dir", ""))
PY
)"

  if [[ -z "$runs_dir" ]]; then
    echo "No runs_dir registered for $runner_id" >&2
    exit 1
  fi

  "$COMPARE_RUNS" "$runs_dir" $(json_flag)
}

main() {
  local command="${1:-}"
  shift || true

  case "${1:-}" in
    --json)
      OUTPUT_JSON="true"
      shift
      ;;
  esac

  case "$command" in
    status)
      if [[ "${1:-}" == "--json" ]]; then
        OUTPUT_JSON="true"
      fi
      status_cmd
      ;;
    cost)
      [[ $# -lt 1 ]] && show_help && exit 1
      local runner_id="$1"
      shift
      [[ "${1:-}" == "--json" ]] && OUTPUT_JSON="true"
      cost_cmd "$runner_id"
      ;;
    runs)
      [[ $# -lt 1 ]] && show_help && exit 1
      local runner_id="$1"
      shift
      [[ "${1:-}" == "--json" ]] && OUTPUT_JSON="true"
      runs_cmd "$runner_id"
      ;;
    integration)
      local runner_id="${1:-}"
      if [[ "${2:-}" == "--json" || "${1:-}" == "--json" ]]; then
        OUTPUT_JSON="true"
      fi
      if [[ "$runner_id" == "--json" ]]; then
        runner_id=""
      fi
      integration_cmd "$runner_id"
      ;;
    compare)
      [[ $# -lt 1 ]] && show_help && exit 1
      local runner_id="$1"
      shift
      [[ "${1:-}" == "--json" ]] && OUTPUT_JSON="true"
      compare_cmd "$runner_id"
      ;;
    --help|-h|"")
      show_help
      ;;
    *)
      echo "Unknown command: $command" >&2
      show_help
      exit 1
      ;;
  esac
}

main "$@"
