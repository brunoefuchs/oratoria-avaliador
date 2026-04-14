#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER-LIB — Generic Post-Phase Assertions
# ═══════════════════════════════════════════════════════════════
# Shared validation functions for any LLM runner output.
# YAML validity, required fields, file size, markdown structure.
#
# Squad-specific assertions remain in each squad's lib/.
# This file contains ONLY format-agnostic checks.

# ═══════════════════════════════════════════════════════════════
# Schema Constants — for use with assert_yaml_schema()
# Format: "field:type,field:type,..."
# Story: RUNNER-1.3 (Runner Hardening)
# ═══════════════════════════════════════════════════════════════
SCHEMA_SCORE_CARD="validation:dict,overall:dict,dimensions:dict"
SCHEMA_PHASE_HANDOFF="from_phase:str,to_phase:str,status:str"
SCHEMA_STATE="current_phase:str,status:str"
SCHEMA_METRICS_ENTRY="phase:str,model:str,cost_usd:float"

# Validate a YAML file is parseable.
# Args: $1=file_path
# Returns: 0=valid, 1=invalid
assert_yaml_valid() {
  local file="$1"
  if [[ ! -f "$file" ]]; then return 1; fi

  python3 -c "
import yaml, sys
try:
    with open('$file') as f:
        yaml.safe_load(f)
    sys.exit(0)
except Exception as e:
    print(f'  ⛔ YAML parse error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&2
}

# Validate a YAML file contains required top-level keys.
# Args: $1=file_path, $2=comma-separated keys
# Returns: 0=all present, 1=some missing
assert_yaml_has_keys() {
  local file="$1"
  local keys="$2"

  if [[ ! -f "$file" ]]; then return 1; fi

  python3 -c "
import yaml, sys
with open('$file') as f:
    data = yaml.safe_load(f) or {}
required = '$keys'.split(',')
missing = [k.strip() for k in required if k.strip() and k.strip() not in data]
if missing:
    print(f'  ⛔ Missing keys: {missing}', file=sys.stderr)
    sys.exit(1)
sys.exit(0)
" 2>&2
}

# Validate file size is within expected range.
# Args: $1=file_path, $2=min_bytes, $3=max_bytes
# Returns: 0=in range, 1=out of range
assert_file_size_range() {
  local file="$1"
  local min_bytes="${2:-0}"
  local max_bytes="${3:-999999999}"

  if [[ ! -f "$file" ]]; then return 1; fi

  local size
  size=$(wc -c < "$file" | tr -d ' ')

  if [[ "$size" -lt "$min_bytes" ]]; then
    echo "  ⚠️  $(basename "$file") too small: ${size}B (min: ${min_bytes}B)" >&2
    return 1
  fi
  if [[ "$size" -gt "$max_bytes" ]]; then
    echo "  ⚠️  $(basename "$file") too large: ${size}B (max: ${max_bytes}B)" >&2
    return 1
  fi
  return 0
}

# Validate Markdown file is non-trivial (has headings and content).
# Args: $1=file_path
# Returns: 0=valid, 1=trivial
assert_markdown_valid() {
  local file="$1"
  if [[ ! -f "$file" ]]; then return 1; fi

  local lines
  lines=$(wc -l < "$file" | tr -d ' ')
  local headings
  headings=$(grep -c '^#' "$file" 2>/dev/null || echo 0)

  if [[ "$lines" -lt 10 ]]; then
    echo "  ⚠️  $(basename "$file") too short: ${lines} lines" >&2
    return 1
  fi
  if [[ "$headings" -lt 2 ]]; then
    echo "  ⚠️  $(basename "$file") has few headings: ${headings} (expected >= 2)" >&2
    return 1
  fi
  return 0
}

# Validate JSON file is parseable.
# Args: $1=file_path
# Returns: 0=valid, 1=invalid
assert_json_valid() {
  local file="$1"
  if [[ ! -f "$file" ]]; then return 1; fi

  python3 -c "
import json, sys
try:
    with open('$file') as f:
        json.load(f)
    sys.exit(0)
except Exception as e:
    print(f'  ⛔ JSON parse error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&2
}

# Validate a YAML file against a lightweight schema.
# Schema format: "field:type,field:type,..." where type is one of:
#   float, list, str, dict, int, bool
# Args: $1=file_path, $2=schema_spec
# Returns: 0=valid, 1=invalid (errors on stderr)
# Story: RUNNER-1.3 (Runner Hardening)
assert_yaml_schema() {
  local file="$1"
  local schema="$2"

  if [[ ! -f "$file" ]]; then
    echo "  ⛔ File not found: $file" >&2
    return 1
  fi

  python3 - "$file" "$schema" <<'PYEOF'
import yaml, sys

TYPE_MAP = {
    'float': (int, float),
    'list': (list,),
    'str': (str,),
    'dict': (dict,),
    'int': (int,),
    'bool': (bool,),
}

file_path = sys.argv[1]
schema_spec = sys.argv[2]

try:
    with open(file_path) as f:
        data = yaml.safe_load(f) or {}
except Exception as e:
    print(f'YAML parse error: {e}', file=sys.stderr)
    sys.exit(1)

if not isinstance(data, dict):
    print(f'Expected dict at top level, got {type(data).__name__}', file=sys.stderr)
    sys.exit(1)

errors = []
for field_spec in schema_spec.split(','):
    field_spec = field_spec.strip()
    if ':' not in field_spec:
        continue
    field, expected_type = field_spec.split(':', 1)
    field = field.strip()
    expected_type = expected_type.strip()
    if field not in data:
        errors.append(f'Missing field: {field}')
    elif expected_type in TYPE_MAP and not isinstance(data[field], TYPE_MAP[expected_type]):
        errors.append(f'{field}: expected {expected_type}, got {type(data[field]).__name__}')

if errors:
    for e in errors:
        print(f'  ⛔ {e}', file=sys.stderr)
    sys.exit(1)
print(f'  ✓ Schema valid ({len(schema_spec.split(","))} fields checked)')
PYEOF
}

# ═══════════════════════════════════════════════════════════════
# Weighted Assertion Scoring (Promptfoo pattern)
# ═══════════════════════════════════════════════════════════════
# Score = sum(passed_weights) / sum(all_weights) * 100
# Supports per-assertion weights, critical fail-fast, and threshold.
#
# Story: RUNNER-3.1a (Weighted Assertions)

# Run weighted assertions from a YAML config file.
# Args:
#   $1=assertions_yaml — path to assertions config YAML
#   $2=output_file     — file being validated ($OUTPUT_FILE in checks)
#   $3=threshold        — override threshold (optional, defaults to YAML or 70)
# Returns: 0=PASS (score >= threshold), 1=FAIL
# Prints: JSON result with breakdown to stdout

run_weighted_assertions() {
  local assertions_yaml="$1"
  local output_file="$2"
  local threshold_override="${3:-}"

  if [[ ! -f "$assertions_yaml" ]]; then
    echo '{"score":0,"threshold":70,"passed":false,"error":"assertions file not found","breakdown":[]}'
    return 1
  fi

  if [[ ! -f "$output_file" ]]; then
    echo '{"score":0,"threshold":70,"passed":false,"error":"output file not found","breakdown":[]}'
    return 1
  fi

  python3 - "$assertions_yaml" "$output_file" "$threshold_override" <<'PYEOF'
import yaml, json, subprocess, sys, os

assertions_file = sys.argv[1]
output_file = sys.argv[2]
threshold_override = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None

with open(assertions_file) as f:
    config = yaml.safe_load(f) or {}

assertions = config.get('assertions', [])
threshold = int(threshold_override or config.get('threshold', 70))

total_weight = 0
passed_weight = 0
breakdown = []

for a in assertions:
    name = a.get('name', 'unnamed')
    check = a.get('check', '')
    weight = int(a.get('weight', 1))
    critical = a.get('critical', False)

    total_weight += weight

    # Substitute $OUTPUT_FILE in check command
    check_cmd = check.replace('$OUTPUT_FILE', output_file)

    # Run the check
    try:
        result = subprocess.run(
            ['bash', '-c', check_cmd],
            capture_output=True, text=True, timeout=10
        )
        passed = result.returncode == 0
    except subprocess.TimeoutExpired:
        passed = False
    except Exception:
        passed = False

    if passed:
        passed_weight += weight

    contribution = round(weight / max(total_weight, 1) * 100, 1)
    breakdown.append({
        'name': name,
        'weight': weight,
        'passed': passed,
        'critical': critical,
        'contribution': contribution
    })

    # Fail-fast on critical assertion
    if critical and not passed:
        score = round(passed_weight / max(total_weight, 1) * 100, 1)
        print(json.dumps({
            'score': score,
            'threshold': threshold,
            'passed': False,
            'fail_fast': True,
            'fail_reason': f'Critical assertion failed: {name}',
            'breakdown': breakdown,
            'summary': f'{sum(1 for b in breakdown if b["passed"])}/{len(breakdown)} assertions passed'
        }))
        sys.exit(1)

# Calculate final score
score = round(passed_weight / max(total_weight, 1) * 100, 1)
passed_global = score >= threshold

print(json.dumps({
    'score': score,
    'threshold': threshold,
    'passed': passed_global,
    'fail_fast': False,
    'breakdown': breakdown,
    'summary': f'{sum(1 for b in breakdown if b["passed"])}/{len(breakdown)} assertions passed'
}))

sys.exit(0 if passed_global else 1)
PYEOF
}

# Convenience: run weighted assertions and print human-readable summary.
# Args: same as run_weighted_assertions
# Returns: 0=PASS, 1=FAIL
run_weighted_assertions_verbose() {
  local result
  local exit_code=0
  result=$(run_weighted_assertions "$@") || exit_code=$?

  local score threshold summary
  score=$(echo "$result" | jq -r '.score')
  threshold=$(echo "$result" | jq -r '.threshold')
  summary=$(echo "$result" | jq -r '.summary')

  echo "  📊 Weighted Score: ${score}/100 (threshold: ${threshold}) — ${summary}" >&2

  # Print breakdown
  echo "$result" | jq -r '.breakdown[] | "  " + (if .passed then "✅" else "❌" end) + " " + .name + " (w:" + (.weight|tostring) + ")"' >&2

  if [[ "$exit_code" -eq 0 ]]; then
    echo "  ✅ PASS" >&2
  else
    local fail_reason
    fail_reason=$(echo "$result" | jq -r '.fail_reason // empty')
    if [[ -n "$fail_reason" ]]; then
      echo "  🛑 FAIL (critical): $fail_reason" >&2
    else
      echo "  ❌ FAIL (score below threshold)" >&2
    fi
  fi

  echo "$result"
  return $exit_code
}

# Validate all YAML files in a directory are parseable.
# Args: $1=directory
# Returns: 0=all valid, 1=some invalid (count printed)
assert_all_yaml_valid() {
  local dir="$1"
  local failures=0

  for f in "$dir"/*.yaml "$dir"/*.yml; do
    [[ -f "$f" ]] || continue
    assert_yaml_valid "$f" || failures=$((failures + 1))
  done

  if [[ "$failures" -gt 0 ]]; then
    echo "  ⛔ $failures YAML files failed validation in $(basename "$dir")" >&2
    return 1
  fi
  return 0
}
