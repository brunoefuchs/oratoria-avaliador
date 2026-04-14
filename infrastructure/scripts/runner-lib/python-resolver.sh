#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER-LIB: python-resolver.sh — Find Python with PyYAML available
# ═══════════════════════════════════════════════════════════════════════════════
# Tries multiple Python candidates and verifies PyYAML is importable.
# Used by: sinkra-map.sh, validate-squad.sh, sinkra-validate.sh

# Resolve a Python 3 binary that can import yaml.
# Sets RUNNER_PYTHON_BIN on success.
# Returns: 0=found, 1=not found
resolve_python() {
  local candidate
  local candidates=(
    "${RUNNER_PYTHON_BIN:-}"
    "python3"
    "/opt/homebrew/bin/python3"
    "/opt/homebrew/opt/python@3.14/bin/python3.14"
    "/opt/homebrew/opt/python@3.13/bin/python3.13"
    "/opt/homebrew/opt/python@3.12/bin/python3.12"
    "/usr/local/bin/python3"
    "python"
  )

  for candidate in "${candidates[@]}"; do
    [[ -z "$candidate" ]] && continue
    if [[ "$candidate" == */* ]]; then
      [[ -x "$candidate" ]] || continue
    else
      command -v "$candidate" >/dev/null 2>&1 || continue
    fi

    if "$candidate" -c 'import yaml' >/dev/null 2>&1; then
      RUNNER_PYTHON_BIN="$candidate"
      export RUNNER_PYTHON_BIN
      return 0
    fi
  done

  return 1
}

# Resolve or exit with helpful message.
# Usage: require_python
require_python() {
  if ! resolve_python; then
    echo "❌ No Python with PyYAML found." >&2
    echo "   Install: pip3 install pyyaml" >&2
    exit 1
  fi
}

RUNNER_LIB_PYTHON_RESOLVER=true
