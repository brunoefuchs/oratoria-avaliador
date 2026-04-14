#!/bin/bash
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# RUNNER-LIB â€” Pre-flight Dependency Check
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Verifies required binaries and environment variables BEFORE
# a runner starts execution. Prevents silent mid-run failures.
#
# Usage (from any runner):
#   REQUIRED_BINS="claude,jq,python3"
#   REQUIRED_ENV="ANTHROPIC_API_KEY"
#   preflight_check "$REQUIRED_BINS" "$REQUIRED_ENV" || exit 1
#
# Story: RUNNER-1.3 (Runner Hardening)

# Check that required binaries and env vars are available.
# Args: $1=comma-separated binaries, $2=comma-separated env var names
# Returns: 0=all ok, 1=something missing
preflight_check() {
  local required_bins="${1:-}"
  local required_env="${2:-}"
  local missing=()

  # Check binaries
  if [[ -n "$required_bins" ]]; then
    IFS=',' read -ra bins <<< "$required_bins"
    for bin in "${bins[@]}"; do
      bin="${bin## }"; bin="${bin%% }"  # trim
      [[ -z "$bin" ]] && continue
      if [[ "$bin" == "jq" ]] && command -v python3 &>/dev/null; then
        continue
      fi
      if ! command -v "$bin" &>/dev/null; then
        missing+=("binary:$bin")
      fi
    done
  fi

  # Check env vars
  if [[ -n "$required_env" ]]; then
    IFS=',' read -ra vars <<< "$required_env"
    for var in "${vars[@]}"; do
      var="${var## }"; var="${var%% }"  # trim
      [[ -z "$var" ]] && continue
      if [[ -z "${!var:-}" ]]; then
        missing+=("env:$var")
      fi
    done
  fi

  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" >&2
    echo "  PRE-FLIGHT CHECK FAILED" >&2
    echo "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" >&2
    for item in "${missing[@]}"; do
      local type="${item%%:*}"
      local name="${item#*:}"
      if [[ "$type" == "binary" ]]; then
        echo "  âœ— Binary not found: $name" >&2
        _preflight_suggest_install "$name"
      else
        echo "  âœ— Env var not set: $name" >&2
      fi
    done
    echo "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•" >&2
    return 1
  fi

  echo "[preflight] All checks passed (bins: ${required_bins:-none}, env: ${required_env:-none})" >&2
  return 0
}

# Print installation hint for common binaries.
# Args: $1=binary name
_preflight_suggest_install() {
  local bin="$1"
  local hint=""
  case "$bin" in
    claude)   hint="npm install -g @anthropic-ai/claude-code" ;;
    codex)    hint="npm install -g @openai/codex" ;;
    gemini)   hint="npm install -g @anthropic-ai/claude-code  # or: pip install google-generativeai" ;;
    jq)       hint="(macOS) brew install jq | (Linux) apt install jq | (Windows) choco install jq" ;;
    python3)  hint="(macOS) brew install python3 | (Linux) apt install python3 | (Windows) winget install Python" ;;
    yq)       hint="(macOS) brew install yq | (Linux) pip install yq | (Windows) choco install yq" ;;
    rsync)    hint="(macOS) brew install rsync | (Linux) apt install rsync | (Windows) choco install rsync" ;;
    git)      hint="(macOS) brew install git | (Linux) apt install git | (Windows) winget install Git.Git" ;;
    node)     hint="(macOS) brew install node | (Linux) nvm install --lts | (Windows) winget install Node.js" ;;
    npm)      hint="Comes with Node.js — install Node.js first" ;;
    *)        hint="Check your package manager" ;;
  esac
  echo "    Install: $hint" >&2
}
