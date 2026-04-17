"""Gesture Semantic Analyzer — Story 9.6 (Epic 9).

Avalia significado semantico de gestos via Gemini Vision. Por frame classifica
se gesto reforca ou distrai da mensagem (transcript sincronizado). Retorna
score global de coerencia narrativa (0-100).

Worker pago (~$0.015/vídeo Gemini Flash). Feature flag + budget guard hard cap.
Entra em SECONDARY_DIMENSIONS — nao pesa em overall_score.

Uso:
    from workers.gesture_semantic_analyzer import analyze_gesture_semantic

    result = analyze_gesture_semantic(video_path, transcript_words)
    # result: WorkerSuccess ou WorkerFailure (Truth Contract Epic 8)
"""

from __future__ import annotations

import json
import os
import time

import structlog

from contracts import WorkerFailure, WorkerResult, WorkerSuccess

logger = structlog.get_logger()

GESTURE_SCHEMA = {
    "type": "object",
    "properties": {
        "per_frame": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp_s": {"type": "number"},
                    "gesture_type": {"type": "string"},
                    "reinforces_message": {"type": "boolean"},
                    "distracts": {"type": "boolean"},
                },
                "required": ["timestamp_s", "gesture_type", "reinforces_message", "distracts"],
            },
        },
        "global": {
            "type": "object",
            "properties": {
                "gesture_narrative_coherence_score": {"type": "number"},
                "rationale": {"type": "string"},
            },
            "required": ["gesture_narrative_coherence_score", "rationale"],
        },
    },
    "required": ["per_frame", "global"],
}

PROMPT_TEMPLATE = """Voce e um analista de oratoria especializado em linguagem corporal e gesto semantico.

Para cada frame anexado, com o transcript sincronizado abaixo, avalie:
1. Que tipo de gesto esta sendo feito (ou nenhum)
2. O gesto REFORCA a mensagem falada nesse momento?
3. O gesto DISTRAI (movimento excessivo, incongruente, nervoso)?

Apos todos frames, de um score global 0-100 de coerencia narrativa dos gestos com o discurso.
Principio: "Se o gesto distrai da mensagem, e problema; se nao distrai, mantenha"

Responda APENAS em JSON valido seguindo este schema:
{schema}

Transcript sincronizado (palavra: timestamp_s):
{transcript_summary}

Frames anexados em ordem temporal (timestamp_s indicado com cada frame).
"""


