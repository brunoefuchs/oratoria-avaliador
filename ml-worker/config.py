import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CALLBACK_SECRET = os.getenv("CALLBACK_SECRET", "dev-secret")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
