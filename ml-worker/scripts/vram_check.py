"""VRAM Hardware Smoke — Story 9.2 Gate 1.

Carrega/unload cada modelo registrado em MODEL_FACTORIES e reporta peak VRAM.
Valida que RTX 4060 Laptop (8.6GB) consegue hospedar Epic 9 completo.

Uso:
    python ml-worker/scripts/vram_check.py
    python ml-worker/scripts/vram_check.py --json    # output JSON
    python ml-worker/scripts/vram_check.py --budget=7.5  # threshold custom

Exit codes:
    0 — peak_global <= budget_gb (PASS)
    1 — peak excedeu budget OU erro runtime
    2 — CUDA nao disponivel (skip — nao eh failure)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Fix path pra importar ml-worker sem instalar como pacote
_THIS = Path(__file__).resolve()
_ML_WORKER_ROOT = _THIS.parent.parent
sys.path.insert(0, str(_ML_WORKER_ROOT))


def _get_vram_gb(key: str = "peak") -> float:
    try:
        import torch

        if not torch.cuda.is_available():
            return 0.0
        if key == "allocated":
            return torch.cuda.memory_allocated() / 1e9
        if key == "reserved":
            return torch.cuda.memory_reserved() / 1e9
        return torch.cuda.max_memory_allocated() / 1e9
    except (ImportError, RuntimeError):
        return 0.0


def _reset_peak() -> None:
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
    except (ImportError, RuntimeError):
        pass


def _cuda_available() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except ImportError:
        return False


def _gpu_info() -> dict:
    try:
        import torch

        if not torch.cuda.is_available():
            return {"cuda_available": False}
        return {
            "cuda_available": True,
            "device_name": torch.cuda.get_device_name(0),
            "total_vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2),
            "torch_version": torch.__version__,
        }
    except ImportError:
        return {"cuda_available": False, "error": "torch not installed"}


def _test_model(model_name: str) -> dict:
    """Load → unload com telemetria. Retorna dict com peak/durations/status."""
    from workers._model_loader import ModelGPU

    _reset_peak()
    start = time.time()
    result = {
        "model": model_name,
        "status": "unknown",
        "peak_gb": 0.0,
        "duration_s": 0.0,
    }

    try:
        with ModelGPU(model_name) as _model:
            result["peak_gb"] = round(_get_vram_gb("peak"), 2)
        result["duration_s"] = round(time.time() - start, 2)
        result["status"] = "ok"
    except NotImplementedError as e:
        result["status"] = "skipped_stub"
        result["reason"] = str(e)
    except Exception as e:  # noqa: BLE001 — queremos report de qualquer erro
        result["status"] = "failed"
        result["error"] = str(e)
        result["error_type"] = type(e).__name__

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="VRAM hardware smoke (Story 9.2 Gate 1)")
    parser.add_argument("--json", action="store_true", help="Output JSON em stdout")
    parser.add_argument("--budget", type=float, default=7.5, help="VRAM budget em GB (default 7.5)")
    parser.add_argument(
        "--models",
        nargs="*",
        default=["whisper_turbo", "whisper_medium", "wav2vec2_emotion", "pyfeat"],
        help="Modelos pra testar",
    )
    args = parser.parse_args()

    if not _cuda_available():
        report = {
            "status": "skipped",
            "reason": "CUDA not available — rodar em hardware com GPU NVIDIA",
            "gpu": _gpu_info(),
        }
        print(json.dumps(report, indent=2) if args.json else _format_text(report))
        return 2

    report: dict = {
        "status": "unknown",
        "gpu": _gpu_info(),
        "budget_gb": args.budget,
        "models_tested": [],
        "peak_global_gb": 0.0,
        "verdict": "unknown",
    }

    for name in args.models:
        result = _test_model(name)
        report["models_tested"].append(result)
        if result["peak_gb"] > report["peak_global_gb"]:
            report["peak_global_gb"] = result["peak_gb"]

    if report["peak_global_gb"] <= args.budget:
        report["status"] = "pass"
        report["verdict"] = f"PASS (peak {report['peak_global_gb']}GB <= budget {args.budget}GB)"
        exit_code = 0
    else:
        report["status"] = "fail"
        report["verdict"] = f"FAIL (peak {report['peak_global_gb']}GB > budget {args.budget}GB)"
        exit_code = 1

    any_failed = any(m["status"] == "failed" for m in report["models_tested"])
    if any_failed:
        report["status"] = "fail"
        report["verdict"] += " + modelos falharam durante load"
        exit_code = 1

    print(json.dumps(report, indent=2) if args.json else _format_text(report))
    return exit_code


def _format_text(report: dict) -> str:
    lines = ["=" * 60, "VRAM Hardware Smoke — Story 9.2 Gate 1", "=" * 60]
    gpu = report.get("gpu", {})
    if gpu.get("cuda_available"):
        lines.append(f"GPU: {gpu.get('device_name')} · VRAM total: {gpu.get('total_vram_gb')}GB")
    else:
        lines.append(f"GPU: {report.get('reason', 'no info')}")
        return "\n".join(lines)

    lines.append(f"Budget: {report.get('budget_gb')}GB")
    lines.append("")
    lines.append(f"{'Model':<25} {'Peak VRAM':<12} {'Duration':<10} {'Status':<15}")
    lines.append("-" * 60)
    for m in report.get("models_tested", []):
        status_icon = {
            "ok": "✅ ok",
            "skipped_stub": "⏭️  stub (pending)",
            "failed": "❌ failed",
        }.get(m["status"], m["status"])
        lines.append(
            f"{m['model']:<25} "
            f"{m.get('peak_gb', 0):<12} "
            f"{m.get('duration_s', 0):<10} "
            f"{status_icon:<15}"
        )
    lines.append("-" * 60)
    lines.append(f"Peak global: {report.get('peak_global_gb')}GB")
    lines.append(f"Verdict: {report.get('verdict')}")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
