#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C
export LANG=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

BOOKS_FILE="$REPO_ROOT/squads/books/scripts/books.sh"
MMOS_FILE="$REPO_ROOT/squads/mmos/scripts/mmos.sh"
COPY_FILE="$REPO_ROOT/squads/copy/scripts/copy.sh"

APPLY="false"
RUN_BOOKS="false"
RUN_MMOS="false"
RUN_COPY="false"
TMP_FILES=()

cleanup() {
  if [[ ${#TMP_FILES[@]} -gt 0 ]]; then
    rm -f "${TMP_FILES[@]}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

usage() {
  cat <<'EOF'
Migra runners legados para o runner-lib compartilhado.

Uso:
  migrate-books-mmos-to-runner-lib.sh [--apply] [--books|--mmos|--copy|--all]

Modos:
  --dry-run   Preview das mudanças (default)
  --apply     Aplica as mudanças in-place

Targets:
  --books     Migra squads/books/scripts/books.sh
  --mmos      Migra squads/mmos/scripts/mmos.sh
  --copy      Migra squads/copy/scripts/copy.sh
  --all       Migra os três (default)

O script é propositalmente opinionado e foi escrito para o layout atual
dos runners `books.sh`, `mmos.sh` e `copy.sh`. Se os blocos âncora mudarem,
ele falha em vez de aplicar uma transformação incorreta.
EOF
}

info() {
  printf '• %s\n' "$1"
}

success() {
  printf '✅ %s\n' "$1"
}

ensure_executable() {
  local file="$1"
  local label="$2"

  if [[ ! -f "$file" ]]; then
    die "$label: arquivo não encontrado para chmod: $file"
  fi

  if [[ -x "$file" ]]; then
    info "$label: já executável"
    return 0
  fi

  if [[ "$APPLY" == "true" ]]; then
    chmod +x "$file"
    success "$label: bit executável aplicado"
  else
    info "$label: aplicaria chmod +x"
  fi
}

warn() {
  printf '⚠️  %s\n' "$1" >&2
}

die() {
  printf '❌ %s\n' "$1" >&2
  exit 1
}

write_temp() {
  local path
  path="$(mktemp)"
  TMP_FILES+=("$path")
  printf '%s' "$1" > "$path"
  printf '%s\n' "$path"
}

replace_exact() {
  local file="$1"
  local label="$2"
  local search="$3"
  local replace="$4"

  local search_file replace_file status
  search_file="$(write_temp "$search")"
  replace_file="$(write_temp "$replace")"

  status="$(python3 - "$file" "$search_file" "$replace_file" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
search = Path(sys.argv[2]).read_text()
replace = Path(sys.argv[3]).read_text()
text = path.read_text()

if replace in text:
    print("already")
elif search not in text:
    print("missing")
else:
    print("replaceable")
PY
)"

  case "$status" in
    already)
      info "$label: já migrado"
      return 0
      ;;
    missing)
      die "$label: bloco âncora não encontrado em $file"
      ;;
    replaceable)
      if [[ "$APPLY" == "true" ]]; then
        python3 - "$file" "$search_file" "$replace_file" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
search = Path(sys.argv[2]).read_text()
replace = Path(sys.argv[3]).read_text()
text = path.read_text()
path.write_text(text.replace(search, replace, 1))
PY
        success "$label: aplicado"
      else
        info "$label: seria aplicado"
      fi
      ;;
    *)
      die "$label: status inesperado: $status"
      ;;
  esac
}

parse_args() {
  if [[ $# -eq 0 ]]; then
    RUN_BOOKS="true"
    RUN_MMOS="true"
    RUN_COPY="true"
    return
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        usage
        exit 0
        ;;
      --dry-run)
        APPLY="false"
        shift
        ;;
      --apply)
        APPLY="true"
        shift
        ;;
      --books)
        RUN_BOOKS="true"
        shift
        ;;
      --mmos)
        RUN_MMOS="true"
        shift
        ;;
      --copy)
        RUN_COPY="true"
        shift
        ;;
      --all)
        RUN_BOOKS="true"
        RUN_MMOS="true"
        RUN_COPY="true"
        shift
        ;;
      *)
        die "flag desconhecida: $1"
        ;;
    esac
  done

  if [[ "$RUN_BOOKS" != "true" && "$RUN_MMOS" != "true" && "$RUN_COPY" != "true" ]]; then
    RUN_BOOKS="true"
    RUN_MMOS="true"
    RUN_COPY="true"
  fi
}

