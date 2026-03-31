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

        # Future steps (Epic 2) will continue here:
        # - analyzing_posture
        # - analyzing_gesture
        # - analyzing_voice
        # - analyzing_fillers
        # - generating_report

        # For now, mark as analyzed (pipeline skeleton complete)
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
