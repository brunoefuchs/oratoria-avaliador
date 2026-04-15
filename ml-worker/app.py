import asyncio
import logging
import tempfile
import time
from pathlib import Path

import httpx
import structlog
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

import config
from workers.video_processor import split_video

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(config.LOG_LEVEL)),
)

logger = structlog.get_logger()

app = FastAPI(title="Oratoria ML Worker", version="2.0.0")


class ProcessRequest(BaseModel):
    evaluation_id: str
    video_url: str
    callback_url: str


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}


async def _notify_status(callback_url: str, evaluation_id: str, substatus: str):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{callback_url}/evaluations/{evaluation_id}/status-update",
                json={"substatus": substatus},
                headers={"X-Callback-Secret": config.CALLBACK_SECRET},
            )
    except Exception as e:
        logger.warning("status_notify_failed", substatus=substatus, error=str(e))


async def _notify_complete(
    callback_url: str,
    evaluation_id: str,
    status: str,
    error_message: str | None = None,
):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{callback_url}/evaluations/{evaluation_id}/callback",
                json={"status": status, "error_message": error_message},
                headers={"X-Callback-Secret": config.CALLBACK_SECRET},
            )
    except Exception as e:
        logger.error("callback_failed", error=str(e))


def _save_analysis(supabase, evaluation_id: str, dimension: str, result: dict):
    """Salva resultado de analise no banco."""
    supabase.table("analysis_results").upsert(
        {
            "evaluation_id": evaluation_id,
            "dimension": dimension,
            "score": result.get("score", 0),
            "metrics": result.get("metrics", result),
            "confidence": result.get("confidence", "high"),
        }
    ).execute()


def _run_squad_shadow(
    *,
    evaluation_id: str,
    video_url: str,
    video_metadata: dict,
    worker_results: dict,
    evaluation_context: dict | None,
) -> None:
    """Roda oratoria-avaliador squad em shadow mode.

    Shadow = não bloqueia, não afeta fluxo user-facing, apenas loga.
    Import é lazy para evitar custo quando feature flag off.
    Qualquer exceção é capturada pelo caller — aqui só loga-se decisão.
    """
    # Lazy import + sys.path extension (squad mora fora de ml-worker/)
    import sys as _sys
    from pathlib import Path as _Path
    squad_tasks = _Path(__file__).resolve().parents[1] / "squads" / "oratoria-avaliador" / "tasks"
    if str(squad_tasks) not in _sys.path:
        _sys.path.insert(0, str(squad_tasks))

    from process_evaluation import process as _squad_process

    duration = float(video_metadata.get("duration_seconds", 0) or 0)

    result = _squad_process(
        evaluation_id=evaluation_id,
        storage_path=video_url,
        duration_seconds=duration,
        worker_outputs=worker_results,
        evaluation_context=evaluation_context,
        mode="template",  # Epic 3b real-LLM ainda não integrado
    )

    decision = result.get("gate_decision", {})
    artifacts = result.get("artifacts", {})
    fidelity = artifacts.get("fidelity_result", {}).get("fidelity_pct")
    mentor = artifacts.get("router_result", {}).get("mentor")

    logger.info(
        "shadow_squad_decision",
        evaluation_id=evaluation_id,
        verdict=decision.get("verdict"),
        release=decision.get("release_to_user"),
        critical_fails=decision.get("critical_fails", []),
        mentor=mentor,
        fidelity_pct=fidelity,
        pipeline_result=result.get("pipeline_result"),
    )

    if decision.get("verdict") == "FAIL":
        logger.info(
            "shadow_squad_audit",
            evaluation_id=evaluation_id,
            audit=result.get("audit_report"),
        )