migrate_books() {
  [[ -f "$BOOKS_FILE" ]] || die "books.sh não encontrado em $BOOKS_FILE"

  info "books.sh: analisando"

  local search replace

  search='SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOKS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATES_DIR="$BOOKS_DIR/templates/pipeline"
OUTPUTS_DIR="$(cd "$SCRIPT_DIR/../../../outputs/books" && pwd 2>/dev/null || echo "$SCRIPT_DIR/../../../outputs/books")"
'
  replace='SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOKS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$BOOKS_DIR/../.." && pwd)"
TEMPLATES_DIR="$BOOKS_DIR/templates/pipeline"
OUTPUTS_DIR="$REPO_ROOT/outputs/books"
'
  replace_exact "$BOOKS_FILE" "books output root" "$search" "$replace"

  search='#!/bin/bash
# Book Summary Pipeline Script for Claude Code
# External bash loop - each phase/task runs in fresh Claude session
# Usage: ./books.sh <book-slug> [mode] [max-iterations]
'
  replace='#!/bin/bash
# Book Summary Pipeline Script (runtime-agnostic: Claude, Codex, Gemini)
# External bash loop - each phase/task runs in a fresh LLM session
# Usage: ./books.sh [flags] <book-slug> [mode] [max-iterations]
'
  replace_exact "$BOOKS_FILE" "books header" "$search" "$replace"

  search='# Ensure outputs directory exists
mkdir -p "$OUTPUTS_DIR"
'
  replace='# Ensure outputs directory exists
mkdir -p "$OUTPUTS_DIR"

REPO_ROOT="$(cd "$BOOKS_DIR/../.." && pwd)"
RUNNER_LIB_DIR="$REPO_ROOT/infrastructure/scripts/runner-lib"

if [[ ! -f "$RUNNER_LIB_DIR/loader.sh" ]]; then
  echo "❌ runner-lib not found at $RUNNER_LIB_DIR"
  exit 1
fi
source "$RUNNER_LIB_DIR/loader.sh"

REQUESTED_RUNTIME="${BOOKS_LLM_RUNTIME:-auto}"
SELECTED_RUNTIME=""
LLM_TIMEOUT_SECONDS="${BOOKS_LLM_TIMEOUT:-}"
RETRY_MAX_ATTEMPTS="${BOOKS_RETRY_MAX_ATTEMPTS:-}"
RETRY_BASE_DELAY_SECONDS="${BOOKS_RETRY_BASE_DELAY:-3}"
BOOKS_EXPLICIT_MODEL="${BOOKS_MODEL:-}"

books_run_llm() {
  local model="$1"
  local prompt="$2"
  local log_file="$3"
  local phase_label="${4:-books}"

  if [[ "${RUNNER_LIB_RUNTIME:-false}" == "true" ]] && declare -f run_llm_prompt >/dev/null 2>&1; then
    run_llm_prompt "$model" "$prompt" "$log_file" "$phase_label"
  else
    claude -p --model "$model" --dangerously-skip-permissions "$prompt" 2>&1 | tee -a "$log_file"
  fi
}
'
  replace_exact "$BOOKS_FILE" "books loader + runtime config" "$search" "$replace"

  search='MODEL_DEFAULT="sonnet"  # Claude Sonnet - balanced quality/cost
'
  replace='MODEL_DEFAULT=""  # Set after runtime resolution
'
  replace_exact "$BOOKS_FILE" "books model bootstrap" "$search" "$replace"

  search='  echo "Usage: $0 <book-slug> [mode] [max-iterations]"
  echo ""
  echo "Arguments:"
  echo "  book-slug       Book identifier (e.g., atomic_habits, deep_work)"
  echo "  mode            Pipeline mode: greenfield | brownfield (default: greenfield)"
  echo "  max-iterations  Maximum iterations per phase (default: 10)"
  echo ""
  echo "Examples:"
  echo "  $0 atomic_habits                     # New book, greenfield, 10 iters"
  echo "  $0 deep_work brownfield              # Resume existing, 10 iters"
  echo "  $0 the_4_hour_workweek greenfield 15 # Custom 15 iterations"
  echo ""
'
  replace='  echo "Usage: $0 [flags] <book-slug> [mode] [max-iterations]"
  echo ""
  echo "Arguments:"
  echo "  book-slug       Book identifier (e.g., atomic_habits, deep_work)"
  echo "  mode            Pipeline mode: greenfield | brownfield (default: greenfield)"
  echo "  max-iterations  Maximum iterations per phase (default: 10)"
  echo ""
  echo "Flags:"
  echo "  --claude        Force Claude runtime"
  echo "  --codex         Force Codex runtime"
  echo "  --gemini        Force Gemini runtime"
  echo "  --model <name>  Override runtime model"
  echo "  --timeout <s>   Override LLM timeout in seconds"
  echo ""
  echo "Examples:"
  echo "  $0 atomic_habits"
  echo "  $0 --codex deep_work brownfield"
  echo "  $0 --gemini --model gemini-3.1-pro-preview atomic_habits greenfield 15"
  echo ""
'
  replace_exact "$BOOKS_FILE" "books help text" "$search" "$replace"

  search='# Handle --help, -h flags, and no arguments
if [[ "$1" == "--help" || "$1" == "-h" || -z "$1" ]]; then
  show_help
fi

BOOK_SLUG="$1"
MODE="${2:-greenfield}"
MAX_ITERATIONS="${3:-10}"
'
  replace='POSITIONAL_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)   show_help ;;
    --claude)    REQUESTED_RUNTIME="claude"; shift ;;
    --codex)     REQUESTED_RUNTIME="codex"; shift ;;
    --gemini)    REQUESTED_RUNTIME="gemini"; shift ;;
    --model)     BOOKS_EXPLICIT_MODEL="$2"; shift 2 ;;
    --timeout)   LLM_TIMEOUT_SECONDS="$2"; shift 2 ;;
    -*)          echo "❌ Unknown flag: $1"; echo "   Use --help for usage."; exit 1 ;;
    *)           POSITIONAL_ARGS+=("$1"); shift ;;
  esac
