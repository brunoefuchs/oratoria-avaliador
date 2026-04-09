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
    "analyzing_variety",
    "analyzing_archetypes",
    "generating_report",
]

STEP_LABELS = {
    "splitting": "Separando audio e video...",
    "analyzing_posture": "Analisando postura...",
    "analyzing_gesture": "Analisando gestual e contato visual...",
    "analyzing_voice": "Analisando voz e prosodia...",
    "analyzing_fillers": "Detectando vicios de linguagem...",
    "analyzing_variety": "Analisando variedade vocal...",
    "analyzing_archetypes": "Classificando arquetipos vocais...",
    "generating_report": "Gerando relatorio de coaching...",
}

VALID_DIMENSIONS = ["posture", "gesture", "voice", "fillers", "variety", "archetypes"]

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

    report_data = report.data[0] if report.data else {}
    agg_data = agg.data[0] if agg.data else {}

    return {
        "evaluation": {
            "id": evaluation["id"],
            "status": evaluation["status"],
            "duration_seconds": evaluation.get("duration_seconds"),
        },
        "overall_score": agg_data.get("overall_score", 0),
        "dimension_scores": agg_data.get("dimension_scores", {}),
        "detailed_metrics": agg_data.get("detailed_metrics", {}),
        "incomplete_dimensions": agg_data.get("incomplete_dimensions", []),
        "report": {
            # Campos novos (v2)
            "resumo": report_data.get("summary", ""),
            "forcas": report_data.get("forcas", []),
            "melhorias_80_20": report_data.get("melhorias", []),
            "dimensoes": report_data.get("dimension_feedback", {}),
            "plano_12_semanas": report_data.get("plano_12_semanas", []),
            "mensagem_final": report_data.get("mensagem_final", ""),
            # Retrocompatibilidade (v1)
            "summary": report_data.get("summary", ""),
            "dimension_feedback": report_data.get("dimension_feedback", {}),
        },
    }


@router.get("/evaluations/{evaluation_id}/report/{dimension}")
async def get_dimension_detail(evaluation_id: str, dimension: str):
    if dimension not in VALID_DIMENSIONS:
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


class ContextRequest(BaseModel):
    sentimento: int | None = None
    maior_medo: list[str] | None = None
    contexto: str | None = None
    avaliado_antes: bool | None = None
    objetivo: str | None = None


@router.post("/evaluations/{evaluation_id}/context", status_code=201)
async def save_context(evaluation_id: str, body: ContextRequest):
    if body.sentimento is not None and (body.sentimento < 1 or body.sentimento > 5):
        raise HTTPException(status_code=400, detail="Sentimento must be 1-5")

    from app.repositories.evaluation_repo import _get_supabase

    supabase = _get_supabase()

    data: dict = {"evaluation_id": evaluation_id}
    if body.sentimento is not None:
        data["sentimento"] = body.sentimento
    if body.maior_medo is not None:
        data["maior_medo"] = body.maior_medo
    if body.contexto is not None:
        data["contexto"] = body.contexto
    if body.avaliado_antes is not None:
        data["avaliado_antes"] = body.avaliado_antes
    if body.objetivo is not None:
        data["objetivo"] = body.objetivo

    supabase.table("evaluation_context").upsert(data).execute()
    return {"ok": True}


@router.get("/evaluations/{evaluation_id}/context")
async def get_context(evaluation_id: str):
    from app.repositories.evaluation_repo import _get_supabase

    supabase = _get_supabase()
    result = (
        supabase.table("evaluation_context")
        .select("*")
        .eq("evaluation_id", evaluation_id)
        .execute()
    )
    if not result.data:
        return {"context": None}
    return {"context": result.data[0]}


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


