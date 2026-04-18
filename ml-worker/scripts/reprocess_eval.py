"""Re-processa video de eval existente com flags atuais do ml-worker.

Uso: .venv/bin/python scripts/reprocess_eval.py <source_eval_id> [label]
"""

import os
import sys
import uuid

import httpx
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ML_WORKER = os.environ.get("ML_WORKER_URL", "http://localhost:7860")
CALLBACK = os.environ.get("CALLBACK_URL", "http://localhost:8002/api/ml-callback")
SECRET = os.environ.get("CALLBACK_SECRET", "oratoria-dev-secret-2026")


def main(source_id: str, label: str = ""):
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    src = sb.table("evaluations").select("video_url").eq("id", source_id).single().execute()
    video_path = src.data["video_url"]

    new_id = str(uuid.uuid4())
    sb.table("evaluations").insert(
        {"id": new_id, "video_url": video_path, "status": "processing"}
    ).execute()

    r = httpx.post(
        f"{ML_WORKER}/process",
        json={"evaluation_id": new_id, "video_url": video_path, "callback_url": CALLBACK},
        headers={"X-Callback-Secret": SECRET},
        timeout=30,
    )
    r.raise_for_status()
    print(f"[{label}] new eval: {new_id}")
    print(f"[{label}] report: http://localhost:3000/report/{new_id}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