done

if [[ ${#POSITIONAL_ARGS[@]} -eq 0 ]]; then
  show_help
fi

BOOK_SLUG="${POSITIONAL_ARGS[0]}"
MODE="${POSITIONAL_ARGS[1]:-greenfield}"
MAX_ITERATIONS="${POSITIONAL_ARGS[2]:-10}"
'
  replace_exact "$BOOKS_FILE" "books argument parsing" "$search" "$replace"

  search='# Validate mode
if [[ "$MODE" != "greenfield" && "$MODE" != "brownfield" ]]; then
  echo "❌ Invalid mode: $MODE"
  echo "   Valid modes: greenfield, brownfield"
  exit 1
fi

# Book directory path
BOOK_DIR="$OUTPUTS_DIR/$BOOK_SLUG"
'
  replace='# Validate mode
if [[ "$MODE" != "greenfield" && "$MODE" != "brownfield" ]]; then
  echo "❌ Invalid mode: $MODE"
  echo "   Valid modes: greenfield, brownfield"
  exit 1
fi

SELECTED_RUNTIME="$(detect_runtime "$REQUESTED_RUNTIME")"
if [[ "$SELECTED_RUNTIME" == "invalid" ]]; then
  echo "❌ Invalid BOOKS_LLM_RUNTIME: $REQUESTED_RUNTIME"
  echo "   Valid values: auto, claude, codex, gemini"
  exit 1
fi
if [[ "$SELECTED_RUNTIME" == "none" ]]; then
  echo "❌ No supported runtime found in PATH (claude, codex, or gemini)."
  exit 1
fi
validate_runtime "$SELECTED_RUNTIME"

case "$SELECTED_RUNTIME" in
  claude)
    MODEL_DEFAULT="${BOOKS_EXPLICIT_MODEL:-$(get_balanced_model "$SELECTED_RUNTIME")}"
    RETRY_MAX_ATTEMPTS="${RETRY_MAX_ATTEMPTS:-2}"
    LLM_TIMEOUT_SECONDS="${LLM_TIMEOUT_SECONDS:-3600}"
    ;;
  codex)
    MODEL_DEFAULT="${BOOKS_EXPLICIT_MODEL:-$(get_balanced_model "$SELECTED_RUNTIME")}"
    RETRY_MAX_ATTEMPTS="${RETRY_MAX_ATTEMPTS:-3}"
    LLM_TIMEOUT_SECONDS="${LLM_TIMEOUT_SECONDS:-5400}"
    ;;
  gemini)
    MODEL_DEFAULT="${BOOKS_EXPLICIT_MODEL:-$(get_balanced_model "$SELECTED_RUNTIME")}"
    RETRY_MAX_ATTEMPTS="${RETRY_MAX_ATTEMPTS:-2}"
    LLM_TIMEOUT_SECONDS="${LLM_TIMEOUT_SECONDS:-3600}"
    ;;
esac
export SELECTED_RUNTIME LLM_TIMEOUT_SECONDS RETRY_MAX_ATTEMPTS RETRY_BASE_DELAY_SECONDS

# Book directory path
BOOK_DIR="$OUTPUTS_DIR/$BOOK_SLUG"
'
  replace_exact "$BOOKS_FILE" "books runtime resolution" "$search" "$replace"

  search='echo "   Directory:    $BOOK_DIR"
echo "   Max iters:    $MAX_ITERATIONS per phase"
'
  replace='echo "   Directory:    $BOOK_DIR"
echo "   Runtime:      $SELECTED_RUNTIME"
echo "   Model:        $MODEL_DEFAULT"
echo "   Max iters:    $MAX_ITERATIONS per phase"
'
  replace_exact "$BOOKS_FILE" "books status header" "$search" "$replace"

  search='    # Run Claude
    local OUTPUT=$(claude -p --model "$model" --dangerously-skip-permissions "$PHASE_PROMPT" 2>&1 | tee -a "$phase_log") || true
