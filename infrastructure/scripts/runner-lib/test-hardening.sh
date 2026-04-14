#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# RUNNER-LIB — Integration Tests for RUNNER-1.3 Hardening
# ═══════════════════════════════════════════════════════════════
# Tests pre-flight check, schema validation, and cost cap
# WITHOUT burning API tokens. Uses mock data and controlled env.
#
# Usage: bash infrastructure/scripts/runner-lib/test-hardening.sh
# Exit:  0 = all tests pass, 1 = some failed

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TEST_TMP="$(mktemp -d)"
PASS=0
FAIL=0

cleanup() { rm -rf "$TEST_TMP"; }
trap cleanup EXIT

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { PASS=$((PASS + 1)); echo -e "  ${GREEN}✓${NC} $1"; }
fail() { FAIL=$((FAIL + 1)); echo -e "  ${RED}✗${NC} $1"; }

echo "═══════════════════════════════════════════════════════"
echo "  RUNNER-1.3 Hardening — Integration Tests"
echo "═══════════════════════════════════════════════════════"
echo ""

# Source runner-lib
source "$SCRIPT_DIR/loader.sh"

# ─────────────────────────────────────────────────────────────
# TEST GROUP 1: Pre-flight Check
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}1. Pre-flight Check${NC}"

# 1a. All binaries present
if preflight_check "bash,cat,echo" "" 2>/dev/null; then
  ok "Pre-flight passes with common binaries"
else
  fail "Pre-flight should pass with bash,cat,echo"
fi

# 1b. Missing binary
if preflight_check "bash,__nonexistent_binary_xyz__" "" 2>/dev/null; then
  fail "Pre-flight should fail with missing binary"
else
  ok "Pre-flight fails on missing binary (__nonexistent_binary_xyz__)"
fi

# 1c. Missing env var
unset __TEST_MISSING_VAR__ 2>/dev/null || true
if preflight_check "" "__TEST_MISSING_VAR__" 2>/dev/null; then
  fail "Pre-flight should fail with missing env var"
else
  ok "Pre-flight fails on unset env var"
fi

# 1d. Present env var
export __TEST_PRESENT_VAR__="hello"
if preflight_check "" "__TEST_PRESENT_VAR__" 2>/dev/null; then
  ok "Pre-flight passes with set env var"
else
  fail "Pre-flight should pass with set env var"
fi
unset __TEST_PRESENT_VAR__

# 1e. Combined: present bins + missing env
unset __TEST_COMBO_VAR__ 2>/dev/null || true
if preflight_check "bash" "__TEST_COMBO_VAR__" 2>/dev/null; then
  fail "Pre-flight should fail: bin ok but env missing"
else
  ok "Pre-flight fails when env missing (bins ok)"
fi

# 1f. Empty args = no checks = pass
if preflight_check "" "" 2>/dev/null; then
  ok "Pre-flight passes with empty args (no checks)"
else
  fail "Pre-flight should pass with no checks"
fi

echo ""

# ─────────────────────────────────────────────────────────────
# TEST GROUP 2: Schema Validation (assert_yaml_schema)
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}2. Schema Validation${NC}"

# 2a. Valid score_card.yaml
cat > "$TEST_TMP/score_card.yaml" << 'YAML'
validation:
  yaml_valid: true
  keys_present: true
overall:
  score: 75.5
  verdict: pass
dimensions:
  coherence: 80
  depth: 70
YAML

if assert_yaml_schema "$TEST_TMP/score_card.yaml" "$SCHEMA_SCORE_CARD" 2>/dev/null; then
  ok "score_card.yaml validates against SCHEMA_SCORE_CARD"
else
  fail "Valid score_card.yaml should pass schema"
fi

# 2b. Missing field
cat > "$TEST_TMP/bad_score.yaml" << 'YAML'
validation:
  yaml_valid: true
dimensions:
  coherence: 80
YAML

if assert_yaml_schema "$TEST_TMP/bad_score.yaml" "$SCHEMA_SCORE_CARD" 2>/dev/null; then
  fail "score_card missing 'overall' should fail"
else
  ok "Schema rejects missing 'overall' field"
fi

# 2c. Wrong type
cat > "$TEST_TMP/wrong_type.yaml" << 'YAML'
validation: "should be dict"
overall:
  score: 75
dimensions:
  coherence: 80
YAML

if assert_yaml_schema "$TEST_TMP/wrong_type.yaml" "$SCHEMA_SCORE_CARD" 2>/dev/null; then
  fail "String where dict expected should fail"
else
  ok "Schema rejects wrong type (str instead of dict)"
fi

# 2d. Valid phase-handoff
cat > "$TEST_TMP/handoff.yaml" << 'YAML'
from_phase: "phase_3"
to_phase: "phase_4"
status: "completed"
YAML

