#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
REGISTRY_FILE="$SCRIPT_DIR/runner-registry.yaml"

TARGET_PATH=""
VALIDATE_ALL="false"
OUTPUT_JSON="false"
VERBOSE="false"

show_help() {
  cat <<EOF
validate-runner.sh — valida integração runner-lib

Usage:
  $(basename "$0") <path>
  $(basename "$0") --all [--json] [--verbose]

Flags:
  --all      Valida todos os runners registrados
  --json     Saída JSON
  --verbose  Inclui checks e findings
EOF
}

registry_rows() {
  # Fast path: node + js-yaml
  if node -e "require('js-yaml')" 2>/dev/null; then
    node - "$REGISTRY_FILE" <<'NODE'
const fs = require("fs");
const yaml = require("js-yaml");
const file = process.argv[2];
const data = yaml.load(fs.readFileSync(file, "utf8")) || {};
for (const runner of data.runners || []) {
  console.log([
    runner.id || "",
    runner.path || "",
    runner.squad || "",
    runner.type || ""
  ].join("\t"));
}
NODE
    return
  fi
  # Fallback: python3 + PyYAML
  if python3 -c "import yaml" 2>/dev/null; then
    python3 -c "
import yaml, sys
with open(sys.argv[1]) as f:
    data = yaml.safe_load(f) or {}
for r in data.get('runners', []):
    print('\t'.join([r.get('id',''), r.get('path',''), r.get('squad',''), r.get('type','')]))
" "$REGISTRY_FILE"
    return
  fi
  # Last resort: awk (handles simple flat YAML)
  awk '
    /^ *- id:/ {
      if (id != "") printf "%s\t%s\t%s\t%s\n", id, path, squad, type
      id=""; path=""; squad=""; type=""
      sub(/.*- id: */, ""); id=$0; next
    }
    /^ *path:/  { sub(/.*path: */, ""); path=$0 }
    /^ *squad:/ { sub(/.*squad: */, ""); squad=$0 }
    /^ *type:/  { sub(/.*type: */, ""); type=$0 }
    END { if (id != "") printf "%s\t%s\t%s\t%s\n", id, path, squad, type }
  ' "$REGISTRY_FILE"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --all)
        VALIDATE_ALL="true"
        shift
        ;;
      --json)
        OUTPUT_JSON="true"
        shift
        ;;
      --verbose)
        VERBOSE="true"
        shift
        ;;
      --help|-h)
        show_help
        exit 0
        ;;
      *)
        TARGET_PATH="$1"
        shift
        ;;
    esac
  done

  if [[ "$VALIDATE_ALL" != "true" && -z "$TARGET_PATH" ]]; then
    show_help
    exit 1
  fi
}