'
  replace='    # Run selected runtime via runner-lib
    local OUTPUT
    OUTPUT=$(books_run_llm "$model" "$PHASE_PROMPT" "$phase_log" "phase-$phase_num") || true
'
  replace_exact "$BOOKS_FILE" "books LLM call" "$search" "$replace"
  ensure_executable "$BOOKS_FILE" "books.sh"
}

migrate_mmos() {
  [[ -f "$MMOS_FILE" ]] || die "mmos.sh não encontrado em $MMOS_FILE"

  info "mmos.sh: analisando"

  local search replace

  search='SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MMOS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATES_DIR="$MMOS_DIR/templates/pipeline"
OUTPUTS_DIR="$(cd "$SCRIPT_DIR/../../../outputs/minds" && pwd)"
'
  replace='SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MMOS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$MMOS_DIR/../.." && pwd)"
RUNNER_LIB_DIR="$REPO_ROOT/infrastructure/scripts/runner-lib"
TEMPLATES_DIR="$MMOS_DIR/templates/pipeline"
OUTPUTS_DIR="$REPO_ROOT/outputs/minds"
'
  replace_exact "$MMOS_FILE" "mmos repo root + runner-lib path" "$search" "$replace"

  search='# Runtime configuration
# MMOS_LLM_RUNTIME: auto | codex | claude
REQUESTED_RUNTIME="${MMOS_LLM_RUNTIME:-auto}"
SELECTED_RUNTIME=""

detect_runtime() {
  case "$REQUESTED_RUNTIME" in
    auto)
      if command -v codex >/dev/null 2>&1; then
        echo "codex"
      elif command -v claude >/dev/null 2>&1; then
        echo "claude"
      else
        echo "none"
      fi
      ;;
    codex|claude) echo "$REQUESTED_RUNTIME" ;;
    *) echo "invalid" ;;
  esac
}
'
  replace='# Runtime configuration
# MMOS_LLM_RUNTIME: auto | codex | claude | gemini
REQUESTED_RUNTIME="${MMOS_LLM_RUNTIME:-auto}"
SELECTED_RUNTIME=""

detect_runtime() {
  local requested="${1:-$REQUESTED_RUNTIME}"
  case "$requested" in
    auto)
      if command -v codex >/dev/null 2>&1; then
        echo "codex"
      elif command -v claude >/dev/null 2>&1; then
        echo "claude"
      elif command -v gemini >/dev/null 2>&1; then
        echo "gemini"
      else
        echo "none"
      fi
      ;;
    codex|claude|gemini) echo "$requested" ;;
    *) echo "invalid" ;;
  esac
}
'
  replace_exact "$MMOS_FILE" "mmos runtime detector" "$search" "$replace"

  search='  echo "  --claude        Force Claude runtime (sets optimal Claude defaults)"
'
  replace='  echo "  --claude        Force Claude runtime (sets optimal Claude defaults)"
  echo "  --gemini        Force Gemini runtime (sets optimal Gemini defaults)"
'
  replace_exact "$MMOS_FILE" "mmos help flags" "$search" "$replace"

  search='  echo "  MMOS_LLM_RUNTIME          auto | codex | claude (default: auto)"
'
  replace='  echo "  MMOS_LLM_RUNTIME          auto | codex | claude | gemini (default: auto)"
'
  replace_exact "$MMOS_FILE" "mmos help env runtime" "$search" "$replace"

  search='  echo "  $0 --claude --synthetic trinity       # Claude runtime, fictional mind"
'
  replace='  echo "  $0 --claude --synthetic trinity       # Claude runtime, fictional mind"
  echo "  $0 --gemini alan_nicolas brownfield   # Gemini runtime, resume existing"
'
  replace_exact "$MMOS_FILE" "mmos help example" "$search" "$replace"

  search='    --claude)    MMOS_LLM_RUNTIME="claude"; shift ;;
'
  replace='    --claude)    MMOS_LLM_RUNTIME="claude"; shift ;;
    --gemini)    MMOS_LLM_RUNTIME="gemini"; shift ;;
'
  replace_exact "$MMOS_FILE" "mmos arg parsing" "$search" "$replace"

  search='SELECTED_RUNTIME="$(detect_runtime)"
'
  replace='SELECTED_RUNTIME="$(detect_runtime "$REQUESTED_RUNTIME")"
'
  replace_exact "$MMOS_FILE" "mmos runtime detect call" "$search" "$replace"

  search='  echo "   Valid values: auto, codex, claude"
'
  replace='  echo "   Valid values: auto, codex, claude, gemini"
'
  replace_exact "$MMOS_FILE" "mmos invalid runtime message" "$search" "$replace"

  search='  echo "❌ No supported runtime found in PATH (codex or claude)."
'
  replace='  echo "❌ No supported runtime found in PATH (codex, claude, or gemini)."
