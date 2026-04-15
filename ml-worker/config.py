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

# Feature flag: shadow mode do squad oratoria-avaliador.
# Quando true, o squad roda em paralelo ao report_generator existente.
# Não altera comportamento user-facing — só loga decisões para comparação.
# Default false. Ativar via env var ORATORIA_SHADOW_MODE_ENABLED=true.
ORATORIA_SHADOW_MODE_ENABLED = (
    os.getenv("ORATORIA_SHADOW_MODE_ENABLED", "false").lower() == "true"
)
