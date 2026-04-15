"""Convergence Harness CLI — entry point for Story 7.6.

Examples:
    # Dry-run (no LLM calls), useful for sanity-checking correlator with fixtures
    python -m scripts.convergence.harness --dry-run

    # Single video via local path
    python -m scripts.convergence.harness \\
        --video-path ./sample.mp4 \\
        --output-json ./run-result.json

    # Single video by video_id (persists to Supabase)
    python -m scripts.convergence.harness \\
        --video-id 7a3e9ccd-... \\
        --video-url https://.../file.mp4 \\
        --persist

    # Batch mode — file with one "video_id|video_url" per line
    python -m scripts.convergence.harness --batch ./batch.txt --persist
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .correlator import build_batch_report, build_report
from .llm_client import evaluate_all
from .prompts import PROMPT_VERSION, REPORT_EVAL_PROMPT_V1


_FIXTURE = {
    "gemini": {
        "score_geral": 72,
        "scores_por_dimensao": {"voz": 70, "clareza": 75, "presenca": 68, "gestos": 72, "arquetipos": 74, "congruencia": 73},
        "pontos_fortes": ["voz clara e projetada", "postura firme", "abertura com impacto"],
        "pontos_fracos": ["pouca variação de ritmo", "gestos repetitivos", "fechamento fraco"],
    },
    "claude": {
        "score_geral": 74,
        "scores_por_dimensao": {"voz": 72, "clareza": 78, "presenca": 70, "gestos": 71, "arquetipos": 75, "congruencia": 74},
        "pontos_fortes": ["dicção articulada", "postura estável aberta", "hook inicial forte"],
        "pontos_fracos": ["ritmo monótono em passagens", "gestos sem variação", "final sem conclusão"],
    },
    "gpt": {
        "score_geral": 70,
        "scores_por_dimensao": {"voz": 68, "clareza": 73, "presenca": 67, "gestos": 69, "arquetipos": 72, "congruencia": 71},
        "pontos_fortes": ["voz projetada", "corpo aberto", "pergunta reflexiva na abertura"],
        "pontos_fracos": ["pouca dinâmica vocal", "gestos repetem", "fechamento apressado"],
    },
}


def _report_to_dict(report) -> dict:
    return {
        "pairwise_r_overall": report.pairwise_r_overall,
        "mean_r_overall": report.mean_r_overall,
        "pairwise_r_per_dimension": report.pairwise_r_per_dimension,
        "top3_fortes_concordance": report.top3_fortes_concordance,
        "top3_fracos_concordance": report.top3_fracos_concordance,
        "alerts": report.alerts,
    }


def _print_human(report, evaluations: dict) -> None:
    print("\n=== Convergence Report ===")
    print(f"Prompt version: {PROMPT_VERSION}")
    print(f"\nScores gerais por LLM:")
    for llm, ev in evaluations.items():
        sg = ev["score_geral"] if isinstance(ev, dict) else ev.score_geral
        mv = ev.get("model_version", "?") if isinstance(ev, dict) else ev.model_version
        print(f"  {llm:<8} ({mv}): {sg}")

    print(f"\nPairwise proximity (overall, 0-1):")
    for pair, r in report.pairwise_r_overall.items():
        marker = " ✓" if r >= 0.85 else "  ⚠️"
        print(f"  {pair:<16} r={r:.3f}{marker}")
    print(f"  mean_r_overall    {report.mean_r_overall:.3f}")

    print(f"\nPairwise proximity (per dimension, 0-1):")
    for dim, pair_map in report.pairwise_r_per_dimension.items():
        mean = sum(pair_map.values()) / len(pair_map)
        marker = " ✓" if mean >= 0.75 else "  ⚠️"
        print(f"  {dim:<12} mean={mean:.3f}{marker}")

    print(f"\nTop-3 concordância (≥2 de 3 é o alvo):")
    print(f"  fortes: {report.top3_fortes_concordance}")
    print(f"  fracos: {report.top3_fracos_concordance}")

    if report.alerts:
        print(f"\n⚠️  {len(report.alerts)} alert(s):")
        for a in report.alerts:
            print(f"  - {a['dimensao'] or 'overall':<15} r={a['r_calculado']:.3f} (esperado ≥{a['r_esperado']})")
    else:
        print("\n✓ Todos os targets atingidos.")


def run_once(
    video_id: str | None,
    video_path: Path | None,
    video_url: str | None,
    dry_run: bool,
    persist: bool,
) -> dict:
    if dry_run:
        evals_raw = _FIXTURE
        evals_for_report = evals_raw
    else:
        results = evaluate_all(REPORT_EVAL_PROMPT_V1, video_path=video_path, video_url=video_url)
        evals_for_report = {llm: ev for llm, ev in results.items()}
        evals_raw = {llm: asdict(ev) for llm, ev in results.items()}

    report = build_report(evals_for_report)

    out = {
        "video_id": video_id,
        "prompt_version": PROMPT_VERSION,
        "evaluations": evals_raw,
        "report": _report_to_dict(report),
    }

    if persist:
        if not video_id:
            raise ValueError("--persist requires --video-id")
        try:
            from .persistence import persist_alerts, persist_runs  # local import: supabase optional

            persist_runs(video_id, PROMPT_VERSION, {k: v if not isinstance(v, dict) else type("_R", (), v) for k, v in results.items()})  # type: ignore[name-defined]
            persist_alerts(video_id, report)
            out["persisted"] = True
        except Exception as exc:
            out["persist_error"] = str(exc)

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Convergence Harness — Story 7.6")
    parser.add_argument("--video-id", help="Supabase video UUID")
    parser.add_argument("--video-path", type=Path, help="Local path to video file")
    parser.add_argument("--video-url", help="Public URL of video")
    parser.add_argument("--batch", type=Path, help="File with one 'video_id|video_url' per line")
    parser.add_argument("--dry-run", action="store_true", help="Use fixture data; no LLM calls")
    parser.add_argument("--persist", action="store_true", help="Insert into Supabase")
    parser.add_argument("--output-json", type=Path, help="Write full result to JSON file")
    parser.add_argument("--verbose", action="store_true", help="Print raw LLM responses")
    args = parser.parse_args()

    if args.batch:
        results: list[dict] = []
        overall_per_llm: dict[str, list[float]] = {}
        dim_per_llm: dict[str, dict[str, list[float]]] = {}
        lines = [line.strip() for line in args.batch.read_text().splitlines() if line.strip()]
        for i, line in enumerate(lines, 1):
            parts = line.split("|", 1)
            vid = parts[0].strip()
            url = parts[1].strip() if len(parts) == 2 else None
            print(f"\n[{i}/{len(lines)}] Processing {vid}...")
            try:
                out = run_once(vid, None, url, args.dry_run, args.persist)
                results.append(out)
                _print_human_from_out(out)
                for llm, ev in out["evaluations"].items():
                    overall_per_llm.setdefault(llm, []).append(float(ev["score_geral"]))
                    dim_acc = dim_per_llm.setdefault(llm, {})
                    for dim, v in ev.get("scores_por_dimensao", {}).items():
                        dim_acc.setdefault(dim, []).append(float(v))
            except Exception as exc:
                print(f"  ✗ ERROR: {exc}")
                results.append({"video_id": vid, "error": str(exc)})

        successful_n = len(next(iter(overall_per_llm.values()), []))
        if successful_n >= 2:
            print(f"\n=== BATCH AGGREGATE (N={successful_n}) ===")
            batch_report = build_batch_report(overall_per_llm, dim_per_llm, successful_n)
            print(f"mean_r_overall across batch: {batch_report.mean_r_overall:.3f}")
            print(f"pairwise_r_overall: {batch_report.pairwise_r_overall}")
            if batch_report.alerts:
                print(f"⚠️  {len(batch_report.alerts)} batch-level alert(s)")
            results.append({
                "batch_aggregate": _report_to_dict(batch_report),
                "n_videos": successful_n,
                "n_attempted": len(lines),
            })
        else:
            print(f"\n⚠️  Only {successful_n} successful runs — need >=2 for batch Pearson. Skipping aggregate.")

        if args.output_json:
            args.output_json.write_text(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    if not (args.video_path or args.video_url or args.dry_run):
        parser.error("Provide one of: --video-path, --video-url, --dry-run, --batch")

    out = run_once(args.video_id, args.video_path, args.video_url, args.dry_run, args.persist)
    _print_human_from_out(out)

    if args.verbose and not args.dry_run:
        print("\n=== Raw responses ===")
        for llm, ev in out["evaluations"].items():
            print(f"\n--- {llm} ---")
            print(ev.get("raw_response", "(no raw)")[:2000])

    if args.output_json:
        args.output_json.write_text(json.dumps(out, indent=2, ensure_ascii=False))
        print(f"\nFull result written to {args.output_json}")

    return 0


def _print_human_from_out(out: dict) -> None:
    class _R:
        def __init__(self, d):
            self.pairwise_r_overall = d["pairwise_r_overall"]
            self.mean_r_overall = d["mean_r_overall"]
            self.pairwise_r_per_dimension = d["pairwise_r_per_dimension"]
            self.top3_fortes_concordance = d["top3_fortes_concordance"]
            self.top3_fracos_concordance = d["top3_fracos_concordance"]
            self.alerts = d["alerts"]

    _print_human(_R(out["report"]), out["evaluations"])


if __name__ == "__main__":
    sys.exit(main())