'
  replace_exact "$MMOS_FILE" "mmos missing runtime message" "$search" "$replace"

  search='# Configure defaults based on selected runtime
# Each runtime has different rate limits, models, and optimal settings
if [[ "$SELECTED_RUNTIME" == "codex" ]]; then
  MODEL_OPUS="${MMOS_MODEL_OPUS:-gpt-5-codex}"
  MODEL_HAIKU="${MMOS_MODEL_HAIKU:-gpt-5-codex}"
  AB_TEST_MODE="${MMOS_AB_TEST_MODE:-false}"
  RETRY_MAX_ATTEMPTS="${MMOS_LLM_MAX_ATTEMPTS:-3}"
  LLM_TIMEOUT_SECONDS="${MMOS_LLM_TIMEOUT_SECONDS:-5400}"
  PARALLEL_STAGGER_SECONDS="${MMOS_PARALLEL_STAGGER:-15}"  # Higher: Codex rate limits are stricter
else
  MODEL_OPUS="${MMOS_MODEL_OPUS:-opus}"
  MODEL_HAIKU="${MMOS_MODEL_HAIKU:-haiku}"
  AB_TEST_MODE="${MMOS_AB_TEST_MODE:-true}"
  RETRY_MAX_ATTEMPTS="${MMOS_LLM_MAX_ATTEMPTS:-2}"
  LLM_TIMEOUT_SECONDS="${MMOS_LLM_TIMEOUT_SECONDS:-2400}"
  PARALLEL_STAGGER_SECONDS="${MMOS_PARALLEL_STAGGER:-5}"   # Lower: Claude handles concurrency better
fi
'
  replace='# Configure defaults based on selected runtime
# Each runtime has different rate limits, models, and optimal settings
case "$SELECTED_RUNTIME" in
  codex)
    MODEL_OPUS="${MMOS_MODEL_OPUS:-$(get_quality_model "$SELECTED_RUNTIME")}"
    MODEL_HAIKU="${MMOS_MODEL_HAIKU:-$(get_fast_model "$SELECTED_RUNTIME")}"
    AB_TEST_MODE="${MMOS_AB_TEST_MODE:-false}"
    RETRY_MAX_ATTEMPTS="${MMOS_LLM_MAX_ATTEMPTS:-3}"
    LLM_TIMEOUT_SECONDS="${MMOS_LLM_TIMEOUT_SECONDS:-5400}"
    PARALLEL_STAGGER_SECONDS="${MMOS_PARALLEL_STAGGER:-15}"  # Higher: Codex rate limits are stricter
    ;;
  claude)
    MODEL_OPUS="${MMOS_MODEL_OPUS:-$(get_quality_model "$SELECTED_RUNTIME")}"
    MODEL_HAIKU="${MMOS_MODEL_HAIKU:-$(get_fast_model "$SELECTED_RUNTIME")}"
    AB_TEST_MODE="${MMOS_AB_TEST_MODE:-true}"
    RETRY_MAX_ATTEMPTS="${MMOS_LLM_MAX_ATTEMPTS:-2}"
    LLM_TIMEOUT_SECONDS="${MMOS_LLM_TIMEOUT_SECONDS:-2400}"
    PARALLEL_STAGGER_SECONDS="${MMOS_PARALLEL_STAGGER:-5}"   # Lower: Claude handles concurrency better
    ;;
  gemini)
    MODEL_OPUS="${MMOS_MODEL_OPUS:-$(get_quality_model "$SELECTED_RUNTIME")}"
    MODEL_HAIKU="${MMOS_MODEL_HAIKU:-$(get_fast_model "$SELECTED_RUNTIME")}"
    AB_TEST_MODE="${MMOS_AB_TEST_MODE:-false}"
    RETRY_MAX_ATTEMPTS="${MMOS_LLM_MAX_ATTEMPTS:-2}"
    LLM_TIMEOUT_SECONDS="${MMOS_LLM_TIMEOUT_SECONDS:-3600}"
    PARALLEL_STAGGER_SECONDS="${MMOS_PARALLEL_STAGGER:-8}"
    ;;
esac
'
  replace_exact "$MMOS_FILE" "mmos runtime defaults" "$search" "$replace"

  search='# Validate required CLI for selected runtime
if [[ "$SELECTED_RUNTIME" == "codex" ]]; then
  if ! command -v codex >/dev/null 2>&1; then
    echo "❌ '\''codex'\'' CLI not found in PATH."
    exit 1
  fi
else
  if ! command -v claude >/dev/null 2>&1; then
    echo "❌ '\''claude'\'' CLI not found in PATH."
    exit 1
  fi
fi
'
  replace='# Validate required CLI for selected runtime
