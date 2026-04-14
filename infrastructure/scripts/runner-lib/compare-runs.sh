#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# COMPARE-RUNS — Cross-run comparison for any runner pipeline
# ═══════════════════════════════════════════════════════════════
# Works with any versioned-run directory structure:
#   outputs/sinkra-squad/{squad}/validate/{timestamp}/
#   outputs/sinkra-squad/{squad}/map/{timestamp}/
#   outputs/squad-validations/{squad}/{timestamp}/
#
# Usage:
#   compare-runs.sh <runs-directory> [--json]
#   compare-runs.sh outputs/sinkra-squad/copy/validate
#   compare-runs.sh outputs/squad-validations/copy
#   compare-runs.sh outputs/sinkra-squad/books/map --json

set -e

show_help() {
  echo "📊 Compare Runs — Cross-run analysis for any runner"
  echo ""
  echo "Usage: $0 [flags] <runs-directory>"
  echo ""
  echo "Arguments:"
  echo "  runs-directory   Path to directory containing timestamped run folders"
  echo ""
  echo "Flags:"
  echo "  --json    Output as JSON instead of table"
  echo ""
  echo "Examples:"
  echo "  $0 outputs/sinkra-squad/copy/validate"
  echo "  $0 outputs/squad-validations/copy"
  echo "  $0 outputs/sinkra-squad/books/map --json"
  exit 0
}

OUTPUT_JSON="false"
RUNS_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) show_help ;;
    --json)    OUTPUT_JSON="true"; shift ;;
    *)         RUNS_DIR="$1"; shift ;;
  esac
done

if [[ -z "$RUNS_DIR" ]]; then
  echo "❌ Missing runs directory. Use --help."
  exit 1
fi

if [[ ! -d "$RUNS_DIR" ]]; then
  echo "❌ Directory not found: $RUNS_DIR"
  exit 1
fi

LABEL="$(basename "$(dirname "$RUNS_DIR")")/$(basename "$RUNS_DIR")"

export RUNS_DIR OUTPUT_JSON LABEL
python3 << 'PYEOF'
import json, os, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

runs_dir = Path(os.environ.get("RUNS_DIR", ""))
output_json = os.environ.get("OUTPUT_JSON", "false") == "true"
label = os.environ.get("LABEL", "?")

runs = []
for run_dir in sorted(runs_dir.iterdir()):
    if not run_dir.is_dir() or run_dir.name in ("latest", ".git"):
        continue

    run = {
        "run_id": run_dir.name,
        "runtime": "?",
        "model": "?",
        "score": None,
        "status": "?",
        "total_cost": 0.0,
        "total_tokens": 0,
        "total_duration": 0,
        "calls": 0,
    }

    # Parse run_id: YYYYMMDD-HHMMSS-runtime-model
    parts = run_dir.name.split("-", 3)
    if len(parts) >= 4:
        run["runtime"] = parts[2]
        run["model"] = parts[3]

    # Read metrics.jsonl (universal)
    metrics_file = run_dir / "metrics.jsonl"
    if metrics_file.exists():
        for line in metrics_file.read_text().strip().split("\n"):
            if not line.strip():
                continue
            try:
                m = json.loads(line)
                run["total_cost"] += m.get("cost_usd", 0)
                run["total_tokens"] += m.get("input_tokens", 0) + m.get("output_tokens", 0)
                run["total_duration"] += m.get("duration_s", 0)
                run["calls"] += 1
            except json.JSONDecodeError:
                pass

    # Read score_card.yaml (sinkra-validate format)
    score_file = run_dir / "score_card.yaml"
    if score_file.exists() and yaml:
        try:
            with open(score_file) as f:
                sc = yaml.safe_load(f) or {}
            # sinkra format: overall.score / overall.status
            if "overall" in sc:
                run["score"] = sc["overall"].get("score")
                run["status"] = sc["overall"].get("status", "?")
            # squad-creator format: scores.final / scores.verdict
            elif "scores" in sc:
                run["score"] = sc["scores"].get("final")
                run["status"] = sc["scores"].get("verdict", "?")
        except:
            pass

    # Read score_card.json (squad-creator format)
    json_score = run_dir / "score_card.json"
    if json_score.exists() and run["score"] is None:
        try:
            with open(json_score) as f:
                jsc = json.load(f)
            run["score"] = jsc.get("final_score")
            run["status"] = jsc.get("result", "?")
        except:
            pass

    # Read sinkra-state.json (map pipeline)
    state_file = run_dir / "sinkra-state.json"
    if state_file.exists() and run["score"] is None:
        try:
            with open(state_file) as f:
                st = json.load(f)
            run["status"] = st.get("status", "?")
            completed = sum(1 for p in st.get("phases", {}).values() if p.get("status") == "complete")
            total = len(st.get("phases", {}))
            run["score"] = f"{completed}/{total}"
        except:
            pass

    runs.append(run)

if not runs:
    print("No runs found.")
    sys.exit(0)

if output_json:
    print(json.dumps(runs, indent=2, default=str))
    sys.exit(0)

# Table output
print()
print(f"╔══════════════════════════════════════════════════════════════════════════════════════╗")
print(f"║  📊 Compare Runs — {label}  ({len(runs)} runs)")
print(f"╠══════════════════════════════════════════════════════════════════════════════════════╣")
print(f"║  {'Runtime':<10} {'Model':<25} {'Score':<12} {'Status':<15} {'Cost':>8} {'Tokens':>10} {'Time':>6} ║")
print(f"╠══════════════════════════════════════════════════════════════════════════════════════╣")

for r in runs:
    runtime = str(r["runtime"])[:10]
    model = str(r["model"])[:25]
    score = f"{r['score']}" if r["score"] is not None else "?"
    status = (str(r["status"]) or "?")[:15]
    cost = f"${r['total_cost']:.2f}"
    tokens = f"{r['total_tokens']:,}"
    duration = f"{r['total_duration']}s"
    print(f"║  {runtime:<10} {model:<25} {score:<12} {status:<15} {cost:>8} {tokens:>10} {duration:>6} ║")

print(f"╚══════════════════════════════════════════════════════════════════════════════════════╝")

# Best run summary
scored = [r for r in runs if r["score"] is not None and isinstance(r["score"], (int, float))]
if scored:
    best = max(scored, key=lambda r: r["score"])
    cheapest = min(scored, key=lambda r: r["total_cost"])
    fastest = min(scored, key=lambda r: r["total_duration"]) if any(r["total_duration"] > 0 for r in scored) else None
    print()
    print(f"  🏆 Highest score:  {best['runtime']}/{best['model']} — {best['score']}")
    print(f"  💰 Cheapest:       {cheapest['runtime']}/{cheapest['model']} — ${cheapest['total_cost']:.2f}")
    if fastest and fastest["total_duration"] > 0:
        print(f"  ⚡ Fastest:        {fastest['runtime']}/{fastest['model']} — {fastest['total_duration']}s")
    print()
PYEOF
