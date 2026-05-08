"""Story 10.3 — discourse_arc analyzer (família narrativa).

Gemini 2.5 Flash text-mode (NÃO Vision) sobre transcript completo. Rubric
versionada em prompts/discourse_arc_v1.md. Determinismo: temperature=0,
top_p=0, seed=42. Output JSON validado contra schema.

Justificativa Gemini (vs heurística): texto narrativo é semântico —
heurística regex não detecta callback (palavras parafraseadas) nem
profundidade. Memory feedback_gemini_vision_on_demand autoriza ML pago
em dims onde matemática é fraca.

Critério remoção limpa (AC7): se flag NARRATIVE_FAMILY_ENABLED=false,
módulo NÃO é chamado. Zero custo.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field, ValidationError

import config
from contracts import WorkerResult
from workers._truth_contract_helpers import wrap_worker_result

logger = structlog.get_logger()

# Path do prompt versionado
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "discourse_arc_v1.md"

# Gemini 2.5 Flash pricing (USD por 1M tokens, 2026-05)
PRICE_INPUT_PER_1M = 0.30
PRICE_OUTPUT_PER_1M = 2.50

# Truncate transcript pra cap de custo (Q6 decisão Bruno 2026-05-08)
# Aprox 4 chars/token — 10k tokens ≈ 40k chars
MAX_TRANSCRIPT_CHARS = 40_000

# Cache do prompt + SHA (carrega 1x por processo)
_PROMPT_CACHE: dict[str, str] | None = None


def _load_prompt() -> tuple[str, str]:
    """Carrega prompt do arquivo + computa SHA-256 do conteúdo."""
    global _PROMPT_CACHE
    if _PROMPT_CACHE is None:
        text = PROMPT_PATH.read_text(encoding="utf-8")
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        _PROMPT_CACHE = {"text": text, "sha": sha}
    return _PROMPT_CACHE["text"], _PROMPT_CACHE["sha"]


def _truncate_transcript(transcript: str) -> tuple[str, bool]:
    """Trunca em MAX_TRANSCRIPT_CHARS preservando início + fim.

    Returns:
        (transcript_truncado, foi_truncado_bool)
    """
    if len(transcript) <= MAX_TRANSCRIPT_CHARS:
        return transcript, False

    half = MAX_TRANSCRIPT_CHARS // 2 - 50
    truncated = (
        transcript[:half]
        + "\n\n[...transcript truncado pra cap de custo — meio omitido...]\n\n"
        + transcript[-half:]
    )
    return truncated, True


class DiscourseArcOutput(BaseModel):
    """Schema de output esperado do Gemini. Validado via Pydantic."""

    discourse_type: Literal["lista", "argumentacao", "narrativa", "explicativo"]
    score: int = Field(ge=0, le=100)
    arc_label: Literal["incompleto", "linear", "arco_completo", "circular_callback"]
    tem_payoff: bool
    tipo_payoff: Literal["insight", "imagem", "cta", "licao"] | None = None
    callback_abertura_fechamento: bool
    justificativa: str = Field(max_length=600)  # 400+margem
    confidence: float = Field(ge=0.0, le=1.0)
    criterios_atendidos: dict[str, bool]


def _call_gemini(transcript: str, prompt_template: str) -> tuple[dict, dict]:
    """Chama Gemini 2.5 Flash em modo texto.

    Returns:
        (parsed_json, instrumentation_dict)
    """
    import google.generativeai as genai

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt_filled = prompt_template.replace("{TRANSCRIPT}", transcript)

    t0 = time.time()
    # NOTA: Gemini 2.5 Flash usa "thinking tokens" que consomem max_output_tokens
    # antes do output visível. 1024 é insuficiente (corta JSON em ~70 chars).
    # 4096 dá margem pra thinking + JSON completo (~500 tokens output real).
    response = model.generate_content(
        prompt_filled,
        generation_config={
            "temperature": 0.0,
            "top_p": 0.0,
            "response_mime_type": "application/json",
            "max_output_tokens": 4096,
        },
    )
    latency_ms = int((time.time() - t0) * 1000)

    raw_text = response.text
    if not raw_text or not raw_text.strip():
        raise ValueError(
            f"empty_response finish_reason={response.candidates[0].finish_reason if response.candidates else 'none'}"
        )
    parsed = json.loads(raw_text)

    # Instrumentação cost: usage_metadata pode não existir em todas versões SDK
    usage = getattr(response, "usage_metadata", None)
    if usage:
        in_tokens = getattr(usage, "prompt_token_count", 0) or 0
        out_tokens = getattr(usage, "candidates_token_count", 0) or 0
    else:
        in_tokens = len(prompt_filled) // 4  # estimate fallback
        out_tokens = len(raw_text) // 4

    cost_usd = (in_tokens / 1_000_000) * PRICE_INPUT_PER_1M + (
        out_tokens / 1_000_000
    ) * PRICE_OUTPUT_PER_1M

    return parsed, {
        "latency_ms": latency_ms,
        "cost_usd": round(cost_usd, 6),
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
    }


def _compute_discourse_arc(transcript: str | None) -> dict:
    """Compute interno — chama Gemini, valida schema, retorna dict legacy.

    Output dict shape (compatível com wrap_worker_result):
        {
            "score": int,
            "confidence": "high"|"medium"|"low"|"failed",
            "metrics": {... discourse_arc fields + instrumentation ...}
        }
    """
    if not transcript or not transcript.strip():
        return {
            "score": None,
            "confidence": "failed",
            "metrics": {"failure_reason": "empty_transcript"},
        }

    if not config.GEMINI_API_KEY:
        logger.warning("discourse_arc_no_api_key")
        return {
            "score": None,
            "confidence": "failed",
            "metrics": {"failure_reason": "missing_gemini_api_key"},
        }

    prompt_template, prompt_sha = _load_prompt()
    truncated, was_truncated = _truncate_transcript(transcript)
    if was_truncated:
        logger.warning(
            "discourse_arc_transcript_truncated",
            original_chars=len(transcript),
            truncated_chars=len(truncated),
        )

    # Retry strategy: 1 retry em 429/500/timeout
    last_error: Exception | None = None
    instrumentation: dict[str, Any] = {}
    parsed_dict: dict | None = None
    for attempt in (0, 1):
        try:
            parsed_dict, instrumentation = _call_gemini(truncated, prompt_template)
            break
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            retryable = any(c in err_str for c in ("429", "500", "503", "timeout", "deadline"))
            logger.warning(
                "discourse_arc_gemini_attempt_failed",
                attempt=attempt,
                error_type=type(e).__name__,
                retryable=retryable,
            )
            if not retryable or attempt == 1:
                break
            time.sleep(0.5 * (attempt + 1))

    if parsed_dict is None:
        return {
            "score": None,
            "confidence": "failed",
            "metrics": {
                "failure_reason": f"gemini_error: {type(last_error).__name__}: {last_error}",
                "prompt_sha": prompt_sha,
                "transcript_truncated": was_truncated,
            },
        }

    # Validação Pydantic do schema
    try:
        validated = DiscourseArcOutput(**parsed_dict)
    except ValidationError as e:
        logger.warning("discourse_arc_schema_invalid", errors=e.errors())
        return {
            "score": None,
            "confidence": "failed",
            "metrics": {
                "failure_reason": f"schema_validation_failed: {e.errors()[:2]}",
                "raw_output": str(parsed_dict)[:500],
                "prompt_sha": prompt_sha,
            },
        }

    # Confidence string mapping pro wrap_worker_result legacy
    conf_str = "high" if validated.confidence >= 0.7 else "medium" if validated.confidence >= 0.4 else "low"

    metrics = {
        **validated.model_dump(),
        "prompt_sha": prompt_sha,
        "transcript_truncated": was_truncated,
        "retry_count": 0 if "retry" not in str(last_error).lower() else 1,
        **instrumentation,
    }

    logger.info(
        "discourse_arc_computed",
        score=validated.score,
        arc_label=validated.arc_label,
        confidence=validated.confidence,
        cost_usd=instrumentation.get("cost_usd"),
        latency_ms=instrumentation.get("latency_ms"),
        prompt_sha=prompt_sha,
    )

    return {
        "score": validated.score,
        "confidence": conf_str,
        "metrics": metrics,
    }


def analyze_discourse_arc(transcript: str | None, evaluation_id: str = "") -> WorkerResult:
    """Analisa arco narrativo macro do transcript via Gemini.

    Story 10.3 entrypoint. Chamado pelo orchestrator quando
    NARRATIVE_FAMILY_ENABLED=true.

    Args:
        transcript: texto completo do speech (transcrição Whisper)
        evaluation_id: ID pra logging

    Returns:
        WorkerResult (Success com score 0-100 + metrics, ou Failure com reason)
    """
    return wrap_worker_result(
        "discourse_arc",
        _compute_discourse_arc,
        transcript,
    )