case "$SELECTED_RUNTIME" in
  codex)
    if ! command -v codex >/dev/null 2>&1; then
      echo "❌ '\''codex'\'' CLI not found in PATH."
      exit 1
    fi
    ;;
  claude)
    if ! command -v claude >/dev/null 2>&1; then
      echo "❌ '\''claude'\'' CLI not found in PATH."
      exit 1
    fi
    ;;
  gemini)
    if ! command -v gemini >/dev/null 2>&1; then
      echo "❌ '\''gemini'\'' CLI not found in PATH."
      exit 1
    fi
    ;;
esac
'
  replace_exact "$MMOS_FILE" "mmos runtime cli validation" "$search" "$replace"

  search='source "$SCRIPT_DIR/lib/runtime.sh"
'
  replace='if [[ -f "$RUNNER_LIB_DIR/loader.sh" ]]; then
  source "$RUNNER_LIB_DIR/loader.sh"

  if declare -f run_llm_prompt >/dev/null 2>&1 && ! declare -f runner_lib_run_llm_prompt >/dev/null 2>&1; then
    eval "$(declare -f run_llm_prompt | sed '"'"'1s/run_llm_prompt/runner_lib_run_llm_prompt/'"'"')"
  fi

  detect_runtime() {
    local requested="${1:-$REQUESTED_RUNTIME}"
    case "$requested" in
      auto)
        if command -v codex >/dev/null 2>&1; then
          echo "codex"
        elif command -v claude >/dev/null 2>&1; then
          echo "claude"
        elif command -v gemini >/dev/null 2>&1; then
          echo "gemini"
        else
          echo "none"
        fi
        ;;
      codex|claude|gemini) echo "$requested" ;;
      *) echo "invalid" ;;
    esac
  }

  resolve_runtime_model() {
    local model="$1"
    resolve_model_alias "$model" "$SELECTED_RUNTIME"
  }

  run_llm_prompt() {
    local model="$1"
    local prompt="$2"
    local log_file="$3"
    local suppress_terminal_output="${4:-false}"
    local runtime_model
    runtime_model="$(resolve_runtime_model "$model")"
    LAST_LLM_MODEL="$runtime_model"

    local phase_label="${TASK_CTX_TASK_ID:-mmos}"
    local output=""
    local exit_code=0
    output=$(runner_lib_run_llm_prompt "$runtime_model" "$prompt" "$log_file" "$phase_label") || exit_code=$?

    if [[ "$suppress_terminal_output" != "true" && -n "$output" ]]; then
      printf '"'"'%s'"'"' "$output"
    fi

    return "$exit_code"
  }
else
  source "$SCRIPT_DIR/lib/runtime.sh"
fi
'
  replace_exact "$MMOS_FILE" "mmos runtime compatibility shim" "$search" "$replace"
  ensure_executable "$MMOS_FILE" "mmos.sh"
}