validate_one() {
  local runner_id="$1"
  local path="$2"
  local squad="$3"
  local runner_type="$4"

  python3 - "$REPO_ROOT/$path" "$runner_id" "$squad" "$runner_type" "$REPO_ROOT" <<'PY'
import json
import re
import subprocess
import sys
from pathlib import Path

path = Path(sys.argv[1])
runner_id = sys.argv[2]
squad = sys.argv[3]
runner_type = sys.argv[4]
repo_root = Path(sys.argv[5]).resolve()

result = {
    "id": runner_id or path.stem,
    "path": str(path),
    "squad": squad,
    "type": runner_type,
    "checks": [],
    "errors": [],
    "warnings": [],
    "info": [],
}

if not path.exists():
    result["errors"].append("Runner file not found")
    result["integration_score"] = "minimal"
    print(json.dumps(result))
    sys.exit(0)

def add_check(name, passed, severity, detail):
    result["checks"].append({
        "name": name,
        "passed": passed,
        "severity": severity,
        "detail": detail,
    })
    if passed:
        return
    if severity == "error":
        if detail not in result["errors"]:
            result["errors"].append(detail)
    elif severity == "warning":
        if detail not in result["warnings"]:
            result["warnings"].append(detail)
    else:
        if detail not in result["info"]:
            result["info"].append(detail)

def add_unique(bucket, detail):
    if detail not in result[bucket]:
        result[bucket].append(detail)

def normalize_source_target(raw_target, current_file):
    target = raw_target.strip()
    if not target:
        return None
    if "#" in target:
        target = target.split("#", 1)[0].strip()
    if (target.startswith('"') and target.endswith('"')) or (target.startswith("'") and target.endswith("'")):
        target = target[1:-1]

    script_dir = str(current_file.parent.resolve())
    replacements = {
        "$SCRIPT_DIR": script_dir,
        "${SCRIPT_DIR}": script_dir,
        "$RUNNER_LIB_DIR": str((repo_root / "infrastructure/scripts/runner-lib").resolve()),
        "${RUNNER_LIB_DIR}": str((repo_root / "infrastructure/scripts/runner-lib").resolve()),
        "$REPO_ROOT": str(repo_root),
        "${REPO_ROOT}": str(repo_root),
    }
    for source, value in replacements.items():
        target = target.replace(source, value)

    target_path = Path(target)
    if not target_path.is_absolute():
        target_path = (current_file.parent / target_path).resolve()
    else:
        target_path = target_path.resolve()
    return target_path

def collect_analysis_files(entrypoint):
    visited = set()
    ordered_files = []
    stack = [entrypoint.resolve()]
    source_pattern = re.compile(r'^\s*(?:source|\.)\s+([^\s;]+)')
    runner_lib_root = (repo_root / "infrastructure/scripts/runner-lib").resolve()

    while stack:
        current = stack.pop()
        if current in visited or not current.exists():
            continue
        visited.add(current)
        ordered_files.append(current)

        try:
            text = current.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for line in text.splitlines():
            match = source_pattern.match(line)
            if not match:
                continue
            target = normalize_source_target(match.group(1), current)
            if target is None or not target.exists():
                continue
            try:
                target.relative_to(repo_root)
            except ValueError:
                continue
            try:
                target.relative_to(runner_lib_root)
                continue
            except ValueError:
                pass
            if target not in visited:
                stack.append(target)

    return ordered_files

analysis_files = collect_analysis_files(path)
main_content = path.read_text(encoding="utf-8", errors="ignore")
content = "\n".join(
    file.read_text(encoding="utf-8", errors="ignore")
    for file in analysis_files
)
claude_lines = [line.strip() for line in main_content.splitlines() if "claude " in line and "-p" in line]

bootstrap = bool(re.search(r"pipeline-bootstrap\.sh|loader\.sh", main_content))
runtime = bool(re.search(r"RUNNER_LIB_RUNTIME=true|\brun_llm_prompt(?:_with_replan)?\b", main_content))
hardcoded_claude = bool(re.search(r"(^|\s)claude\s+-p\b", main_content, re.MULTILINE))
trap_exit = bool(re.search(r"trap\s+.*\bEXIT\b", main_content))
safe_claude = all("--dangerously-skip-permissions" in line for line in claude_lines) if claude_lines else True

add_check("bootstrap", bootstrap, "error", "Runner must source pipeline-bootstrap.sh or loader.sh")
add_check("runtime", runtime, "error", "Runner must use RUNNER_LIB_RUNTIME=true or run_llm_prompt()")
add_check("no_hardcoded_claude", not hardcoded_claude, "error", "Runner still contains hardcoded `claude -p` calls")
add_check("trap_exit", trap_exit, "error", "Runner must declare trap ... EXIT")
add_check("permissions_flag", safe_claude, "error", "Claude invocations must include --dangerously-skip-permissions")

state_manager = bool(re.search(r"\bstate_(init|update|phase_update|complete)\b", content))
metrics = bool(re.search(r"\brecord_metrics\b|METRICS_FILE=", content))
session = bool(re.search(r"\bsession_(start|end)\b|SESSION_TRACKING=true", content))
cost_cap = bool(re.search(r"\bcheck_cost_cap\b", content))
headless = bool(re.search(r"\bfilter_llm_output\b|\btruncate_prior_context\b", content))

add_check("state_manager", state_manager, "warning", "Runner does not use state-manager helpers")
add_check("metrics", metrics, "warning", "Runner does not expose explicit metrics integration")
add_check("session_mgr", session, "warning", "Runner does not expose explicit session tracking")
add_check("cost_cap", cost_cap, "warning", "Runner does not guard max cost")
add_check("headless_guard", headless, "warning", "Runner does not use headless guard helpers")

cascade = bool(re.search(r"\bcascade_run\b", content))
hooks = bool(re.search(r"\bhooks_(load|run_pre|run_post)\b", content))
evaluator = bool(re.search(r"\bevaluate_phase_output\b", content))
context = bool(re.search(r"\bread_focused_context\b", content))

if not cascade:
    add_unique("info", "Runner does not use cascade_run()")
if not hooks:
    add_unique("info", "Runner does not use hooks.sh helpers")
if not evaluator:
    add_unique("info", "Runner does not use evaluate_phase_output()")
if not context:
    add_unique("info", "Runner does not use read_focused_context()")

if re.search(r'>\s*["\']?\$STATE_FILE\.tmp["\']?\s*&&\s*mv\s*["\']?\$STATE_FILE\.tmp["\']?\s*["\']?\$STATE_FILE["\']?', content):
    add_unique("warnings", "Runner still updates state with jq redirection instead of state_update()")

if not metrics:
    add_unique("warnings", "No record_metrics() or METRICS_FILE found")

# ── Smoke test existence check (Story 101.16) ──
# AC7: Check that a smoke test exists for this runner
# AC8: WARNING only (not BLOCK) so legacy runners without tests are not broken
# AC9: If smoke test exists but fails, validate-runner must report ERROR
smoke_test_dir = repo_root / "infrastructure" / "scripts" / "runner-lib" / "tests" / "smoke"
smoke_test_path = smoke_test_dir / f"test-{result['id']}.sh"
has_smoke_test = smoke_test_path.exists()
add_check(
    "smoke_test_exists",
    has_smoke_test,
    "warning",
    f"No smoke test found at tests/smoke/test-{result['id']}.sh (create via test-runner-template.sh)"
)
if has_smoke_test:
    try:
        smoke_run = subprocess.run(
            ["bash", str(smoke_test_path)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=90,
        )
        add_check(
            "smoke_test_passes",
            smoke_run.returncode == 0,
            "error",
            f"Smoke test failed at tests/smoke/test-{result['id']}.sh"
        )
        if smoke_run.returncode != 0:
            tail = (smoke_run.stdout or smoke_run.stderr or "").strip().splitlines()[-6:]
            if tail:
                add_unique("info", "Smoke test tail: " + " | ".join(tail))
    except subprocess.TimeoutExpired:
        add_check(
            "smoke_test_passes",
            False,
            "error",
            f"Smoke test timed out at tests/smoke/test-{result['id']}.sh"
        )

must_ok = len(result["errors"]) == 0
warning_passes = len([c for c in result["checks"] if c["severity"] == "warning" and c["passed"]])
warning_count = len(result["warnings"])

if must_ok and warning_count == 0 and warning_passes >= 4:
    score = "full"
elif must_ok and warning_passes >= 2:
    score = "partial"
else:
    score = "minimal"

result["analyzed_files"] = [str(file) for file in analysis_files]
result["integration_score"] = score
print(json.dumps(result))
PY
}

render_results() {
  local results_file="$1"
  local mode="$2"
  python3 - "$results_file" "$mode" "$VERBOSE" <<'PY'
import json
import sys

path, mode, verbose = sys.argv[1:4]
items = [json.loads(line) for line in open(path) if line.strip()]

if mode == "json":
    print(json.dumps(items, indent=2))
    sys.exit(0)

print(f"{'Runner':<18} {'Score':<8} {'Errors':>6} {'Warn':>6}  Path")
print("-" * 96)
for item in items:
    print(f"{item['id']:<18} {item['integration_score']:<8} {len(item['errors']):>6} {len(item['warnings']):>6}  {item['path']}")
    if verbose == "true":
        check_error_details = {check["detail"] for check in item["checks"] if not check["passed"] and check["severity"] == "error"}
        check_warning_details = {check["detail"] for check in item["checks"] if not check["passed"] and check["severity"] == "warning"}
        for check in item["checks"]:
            status = "PASS" if check["passed"] else check["severity"].upper()
            print(f"  - [{status}] {check['name']}: {check['detail']}")
        for extra in item["errors"]:
            if extra not in check_error_details:
                print(f"  - [ERROR] {extra}")
        for extra in item["warnings"]:
            if extra not in check_warning_details:
                print(f"  - [WARN] {extra}")
        for extra in item["info"]:
            print(f"  - [INFO] {extra}")
        for analyzed_file in item.get("analyzed_files", []):
            print(f"  - [FILE] {analyzed_file}")
PY
}

main() {
  parse_args "$@"

  local results_file
  results_file="$(mktemp)"

  if [[ "$VALIDATE_ALL" == "true" ]]; then
    while IFS=$'\t' read -r runner_id path squad runner_type; do
      [[ -z "$runner_id" ]] && continue
      validate_one "$runner_id" "$path" "$squad" "$runner_type" >> "$results_file"
    done < <(registry_rows)
  else
    validate_one "$(basename "$TARGET_PATH" .sh)" "$TARGET_PATH" "unknown" "unknown" >> "$results_file"
  fi

  if [[ "$OUTPUT_JSON" == "true" ]]; then
    render_results "$results_file" "json"
  else
    render_results "$results_file" "table"
  fi

  if python3 - "$results_file" <<'PY'
import json
import sys
items = [json.loads(line) for line in open(sys.argv[1]) if line.strip()]
sys.exit(1 if any(item["errors"] for item in items) else 0)
PY
  then
    rm -f "$results_file"
    exit 0
  fi

  rm -f "$results_file"
  exit 1
}

main "$@"
