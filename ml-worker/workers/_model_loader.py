"""Model GPU Orchestrator — Story 9.2 (Epic 9).

Context manager pra load/unload explicito de modelos ML pesados no RTX 4060
(8.6GB VRAM). Permite pipeline carregar whisper → unload → mediapipe sem OOM.

Factory pattern em MODEL_FACTORIES permite Stories 9.3 (Wav2Vec2) e 9.5
(py-feat) adicionarem seus modelos sem tocar no orchestrator core.

Uso:
    with ModelGPU("whisper_turbo") as model:
        result = model.transcribe(audio_path)
    # model unloaded, VRAM liberada aqui

Telemetria: peak VRAM antes/durante/depois via torch.cuda.max_memory_allocated.
Thread-safe: Lock por model_name evita double-load concorrente.
"""

from __future__ import annotations

import gc
import threading
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

import structlog

logger = structlog.get_logger()

# Lock por model_name — permite loads concorrentes de models diferentes,
# mas serializa load do mesmo model name (evita double-download/memory spike).
_MODEL_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_REGISTRY_LOCK = threading.Lock()


def _get_lock(model_name: str) -> threading.Lock:
    with _LOCKS_REGISTRY_LOCK:
        if model_name not in _MODEL_LOCKS:
            _MODEL_LOCKS[model_name] = threading.Lock()
        return _MODEL_LOCKS[model_name]


# ─────────────────────────────────────────────────────────────────────────────
# MODEL FACTORIES
# ─────────────────────────────────────────────────────────────────────────────
# Cada factory retorna o modelo carregado. Stories 9.3 e 9.5 adicionam aqui.


def _load_whisper_turbo() -> Any:
    import whisper

    return whisper.load_model("turbo")


def _load_whisper_medium() -> Any:
    import whisper

    return whisper.load_model("medium")


def _load_wav2vec2_emotion() -> Any:
    """Story 9.3: carrega Wav2Vec2-Emotion (facebook/wav2vec2-base-superb-er).

    Delega pra workers._emotion_ml.load_wav2vec2_emotion que faz lazy import
    de transformers + graceful fallback se lib ausente.
    """
    from workers._emotion_ml import load_wav2vec2_emotion

    bundle = load_wav2vec2_emotion()
    if bundle is None:
        raise RuntimeError(
            "Wav2Vec2-Emotion indisponivel — instalar via: pip install -e '.[emotion]'"
        )
    return bundle


def _load_wavlm_emotion() -> Any:
    """Story 10.1: carrega WavLM-base+ via workers._wavlm_emotion.

    Path 1 v2 (re-escopada): feature extractor only, sem classifier head.
    Substitui infraestrutura wav2vec2 (legacy) mas NÃO substitui o classifier
    pra emotion classification (não há checkpoint emotion drop-in pra PT/EN).
    """
    from workers._wavlm_emotion import load_wavlm_emotion

    bundle = load_wavlm_emotion()
    if bundle is None:
        raise RuntimeError(
            "WavLM-base+ indisponivel — verificar transformers + torch"
        )
    return bundle


def _load_pyfeat() -> Any:
    """Story 9.5: carrega py-feat FACS Detector via workers._facs_ml.

    Delega pra load_pyfeat_detector que faz lazy import + graceful fallback.
    """
    from workers._facs_ml import load_pyfeat_detector

    detector = load_pyfeat_detector()
    if detector is None:
        raise RuntimeError("py-feat indisponivel — instalar via: pip install -e '.[facs]'")
    return detector


MODEL_FACTORIES: dict[str, Callable[[], Any]] = {
    "whisper_turbo": _load_whisper_turbo,
    "whisper_medium": _load_whisper_medium,
    "wav2vec2_emotion": _load_wav2vec2_emotion,
    "wavlm_emotion": _load_wavlm_emotion,  # Story 10.1 — feature extractor only
    "pyfeat": _load_pyfeat,
}


