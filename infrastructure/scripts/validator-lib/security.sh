#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR-LIB: security.sh — Grep-based security scanning
# ═══════════════════════════════════════════════════════════════════════════════
# Shared between validate-skill.sh and validate-squad.sh
# Source: infrastructure/scripts/validator-lib/security.sh
#
# Two modes:
#   - Single file:  scan_* functions accept a file path
#   - Directory:    scan_dir_* functions accept a directory + exclusions

# ── Standard exclude dirs for directory scans ──
_SEC_EXCLUDES=(--exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=node_modules --exclude-dir=tests)

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE FILE SCANS (for validate-skill: scan one SKILL.md)
# ═══════════════════════════════════════════════════════════════════════════════

scan_hardcoded_paths() {
  local file="$1"
  local count
  count=$(grep -ciE '(/Users/[a-zA-Z]|/home/[a-zA-Z]|C:\\Users)' "$file" 2>/dev/null | tr -d '[:space:]' || true)
  echo "${count:-0}"
}

scan_secrets() {
  local file="$1"
  local count
  count=$(grep -ciE '(API_KEY|SECRET_KEY|TOKEN|PASSWORD|CREDENTIAL)[[:space:]]*=' "$file" 2>/dev/null | tr -d '[:space:]' || true)
  echo "${count:-0}"
}

scan_file_urls() {
  local file="$1"
  local count
  count=$(grep -ciE 'file://' "$file" 2>/dev/null | tr -d '[:space:]' || true)
  echo "${count:-0}"
}

# Run all single-file scans — returns "total|paths|secrets|urls"
scan_all() {
  local file="$1"
  local paths secrets urls total
  paths=$(scan_hardcoded_paths "$file")
  secrets=$(scan_secrets "$file")
  urls=$(scan_file_urls "$file")
  total=$((paths + secrets + urls))
  echo "$total|$paths|$secrets|$urls"
}

# ═══════════════════════════════════════════════════════════════════════════════
# DIRECTORY SCANS (for validate-squad: scan entire squad directory)
# ═══════════════════════════════════════════════════════════════════════════════
# Each returns: matching lines (empty = clean) for the consumer to count/report.
# Excludes: placeholders, examples, documentation, fake values.

scan_dir_api_keys() {
  local dir="$1"
  grep -rE "${_SEC_EXCLUDES[@]}" "(api[_-]?key|apikey)[[:space:]]*[:=][[:space:]]*['\"][^'\"\$\{]{8,}" "$dir" 2>/dev/null \
    | grep -vE "(\{\{|\\\$\{|process\.env|[Ee]xample|placeholder|grep|pattern|EXAMPLE|sk-1234|your-key|#.*api)" || true
}

scan_dir_secrets() {
  local dir="$1"
  grep -rE "${_SEC_EXCLUDES[@]}" "(secret|password)[[:space:]]*[:=][[:space:]]*['\"][^'\"\$\{]{8,}" "$dir" 2>/dev/null \
    | grep -vE "(\{\{|\\\$\{|process\.env|[Ee]xample|placeholder|grep|pattern|EXAMPLE|secret_key|your-secret|#.*secret|#.*password|mySecret|super-secret|-secret-|-here)" || true
}

scan_dir_aws_keys() {
  local dir="$1"
  grep -rE "${_SEC_EXCLUDES[@]}" "AKIA[A-Z0-9]{16}" "$dir" 2>/dev/null \
    | grep -vE "(EXAMPLE|grep|pattern|\.sh:|\.md:.*grep)" || true
}

scan_dir_gcp_service_accounts() {
  local dir="$1"
  grep -rE "${_SEC_EXCLUDES[@]}" '"type"[[:space:]]*:[[:space:]]*"service_account"' "$dir" 2>/dev/null || true
}

scan_dir_private_keys() {
  local dir="$1"
  grep -rE "${_SEC_EXCLUDES[@]}" "-----BEGIN.*(PRIVATE|RSA|DSA|EC).*KEY-----" "$dir" 2>/dev/null || true
}

scan_dir_key_files() {
  local dir="$1"
  find "$dir" -name "*.pem" -o -name "*.key" -o -name "id_rsa*" 2>/dev/null || true
}

scan_dir_db_urls() {
  local dir="$1"
  grep -rE "${_SEC_EXCLUDES[@]}" "(postgres|mysql|mongodb|redis)://[^:]+:[^@]+@" "$dir" 2>/dev/null \
    | grep -vE "(\{\{|\[PASSWORD\]|[Ee]xample|localhost|user:pass|:password@|:secret@|grep|pattern)" || true
}

scan_dir_env_files() {
  local dir="$1"
  find "$dir" -name ".env*" -o -name "*.env" 2>/dev/null || true
}

VALIDATOR_LIB_SECURITY=true
