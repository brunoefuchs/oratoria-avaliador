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
ORATORIA_SHADOW_MODE_ENABLED = os.getenv("ORATORIA_SHADOW_MODE_ENABLED", "false").lower() == "true"

# Feature flag: Truth Contract (Story 8.1).
# Quando true, workers migrados retornam WorkerResult (Pydantic) e analysis_results
# grava dimension_status + failure_reason. Quando false, usa path legacy com
# score=0 fallback em falha (comportamento pre-Epic 8.0).
#
# Rollout seguro: env var → reload basta (sem restart). Kill switch imediato.
# Story 8.3: default AGORA e true — todos os 13 workers migrados.
# Kill switch: env var TRUTH_CONTRACT_ENABLED=false reverte pra legacy.
#
# Workers migrados (Story 8.2): posture, gesture, voice, fillers, archetypes, identity
# Workers migrados (Story 8.3): facial, tonality, opening, storytelling, temporal, congruence
# Total migrado: 13 workers (incluindo variety da Story 8.1)
TRUTH_CONTRACT_ENABLED = os.getenv("TRUTH_CONTRACT_ENABLED", "true").lower() == "true"
