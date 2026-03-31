from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.models.evaluation import ApiErrorResponse, EvaluationResponse
from app.repositories import evaluation_repo

router = APIRouter()

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

    return JSONResponse(
        status_code=201,
        content={
            "id": evaluation["id"],
            "status": evaluation["status"],
            "video_url": evaluation["video_url"],
            "created_at": evaluation["created_at"],
        },
    )
