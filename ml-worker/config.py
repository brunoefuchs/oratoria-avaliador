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

# Feature flag: Epic 9 State of the Art (Story 9.1).
# Quando true, aggregator usa nova formula de pesos (6 scoring dims) + SECONDARY_DIMENSIONS
# separadas + confidence badges no payload. Schema bump pra v1.2.0.
# Default false — rollback instantaneo garantido. v0.6.0 preservada bit-identica.
#
# Gate 2 antes de flip em prod: 10 videos smoke, delta overall_score <=15pt,
# rastreabilidade por fórmula, direção consistente (monotonicos ↓, variados ↑).
STATE_OF_ART_ENABLED = os.getenv("STATE_OF_ART_ENABLED", "false").lower() == "true"


def is_state_of_art_enabled() -> bool:
    """Helper testavel pra leitura da flag Epic 9.

    Usar este helper em vez de ler a constante diretamente quando precisar
    monkeypatchar em testes (pytest.MonkeyPatch.setenv + reimport).
    """
    return os.getenv("STATE_OF_ART_ENABLED", "false").strip().lower() == "true"


# Feature flag: Epic 9 Story 9.2 — Whisper large-v3-turbo.
# Quando true (default), voice_analyzer tenta "turbo" e faz fallback para WHISPER_MODEL
# (medium) se load falhar. Rollback explicito via WHISPER_TURBO_ENABLED=false.
WHISPER_TURBO_ENABLED = os.getenv("WHISPER_TURBO_ENABLED", "true").lower() == "true"


def is_whisper_turbo_enabled() -> bool:
    """Helper testavel pra flag Story 9.2."""
    return os.getenv("WHISPER_TURBO_ENABLED", "true").strip().lower() == "true"


# Feature flag: Epic 9 Story 9.2 — Model Orchestrator (VRAM management).
# Default false ate Gate 1 PASS (vram_check.py peak <=7.5GB). Flip para true em
# follow-up commit pos-merge conforme AC9 (decisao PO 2026-04-17).
# Habilita load/unload explicito via ModelGPU context manager, desbloqueando
# stories 9.3 (Wav2Vec2) e 9.5 (py-feat) no RTX 4060 8.6GB.
MODEL_ORCHESTRATOR_ENABLED = os.getenv("MODEL_ORCHESTRATOR_ENABLED", "false").lower() == "true"


def is_orchestrator_enabled() -> bool:
    """Helper testavel pra flag Story 9.2."""
    return os.getenv("MODEL_ORCHESTRATOR_ENABLED", "false").strip().lower() == "true"


# Feature flags Story 9.4 — prosody deep dive (CPU-only).
# Independentes entre si — rollout granular.
OPENSMILE_ENABLED = os.getenv("OPENSMILE_ENABLED", "false").lower() == "true"
PYANNOTE_VAD_ENABLED = os.getenv("PYANNOTE_VAD_ENABLED", "false").lower() == "true"


def is_opensmile_enabled() -> bool:
    """Helper testavel pra flag openSMILE eGeMAPS (Story 9.4)."""
    return os.getenv("OPENSMILE_ENABLED", "false").strip().lower() == "true"


def is_pyannote_vad_enabled() -> bool:
    """Helper testavel pra flag pyannote VAD (Story 9.4)."""
    return os.getenv("PYANNOTE_VAD_ENABLED", "false").strip().lower() == "true"


# Feature flag Story 9.3 — Wav2Vec2-Emotion ML (promove tonality 🟡 → 🟢).
# Default false — requer pip install -e ".[emotion]" + ativacao explicita.
TONALITY_ML_ENABLED = os.getenv("TONALITY_ML_ENABLED", "false").lower() == "true"


def is_tonality_ml_enabled() -> bool:
    """Helper testavel pra flag Wav2Vec2 emotion (Story 9.3)."""
    return os.getenv("TONALITY_ML_ENABLED", "false").strip().lower() == "true"


# Feature flag Story 9.5 — py-feat FACS (20 AUs + 6 emocoes).
# Default false — requer pip install -e ".[facs]".
PYFEAT_ENABLED = os.getenv("PYFEAT_ENABLED", "false").lower() == "true"


def is_pyfeat_enabled() -> bool:
    """Helper testavel pra flag py-feat FACS (Story 9.5)."""
    return os.getenv("PYFEAT_ENABLED", "false").strip().lower() == "true"