if assert_yaml_schema "$TEST_TMP/handoff.yaml" "$SCHEMA_PHASE_HANDOFF" 2>/dev/null; then
  ok "phase-handoff.yaml validates against SCHEMA_PHASE_HANDOFF"
else
  fail "Valid phase-handoff should pass"
fi

# 2e. Valid state
cat > "$TEST_TMP/state.yaml" << 'YAML'
current_phase: "phase_5"
status: "in_progress"
YAML

if assert_yaml_schema "$TEST_TMP/state.yaml" "$SCHEMA_STATE" 2>/dev/null; then
  ok "state.yaml validates against SCHEMA_STATE"
else
  fail "Valid state should pass"
fi

# 2f. Non-existent file
if assert_yaml_schema "$TEST_TMP/nonexistent.yaml" "$SCHEMA_SCORE_CARD" 2>/dev/null; then
  fail "Non-existent file should fail"
else
  ok "Schema rejects non-existent file"
fi

# 2g. Empty YAML
echo "" > "$TEST_TMP/empty.yaml"
if assert_yaml_schema "$TEST_TMP/empty.yaml" "$SCHEMA_SCORE_CARD" 2>/dev/null; then
  fail "Empty YAML should fail schema"
else
  ok "Schema rejects empty YAML"
fi

echo ""

# ─────────────────────────────────────────────────────────────
# TEST GROUP 3: Cost Cap (check_cost_cap)
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}3. Cost Cap${NC}"

# 3a. No cap = always pass
METRICS_FILE=""
METRICS_TOTAL_COST_USD=0
if check_cost_cap "" 2>/dev/null; then
  ok "No cap set → passes (backward compatible)"
else
  fail "No cap should always return 0"
fi

# 3b. Under cap
METRICS_FILE="$TEST_TMP/metrics_under.jsonl"
echo '{"phase":"p1","model":"haiku","cost_usd":0.005}' > "$METRICS_FILE"
echo '{"phase":"p2","model":"haiku","cost_usd":0.010}' >> "$METRICS_FILE"
if check_cost_cap "1.00" 2>/dev/null; then
  ok "Under cap (\$0.015 < \$1.00) → passes"
else
  fail "Should pass when under cap"
fi

# 3c. Over cap
METRICS_FILE="$TEST_TMP/metrics_over.jsonl"
echo '{"phase":"p1","model":"opus","cost_usd":1.50}' > "$METRICS_FILE"
echo '{"phase":"p2","model":"opus","cost_usd":1.20}' >> "$METRICS_FILE"
check_cost_cap "2.00" 2>/dev/null
rc=$?
if [[ "$rc" -eq 75 ]]; then
  ok "Over cap (\$2.70 > \$2.00) → exit 75 (TEMPFAIL)"
else
  fail "Should return 75 when over cap (got $rc)"
fi

# 3d. Exact boundary (at cap but not over)
METRICS_FILE="$TEST_TMP/metrics_exact.jsonl"
echo '{"phase":"p1","model":"haiku","cost_usd":1.00}' > "$METRICS_FILE"
if check_cost_cap "1.00" 2>/dev/null; then
  ok "At cap exactly (\$1.00 == \$1.00) → passes (not exceeded)"
else
  fail "At cap should pass (> not >=)"
fi

# 3e. Very low cap triggers on first phase
METRICS_FILE="$TEST_TMP/metrics_low.jsonl"
echo '{"phase":"p1","model":"opus","cost_usd":0.50}' > "$METRICS_FILE"
check_cost_cap "0.01" 2>/dev/null
rc=$?
if [[ "$rc" -eq 75 ]]; then
  ok "Very low cap (\$0.50 > \$0.01) → stops after 1st phase"
else
  fail "Low cap should trigger exit 75 (got $rc)"
fi

# 3f. Empty metrics file = under any cap
METRICS_FILE="$TEST_TMP/metrics_empty.jsonl"
touch "$METRICS_FILE"
if check_cost_cap "0.01" 2>/dev/null; then
  ok "Empty metrics file → under cap"
else
  fail "Empty metrics should be under any cap"
fi

echo ""

# ─────────────────────────────────────────────────────────────
# TEST GROUP 4: Runner Integration (loader + preflight wiring)
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}4. Runner Integration${NC}"

# 4a. Loader flags are set
if [[ "$RUNNER_LIB_PREFLIGHT" == "true" ]]; then
  ok "loader.sh sets RUNNER_LIB_PREFLIGHT=true"
else
  fail "loader.sh should set RUNNER_LIB_PREFLIGHT=true"
fi

