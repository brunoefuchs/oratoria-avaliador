#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# MARKDOWN COMPANION — Shell helper for companion .md generation
# ═══════════════════════════════════════════════════════════════
# Story: STORY-118.4
#
# Lightweight shell function that emits a Markdown summary file
# alongside a JSON/JSONL output. For full audience-aware templates,
# use the Node.js module (markdown-companion.js).
#
# Usage:
#   source "$RUNNER_LIB_DIR/markdown-companion.sh"
#   md_path=$(emit_markdown_companion "/path/to/output.json" "Run Title" "Summary text here")

# Guard: idempotent sourcing
[[ -n "${_RUNNER_LIB_MARKDOWN_COMPANION_LOADED:-}" ]] && return 0
_RUNNER_LIB_MARKDOWN_COMPANION_LOADED=1

##
# emit_markdown_companion — Generate a companion .md summary from text
#
# Arguments:
#   $1 - json_path: Path to the source JSON/JSONL file
#   $2 - title: Document title
#   $3 - summary_text: Pre-formatted summary content (Markdown allowed)
#
# Output:
#   Prints the path to the generated .md file to stdout
#
# Returns:
#   0 on success, 1 on missing arguments
##
emit_markdown_companion() {
  local json_path="$1"
  local title="$2"
  local summary_text="$3"

  if [[ -z "$json_path" || -z "$title" ]]; then
    echo "ERROR: emit_markdown_companion requires json_path and title" >&2
    return 1
  fi

  # Derive .md path: foo.json -> foo-summary.md, foo.jsonl -> foo-summary.md
  local md_path
  md_path="${json_path%.jsonl}"
  md_path="${md_path%.json}-summary.md"

  {
    echo "# ${title} -- Summary"
    echo ""
    if [[ -n "$summary_text" ]]; then
      echo "${summary_text}"
      echo ""
    fi
    echo "---"
    echo "*Auto-generated companion for $(basename "$json_path")*"
  } > "$md_path"

  echo "$md_path"
}
