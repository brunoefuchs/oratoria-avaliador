from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.models.evaluation import (
    ApiErrorResponse,
    EvaluationResponse,
    EvaluationStatusResponse,
)
from app.repositories import evaluation_repo

router = APIRouter()

STEP_ORDER = [
    "splitting",
    "analyzing_posture",
    "analyzing_gesture",
    "analyzing_voice",
    "analyzing_fillers",
    "generating_report",
]

STEP_LABELS = {
    "splitting": "Separando audio e video...",
    "analyzing_posture": "Analisando postura...",
    "analyzing_gesture": "Analisando gestual...",
    "analyzing_voice": "Analisando tom de voz...",
    "analyzing_fillers": "Detectando vicios de linguagem...",
    "generating_report": "Gerando relatorio...",
}

ALLOWED_CONTENT_TYPES = {"video/mp4", "video/webm"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB


@router.post("/evaluations", status_code=201, response_model=EvaluationResponse)
async def create_evaluation(video: UploadFile):
    # Validate content type
    if video.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=ApiErrorResponse(
                code="INVALID_VIDEO_FORMAT",
                message="Formato de video nao suportado. Use MP4 ou WebM.",
            ).model_dump(),
        )

    # Read file and validate size
    file_bytes = await video.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=ApiErrorResponse(
                code="VIDEO_TOO_LARGE",
                message="Video deve ter no maximo 500MB.",
            ).model_dump(),
        )

    # Upload to Supabase Storage
    ext = video.filename.rsplit(".", 1)[-1] if video.filename else "mp4"
    import uuid

    from app.services.dispatcher import dispatch_to_ml_worker

    temp_id = str(uuid.uuid4())
    storage_path = f"evaluations/{temp_id}/video.{ext}"

    try:
        evaluation_repo.upload_video(file_bytes, storage_path, video.content_type)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ApiErrorResponse(
                code="UPLOAD_FAILED",
                message=f"Falha ao fazer upload do video: {e}",
            ).model_dump(),
        )

    # Create evaluation record
    evaluation = await evaluation_repo.create_evaluation(video_url=storage_path)

    # Dispatch to ML worker (fire-and-forget)
    import asyncio

    asyncio.create_task(
        dispatch_to_ml_worker(evaluation["id"], evaluation["video_url"])
    )

    return JSONResponse(
        status_code=201,
        content={
            "id": evaluation["id"],
            "status": evaluation["status"],
            "video_url": evaluation["video_url"],
            "created_at": evaluation["created_at"],
        },
    )


@router.get(
    "/evaluations/{evaluation_id}/status",
    response_model=EvaluationStatusResponse,
)
async def get_evaluation_status(evaluation_id: str):
    evaluation = await evaluation_repo.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    substatus = evaluation.get("substatus")
    steps_completed = 0
    current_step = None

    if substatus and substatus in STEP_ORDER:
        steps_completed = STEP_ORDER.index(substatus)
        current_step = STEP_LABELS.get(substatus)

    if evaluation["status"] == "completed":
        steps_completed = len(STEP_ORDER)

    return {
        "id": evaluation["id"],
        "status": evaluation["status"],
        "substatus": substatus,
        "progress": {
            "steps_completed": steps_completed,
            "steps_total": len(STEP_ORDER),
            "current_step": current_step,
        },
    }


@router.get("/evaluations/{evaluation_id}/report")
async def get_evaluation_report(evaluation_id: str):
    from app.repositories.evaluation_repo import _get_supabase

    supabase = _get_supabase()

    evaluation = await evaluation_repo.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Get aggregated metrics
    agg = (
        supabase.table("aggregated_metrics")
        .select("*")
        .eq("evaluation_id", evaluation_id)
        .execute()
    )

    # Get report
    report = (
        supabase.table("reports")
        .select("*")
        .eq("evaluation_id", evaluation_id)
        .execute()
    )

    return {
        "evaluation": {
            "id": evaluation["id"],
            "status": evaluation["status"],
            "duration_seconds": evaluation.get("duration_seconds"),
        },
        "overall_score": agg.data[0]["overall_score"] if agg.data else 0,
        "dimension_scores": (agg.data[0]["dimension_scores"] if agg.data else {}),
        "detailed_metrics": (agg.data[0]["detailed_metrics"] if agg.data else {}),
        "incomplete_dimensions": (
            agg.data[0]["incomplete_dimensions"] if agg.data else []
        ),
        "report": {
            "summary": report.data[0]["summary"] if report.data else "",
            "dimension_feedback": (
                report.data[0]["dimension_feedback"] if report.data else {}
            ),
        },
    }


@router.get("/evaluations/{evaluation_id}/report/{dimension}")
async def get_dimension_detail(evaluation_id: str, dimension: str):
    valid = ["posture", "gesture", "voice", "fillers"]
    if dimension not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid dimension: {dimension}")

    from app.repositories.evaluation_repo import _get_supabase

    supabase = _get_supabase()

    # Get analysis result for dimension
    result = (
        supabase.table("analysis_results")
        .select("*")
        .eq("evaluation_id", evaluation_id)
        .eq("dimension", dimension)
        .execute()
    )

    # Get report feedback for dimension
    report = (
        supabase.table("reports")
        .select("dimension_feedback")
        .eq("evaluation_id", evaluation_id)
        .execute()
    )

    feedback = {}
    if report.data:
        feedback = report.data[0].get("dimension_feedback", {}).get(dimension, {})

    return {
        "dimension": dimension,
        "score": result.data[0]["score"] if result.data else 0,
        "confidence": result.data[0]["confidence"] if result.data else "failed",
        "metrics": result.data[0]["metrics"] if result.data else {},
        "feedback": feedback,
    }


class RatingRequest(BaseModel):
    rating: int
    comment: str | None = None


@router.post("/evaluations/{evaluation_id}/rating", status_code=201)
async def create_rating(evaluation_id: str, body: RatingRequest):
    if body.rating < 1 or body.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    from app.repositories.evaluation_repo import _get_supabase

    supabase = _get_supabase()

    data = {
        "evaluation_id": evaluation_id,
        "rating": body.rating,
    }
    if body.comment:
        data["comment"] = body.comment

    supabase.table("report_ratings").upsert(data).execute()
    return {"ok": True}