async def _run_pipeline(req: ProcessRequest):
    start = time.time()
    logger.info("pipeline_start", evaluation_id=req.evaluation_id)

    try:
        # Step 1: Download video do Supabase Storage
        await _notify_status(req.callback_url, req.evaluation_id, "splitting")

        from supabase import create_client

        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

        tmp_dir = tempfile.mkdtemp(prefix="oratoria_")
        video_ext = req.video_url.rsplit(".", 1)[-1] if "." in req.video_url else "mp4"
        video_path = str(Path(tmp_dir) / f"video.{video_ext}")

        logger.info("downloading_video", video_url=req.video_url)
        download_start = time.time()
        video_bytes = supabase.storage.from_("videos").download(req.video_url)

        with open(video_path, "wb") as f:
            f.write(video_bytes)

        logger.info(
            "download_complete",
            duration_seconds=round(time.time() - download_start, 2),
        )

        # Step 2: Separar video em audio + video
        audio_path, video_path = split_video(video_path)

        logger.info(
            "pipeline_split_done",
            evaluation_id=req.evaluation_id,
            audio_path=audio_path,
            total_seconds=round(time.time() - start, 2),
        )

        # Step 3: Analise de postura
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_posture")
        try:
            from workers.posture_analyzer import analyze_posture

            posture_result = analyze_posture(video_path)
        except Exception as e:
            logger.error("posture_analysis_failed", error=str(e))
            posture_result = {"score": 0, "confidence": "failed", "metrics": {}}

        _save_analysis(supabase, req.evaluation_id, "posture", posture_result)

        # Step 4: Analise gestual e contato visual
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_gesture")
        try:
            from workers.gesture_analyzer import analyze_gestures

            gesture_result = analyze_gestures(video_path)
        except Exception as e:
            logger.error("gesture_analysis_failed", error=str(e))
            gesture_result = {"score": 0, "confidence": "failed", "metrics": {}}

        _save_analysis(supabase, req.evaluation_id, "gesture", gesture_result)

        # Step 4.5: Story 7.4 — Analise de expressao facial (smile, brow, eye openness)
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_facial")
        try:
            from workers.facial_analyzer import analyze_facial

            facial_result = analyze_facial(video_path)
        except Exception as e:
            logger.error("facial_analysis_failed", error=str(e))
            facial_result = {"disponivel": False, "score": 0, "diagnostico": "failed", "feedback": str(e)}

        # Step 5: Analise de voz (Whisper + Parselmouth)
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_voice")
        try:
            from workers.voice_analyzer import (
                analyze_prosody,
                calculate_voice_metrics,
                transcribe_audio,
            )

            transcription = transcribe_audio(audio_path, config.WHISPER_MODEL)
            prosody = analyze_prosody(audio_path)
            voice_result = calculate_voice_metrics(transcription, prosody)

            # Salvar transcricao
            supabase.table("transcriptions").insert(
                {
                    "evaluation_id": req.evaluation_id,
                    "full_text": transcription["full_text"],
                    "words": transcription["words"],
                    "language": transcription["language"],
                    "model": transcription["model"],
                }
            ).execute()
        except Exception as e:
            logger.error("voice_analysis_failed", error=str(e))
            voice_result = {"score": 0, "confidence": "failed", "metrics": {}}
            transcription = {"full_text": "", "words": []}

        _save_analysis(supabase, req.evaluation_id, "voice", voice_result)

        # Step 5.5: Story 7.5 — Tonality VAD (5a Vocal Foundation)
        try:
            from workers.tonality_analyzer import analyze_tonality

            tonality_result = analyze_tonality(audio_path)
        except Exception as e:
            logger.error("tonality_analysis_failed", error=str(e))
            tonality_result = {
                "disponivel": False, "score": 0, "diagnostico": "failed",
                "feedback": str(e), "warnings": [str(e)],
            }

        # Step 6: Deteccao de vicios de linguagem
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_fillers")
        try:
            from workers.filler_detector import detect_fillers

            filler_result = detect_fillers(transcription)
        except Exception as e:
            logger.error("filler_detection_failed", error=str(e))
            filler_result = {"score": 0, "confidence": "failed", "metrics": {}}

        _save_analysis(supabase, req.evaluation_id, "fillers", filler_result)

        # Step 6.5: Analise de identidade comunicativa (Epic 6)
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_identity")
        try:
            from workers.identity_analyzer import analyze_identity

            identity_result = analyze_identity(transcription)
        except Exception as e:
            logger.error("identity_analysis_failed", error=str(e))
            identity_result = {"score": 0, "diagnostico": "failed"}

        _save_analysis(supabase, req.evaluation_id, "identity", identity_result)

        # Step 6.6: Analise de abertura (Epic 6)
        try:
            from workers.opening_analyzer import analyze_opening

            opening_result = analyze_opening(
                transcription,
                voice_result.get("metrics", voice_result),
                voice_result.get(
                    "audio_duration_seconds",
                    voice_result.get("metrics", {}).get("audio_duration_seconds", 0),
                ),
            )
        except Exception as e:
            logger.error("opening_analysis_failed", error=str(e))
            opening_result = {"disponivel": False, "motivo": str(e)}

        # Step 7: Analise de variedade (meta-analyzer) — NOVO
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_variety")
        try:
            from workers.variety_analyzer import analyze_variety

            variety_result = analyze_variety(voice_result, gesture_result)
        except Exception as e:
            logger.error("variety_analysis_failed", error=str(e))
            variety_result = {"score": 0, "confidence": "failed", "metrics": {}}

        _save_analysis(supabase, req.evaluation_id, "variety", variety_result)

        # Step 7.5: Story 7.3 — Storytelling Analyzer (bridge, hook, CTA, chemicals)
        try:
            from workers.storytelling_analyzer import analyze_storytelling

            storytelling_result = analyze_storytelling(
                transcription,
                variety_metrics=variety_result.get("metrics") if isinstance(variety_result, dict) else None,
                opening_result=opening_result,  # Story 7.3 fix QA — consistencia hook
            )
        except Exception as e:
            logger.error("storytelling_analysis_failed", error=str(e))
            storytelling_result = {
                "disponivel": False, "score": 0, "diagnostico": "failed",
                "suggestions": [str(e)],
            }

        # Step 8: Classificacao de arquetipos vocais — NOVO
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_archetypes")
        try:
            from workers.archetype_classifier import classify_archetypes

            archetype_result = classify_archetypes(audio_path)
        except Exception as e:
            logger.error("archetype_classification_failed", error=str(e))
            archetype_result = {"score": 0, "confidence": "failed", "metrics": {}}

        _save_analysis(supabase, req.evaluation_id, "archetypes", archetype_result)

        # Step 9: Buscar contexto do orador + Agregar metricas (6 dimensoes)
        from workers.aggregator import aggregate_metrics

        # voice_result pode ter formato nested {"score":..,"metrics":{...}}
        voice_metrics_data = voice_result.get("metrics", voice_result)
        video_metadata = {
            "duration_seconds": voice_metrics_data.get("audio_duration_seconds", 0),
            "frames_processed": posture_result.get("metrics", {}).get("total_frames", 0),
        }

        # Buscar contexto do questionario pre-avaliacao (V2 — 6 perguntas)
        # Race-safe: usuario pode ainda estar preenchendo o questionario enquanto
        # o pipeline roda. Aguarda ate 15s pelo contexto antes de cair no default.
        eval_contexto = None
        eval_motivacao = None
        ctx_wait_deadline = time.time() + 15
        while True:
            try:
                ctx_result = (
                    supabase.table("evaluation_context")
                    .select("*")
                    .eq("evaluation_id", req.evaluation_id)
                    .execute()
                )
                if ctx_result.data:
                    ctx = ctx_result.data[0]
                    eval_contexto = ctx.get("contexto")  # backward compat V1
                    eval_motivacao = ctx.get("motivacao")  # V2
                    break
            except Exception:
                pass
            if time.time() >= ctx_wait_deadline:
                logger.info("evaluation_context_timeout", evaluation_id=req.evaluation_id)
                break
            time.sleep(1)

        aggregated = aggregate_metrics(
            req.evaluation_id,
            posture_result,
            gesture_result,
            voice_result,
            filler_result,
            variety_result,
            archetype_result,
            video_metadata,
            contexto=eval_contexto,
            motivacao=eval_motivacao,
        )

        # Adicionar identity e opening ao aggregated (informativo)
        aggregated["identity"] = identity_result
        aggregated["opening"] = opening_result

        # Step 9.5: Analise de congruencia (cruzar sinais entre canais)
        try:
            from workers.congruence_analyzer import analyze_congruence

            congruence = analyze_congruence(aggregated["detailed_metrics"])
            aggregated["congruence"] = congruence
        except Exception as e:
            logger.warning("congruence_analysis_failed", error=str(e))

        # Step 9.6: Analise temporal (3 tercos)
        try:
            from workers.temporal_analyzer import analyze_temporal

            temporal = analyze_temporal(
                voice_result,
                variety_result,
                filler_result,
                duration_seconds=video_metadata.get("duration_seconds", 0),
            )
            aggregated["temporal"] = temporal
        except Exception as e:
            logger.warning("temporal_analysis_failed", error=str(e))
            aggregated["temporal"] = {"disponivel": False, "motivo": str(e)}

        # Incluir identity, opening, temporal e congruence no detailed_metrics
        # para que a API possa retornar ao frontend
        full_detailed = {**aggregated["detailed_metrics"]}
        if aggregated.get("identity"):
            full_detailed["identity"] = aggregated["identity"]
        if aggregated.get("opening"):
            full_detailed["opening"] = aggregated["opening"]
        if aggregated.get("temporal"):
            full_detailed["temporal"] = aggregated["temporal"]
        if aggregated.get("congruence"):
            full_detailed["congruence"] = aggregated["congruence"]
        # Story 5.3: expor contexto + pesos no relatorio (badge + transparencia)
        if aggregated.get("contexto"):
            full_detailed["contexto"] = aggregated["contexto"]
        if aggregated.get("pesos_utilizados"):
            full_detailed["pesos_utilizados"] = aggregated["pesos_utilizados"]
        # Story 7.4: expor analise facial no relatorio
        if facial_result and facial_result.get("disponivel"):
            full_detailed["facial"] = facial_result
        # Story 7.5: expor tonality VAD no relatorio
        if tonality_result and tonality_result.get("disponivel"):
            full_detailed["tonality"] = tonality_result
        # Story 7.3: expor analise de storytelling no relatorio
        if storytelling_result and storytelling_result.get("disponivel"):
            full_detailed["storytelling"] = storytelling_result

        supabase.table("aggregated_metrics").insert(
            {
                "evaluation_id": req.evaluation_id,
                "overall_score": aggregated["overall_score"],
                "dimension_scores": aggregated["dimension_scores"],
                "detailed_metrics": full_detailed,
                "incomplete_dimensions": aggregated["incomplete_dimensions"],
                "video_metadata": aggregated["video_metadata"],
            }
        ).execute()

        # Step 10: Gerar relatorio de coaching com LLM
        await _notify_status(req.callback_url, req.evaluation_id, "generating_report")
        try:
            from workers.report_generator import generate_report

            # Buscar contexto completo do orador para o LLM
            eval_context = None
            try:
                ctx_result = (
                    supabase.table("evaluation_context")
                    .select("*")
                    .eq("evaluation_id", req.evaluation_id)
                    .execute()
                )
                if ctx_result.data:
                    eval_context = ctx_result.data[0]
            except Exception:
                pass

            report = generate_report(aggregated, context=eval_context)
            supabase.table("reports").insert(
                {
                    "evaluation_id": req.evaluation_id,
                    "summary": report.get("resumo", report.get("summary", "")),
                    "dimension_feedback": report.get(
                        "dimensoes", report.get("dimension_feedback", {})
                    ),
                    "forcas": report.get("forcas", []),
                    "melhorias": report.get("melhorias_80_20", []),
                    "plano_12_semanas": report.get("plano_12_semanas", []),
                    "mensagem_final": report.get("mensagem_final", ""),
                    "llm_model": report.get("llm_model", "gemini-2.5-flash"),
                    "llm_cost_usd": report.get("llm_cost_usd", 0.0),
                }
            ).execute()
        except Exception as e:
            logger.error("report_generation_failed", error=str(e))

        # Step 11: SHADOW MODE — squad oratoria-avaliador em paralelo
        # Não altera fluxo user-facing. Apenas loga decisões para comparação.
        # Feature flag: config.ORATORIA_SHADOW_MODE_ENABLED.
        if config.ORATORIA_SHADOW_MODE_ENABLED:
            try:
                _run_squad_shadow(
                    evaluation_id=req.evaluation_id,
                    video_url=req.video_url,
                    video_metadata=video_metadata,
                    worker_results={
                        "voice_analyzer": voice_result,
                        "filler_detector": filler_result,
                        "posture_analyzer": posture_result,
                        "gesture_analyzer": gesture_result,
                        "facial_analyzer": facial_result,
                        "opening_analyzer": opening_result,
                        "tonality_analyzer": tonality_result,
                    },
                    evaluation_context={
                        "motivacao": eval_motivacao,
                        "contexto_v1": eval_contexto,
                    } if (eval_motivacao or eval_contexto) else None,
                )
            except Exception as e:
                # Shadow NUNCA derruba pipeline real.
                logger.warning(
                    "shadow_mode_failed",
                    evaluation_id=req.evaluation_id,
                    error=str(e),
                )

        elapsed = time.time() - start
        logger.info(
            "pipeline_complete",
            evaluation_id=req.evaluation_id,
            overall_score=aggregated["overall_score"],
            duration_seconds=round(elapsed, 2),
        )

        await _notify_complete(req.callback_url, req.evaluation_id, "completed")

    except Exception as e:
        logger.error(
            "pipeline_error",
            evaluation_id=req.evaluation_id,
            error=str(e),
        )
        await _notify_complete(req.callback_url, req.evaluation_id, "error", error_message=str(e))


@app.post("/process")
async def process_video(
    req: ProcessRequest,
    x_callback_secret: str = Header(),
):
    if x_callback_secret != config.CALLBACK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid callback secret")

    # Fire-and-forget: pipeline roda em background
    asyncio.create_task(_run_pipeline(req))

    return {"accepted": True, "evaluation_id": req.evaluation_id}
