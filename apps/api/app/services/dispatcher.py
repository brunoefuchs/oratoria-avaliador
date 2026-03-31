import httpx
import structlog

from app.config import settings
from app.repositories import evaluation_repo

logger = structlog.get_logger()


async def dispatch_to_ml_worker(evaluation_id: str, video_url: str) -> None:
    callback_url = f"{settings.ml_worker_url.rstrip('/')}"

    await evaluation_repo.update_evaluation(
        evaluation_id, {"status": "processing", "substatus": "splitting"}
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{settings.ml_worker_url}/process",
                json={
                    "evaluation_id": evaluation_id,
                    "video_url": video_url,
                    "callback_url": callback_url,
                },
                headers={"X-Callback-Secret": settings.callback_secret},
            )
        logger.info(
            "dispatched_to_ml_worker",
            evaluation_id=evaluation_id,
        )
    except httpx.HTTPError as e:
        logger.error(
            "ml_worker_dispatch_failed",
            evaluation_id=evaluation_id,
            error=str(e),
        )
        await evaluation_repo.update_evaluation(
            evaluation_id,
            {
                "status": "error",
                "error_message": f"ML worker indisponivel: {e}",
            },
        )
