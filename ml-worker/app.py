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


def _save_analysis(supabase, evaluation_id: str, dimension: str, result):
    """Salva resultado de analise no banco.

    Story 8.1 (Truth Contract) T6: dispatcher entre dois paths:

    - Path NOVO: quando result eh WorkerResult (Pydantic) E feature flag
      TRUTH_CONTRACT_ENABLED=true → grava via repositories.save_analysis_result
      (score + dimension_status + failure_reason colunas novas).

    - Path LEGACY: quando result eh dict → grava via
      repositories.save_analysis_result_legacy (score=0 fallback documentado).

    - Defensive: WorkerResult com flag OFF → loga warning e usa legacy via
      model_dump(). Evita quebrar pipeline quando worker migrado roda em
      ambiente sem flag.
    """
    from contracts import WorkerFailure, WorkerSuccess
    from repositories import save_analysis_result, save_analysis_result_legacy

    is_worker_result = isinstance(result, (WorkerSuccess, WorkerFailure))

    if is_worker_result and config.TRUTH_CONTRACT_ENABLED:
        save_analysis_result(supabase, evaluation_id, result)
        return

    if is_worker_result:
        # Flag OFF mas worker ja migrado — log + downgrade pra legacy
        logger.warning(
            "truth_contract_worker_result_with_flag_off",
            evaluation_id=evaluation_id,
            dimension=dimension,
            dimension_status=result.dimension_status,
        )
        result_dict = result.model_dump()
        save_analysis_result_legacy(supabase, evaluation_id, dimension, result_dict)
        return

    # Path legacy padrao: result eh dict
    save_analysis_result_legacy(supabase, evaluation_id, dimension, result)


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

    _parent_dir = _Path(__file__).resolve().parents[1]
    _squad_dir = _parent_dir / "squads" / "oratoria-avaliador"
    squad_tasks = _squad_dir / "tasks"
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
        # Story 8.2: dispatch via feature flag (same pattern as variety — Step 7).
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_posture")
        if config.TRUTH_CONTRACT_ENABLED:
            from workers.posture_analyzer import analyze_posture

            posture_result = analyze_posture(video_path)
        else:
            try:
                from workers.posture_analyzer import analyze_posture_legacy

                posture_result = analyze_posture_legacy(video_path)
            except Exception as e:
                logger.error("posture_analysis_failed", error=str(e))
                posture_result = {"score": 0, "confidence": "failed", "metrics": {}}

        _save_analysis(supabase, req.evaluation_id, "posture", posture_result)

        # Step 4: Analise gestual e contato visual
        # Story 8.2: dispatch via feature flag.
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_gesture")
        if config.TRUTH_CONTRACT_ENABLED:
            from workers.gesture_analyzer import analyze_gestures

            gesture_result = analyze_gestures(video_path)
        else:
            try:
                from workers.gesture_analyzer import analyze_gestures_legacy

                gesture_result = analyze_gestures_legacy(video_path)
            except Exception as e:
                logger.error("gesture_analysis_failed", error=str(e))
                gesture_result = {"score": 0, "confidence": "failed", "metrics": {}}

        _save_analysis(supabase, req.evaluation_id, "gesture", gesture_result)

        # Step 4.5: Story 7.4 — Analise de expressao facial (smile, brow, eye openness)
        # Story 8.3: dispatch via feature flag.
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_facial")
        if config.TRUTH_CONTRACT_ENABLED:
            from workers.facial_analyzer import analyze_facial

            facial_result = analyze_facial(video_path)
        else:
            try:
                from workers.facial_analyzer import analyze_facial_legacy

                facial_result = analyze_facial_legacy(video_path)
            except Exception as e:
                logger.error("facial_analysis_failed", error=str(e))
                facial_result = {
                    "disponivel": False,
                    "score": 0,
                    "diagnostico": "failed",
                    "feedback": str(e),
                }

        # Step 5: Analise de voz (Whisper + Parselmouth)
        # Story 8.2: transcribe_audio + analyze_prosody are intermediates — kept as-is.
        # Only the final voice metrics output is dispatched via feature flag.
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_voice")
        _voice_ok = False
        try:
            from workers.voice_analyzer import (
                analyze_prosody,
                transcribe_audio,
            )

            transcription = transcribe_audio(audio_path, config.WHISPER_MODEL)
            prosody = analyze_prosody(audio_path)

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
            _voice_ok = True
        except Exception as e:
            logger.error("voice_analysis_failed", error=str(e))
            voice_result = {"score": 0, "confidence": "failed", "metrics": {}}
            transcription = {"full_text": "", "words": []}
            prosody = {}

        if _voice_ok:
            if config.TRUTH_CONTRACT_ENABLED:
                from workers.voice_analyzer import analyze_voice

                voice_result = analyze_voice(transcription, prosody)
            else:
                try:
                    from workers.voice_analyzer import analyze_voice_legacy

                    voice_result = analyze_voice_legacy(transcription, prosody)
                except Exception as e:
                    logger.error("voice_metrics_failed", error=str(e))
                    voice_result = {"score": 0, "confidence": "failed", "metrics": {}}

        _save_analysis(supabase, req.evaluation_id, "voice", voice_result)

        # Step 5.5: Story 7.5 — Tonality VAD (5a Vocal Foundation)
        # Story 8.3: dispatch via feature flag.
        if config.TRUTH_CONTRACT_ENABLED:
            from workers.tonality_analyzer import analyze_tonality

            tonality_result = analyze_tonality(audio_path)
        else:
            try:
                from workers.tonality_analyzer import analyze_tonality_legacy

                tonality_result = analyze_tonality_legacy(audio_path)
            except Exception as e:
                logger.error("tonality_analysis_failed", error=str(e))
                tonality_result = {
                    "disponivel": False,
                    "score": 0,
                    "diagnostico": "failed",
                    "feedback": str(e),
                    "warnings": [str(e)],
                }

        # Step 6: Deteccao de vicios de linguagem
        # Story 8.2: dispatch via feature flag.
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_fillers")
        if config.TRUTH_CONTRACT_ENABLED:
            from workers.filler_detector import analyze_fillers

            filler_result = analyze_fillers(transcription)
        else:
            try:
                from workers.filler_detector import detect_fillers_legacy

                filler_result = detect_fillers_legacy(transcription)
            except Exception as e:
                logger.error("filler_detection_failed", error=str(e))
                filler_result = {"score": 0, "confidence": "failed", "metrics": {}}

        _save_analysis(supabase, req.evaluation_id, "fillers", filler_result)

        # Step 6.5: Analise de identidade comunicativa (Epic 6)
        # Story 8.2: dispatch via feature flag.
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_identity")
        if config.TRUTH_CONTRACT_ENABLED:
            from workers.identity_analyzer import analyze_identity_tc

            identity_result = analyze_identity_tc(transcription)
        else:
            try:
                from workers.identity_analyzer import analyze_identity_legacy

                identity_result = analyze_identity_legacy(transcription)
            except Exception as e:
                logger.error("identity_analysis_failed", error=str(e))
                identity_result = {"score": 0, "diagnostico": "failed"}

        _save_analysis(supabase, req.evaluation_id, "identity", identity_result)

        # Step 6.6: Analise de abertura (Epic 6)
        # Story 8.3: dispatch via feature flag.
        # voice_result pode ser WorkerSuccess (TC) ou dict (legacy) — extrair metrics resiliente.
        _voice_metrics_for_opening = (
            voice_result.metrics
            if hasattr(voice_result, "metrics")
            else voice_result.get("metrics", voice_result)
        )
        _voice_duration = _voice_metrics_for_opening.get("audio_duration_seconds", 0)
        if config.TRUTH_CONTRACT_ENABLED:
            from workers.opening_analyzer import analyze_opening

            opening_result = analyze_opening(transcription, _voice_metrics_for_opening, _voice_duration)
        else:
            try:
                from workers.opening_analyzer import analyze_opening_legacy

                opening_result = analyze_opening_legacy(
                    transcription, _voice_metrics_for_opening, _voice_duration
                )
            except Exception as e:
                logger.error("opening_analysis_failed", error=str(e))
                opening_result = {"disponivel": False, "motivo": str(e)}

        # Step 7: Analise de variedade (meta-analyzer)
        # Story 8.1 T6: dispatch via feature flag.
        # - Flag ON: analyze_variety() retorna WorkerResult (Pydantic).
        #   _save_analysis detecta tipo e usa repositories.save_analysis_result
        #   (path Truth Contract).
        # - Flag OFF: analyze_variety_legacy() retorna dict (comportamento
        #   pre-Epic 8.0 preservado).
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_variety")
        if config.TRUTH_CONTRACT_ENABLED:
            # Truth Contract: analyze_variety ja captura excecoes internamente
            # e retorna WorkerFailure(crashed). Nao precisa try/except aqui.
            from workers.variety_analyzer import analyze_variety

            variety_result = analyze_variety(voice_result, gesture_result)
        else:
            # Legacy path: try/except pra preservar comportamento antigo
            try:
                from workers.variety_analyzer import analyze_variety_legacy

                variety_result = analyze_variety_legacy(voice_result, gesture_result)
            except Exception as e:
                logger.error("variety_analysis_failed", error=str(e))
                variety_result = {"score": 0, "confidence": "failed", "metrics": {}}

        _save_analysis(supabase, req.evaluation_id, "variety", variety_result)

        # Step 7.5: Story 7.3 — Storytelling Analyzer (bridge, hook, CTA, chemicals)
        # Story 8.3: dispatch via feature flag.
        # variety_result e opening_result podem ser WorkerResult (TC) ou dict (legacy).
        from contracts import WorkerSuccess as _WS

        if isinstance(variety_result, _WS):
            variety_metrics = variety_result.metrics
        elif isinstance(variety_result, dict):
            variety_metrics = variety_result.get("metrics")
        else:
            variety_metrics = None

        # opening_result para storytelling: se WorkerResult, extrai metrics como dict
        from contracts import WorkerFailure as _WF_check

        if isinstance(opening_result, _WS):
            _opening_for_storytelling = {**opening_result.metrics, "disponivel": True}
        elif isinstance(opening_result, _WF_check):
            _opening_for_storytelling = {"disponivel": False, "motivo": opening_result.failure_reason}
        else:
            _opening_for_storytelling = opening_result

        if config.TRUTH_CONTRACT_ENABLED:
            from workers.storytelling_analyzer import analyze_storytelling

            storytelling_result = analyze_storytelling(
                transcription,
                variety_metrics=variety_metrics,
                opening_result=_opening_for_storytelling,
            )
        else:
            try:
                from workers.storytelling_analyzer import analyze_storytelling_legacy

                storytelling_result = analyze_storytelling_legacy(
                    transcription,
                    variety_metrics=variety_metrics,
                    opening_result=_opening_for_storytelling,
                )
            except Exception as e:
                logger.error("storytelling_analysis_failed", error=str(e))
                storytelling_result = {
                    "disponivel": False,
                    "score": 0,
                    "diagnostico": "failed",
                    "suggestions": [str(e)],
                }

        # Step 8: Classificacao de arquetipos vocais — NOVO
        # Story 8.2: dispatch via feature flag.
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_archetypes")
        if config.TRUTH_CONTRACT_ENABLED:
            from workers.archetype_classifier import analyze_archetypes

            archetype_result = analyze_archetypes(audio_path)
        else:
            try:
                from workers.archetype_classifier import classify_archetypes_legacy

                archetype_result = classify_archetypes_legacy(audio_path)
            except Exception as e:
                logger.error("archetype_classification_failed", error=str(e))
                archetype_result = {"score": 0, "confidence": "failed", "metrics": {}}

        _save_analysis(supabase, req.evaluation_id, "archetypes", archetype_result)

        # Step 9: Buscar contexto do orador + Agregar metricas
        # Story 8.4: aggregator agora recebe dict[str, WorkerResult] diretamente.
        # O shim _wr_to_agg() foi removido do path TRUTH_CONTRACT_ENABLED=true.

        # voice_result pode ter formato nested {"score":..,"metrics":{...}}
        # (compat legacy: voice_result pode ser WorkerResult ou dict)
        _voice_metrics_raw = (
            voice_result.metrics if isinstance(voice_result, _WS) else
            voice_result.get("metrics", voice_result) if isinstance(voice_result, dict) else {}
        )
        _posture_frames = (
            posture_result.metrics.get("total_frames", 0) if isinstance(posture_result, _WS) else
            posture_result.get("metrics", {}).get("total_frames", 0) if isinstance(posture_result, dict) else 0
        )
        video_metadata = {
            "duration_seconds": _voice_metrics_raw.get("audio_duration_seconds", 0),
            "frames_processed": _posture_frames,
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

        if config.TRUTH_CONTRACT_ENABLED:
            # ----------------------------------------------------------------
            # PATH TRUTH CONTRACT (flag ON)
            # Story 8.4: sem shim, sem _wr_to_agg().
            # Congruencia e temporal rodam ANTES do aggregator (Option B):
            # nao afetam overall_score (augmentation dims), mas precisam de
            # dados dos scoring workers ja processados.
            # ----------------------------------------------------------------

            # Step 9.5: Analise de congruencia (cruzar sinais entre canais)
            from workers.congruence_analyzer import analyze_congruence

            # Congruence precisa de detailed_metrics dict — extrair de WorkerSuccess.metrics
            _scoring_metrics_for_congruence: dict = {}
            for _dim, _res in [
                ("posture", posture_result),
                ("gesture", gesture_result),
                ("voice", voice_result),
                ("fillers", filler_result),
                ("variety", variety_result),
                ("archetypes", archetype_result),
                ("facial", facial_result),
                ("tonality", tonality_result),
                ("identity", identity_result),
                ("opening", opening_result),
            ]:
                if isinstance(_res, _WS):
                    _scoring_metrics_for_congruence[_dim] = _res.metrics
            congruence_result = analyze_congruence(_scoring_metrics_for_congruence)

            # Step 9.6: Analise temporal (3 tercos)
            from workers.temporal_analyzer import analyze_temporal

            # Temporal precisa de dicts com metricas brutas dos workers
            _voice_dict = {"metrics": _voice_metrics_raw} if _voice_metrics_raw else {}
            _variety_metrics_raw = (
                variety_result.metrics if isinstance(variety_result, _WS) else
                variety_result.get("metrics", variety_result) if isinstance(variety_result, dict) else {}
            )
            _variety_dict = {"metrics": _variety_metrics_raw}
            _filler_metrics_raw = (
                filler_result.metrics if isinstance(filler_result, _WS) else
                filler_result.get("metrics", filler_result) if isinstance(filler_result, dict) else {}
            )
            _filler_dict = {"metrics": _filler_metrics_raw}
            temporal_result = analyze_temporal(
                _voice_dict,
                _variety_dict,
                _filler_dict,
                duration_seconds=video_metadata.get("duration_seconds", 0),
            )

            # Construir dict[str, WorkerResult] com todas 13 dimensoes
            all_results: dict = {
                "posture": posture_result,
                "gesture": gesture_result,
                "voice": voice_result,
                "fillers": filler_result,
                "variety": variety_result,
                "archetypes": archetype_result,
                "facial": facial_result,
                "tonality": tonality_result,
                "identity": identity_result,
                "opening": opening_result,
                "storytelling": storytelling_result,
                "congruence": congruence_result,
                "temporal": temporal_result,
            }

            from workers.aggregator import aggregate_metrics

            aggregated = aggregate_metrics(
                req.evaluation_id,
                all_results,
                video_metadata,
                contexto=eval_contexto,
                motivacao=eval_motivacao,
            )

            # Construir full_detailed a partir do aggregated (ja inclui augmentation dims)
            full_detailed = {**aggregated["detailed_metrics"]}
            # Story 5.3: expor contexto + pesos no relatorio (badge + transparencia)
            if aggregated.get("contexto"):
                full_detailed["contexto"] = aggregated["contexto"]
            if aggregated.get("pesos_utilizados"):
                full_detailed["pesos_utilizados"] = aggregated["pesos_utilizados"]

        else:
            # ----------------------------------------------------------------
            # PATH LEGACY (flag OFF)
            # Story 8.4: shim _wr_to_agg() preservado APENAS aqui.
            # aggregate_metrics_legacy() com 6 dicts separados (score=0 fallback
            # documentado — eh legacy, nao bug).
            # ----------------------------------------------------------------

            # Converter WorkerResult → dict compatível com aggregator legacy (espera .get())
            def _wr_to_agg(r):
                if isinstance(r, _WS):
                    return {"score": r.score, "confidence": "high", "metrics": r.metrics}
                if isinstance(r, _WF_check):
                    return {"score": 0, "confidence": "failed", "metrics": r.metrics if r.metrics else {}}
                return r

            from workers.aggregator import aggregate_metrics_legacy

            aggregated = aggregate_metrics_legacy(
                req.evaluation_id,
                _wr_to_agg(posture_result),
                _wr_to_agg(gesture_result),
                _wr_to_agg(voice_result),
                _wr_to_agg(filler_result),
                _wr_to_agg(variety_result),
                _wr_to_agg(archetype_result),
                video_metadata,
                contexto=eval_contexto,
                motivacao=eval_motivacao,
            )

            # Adicionar identity e opening ao aggregated (informativo)
            aggregated["identity"] = _wr_to_agg(identity_result)
            aggregated["opening"] = _wr_to_agg(opening_result)

            # Step 9.5: Analise de congruencia (cruzar sinais entre canais)
            try:
                from workers.congruence_analyzer import analyze_congruence_legacy

                aggregated["congruence"] = analyze_congruence_legacy(aggregated["detailed_metrics"])
            except Exception as e:
                logger.warning("congruence_analysis_failed", error=str(e))

            # Step 9.6: Analise temporal (3 tercos)
            try:
                from workers.temporal_analyzer import analyze_temporal_legacy

                aggregated["temporal"] = analyze_temporal_legacy(
                    _wr_to_agg(voice_result),
                    _wr_to_agg(variety_result),
                    _wr_to_agg(filler_result),
                    duration_seconds=video_metadata.get("duration_seconds", 0),
                )
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
        # Story 8.3: facial_result pode ser WorkerSuccess (TC) ou dict (legacy).
        from contracts import WorkerFailure as _WF

        if facial_result and not isinstance(facial_result, _WF):
            _facial_data = (
                facial_result.metrics if isinstance(facial_result, _WS) else facial_result
            )
            if _facial_data and _facial_data.get("disponivel", True):
                full_detailed["facial"] = _facial_data
        # Story 7.5: expor tonality VAD no relatorio
        if tonality_result and not isinstance(tonality_result, _WF):
            _tonality_data = (
                tonality_result.metrics if isinstance(tonality_result, _WS) else tonality_result
            )
            if _tonality_data and _tonality_data.get("disponivel", True):
                full_detailed["tonality"] = _tonality_data
        # Story 7.3: expor analise de storytelling no relatorio
        if storytelling_result and not isinstance(storytelling_result, _WF):
            _storytelling_data = (
                storytelling_result.metrics
                if isinstance(storytelling_result, _WS)
                else storytelling_result
            )
            if _storytelling_data and _storytelling_data.get("disponivel", True):
                full_detailed["storytelling"] = _storytelling_data

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
                # Story 8.3: shadow squad expects dicts — downgrade WorkerResult if needed.
                def _to_dict(r):
                    return r.model_dump() if hasattr(r, "model_dump") else r

                _run_squad_shadow(
                    evaluation_id=req.evaluation_id,
                    video_url=req.video_url,
                    video_metadata=video_metadata,
                    worker_results={
                        "voice_analyzer": _to_dict(voice_result),
                        "filler_detector": _to_dict(filler_result),
                        "posture_analyzer": _to_dict(posture_result),
                        "gesture_analyzer": _to_dict(gesture_result),
                        "facial_analyzer": _to_dict(facial_result),
                        "opening_analyzer": _to_dict(opening_result),
                        "tonality_analyzer": _to_dict(tonality_result),
                    },
                    evaluation_context={
                        "motivacao": eval_motivacao,
                        "contexto_v1": eval_contexto,
                    }
                    if (eval_motivacao or eval_contexto)
                    else None,
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
        import traceback
        logger.error(
            "pipeline_error",
            evaluation_id=req.evaluation_id,
            error=str(e),
            traceback=traceback.format_exc(),
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