@router.get("/evaluations/{evaluation_id}/replay")
async def get_replay_data(evaluation_id: str):
    """Retorna URL assinada do video + eventos temporais para replay."""
    from app.repositories.evaluation_repo import _get_supabase

    supabase = _get_supabase()

    evaluation = await evaluation_repo.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # URL assinada do video (expira em 1h)
    video_url = evaluation.get("video_url", "")
    try:
        signed = supabase.storage.from_("videos").create_signed_url(video_url, 3600)
        signed_url = signed.get("signedURL", "") if isinstance(signed, dict) else ""
    except Exception:
        signed_url = ""

    # Buscar eventos temporais das analises
    events = []

    # Clusters de fillers
    fillers_result = (
        supabase.table("analysis_results")
        .select("metrics")
        .eq("evaluation_id", evaluation_id)
        .eq("dimension", "fillers")
        .execute()
    )
    if fillers_result.data:
        metrics = fillers_result.data[0].get("metrics", {})
        for cluster in metrics.get("clusters", []):
            events.append({
                "type": "cluster",
                "start": cluster.get("inicio", 0),
                "end": cluster.get("fim", cluster.get("inicio", 0) + 5),
            })

    # Trechos monotonos
    variety_result = (
        supabase.table("analysis_results")
        .select("metrics")
        .eq("evaluation_id", evaluation_id)
        .eq("dimension", "variety")
        .execute()
    )
    if variety_result.data:
        metrics = variety_result.data[0].get("metrics", {})
        trechos_raw = metrics.get("trechos_monotonos", [])
        # trechos_monotonos pode ser dict {velocidade: [...], volume: [...], pitch: [...]} ou lista
        trechos_flat = []
        if isinstance(trechos_raw, dict):
            for v in trechos_raw.values():
                if isinstance(v, list):
                    trechos_flat.extend(v)
        elif isinstance(trechos_raw, list):
            trechos_flat = trechos_raw
        for trecho in trechos_flat:
            if not isinstance(trecho, dict):
                continue
            events.append({
                "type": "monotono",
                "start": trecho.get("inicio", 0),
                "end": trecho.get("fim", trecho.get("inicio", 0) + 15),
            })

    # Pausas estrategicas (momentos de alta performance)
    voice_result = (
        supabase.table("analysis_results")
        .select("metrics")
        .eq("evaluation_id", evaluation_id)
        .eq("dimension", "voice")
        .execute()
    )
    if voice_result.data:
        metrics = voice_result.data[0].get("metrics", {})
        pausas = metrics.get("pausas", {})
        for pausa in pausas.get("estrategicas", []):
            events.append({
                "type": "alta_performance",
                "start": pausa.get("start", 0),
                "end": pausa.get("end", pausa.get("start", 0) + 2),
            })

    return {
        "video_url": signed_url,
        "events": events,
        "duration_seconds": evaluation.get("duration_seconds", 0),
    }


@router.post("/evaluations/{evaluation_id}/share", status_code=201)
async def create_share(evaluation_id: str):
    """Gera link de compartilhamento para um relatorio."""
    from app.repositories.evaluation_repo import _get_supabase

    supabase = _get_supabase()

    evaluation = await evaluation_repo.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Verificar se ja existe share ativo
    existing = (
        supabase.table("report_shares")
        .select("share_token, expires_at")
        .eq("evaluation_id", evaluation_id)
        .gte("expires_at", "now()")
        .execute()
    )

    if existing.data:
        return {"share_token": existing.data[0]["share_token"], "expires_at": existing.data[0]["expires_at"]}

    result = (
        supabase.table("report_shares")
        .insert({"evaluation_id": evaluation_id})
        .execute()
    )

    share = result.data[0]
    return {"share_token": share["share_token"], "expires_at": share["expires_at"]}


@router.get("/shared/{share_token}")
async def get_shared_report(share_token: str):
    """Acessa relatorio via link de compartilhamento (sem auth)."""
    from app.repositories.evaluation_repo import _get_supabase

    supabase = _get_supabase()

    share = (
        supabase.table("report_shares")
        .select("evaluation_id, expires_at")
        .eq("share_token", share_token)
        .execute()
    )

    if not share.data:
        raise HTTPException(status_code=404, detail="Link nao encontrado")

    from datetime import datetime, timezone

    expires = datetime.fromisoformat(share.data[0]["expires_at"].replace("Z", "+00:00"))
    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Link expirado")

    evaluation_id = share.data[0]["evaluation_id"]

    # Reutilizar logica do get_evaluation_report
    return await get_evaluation_report(evaluation_id)


@router.get("/evaluations")
async def list_evaluations(user_token: str | None = None):
    """Lista avaliacoes por user_token para dashboard de evolucao."""
    if not user_token:
        raise HTTPException(status_code=400, detail="user_token is required")

    from app.repositories.evaluation_repo import _get_supabase

    supabase = _get_supabase()

    evals = (
        supabase.table("evaluations")
        .select("id, status, created_at, duration_seconds")
        .eq("user_token", user_token)
        .eq("status", "completed")
        .order("created_at")
        .execute()
    )

    if not evals.data:
        return {"evaluations": []}

    results = []
    for ev in evals.data:
        agg = (
            supabase.table("aggregated_metrics")
            .select("overall_score, dimension_scores")
            .eq("evaluation_id", ev["id"])
            .execute()
        )
        agg_data = agg.data[0] if agg.data else {}
        results.append({
            "id": ev["id"],
            "created_at": ev["created_at"],
            "overall_score": agg_data.get("overall_score", 0),
            "dimension_scores": agg_data.get("dimension_scores", {}),
        })

    return {"evaluations": results}
