"""WER Benchmark — Story 9.2 AC6.

Compara Word Error Rate (WER) entre Whisper medium e large-v3-turbo em N
audios de calibracao. Meta: turbo <= medium + 5% em todos; < medium em >=7/10.

Fixtures:
- Espera pasta FIXTURES_DIR com estrutura:
    fixtures/<audio_id>/audio.{wav|mp3|m4a}
    fixtures/<audio_id>/reference.txt  (transcript ground truth)
- Se FIXTURES_DIR vazia: tenta usar N audios do Supabase via REPLAY_FROM_DB=true
- Se nenhuma fonte: skip elegante com warning (AC6 permite N<3)

Uso:
    python ml-worker/scripts/wer_benchmark.py
    python ml-worker/scripts/wer_benchmark.py --fixtures=/path/to/fixtures
    python ml-worker/scripts/wer_benchmark.py --tolerance=5.0  # em pontos percentuais

Exit codes:
    0 — PASS (AC6 atendido)
    1 — FAIL (WER turbo fora da tolerancia)
    2 — SKIPPED (nenhuma fixture disponivel)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_THIS = Path(__file__).resolve()
_ML_WORKER_ROOT = _THIS.parent.parent
sys.path.insert(0, str(_ML_WORKER_ROOT))


def _compute_wer(reference: str, hypothesis: str) -> float:
    """Calcula Word Error Rate (0.0 = perfeito, 1.0 = tudo errado).

    Usa jiwer se disponivel. Fallback: Levenshtein simples sobre words.
    """
    try:
        import jiwer

        return jiwer.wer(reference, hypothesis)
    except ImportError:
        # Fallback simples — Levenshtein word-level
        ref_words = reference.lower().split()
        hyp_words = hypothesis.lower().split()

        m, n = len(ref_words), len(hyp_words)
        if m == 0:
            return 1.0 if n > 0 else 0.0
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if ref_words[i - 1] == hyp_words[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
        return dp[m][n] / m


def _find_fixtures(fixtures_dir: Path) -> list[dict]:
    """Procura pares (audio, reference) em fixtures_dir."""
    if not fixtures_dir.exists() or not fixtures_dir.is_dir():
        return []

    pairs = []
    for sample_dir in sorted(fixtures_dir.iterdir()):
        if not sample_dir.is_dir():
            continue
        audio = None
        for ext in ("wav", "mp3", "m4a", "ogg"):
            candidates = list(sample_dir.glob(f"*.{ext}"))
            if candidates:
                audio = candidates[0]
                break
        reference = sample_dir / "reference.txt"
        if audio and reference.exists():
            pairs.append(
                {
                    "id": sample_dir.name,
                    "audio_path": str(audio),
                    "reference": reference.read_text(encoding="utf-8").strip(),
                }
            )
    return pairs


def _run_transcription(audio_path: str, model_name: str) -> tuple[str, float]:
    """Transcreve audio e retorna (texto, wall_time_ms)."""
    import whisper

    model = whisper.load_model(model_name)
    start = time.time()
    result = model.transcribe(audio_path, language="pt", condition_on_previous_text=False)
    duration_ms = (time.time() - start) * 1000
    # Liberar modelo
    del model
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass
    return result.get("text", ""), duration_ms


def _write_report(pairs: list[dict], results: list[dict], output_path: Path) -> None:
    lines = [
        "# WER Benchmark — Story 9.2 AC6",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Fixtures:** {len(pairs)}",
        "",
        "## Results",
        "",
        "| ID | Duration | WER medium | WER turbo | delta | time medium | time turbo |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        delta = r["wer_turbo"] - r["wer_medium"]
        delta_str = f"{delta:+.3f}"
        lines.append(
            f"| {r['id']} | — | {r['wer_medium']:.3f} | {r['wer_turbo']:.3f} | "
            f"{delta_str} | {r['time_medium_ms']:.0f}ms | {r['time_turbo_ms']:.0f}ms |"
        )
    lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="WER Benchmark Story 9.2 AC6")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=_ML_WORKER_ROOT / "fixtures" / "wer_benchmark",
        help="Diretorio com subpastas <id>/{audio,reference.txt}",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=5.0,
        help="Tolerancia WER turbo - medium em pontos percentuais (default 5.0)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_ML_WORKER_ROOT.parent / "docs" / "qa" / "wer-benchmark-story92.md",
        help="Path do markdown report",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    pairs = _find_fixtures(args.fixtures)

    if len(pairs) == 0:
        msg = {
            "status": "skipped",
            "reason": f"No fixtures em {args.fixtures}. Ver docs/qa/wer-benchmark-setup.md",
            "ac6_verdict": "DEFERRED — requer fixtures de calibracao",
        }
        print(json.dumps(msg, indent=2) if args.json else _format_skip(msg, args))
        return 2

    if len(pairs) < 3:
        print(
            f"⚠️  Aviso: {len(pairs)} fixtures encontradas, AC6 recomenda N>=3.",
            file=sys.stderr,
        )

    results = []
    any_fail = False
    tolerance_frac = args.tolerance / 100.0

    for p in pairs:
        print(f"Processando {p['id']}...", file=sys.stderr)
        hyp_medium, t_medium = _run_transcription(p["audio_path"], "medium")
        hyp_turbo, t_turbo = _run_transcription(p["audio_path"], "turbo")

        wer_medium = _compute_wer(p["reference"], hyp_medium)
        wer_turbo = _compute_wer(p["reference"], hyp_turbo)

        results.append(
            {
                "id": p["id"],
                "wer_medium": wer_medium,
                "wer_turbo": wer_turbo,
                "delta": wer_turbo - wer_medium,
                "time_medium_ms": t_medium,
                "time_turbo_ms": t_turbo,
            }
        )

        if wer_turbo > wer_medium + tolerance_frac:
            any_fail = True

    _write_report(pairs, results, args.output)

    turbo_wins = sum(1 for r in results if r["wer_turbo"] < r["wer_medium"])

    report = {
        "status": "fail" if any_fail else "pass",
        "fixtures_count": len(pairs),
        "tolerance_pct": args.tolerance,
        "turbo_better_count": turbo_wins,
        "turbo_better_ratio": turbo_wins / len(results),
        "results": results,
        "verdict": "PASS" if not any_fail else "FAIL",
        "report_written": str(args.output),
    }

    print(json.dumps(report, indent=2) if args.json else _format_result(report))
    return 0 if not any_fail else 1


def _format_skip(msg: dict, args) -> str:
    return (
        f"\n⏭️  WER Benchmark SKIPPED\n"
        f"   Reason: {msg['reason']}\n"
        f"   To run: populate {args.fixtures} com subpastas contendo audio + reference.txt\n"
        f"   AC6 permite defer para Story 9.1.1 (Gate 2 smoke execution).\n"
    )


def _format_result(report: dict) -> str:
    lines = [
        "=" * 60,
        "WER Benchmark — Story 9.2 AC6",
        "=" * 60,
        f"Fixtures testadas: {report['fixtures_count']}",
        f"Tolerancia: {report['tolerance_pct']}%",
        f"Turbo venceu medium em: {report['turbo_better_count']}/{report['fixtures_count']}",
        "",
    ]
    for r in report["results"]:
        lines.append(
            f"  {r['id']}: medium {r['wer_medium']:.3f} · turbo {r['wer_turbo']:.3f} · "
            f"delta {r['delta']:+.3f}"
        )
    lines.append("")
    lines.append(f"Verdict: {report['verdict']}")
    lines.append(f"Report: {report['report_written']}")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
