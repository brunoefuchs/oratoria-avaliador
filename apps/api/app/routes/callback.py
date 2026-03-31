from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.repositories import evaluation_repo

router = APIRouter()


class StatusUpdateRequest(BaseModel):
    substatus: str


class CallbackRequest(BaseModel):
    status: str
    error_message: str | None = None
    results: dict | None = None


@router.post("/evaluations/{evaluation_id}/status-update")
async def status_update(
    evaluation_id: str,
    body: StatusUpdateRequest,
    x_callback_secret: str = Header(),
):
    if x_callback_secret != settings.callback_secret:
        raise HTTPException(status_code=403, detail="Invalid callback secret")

    await evaluation_repo.update_evaluation(
        evaluation_id, {"substatus": body.substatus}
    )
    return {"ok": True}


@router.post("/evaluations/{evaluation_id}/callback")
async def callback(
    evaluation_id: str,
    body: CallbackRequest,
    x_callback_secret: str = Header(),
):
    if x_callback_secret != settings.callback_secret:
        raise HTTPException(status_code=403, detail="Invalid callback secret")

    updates: dict = {"status": body.status}
    if body.error_message:
        updates["error_message"] = body.error_message
    if body.status == "completed":
        from datetime import datetime, timezone

        updates["completed_at"] = datetime.now(timezone.utc).isoformat()

    await evaluation_repo.update_evaluation(evaluation_id, updates)
    return {"ok": True}
