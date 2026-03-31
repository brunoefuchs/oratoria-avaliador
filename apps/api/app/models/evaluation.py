from datetime import datetime

from pydantic import BaseModel


class EvaluationResponse(BaseModel):
    id: str
    status: str
    video_url: str
    created_at: datetime


class EvaluationStatusResponse(BaseModel):
    id: str
    status: str
    substatus: str | None = None
    progress: dict | None = None


class ApiErrorResponse(BaseModel):
    code: str
    message: str
    details: dict | None = None