if [[ "$RUNNER_LIB_ASSERTIONS" == "true" ]]; then
  ok "loader.sh sets RUNNER_LIB_ASSERTIONS=true"
else
  fail "loader.sh should set RUNNER_LIB_ASSERTIONS=true"
fi

if [[ "$RUNNER_LIB_METRICS" == "true" ]]; then
  ok "loader.sh sets RUNNER_LIB_METRICS=true"
else
  fail "loader.sh should set RUNNER_LIB_METRICS=true"
fi

# 4b. Schema constants are defined
if [[ -n "${SCHEMA_SCORE_CARD:-}" ]]; then
  ok "SCHEMA_SCORE_CARD constant defined"
else
  fail "SCHEMA_SCORE_CARD should be defined after loading assertions.sh"
fi

if [[ -n "${SCHEMA_PHASE_HANDOFF:-}" ]]; then
  ok "SCHEMA_PHASE_HANDOFF constant defined"
else
  fail "SCHEMA_PHASE_HANDOFF should be defined"
fi

if [[ -n "${SCHEMA_STATE:-}" ]]; then
  ok "SCHEMA_STATE constant defined"
else
  fail "SCHEMA_STATE should be defined"
fi

if [[ -n "${SCHEMA_METRICS_ENTRY:-}" ]]; then
  ok "SCHEMA_METRICS_ENTRY constant defined"
else
  fail "SCHEMA_METRICS_ENTRY should be defined"
fi

# 4c. Functions are callable
for fn in preflight_check assert_yaml_schema assert_yaml_valid check_cost_cap; do
  if declare -f "$fn" >/dev/null 2>&1; then
    ok "Function $fn() is available"
  else
    fail "Function $fn() should be available after loader"
  fi
done

echo ""

# ─────────────────────────────────────────────────────────────
# TEST GROUP 5: Real output validation (existing artifacts)
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}5. Real Artifact Validation${NC}"

# Alguns artifacts reais ainda usam wrapper roots legados (`score_card`,
# `handoff`). Enquanto a migração não fecha, validamos parseabilidade desses
# outputs históricos e mantemos schema strict nos fixtures/shared tests.

REAL_SCORE=$(find "$REPO_ROOT/outputs" -name "score_card.yaml" -type f 2>/dev/null | head -1)
if [[ -n "$REAL_SCORE" && -f "$REAL_SCORE" ]]; then
  if assert_yaml_valid "$REAL_SCORE" 2>/dev/null; then
    ok "Real score_card.yaml is valid YAML: $(basename "$(dirname "$REAL_SCORE")")"
  else
    fail "Real score_card.yaml is invalid YAML: $REAL_SCORE"
  fi
else
  echo "  ⏭  No real score_card.yaml found in outputs/ (skipped)"
fi

REAL_HANDOFF=$(find "$REPO_ROOT/outputs" -name "phase-handoff.yaml" -type f 2>/dev/null | head -1)
if [[ -n "$REAL_HANDOFF" && -f "$REAL_HANDOFF" ]]; then
  if assert_yaml_valid "$REAL_HANDOFF" 2>/dev/null; then
    ok "Real phase-handoff.yaml is valid YAML: $(basename "$(dirname "$REAL_HANDOFF")")"
  else
    fail "Real phase-handoff.yaml is invalid YAML: $REAL_HANDOFF"
  fi
else
  echo "  ⏭  No real phase-handoff.yaml found in outputs/ (skipped)"
fi

REAL_STATE=$(find "$REPO_ROOT/outputs" -name "sinkra-state.json" -type f 2>/dev/null | head -1)
if [[ -n "$REAL_STATE" && -f "$REAL_STATE" ]]; then
  if assert_json_valid "$REAL_STATE" 2>/dev/null; then
    ok "Real sinkra-state.json is valid JSON: $(basename "$(dirname "$REAL_STATE")")"
  else
    fail "Real sinkra-state.json is invalid JSON: $REAL_STATE"
  fi
else
  echo "  ⏭  No real sinkra-state.json found in outputs/ (skipped)"
fi

echo ""
echo -e "${BOLD}NOTE:${NC} Alguns artifacts históricos ainda usam wrapper roots legados."
echo "  O schema shared atual cobre o formato runner-lib vigente;"
echo "  outputs legados continuam parse-validated até a migração completa."

echo ""

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
TOTAL=$((PASS + FAIL))
echo "═══════════════════════════════════════════════════════"
if [[ "$FAIL" -eq 0 ]]; then
  echo -e "  ${GREEN}${BOLD}ALL $TOTAL TESTS PASSED${NC}"
else
  echo -e "  ${RED}${BOLD}$FAIL/$TOTAL TESTS FAILED${NC}"
fi
echo "═══════════════════════════════════════════════════════"

exit "$FAIL"