migrate_copy() {
  [[ -f "$COPY_FILE" ]] || die "copy.sh não encontrado em $COPY_FILE"

  info "copy.sh: analisando"

  local search replace

  search='#!/bin/bash
# Copy Workflow Loop Script for Claude Code
# Executes Copy workflows by PHASES (not stories) with checkpoints
# Usage: ./copy.sh <project-dir> [max-iterations]
'
  replace='#!/bin/bash
# Copy Workflow Loop Script (runtime-agnostic: Claude, Codex, Gemini)
# Executes Copy workflows by PHASES (not stories) with checkpoints
# Usage: ./copy.sh [flags] <project-dir> [max-iterations]
'
  replace_exact "$COPY_FILE" "copy header" "$search" "$replace"

  search='# Detect unbuffered output command (platform-agnostic)
if command -v stdbuf &> /dev/null; then
  UNBUFFER_CMD="stdbuf -oL"
elif command -v unbuffer &> /dev/null; then
  UNBUFFER_CMD="unbuffer"
else
  UNBUFFER_CMD=""
fi
'
  replace='# Detect unbuffered output command (platform-agnostic)
if command -v stdbuf &> /dev/null; then
  UNBUFFER_CMD="stdbuf -oL"
elif command -v unbuffer &> /dev/null; then
  UNBUFFER_CMD="unbuffer"
else
  UNBUFFER_CMD=""
fi

REPO_ROOT="$(cd "$COPY_DIR/../.." && pwd)"
RUNNER_LIB_DIR="$REPO_ROOT/infrastructure/scripts/runner-lib"

if [[ ! -f "$RUNNER_LIB_DIR/loader.sh" ]]; then
  echo "❌ runner-lib not found at $RUNNER_LIB_DIR"
  exit 1
fi
source "$RUNNER_LIB_DIR/loader.sh"

REQUESTED_RUNTIME="${COPY_LLM_RUNTIME:-auto}"
SELECTED_RUNTIME=""
LLM_TIMEOUT_SECONDS="${COPY_LLM_TIMEOUT:-}"
RETRY_MAX_ATTEMPTS="${COPY_RETRY_MAX_ATTEMPTS:-}"
RETRY_BASE_DELAY_SECONDS="${COPY_RETRY_BASE_DELAY:-3}"
COPY_EXPLICIT_MODEL="${COPY_MODEL:-}"
MODEL_DEFAULT=""

copy_run_llm() {
  local model="$1"
  local prompt="$2"
  local log_file="$3"
  local phase_label="${4:-copy}"

  if [[ "${RUNNER_LIB_RUNTIME:-false}" == "true" ]] && declare -f run_llm_prompt >/dev/null 2>&1; then
    run_llm_prompt "$model" "$prompt" "$log_file" "$phase_label"
  else
    if [[ -n "$UNBUFFER_CMD" ]]; then
      bash -lc "$UNBUFFER_CMD claude -p --model \"$model\" --dangerously-skip-permissions \"\$1\"" _ "$prompt"
    else
      claude -p --model "$model" --dangerously-skip-permissions "$prompt"
    fi
  fi
}
'
  replace_exact "$COPY_FILE" "copy loader + runtime config" "$search" "$replace"

  search='if [[ -z "$1" ]]; then
  echo "📝 Copy Workflow Runner"
  echo ""
  echo "Usage: $0 <project-dir> [max-iterations]"
'
  replace='if [[ "$1" == "--help" || "$1" == "-h" || -z "${1:-}" ]]; then
  echo "📝 Copy Workflow Runner"
  echo ""
  echo "Usage: $0 [flags] <project-dir> [max-iterations]"
  echo ""
  echo "Flags:"
  echo "  --claude        Force Claude runtime"
  echo "  --codex         Force Codex runtime"
  echo "  --gemini        Force Gemini runtime"
  echo "  --model <name>  Override runtime model"
  echo "  --timeout <s>   Override LLM timeout in seconds"
'
  replace_exact "$COPY_FILE" "copy help header" "$search" "$replace"

  search='PROJECT_DIR="$1"
MAX_ITERATIONS=${2:-30}
'
  replace='POSITIONAL_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)   shift; break ;;
    --claude)    REQUESTED_RUNTIME="claude"; shift ;;
    --codex)     REQUESTED_RUNTIME="codex"; shift ;;
    --gemini)    REQUESTED_RUNTIME="gemini"; shift ;;
    --model)     COPY_EXPLICIT_MODEL="$2"; shift 2 ;;
    --timeout)   LLM_TIMEOUT_SECONDS="$2"; shift 2 ;;
    -*)          echo "❌ Unknown flag: $1"; echo "   Use --help for usage."; exit 1 ;;
    *)           POSITIONAL_ARGS+=("$1"); shift ;;
  esac
done

PROJECT_DIR="${POSITIONAL_ARGS[0]:-}"
MAX_ITERATIONS="${POSITIONAL_ARGS[1]:-30}"

if [[ -z "$PROJECT_DIR" ]]; then
  echo "❌ Missing project-dir"
  echo "   Use --help for usage."
  exit 1
fi
'
  replace_exact "$COPY_FILE" "copy argument parsing" "$search" "$replace"

  search='# Remove trailing slash
PROJECT_DIR="${PROJECT_DIR%/}"
'
  replace='# Remove trailing slash
PROJECT_DIR="${PROJECT_DIR%/}"
PROJECT_SLUG="$(basename "$PROJECT_DIR")"
'
  replace_exact "$COPY_FILE" "copy project slug" "$search" "$replace"

  search='# Check project directory exists
if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "❌ Project directory not found: $PROJECT_DIR"
  echo "   Create it first with copy-state.json or run decision matrix."
  exit 1
fi
'
  replace='# Check project directory exists
if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "❌ Project directory not found: $PROJECT_DIR"
  echo "   Create it first with copy-state.json or run decision matrix."
  exit 1
fi

SELECTED_RUNTIME="$(detect_runtime "$REQUESTED_RUNTIME")"
if [[ "$SELECTED_RUNTIME" == "invalid" ]]; then
  echo "❌ Invalid COPY_LLM_RUNTIME: $REQUESTED_RUNTIME"
  echo "   Valid values: auto, claude, codex, gemini"
  exit 1
fi
if [[ "$SELECTED_RUNTIME" == "none" ]]; then
  echo "❌ No supported runtime found in PATH (claude, codex, or gemini)."
  exit 1
fi
validate_runtime "$SELECTED_RUNTIME"

