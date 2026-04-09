import uuid
from datetime import datetime, timezone

from app.config import settings

_supabase_client = None


def _get_supabase():
    global _supabase_client
    if _supabase_client is None:
        from supabase import ClientOptions, create_client

        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
            options=ClientOptions(
                postgrest_client_timeout=30,
                storage_client_timeout=120,
            ),
        )
    return _supabase_client


async def create_evaluation(video_url: str) -> dict:
    supabase = _get_supabase()
    evaluation_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    data = {
        "id": evaluation_id,
        "video_url": video_url,
        "status": "uploaded",
        "created_at": now,
    }

    result = supabase.table("evaluations").insert(data).execute()
    return result.data[0]


async def get_evaluation(evaluation_id: str) -> dict | None:
    supabase = _get_supabase()
    result = supabase.table("evaluations").select("*").eq("id", evaluation_id).execute()
    return result.data[0] if result.data else None


async def update_evaluation(evaluation_id: str, updates: dict) -> dict | None:
    supabase = _get_supabase()
    result = (
        supabase.table("evaluations").update(updates).eq("id", evaluation_id).execute()
    )
    return result.data[0] if result.data else None


def upload_video(file_bytes: bytes, path: str, content_type: str) -> str:
    supabase = _get_supabase()
    supabase.storage.from_("videos").upload(
        path, file_bytes, {"content-type": content_type}
    )
    return path
