#!/usr/bin/env python3
"""
Ground Truth comparison — Story 7.7

Puxa scores do app (Supabase) e compara com scores do Gui (CSV export do Google Sheets).
Gera aba Comparação com distâncias e flags.

Workflow completo (7.7):
    1. Rubric master:       docs/sessions/2026-04/handoff-7.7-ground-truth-rubric-gui-reginatto.md
    2. Sheet templates:     docs/templates/7.7-sheet/*.csv
    3. Setup instructions:  docs/templates/7.7-sheet/IMPORT-INSTRUCTIONS.md
    4. Gui preenche Google Sheet (10 videos, blind)
    5. Bruno exporta aba "Ground Truth" como CSV
    6. Este script gera aba "Comparação" com distâncias
    7. Bruno cola output na aba Comparação

Usage:
    python scripts/compare-ground-truth.py \\
        --gui-csv ./ground-truth-gui.csv \\
        --supabase-url $SUPABASE_URL \\
        --supabase-key $SUPABASE_SERVICE_KEY \\
        --output ./ground-truth-comparison.csv

Output columns: video_id, dimension, app_score, gui_score, distance, flag_gt20
Threshold de erro: distância absoluta > 20 em qualquer dimensão dispara flag.

Dependencies:
    pip install supabase pandas
"""

import argparse
import csv
import os
import sys
from dataclasses import dataclass

try:
    from supabase import create_client
except ImportError:
    print("ERROR: pip install supabase pandas", file=sys.stderr)
    sys.exit(1)


DIMENSIONS = [
    "posture", "gesture", "voice", "fillers", "variety",
    "archetypes", "identity", "opening", "congruence", "temporal"
]

DISTANCE_FLAG_THRESHOLD = 20


@dataclass
class Comparison:
    video_id: str
    dimension: str
    app_score: float
    gui_score: float
    distance: float
    flag: bool


def load_gui_scores(csv_path: str) -> dict[str, dict[str, float]]:
    """Returns {video_id: {dimension: score}}"""
    result = {}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            vid = row.get("video_id", "").strip()
            if not vid:
                continue
            scores = {}
            for dim in DIMENSIONS + ["overall"]:
                col = f"{dim}_score"
                val = row.get(col, "").strip()
                if val:
                    try:
                        scores[dim] = float(val)
                    except ValueError:
                        pass
            if scores:
                result[vid] = scores
    return result


def load_app_scores(supabase_url: str, supabase_key: str, video_ids: list[str]) -> dict[str, dict[str, float]]:
    """Returns {video_id: {dimension: score}}.

    Note: the rubric's `video_id` column holds the Supabase `evaluations.id`
    UUID (1 video upload = 1 evaluation row). Scores live in
    `aggregated_metrics`, which has a UNIQUE `evaluation_id` FK to
    `evaluations.id`, so a single query by `evaluation_id` returns the
    canonical scoring row for that video.
    """
    client = create_client(supabase_url, supabase_key)
    result = {}
    for vid in video_ids:
        res = (
            client.table("aggregated_metrics")
            .select("overall_score, dimension_scores")
            .eq("evaluation_id", vid)
            .limit(1)
            .execute()
        )
        if not res.data:
            print(f"WARN: no aggregated_metrics for evaluation {vid}", file=sys.stderr)
            continue
        row = res.data[0]
        scores = dict(row.get("dimension_scores") or {})
        scores["overall"] = row.get("overall_score")
        result[vid] = {k: float(v) for k, v in scores.items() if v is not None}
    return result


def compute_comparisons(gui: dict, app: dict) -> list[Comparison]:
    out = []
    for vid in gui:
        if vid not in app:
            continue
        for dim in DIMENSIONS + ["overall"]:
            g = gui[vid].get(dim)
            a = app[vid].get(dim)
            if g is None or a is None:
                continue
            d = abs(a - g)
            out.append(Comparison(
                video_id=vid,
                dimension=dim,
                app_score=a,
                gui_score=g,
                distance=d,
                flag=d > DISTANCE_FLAG_THRESHOLD,
            ))
    return out


def write_csv(comparisons: list[Comparison], path: str) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["video_id", "dimension", "app_score", "gui_score", "distance", "flag_gt20"])
        for c in comparisons:
            w.writerow([c.video_id, c.dimension, c.app_score, c.gui_score, c.distance, c.flag])


def print_summary(comparisons: list[Comparison]) -> None:
    by_dim = {}
    for c in comparisons:
        by_dim.setdefault(c.dimension, []).append(c.distance)

    print("\n=== Distance summary (by dimension) ===")
    print(f"{'dimension':<15} {'avg':>8} {'max':>8} {'flagged (>20)':>15}")
    for dim in DIMENSIONS + ["overall"]:
        dists = by_dim.get(dim, [])
        if not dists:
            continue
        avg = sum(dists) / len(dists)
        mx = max(dists)
        flagged = sum(1 for d in dists if d > DISTANCE_FLAG_THRESHOLD)
        marker = " <-- FLAG" if flagged else ""
        print(f"{dim:<15} {avg:>8.1f} {mx:>8.1f} {flagged:>15d}{marker}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gui-csv", required=True, help="CSV export from Google Sheets (Ground Truth tab)")
    ap.add_argument("--supabase-url", default=os.environ.get("SUPABASE_URL"))
    ap.add_argument("--supabase-key", default=os.environ.get("SUPABASE_SERVICE_KEY"))
    ap.add_argument("--output", required=True, help="Output CSV path (Comparação)")
    args = ap.parse_args()

    if not args.supabase_url or not args.supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required (env or flags)", file=sys.stderr)
        sys.exit(1)

    gui = load_gui_scores(args.gui_csv)
    if not gui:
        print("ERROR: no Gui scores loaded from CSV", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(gui)} videos from Gui CSV")
    app = load_app_scores(args.supabase_url, args.supabase_key, list(gui.keys()))
    print(f"Loaded {len(app)} evaluations from Supabase")

    comparisons = compute_comparisons(gui, app)
    write_csv(comparisons, args.output)
    print(f"Wrote {len(comparisons)} comparisons to {args.output}")

    print_summary(comparisons)


if __name__ == "__main__":
    main()