case "$SELECTED_RUNTIME" in
  claude)
    MODEL_DEFAULT="${COPY_EXPLICIT_MODEL:-$(get_balanced_model "$SELECTED_RUNTIME")}"
    RETRY_MAX_ATTEMPTS="${RETRY_MAX_ATTEMPTS:-2}"
    LLM_TIMEOUT_SECONDS="${LLM_TIMEOUT_SECONDS:-3600}"
    ;;
  codex)
    MODEL_DEFAULT="${COPY_EXPLICIT_MODEL:-$(get_balanced_model "$SELECTED_RUNTIME")}"
    RETRY_MAX_ATTEMPTS="${RETRY_MAX_ATTEMPTS:-3}"
    LLM_TIMEOUT_SECONDS="${LLM_TIMEOUT_SECONDS:-5400}"
    ;;
  gemini)
    MODEL_DEFAULT="${COPY_EXPLICIT_MODEL:-$(get_balanced_model "$SELECTED_RUNTIME")}"
    RETRY_MAX_ATTEMPTS="${RETRY_MAX_ATTEMPTS:-2}"
    LLM_TIMEOUT_SECONDS="${LLM_TIMEOUT_SECONDS:-3600}"
    ;;
esac
export SELECTED_RUNTIME LLM_TIMEOUT_SECONDS RETRY_MAX_ATTEMPTS RETRY_BASE_DELAY_SECONDS
'
  replace_exact "$COPY_FILE" "copy runtime resolution" "$search" "$replace"

  search='OUTPUTS_DIR="$PROJECT_DIR/outputs"
LOGS_DIR="$PROJECT_DIR/logs"
LLM_LOG_FILE="$LOGS_DIR/llm-$(date +%Y%m%d).log"

# Create outputs directory if missing
mkdir -p "$OUTPUTS_DIR" "$LOGS_DIR"
'
  replace='OUTPUTS_ROOT_DIR="$REPO_ROOT/outputs/copy"
OUTPUTS_DIR="$OUTPUTS_ROOT_DIR/$PROJECT_SLUG"
LOGS_DIR="$OUTPUTS_DIR/logs"
LLM_LOG_FILE="$LOGS_DIR/llm-$(date +%Y%m%d).log"

# Create outputs directory if missing
mkdir -p "$OUTPUTS_ROOT_DIR" "$OUTPUTS_DIR" "$LOGS_DIR"
'
  replace_exact "$COPY_FILE" "copy logs setup" "$search" "$replace"

  search='echo "   Project:    $PROJECT_NAME"
echo "   Directory:  $PROJECT_DIR"
'
  replace='echo "   Project:    $PROJECT_NAME"
echo "   Project Dir:$PROJECT_DIR"
echo "   Output Dir: $OUTPUTS_DIR"
'
  replace_exact "$COPY_FILE" "copy directory labels" "$search" "$replace"

  search='echo "   Handoff:    $HANDOFF_FILE"
echo "   Max iters:  $MAX_ITERATIONS"
'
  replace='echo "   Handoff:    $HANDOFF_FILE"
echo "   Runtime:    $SELECTED_RUNTIME"
echo "   Model:      $MODEL_DEFAULT"
echo "   Max iters:  $MAX_ITERATIONS"
'
  replace_exact "$COPY_FILE" "copy status header" "$search" "$replace"

  search='  # Run Claude Code with the prompt
  echo "─────────────────────────────────────"
  if [[ -n "$UNBUFFER_CMD" ]]; then
    OUTPUT=$($UNBUFFER_CMD claude -p --dangerously-skip-permissions "$FULL_PROMPT" 2>&1 | tee /dev/stderr) || true
  else
    OUTPUT=$(claude -p --dangerously-skip-permissions "$FULL_PROMPT" 2>&1 | tee /dev/stderr) || true
  fi
  echo "─────────────────────────────────────"
'
  replace='  # Run selected runtime with the prompt
  echo "─────────────────────────────────────"
  PHASE_LABEL=$(printf '\''%s'\'' "$CURRENT_PHASE" | tr '\''[:upper:]'\'' '\''[:lower:]'\'')
  OUTPUT=$(copy_run_llm "$MODEL_DEFAULT" "$FULL_PROMPT" "$LLM_LOG_FILE" "$PHASE_LABEL" 2>&1 | tee /dev/stderr) || true
  echo "─────────────────────────────────────"
'
  replace_exact "$COPY_FILE" "copy LLM call" "$search" "$replace"
  ensure_executable "$COPY_FILE" "copy.sh"
}

main() {
  parse_args "$@"

  info "modo: $([[ "$APPLY" == "true" ]] && echo "apply" || echo "dry-run")"
  info "targets: $([[ "$RUN_BOOKS" == "true" ]] && printf 'books ')$([[ "$RUN_MMOS" == "true" ]] && printf 'mmos ')$([[ "$RUN_COPY" == "true" ]] && printf 'copy')"

  [[ "$RUN_BOOKS" == "true" ]] && migrate_books
  [[ "$RUN_MMOS" == "true" ]] && migrate_mmos
  [[ "$RUN_COPY" == "true" ]] && migrate_copy

  if [[ "$APPLY" == "true" ]]; then
    success "migração concluída"
  else
    success "preview concluído"
    info "use --apply para aplicar as mudanças"
  fi
}

main "$@"