def _build_prompt(transcript_words: list[dict]) -> str:
    """Sumariza transcript com timestamps pra caber no prompt."""
    # Sample transcript to ~100 words com timestamps
    if not transcript_words:
        return PROMPT_TEMPLATE.format(
            schema=json.dumps(GESTURE_SCHEMA, indent=2),
            transcript_summary="(sem transcript disponivel)",
        )

    step = max(1, len(transcript_words) // 100)
    sampled = transcript_words[::step][:100]
    lines = [f"{w.get('word', '')}: {w.get('start', 0):.1f}" for w in sampled]
    summary = " | ".join(lines)

    return PROMPT_TEMPLATE.format(
        schema=json.dumps(GESTURE_SCHEMA, indent=2),
        transcript_summary=summary,
    )


def _call_gemini_vision(
    prompt: str,
    frames: list[dict],
    model_id: str,
    api_key: str,
    temperature: float = 0.3,
) -> dict | None:
    """Chama Gemini Vision multimodal. Retorna dict parseado ou None."""
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        parts = [prompt]
        for f in frames:
            parts.append({"mime_type": "image/png", "data": f["image_b64"]})

        model = genai.GenerativeModel(model_id)
        response = model.generate_content(
            parts,
            generation_config={
                "temperature": temperature,
                "response_mime_type": "application/json",
            },
        )

        text = response.text
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("gemini_json_parse_failed", error=str(e))
        return None
    except Exception as e:  # noqa: BLE001
        logger.warning("gemini_vision_call_failed", error=str(e), error_type=type(e).__name__)
        return None


def analyze_gesture_semantic(
    video_path: str,
    transcript_words: list[dict] | None = None,
) -> WorkerResult:
    """Worker principal — Gemini Vision multimodal inference.

    Returns WorkerResult (Truth Contract). Budget guard + graceful failures.
    """
    from config import (
        GEMINI_API_KEY,
        GEMINI_VISION_MODEL,
        GESTURE_SEMANTIC_FPS,
        GESTURE_SEMANTIC_MAX_COST_PER_EVAL,
        GESTURE_SEMANTIC_MAX_FRAMES,
    )
    from workers._frame_sampler import estimate_cost, sample_frames_base64

    start = time.time()

    if not GEMINI_API_KEY:
        return WorkerFailure(
            dimension="gesture_semantic",
            dimension_status="insufficient_data",
            failure_reason="GEMINI_API_KEY nao configurada",
        )

    # Frame sampling
    frames = sample_frames_base64(
        video_path,
        fps=GESTURE_SEMANTIC_FPS,
        max_frames=GESTURE_SEMANTIC_MAX_FRAMES,
    )

    if not frames:
        return WorkerFailure(
            dimension="gesture_semantic",
            dimension_status="failed",
            failure_reason="Frame extraction retornou zero frames",
        )

    # Budget guard (AC1)
    estimated_cost = estimate_cost(len(frames))
    if estimated_cost > GESTURE_SEMANTIC_MAX_COST_PER_EVAL:
        logger.warning(
            "gesture_semantic_over_budget",
            estimated_cost=estimated_cost,
            budget=GESTURE_SEMANTIC_MAX_COST_PER_EVAL,
            num_frames=len(frames),
        )
        return WorkerFailure(
            dimension="gesture_semantic",
            dimension_status="skipped",
            failure_reason=(
                f"Custo estimado ${estimated_cost} excede budget "
                f"${GESTURE_SEMANTIC_MAX_COST_PER_EVAL}"
            ),
        )

    # Prompt build
    prompt = _build_prompt(transcript_words or [])

    # Retry 2x com temperatura variante (padrao Story 8.5)
    parsed = None
    for attempt, temp in enumerate([0.3, 0.2], start=1):
        parsed = _call_gemini_vision(
            prompt=prompt,
            frames=frames,
            model_id=GEMINI_VISION_MODEL,
            api_key=GEMINI_API_KEY,
            temperature=temp,
        )
        if parsed is not None:
            break
        logger.info("gemini_vision_retry", attempt=attempt, next_temp=temp)

    if parsed is None:
        return WorkerFailure(
            dimension="gesture_semantic",
            dimension_status="failed",
            failure_reason="Gemini Vision retornou JSON invalido apos 2 tentativas",
        )

    # Extract score
    global_data = parsed.get("global", {})
    score = int(round(global_data.get("gesture_narrative_coherence_score", 0)))
    score = max(0, min(100, score))

    elapsed = time.time() - start
    logger.info(
        "gesture_semantic_done",
        score=score,
        num_frames=len(frames),
        cost_estimated=estimated_cost,
        duration_s=round(elapsed, 2),
    )

    return WorkerSuccess(
        dimension="gesture_semantic",
        score=score,
        metrics={
            "per_frame": parsed.get("per_frame", []),
            "rationale": global_data.get("rationale", ""),
            "model_id": GEMINI_VISION_MODEL,
            "num_frames_analyzed": len(frames),
            "estimated_cost_usd": estimated_cost,
            "duration_seconds": round(elapsed, 2),
        },
        confidence=0.75,  # LLM structured output — media confianca ate Gate 3
    )


def analyze_gesture_semantic_legacy(
    video_path: str, transcript_words: list[dict] | None = None
) -> dict:
    """Legacy dict path — preservado pra TRUTH_CONTRACT_ENABLED=false."""
    result = analyze_gesture_semantic(video_path, transcript_words)
    if isinstance(result, WorkerSuccess):
        return {
            "score": result.score,
            "confidence": result.confidence,
            "metrics": result.metrics,
        }
    return {"score": 0, "confidence": "failed", "metrics": {}}


# Evita falhas em ambientes sem var (testes)
os.environ.setdefault("GEMINI_API_KEY", "")
