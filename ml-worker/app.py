import asyncio
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
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.get_level_from_name(config.LOG_LEVEL)
    ),
)

logger = structlog.get_logger()

app = FastAPI(title="Oratoria ML Worker", version="0.1.0")


class ProcessRequest(BaseModel):
    evaluation_id: str
    video_url: str
    callback_url: str


@app.get("/health")
async def health_check():
    return {"status": "ok"}


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
    """Save analysis result to database."""
    supabase.table("analysis_results").upsert(
        {
            "evaluation_id": evaluation_id,
            "dimension": dimension,
            "score": result.get("score", 0),
            "metrics": result.get("metrics", result),
            "confidence": result.get("confidence", "high"),
        }
    ).execute()


async def _run_pipeline(req: ProcessRequest):
    start = time.time()
    logger.info("pipeline_start", evaluation_id=req.evaluation_id)

    try:
        # Step 1: Download video from Supabase Storage
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

        # Step 2: Split video into audio + video
        audio_path, video_path = split_video(video_path)

        logger.info(
            "pipeline_split_done",
            evaluation_id=req.evaluation_id,
            audio_path=audio_path,
            total_seconds=round(time.time() - start, 2),
        )

        # Step 3: Posture analysis
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_posture")
        try:
            from workers.posture_analyzer import analyze_posture

            posture_result = analyze_posture(video_path)
        except Exception as e:
            logger.error("posture_analysis_failed", error=str(e))
            posture_result = {"score": 0, "confidence": "failed", "metrics": {}}

        _save_analysis(supabase, req.evaluation_id, "posture", posture_result)

        # Step 4: Gesture & gaze analysis
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_gesture")
        try:
            from workers.gesture_analyzer import analyze_gestures

            gesture_result = analyze_gestures(video_path)
        except Exception as e:
            logger.error("gesture_analysis_failed", error=str(e))
            gesture_result = {"score": 0, "confidence": "failed", "metrics": {}}

        _save_analysis(supabase, req.evaluation_id, "gesture", gesture_result)

        # Step 5: Voice analysis (Whisper + Parselmouth)
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

            # Save transcription
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

        # Step 6: Filler detection
        await _notify_status(req.callback_url, req.evaluation_id, "analyzing_fillers")
        try:
            from workers.filler_detector import detect_fillers

            filler_result = detect_fillers(transcription)
        except Exception as e:
            logger.error("filler_detection_failed", error=str(e))
            filler_result = {"score": 0, "confidence": "failed", "metrics": {}}

        _save_analysis(supabase, req.evaluation_id, "fillers", filler_result)

        # Step 7: Aggregate metrics
        from workers.aggregator import aggregate_metrics

        video_metadata = {
            "duration_seconds": voice_result.get("audio_duration_seconds", 0),
            "frames_processed": posture_result.get("metrics", {}).get(
                "total_frames", 0
            ),
        }

        aggregated = aggregate_metrics(
            req.evaluation_id,
            posture_result,
            gesture_result,
            voice_result,
            filler_result,
            video_metadata,
        )

        supabase.table("aggregated_metrics").insert(
            {
                "evaluation_id": req.evaluation_id,
                "overall_score": aggregated["overall_score"],
                "dimension_scores": aggregated["dimension_scores"],
                "detailed_metrics": aggregated["detailed_metrics"],
                "incomplete_dimensions": aggregated["incomplete_dimensions"],
                "video_metadata": aggregated["video_metadata"],
            }
        ).execute()

        await _notify_complete(req.callback_url, req.evaluation_id, "analyzed")

    except Exception as e:
        logger.error(
            "pipeline_error",
            evaluation_id=req.evaluation_id,
            error=str(e),
        )
        await _notify_complete(
            req.callback_url, req.evaluation_id, "error", error_message=str(e)
        )


@app.post("/process")
async def process_video(
    req: ProcessRequest,
    x_callback_secret: str = Header(),
):
    if x_callback_secret != config.CALLBACK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid callback secret")

    # Fire-and-forget: run pipeline in background
    asyncio.create_task(_run_pipeline(req))

    return {"accepted": True, "evaluation_id": req.evaluation_id}