# ─────────────────────────────────────────────────────────────────────────────
# VRAM TELEMETRY
# ─────────────────────────────────────────────────────────────────────────────


def _get_vram_stats() -> dict[str, float]:
    """Retorna stats VRAM em GB. Zero se CUDA nao disponivel."""
    try:
        import torch

        if not torch.cuda.is_available():
            return {"allocated_gb": 0.0, "reserved_gb": 0.0, "peak_gb": 0.0}
        return {
            "allocated_gb": torch.cuda.memory_allocated() / 1e9,
            "reserved_gb": torch.cuda.memory_reserved() / 1e9,
            "peak_gb": torch.cuda.max_memory_allocated() / 1e9,
        }
    except (ImportError, RuntimeError):
        return {"allocated_gb": 0.0, "reserved_gb": 0.0, "peak_gb": 0.0}


def _clear_vram_peak() -> None:
    """Reset peak counter — chamar antes de load pra medir delta do modelo."""
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
    except (ImportError, RuntimeError):
        pass


def _empty_vram_cache() -> None:
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except (ImportError, RuntimeError):
        pass


# ─────────────────────────────────────────────────────────────────────────────
# ModelGPU context manager
# ─────────────────────────────────────────────────────────────────────────────


class ModelGPU(AbstractContextManager):
    """Context manager para load/unload de modelo ML com telemetria VRAM.

    __enter__:
      - Adquire lock do model_name
      - Clear cache + reset peak counter
      - Load via MODEL_FACTORIES[name]
      - Log peak VRAM pos-load

    __exit__:
      - del model + gc.collect()
      - torch.cuda.empty_cache()
      - Release lock

    Raises:
      KeyError: se model_name nao esta em MODEL_FACTORIES
      NotImplementedError: se factory e stub (9.3/9.5 pending)
      Exception: propaga erros de load (caller decide fallback)
    """

    def __init__(self, model_name: str):
        if model_name not in MODEL_FACTORIES:
            raise KeyError(
                f"Model '{model_name}' nao registrado. "
                f"Disponiveis: {sorted(MODEL_FACTORIES.keys())}"
            )
        self.model_name = model_name
        self.model: Any = None
        self._lock: threading.Lock | None = None
        self._started_at: float = 0.0

    def __enter__(self) -> Any:
        self._lock = _get_lock(self.model_name)
        self._lock.acquire()
        self._started_at = time.time()

        try:
            _empty_vram_cache()
            _clear_vram_peak()

            vram_before = _get_vram_stats()
            logger.info(
                "model_load_start",
                model=self.model_name,
                vram_allocated_gb_before=round(vram_before["allocated_gb"], 2),
            )

            factory = MODEL_FACTORIES[self.model_name]
            self.model = factory()

            load_duration = time.time() - self._started_at
            vram_after = _get_vram_stats()
            logger.info(
                "model_load_done",
                model=self.model_name,
                load_duration_s=round(load_duration, 2),
                vram_allocated_gb=round(vram_after["allocated_gb"], 2),
                vram_peak_gb=round(vram_after["peak_gb"], 2),
            )

            return self.model
        except Exception:
            # Libera lock se load falhar para nao deixar leak
            self._lock.release()
            self._lock = None
            raise

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            vram_before_unload = _get_vram_stats()
            self.model = None  # drop reference
            gc.collect()
            _empty_vram_cache()
            vram_after = _get_vram_stats()

            total_duration = time.time() - self._started_at
            logger.info(
                "model_unload_done",
                model=self.model_name,
                total_duration_s=round(total_duration, 2),
                vram_freed_gb=round(
                    vram_before_unload["allocated_gb"] - vram_after["allocated_gb"], 2
                ),
                vram_allocated_gb_after=round(vram_after["allocated_gb"], 2),
            )
        finally:
            if self._lock is not None:
                self._lock.release()
                self._lock = None
